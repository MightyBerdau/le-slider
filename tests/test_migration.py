"""
Unit tests for NPZ-to-JSON migration tool.
"""

import unittest
import os
import json
import tempfile
from pathlib import Path

import numpy as np

from tools.migrate_npz_to_json import migrate_npz_file, migrate_directory


class TestNpzMigration(unittest.TestCase):
    """Test NPZ to JSON migration functionality."""
    
    def setUp(self):
        """Create test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.input_dir = os.path.join(self.temp_dir, 'input')
        self.output_dir = os.path.join(self.temp_dir, 'output')
        os.makedirs(self.input_dir)
        os.makedirs(self.output_dir)
    
    def tearDown(self):
        """Clean up temp files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _create_legacy_npz(self, filename: str, with_metadata: bool = True):
        """Helper: Create a legacy NPZ file for testing."""
        # Create sample listening effort data
        le_values = np.array([5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0], dtype=np.float32)
        frames = np.arange(len(le_values), dtype=np.int32)
        
        data_dict = {
            'LE_values': le_values,
            'frames': frames,
        }
        
        if with_metadata:
            data_dict.update({
                'stimulus_name': 'speech_01.wav',
                'participant_id': 'VP001',
                'session_id': 'Session_A',
                'sample_rate': 48000,
                'blocksize': 256,
                'buffersize': 4,
            })
        
        filepath = os.path.join(self.input_dir, filename)
        np.savez(filepath, **data_dict)
        return filepath
    
    def test_migrate_single_file_with_metadata(self):
        """Test migrating a single NPZ file with metadata."""
        npz_file = self._create_legacy_npz('recording_01.npz', with_metadata=True)
        
        result = migrate_npz_file(npz_file, self.output_dir, verbose=False)
        
        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))
        self.assertTrue(result.endswith('.json'))
        
        # Verify JSON content
        with open(result, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(data['participant_id'], 'VP001')
        self.assertEqual(data['stimulus_file'], 'speech_01.wav')
        self.assertEqual(len(data['recordings']), 7)
    
    def test_migrate_file_without_metadata(self):
        """Test migrating NPZ file with minimal metadata."""
        npz_file = self._create_legacy_npz('recording_02.npz', with_metadata=False)
        
        result = migrate_npz_file(npz_file, self.output_dir, verbose=False)
        
        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))
        
        # Verify uses defaults
        with open(result, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(data['participant_id'], 'Unknown')
        self.assertEqual(data['stimulus_file'], 'unknown.wav')
    
    def test_migrate_directory(self):
        """Test migrating multiple files from directory."""
        # Create multiple NPZ files
        self._create_legacy_npz('recording_01.npz')
        self._create_legacy_npz('recording_02.npz')
        self._create_legacy_npz('recording_03.npz')
        
        summary = migrate_directory(self.input_dir, self.output_dir, verbose=False)
        
        self.assertEqual(summary['total'], 3)
        self.assertEqual(summary['successful'], 3)
        self.assertEqual(summary['failed'], 0)
        
        # Check output files exist
        json_files = list(Path(self.output_dir).glob('*.json'))
        self.assertEqual(len(json_files), 3)
    
    def test_migrate_invalid_directory(self):
        """Test error handling for nonexistent directory."""
        with self.assertRaises(FileNotFoundError):
            migrate_directory('/nonexistent/directory', self.output_dir)
    
    def test_migrate_empty_directory(self):
        """Test migrating directory with no NPZ files."""
        summary = migrate_directory(self.input_dir, self.output_dir)
        
        self.assertEqual(summary['total'], 0)
        self.assertEqual(summary['successful'], 0)
    
    def test_migrate_npz_without_le_values(self):
        """Test handling NPZ file missing required 'LE_values' key."""
        # Create NPZ without LE_values
        data_dict = {
            'other_data': np.array([1, 2, 3]),
        }
        filepath = os.path.join(self.input_dir, 'invalid.npz')
        np.savez(filepath, **data_dict)
        
        result = migrate_npz_file(filepath, self.output_dir, verbose=False)
        
        self.assertIsNone(result)  # Should return None for invalid NPZ
    
    def test_recording_frame_structure(self):
        """Test that migrated frames have correct structure."""
        npz_file = self._create_legacy_npz('recording.npz')
        result = migrate_npz_file(npz_file, self.output_dir, verbose=False)
        
        with open(result, 'r') as f:
            data = json.load(f)
        
        # Verify frame structure
        for frame in data['recordings']:
            self.assertIn('frame', frame)
            self.assertIn('value', frame)
            self.assertIn('raw_value', frame)
            self.assertIn('timestamp_rel_sec', frame)
            
            # Verify types
            self.assertIsInstance(frame['frame'], int)
            self.assertIsInstance(frame['value'], float)
            self.assertIsInstance(frame['timestamp_rel_sec'], float)
    
    def test_migration_preserves_values(self):
        """Test that listening effort values are preserved during migration."""
        # Create NPZ with known values
        le_values = np.array([1.0, 5.5, 7.0, 14.0])
        data_dict = {
            'LE_values': le_values,
            'frames': np.arange(len(le_values), dtype=np.int32),
        }
        filepath = os.path.join(self.input_dir, 'test_values.npz')
        np.savez(filepath, **data_dict)
        
        result = migrate_npz_file(filepath, self.output_dir, verbose=False)
        
        with open(result, 'r') as f:
            data = json.load(f)
        
        migrated_values = [frame['value'] for frame in data['recordings']]
        
        np.testing.assert_array_almost_equal(migrated_values, le_values)


if __name__ == '__main__':
    unittest.main()
