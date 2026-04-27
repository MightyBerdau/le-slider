
import os
import sounddevice as sd
import yaml

from .audio_player import AudioPlayer
from .config import SLIDER_CONFIG_PATH, STIMULUS_LISTS_PATH, RESULTS_PATH
from le_slider_io import RatingRecordingSchema
from .gui import (StartDialog, PostStimulusDialog, EndScreen, RatingSlider)
from .utils import get_current_time

class MeasurementSession:
    def __init__(self):
        """Initialize MeasurementSession and load configuration files.
        
        Reads slider configuration, stimulus lists, and valid audio devices
        from configuration files on initialization.
        """
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
        """Get slider configuration dictionary.
        
        Returns:
            Dictionary with slider configuration parameters
        """
        return self._slider_config

    @property
    def measurement_lists(self) -> list[str]:
        """Get list of available stimulus list filenames.
        
        Returns:
            Sorted list of stimulus list filenames
        """
        return self._measurement_lists

    @property
    def valid_sounddevices(self):
        """Get list of valid stereo output audio devices.
        
        Returns:
            List of sound device dictionaries with 2 output channels
        """
        return self._valid_sounddevices

    def _read_configs(self):
        """Read all configuration files needed for the session."""
        self._read_slider_config()

    def _read_slider_config(self):
        """Read slider configuration from YAML file.
        
        Stores configuration in self._slider_config.
        """
        with open(SLIDER_CONFIG_PATH, 'r', encoding="utf-8") as file:
            slider_config = yaml.safe_load(file)
        self._slider_config = slider_config

    def _read_measurement_lists(self):
        """Read stimulus list filenames from directory.
        
        Filters for .txt files and sorts them alphabetically.
        """
        measurement_lists_unsorted = [file for file in os.listdir(STIMULUS_LISTS_PATH) if '.txt' in file]
        self._measurement_lists = sorted(measurement_lists_unsorted)

    def _read_valid_sounddevices(self):
        """Read and filter stereo output audio devices.
        
        Only includes devices with exactly 2 output channels.
        """
        self._valid_sounddevices = [d for d in sd.query_devices() if d['max_output_channels'] == 2]

    def _write_recordings(self, ratings: list, stimulus_path: str, stimulus_start:str, stimulus_end:str):
        """Save recording data and ratings to JSON file.
        
        Args:
            ratings: List of slider ratings collected during stimulus
            stimulus_path: Path to the played stimulus audio file
            stimulus_start: ISO format timestamp when stimulus started
            stimulus_end: ISO format timestamp when stimulus ended
        """
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
        """Play stimulus audio and record slider ratings with timestamps.
        
        Args:
            stimulus_path: Path to stimulus audio file
            
        Returns:
            Tuple of (ratings, stimulus_start, stimulus_end) where:
            - ratings: List of slider values recorded during playback
            - stimulus_start: ISO format timestamp when playback started
            - stimulus_end: ISO format timestamp when playback ended
        """
        self._slider.enable()
        stimulus_start = get_current_time()
        ratings = await self._audio_player.play_stimulus_and_record_ratings(stimulus_path)
        stimulus_end = get_current_time()
        self._slider.disable()
        return ratings, stimulus_start, stimulus_end

    async def run(self):
        """Defines the general measurement routine"""
        for stimulus_path in self._filepath_list:
            await StartDialog()
            ratings, stimulus_start, stimulus_end = await self.play_rec_and_time(stimulus_path) 
            self._write_recordings(ratings, stimulus_path, stimulus_start, stimulus_end)
            await PostStimulusDialog()

        EndScreen().open()