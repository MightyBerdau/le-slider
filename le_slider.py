from nicegui import ui
import os
import sounddevice as sd

from functions.utils_gui_new import (SettingsScreen, StartDialog, PostStimulusDialog, EndScreen, RatingSlider)

import asyncio
import numpy as np

import soundfile as sf

import logging

logger = logging.getLogger(__name__)

class AudioPlayer:
    def __init__(self, rating_slider: RatingSlider,
                 device_id: int, blocksize: int, buffersize: int):
        self._slider = rating_slider
        self._device_id = device_id
        self._blocksize = blocksize
        self._buffersize = buffersize
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

    async def play_stimulus_and_record_ratings(self, audio, fs):
        self._done = asyncio.Event()
        self._loop = asyncio.get_event_loop()
        self._idx_start = 0
        self.ratings = []
        self._audio = audio
        self._fs = fs
        
        with sd.OutputStream(
            callback=self._callback,
            samplerate=self._fs,
            channels=self._audio.shape[1],
            blocksize=self._blocksize,
            device=self._device_id,
        ):
            await self._done.wait()
        return self.ratings


def read_measurement_lists(base_path:str) -> list[str]:
    txt_file_list_unsorted = [file for file in os.listdir(base_path) if '.txt' in file] # must be .txt!
    txt_file_list = sorted(txt_file_list_unsorted)
    return txt_file_list

def read_valid_sounddevices() -> sd.DeviceList:
    # Required: binaural playback system (TODO remove hard that constraint)
    device_list = [d for d in sd.query_devices() if d['max_output_channels'] == 2]
    return device_list

import json

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

import matplotlib.pyplot as plt

async def run_experiment(): # TODO better: run_measurement()
    results_path = 'results/'

    # INITIAL SETUP
    slider = RatingSlider(value_init=1)
    slider.disable()

    # RETRIEVE RUNTIME SETTINGS FROM USER
    txt_file_list = read_measurement_lists('txt_lists_debugging') # TODO one fixed folder for this project 
    device_list = read_valid_sounddevices()
    settings = await SettingsScreen(txt_file_list, device_list) # Settings for the Ratings Recorder...

    # TODO A SESSION CLASS COULD BE INSTANTIATED HERE...

    # READ SELECTED STIMULUS LIST
    with open(os.path.join('txt_lists_debugging', settings['stimulus_list']), 'r', encoding='utf-8') as f:
        filepath_list = [line.strip() for line in f if line.strip()]

    # SETTING UP AUDIO BASED ON PROVIDED SETTINGS
    audio_player = AudioPlayer(
        slider,
        settings['device_id'],
        settings['blocksize'],
        settings['buffersize']
    )

    await StartDialog()

    for ii, filepath in enumerate(filepath_list):
        data, fs = sf.read(filepath)
        
        slider.enable()
        ratings = await audio_player.play_stimulus_and_record_ratings(data, fs)
        slider.disable()

        # Saving TODO
        write_recordings(
            participant_id=settings['participant_id'],
            stimulus_file=filepath,
            output_dir=results_path,
            recordings=ratings
        )

        if ii<len(filepath_list)-1:
            await PostStimulusDialog() # technically could appear while saving...
        
    EndScreen().open()

    # await asyncio.to_thread(plot_ratings, audio_player.ratings, settings['blocksize'], audio_player._fs)

def plot_ratings(ratings, blocksize, samplerate):
    time_axis = np.arange(len(ratings)) * blocksize / samplerate
    fig, ax = plt.subplots()
    ax.plot(time_axis, ratings)
    ax.set_xlabel('Zeit (s)')
    ax.set_ylabel('Höranstrengung')
    plt.show()  # blockiert bis Fenster geschlossen – daher im Thread


ui.timer(0, run_experiment, once=True)
ui.run(host='0.0.0.0')