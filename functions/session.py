
import os
from pathlib import Path
import sounddevice as sd
import yaml

from .audio_player import AudioPlayer
from .config import SLIDER_CONFIG_PATH, PATHS_CONFIG_PATH, CALIB_CONFIG_PATH
from le_slider_io import RatingRecordingSchema, CalibrationSchema
from .gui import (StartDialog, PostStimulusDialog, EndScreen, RatingSlider, ErrorDialog)
from .utils import get_current_time, validate_stimulus_files, get_stimulus_samplerates
from .errors import MissingStimulisError, MissingCalibrationFileError

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
        self._target_fs = None
        self._calib_gain = None

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
    def valid_sounddevices(self) -> list[dict]:
        """Get list of valid stereo output audio devices.
        
        Returns:
            List of sound device dictionaries with 2 output channels
        """
        return self._valid_sounddevices

    def _read_configs(self):
        """Read all configuration files needed for the session.
        
        Currently reads the slider configuration from YAML file. This method
        serves as the main orchestrator for configuration loading and can be
        extended to load additional configuration files as needed.
        
        Called during __init__() to ensure all required configurations are
        available before session setup.
        """
        self._load_paths_config()
        self._read_slider_config()
        self._load_calibration()

    def _load_paths_config(self):
        """TODO doc"""
        with open(PATHS_CONFIG_PATH, 'r', encoding="utf-8") as file:
            paths_config = yaml.safe_load(file)
        self._paths_config = paths_config

    def _read_slider_config(self):
        """Read slider configuration from YAML file.
        
        Stores configuration in self._slider_config.
        """
        with open(SLIDER_CONFIG_PATH, 'r', encoding="utf-8") as file:
            slider_config = yaml.safe_load(file)
        self._slider_config = slider_config

    def _load_calibration(self):
        """Load calibration gain from config/calibration.json.

        Raises:
            MissingCalibrationFileError: If calibration.json does not exist.
        """
        try:
            schema = CalibrationSchema.from_json_file(CALIB_CONFIG_PATH)
        except FileNotFoundError:
            raise MissingCalibrationFileError()

        self._calib_gain = schema.gain_calib
        print(
            f"\n🎚️  Calibration loaded:"
            f"\n   Timestamp : {schema.session_id}"
            f"\n   Gain L    : {self._calib_gain[0]:.4f}"
            f"\n   Gain R    : {self._calib_gain[1]:.4f}\n"
        )

    def _read_measurement_lists(self):
        """Read stimulus list filenames from directory.
        
        Filters for .txt files and sorts them alphabetically.
        """
        measurement_lists_unsorted = [file.name for file in Path(self._paths_config['measurement_lists']).glob('*.txt')]
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
        
        stimulus_base = Path(stimulus_path).stem
        filename = f"{self._participant_id}_{stimulus_base}.json"
        filepath = Path(self._paths_config['results']) / filename

        schema.to_json_file(str(filepath))

    def setup(
            self,
            slider:RatingSlider,
            participant_id:int,
            stimulus_list:str,
            device_id:int,
            blocksize:int,
            fs:int):
        """Call this just before starting the session to implement the runtime arguments provided by the user.
        
        Args:
            slider: RatingSlider instance for user interactions
            participant_id: Unique identifier for this measurement session
            stimulus_list: Filename of stimulus list to use
            device_id: Audio device ID for playback
            blocksize: Audio buffer blocksize in samples
            fs: Target sampling rate in Hz for all audio playback
            
        Raises:
            MissingStimulisError: If any stimulus files referenced in the measurement list do not exist.
        """
        self._slider = slider
        self._participant_id = participant_id
        self._stimulus_list = stimulus_list
        self._device_id = device_id
        self._blocksize = blocksize
        self._target_fs = fs

        with open(Path(self._paths_config['measurement_lists']) / self._stimulus_list, 'r', encoding='utf-8') as f:
            self._filepath_list = [line.strip() for line in f if line.strip()]

        # Validate that all stimulus files exist before proceeding
        is_valid, missing_files = validate_stimulus_files(self._filepath_list, str(Path.cwd()))
        if not is_valid:
            ErrorDialog(missing_files).open()
            raise MissingStimulisError(missing_files)

        # Check sampling rates and warn about resampling
        stimulus_fs_dict = get_stimulus_samplerates(self._filepath_list, str(Path.cwd()))
        files_to_resample = [fp for fp, file_fs in stimulus_fs_dict.items() if file_fs is not None and file_fs != self._target_fs]
        
        if files_to_resample:
            print(f"\n⚠️  Resampling Notice:")
            print(f"The following stimuli will be resampled to {self._target_fs} Hz:")
            for fp in files_to_resample:
                actual_fs = stimulus_fs_dict[fp]
                print(f"  - {fp} ({actual_fs} Hz → {self._target_fs} Hz)")
            print()

        self._audio_player = AudioPlayer(
                self._slider,
                self._device_id,
                self._blocksize,
                self._target_fs,
                calib_gain=self._calib_gain
            )

    async def play_rec_and_time(self, stimulus_path) -> tuple[list[float], str, str]:
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

    async def run(self) -> None:
        """Execute the complete measurement session workflow.
        
        Iterates through all stimuli in the filepath_list, presenting dialogs
        and collecting ratings for each stimulus. For each stimulus:
        1. Opens StartDialog to prompt user to begin
        2. Calls play_rec_and_time to play audio and collect ratings
        3. Writes the recorded ratings to JSON file
        4. Opens PostStimulusDialog between stimuli
        
        After all stimuli are processed, opens EndScreen to display completion.
        This is an async method that must be awaited.
        """
        for stimulus_path in self._filepath_list:
            await StartDialog()
            ratings, stimulus_start, stimulus_end = await self.play_rec_and_time(stimulus_path) 
            self._write_recordings(ratings, stimulus_path, stimulus_start, stimulus_end)
            await PostStimulusDialog()

        EndScreen().open()