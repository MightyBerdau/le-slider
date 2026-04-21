from nicegui import ui
import os
import sounddevice as sd

from functions.utils_gui import (SettingsScreen, StartDialog, PostStimulusDialog, EndScreen, RatingSlider)

import asyncio
import numpy as np
import json
import soundfile as sf

import logging

logger = logging.getLogger(__name__)

class AudioPlayer:
    def __init__(
            self,
            rating_slider: RatingSlider,
            device_id: int,
            blocksize: int):
        self._slider = rating_slider
        self._device_id = device_id
        self._blocksize = blocksize
        self._idx_start = None # 0
        self.ratings = None # []

        self._audio = None
        self._fs = None

        self._done = None # asyncio.Event()
        self._loop = None # asyncio.get_event_loop()

    def _callback(self, outdata, frames, time, status):
        chunk = self._audio[self._idx_start : self._idx_start + frames]
        
        if len(chunk) < frames:
            outdata[:len(chunk)] = chunk
            outdata[len(chunk):] = 0
            self._loop.call_soon_threadsafe(self._done.set)
        else:
            outdata[:] = chunk
        
        self.ratings.append(self._slider.value)
        self._idx_start += frames

    async def play_stimulus_and_record_ratings(self, filepath: str):
        self._audio, self._fs = sf.read(filepath)
        
        self._done = asyncio.Event()
        self._loop = asyncio.get_event_loop()
        self._idx_start = 0
        self.ratings = []
        
        with sd.OutputStream(
            callback=self._callback,
            samplerate=self._fs,
            channels=self._audio.shape[1],
            blocksize=self._blocksize,
            device=self._device_id,
        ):
            await self._done.wait()
        return self.ratings

def write_recordings(
        participant_id: str,
        stimulus_file: str,
        output_dir: str,
        recordings):
    # encode time of writing file
    stimulus_base = os.path.splitext(
            os.path.basename(stimulus_file)
        )[0]
    filename = f"{participant_id}_{stimulus_base}.json"
    filepath = os.path.join(output_dir, filename)

    os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(recordings, f, indent=2)

STIMULUS_LISTS_PATH = 'txt_lists_debugging'
RESULTS_PATH = 'results/'

class MeasurementSession:
    def __init__(self, slider:RatingSlider):
        self._slider = slider
        self._audio_player = None # created at runtime in self.setup()
        self._runtime_settings = None # read at runtime in self.setup()

        self._read_measurement_lists()
        self._read_valid_sounddevices()

    @property
    def measurement_lists(self) -> list[str]:
        return self._measurement_lists

    @property
    def valid_sounddevices(self):
        return self._valid_sounddevices

    def _read_measurement_lists(self):
        txt_file_list_unsorted = [file for file in os.listdir(STIMULUS_LISTS_PATH) if '.txt' in file] # must be .txt!
        self._measurement_lists = sorted(txt_file_list_unsorted)

    def _read_valid_sounddevices(self):
        self._valid_sounddevices = [d for d in sd.query_devices() if d['max_output_channels'] == 2]

    def setup(self, runtime_settings: dict):
        """Call this just before starting the session to implement the runtime arguments provided by the user"""
        self._runtime_settings = runtime_settings

        with open(os.path.join(STIMULUS_LISTS_PATH, self._runtime_settings['stimulus_list']), 'r', encoding='utf-8') as f:
            self._filepath_list = [line.strip() for line in f if line.strip()]

        self._audio_player = AudioPlayer(
                self._slider,
                runtime_settings['device_id'],
                runtime_settings['blocksize']
            )

    async def run(self):
        """Defines the general measurement routine"""
        await StartDialog()

        for ii, filepath in enumerate(self._filepath_list):
            # Play & record
            self._slider.enable()
            ratings = await self._audio_player.play_stimulus_and_record_ratings(filepath)
            self._slider.disable()
            
            # Write results
            write_recordings(
                participant_id=self._runtime_settings['participant_id'],
                stimulus_file=filepath,
                output_dir=RESULTS_PATH,
                recordings=ratings
            )

            await PostStimulusDialog()

        EndScreen().open()

async def run_measurement():
    slider = RatingSlider() # GUI element for continuous user rating
    session = MeasurementSession(slider) # Manages measurement procedure
    runtime_settings = await SettingsScreen(session.measurement_lists, session.valid_sounddevices)
    session.setup(runtime_settings) # Setting up with args chosen at runtime
    await session.run() # Starting measurement 

ui.timer(0, run_measurement, once=True)
ui.run(host='0.0.0.0')