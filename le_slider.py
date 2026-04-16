from nicegui import ui
import os
import sounddevice as sd

from functions.utils_gui_new import (SettingsScreen, StartDialog, PostStimulusDialog, EndScreen, RatingSlider)

import asyncio
import numpy as np

import soundfile as sf

import queue

import sys

import threading

import logging

logger = logging.getLogger(__name__)

class AudioPlayer:
    def __init__(self, audio_data: np.ndarray, fs: int, rating_slider: RatingSlider,
                 device_id: int, blocksize: int, buffersize: int):
        self._audio = audio_data
        self._fs = fs
        self._slider = rating_slider
        self._device_id = device_id
        self._blocksize = blocksize
        self._buffersize = buffersize
        self._position = 0
        self.ratings = []

        self._done = asyncio.Event()
        self._loop = asyncio.get_event_loop()  # Loop hier speichern, nicht im Callback

    def _callback(self, outdata, frames, time, status):
        chunk = self._audio[self._position : self._position + frames]
        
        if len(chunk) < frames:
            outdata[:len(chunk)] = chunk
            outdata[len(chunk):] = 0
            self._loop.call_soon_threadsafe(self._done.set)  # gespeicherten Loop nutzen
        else:
            outdata[:] = chunk
        
        self.ratings.append(self._slider.value)
        self._position += frames

    async def _run(self):
        with sd.OutputStream(
            callback=self._callback,
            samplerate=self._fs,
            channels=self._audio.shape[1],
            blocksize=self._blocksize,
            device=self._device_id,
        ):
            await self._done.wait()  # wartet exakt bis der Callback fertig ist

    def __await__(self):
        return self._run().__await__()


def read_measurement_lists(base_path:str) -> list[str]:
    txt_file_list_unsorted = [file for file in os.listdir(base_path) if '.txt' in file] # must be .txt!
    txt_file_list = sorted(txt_file_list_unsorted)
    return txt_file_list

def read_valid_sounddevices() -> sd.DeviceList:
    # Required: binaural playback system (TODO remove hard that constraint)
    device_list = [d for d in sd.query_devices() if d['max_output_channels'] == 2]
    return device_list

import matplotlib.pyplot as plt

async def run_experiment():
    # INITIAL SETUP
    slider = RatingSlider(value_init=1)
    slider.disable()

    # RETRIEVE RUNTIME SETTINGS FROM USER
    txt_file_list = read_measurement_lists('txt_lists_debugging')
    device_list = read_valid_sounddevices()
    settings = await SettingsScreen(txt_file_list, device_list) # Settings for the Ratings Recorder...
    await StartDialog()

    # SETTING UP AUDIO BASED ON PROVIDED SETTINGS
    data, fs = sf.read('audio_debugging/phase_mod_short.wav')
    audio_player = AudioPlayer(
        data,
        fs,
        slider,
        settings['device_id'],
        settings['blocksize'],
        settings['buffersize']
    )

    # START
    slider.enable()
    
    await audio_player  # Plays audio and blocks until finished
    slider.disable()

    # for ii in range(N):
    #     await asyncio.sleep(3) # 3 seconds for experimenting with the slider...
    #     slider.disable()

    #     if ii<N-1:
    #         await PostStimulusDialog()
    #         slider.enable()
        
    EndScreen().open()

    await asyncio.to_thread(plot_ratings, audio_player.ratings, settings['blocksize'], audio_player._fs)

def plot_ratings(ratings, blocksize, samplerate):
    time_axis = np.arange(len(ratings)) * blocksize / samplerate
    fig, ax = plt.subplots()
    ax.plot(time_axis, ratings)
    ax.set_xlabel('Zeit (s)')
    ax.set_ylabel('Höranstrengung')
    plt.show()  # blockiert bis Fenster geschlossen – daher im Thread


ui.timer(0, run_experiment, once=True)
ui.run(host='0.0.0.0')