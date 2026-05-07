"""
Unit tests for the audio player module.

Tests AudioPlayer class functionality including initialization, properties,
and callback behavior.
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, MagicMock, patch, call
from functions.audio_player import AudioPlayer


@pytest.fixture
def mock_slider():
    """Create a mock RatingSlider."""
    slider = Mock()
    slider.value = 5.0
    return slider


@pytest.fixture
def audio_player(mock_slider):
    """Create a test audio player instance."""
    player = AudioPlayer(
        rating_slider=mock_slider,
        device_id=0,
        blocksize=256,
        target_fs=48000
    )
    return player


def test_audio_player_initialization(audio_player):
    """Test AudioPlayer is initialized with correct parameters."""
    assert audio_player.blocksize == 256
    assert audio_player._device_id == 0
    assert audio_player._slider is not None


def test_audio_player_blocksize_property(audio_player):
    """Test blocksize property."""
    assert audio_player.blocksize == 256


def test_audio_player_fs_property_initial(audio_player):
    """Test fs property returns target_fs."""
    assert audio_player.fs == 48000


def test_audio_player_ratings_none_initially(audio_player):
    """Test that ratings list is None until playback."""
    assert audio_player.ratings is None


def test_audio_player_audio_none_initially(audio_player):
    """Test that audio data is None initially."""
    assert audio_player._audio is None


def test_audio_player_different_blocksizes():
    """Test AudioPlayer with different blocksize values."""
    mock_slider = Mock()
    
    for blocksize in [128, 256, 512, 1024]:
        player = AudioPlayer(mock_slider, device_id=0, blocksize=blocksize, target_fs=48000)
        assert player.blocksize == blocksize


def test_audio_player_different_devices():
    """Test AudioPlayer with different device IDs."""
    mock_slider = Mock()
    
    for device_id in [0, 1, 2, -1]:
        player = AudioPlayer(mock_slider, device_id=device_id, blocksize=256, target_fs=48000)
        assert player._device_id == device_id


def test_callback_collects_slider_values(audio_player, mock_slider):
    """Test that _callback collects slider values."""
    # Setup callback state
    audio_player._audio = np.zeros((1000, 2))  # Stereo audio
    audio_player._fs = 48000
    audio_player._idx_start = 0
    audio_player.ratings = []
    audio_player._done = MagicMock()
    audio_player._loop = MagicMock()
    
    # Mock slider values
    mock_slider.value = 3.5
    
    # Create output buffer
    outdata = np.zeros((256, 2))
    
    # Call callback
    audio_player._callback(outdata, 256, None, None)
    
    # Should have recorded the slider value
    assert len(audio_player.ratings) == 1
    assert audio_player.ratings[0] == 3.5


def test_callback_advances_index(audio_player):
    """Test that _callback advances the audio index."""
    audio_player._audio = np.zeros((1000, 2))
    audio_player._fs = 48000
    audio_player._idx_start = 0
    audio_player.ratings = []
    audio_player._done = MagicMock()
    audio_player._loop = MagicMock()
    
    outdata = np.zeros((256, 2))
    audio_player._callback(outdata, 256, None, None)
    
    # Index should advance by frames
    assert audio_player._idx_start == 256


def test_callback_signals_done_on_end(audio_player):
    """Test that _callback signals done event when audio ends."""
    # Audio is 256 samples, callback requests 512
    audio_player._audio = np.zeros((256, 2))
    audio_player._fs = 48000
    audio_player._idx_start = 0
    audio_player.ratings = []
    audio_player._done = MagicMock()
    audio_player._loop = MagicMock()
    
    outdata = np.zeros((512, 2))
    audio_player._callback(outdata, 512, None, None)
    
    # Should have called done.set()
    audio_player._loop.call_soon_threadsafe.assert_called_once()


def test_callback_fills_remaining_with_zeros(audio_player):
    """Test that callback pads with zeros when audio ends."""
    # Audio is 256 samples, callback requests 512
    audio_player._audio = np.ones((256, 2))  # Fill with ones
    audio_player._fs = 48000
    audio_player._idx_start = 0
    audio_player.ratings = []
    audio_player._done = MagicMock()
    audio_player._loop = MagicMock()
    
    outdata = np.zeros((512, 2))
    audio_player._callback(outdata, 512, None, None)
    
    # First 256 samples should be ones, rest should be zeros
    assert np.all(outdata[:256] == 1)
    assert np.all(outdata[256:] == 0)


def test_audio_player_slider_integration(mock_slider):
    """Test AudioPlayer correctly stores slider reference."""
    player = AudioPlayer(mock_slider, device_id=1, blocksize=512, target_fs=48000)
    assert player._slider is mock_slider


def test_callback_with_multiple_channels(audio_player):
    """Test callback handles multi-channel audio correctly."""
    # Test with stereo (2 channels)
    audio_player._audio = np.zeros((1000, 2))
    audio_player._fs = 48000
    audio_player._idx_start = 0
    audio_player.ratings = []
    audio_player._done = MagicMock()
    audio_player._loop = MagicMock()
    
    outdata = np.zeros((256, 2))
    audio_player._callback(outdata, 256, None, None)
    
    assert audio_player._idx_start == 256
    assert len(audio_player.ratings) == 1


def test_callback_with_mono_audio(audio_player):
    """Test callback handles mono audio correctly."""
    # Test with mono (1 channel)
    audio_player._audio = np.zeros((1000, 1))
    audio_player._fs = 48000
    audio_player._idx_start = 0
    audio_player.ratings = []
    audio_player._done = MagicMock()
    audio_player._loop = MagicMock()
    
    outdata = np.zeros((256, 1))
    audio_player._callback(outdata, 256, None, None)
    
    assert audio_player._idx_start == 256


@pytest.mark.parametrize("blocksize,device", [
    (128, 0),
    (256, 1),
    (512, 0),
    (1024, 2),
])
def test_audio_player_various_configs(blocksize, device):
    """Test AudioPlayer with various configuration combinations."""
    mock_slider = Mock()
    player = AudioPlayer(mock_slider, device_id=device, blocksize=blocksize, target_fs=48000)
    
    assert player.blocksize == blocksize
    assert player._device_id == device
