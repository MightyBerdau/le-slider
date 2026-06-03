import asyncio
from datetime import datetime
from nicegui import ui
from pathlib import Path
import sounddevice as sd
from le_slider_io import CalibrationSchema
import yaml

from functions.audio_player import AudioPlayerBase
from functions.config import PATHS_CONFIG_PATH
from functions.gui import SettingsScreen
from functions.utils import get_device_supported_samplerates, get_current_time

CALIB_DIR = Path("calib/")


async def main():
    with open(PATHS_CONFIG_PATH, 'r', encoding="utf-8") as file:
        calib_filepath = Path(yaml.safe_load(file)['calibration_filepath'])
    
    calib_signal_filename = calib_filepath.name
    print(f'Calibration signal: {calib_filepath}')

    valid_devices = [d for d in sd.query_devices() if d['max_output_channels'] >= 2]
    settings = await SettingsScreen(
        device_list=valid_devices,
        device_supported_fs=get_device_supported_samplerates(valid_devices),
        fs_preferred=[48000, 44100]
    )

    # Extract selected device details
    device_id = settings['device_id']
    fs = settings['fs']
    selected_device = next(d for d in valid_devices if d['index'] == device_id)
    device_name = selected_device['name']

    player = AudioPlayerBase(
        device_id=device_id,
        blocksize=settings['blocksize'],
        target_fs=fs,
    )
    play_task: asyncio.Task | None = None

    async def toggle():
        nonlocal play_task
        if play_task and not play_task.done():
            player.stop()
            btn.set_text('Start')
        else:
            async def _play():
                await player.pre_load_stimulus(calib_filepath)
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

        # Generate timestamped filename: calib_YYYY-MM-DDTHH-mm-ss.json
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        calib_filename = f"calib_{timestamp}.json"
        calib_filepath_output = CALIB_DIR / calib_filename

        schema = CalibrationSchema(
            session_id=get_current_time(),
            device_id=device_id,
            device_name=device_name,
            fs=fs,
            measured_spl_left=spl_L,
            measured_spl_right=spl_R,
            desired_spl=spl_desired,
            calib_signal_path=calib_signal_filename,
            gain_calib=[gain_L, gain_R],
        )
        saved_path = schema.to_json_file(str(calib_filepath_output), prevent_overwrite=False)
        msg = f'Calibration saved: gain_L={gain_L:.4f}, gain_R={gain_R:.4f}'
        ui.notify(f'{msg} → {saved_path}', type='positive')
        print(f'✅ {msg} | file: {saved_path}')

    with ui.card().classes('absolute-center items-center gap-4').style('min-width: 340px;'):
        ui.label('Calibration').classes('text-xl font-bold')
        ui.label(f'Signal: {calib_signal_filename}').classes('text-sm text-gray-500')
        ui.label(f'Device: {device_name} @ {fs} Hz').classes('text-sm text-gray-500')

        btn = ui.button('Start', on_click=toggle)

        ui.separator()

        ui.label('SPL Measurement').classes('text-base font-semibold')
        spl_L_field       = ui.input(label='Measured SPL — Left ear (dB)',  value='').style('width: 100%;')
        spl_R_field       = ui.input(label='Measured SPL — Right ear (dB)', value='').style('width: 100%;')
        spl_desired_field = ui.input(label='Desired SPL (dB)',               value='').style('width: 100%;')

        ui.button('Save Calibration', on_click=save_calibration, icon='save').style('width: 100%;')


ui.timer(0, main, once=True)
ui.run(title='Calibration', reload=False)