from nicegui import ui

from functions.gui import RatingSlider, SettingsScreen
from functions.network import get_local_ip
from functions.session import MeasurementSession
from functions.utils import get_device_supported_samplerates

# TODO implement logging in session?
# import logging
# logger = logging.getLogger(__name__)

async def run_measurement():
    session = MeasurementSession() # Manages measurement procedure
    slider = RatingSlider(**session.slider_config) # GUI element for continuous user rating
    device_supported_fs = get_device_supported_samplerates(session.valid_sounddevices)
    runtime_settings = await SettingsScreen(
        session.measurement_lists,
        session.valid_sounddevices,
        device_supported_fs
    )
    session.setup(slider, **runtime_settings)
    await session.run() # Starting measurement

ui.timer(0, run_measurement, once=True)

local_ip = get_local_ip()
port = 8080
print(f'Enter the following address your smartphone browser: http://{local_ip}:{port}')

ui.run(reload=False, host=local_ip, port=port)