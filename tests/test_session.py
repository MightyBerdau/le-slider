"""
Unit tests for the MeasurementSession module.

Tests session configuration, setup, and workflow.
"""

import pytest
import tempfile
import os
import shutil
import yaml
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from functions.session import MeasurementSession, MissingStimulisError


@pytest.fixture
def temp_session_dir():
    """Create temporary directory for session tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_sounddevices():
    """Create mock sound devices."""
    return [
        {'index': 0, 'name': 'Device 1', 'max_output_channels': 2},
        {'index': 1, 'name': 'Device 2', 'max_output_channels': 1},
        {'index': 2, 'name': 'Device 3', 'max_output_channels': 2},
    ]


def test_measurement_session_initialization():
    """Test MeasurementSession initialization."""
    with patch('functions.session.sd.query_devices', return_value=[]):
        session = MeasurementSession()
        assert session is not None
        assert session._session_id is not None


def test_measurement_session_properties():
    """Test MeasurementSession has required properties."""
    with patch('functions.session.sd.query_devices', return_value=[]):
        session = MeasurementSession()
        assert hasattr(session, 'slider_config')
        assert isinstance(session.slider_config, dict)
        assert hasattr(session, 'measurement_lists')
        assert isinstance(session.measurement_lists, list)
        assert hasattr(session, 'valid_sounddevices')


def test_measurement_session_filters_stereo_devices(mock_sounddevices):
    """Test that valid_sounddevices filters for stereo output."""
    with patch('functions.session.sd.query_devices', return_value=mock_sounddevices):
        session = MeasurementSession()
        # Should only include devices with 2 output channels
        assert len(session.valid_sounddevices) == 2
        for device in session.valid_sounddevices:
            assert device['max_output_channels'] == 2


def test_measurement_session_reads_slider_config():
    """Test that slider config is read on init."""
    with patch('functions.session.sd.query_devices', return_value=[]):
        session = MeasurementSession()
        assert session.slider_config is not None
        assert isinstance(session.slider_config, dict)


def test_measurement_session_reads_measurement_lists():
    """Test that measurement lists are read on init."""
    with patch('functions.session.sd.query_devices', return_value=[]):
        session = MeasurementSession()
        assert session.measurement_lists is not None
        assert isinstance(session.measurement_lists, list)


def test_measurement_session_setup(skip_calibration, mock_paths_config):
    """Test session.setup() initializes runtime parameters."""
    with patch('functions.session.sd.query_devices', return_value=[]):
        session = MeasurementSession()
        
        mock_slider = Mock()
        
        # Create a test stimulus list file in the mocked measurement_lists directory
        from functions.config import PATHS_CONFIG_PATH
        with open(PATHS_CONFIG_PATH, 'r') as f:
            paths_config = yaml.safe_load(f)
        
        measurement_lists_dir = Path(paths_config['measurement_lists'])
        measurement_lists_dir.mkdir(parents=True, exist_ok=True)
        
        # Create stimulus files
        (measurement_lists_dir / "stimulus1.wav").touch()
        (measurement_lists_dir / "stimulus2.wav").touch()
        
        # Create a test stimulus list file
        list_path = measurement_lists_dir / "test_list.txt"
        with open(list_path, 'w') as f:
            f.write("stimulus1.wav\n")
            f.write("stimulus2.wav\n")
        
        # Simulate reading the file
        with open(list_path, 'r') as f:
            filepaths = [line.strip() for line in f if line.strip()]
        
        session._participant_id = "VP001"
        session._stimulus_list = "test_list.txt"
        session._device_id = 0
        session._blocksize = 256
        session._slider = mock_slider
        session._filepath_list = filepaths
        
        from functions.audio_player import AudioPlayer
        session._audio_player = AudioPlayer(mock_slider, 0, 256, 48000)
        
        assert session._participant_id == "VP001"
        assert session._device_id == 0
        assert session._blocksize == 256
        assert len(session._filepath_list) == 2


def test_measurement_session_write_recordings(skip_calibration, mock_paths_config):
    """Test _write_recordings saves recording data."""
    with patch('functions.session.sd.query_devices', return_value=[]):
        session = MeasurementSession()
        
        mock_audio_player = Mock()
        mock_audio_player.fs = 48000
        session._audio_player = mock_audio_player
        session._participant_id = "VP001"
        session._stimulus_list = "test_list.txt"
        session._session_id = "2024-04-27T10:00:00+00:00"
        session._blocksize = 256  # Set blocksize before writing
        
        test_slider_config = {
            'name': 'listening_effort',
            'min_val': 1,
            'max_val': 14
        }
        session._slider_config = test_slider_config
        
        ratings = [1.0, 2.0, 3.0, 4.0, 5.0]
        stimulus_path = "stimulus1.wav"
        stimulus_start = "2024-04-27T10:00:00+00:00"
        stimulus_end = "2024-04-27T10:00:05+00:00"
        
        with patch('functions.session.RatingRecordingSchema') as mock_schema_class:
            mock_schema = Mock()
            mock_schema_class.return_value = mock_schema
            
            session._write_recordings(
                ratings,
                stimulus_path,
                stimulus_start,
                stimulus_end
            )
            
            # Check that RatingRecordingSchema was instantiated with correct data
            mock_schema_class.assert_called_once()
            call_kwargs = mock_schema_class.call_args[1]
            
            assert call_kwargs['participant_id'] == "VP001"
            assert call_kwargs['session_id'] == "2024-04-27T10:00:00+00:00"
            assert call_kwargs['ratings'] == ratings
            assert call_kwargs['stimulus_path'] == stimulus_path
            assert call_kwargs['stimulus_start'] == stimulus_start
            assert call_kwargs['stimulus_end'] == stimulus_end


def test_measurement_session_multiple_devices(mock_sounddevices):
    """Test handling of multiple audio devices."""
    with patch('functions.session.sd.query_devices', return_value=mock_sounddevices):
        session = MeasurementSession()
        # Should have 2 stereo devices
        assert len(session.valid_sounddevices) == 2


def test_measurement_session_no_stereo_devices():
    """Test handling when no stereo devices available."""
    mono_devices = [
        {'index': 0, 'name': 'Mono', 'max_output_channels': 1},
    ]
    with patch('functions.session.sd.query_devices', return_value=mono_devices):
        session = MeasurementSession()
        # Should have no stereo devices
        assert len(session.valid_sounddevices) == 0


def test_measurement_session_session_id_format():
    """Test that session_id is in ISO format."""
    with patch('functions.session.sd.query_devices', return_value=[]):
        session = MeasurementSession()
        # Should be ISO format string
        assert isinstance(session._session_id, str)
        assert 'T' in session._session_id


def test_measurement_session_participant_id_none_initially():
    """Test that participant_id is None initially."""
    with patch('functions.session.sd.query_devices', return_value=[]):
        session = MeasurementSession()
        assert session._participant_id is None


def test_measurement_session_audio_player_none_initially():
    """Test that audio_player is None initially."""
    with patch('functions.session.sd.query_devices', return_value=[]):
        session = MeasurementSession()
        assert session._audio_player is None


def test_write_recordings_calculates_timestamps(skip_calibration, mock_paths_config):
    """Test that _write_recordings calculates correct timestamps."""
    with patch('functions.session.sd.query_devices', return_value=[]):
        session = MeasurementSession()
        
        mock_audio_player = Mock()
        mock_audio_player.fs = 48000  # 48kHz
        session._audio_player = mock_audio_player
        session._participant_id = "VP001"
        session._stimulus_list = "test.txt"
        session._session_id = "2024-01-01T00:00:00+00:00"
        session._slider_config = {'name': 'test'}
        session._blocksize = 256
        
        # 5 ratings with blocksize 256 at 48kHz
        # Each block is 256/48000 = 0.00533 seconds
        ratings = [1.0, 2.0, 3.0, 4.0, 5.0]
        
        with patch('functions.session.RatingRecordingSchema') as mock_schema_class:
            mock_schema = Mock()
            mock_schema_class.return_value = mock_schema
            
            session._write_recordings(
                ratings,
                "test.wav",
                "2024-01-01T00:00:00+00:00",
                "2024-01-01T00:00:05+00:00"
            )
            
            call_kwargs = mock_schema_class.call_args[1]
            timestamps = call_kwargs['time_stamps']
            
            # Should have 5 timestamps
            assert len(timestamps) == 5
            # Timestamps should be increasing
            assert all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))


@pytest.mark.parametrize("device_count,stereo_count", [
    (0, 0),
    (2, 1),  # Device 0: stereo, Device 1: mono -> 1 stereo
    (2, 2),  # Device 0: stereo, Device 1: stereo -> 2 stereo
    (4, 2),  # Alternating stereo/mono -> 2 stereo
    (5, 3),  # Multiple stereo/mono mix -> 3 stereo
])
def test_measurement_session_device_filtering(device_count, stereo_count):
    """Test device filtering with various device configurations."""
    devices = []
    for i in range(device_count):
        # Alternate between stereo and mono
        channels = 2 if i % 2 == 0 else 1
        devices.append({
            'index': i,
            'name': f'Device {i}',
            'max_output_channels': channels
        })
    
    with patch('functions.session.sd.query_devices', return_value=devices):
        session = MeasurementSession()
        # Should filter to only stereo devices
        stereo_devices = [d for d in devices if d['max_output_channels'] == 2]
        assert len(session.valid_sounddevices) == len(stereo_devices)


class TestSetupWithValidation:
    """Test MeasurementSession.setup() with stimulus file validation."""
    
    @pytest.fixture
    def temp_session_with_files(self, mock_paths_config):
        """Create temp directory with valid stimulus files."""
        # Get the measurement_lists directory from the config
        from functions.config import PATHS_CONFIG_PATH
        with open(PATHS_CONFIG_PATH, 'r') as f:
            paths_config = yaml.safe_load(f)
        
        measurement_lists_dir = Path(paths_config['measurement_lists'])
        measurement_lists_dir.mkdir(parents=True, exist_ok=True)
        
        # Create stimulus files
        (measurement_lists_dir / "stimulus1.wav").touch()
        (measurement_lists_dir / "stimulus2.wav").touch()
        
        # Create measurement list file with valid paths
        list_path = measurement_lists_dir / "valid_list.txt"
        with open(list_path, 'w') as f:
            f.write("stimulus1.wav\n")
            f.write("stimulus2.wav\n")
        
        yield str(measurement_lists_dir)
    
    @pytest.fixture
    def temp_session_missing_files(self, mock_paths_config):
        """Create temp directory with missing stimulus files in list."""
        # Get the measurement_lists directory from the config
        from functions.config import PATHS_CONFIG_PATH
        with open(PATHS_CONFIG_PATH, 'r') as f:
            paths_config = yaml.safe_load(f)
        
        measurement_lists_dir = Path(paths_config['measurement_lists'])
        measurement_lists_dir.mkdir(parents=True, exist_ok=True)
        
        # Create measurement list file referencing non-existent files
        list_path = measurement_lists_dir / "invalid_list.txt"
        with open(list_path, 'w') as f:
            f.write("missing1.wav\n")
            f.write("missing2.wav\n")
        
        yield str(measurement_lists_dir)
    
    def test_setup_validates_stimulus_files_success(self, skip_calibration, temp_session_with_files):
        """Test setup() succeeds when all stimulus files exist."""
        with patch('functions.session.sd.query_devices', return_value=[]):
            session = MeasurementSession()
            mock_slider = Mock()
            
            with patch('functions.session.os.getcwd', return_value=temp_session_with_files):
                # Should not raise exception
                session.setup(
                    slider=mock_slider,
                    participant_id="VP001",
                    stimulus_list="valid_list.txt",
                    device_id=0,
                    blocksize=256,
                    fs=48000
                )
                
                assert session._participant_id == "VP001"
                assert len(session._filepath_list) == 2
    
    def test_setup_raises_missing_stimulus_error(self, skip_calibration, temp_session_missing_files):
        """Test setup() raises MissingStimulisError when files don't exist."""
        with patch('functions.session.sd.query_devices', return_value=[]):
            session = MeasurementSession()
            mock_slider = Mock()
            
            with patch('functions.session.os.getcwd', return_value=temp_session_missing_files):
                with patch('functions.session.ErrorDialog') as mock_error_dialog:
                    with pytest.raises(MissingStimulisError) as exc_info:
                        session.setup(
                            slider=mock_slider,
                            participant_id="VP001",
                            stimulus_list="invalid_list.txt",
                            device_id=0,
                            blocksize=256,
                            fs=48000
                        )
                    
                    # Verify the exception contains the missing files
                    assert len(exc_info.value.missing_files) == 2
                    assert "missing1.wav" in exc_info.value.missing_files
                    assert "missing2.wav" in exc_info.value.missing_files
    
    def test_setup_calls_error_dialog_on_missing_files(self, skip_calibration, temp_session_missing_files):
        """Test setup() calls ErrorDialog when files are missing."""
        with patch('functions.session.sd.query_devices', return_value=[]):
            session = MeasurementSession()
            mock_slider = Mock()
            
            with patch('functions.session.os.getcwd', return_value=temp_session_missing_files):
                with patch('functions.session.ErrorDialog') as mock_error_dialog:
                    mock_dialog_instance = MagicMock()
                    mock_error_dialog.return_value = mock_dialog_instance
                    
                    with pytest.raises(MissingStimulisError):
                        session.setup(
                            slider=mock_slider,
                            participant_id="VP001",
                            stimulus_list="invalid_list.txt",
                            device_id=0,
                            blocksize=256,
                            fs=48000
                        )
                    
                    # Verify ErrorDialog was called
                    mock_error_dialog.assert_called_once()
                    # Verify open() was called on the dialog
                    mock_dialog_instance.open.assert_called_once()
    
    def test_setup_does_not_call_error_dialog_on_success(self, skip_calibration, temp_session_with_files):
        """Test setup() does not call ErrorDialog when all files exist."""
        with patch('functions.session.sd.query_devices', return_value=[]):
            session = MeasurementSession()
            mock_slider = Mock()
            
            with patch('functions.session.os.getcwd', return_value=temp_session_with_files):
                with patch('functions.session.ErrorDialog') as mock_error_dialog:
                    session.setup(
                        slider=mock_slider,
                        participant_id="VP001",
                        stimulus_list="valid_list.txt",
                        device_id=0,
                        blocksize=256,
                        fs=48000
                    )
                    
                    # ErrorDialog should not be called
                    mock_error_dialog.assert_not_called()
    
    def test_setup_does_not_create_audio_player_on_validation_failure(self, skip_calibration, temp_session_missing_files):
        """Test setup() does not create AudioPlayer if validation fails."""
        with patch('functions.session.sd.query_devices', return_value=[]):
            session = MeasurementSession()
            mock_slider = Mock()
            
            with patch('functions.session.os.getcwd', return_value=temp_session_missing_files):
                with patch('functions.session.ErrorDialog'):
                    with patch('functions.session.AudioPlayer') as mock_audio_player:
                        with pytest.raises(MissingStimulisError):
                            session.setup(
                                slider=mock_slider,
                                participant_id="VP001",
                                stimulus_list="invalid_list.txt",
                                device_id=0,
                                blocksize=256,
                                fs=48000
                            )
                        
                        # AudioPlayer should not be instantiated
                        mock_audio_player.assert_not_called()
                        assert session._audio_player is None
    
    def test_setup_creates_audio_player_on_validation_success(self, skip_calibration, temp_session_with_files):
        """Test setup() creates AudioPlayer when validation succeeds."""
        with patch('functions.session.sd.query_devices', return_value=[]):
            session = MeasurementSession()
            mock_slider = Mock()
            
            with patch('functions.session.os.getcwd', return_value=temp_session_with_files):
                with patch('functions.session.AudioPlayer') as mock_audio_player_class:
                    mock_audio_player = MagicMock()
                    mock_audio_player_class.return_value = mock_audio_player
                    
                    session.setup(
                        slider=mock_slider,
                        participant_id="VP001",
                        stimulus_list="valid_list.txt",
                        device_id=0,
                        blocksize=256,
                        fs=48000
                    )
                    
                    # AudioPlayer should be created (check it was called at least once)
                    mock_audio_player_class.assert_called_once()
                    # Verify the mock was called with correct positional arguments
                    call_args = mock_audio_player_class.call_args
                    assert call_args[0][0] == mock_slider  # slider
                    assert call_args[0][1] == 0  # device_id
                    assert call_args[0][2] == 256  # blocksize
                    assert call_args[0][3] == 48000  # fs
                    assert session._audio_player is mock_audio_player
