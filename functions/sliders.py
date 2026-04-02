"""
Abstract slider framework and reference implementations.

Provides BaseRatingSlider (NiceGUI wrapper) and concrete subclasses
for different rating scales. Uses factory pattern for instantiation.
"""

from dataclasses import asdict
from typing import Optional, Dict, Any
import matplotlib.cm as cm
import matplotlib.colors as mcolors

from .config import SliderConfig


class BaseRatingSlider:
    """Abstract base class for rating sliders.
    
    Wraps a NiceGUI slider and handles recording, color mapping,
    and JSON export of ratings. Subclasses can customize value
    adjustment (e.g., for scale reversals).
    
    **Note**: Requires NiceGUI context (ui.slider, ui.element setup)
    before instantiation.
    """
    
    def __init__(self, config: SliderConfig):
        """Initialize slider with configuration.
        
        Args:
            config: SliderConfig instance (must be pre-validated)
            
        Raises:
            ValueError: If config is invalid
        """
        self.config = config
        self.recorded_values = []
        self.raw_values = []
        self.current_value = config.init_val
        
        # Validate config
        if not isinstance(config, SliderConfig):
            raise ValueError("config must be a SliderConfig instance")
        
        config.validate()
    
    def record_value(self, raw_slider_value: float, frame_index: int):
        """Record a single rating value.
        
        Applies any adjustments (e.g., reversal) before recording.
        
        Args:
            raw_slider_value: Direct slider value from UI
            frame_index: Frame/callback index for timing
        """
        # Apply slider-specific adjustments
        adjusted_value = self._adjust_recorded_value(raw_slider_value)
        
        # Clamp to valid range
        adjusted_value = max(self.config.min_val, 
                            min(self.config.max_val, adjusted_value))
        
        self.recorded_values.append(adjusted_value)
        self.raw_values.append(raw_slider_value)
        self.current_value = adjusted_value
    
    def _adjust_recorded_value(self, value: float) -> float:
        """Apply slider-specific value transformations.
        
        Subclasses override to implement reversals or other transformations.
        Default implementation: identity (no change).
        
        Args:
            value: Raw slider value
            
        Returns:
            Adjusted value
        """
        # If reversal enabled, invert the scale
        if self.config.slider_reversal:
            return self.config.max_val - value + self.config.min_val
        return value
    
    def to_json(self) -> Dict[str, Any]:
        """Export slider configuration and recorded values as JSON dict.
        
        Returns:
            Dictionary with config and recordings
        """
        return {
            'config': asdict(self.config),
            'recorded_values': self.recorded_values,
            'raw_values': self.raw_values,
        }
    
    def reset(self):
        """Reset slider to initial state (clears recordings)."""
        self.recorded_values = []
        self.raw_values = []
        self.current_value = self.config.init_val
    
    @staticmethod
    def _compute_colormap_color(value: float, 
                                min_val: float, 
                                max_val: float,
                                hue_min: float = 0.03,
                                hue_max: float = 0.3,
                                saturation: float = 0.8,
                                value_level: float = 0.9) -> str:
        """Compute RGB color for a value using HSV colormap.
        
        Maps value range [min_val, max_val] to HSV range,
        then converts to hex RGB string for UI display.
        
        Args:
            value: Rating value
            min_val: Minimum of value range
            max_val: Maximum of value range
            hue_min: Minimum HSV hue (0-1, where 0.03 ≈ red, 0.3 ≈ green)
            hue_max: Maximum HSV hue
            saturation: HSV saturation level (0-1)
            value_level: HSV value/brightness level (0-1)
            
        Returns:
            Hex color string (e.g., '#FF0000' for red)
        """
        # Normalize value to [0, 1]
        if max_val == min_val:
            norm_val = 0.5
        else:
            norm_val = (value - min_val) / (max_val - min_val)
        
        # Clamp to valid range
        norm_val = max(0.0, min(1.0, norm_val))
        
        # Interpolate hue
        hue = hue_min + norm_val * (hue_max - hue_min)
        
        # Convert HSV to RGB (using matplotlib's colorsys)
        rgb = mcolors.hsv_to_rgb((hue, saturation, value_level))
        
        # Convert to hex string
        return '#{:02x}{:02x}{:02x}'.format(
            int(rgb[0] * 255),
            int(rgb[1] * 255),
            int(rgb[2] * 255),
        )
    
    def get_color_for_value(self, value: float) -> str:
        """Get color for a rating value based on config colormap.
        
        Args:
            value: Rating value
            
        Returns:
            Hex color string
        """
        hue_range = self.config.color_range_hsv or {}
        return self._compute_colormap_color(
            value,
            self.config.min_val,
            self.config.max_val,
            hue_min=hue_range.get('hue_min', 0.03),
            hue_max=hue_range.get('hue_max', 0.3),
            saturation=hue_range.get('saturation', 0.8),
            value_level=hue_range.get('value', 0.9),
        )


