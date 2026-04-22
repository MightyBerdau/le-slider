from nicegui import ui

from functions.gui import RatingSlider, SettingsScreen
from functions.network import get_local_ip
from functions.session import MeasurementSession

# TODO implement logging in session?
# import logging
# logger = logging.getLogger(__name__)

async def run_measurement():
    session = MeasurementSession() # Manages measurement procedure
    slider = RatingSlider(**session.slider_config) # GUI element for continuous user rating
    runtime_settings = await SettingsScreen(session.measurement_lists, session.valid_sounddevices)
    session.setup(slider, **runtime_settings) # Setting up with args chosen at runtime
    await session.run() # Starting measurement

ui.timer(0, run_measurement, once=True)

local_ip = get_local_ip()
port = 8080
print(f'Enter the following address your smartphone browser: http://{local_ip}:{port}')

ui.run(reload=False, host=local_ip, port=port)