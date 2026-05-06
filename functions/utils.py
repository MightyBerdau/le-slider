from datetime import datetime
import os

def get_current_time():
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
        base_dir = os.getcwd()
    
    missing_files = []
    
    for filepath in filepath_list:
        # Check if file exists as-is (for absolute paths or paths relative to cwd)
        if os.path.isabs(filepath):
            full_path = filepath
        else:
            full_path = os.path.join(base_dir, filepath)
        
        if not os.path.exists(full_path):
            missing_files.append(filepath)
    
    is_valid = len(missing_files) == 0
    return is_valid, missing_files