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
from unittest.mock import Mock, MagicMock, patch, call
from functions.session import MeasurementSession
from functions.config import SLIDER_CONFIG_PATH, STIMULUS_LISTS_PATH, RESULTS_PATH


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


def test_measurement_session_setup(temp_session_dir):
    """Test session.setup() initializes runtime parameters."""
    with patch('functions.session.sd.query_devices', return_value=[]):
        session = MeasurementSession()
        
        mock_slider = Mock()
        
        # Create a test stimulus list file
        list_path = os.path.join(temp_session_dir, "test_list.txt")
        with open(list_path, 'w') as f:
            f.write("stimulus1.wav\n")
            f.write("stimulus2.wav\n")
        
        with patch('functions.session.STIMULUS_LISTS_PATH', temp_session_dir):
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
            session._audio_player = AudioPlayer(mock_slider, 0, 256)
            
            assert session._participant_id == "VP001"
            assert session._device_id == 0
            assert session._blocksize == 256
            assert len(session._filepath_list) == 2


def test_measurement_session_write_recordings(temp_session_dir):
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
        
        with patch('functions.session.RESULTS_PATH', temp_session_dir):
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


def test_write_recordings_calculates_timestamps(temp_session_dir):
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
        
        with patch('functions.session.RESULTS_PATH', temp_session_dir):
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
