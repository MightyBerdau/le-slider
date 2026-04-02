"""
Unit tests for data I/O module (RatingRecorder, loading, summaries).
"""

import unittest
import os
import json
import tempfile
from datetime import datetime

from functions.data_io import (
    RatingRecorder,
    load_recording_from_json,
    load_all_recordings_from_dir,
    get_recording_summary,
)
from functions.config import SliderConfig


class TestRatingRecorder(unittest.TestCase):
    """Test RatingRecorder basic functionality."""
    
    def setUp(self):
        """Create test fixtures."""
        self.config = SliderConfig(
            name='listening_effort',
            min_val=1.0,
            max_val=14.0,
            init_val=7.0,
            step=1.0,
            marker_step=1.0,
            categories_dict={
                1.0: 'sehr leicht',
                7.0: 'mittel',
                14.0: 'sehr schwer',
            },
            language='de',
            slider_reversal=False,
            description='Listening effort test',
        )
    
    def test_init(self):
        """Test recorder initialization."""
        recorder = RatingRecorder(
            self.config,
            participant_id='VP01',
            stimulus_file='speech_01.wav',
            session_id='Session_A',
        )
        
        self.assertEqual(recorder.participant_id, 'VP01')
        self.assertEqual(recorder.stimulus_file, 'speech_01.wav')
        self.assertEqual(recorder.session_id, 'Session_A')
        self.assertEqual(recorder.frame_count, 0)
        self.assertEqual(len(recorder.recorded_frames), 0)
    
    def test_add_frame(self):
        """Test recording individual frames."""
        recorder = RatingRecorder(self.config, 'VP01', 'test.wav')
        
        # Test with device-accurate timestamps
        recorder.add_frame(5.0, timestamp_rel_sec=0.0)
        recorder.add_frame(6.0, timestamp_rel_sec=0.005)
        recorder.add_frame(7.0, timestamp_rel_sec=0.010)
        
        self.assertEqual(recorder.frame_count, 3)
        self.assertEqual(len(recorder.recorded_frames), 3)
        self.assertEqual(recorder.recorded_frames[0]['value'], 5.0)
        self.assertEqual(recorder.recorded_frames[0]['timestamp_rel_sec'], 0.0)
        self.assertEqual(recorder.recorded_frames[1]['value'], 6.0)
        self.assertEqual(recorder.recorded_frames[1]['timestamp_rel_sec'], 0.005)
        self.assertEqual(recorder.recorded_frames[2]['value'], 7.0)
        self.assertEqual(recorder.recorded_frames[2]['timestamp_rel_sec'], 0.010)
    
    def test_add_frame_with_raw_value(self):
        """Test adding frame (raw_value parameter deprecated, using value only)."""
        recorder = RatingRecorder(self.config, 'VP01', 'test.wav')
        
        # Now we only record value (simplified format)
        recorder.add_frame(value=12.0)
        
        frame = recorder.recorded_frames[0]
        self.assertEqual(frame['value'], 12.0)
        # raw_value field has been removed for simplicity
        self.assertNotIn('raw_value', frame)
    
    def test_frame_indexing(self):
        """Test that frames are indexed correctly."""
        recorder = RatingRecorder(self.config, 'VP01', 'test.wav')
        
        for i in range(5):
            recorder.add_frame(float(i))
        
        for i, frame in enumerate(recorder.recorded_frames):
            self.assertEqual(frame['frame'], i)
    
    def test_frame_timestamps(self):
        """Test that timestamps are recorded and increasing."""
        recorder = RatingRecorder(self.config, 'VP01', 'test.wav')
        
        recorder.add_frame(5.0)
        recorder.add_frame(6.0)
        
        # Timestamps should be increasing
        t1 = recorder.recorded_frames[0]['timestamp_rel_sec']
        t2 = recorder.recorded_frames[1]['timestamp_rel_sec']
        
        self.assertGreaterEqual(t2, t1)
        self.assertGreaterEqual(t1, 0.0)
    
    def test_set_audio_metadata(self):
        """Test setting audio playback metadata."""
        recorder = RatingRecorder(self.config, 'VP01', 'test.wav')
        
        recorder.set_audio_metadata(
            sample_rate=48000,
            blocksize=256,
            buffersize=4,
            duration_sec=10.5,
        )
        
        self.assertEqual(recorder.audio_metadata['sample_rate'], 48000)
        self.assertEqual(recorder.audio_metadata['blocksize'], 256)
        self.assertEqual(recorder.audio_metadata['duration_sec'], 10.5)
    
    def test_reset(self):
        """Test resetting recorder for next stimulus."""
        recorder = RatingRecorder(self.config, 'VP01', 'test.wav')
        
        recorder.add_frame(5.0)
        recorder.add_frame(6.0)
        
        self.assertEqual(recorder.frame_count, 2)
        
        recorder.reset()
        
        self.assertEqual(recorder.frame_count, 0)
        self.assertEqual(len(recorder.recorded_frames), 0)


