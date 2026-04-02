"""
Configuration system for rating sliders and recording sessions.

Provides dataclasses and loaders for slider configuration, session settings,
and validation logic to ensure consistency across different psychoacoustic measures.
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Optional
import json
import yaml
import logging

logger = logging.getLogger(__name__)


@dataclass
class SliderConfig:
    """Configuration for a single rating slider.
    
    Defines the scale, categories, visual feedback, and language for a slider
    that measures a specific psychoacoustic percept (e.g., listening effort,
    speech quality, noisiness).
    
    Attributes:
        name: Unique identifier for this slider type (e.g., "listening_effort")
        min_val: Minimum slider value (inclusive)
        max_val: Maximum slider value (inclusive)
        init_val: Initial position on slider
        step: Minimum step size between values
        marker_step: Distance between marker lines on slider
        categories_dict: Mapping {value: label} for category descriptions.
                        Should only include values where labels exist.
        color_range_hsv: Tuple (hue_min, hue_max) for colormap normalization.
                        E.g., (0.03, 0.3) for green→red; (0.6, 0.0) for blue→red
        language: Language code for categories ('de' or 'en')
        slider_reversal: If True, visual slider runs backward (max at bottom)
        description: Human-readable description of what this slider measures
    """
    name: str
    min_val: float
    max_val: float
    init_val: float
    step: float
    marker_step: float
    categories_dict: Dict[float, str]
    better_at_high: bool = True  # True: higher values are better (green at max); False: lower values are better (green at min)
    color_range_hsv: Dict[str, float] = field(default_factory=lambda: {
        'hue_min': 0.03,
        'hue_max': 0.3,
        'saturation': 0.8,
        'value': 0.9,
    })
    language: str = "de"
    slider_reversal: bool = False
    description: str = ""
    
    def validate(self):
        """Validate config consistency. Raises ValueError if invalid."""
        if self.min_val >= self.max_val:
            logger.error(f"Invalid slider config: min_val ({self.min_val}) >= max_val ({self.max_val})")
            raise ValueError(f"min_val ({self.min_val}) must be < max_val ({self.max_val})")
        
        if not (self.min_val <= self.init_val <= self.max_val):
            raise ValueError(
                f"init_val ({self.init_val}) must be between min_val ({self.min_val}) "
                f"and max_val ({self.max_val})"
            )
        
        if self.step <= 0:
            raise ValueError(f"step must be positive, got {self.step}")
        
        if self.marker_step <= 0:
            raise ValueError(f"marker_step must be positive, got {self.marker_step}")
        
        # Categories should only reference values within [min_val, max_val]
        for val in self.categories_dict.keys():
            if not (self.min_val <= val <= self.max_val):
                raise ValueError(
                    f"Category value {val} outside valid range [{self.min_val}, {self.max_val}]"
                )
        
        if self.language not in ("de", "en"):
            raise ValueError(f"Language must be 'de' or 'en', got {self.language}")
        
        # Validate color_range_hsv dict keys if provided
        if self.color_range_hsv:
            for key in ['hue_min', 'hue_max', 'saturation', 'value']:
                if key in self.color_range_hsv:
                    val = self.color_range_hsv[key]
                    if not (0 <= val <= 1):
                        raise ValueError(
                            f"color_range_hsv['{key}'] must be in [0, 1], got {val}"
                        )


@dataclass
class SessionConfig:
    """Configuration for a recording session.
    
    Defines participant ID, device settings, file paths, and experiment parameters.
    
    Attributes:
        participant_id: Unique identifier for participant (e.g., "VP01")
        session_id: Unique session identifier (auto-generated if not provided)
        measurement_list_path: Path to .txt file containing audio file list
        device_id: Audio device index (or None for default)
        blocksize: Number of samples per audio callback
        buffersize: Number of blocks to pre-buffer
        output_dir: Directory for saving results (auto-creates subdirectory per participant)
        language: Interface language ('de' or 'en')
    """
    participant_id: str
    measurement_list_path: str
    device_id: Optional[int] = None
    blocksize: int = 512
    buffersize: int = 20
    output_dir: str = "measurement/Results"
    language: str = "de"
    session_id: str = field(default_factory=lambda: None)
    
    def validate(self):
        """Validate session config. Raises ValueError if invalid."""
        if not self.participant_id:
            raise ValueError("participant_id must not be empty")
        
        if not self.measurement_list_path:
            raise ValueError("measurement_list_path must not be empty")
        
        if self.blocksize <= 0:
            raise ValueError(f"blocksize must be positive, got {self.blocksize}")
        
        if self.buffersize <= 0:
            raise ValueError(f"buffersize must be positive, got {self.buffersize}")
        
        if self.language not in ("de", "en"):
            raise ValueError(f"Language must be 'de' or 'en', got {self.language}")


def load_slider_config_from_yaml(filepath: str) -> SliderConfig:
    """Load a slider configuration from a YAML file.
    
    Args:
        filepath: Path to YAML config file
        
    Returns:
        SliderConfig instance
        
    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If config is invalid
        yaml.YAMLError: If YAML is malformed
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML dict at root level, got {type(data)}")
    
    # Convert categories back from YAML (may be strings) to correct types
    if 'categories_dict' in data and isinstance(data['categories_dict'], dict):
        categories_dict = {}
        for key, val in data['categories_dict'].items():
            # Keys might be strings from YAML; convert to float
            try:
                categories_dict[float(key)] = str(val)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Category key '{key}' could not be converted to float: {e}")
        data['categories_dict'] = categories_dict
    
    try:
        config = SliderConfig(**data)
        # Ensure better_at_high has a sensible default based on config name if not provided
        if not hasattr(config, 'better_at_high') or config.better_at_high is None:
            # Default based on slider type
            if 'quality' in config.name.lower():
                config.better_at_high = True
            elif 'effort' in config.name.lower() or 'noisiness' in config.name.lower():
                config.better_at_high = False
            else:
                config.better_at_high = True  # Safe default
        config.validate()
        logger.info(f"Successfully loaded slider config: {config.name} (better_at_high={config.better_at_high})")
        return config
    except (TypeError, ValueError) as e:
        logger.error(f"Failed to create SliderConfig: {e}")
        raise


def load_session_config_from_yaml(filepath: str) -> SessionConfig:
    """Load a session configuration from a YAML file.
    
    Args:
        filepath: Path to YAML config file
        
    Returns:
        SessionConfig instance
        
    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If config is invalid
        yaml.YAMLError: If YAML is malformed
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML dict at root level, got {type(data)}")
    
    config = SessionConfig(**data)
    config.validate()
    return config


def save_slider_config_to_yaml(config: SliderConfig, filepath: str):
    """Save a slider configuration to a YAML file.
    
    Args:
        config: SliderConfig instance to save
        filepath: Path to output YAML file
    """
    config.validate()
    data = asdict(config)
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def save_session_config_to_yaml(config: SessionConfig, filepath: str):
    """Save a session configuration to a YAML file.
    
    Args:
        config: SessionConfig instance to save
        filepath: Path to output YAML file
    """
    config.validate()
    data = asdict(config)
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
