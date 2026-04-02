"""
Unit tests for rating slider classes (functions/sliders.py).

Tests BaseRatingSlider, ListeningEffortSlider, and factory function.
"""

import unittest
from functions.config import SliderConfig
from functions.sliders import (
    BaseRatingSlider,
    ListeningEffortSlider,
    create_slider_from_config,
)


class TestListeningEffortSlider(unittest.TestCase):
    """Test ListeningEffortSlider preset configurations."""
    
    def test_create_german_config(self):
        """Create German LE config and verify properties."""
        config = ListeningEffortSlider.create_de_config()
        self.assertEqual(config.name, "listening_effort")
        self.assertEqual(config.min_val, 1)
        self.assertEqual(config.max_val, 14)
        self.assertEqual(config.init_val, 7)
        self.assertEqual(config.language, "de")
        config.validate()  # Should not raise
    
    def test_create_english_config(self):
        """Create English LE config."""
        config = ListeningEffortSlider.create_en_config()
        self.assertEqual(config.name, "listening_effort")
        self.assertEqual(config.language, "en")
        config.validate()  # Should not raise
    
    def test_german_categories(self):
        """Verify German LE categories are present."""
        config = ListeningEffortSlider.create_de_config()
        self.assertIn(1, config.categories_dict)
        self.assertIn(14, config.categories_dict)
        self.assertEqual(config.categories_dict[1], "sehr leicht")
        self.assertEqual(config.categories_dict[14], "sehr schwer")
    
    def test_english_categories(self):
        """Verify English LE categories."""
        config = ListeningEffortSlider.create_en_config()
        self.assertIn(1, config.categories_dict)
        self.assertEqual(config.categories_dict[1], "very easy")


class TestBaseRatingSlider(unittest.TestCase):
    """Test BaseRatingSlider recording and export."""
    
    def test_slider_init(self):
        """Initialize slider from config."""
        config = SliderConfig(
            name="test",
            min_val=1,
            max_val=10,
            init_val=5,
            step=0.1,
            marker_step=1,
            categories_dict={1: "Low", 10: "High"},
        )
        # Note: We can't directly instantiate without NiceGUI running
        # This is a limitation of the design; would need Qt/mock GUI for full testing
        config.validate()
    
    def test_listening_effort_slider_init(self):
        """Initialize LE slider with German config."""
        config = ListeningEffortSlider.create_de_config()
        slider = ListeningEffortSlider(config)
        self.assertEqual(slider.config.name, "listening_effort")
        self.assertEqual(slider.config.min_val, 1)
        self.assertEqual(slider.config.max_val, 14)
    
    def test_listening_effort_slider_with_custom_config(self):
        """Initialize LE slider with custom config."""
        config = ListeningEffortSlider.create_en_config()
        slider = ListeningEffortSlider(config)
        self.assertEqual(slider.config.language, "en")


class TestSliderFactory(unittest.TestCase):
    """Test slider factory function."""
    
    def test_create_listening_effort_slider(self):
        """Factory creates ListeningEffortSlider for LE config."""
        config = ListeningEffortSlider.create_de_config()
        slider = create_slider_from_config(config)
        self.assertIsInstance(slider, ListeningEffortSlider)
    
    def test_factory_validates_config(self):
        """Factory validates config before creating slider."""
        config = SliderConfig(
            name="listening_effort",
            min_val=10,
            max_val=5,  # Invalid: min > max
            init_val=7,
            step=0.1,
            marker_step=1,
            categories_dict={5: "Low"},
        )
        with self.assertRaises(ValueError):
            create_slider_from_config(config)
    
    def test_factory_creates_generic_slider(self):
        """Factory creates generic BaseRatingSlider for unknown types."""
        config = SliderConfig(
            name="unknown_type",
            min_val=1,
            max_val=10,
            init_val=5,
            step=0.1,
            marker_step=1,
            categories_dict={1: "Low", 10: "High"},
        )
        slider = create_slider_from_config(config)
        self.assertIsInstance(slider, BaseRatingSlider)


class TestSliderColorMapping(unittest.TestCase):
    """Test color computation for visual feedback."""
    
    def test_colormap_edge_values(self):
        """Test color at minimum, maximum, and middle values."""
        # Test static method
        color_min = BaseRatingSlider._compute_colormap_color(1, 1, 14)
        color_max = BaseRatingSlider._compute_colormap_color(14, 1, 14)
        color_mid = BaseRatingSlider._compute_colormap_color(7, 1, 14)
        
        # Should all be valid hex color strings
        self.assertTrue(color_min.startswith("#"))
        self.assertTrue(color_max.startswith("#"))
        self.assertTrue(color_mid.startswith("#"))
        self.assertEqual(len(color_min), 7)  # #RRGGBB format
    
    def test_color_hsv_range_variation(self):
        """Different HSV ranges should produce different colors."""
        color_red_to_green = BaseRatingSlider._compute_colormap_color(
            7, 1, 14, hue_min=0.0, hue_max=0.33
        )
        color_green_to_red = BaseRatingSlider._compute_colormap_color(
            7, 1, 14, hue_min=0.33, hue_max=0.0
        )
        # Colors should be different
        self.assertNotEqual(color_red_to_green, color_green_to_red)
        self.assertTrue(color_red_to_green.startswith("#"))
        self.assertTrue(color_green_to_red.startswith("#"))


if __name__ == '__main__':
    unittest.main()
