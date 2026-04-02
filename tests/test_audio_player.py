"""
Unit tests for audio player refactoring and event system.

Tests RatingAudioPlayer abstract class, event emission, and audio backend integration.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from functions.audio_player import (
    RatingAudioPlayer,
    FrameEvent,
    FrameEventType,
    FrameEventListener,
)


class MockAudioPlayer(RatingAudioPlayer):
    """Mock implementation of RatingAudioPlayer for testing."""
    
    def __init__(self, device=None, blocksize=256, buffersize=4):
        super().__init__(device=device, blocksize=blocksize, buffersize=buffersize)
        self.play_called = False
        self.played_file = None
    
    def play(self, filepath: str):
        """Mock play implementation."""
        self.play_called = True
        self.played_file = filepath
        
        # Simulate a short playback
        self._emit_playback_started()
        
        # Simulate 5 frames with device-accurate timing
        # Simulating 256 sample blocks at 48kHz gives 5.33ms per frame
        self._playback_start_time = 0.0  # Start at time 0
        self.fs = 48000
        for i in range(5):
            # Calculate elapsed time (device time)
            elapsed_sec = (i * self.blocksize) / 48000.0
            # Emit frame event
            event = FrameEvent(
                event_type=FrameEventType.FRAME_RENDERED,
                frame_index=i,
                timestamp_sec=elapsed_sec,
                blocksize=self.blocksize,
                sample_rate=48000,
            )
            self._emit_frame_event(event)
        
        self._emit_playback_finished()


class TestFrameEvent(unittest.TestCase):
    """Test FrameEvent dataclass."""
    
    def test_create_frame_event(self):
        """Test creating a frame event."""
        event = FrameEvent(
            event_type=FrameEventType.FRAME_RENDERED,
            frame_index=10,
            timestamp_sec=0.053,
            blocksize=256,
            sample_rate=48000,
        )
        
        self.assertEqual(event.event_type, FrameEventType.FRAME_RENDERED)
        self.assertEqual(event.frame_index, 10)
        self.assertEqual(event.timestamp_sec, 0.053)
        self.assertIsNone(event.error_message)
    
    def test_frame_event_with_error(self):
        """Test frame event with error message."""
        event = FrameEvent(
            event_type=FrameEventType.ERROR,
            frame_index=0,
            timestamp_sec=0.0,
            blocksize=0,
            sample_rate=0,
            error_message="Test error",
        )
        
        self.assertEqual(event.error_message, "Test error")


class TestRatingAudioPlayer(unittest.TestCase):
    """Test RatingAudioPlayer abstract base class."""
    
    def setUp(self):
        """Create test player instance."""
        self.player = MockAudioPlayer(device=0, blocksize=256, buffersize=4)
    
    def test_initialization(self):
        """Test player initialization."""
        self.assertEqual(self.player.device, 0)
        self.assertEqual(self.player.blocksize, 256)
        self.assertEqual(self.player.buffersize, 4)
        self.assertFalse(self.player.is_playing())
    
    def test_add_listener(self):
        """Test adding event listeners."""
        listener = Mock(spec=FrameEventListener)
        
        self.assertEqual(len(self.player._listeners), 0)
        self.player.add_listener(listener)
        self.assertEqual(len(self.player._listeners), 1)
    
    def test_add_duplicate_listener(self):
        """Test that duplicate listeners are not added."""
        listener = Mock(spec=FrameEventListener)
        
        self.player.add_listener(listener)
        self.player.add_listener(listener)
        
        self.assertEqual(len(self.player._listeners), 1)
    
    def test_remove_listener(self):
        """Test removing event listeners."""
        listener = Mock(spec=FrameEventListener)
        
        self.player.add_listener(listener)
        self.assertEqual(len(self.player._listeners), 1)
        
        self.player.remove_listener(listener)
        self.assertEqual(len(self.player._listeners), 0)
    
    def test_emit_frame_event_to_listeners(self):
        """Test that events are emitted to all listeners."""
        listener1 = Mock(spec=FrameEventListener)
        listener2 = Mock(spec=FrameEventListener)
        
        self.player.add_listener(listener1)
        self.player.add_listener(listener2)
        
        event = FrameEvent(
            event_type=FrameEventType.FRAME_RENDERED,
            frame_index=0,
            timestamp_sec=0.0,
            blocksize=256,
            sample_rate=48000,
        )
        
        self.player._emit_frame_event(event)
        
        listener1.on_frame_event.assert_called_once_with(event)
        listener2.on_frame_event.assert_called_once_with(event)
    
    def test_listener_exception_handling(self):
        """Test that exceptions in listeners don't break event emission."""
        listener_bad = Mock(spec=FrameEventListener)
        listener_bad.on_frame_event.side_effect = Exception("Test error")
        
        listener_good = Mock(spec=FrameEventListener)
        
        self.player.add_listener(listener_bad)
        self.player.add_listener(listener_good)
        
        event = FrameEvent(
            event_type=FrameEventType.FRAME_RENDERED,
            frame_index=0,
            timestamp_sec=0.0,
            blocksize=256,
            sample_rate=48000,
        )
        
        # Should not raise
        self.player._emit_frame_event(event)
        
        # Good listener should still be called
        listener_good.on_frame_event.assert_called_once()


