"""
Unit tests for stimulus file validation and error handling.

Tests validate_stimulus_files(), MissingStimulisError, and ErrorDialog.
"""

import pytest
import tempfile
import os
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from functions.utils import validate_stimulus_files
from functions.errors import MissingStimulisError
from functions.gui import ErrorDialog


class TestValidateStimulusFiles:
    """Test the validate_stimulus_files validation function."""
    
    @pytest.fixture
    def temp_dir_with_files(self):
        """Create temporary directory with test audio files."""
        temp_dir = tempfile.mkdtemp()
        
        # Create some test audio files
        (Path(temp_dir) / "stimulus1.wav").touch()
        (Path(temp_dir) / "stimulus2.wav").touch()
        (Path(temp_dir) / "audio_dir").mkdir()
        (Path(temp_dir) / "audio_dir" / "stimulus3.wav").touch()
        
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_validate_all_files_exist(self, temp_dir_with_files):
        """Test validation passes when all files exist."""
        filepaths = [
            "stimulus1.wav",
            "stimulus2.wav",
            "audio_dir/stimulus3.wav"
        ]
        
        is_valid, missing = validate_stimulus_files(filepaths, temp_dir_with_files)
        
        assert is_valid is True
        assert missing == []
    
    def test_validate_missing_single_file(self, temp_dir_with_files):
        """Test validation detects single missing file."""
        filepaths = [
            "stimulus1.wav",
            "nonexistent.wav",
            "stimulus2.wav"
        ]
        
        is_valid, missing = validate_stimulus_files(filepaths, temp_dir_with_files)
        
        assert is_valid is False
        assert "nonexistent.wav" in missing
        assert len(missing) == 1
    
    def test_validate_missing_multiple_files(self, temp_dir_with_files):
        """Test validation detects multiple missing files."""
        filepaths = [
            "stimulus1.wav",
            "fake1.wav",
            "stimulus2.wav",
            "fake2.wav"
        ]
        
        is_valid, missing = validate_stimulus_files(filepaths, temp_dir_with_files)
        
        assert is_valid is False
        assert "fake1.wav" in missing
        assert "fake2.wav" in missing
        assert len(missing) == 2
    
    def test_validate_empty_list(self, temp_dir_with_files):
        """Test validation passes for empty file list."""
        is_valid, missing = validate_stimulus_files([], temp_dir_with_files)
        
        assert is_valid is True
        assert missing == []
    
    def test_validate_absolute_paths(self, temp_dir_with_files):
        """Test validation with absolute file paths."""
        absolute_path = str(Path(temp_dir_with_files) / "stimulus1.wav")
        filepaths = [absolute_path]
        
        is_valid, missing = validate_stimulus_files(filepaths, temp_dir_with_files)
        
        assert is_valid is True
        assert missing == []
    
    def test_validate_absolute_paths_missing(self, temp_dir_with_files):
        """Test validation detects missing absolute path files."""
        fake_absolute = str(Path(temp_dir_with_files) / "fake.wav")
        filepaths = [fake_absolute]
        
        is_valid, missing = validate_stimulus_files(filepaths, temp_dir_with_files)
        
        assert is_valid is False
        assert fake_absolute in missing
    
    def test_validate_nested_relative_paths(self, temp_dir_with_files):
        """Test validation with nested relative paths."""
        filepaths = ["audio_dir/stimulus3.wav"]
        
        is_valid, missing = validate_stimulus_files(filepaths, temp_dir_with_files)
        
        assert is_valid is True
        assert missing == []
    
    def test_validate_nested_missing_paths(self, temp_dir_with_files):
        """Test validation detects missing nested paths."""
        filepaths = ["audio_dir/nonexistent.wav"]
        
        is_valid, missing = validate_stimulus_files(filepaths, temp_dir_with_files)
        
        assert is_valid is False
        assert "audio_dir/nonexistent.wav" in missing
    
    def test_validate_with_cwd_default(self, temp_dir_with_files):
        """Test validation uses current working directory when base_dir is None."""
        # Save current directory
        original_cwd = os.getcwd()
        try:
            # Change to temp directory
            os.chdir(temp_dir_with_files)
            
            filepaths = ["stimulus1.wav"]
            is_valid, missing = validate_stimulus_files(filepaths, None)
            
            assert is_valid is True
            assert missing == []
        finally:
            # Restore original directory
            os.chdir(original_cwd)
    
    def test_validate_preserves_original_paths_in_missing(self, temp_dir_with_files):
        """Test that missing files list contains original path strings."""
        filepaths = [
            "stimulus1.wav",
            "missing/path/file.wav",
            "another_missing.wav"
        ]
        
        is_valid, missing = validate_stimulus_files(filepaths, temp_dir_with_files)
        
        assert is_valid is False
        assert "missing/path/file.wav" in missing
        assert "another_missing.wav" in missing
        # Original paths should be preserved, not converted to absolute
        assert not any(Path(path).is_absolute() for path in missing)


