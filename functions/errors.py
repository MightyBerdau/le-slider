class MissingStimulisError(Exception):
    """Exception raised when stimulus files referenced in measurement list are missing.
    
    Attributes:
        missing_files: List of missing stimulus file paths
    """
    def __init__(self, missing_files: list[str]) -> None:
        """Initialize exception with list of missing stimulus files.
        
        Args:
            missing_files: List of stimulus file paths that were not found
        """
        self.missing_files = missing_files
        files_str = "\n".join([f"  - {f}" for f in missing_files])
        super().__init__(f"The following stimulus files are missing:\n{files_str}")