class TestRatingRecorderExport(unittest.TestCase):
    """Test exporting recordings to JSON format."""
    
    def setUp(self):
        """Create test fixtures and temp directory."""
        self.config = SliderConfig(
            name='listening_effort',
            min_val=1.0,
            max_val=14.0,
            init_val=7.0,
            step=1.0,
            marker_step=1.0,
            categories_dict={1.0: 'easy', 14.0: 'hard'},
            language='en',
        )
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up temp files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_export_schema(self):
        """Test exporting to RatingRecordingSchema."""
        recorder = RatingRecorder(self.config, 'VP01', 'test.wav')
        recorder.set_audio_metadata(48000, 256, 4, 10.5)
        recorder.add_frame(5.0)
        recorder.add_frame(6.0)
        
        schema = recorder.export_schema()
        
        self.assertEqual(schema.participant_id, 'VP01')
        self.assertEqual(schema.stimulus_file, 'test.wav')
        self.assertEqual(len(schema.recordings), 2)
        self.assertEqual(schema.audio_settings['sample_rate'], 48000)
    
    def test_save_to_json(self):
        """Test saving recording to JSON file."""
        recorder = RatingRecorder(self.config, 'VP01', 'test.wav')
        recorder.set_audio_metadata(48000, 256, 4, 10.5)
        recorder.add_frame(5.0)
        recorder.add_frame(6.0)
        
        output_file = os.path.join(self.temp_dir, 'recording.json')
        recorder.save_to_json(output_file)
        
        self.assertTrue(os.path.exists(output_file))
        
        # Verify JSON is valid and has expected structure
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertEqual(data['participant_id'], 'VP01')
        self.assertEqual(data['stimulus_file'], 'test.wav')
        self.assertEqual(len(data['recordings']), 2)
    
    def test_save_creates_directory(self):
        """Test that save_to_json creates missing directories."""
        recorder = RatingRecorder(self.config, 'VP01', 'test.wav')
        recorder.add_frame(5.0)
        
        nested_path = os.path.join(self.temp_dir, 'nested', 'deep', 'recording.json')
        recorder.save_to_json(nested_path)
        
        self.assertTrue(os.path.exists(nested_path))


