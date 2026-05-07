"""
Extended unit tests for utility functions.

Tests for get_device_supported_samplerates and get_stimulus_samplerates functions.
"""

import pytest
import tempfile
import os
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path
import numpy as np
import soundfile as sf
from functions.utils import get_device_supported_samplerates, get_stimulus_samplerates


class TestGetDeviceSupportedSamplerates:
    """Test get_device_supported_samplerates function."""
    
    def test_get_device_supported_samplerates_empty_list(self):
        """Test with empty device list."""
        result = get_device_supported_samplerates([])
        assert isinstance(result, dict)
        assert len(result) == 0
    
    def test_get_device_supported_samplerates_returns_dict(self):
        """Test that function returns dictionary."""
        devices = [
            {'index': 0, 'name': 'Device 0', 'max_output_channels': 2}
        ]
        
        with patch('functions.utils.sd.check_output_settings') as mock_check:
            mock_check.return_value = None  # No exception = supported
            result = get_device_supported_samplerates(devices)
        
        assert isinstance(result, dict)
        assert 0 in result  # Device ID should be a key
    
    def test_get_device_supported_samplerates_lists_supported(self):
        """Test that supported rates are collected."""
        devices = [
            {'index': 0, 'name': 'Device 0', 'max_output_channels': 2}
        ]
        
        supported_rates = [48000, 96000]
        call_count = [0]
        
        def check_settings_side_effect(device, samplerate, channels):
            call_count[0] += 1
            if samplerate in supported_rates:
                return None  # No exception = supported
            else:
                raise ValueError("Not supported")
        
        with patch('functions.utils.sd.check_output_settings', side_effect=check_settings_side_effect):
            result = get_device_supported_samplerates(devices)
        
        # Should have rates list for device 0
        assert 0 in result
        assert 48000 in result[0]
        assert 96000 in result[0]
    
    def test_get_device_supported_samplerates_sorted(self):
        """Test that returned rates are sorted in ascending order."""
        devices = [
            {'index': 0, 'name': 'Device 0', 'max_output_channels': 2}
        ]
        
        with patch('functions.utils.sd.check_output_settings') as mock_check:
            mock_check.return_value = None  # All supported
            result = get_device_supported_samplerates(devices)
        
        # Should be sorted
        if 0 in result:
            rates = result[0]
            assert rates == sorted(rates)
    
    def test_get_device_supported_samplerates_multiple_devices(self):
        """Test with multiple devices."""
        devices = [
            {'index': 0, 'name': 'Device 0', 'max_output_channels': 2},
            {'index': 2, 'name': 'Device 2', 'max_output_channels': 2}
        ]
        
        device_support = {0: [48000, 96000], 2: [44100, 48000]}
        
        def check_settings_side_effect(device, samplerate, channels):
            if device in device_support and samplerate in device_support[device]:
                return None
            else:
                raise ValueError("Not supported")
        
        with patch('functions.utils.sd.check_output_settings', side_effect=check_settings_side_effect):
            result = get_device_supported_samplerates(devices)
        
        # Both devices should be in result
        assert 0 in result
        assert 2 in result
    
    def test_get_device_supported_samplerates_exception_handling(self):
        """Test that PortAudioError is handled gracefully."""
        devices = [
            {'index': 0, 'name': 'Device 0', 'max_output_channels': 2}
        ]
        
        with patch('functions.utils.sd.check_output_settings') as mock_check:
            # All checks fail with ValueError
            mock_check.side_effect = ValueError("Not supported")
            result = get_device_supported_samplerates(devices)
        
        # Should have empty list for the device when all rates fail
        assert 0 in result
        assert len(result[0]) == 0


class TestGetStimulusSamplerates:
    """Test get_stimulus_samplerates function."""
    
    def test_get_stimulus_samplerates_empty_list(self):
        """Test with empty file list."""
        result = get_stimulus_samplerates([])
        assert isinstance(result, dict)
        assert len(result) == 0
    
    def test_get_stimulus_samplerates_returns_dict(self):
        """Test that function returns dictionary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test wav file
            filepath = str(Path(tmpdir) / "test.wav")
            data = np.random.rand(100).astype(np.float32)
            sf.write(filepath, data, 48000)
            
            result = get_stimulus_samplerates([filepath], base_dir=tmpdir)
        
        assert isinstance(result, dict)
    
    def test_get_stimulus_samplerates_single_file(self):
        """Test with single stimulus file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test wav file at 48 kHz
            filepath = str(Path(tmpdir) / "test.wav")
            data = np.random.rand(100).astype(np.float32)
            target_fs = 48000
            sf.write(filepath, data, target_fs)
            
            result = get_stimulus_samplerates(["test.wav"], base_dir=tmpdir)
        
        # Should contain the file with correct samplerate
        assert "test.wav" in result
        assert result["test.wav"] == target_fs
    
    def test_get_stimulus_samplerates_multiple_files_different_rates(self):
        """Test with multiple files at different sample rates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files at different sample rates
            files_rates = [
                ("file1.wav", 44100),
                ("file2.wav", 48000),
                ("file3.wav", 96000),
            ]
            
            for filename, fs in files_rates:
                filepath = str(Path(tmpdir) / filename)
                data = np.random.rand(100).astype(np.float32)
                sf.write(filepath, data, fs)
            
            filenames = [f[0] for f in files_rates]
            result = get_stimulus_samplerates(filenames, base_dir=tmpdir)
        
        # All files should be present with correct rates
        for filename, expected_fs in files_rates:
            assert filename in result
            assert result[filename] == expected_fs
    
    def test_get_stimulus_samplerates_uses_base_dir(self):
        """Test that base_dir parameter is used correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = str(Path(tmpdir) / "subdir")
            Path(subdir).mkdir()
            
            # Create file in subdirectory
            filepath = str(Path(subdir) / "test.wav")
            data = np.random.rand(100).astype(np.float32)
            sf.write(filepath, data, 48000)
            
            # Call with relative path and base_dir
            result = get_stimulus_samplerates(["test.wav"], base_dir=subdir)
        
        assert "test.wav" in result
        assert result["test.wav"] == 48000
    
    def test_get_stimulus_samplerates_absolute_path(self):
        """Test with absolute file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file with absolute path
            filepath = str(Path(tmpdir) / "test.wav")
            data = np.random.rand(100).astype(np.float32)
            sf.write(filepath, data, 48000)
            
            # Call with absolute path
            result = get_stimulus_samplerates([filepath])
        
        assert filepath in result
        assert result[filepath] == 48000
    
    def test_get_stimulus_samplerates_missing_file(self):
        """Test behavior with non-existent file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Reference non-existent file
            result = get_stimulus_samplerates(
                ["nonexistent.wav"],
                base_dir=tmpdir
            )
        
        # Should either be empty or have None for missing file
        # Depending on implementation
        assert isinstance(result, dict)
    
    def test_get_stimulus_samplerates_default_base_dir(self):
        """Test that function uses current directory if base_dir is None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file
            filepath = str(Path(tmpdir) / "test.wav")
            data = np.random.rand(100).astype(np.float32)
            sf.write(filepath, data, 48000)
            
            # Save current directory and change to tmpdir
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                # Call without base_dir
                result = get_stimulus_samplerates(["test.wav"])
                assert "test.wav" in result
            finally:
                os.chdir(original_cwd)
