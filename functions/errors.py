class MissingStimulisError(Exception):
    """Exception raised when stimulus files referenced in measurement list are missing."""
    def __init__(self, missing_files: list[str]) -> None:
        self.missing_files = missing_files
        files_str = "\n".join([f"  - {f}" for f in missing_files])
        super().__init__(f"The following stimulus files are missing:\n{files_str}")


class MissingCalibrationFileError(Exception):
    """Exception raised when no calibration file exists at the expected path."""
    def __init__(self) -> None:
        super().__init__(
            "No calibration file found. Please run calibrate.py before starting a measurement."
        )


class MissingCalibrationSignalError(Exception):
    """Exception raised when no .wav file is found in the calib/ directory."""
    def __init__(self, calib_dir: str) -> None:
        super().__init__(
            f"No .wav calibration signal found in '{calib_dir}'. "
            "Please place a calibration signal (e.g. SSN.wav) in that directory."
        )