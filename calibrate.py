import asyncio
from nicegui import ui
from pathlib import Path
import sounddevice as sd
from le_slider_io import CalibrationSchema

from functions.audio_player import AudioPlayerBase
from functions.config import CALIB_CONFIG_PATH
from functions.errors import MissingCalibrationSignalError
from functions.gui import SettingsScreen
from functions.utils import get_device_supported_samplerates, get_current_time

CALIB_DIR = Path("calib/")


async def main():
    # Fail fast if no calibration signal is present
    calib_files = list(CALIB_DIR.rglob("*.wav"))
    if not calib_files:
        ui.notify(
            str(MissingCalibrationSignalError(CALIB_DIR)),
            type='negative',
            timeout=0,
        )
        return
    calib_filepath = calib_files[0]
    print(f'Calibration signal: {calib_filepath}')

    valid_devices = [d for d in sd.query_devices() if d['max_output_channels'] >= 2]
    settings = await SettingsScreen(
        device_list=valid_devices,
        device_supported_fs=get_device_supported_samplerates(valid_devices),
    )

    player = AudioPlayerBase(
        device_id=settings['device_id'],
        blocksize=settings['blocksize'],
        target_fs=settings['fs'],
    )
    play_task: asyncio.Task | None = None

    async def toggle():
        nonlocal play_task
        if play_task and not play_task.done():
            player.stop()
            btn.set_text('Start')
        else:
            async def _play():
                await player.play_stimulus(calib_filepath)
                btn.set_text('Start')
            play_task = asyncio.create_task(_play())
            btn.set_text('Stop')

    def save_calibration():
        try:
            spl_L       = float(spl_L_field.value)
            spl_R       = float(spl_R_field.value)
            spl_desired = float(spl_desired_field.value)
        except ValueError:
            ui.notify('Please enter valid numbers for all SPL fields.', type='warning')
            return

        gain_L = 10 ** ((spl_desired - spl_L) / 20)
        gain_R = 10 ** ((spl_desired - spl_R) / 20)

        schema = CalibrationSchema(
            session_id=get_current_time(),
            gain_calib=[gain_L, gain_R],
        )
        saved_path = schema.to_json_file(CALIB_CONFIG_PATH, prevent_overwrite=False)
        msg = f'Calibration saved: gain_L={gain_L:.4f}, gain_R={gain_R:.4f}'
        ui.notify(f'{msg} → {saved_path}', type='positive')
        print(f'✅ {msg} | file: {saved_path}')

    with ui.card().classes('absolute-center items-center gap-4').style('min-width: 340px;'):
        ui.label('Calibration').classes('text-xl font-bold')
        ui.label(f'Signal: {calib_filepath.name}').classes('text-sm text-gray-500')

        btn = ui.button('Start', on_click=toggle)

        ui.separator()

        ui.label('SPL Measurement').classes('text-base font-semibold')
        spl_L_field       = ui.input(label='Measured SPL — Left ear (dB)',  value='').style('width: 100%;')
        spl_R_field       = ui.input(label='Measured SPL — Right ear (dB)', value='').style('width: 100%;')
        spl_desired_field = ui.input(label='Desired SPL (dB)',               value='').style('width: 100%;')

        ui.button('Save Calibration', on_click=save_calibration, icon='save').style('width: 100%;')


ui.timer(0, main, once=True)
ui.run(title='Calibration', reload=False)