"""
Unit tests for AudioPlayer base class and callback methods.

Tests base class functionality for audio playback and rating recording.
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, MagicMock, patch, call, AsyncMock, ANY
from functions.audio_player import AudioPlayer, AudioPlayerBase


class TestAudioPlayerBase:
    """Test AudioPlayerBase class methods."""
    
    @pytest.fixture
    def base_player(self):
        """Create a base audio player instance for testing."""
        return AudioPlayerBase(
            device_id=0,
            blocksize=256,
            target_fs=48000
        )
    
    def test_audio_player_base_initialization(self, base_player):
        """Test AudioPlayerBase stores initialization parameters."""
        assert base_player.blocksize == 256
        assert base_player._device_id == 0
        assert base_player._target_fs == 48000
        # AudioPlayerBase doesn't have a slider attribute (only AudioPlayer does)
    
    def test_audio_player_base_blocksize_property(self, base_player):
        """Test blocksize property."""
        assert base_player.blocksize == 256
    
    def test_audio_player_base_fs_property(self, base_player):
        """Test fs property returns target_fs."""
        assert base_player.fs == 48000
    
    def test_audio_player_base_callback_fills_buffer(self, base_player):
        """Test _callback fills output buffer correctly."""
        # Setup callback state
        base_player._audio = np.ones((1000, 2))  # Stereo audio filled with ones
        base_player._idx_start = 0
        base_player._done = MagicMock()
        base_player._loop = MagicMock()
        
        # Create output buffer
        outdata = np.zeros((256, 2))
        
        # Call callback
        base_player._callback(outdata, 256, None, None)
        
        # Output should be filled with ones (from the audio data)
        assert np.all(outdata == 1)
    
    def test_audio_player_base_callback_advances_index(self, base_player):
        """Test _callback advances the audio index."""
        base_player._audio = np.zeros((1000, 2))
        base_player._idx_start = 0
        base_player._done = MagicMock()
        base_player._loop = MagicMock()
        
        outdata = np.zeros((256, 2))
        base_player._callback(outdata, 256, None, None)
        
        # Index should advance by frames
        assert base_player._idx_start == 256
    
    def test_audio_player_base_callback_pads_with_zeros(self, base_player):
        """Test _callback pads with zeros when audio ends."""
        # Audio is 256 samples, callback requests 512
        base_player._audio = np.ones((256, 2))
        base_player._idx_start = 0
        base_player._done = MagicMock()
        base_player._loop = MagicMock()
        
        outdata = np.zeros((512, 2))
        base_player._callback(outdata, 512, None, None)
        
        # First 256 samples should be ones, rest should be zeros
        assert np.all(outdata[:256] == 1)
        assert np.all(outdata[256:] == 0)
    
    def test_audio_player_base_callback_signals_done(self, base_player):
        """Test _callback signals done event when audio ends."""
        base_player._audio = np.zeros((256, 2))
        base_player._idx_start = 0
        base_player._done = MagicMock()
        base_player._loop = MagicMock()
        
        outdata = np.zeros((512, 2))
        base_player._callback(outdata, 512, None, None)
        
        # Should signal done
        base_player._loop.call_soon_threadsafe.assert_called_once()
        # The argument should be a callable that sets done
        call_args = base_player._loop.call_soon_threadsafe.call_args
        assert call_args is not None


class TestAudioPlayerCallbackRatingCollection:
    """Test AudioPlayer._callback method for rating collection."""
    
    @pytest.fixture
    def player_with_callback_state(self):
        """Create player with callback state for testing."""
        mock_slider = Mock()
        mock_slider.value = 3.5
        player = AudioPlayer(
            rating_slider=mock_slider,
            device_id=0,
            blocksize=256,
            target_fs=48000
        )
        # Setup callback state
        player._audio = np.zeros((1000, 2))
        player._idx_start = 0
        player.ratings = []
        player._done = MagicMock()
        player._loop = MagicMock()
        return player, mock_slider
    
    def test_callback_collects_ratings(self, player_with_callback_state):
        """Test _callback collects slider ratings."""
        player, mock_slider = player_with_callback_state
        mock_slider.value = 3.5
        
        outdata = np.zeros((256, 2))
        player._callback(outdata, 256, None, None)
        
        # Rating should be recorded
        assert len(player.ratings) == 1
        assert player.ratings[0] == 3.5
    
    def test_callback_collects_multiple_ratings(self, player_with_callback_state):
        """Test _callback collects multiple ratings on repeated calls."""
        player, mock_slider = player_with_callback_state
        
        slider_values = [1.0, 2.0, 3.0, 4.0, 5.0]
        for val in slider_values:
            mock_slider.value = val
            outdata = np.zeros((256, 2))
            player._callback(outdata, 256, None, None)
        
        # All ratings should be recorded
        assert len(player.ratings) == 5
        assert player.ratings == slider_values
    
    def test_callback_rating_order(self, player_with_callback_state):
        """Test _callback maintains rating order."""
        player, mock_slider = player_with_callback_state
        
        # Change slider value multiple times
        for i, val in enumerate([5.0, 4.5, 3.0, 2.5, 1.0]):
            mock_slider.value = val
            outdata = np.zeros((256, 2))
            player._callback(outdata, 256, None, None)
        
        # Ratings should be in order of collection
        assert player.ratings == [5.0, 4.5, 3.0, 2.5, 1.0]