class ListeningEffortSlider(BaseRatingSlider):
    """Concrete slider for listening effort ratings.
    
    Implements ESCU (Effort Characterization Scale for Unaided Listeners)
    1-14 scale with German and English presets.
    """
    
    @staticmethod
    def create_de_config() -> SliderConfig:
        """Create listening effort config with German labels.
        
        Returns:
            SliderConfig for ESCU 1-14 German scale
        """
        return SliderConfig(
            name='listening_effort',
            min_val=1.0,
            max_val=14.0,
            init_val=7.0,
            step=1.0,
            marker_step=1.0,
            categories_dict={
                1.0: 'sehr leicht',
                2.0: 'leicht',
                3.0: 'ziemlich leicht',
                4.0: 'ziemlich leicht',
                5.0: 'weder leicht noch schwer',
                6.0: 'weder leicht noch schwer',
                7.0: 'mittel',
                8.0: 'weder leicht noch schwer',
                9.0: 'weder leicht noch schwer',
                10.0: 'ziemlich schwer',
                11.0: 'ziemlich schwer',
                12.0: 'schwer',
                13.0: 'schwer',
                14.0: 'sehr schwer',
            },
            language='de',
            slider_reversal=False,
            color_range_hsv={
                'hue_min': 0.03,    # Red
                'hue_max': 0.3,     # Green
                'saturation': 0.8,
                'value': 0.9,
            },
            description='Anstrengung beim Hören (ESCU 1-14)',
        )
    
    @staticmethod
    def create_en_config() -> SliderConfig:
        """Create listening effort config with English labels.
        
        Returns:
            SliderConfig for ESCU 1-14 English scale
        """
        return SliderConfig(
            name='listening_effort',
            min_val=1.0,
            max_val=14.0,
            init_val=7.0,
            step=1.0,
            marker_step=1.0,
            categories_dict={
                1.0: 'very easy',
                2.0: 'easy',
                3.0: 'rather easy',
                4.0: 'rather easy',
                5.0: 'medium',
                6.0: 'medium',
                7.0: 'neutral',
                8.0: 'medium',
                9.0: 'medium',
                10.0: 'rather difficult',
                11.0: 'rather difficult',
                12.0: 'difficult',
                13.0: 'difficult',
                14.0: 'very difficult',
            },
            language='en',
            slider_reversal=False,
            color_range_hsv={
                'hue_min': 0.03,    # Red (easy)
                'hue_max': 0.3,     # Green (difficult)
                'saturation': 0.8,
                'value': 0.9,
            },
            description='Listening effort (ESCU 1-14)',
        )


def create_slider_from_config(config: SliderConfig) -> BaseRatingSlider:
    """Factory function to create appropriate slider from config.
    
    Validates config and dispatches to appropriate slider subclass.
    If config.name matches a known slider type, returns that subclass.
    Otherwise returns generic BaseRatingSlider.
    
    Args:
        config: SliderConfig instance
        
    Returns:
        Appropriate BaseRatingSlider subclass instance
        
    Raises:
        ValueError: If config is invalid
    """
    # Validate config first
    config.validate()
    
    # Dispatch based on slider name
    if config.name == 'listening_effort':
        return ListeningEffortSlider(config)
    else:
        # Default: generic slider for unknown types
        return BaseRatingSlider(config)
