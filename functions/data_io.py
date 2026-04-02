"""
Data I/O utilities for rating recordings.

Provides RatingRecorder class for recording slider values during playback
and exporting to JSON, and utilities for loading saved data.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from .data_schema import RatingRecordingSchema, create_recording_schema
from .config import SliderConfig

logger = logging.getLogger(__name__)


class RatingRecorder:
    """Records rating values during audio playback and exports to JSON.
    
    Wraps a slider and records its values frame-by-frame as audio plays.
    Accumulates metadata and exports to JSON in the schema format.
    """
    
    def __init__(
        self,
        slider_config: SliderConfig,
        participant_id: str,
        stimulus_file: str,
        session_id: Optional[str] = None,
    ):
        """Initialize recorder with slider configuration.
        
        Args:
            slider_config: SliderConfig defining the scale
            participant_id: Participant identifier
            stimulus_file: Name of stimulus being rated (filename only)
            session_id: Optional session ID (auto-generated if not provided)
        """
        self.slider_config = slider_config
        self.participant_id = participant_id
        self.stimulus_file = stimulus_file
        self.session_id = session_id or datetime.utcnow().isoformat() + "Z"
        
        self.recorded_frames: list = []
        self.frame_count = 0
        self.audio_metadata: Dict[str, Any] = {}
        self.timestamp_start = datetime.utcnow()
    
    def set_audio_metadata(
        self,
        sample_rate: int,
        blocksize: int,
        buffersize: int,
        duration_sec: float,
    ):
        """Set audio playback metadata.
        
        Args:
            sample_rate: Sampling frequency in Hz
            blocksize: Samples per callback
            buffersize: Number of blocks in buffer
            duration_sec: Total stimulus duration
        """
        self.audio_metadata = {
            'sample_rate': sample_rate,
            'blocksize': blocksize,
            'buffersize': buffersize,
            'duration_sec': duration_sec,
        }
    
    def add_frame(self, value: float, timestamp_rel_sec: Optional[float] = None):
        """Record a single rating value.
        
        Called once per audio callback (frame) with device-accurate timing.
        
        Args:
            value: Rating value from slider
            timestamp_rel_sec: Time relative to playback start (from device, optional for backward compat)
        """
        # Use device time if provided, otherwise calculate from wall-clock
        if timestamp_rel_sec is None:
            elapsed = (datetime.utcnow() - self.timestamp_start).total_seconds()
        else:
            elapsed = timestamp_rel_sec
        
        frame_data = {
            'frame': self.frame_count,
            'value': value,
            'timestamp_rel_sec': elapsed,
        }
        
        self.recorded_frames.append(frame_data)
        self.frame_count += 1
    
    def export_schema(self) -> RatingRecordingSchema:
        """Export recorded data as RatingRecordingSchema.
        
        Returns:
            RatingRecordingSchema with all recorded data
        """
        config_dict = {
            'name': self.slider_config.name,
            'min_val': self.slider_config.min_val,
            'max_val': self.slider_config.max_val,
            'init_val': self.slider_config.init_val,
            'step': self.slider_config.step,
            'marker_step': self.slider_config.marker_step,
            'categories_dict': self.slider_config.categories_dict,
            'language': self.slider_config.language,
            'description': self.slider_config.description,
        }
        
        return create_recording_schema(
            participant_id=self.participant_id,
            stimulus_file=self.stimulus_file,
            slider_config=config_dict,
            audio_settings=self.audio_metadata,
            recordings=self.recorded_frames,
            session_id=self.session_id,
        )
    
    def save_to_json(self, filepath: str, indent: int = 2):
        """Save recorded data to JSON file.
        
        Args:
            filepath: Output file path (should end with .json)
            indent: JSON indentation level (2 or 4 recommended)
            
        Raises:
            OSError: If file cannot be written
        """
        logger.info(f"Saving recording to JSON: {filepath}")
        
        try:
            schema = self.export_schema()
            json_str = schema.to_json_string(indent=indent)
            
            # Create directory if needed
            os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json_str)
            
            logger.info(f"Recording saved successfully ({self.frame_count} frames)")
        except OSError as e:
            logger.error(f"Failed to save recording: {e}")
            raise
    
    def reset(self):
        """Reset recorder for next stimulus."""
        self.recorded_frames = []
        self.frame_count = 0
        self.timestamp_start = datetime.utcnow()


def load_recording_from_json(filepath: str) -> RatingRecordingSchema:
    """Load a saved recording from JSON file.
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        RatingRecordingSchema with recorded data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is malformed
        ValueError: If schema is invalid
    """
    return RatingRecordingSchema.from_json_file(filepath)


def load_all_recordings_from_dir(directory: str) -> Dict[str, RatingRecordingSchema]:
    """Load all JSON recording files from a directory.
    
    Args:
        directory: Directory containing .json files
        
    Returns:
        Dictionary mapping filename → RatingRecordingSchema
        
    Raises:
        FileNotFoundError: If directory doesn't exist
    """
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    recordings = {}
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            filepath = os.path.join(directory, filename)
            try:
                schema = load_recording_from_json(filepath)
                recordings[filename] = schema
            except (json.JSONDecodeError, ValueError) as e:
                # Log and skip invalid files
                print(f"Warning: Could not load {filename}: {e}")
                continue
    
    return recordings


def get_recording_summary(schema: RatingRecordingSchema) -> Dict[str, Any]:
    """Extract summary statistics from a recording schema.
    
    Args:
        schema: RatingRecordingSchema instance
        
    Returns:
        Dictionary with summary stats (mean, min, max, frame_count, etc.)
    """
    if not schema.recordings:
        return {
            'frame_count': 0,
            'mean_value': None,
            'min_value': None,
            'max_value': None,
            'duration_sec': 0,
        }
    
    values = [f['value'] for f in schema.recordings]
    
    return {
        'frame_count': len(schema.recordings),
        'mean_value': sum(values) / len(values),
        'min_value': min(values),
        'max_value': max(values),
        'duration_sec': schema.recordings[-1]['timestamp_rel_sec'] if schema.recordings else 0,
    }