class TestPlaybackEvents(unittest.TestCase):
    """Test playback event lifecycle."""
    
    def setUp(self):
        """Create test player and listener."""
        self.player = MockAudioPlayer()
        self.listener = Mock(spec=FrameEventListener)
        self.player.add_listener(self.listener)
    
    def test_playback_started_event(self):
        """Test playback started event is emitted."""
        self.player.play("dummy.wav")
        
        # Check that playback started event was emitted
        calls = self.listener.on_frame_event.call_args_list
        first_event = calls[0][0][0]
        
        self.assertEqual(first_event.event_type, FrameEventType.PLAYBACK_STARTED)
    
    def test_frame_events_emitted(self):
        """Test that frame events are emitted during playback."""
        self.player.play("dummy.wav")
        
        calls = self.listener.on_frame_event.call_args_list
        frame_events = [
            call[0][0] for call in calls
            if call[0][0].event_type == FrameEventType.FRAME_RENDERED
        ]
        
        # Mock player emits 5 frames
        self.assertEqual(len(frame_events), 5)
    
    def test_frame_indices_increment(self):
        """Test that frame indices increment correctly."""
        self.player.play("dummy.wav")
        
        calls = self.listener.on_frame_event.call_args_list
        frame_events = [
            call[0][0] for call in calls
            if call[0][0].event_type == FrameEventType.FRAME_RENDERED
        ]
        
        for i, event in enumerate(frame_events):
            self.assertEqual(event.frame_index, i)
    
    def test_timestamps_increment(self):
        """Test that relative timestamps increment correctly."""
        self.player.play("dummy.wav")
        
        calls = self.listener.on_frame_event.call_args_list
        frame_events = [
            call[0][0] for call in calls
            if call[0][0].event_type == FrameEventType.FRAME_RENDERED
        ]
        
        sample_rate = 48000
        blocksize = 256
        expected_interval = blocksize / sample_rate
        
        for i, event in enumerate(frame_events):
            expected_time = i * expected_interval
            self.assertAlmostEqual(event.timestamp_sec, expected_time, places=5)
    
    def test_playback_finished_event(self):
        """Test playback finished event is emitted."""
        self.player.play("dummy.wav")
        
        calls = self.listener.on_frame_event.call_args_list
        events = [call[0][0] for call in calls]
        
        # Last event should be playback finished
        last_event = events[-1]
        self.assertEqual(last_event.event_type, FrameEventType.PLAYBACK_FINISHED)


class TestPlaybackControl(unittest.TestCase):
    """Test playback control methods."""
    
    def setUp(self):
        """Create test player."""
        self.player = MockAudioPlayer()
    
    def test_is_playing_flag(self):
        """Test is_playing() flag during playback."""
        self.assertFalse(self.player.is_playing())
        
        self.player.play("dummy.wav")
        
        # After playback completes, should be False
        self.assertFalse(self.player.is_playing())
    
    def test_stop_signal(self):
        """Test stop signal mechanism."""
        self.assertFalse(self.player.should_stop())
        
        self.player.stop()
        
        self.assertTrue(self.player.should_stop())



if __name__ == '__main__':
    unittest.main()