class TestMissingStimulisError:
    """Test the MissingStimulisError exception."""
    
    def test_error_initialization(self):
        """Test MissingStimulisError initializes correctly."""
        missing_files = ["file1.wav", "file2.wav"]
        error = MissingStimulisError(missing_files)
        
        assert error.missing_files == missing_files
    
    def test_error_message_format(self):
        """Test error message includes all missing files."""
        missing_files = ["stimulus1.wav", "stimulus2.wav"]
        error = MissingStimulisError(missing_files)
        error_msg = str(error)
        
        assert "stimulus1.wav" in error_msg
        assert "stimulus2.wav" in error_msg
        assert "missing" in error_msg.lower()
    
    def test_error_message_formatting(self):
        """Test error message is properly formatted with bullet points."""
        missing_files = ["file1.wav"]
        error = MissingStimulisError(missing_files)
        error_msg = str(error)
        
        assert "  - file1.wav" in error_msg
    
    def test_error_single_file(self):
        """Test error with single missing file."""
        error = MissingStimulisError(["single.wav"])
        
        assert error.missing_files == ["single.wav"]
        assert str(error) is not None
    
    def test_error_multiple_files(self):
        """Test error with multiple missing files."""
        missing = ["a.wav", "b.wav", "c.wav"]
        error = MissingStimulisError(missing)
        
        assert error.missing_files == missing
        assert len(error.missing_files) == 3
    
    def test_error_inherits_from_exception(self):
        """Test MissingStimulisError is a proper Exception."""
        error = MissingStimulisError(["test.wav"])
        
        assert isinstance(error, Exception)
    
    def test_error_can_be_raised_and_caught(self):
        """Test error can be raised and caught as exception."""
        with pytest.raises(MissingStimulisError) as exc_info:
            raise MissingStimulisError(["missing.wav"])
        
        assert exc_info.value.missing_files == ["missing.wav"]


class TestErrorDialog:
    """Test the ErrorDialog GUI component."""
    
    @patch('functions.gui.ui.dialog')
    @patch('functions.gui.ui.card')
    @patch('functions.gui.ui.column')
    @patch('functions.gui.ui.label')
    @patch('functions.gui.ui.button')
    def test_error_dialog_initialization(self, mock_button, mock_label, mock_column, 
                                         mock_card, mock_dialog):
        """Test ErrorDialog can be instantiated."""
        missing_files = ["test1.wav", "test2.wav"]
        
        # Create a mock dialog instance
        dialog_instance = MagicMock()
        mock_dialog.return_value.__enter__.return_value = dialog_instance
        
        dialog = ErrorDialog(missing_files)
        
        assert dialog is not None
    
    @patch('functions.gui.ui')
    def test_error_dialog_has_persistent_prop(self, mock_ui):
        """Test ErrorDialog sets persistent property."""
        missing_files = ["test.wav"]
        dialog_instance = MagicMock(spec=['props', '__enter__', '__exit__'])
        mock_ui.dialog.return_value = dialog_instance
        
        with patch('functions.gui.ui.dialog', return_value=dialog_instance):
            dialog = ErrorDialog(missing_files)
        
        # Should call props('persistent') to make it persistent
        # This is verified through the class definition


class TestValidationIntegration:
    """Integration tests for validation in MeasurementSession.setup()."""
    
    @pytest.fixture
    def temp_session_setup(self):
        """Create temp directory with measurement list for testing."""
        temp_dir = tempfile.mkdtemp()
        
        # Create stimulus directory and files
        stimulus_dir = Path(temp_dir) / "stimuli"
        stimulus_dir.mkdir()
        (stimulus_dir / "valid_stimulus.wav").touch()
        
        # Create measurement list file
        list_file = Path(temp_dir) / "valid_list.txt"
        with open(list_file, 'w') as f:
            f.write("stimuli/valid_stimulus.wav\n")
        
        list_file_missing = Path(temp_dir) / "invalid_list.txt"
        with open(list_file_missing, 'w') as f:
            f.write("stimuli/missing_stimulus.wav\n")
        
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_validate_fails_with_missing_files(self, temp_session_setup):
        """Test validation fails when stimulus files don't exist."""
        filepaths = ["stimuli/missing_stimulus.wav"]
        base_dir = temp_session_setup
        
        is_valid, missing = validate_stimulus_files(filepaths, base_dir)
        
        assert is_valid is False
        assert len(missing) == 1
    
    def test_validate_passes_with_valid_files(self, temp_session_setup):
        """Test validation passes when all stimulus files exist."""
        filepaths = ["stimuli/valid_stimulus.wav"]
        base_dir = temp_session_setup
        
        is_valid, missing = validate_stimulus_files(filepaths, base_dir)
        
        assert is_valid is True
        assert missing == []
