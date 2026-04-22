
import os
import sounddevice as sd
import yaml

from .audio_player import AudioPlayer
from .config import SLIDER_CONFIG_PATH, STIMULUS_LISTS_PATH, RESULTS_PATH
from .data_io import RatingRecordingSchema
from .gui import (StartDialog, PostStimulusDialog, EndScreen, RatingSlider)
from .utils import get_current_time

class MeasurementSession:
    def __init__(self):
        self._slider = None # linked at runtime in self.setup()
        self._audio_player = None # created at runtime in self.setup()
        # self._runtime_settings = None # read at runtime in self.setup()

        self._participant_id = None
        self._stimulus_list = None
        self._device_id = None
        self._blocksize = None

        self._session_id = get_current_time()

        self._read_configs()
        self._read_measurement_lists()
        self._read_valid_sounddevices()

    @property
    def slider_config(self) -> dict:
        return self._slider_config

    @property
    def measurement_lists(self) -> list[str]:
        return self._measurement_lists

    @property
    def valid_sounddevices(self): # TODO which type is returned?
        return self._valid_sounddevices

    def _read_configs(self):
        self._read_slider_config()

    def _read_slider_config(self):
        with open(SLIDER_CONFIG_PATH, 'r', encoding="utf-8") as file:
            slider_config = yaml.safe_load(file)
        self._slider_config = slider_config

    def _read_measurement_lists(self):
        measurement_lists_unsorted = [file for file in os.listdir(STIMULUS_LISTS_PATH) if '.txt' in file]
        self._measurement_lists = sorted(measurement_lists_unsorted)

    def _read_valid_sounddevices(self):
        self._valid_sounddevices = [d for d in sd.query_devices() if d['max_output_channels'] == 2]

    def _write_recordings(self, ratings: list, stimulus_path: str, stimulus_start:str, stimulus_end:str):
        time_stamps = [(ii+1)*self._blocksize/self._audio_player.fs for ii in range(len(ratings))]
        
        # TODO add fs, blocksize

        schema = RatingRecordingSchema(
            participant_id=self._participant_id,
            session_id=self._session_id,
            stimulus_path=stimulus_path,
            stimulus_list=self._stimulus_list,
            stimulus_start=stimulus_start,
            stimulus_end=stimulus_end,
            slider_config=self._slider_config,
            ratings=ratings,
            time_stamps=time_stamps
            )
        
        stimulus_base = os.path.splitext(os.path.basename(stimulus_path))[0]
        filename = f"{self._participant_id}_{stimulus_base}.json"
        filepath = os.path.join(RESULTS_PATH, filename)

        schema.to_json_file(filepath)

    def setup(
            self,
            slider:RatingSlider,
            participant_id:int,
            stimulus_list:str,
            device_id:int,
            blocksize:int):
        """Call this just before starting the session to implement the runtime arguments provided by the user"""
        self._slider = slider
        self._participant_id = participant_id
        self._stimulus_list = stimulus_list
        self._device_id = device_id
        self._blocksize = blocksize

        with open(os.path.join(STIMULUS_LISTS_PATH, self._stimulus_list), 'r', encoding='utf-8') as f:
            self._filepath_list = [line.strip() for line in f if line.strip()]

        self._audio_player = AudioPlayer(
                self._slider,
                self._device_id,
                self._blocksize
            )

    async def play_rec_and_time(self, stimulus_path):
        self._slider.enable()
        stimulus_start = get_current_time()
        ratings = await self._audio_player.play_stimulus_and_record_ratings(stimulus_path)
        stimulus_end = get_current_time()
        self._slider.disable()
        return ratings, stimulus_start, stimulus_end

    async def run(self):
        """Defines the general measurement routine"""
        await StartDialog()

        for stimulus_path in self._filepath_list:
            ratings, stimulus_start, stimulus_end = await self.play_rec_and_time(stimulus_path) 
            self._write_recordings(ratings, stimulus_path, stimulus_start, stimulus_end)
            await PostStimulusDialog()

        EndScreen().open()