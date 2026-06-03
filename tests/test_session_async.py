"""
Unit tests for async methods in MeasurementSession module.

Tests async workflow methods including run(), play_rec_and_time() and related async operations.
"""

import pytest
import asyncio
import tempfile
import os
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call, AsyncMock
from datetime import datetime
from functions.session import MeasurementSession
from functions.errors import MissingStimulisError


class TestPlayRecAndTime:
    """Test MeasurementSession.play_rec_and_time() async method."""
    
    @pytest.fixture
    def session_setup(self):
        """Setup a session for testing."""
        patcher = patch('functions.session.sd.query_devices', return_value=[])
        patcher.start()
        try:
            session = MeasurementSession()
            mock_slider = Mock()
            mock_slider.enable = Mock()
            mock_slider.disable = Mock()
            mock_audio_player = AsyncMock()
            mock_audio_player.play_stimulus_and_record_ratings = AsyncMock(
                return_value=[1.0, 2.0, 3.0, 4.0, 5.0]
            )
            session._slider = mock_slider
            session._audio_player = mock_audio_player
            yield session, mock_slider, mock_audio_player
        finally:
            patcher.stop()
    
    @pytest.mark.asyncio
    async def test_play_rec_and_time_enables_slider(self, session_setup):
        """Test that play_rec_and_time enables slider before playback."""
        session, mock_slider, mock_audio_player = session_setup
        
        await session.play_rec_and_time("test_stimulus.wav")
        
        # Slider should be enabled
        mock_slider.enable.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_play_rec_and_time_disables_slider(self, session_setup):
        """Test that play_rec_and_time disables slider after playback."""
        session, mock_slider, mock_audio_player = session_setup
        
        await session.play_rec_and_time("test_stimulus.wav")
        
        # Slider should be disabled
        mock_slider.disable.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_play_rec_and_time_calls_audio_player(self, session_setup):
        """Test that play_rec_and_time calls audio player with correct path."""
        session, mock_slider, mock_audio_player = session_setup
        
        await session.play_rec_and_time("test_stimulus.wav")
        
        # Audio player should be called with the stimulus path
        mock_audio_player.play_stimulus_and_record_ratings.assert_called_once_with(
            "test_stimulus.wav"
        )
    
    @pytest.mark.asyncio
    async def test_play_rec_and_time_returns_ratings(self, session_setup):
        """Test that play_rec_and_time returns ratings from audio player."""
        session, mock_slider, mock_audio_player = session_setup
        expected_ratings = [1.0, 2.0, 3.0, 4.0, 5.0]
        
        ratings, start_time, end_time = await session.play_rec_and_time("test_stimulus.wav")
        
        assert ratings == expected_ratings
    
    @pytest.mark.asyncio
    async def test_play_rec_and_time_returns_timestamps(self, session_setup):
        """Test that play_rec_and_time returns ISO format timestamps."""
        session, mock_slider, mock_audio_player = session_setup
        
        ratings, start_time, end_time = await session.play_rec_and_time("test_stimulus.wav")
        
        # Timestamps should be ISO format strings
        assert isinstance(start_time, str)
        assert isinstance(end_time, str)
        assert 'T' in start_time  # ISO format indicator
        assert 'T' in end_time
    
    @pytest.mark.asyncio
    async def test_play_rec_and_time_start_before_end(self, session_setup):
        """Test that start time is before or equal to end time."""
        session, mock_slider, mock_audio_player = session_setup
        
        ratings, start_time, end_time = await session.play_rec_and_time("test_stimulus.wav")
        
        # Parse timestamps and compare
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
        assert start_dt <= end_dt


