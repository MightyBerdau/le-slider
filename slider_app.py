"""
Rating Collection Application - Main UI

Refactored to use new architecture (Phase 4):
- Configuration-driven slider settings (load from YAML)
- Event-driven audio playback with frame-synchronized recording
- Localization support (German/English)
- JSON data export (FAIR-compliant)

Legacy support: Still supports reading .txt stimulus lists and writing to output directory.
"""

from nicegui import ui, native
import os
import logging
from typing import Optional

from functions.config import SliderConfig, load_slider_config_from_yaml
from functions.session import SliderSession
from functions.i18n import LanguagePack
from functions.utils_gui import (
    get_color_from_colormap, Vertical_Slider, make_labels,
    StartDialog, EndScreen, SettingsScreen, PostStimulusDialog, GreetingsDialog
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default configuration (can be overridden by YAML config files)
DEFAULT_CONFIG_FILE = "examples/config_speech_quality_en.yaml"#"examples/config_listening_effort_de.yaml"
DEFAULT_STIMULUS_LIST = 'measurement/Measurement_Lists/example_list.txt'
DEFAULT_OUTPUT_DIR = 'measurement/Results'
DEFAULT_BLOCKSIZE = 256
DEFAULT_BUFFERSIZE = 4
DEFAULT_LANGUAGE = "de"


class SessionUIController:
    """Manages coordination between SliderSession and NiceGUI components."""
    
    def __init__(self):
        self.session: Optional[SliderSession] = None
        self.slider_element: Optional[Vertical_Slider] = None
        self.participant_id = "Unknown"
        self.current_slider_value = 0.0
        self.is_playing = False
        self.i18n = LanguagePack()
        self.i18n.set_language(DEFAULT_LANGUAGE)
    
    def initialize_session(
        self,
        config_file: Optional[str],
        stimulus_list_file: str,
        output_dir: str,
        participant_id: str,
        device_id: Optional[int],
        blocksize: int,
        buffersize: int,
        language: str = "de"
    ):
        """Initialize a new rating session.
        
        Args:
            config_file: Path to slider config YAML (or None for default)
            stimulus_list_file: Path to .txt file with audio filenames
            output_dir: Output directory for JSON recordings
            participant_id: Unique participant identifier
            device_id: Audio device index
            blocksize: Audio blocksize
            buffersize: Buffer size
            language: Session language
        """
        # Load slider config (config_file is already validated by caller)
        slider_config = load_slider_config_from_yaml(config_file)
        
        # Create session
        self.session = SliderSession(
            slider_config=slider_config,
            participant_id=participant_id,
            stimulus_list_file=stimulus_list_file,
            output_dir=output_dir,
            device_id=device_id,
            blocksize=blocksize,
            buffersize=buffersize,
            language=language,
        )
        
        # Register callbacks
        self.session.on_playback_started = self.on_playback_started
        self.session.on_playback_finished = self.on_playback_finished
        self.session.on_stimulus_changed = self.on_stimulus_changed
        self.session.on_session_finished = self.on_session_finished
        
        self.participant_id = participant_id
        self.i18n.set_language(language)
    
    def on_playback_started(self):
        """Called when audio playback starts."""
        self.is_playing = True
        if self.slider_element:
            self.slider_element.enable()
    
    def on_playback_finished(self):
        """Called when audio playback finishes."""
        self.is_playing = False
        if self.slider_element:
            self.slider_element.disable()
        # Save recording
        if self.session:
            self.session.save_current_recording()
        # Show post-stimulus dialog
        post_stimulus_dialog.open()
    
    def on_stimulus_changed(self, stimulus_name: str):
        """Called when stimulus changes.
        
        Args:
            stimulus_name: New stimulus filename
        """
        pass  # UI will be updated by prepare_next_stimulus()
    
    def on_session_finished(self):
        """Called when all stimuli have been played."""
        if self.session:
            self.session.end_session()
        end_screen.open()
    
    def play_current_stimulus(self):
        """Start playback of current stimulus."""
        if not self.session or not self.session.has_next_stimulus():
            return
        
        stimulus_file = self.session.get_current_stimulus()
        if not stimulus_file:
            return
        
        # Update slider value from config (range is fixed at initialization)
        config = self.session.slider_config
        if self.slider_element:
            self.slider_element.set_value(config.init_val)
        
        # Start playback (will call on_playback_started)
        # Pass slider widget so recording can capture values
        self.session.start_playback(stimulus_file, slider_widget=self.slider_element)
    
    def stop_playback(self):
        """Stop current playback."""
        if self.session:
            self.session.stop_playback()
    
    def next_stimulus(self) -> bool:
        """Move to next stimulus.
        
        Returns:
            True if more stimuli, False if session complete
        """
        if not self.session:
            return False
        
        if self.session.next_stimulus():
            stimulus_file = self.session.get_current_stimulus()
            start_dialog.open()
            return True
        else:
            end_screen.open()
            return False
    
    def get_slider_config(self) -> Optional[SliderConfig]:
        """Get current slider configuration.
        
        Returns:
            SliderConfig instance, or None if no session active
        """
        if self.session:
            return self.session.slider_config
        return None


# Global UI controller
controller = SessionUIController()


# Callbacks
def play_audio():
    """Start audio playback in thread."""
    logger.info("Starting audio playback")
    try:
        controller.play_current_stimulus()
    except Exception as e:
        logger.error(f"Failed to start playback: {e}")


def prepare_next_stimulus():
    """Prepare and show next stimulus."""
    logger.info("Preparing next stimulus")
    try:
        controller.next_stimulus()
    except Exception as e:
        logger.error(f"Failed to prepare next stimulus: {e}")


def update_background_color(value: float):
    """Update background color based on slider value for feedback."""
    try:
        config = controller.get_slider_config()
        if config:
            background_color = get_color_from_colormap(
                value, 
                config.min_val, 
                config.max_val,
                better_at_high=config.better_at_high
            )
            ui.query('body').style(f'background-color: {background_color}')
    except Exception as e:
        logger.warning(f"Failed to update background color: {e}")


def on_settings_submitted(
    participant_id: str,
    stimulus_list: str,
    output_dir: str,
    device_id: Optional[int],
    blocksize: int,
    buffersize: int,
    language: str = "de",
    config_file: Optional[str] = None
):
    """Called when settings are submitted.
    
    Args:
        participant_id: Participant ID
        stimulus_list: Path to stimulus list file
        output_dir: Output directory
        device_id: Audio device
        blocksize: Audio blocksize
        buffersize: Buffer size
        language: Session language
        config_file: Config YAML file (optional)
    """
    # Initialize session with settings
    controller.initialize_session(
        config_file=config_file or DEFAULT_CONFIG_FILE,
        stimulus_list_file=stimulus_list,
        output_dir=output_dir,
        participant_id=participant_id,
        device_id=device_id,
        blocksize=blocksize,
        buffersize=buffersize,
        language=language,
    )
    
    logger.info(f"Settings submitted: participant={participant_id}, device={device_id}, language={language}")
    
    try:
        config = controller.get_slider_config()
        if config and title_label:
            # Update the title to show new config name
            title_label.text = config.name
            title_label.update()
            
            # Rebuild labels with new config categories
            if labels_container:
                labels_container.clear()
                # Add labels within the container's context
                with labels_container:
                    make_labels(config.categories_dict)
            
            logger.info(f"Slider updated to config: {config.name}")
        
        logger.info("Session initialized successfully, opening greetings dialog")
        # Open greetings dialog
        greetings_dialog.open()
    except Exception as e:
        logger.error(f"Failed to initialize session: {e}")
        raise


# GUI ELEMENTS
# Load default config for initial display
default_config = load_slider_config_from_yaml(DEFAULT_CONFIG_FILE)

# UI elements (will be updated dynamically)
title_label = None
labels_container = None


# Create main UI container with original layout
with ui.column(align_items="center").classes("w-full"):
    # Title (top, centered)
    title_label = ui.label(default_config.name).classes("h-[10svh] text-3xl")
    
    # Slider row (middle, with slider and labels)
    with ui.row().classes("h-[90svh] max-h-96"):
        # Slider (left side, centered)
        with ui.column().classes("h-full justify-center"):
            slider = (
                Vertical_Slider(
                    min_val=default_config.min_val,
                    max_val=default_config.max_val,
                    step_width=default_config.step,
                    value_init=default_config.init_val,
                    marker_step=default_config.marker_step
                )
                .on('update:model-value', lambda e: update_background_color(e.args))
            )
            controller.slider_element = slider
            slider.disable()
        
        # Categories/Labels (right side, container for dynamic updates)
        with ui.column().classes("h-full justify-between") as labels_container:
            make_labels(default_config.categories_dict)

# Dialog setup
start_dialog = StartDialog(play_audio)
greetings_dialog = GreetingsDialog(start_dialog)
end_screen = EndScreen()

settings_dialog = SettingsScreen(
    on_submit=on_settings_submitted,
    initial_stimulus_list=DEFAULT_STIMULUS_LIST,
    initial_output_dir=DEFAULT_OUTPUT_DIR,
    initial_blocksize=DEFAULT_BLOCKSIZE,
    initial_buffersize=DEFAULT_BUFFERSIZE,
)

post_stimulus_dialog = PostStimulusDialog(prepare_next_stimulus)

# Use timer to defer dialog opening until after page is fully loaded
ui.timer(0.1, lambda: settings_dialog.open(), once=True)

ui.run(reload=False, port=native.find_open_port())