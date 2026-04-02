"""
Unit tests for the configuration system (functions/config.py).

Tests SliderConfig, SessionConfig, loaders, savers, and validation logic.
"""

import unittest
import tempfile
import os
from pathlib import Path

from functions.config import (
    SliderConfig,
    SessionConfig,
    load_slider_config_from_yaml,
    load_session_config_from_yaml,
    save_slider_config_to_yaml,
    save_session_config_to_yaml,
)


class TestSliderConfig(unittest.TestCase):
    """Test SliderConfig validation and properties."""
    
    def test_valid_slider_config(self):
        """Valid config should not raise."""
        config = SliderConfig(
            name="test_slider",
            min_val=1,
            max_val=14,
            init_val=7,
            step=0.1,
            marker_step=1,
            categories_dict={1: "Low", 14: "High"},
            language="de",
        )
        config.validate()  # Should not raise
    
    def test_init_val_out_of_range(self):
        """init_val outside [min_val, max_val] should raise."""
        config = SliderConfig(
            name="test",
            min_val=1,
            max_val=10,
            init_val=15,  # Out of range
            step=0.1,
            marker_step=1,
            categories_dict={1: "Low"},
        )
        with self.assertRaises(ValueError):
            config.validate()
    
    def test_min_max_reversed(self):
        """min_val >= max_val should raise."""
        config = SliderConfig(
            name="test",
            min_val=10,
            max_val=5,  # Reversed
            init_val=7,
            step=0.1,
            marker_step=1,
            categories_dict={5: "Low", 10: "High"},
        )
        with self.assertRaises(ValueError):
            config.validate()
    
    def test_category_out_of_range(self):
        """Category value outside [min_val, max_val] should raise."""
        config = SliderConfig(
            name="test",
            min_val=1,
            max_val=10,
            init_val=5,
            step=0.1,
            marker_step=1,
            categories_dict={1: "Low", 15: "Way too high"},  # 15 out of range
        )
        with self.assertRaises(ValueError):
            config.validate()
    
    def test_invalid_language(self):
        """Unsupported language should raise."""
        config = SliderConfig(
            name="test",
            min_val=1,
            max_val=10,
            init_val=5,
            step=0.1,
            marker_step=1,
            categories_dict={1: "Low"},
            language="fr",  # Not supported yet
        )
        with self.assertRaises(ValueError):
            config.validate()
    
    def test_negative_step(self):
        """Negative step should raise."""
        config = SliderConfig(
            name="test",
            min_val=1,
            max_val=10,
            init_val=5,
            step=-0.1,  # Negative
            marker_step=1,
            categories_dict={1: "Low"},
        )
        with self.assertRaises(ValueError):
            config.validate()


class TestSessionConfig(unittest.TestCase):
    """Test SessionConfig validation."""
    
    def test_valid_session_config(self):
        """Valid session config should not raise."""
        config = SessionConfig(
            participant_id="VP01",
            measurement_list_path="/path/to/list.txt",
            blocksize=512,
            buffersize=20,
        )
        config.validate()  # Should not raise
    
    def test_empty_participant_id(self):
        """Empty participant_id should raise."""
        config = SessionConfig(
            participant_id="",
            measurement_list_path="/path/to/list.txt",
        )
        with self.assertRaises(ValueError):
            config.validate()
    
    def test_negative_blocksize(self):
        """Negative blocksize should raise."""
        config = SessionConfig(
            participant_id="VP01",
            measurement_list_path="/path/to/list.txt",
            blocksize=-512,
        )
        with self.assertRaises(ValueError):
            config.validate()


class TestSliderConfigYAML(unittest.TestCase):
    """Test loading and saving slider configs to YAML."""
    
    def setUp(self):
        """Create temporary directory for test files."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_save_and_load_slider_config(self):
        """Save config to YAML, load it back, should match."""
        config = SliderConfig(
            name="listening_effort",
            min_val=1,
            max_val=14,
            init_val=7,
            step=0.1,
            marker_step=1,
            categories_dict={1.0: "mühelos", 14.0: "extrem"},
            color_range_hsv={
                'hue_min': 0.03,
                'hue_max': 0.3,
                'saturation': 0.8,
                'value': 0.9,
            },
            language="de",
            description="Test config",
        )
        
        filepath = os.path.join(self.temp_dir, "test_config.yaml")
        save_slider_config_to_yaml(config, filepath)
        
        # Verify file exists and is readable
        self.assertTrue(os.path.exists(filepath))
        
        # Load and compare
        loaded_config = load_slider_config_from_yaml(filepath)
        self.assertEqual(config.name, loaded_config.name)
        self.assertEqual(config.min_val, loaded_config.min_val)
        self.assertEqual(config.max_val, loaded_config.max_val)
        self.assertEqual(config.init_val, loaded_config.init_val)
        self.assertEqual(config.categories_dict, loaded_config.categories_dict)
        self.assertEqual(config.language, loaded_config.language)
    
    def test_load_invalid_yaml(self):
        """Loading malformed YAML should raise."""
        filepath = os.path.join(self.temp_dir, "bad.yaml")
        with open(filepath, 'w') as f:
            f.write("{ invalid yaml [")
        
        with self.assertRaises(Exception):  # YAML error
            load_slider_config_from_yaml(filepath)
    
    def test_load_missing_file(self):
        """Loading non-existent file should raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            load_slider_config_from_yaml("/nonexistent/path.yaml")


class TestSessionConfigYAML(unittest.TestCase):
    """Test loading and saving session configs to YAML."""
    
    def setUp(self):
        """Create temporary directory for test files."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_save_and_load_session_config(self):
        """Save session config to YAML, load it back, should match."""
        config = SessionConfig(
            participant_id="VP01",
            measurement_list_path="measurement/Lists/List1.txt",
            device_id=2,
            blocksize=512,
            buffersize=20,
            language="de",
        )
        
        filepath = os.path.join(self.temp_dir, "test_session.yaml")
        save_session_config_to_yaml(config, filepath)
        
        loaded_config = load_session_config_from_yaml(filepath)
        self.assertEqual(config.participant_id, loaded_config.participant_id)
        self.assertEqual(config.measurement_list_path, loaded_config.measurement_list_path)
        self.assertEqual(config.device_id, loaded_config.device_id)
        self.assertEqual(config.blocksize, loaded_config.blocksize)


if __name__ == '__main__':
    unittest.main()
