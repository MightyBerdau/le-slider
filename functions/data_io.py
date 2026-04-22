from dataclasses import dataclass, asdict, field
import json
import os
from typing import Dict, Any

@dataclass
class RatingRecordingSchema:
    session_id: str = ""
    participant_id: str = ""
    stimulus_path: str = ""
    stimulus_list: str = ""
    stimulus_start: str = ""
    stimulus_end: str = ""
    slider_config: Dict[str, Any] = field(default_factory=dict)
    ratings: list = field(default_factory=list)
    time_stamps: list = field(default_factory=list)

    def to_json_dict(self) -> Dict[str, Any]:
            """Convert schema to JSON-serializable dictionary."""
            return asdict(self)
        
    def to_json_string(self, indent: int = 2) -> str:
        """Convert schema to formatted JSON string."""
        return json.dumps(self.to_json_dict(), indent=indent, ensure_ascii=False)

    def to_json_file(self, filepath: str, indent: int = 2):
        """Save schema to JSON file.
        
        Args:
            filepath: Path to output JSON file
            indent: JSON indentation level
        """
        # TODO overwrite prevention
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
        """
        return RatingRecordingSchema(
            participant_id=data['participant_id'],
            session_id=data.get('session_id', ''),
            stimulus_path=data['stimulus_path'],
            stimulus_list=data['stimulus_list'],
            stimulus_start=data.get('stimulus_start', ''),
            stimulus_end=data.get('stimulus_end', ''),
            slider_config=data.get('slider_config', {}),
            ratings=data.get('ratings', []),
            time_stamps=data.get('time_stamps', []),
        )
    
    @staticmethod
    def from_json_file(filepath: str) -> 'RatingRecordingSchema':
        """Load schema from JSON file.
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            RatingRecordingSchema instance
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return RatingRecordingSchema.from_json_dict(data)