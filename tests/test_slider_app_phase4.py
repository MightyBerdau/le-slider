"""
Integration tests for Phase 4: Refactored slider_app.py

Tests the integration of:
- SliderSession for orchestrating session workflows
- Configuration system (loading YAML, setting slider params)
- Audio event synchronization (RatingRecorder with audio player)
- Localization support throughout UI
"""

import unittest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from functions.session import SliderSession, SimpleSessionListener
from functions.config import SliderConfig
from functions.i18n import LanguagePack
from functions.data_io import RatingRecorder
from functions.audio_player import FrameEvent, FrameEventType
from functions.audio_player import RatingAudioPlayer


class TestSliderSession(unittest.TestCase):
    """Test SliderSession lifecycle and workflow management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = SliderConfig(
            name="test_slider",
            min_val=1,
            max_val=7,
            init_val=4,
            step=0.1,
            marker_step=1,
            categories_dict={1: "low", 4: "medium", 7: "high"}
        )
        
        # Create test stimulus list
        self.stimulus_file = os.path.join(self.temp_dir, "stimuli.txt")
        with open(self.stimulus_file, 'w') as f:
            f.write("stimulus1.wav\n")
            f.write("stimulus2.wav\n")
            f.write("stimulus3.wav\n")
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_session_initialization(self):
        """Test session creation with slider config."""
        session = SliderSession(
            slider_config=self.config,
            participant_id="VP001",
            stimulus_list_file=self.stimulus_file,
            output_dir=self.temp_dir,
            language="de"
        )
        
        self.assertEqual(session.participant_id, "VP001")
        self.assertEqual(session.slider_config.name, "test_slider")
        self.assertEqual(len(session.stimuli), 3)
        self.assertTrue(session.has_next_stimulus())
    
    def test_stimulus_list_loading(self):
        """Test loading stimulus list from file."""
        session = SliderSession(
            slider_config=self.config,
            participant_id="VP001",
            stimulus_list_file=self.stimulus_file,
            output_dir=self.temp_dir
        )
        
        self.assertEqual(session.get_current_stimulus(), "stimulus1.wav")
        self.assertEqual(len(session.stimuli), 3)
    
    def test_stimulus_navigation(self):
        """Test moving through stimulus list."""
        session = SliderSession(
            slider_config=self.config,
            participant_id="VP001",
            stimulus_list_file=self.stimulus_file,
            output_dir=self.temp_dir
        )
        
        # First stimulus
        self.assertEqual(session.get_current_stimulus(), "stimulus1.wav")
        self.assertTrue(session.has_next_stimulus())
        
        # Move to next
        session.next_stimulus()
        self.assertEqual(session.get_current_stimulus(), "stimulus2.wav")
        self.assertTrue(session.has_next_stimulus())
        
        # Move to next
        session.next_stimulus()
        self.assertEqual(session.get_current_stimulus(), "stimulus3.wav")
        self.assertTrue(session.has_next_stimulus())
        
        # Move to next (should reach end)
        session.next_stimulus()
        self.assertFalse(session.has_next_stimulus())
        self.assertIsNone(session.get_current_stimulus())
    
    def test_prepare_stimulus(self):
        """Test preparing a recording for a stimulus."""
        session = SliderSession(
            slider_config=self.config,
            participant_id="VP001",
            stimulus_list_file=self.stimulus_file,
            output_dir=self.temp_dir
        )
        
        recorder = session.prepare_stimulus("stimulus1.wav")
        
        self.assertIsNotNone(recorder)
        self.assertEqual(recorder.slider_config, self.config)
        self.assertEqual(recorder.participant_id, "VP001")
        self.assertEqual(recorder.stimulus_file, "stimulus1.wav")
    
    def test_callbacks_registered(self):
        """Test that callbacks can be registered and will be called."""
        session = SliderSession(
            slider_config=self.config,
            participant_id="VP001",
            stimulus_list_file=self.stimulus_file,
            output_dir=self.temp_dir
        )
        
        # Register mocks
        session.on_playback_started = MagicMock()
        session.on_playback_finished = MagicMock()
        session.on_stimulus_changed = MagicMock()
        session.on_session_finished = MagicMock()
        
        # These should be callable
        session.on_playback_started()
        session.on_playback_finished()
        session.on_stimulus_changed("test.wav")
        session.on_session_finished()
        
        session.on_playback_started.assert_called_once()
        session.on_playback_finished.assert_called_once()
        session.on_stimulus_changed.assert_called_once_with("test.wav")
        session.on_session_finished.assert_called_once()


class TestSessionLocalization(unittest.TestCase):
    """Test localization support in session."""
    
    def test_session_language_support(self):
        """Test that session supports multiple languages."""
        config = SliderConfig(
            name="test",
            min_val=1,
            max_val=5,
            init_val=3,
            step=0.1,
            marker_step=1,
            categories_dict={}
        )
        
        session_de = SliderSession(
            slider_config=config,
            participant_id="VP001",
            output_dir=tempfile.gettempdir(),
            language="de"
        )
        
        session_en = SliderSession(
            slider_config=config,
            participant_id="VP002",
            output_dir=tempfile.gettempdir(),
            language="en"
        )
        
        self.assertEqual(session_de.i18n.language, "de")
        self.assertEqual(session_en.i18n.language, "en")


class TestSimpleSessionListener(unittest.TestCase):
    """Test the SimpleSessionListener event bridge."""
    
    def test_listener_initialization(self):
        """Test creating a session listener."""
        callback = MagicMock()
        listener = SimpleSessionListener(slider_value_callback=callback)
        
        self.assertIsNotNone(listener)
        self.assertEqual(listener.current_slider_value, 0.0)
    
    def test_set_slider_value(self):
        """Test setting slider value in listener."""
        listener = SimpleSessionListener()
        listener.set_slider_value(4.5)
        
        self.assertEqual(listener.current_slider_value, 4.5)
    
    def test_frame_event_handling(self):
        """Test that listener can handle frame events."""
        listener = SimpleSessionListener()
        
        # Create mock frame event
        event = MagicMock(spec=FrameEvent)
        event.event_type = FrameEventType.FRAME_RENDERED
        
        # Should not raise
        listener.on_frame_event(event)


class TestSliderSessionRecording(unittest.TestCase):
    """Test recording integration in SliderSession."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = SliderConfig(
            name="test_slider",
            min_val=1,
            max_val=5,
            init_val=3,
            step=0.1,
            marker_step=1,
            categories_dict={}
        )
    
    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_recorder_creation(self):
        """Test that session creates recorder for stimulus."""
        session = SliderSession(
            slider_config=self.config,
            participant_id="VP001",
            output_dir=self.temp_dir
        )
        
        recorder = session.prepare_stimulus("test_audio.wav")
        
        self.assertIsNotNone(recorder)
        self.assertIsInstance(recorder, RatingRecorder)
    
    def test_save_recording(self):
        """Test saving recording to JSON."""
        session = SliderSession(
            slider_config=self.config,
            participant_id="VP001",
            output_dir=self.temp_dir
        )
        
        recorder = session.prepare_stimulus("test_audio.wav")
        recorder.set_audio_metadata(
            sample_rate=48000,
            blocksize=256,
            buffersize=4,
            duration_sec=10.0
        )
        
        # Add some test data
        recorder.add_frame(3.5)
        recorder.add_frame(4.0)
        recorder.add_frame(3.8)
        
        # Redirect to current recorder
        session.current_recorder = recorder
        
        # Save
        output_path = session.save_current_recording()
        
        self.assertIsNotNone(output_path)
        self.assertTrue(os.path.exists(output_path))
        self.assertTrue(output_path.endswith('.json'))
        
        # Validate JSON
        with open(output_path, 'r') as f:
            data = json.load(f)
            # Metadata is at top level
            self.assertIn('participant_id', data)
            self.assertIn('recordings', data)
            self.assertEqual(data['participant_id'], "VP001")


