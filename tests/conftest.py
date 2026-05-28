"""
Centralized pytest fixtures for test configuration and setup.

This module provides reusable fixtures for:
- Temporary directories (measurement lists, results, calibration)
- Temporary paths.yaml configuration files
- Monkeypatching of path configuration for tests
"""

import pytest
import tempfile
import shutil
import yaml
from pathlib import Path
from unittest.mock import patch


@pytest.fixture
def temp_measurement_lists_dir():
    """Create and cleanup temporary directory for measurement lists.
    
    Yields:
        Path: Temporary directory path
    """
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_results_dir():
    """Create and cleanup temporary directory for results.
    
    Yields:
        Path: Temporary directory path
    """
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_calib_dir():
    """Create and cleanup temporary directory for calibration files.
    
    Yields:
        Path: Temporary directory path
    """
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_paths_config(temp_measurement_lists_dir, temp_results_dir, temp_calib_dir):
    """Create temporary paths.yaml configuration file.
    
    This fixture creates a temporary YAML config file with paths pointing to
    temporary directories, ensuring test isolation without modifying the
    actual config/paths.yaml file.
    
    Args:
        temp_measurement_lists_dir: Fixture providing temp measurement_lists directory
        temp_results_dir: Fixture providing temp results directory
        temp_calib_dir: Fixture providing temp calibration directory
    
    Yields:
        Path: Path to temporary paths.yaml file
    """
    config_data = {
        'measurement_lists': str(temp_measurement_lists_dir),
        'results': str(temp_results_dir),
        'calibration_filepath': str(temp_calib_dir / 'calib_noise.wav')
    }
    
    # Create temp file in a way that ensures it can be deleted
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.yaml',
        delete=False,
        dir=tempfile.gettempdir()
    ) as config_file:
        yaml.dump(config_data, config_file)
        config_path = config_file.name
    
    yield Path(config_path)
    
    # Cleanup - ensure file is closed before deleting
    try:
        Path(config_path).unlink(missing_ok=True)
    except (PermissionError, OSError):
        # If file is still locked, it will be cleaned up by Windows temp cleanup
        pass


@pytest.fixture
def mock_paths_config(temp_paths_config, monkeypatch):
    """Monkeypatch PATHS_CONFIG_PATH to use temporary config file.
    
    This fixture ensures that all session instances load paths from a
    temporary config file instead of the default config/paths.yaml.
    
    Args:
        temp_paths_config: Fixture providing temporary paths.yaml
        monkeypatch: pytest's monkeypatch fixture
    
    Yields:
        Path: Path to temporary config file
    """
    # Import here to ensure it's available
    from functions.config import PATHS_CONFIG_PATH
    
    # Monkeypatch the config path to point to temporary file
    monkeypatch.setattr(
        'functions.config.PATHS_CONFIG_PATH',
        temp_paths_config
    )
    monkeypatch.setattr(
        'functions.session.PATHS_CONFIG_PATH',
        temp_paths_config
    )
    
    yield temp_paths_config


@pytest.fixture
def skip_calibration(monkeypatch):
    """Skip calibration validation in tests.
    
    This fixture patches the _load_calibration method to skip checking
    for calibration files, allowing tests to run without requiring
    actual calibration.json or calib_noise.wav files.
    
    Args:
        monkeypatch: pytest's monkeypatch fixture
    """
    def mock_load_calibration(self):
        """Mock calibration loading - just set default gains."""
        pass
    
    monkeypatch.setattr(
        'functions.session.MeasurementSession._load_calibration',
        mock_load_calibration
    )
    
    yield


@pytest.fixture
def temp_session_dir():
    """Create temporary directory for session tests.
    
    Yields:
        str: Path to temporary directory
    """
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)