class TestMeasurementSessionRun:
    """Test MeasurementSession.run() async method."""
    
    @pytest.fixture
    def session_with_stimuli(self):
        """Setup a session with multiple stimuli."""
        patcher = patch('functions.session.sd.query_devices', return_value=[])
        patcher.start()
        try:
            session = MeasurementSession()
            mock_slider = Mock()
            session._slider = mock_slider
            session._participant_id = "VP001"
            session._stimulus_list = "test_list.txt"
            session._blocksize = 256
            session._target_fs = 48000
            session._filepath_list = ["stimulus1.wav", "stimulus2.wav"]
            session._slider_config = {'name': 'test'}
            
            # Mock audio player and write method
            mock_audio_player = AsyncMock()
            mock_audio_player.play_stimulus_and_record_ratings = AsyncMock(
                return_value=[1.0, 2.0, 3.0]
            )
            mock_audio_player.pre_load_stimulus = AsyncMock()
            session._audio_player = mock_audio_player
            session._write_recordings = Mock()
            
            yield session
        finally:
            patcher.stop()
    
    @pytest.mark.asyncio
    async def test_run_processes_all_stimuli(self, session_with_stimuli):
        """Test that run() processes each stimulus in the filepath list."""
        session = session_with_stimuli
        
        # Create async mock for dialogs that return awaitable
        start_dialog_mock = AsyncMock(return_value=None)
        post_dialog_mock = AsyncMock(return_value=None)
        end_screen_mock = Mock()
        end_screen_instance = Mock()
        end_screen_mock.return_value = end_screen_instance
        
        with patch('functions.session.StartDialog', start_dialog_mock):
            with patch('functions.session.PostStimulusDialog', post_dialog_mock):
                with patch('functions.session.EndScreen', end_screen_mock):
                    await session.run()
        
        # Should process all stimuli
        assert session._audio_player.play_stimulus_and_record_ratings.call_count == 2
    
    @pytest.mark.asyncio
    async def test_run_calls_start_dialog_for_each_stimulus(self, session_with_stimuli):
        """Test that run() calls StartDialog for each stimulus."""
        session = session_with_stimuli
        
        start_dialog_mock = AsyncMock(return_value=None)
        post_dialog_mock = AsyncMock(return_value=None)
        end_screen_mock = Mock(return_value=Mock())
        
        with patch('functions.session.StartDialog', start_dialog_mock):
            with patch('functions.session.PostStimulusDialog', post_dialog_mock):
                with patch('functions.session.EndScreen', end_screen_mock):
                    await session.run()
        
        # StartDialog should be called twice (once per stimulus)
        assert start_dialog_mock.call_count == 2
    
    @pytest.mark.asyncio
    async def test_run_calls_post_stimulus_dialog_for_each_stimulus(self, session_with_stimuli):
        """Test that run() calls PostStimulusDialog for each stimulus."""
        session = session_with_stimuli
        
        start_dialog_mock = AsyncMock(return_value=None)
        post_dialog_mock = AsyncMock(return_value=None)
        end_screen_mock = Mock(return_value=Mock())
        
        with patch('functions.session.StartDialog', start_dialog_mock):
            with patch('functions.session.PostStimulusDialog', post_dialog_mock):
                with patch('functions.session.EndScreen', end_screen_mock):
                    await session.run()
        
        # PostStimulusDialog should be called twice (once per stimulus)
        assert post_dialog_mock.call_count == 2
    
    @pytest.mark.asyncio
    async def test_run_writes_recordings_for_each_stimulus(self, session_with_stimuli):
        """Test that run() writes recordings for each stimulus."""
        session = session_with_stimuli
        
        start_dialog_mock = AsyncMock(return_value=None)
        post_dialog_mock = AsyncMock(return_value=None)
        end_screen_mock = Mock(return_value=Mock())
        
        with patch('functions.session.StartDialog', start_dialog_mock):
            with patch('functions.session.PostStimulusDialog', post_dialog_mock):
                with patch('functions.session.EndScreen', end_screen_mock):
                    with patch('functions.session.get_current_time', return_value="2024-01-01T00:00:00+00:00"):
                        await session.run()
        
        # _write_recordings should be called twice
        assert session._write_recordings.call_count == 2
    
    @pytest.mark.asyncio
    async def test_run_shows_end_screen(self, session_with_stimuli):
        """Test that run() shows EndScreen after all stimuli."""
        session = session_with_stimuli
        
        start_dialog_mock = AsyncMock(return_value=None)
        post_dialog_mock = AsyncMock(return_value=None)
        end_screen_instance = Mock()
        end_screen_mock = Mock(return_value=end_screen_instance)
        
        with patch('functions.session.StartDialog', start_dialog_mock):
            with patch('functions.session.PostStimulusDialog', post_dialog_mock):
                with patch('functions.session.EndScreen', end_screen_mock):
                    await session.run()
        
        # EndScreen should be created and opened
        end_screen_mock.assert_called_once()
        end_screen_instance.open.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_processes_stimuli_in_order(self, session_with_stimuli):
        """Test that run() processes stimuli in the order they appear in the list."""
        session = session_with_stimuli
        stimulus_order = []
        
        async def track_stimulus(path):
            stimulus_order.append(path)
            return [1.0, 2.0, 3.0]
        
        session._audio_player.play_stimulus_and_record_ratings.side_effect = track_stimulus
        
        start_dialog_mock = AsyncMock(return_value=None)
        post_dialog_mock = AsyncMock(return_value=None)
        end_screen_mock = Mock(return_value=Mock())
        
        with patch('functions.session.StartDialog', start_dialog_mock):
            with patch('functions.session.PostStimulusDialog', post_dialog_mock):
                with patch('functions.session.EndScreen', end_screen_mock):
                    await session.run()
        
        # Stimuli should be processed in order
        assert stimulus_order == ["stimulus1.wav", "stimulus2.wav"]
    
    @pytest.mark.asyncio
    async def test_run_with_single_stimulus(self):
        """Test run() with only one stimulus."""
        patcher = patch('functions.session.sd.query_devices', return_value=[])
        patcher.start()
        try:
            session = MeasurementSession()
            session._slider = Mock()
            session._participant_id = "VP001"
            session._stimulus_list = "test_list.txt"
            session._filepath_list = ["single_stimulus.wav"]
            session._slider_config = {'name': 'test'}
            
            mock_audio_player = AsyncMock()
            mock_audio_player.play_stimulus_and_record_ratings = AsyncMock(return_value=[5.0])
            mock_audio_player.pre_load_stimulus = AsyncMock()
            session._audio_player = mock_audio_player
            session._write_recordings = Mock()
            
            start_dialog_mock = AsyncMock(return_value=None)
            post_dialog_mock = AsyncMock(return_value=None)
            end_screen_mock = Mock(return_value=Mock())
            
            with patch('functions.session.StartDialog', start_dialog_mock):
                with patch('functions.session.PostStimulusDialog', post_dialog_mock):
                    with patch('functions.session.EndScreen', end_screen_mock):
                        await session.run()
            
            # Should process the single stimulus
            mock_audio_player.play_stimulus_and_record_ratings.assert_called_once_with("single_stimulus.wav")
        finally:
            patcher.stop()