class TestSliderConfigIntegration(unittest.TestCase):
    """Test integration of config system with session."""
    
    def test_config_applied_to_session(self):
        """Test that slider config parameters are used by session."""
        config = SliderConfig(
            name="listening_effort",
            min_val=1,
            max_val=14,
            init_val=7,
            step=0.1,
            marker_step=1,
            categories_dict={
                1: "mühelos",
                7: "mittelgradig anstrengend",
                14: "nur Störgeräusch"
            }
        )
        
        session = SliderSession(
            slider_config=config,
            participant_id="VP001",
            output_dir=tempfile.gettempdir()
        )
        
        self.assertEqual(session.slider_config.min_val, 1)
        self.assertEqual(session.slider_config.max_val, 14)
        self.assertEqual(session.slider_config.init_val, 7)
        self.assertEqual(len(session.slider_config.categories_dict), 3)


class TestSliderSessionWithCallbacks(unittest.TestCase):
    """Test session behavior with registered callbacks."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = SliderConfig(
            name="test",
            min_val=1,
            max_val=5,
            init_val=3,
            step=0.1,
            marker_step=1,
            categories_dict={}
        )
        
        # Create stimulus list
        self.stimulus_file = os.path.join(self.temp_dir, "stimuli.txt")
        with open(self.stimulus_file, 'w') as f:
            f.write("stimulus1.wav\n")
            f.write("stimulus2.wav\n")
    
    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_session_finished_callback(self):
        """Test on_session_finished is called when all stimuli done."""
        session = SliderSession(
            slider_config=self.config,
            participant_id="VP001",
            stimulus_list_file=self.stimulus_file,
            output_dir=self.temp_dir
        )
        
        finished_callback = MagicMock()
        session.on_session_finished = finished_callback
        
        # Navigate through all stimuli
        session.next_stimulus()  # stimulus 2
        session.next_stimulus()  # done
        
        # Should have called callback
        finished_callback.assert_called_once()
    
    def test_stimulus_changed_callback(self):
        """Test on_stimulus_changed is called on next_stimulus."""
        session = SliderSession(
            slider_config=self.config,
            participant_id="VP001",
            stimulus_list_file=self.stimulus_file,
            output_dir=self.temp_dir
        )
        
        changed_callback = MagicMock()
        session.on_stimulus_changed = changed_callback
        
        # Move to next stimulus
        session.next_stimulus()
        
        # Should have called callback with new stimulus
        changed_callback.assert_called_once_with("stimulus2.wav")


if __name__ == '__main__':
    unittest.main()
