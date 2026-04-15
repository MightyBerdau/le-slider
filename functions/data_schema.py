"""
Data schema and validation for rating recordings.

Defines the JSON schema for saving participant ratings, stimulus metadata,
and session information in a FAIR-compliant format.
"""

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json


@dataclass
class RatingRecordingSchema:
    """Complete schema for a rating recording session.
    
    Represents all data saved after a participant rates one stimulus.
    Includes slider configuration, participant info, and recorded values.
    
    Attributes:
        version: Schema version string (e.g., "1.0")
        participant_id: Unique participant identifier
        session_id: Unique session identifier
        stimulus_file: Filename of the audio stimulus
        timestamp_start: ISO 8601 start time (UTC)
        timestamp_end: ISO 8601 end time (UTC)
        slider_config: Dict with slider metadata
        audio_settings: AudioMetadata for the recording
        recordings: List of RecordingFrame dicts
    """
    version: str = "1.0"
    participant_id: str = ""
    session_id: str = ""
    stimulus_file: str = ""
    timestamp_start: str = ""
    timestamp_end: str = ""
    slider_config: Dict[str, Any] = field(default_factory=dict)
    audio_settings: Dict[str, Any] = field(default_factory=dict)
    recordings: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_json_dict(self) -> Dict[str, Any]:
        """Convert schema to JSON-serializable dictionary."""
        return asdict(self)
    
    def to_json_string(self, indent: int = 2) -> str:
        """Convert schema to formatted JSON string."""
        return json.dumps(self.to_json_dict(), indent=indent)
    
    def to_json_file(self, filepath: str, indent: int = 2):
        """Save schema to JSON file.
        
        Args:
            filepath: Path to output JSON file
            indent: JSON indentation level
        """
        import os
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json_string(indent=indent))
    
    @staticmethod
    def from_json_dict(data: Dict[str, Any]) -> 'RatingRecordingSchema':
        """Create schema instance from JSON dict.
        
        Args:
            data: Dictionary with schema fields
            
        Returns:
            RatingRecordingSchema instance
            
        Raises:
            ValueError: If schema version incompatible or required fields missing
        """
        # Validate version
        version = data.get('version', '1.0')
        if version != '1.0':
            raise ValueError(f"Unsupported schema version: {version}")
        
        # Validate required fields
        required = ['participant_id', 'stimulus_file', 'recordings']
        for field_name in required:
            if field_name not in data:
                raise ValueError(f"Missing required field: {field_name}")
        
        return RatingRecordingSchema(
            version=version,
            participant_id=data['participant_id'],
            session_id=data.get('session_id', ''),
            stimulus_file=data['stimulus_file'],
            timestamp_start=data.get('timestamp_start', ''),
            timestamp_end=data.get('timestamp_end', ''),
            slider_config=data.get('slider_config', {}),
            audio_settings=data.get('audio_settings', {}),
            recordings=data.get('recordings', []),
        )
    
    @staticmethod
    def from_json_file(filepath: str) -> 'RatingRecordingSchema':
        """Load schema from JSON file.
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            RatingRecordingSchema instance
            
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If JSON is malformed
            ValueError: If schema is invalid
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return RatingRecordingSchema.from_json_dict(data)


def create_recording_schema(
    participant_id: str,
    stimulus_file: str,
    slider_config: Dict[str, Any],
    audio_settings: Dict[str, Any],
    recordings: List[Dict[str, Any]],
    session_id: Optional[str] = None,
) -> RatingRecordingSchema:
    """Create a new recording schema instance.
    
    Convenience function for creating populated schema objects.
    
    Args:
        participant_id: Participant ID
        stimulus_file: Stimulus filename
        slider_config: Slider configuration dict
        audio_settings: Audio metadata dict
        recordings: List of recording frame dicts
        session_id: Optional session ID (defaults to timestamp)
        
    Returns:
        RatingRecordingSchema instance
    """
    if session_id is None:
        session_id = datetime.utcnow().isoformat() + "Z"
    
    return RatingRecordingSchema(
        version="1.0",
        participant_id=participant_id,
        session_id=session_id,
        stimulus_file=stimulus_file,
        timestamp_start=datetime.utcnow().isoformat() + "Z",
        timestamp_end=datetime.utcnow().isoformat() + "Z",
        slider_config=slider_config,
        audio_settings=audio_settings,
        recordings=recordings,
    )
