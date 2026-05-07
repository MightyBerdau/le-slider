import asyncio
from nicegui import ui
import sounddevice as sd

from functions.audio_player import AudioPlayerBase
from functions.gui import SettingsScreen
from functions.utils import get_device_supported_samplerates

CALIB_FILEPATH = "C:/Users/berdmt/Desktop/listening-effort-and-dip-listening/res/speech_shaped_noise/SSN.wav"

async def main():
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
        else:
            async def _play():
                await player.play_stimulus(CALIB_FILEPATH)
                btn.set_text('Start')
            play_task = asyncio.create_task(_play())
            btn.set_text('Stop')

    with ui.card().classes('absolute-center items-center gap-4'):
        ui.label('Calibration Playback').classes('text-xl font-bold')
        btn = ui.button('Start', on_click=toggle)

ui.timer(0, main, once=True)
ui.run(title='Audio Preview', reload=False)