class TestLoadRecordings(unittest.TestCase):
    """Test loading recordings from JSON files."""
    
    def setUp(self):
        """Create test recordings."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a sample recording
        self.config = SliderConfig(
            name='listening_effort',
            min_val=1.0,
            max_val=14.0,
            init_val=7.0,
            step=1.0,
            marker_step=1.0,
            categories_dict={1.0: 'easy', 14.0: 'hard'},
            language='en',
        )
        
        recorder = RatingRecorder(self.config, 'VP01', 'test.wav')
        recorder.set_audio_metadata(48000, 256, 4, 10.5)
        recorder.add_frame(5.0)
        recorder.add_frame(6.0)
        recorder.add_frame(7.0)
        
        self.recording_file = os.path.join(self.temp_dir, 'recording.json')
        recorder.save_to_json(self.recording_file)
    
    def tearDown(self):
        """Clean up temp files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_load_recording_from_json(self):
        """Test loading a single recording from JSON."""
        schema = load_recording_from_json(self.recording_file)
        
        self.assertEqual(schema.participant_id, 'VP01')
        self.assertEqual(schema.stimulus_file, 'test.wav')
        self.assertEqual(len(schema.recordings), 3)
    
    def test_load_nonexistent_file(self):
        """Test error when loading nonexistent file."""
        with self.assertRaises(FileNotFoundError):
            load_recording_from_json('/nonexistent/path/file.json')
    
    def test_load_all_from_directory(self):
        """Test loading all JSON files from a directory."""
        # Create second recording
        recorder2 = RatingRecorder(self.config, 'VP02', 'test2.wav')
        recorder2.add_frame(8.0)
        recordings_file = os.path.join(self.temp_dir, 'recording2.json')
        recorder2.save_to_json(recordings_file)
        
        # Load all
        all_recordings = load_all_recordings_from_dir(self.temp_dir)
        
        self.assertEqual(len(all_recordings), 2)
        self.assertIn('recording.json', all_recordings)
        self.assertIn('recording2.json', all_recordings)
    
    def test_load_from_nonexistent_directory(self):
        """Test error when directory doesn't exist."""
        with self.assertRaises(FileNotFoundError):
            load_all_recordings_from_dir('/nonexistent/directory')
    
    def test_load_all_skips_invalid_json(self):
        """Test that invalid JSON files are skipped."""
        # Create invalid JSON file
        invalid_file = os.path.join(self.temp_dir, 'invalid.json')
        with open(invalid_file, 'w') as f:
            f.write('{ invalid json')
        
        # Should not raise; just skips invalid file
        recordings = load_all_recordings_from_dir(self.temp_dir)
        
        self.assertEqual(len(recordings), 1)  # Only the valid one


class TestRecordingSummary(unittest.TestCase):
    """Test summary statistics extraction."""
    
    def setUp(self):
        """Create test recording."""
        self.config = SliderConfig(
            name='listening_effort',
            min_val=1.0,
            max_val=14.0,
            init_val=7.0,
            step=1.0,
            marker_step=1.0,
            categories_dict={1.0: 'easy', 14.0: 'hard'},
            language='en',
        )
        
        recorder = RatingRecorder(self.config, 'VP01', 'test.wav')
        recorder.set_audio_metadata(48000, 256, 4, 10.5)
        for value in [5.0, 6.0, 7.0, 8.0, 9.0]:
            recorder.add_frame(value)
        
        self.schema = recorder.export_schema()
    
    def test_summary_statistics(self):
        """Test extracting summary statistics."""
        summary = get_recording_summary(self.schema)
        
        self.assertEqual(summary['frame_count'], 5)
        self.assertEqual(summary['mean_value'], 7.0)
        self.assertEqual(summary['min_value'], 5.0)
        self.assertEqual(summary['max_value'], 9.0)
        self.assertGreaterEqual(summary['duration_sec'], 0)
    
    def test_summary_empty_recording(self):
        """Test summary of empty recording."""
        empty_schema = self.schema.__class__(
            version='1.0',
            participant_id='VP01',
            session_id='test',
            stimulus_file='test.wav',
            timestamp_start='2024-01-01T00:00:00Z',
            timestamp_end='2024-01-01T00:00:01Z',
            slider_config={},
            audio_settings={},
            recordings=[],
        )
        
        summary = get_recording_summary(empty_schema)
        
        self.assertEqual(summary['frame_count'], 0)
        self.assertIsNone(summary['mean_value'])
        self.assertIsNone(summary['min_value'])


if __name__ == '__main__':
    unittest.main()
