from datetime import datetime
import os
from pathlib import Path
import sounddevice as sd
import soundfile as sf

def get_current_time() -> str:
    """Get the current time in ISO format with timezone.
    
    Returns:
        Current datetime as ISO format string with timezone information
    """
    return datetime.now().astimezone().isoformat()

def validate_stimulus_files(filepath_list: list[str], base_dir: str = None) -> tuple[bool, list[str]]:
    """Validate that all stimulus files in the list exist.
    
    Args:
        filepath_list: List of stimulus file paths (absolute or relative)
        base_dir: Base directory for resolving relative paths. If None, uses current working directory.
        
    Returns:
        Tuple of (is_valid: bool, missing_files: list[str]) where:
        - is_valid: True if all files exist, False otherwise
        - missing_files: List of missing file paths
    """
    if base_dir is None:
        base_dir = str(Path.cwd())
    
    missing_files = []
    
    for filepath in filepath_list:
        # Check if file exists as-is (for absolute paths or paths relative to cwd)
        if Path(filepath).is_absolute():
            full_path = filepath
        else:
            full_path = str(Path(base_dir) / filepath)
        
        if not Path(full_path).exists():
            missing_files.append(filepath)
    
    is_valid = len(missing_files) == 0
    return is_valid, missing_files


def get_device_supported_samplerates(device_list) -> dict:
    """Query supported sampling rates for each device.
    
    Uses sd.check_output_settings() to efficiently test which sampling rates
    are supported by each device without opening actual audio streams.
    
    Args:
        device_list: List of sounddevice device dictionaries (typically with max_output_channels >= 2)
        
    Returns:
        Dictionary mapping device_id to list of supported sampling rates:
        {device_id: [fs1, fs2, ...], device_id2: [fs1, ...], ...}
        Rates are sorted in ascending order.
    """
    common_fs_to_test = [8000, 11025, 16000, 22050, 44100, 48000, 88200, 96000, 176400, 192000]
    device_supported = {}
    
    for device in device_list:
        device_id = device['index']
        supported = []
        
        for fs in common_fs_to_test:
            try:
                # Check if this fs is supported without actually opening a stream
                sd.check_output_settings(device=device_id, samplerate=fs, channels=2)
                supported.append(fs)
            except (sd.PortAudioError, ValueError):
                # This fs is not supported by this device
                continue
        
        device_supported[device_id] = sorted(supported)
    
    return device_supported


def get_stimulus_samplerates(filepath_list: list[str], base_dir: str = None) -> dict:
    """Get sampling rates for all stimulus files.
    
    Args:
        filepath_list: List of stimulus file paths (absolute or relative)
        base_dir: Base directory for resolving relative paths. If None, uses current working directory.
        
    Returns:
        Dictionary mapping filepath to sampling rate:
        {filepath: fs_value, ...}
    """
    if base_dir is None:
        base_dir = str(Path.cwd())
    
    stimulus_fs = {}
    
    for filepath in filepath_list:
        # Resolve full path
        if Path(filepath).is_absolute():
            full_path = filepath
        else:
            full_path = str(Path(base_dir) / filepath)
        
        try:
            info = sf.info(full_path)
            stimulus_fs[filepath] = info.samplerate
        except Exception as e:
            # If we can't read the file, store None (will be caught later in validation)
            stimulus_fs[filepath] = None
    
    return stimulus_fs