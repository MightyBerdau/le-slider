"""
Session management for rating collection experiments.

Manages participant workflow: settings → greeting → stimulus playback →
recording → post-stimulus questions → next stimulus → completion.
"""

import os
import threading
import logging
from typing import Optional, Callable, List
from datetime import datetime

from .config import SliderConfig, load_slider_config_from_yaml
from .data_io import RatingRecorder
from .audio_player import (
    RatingAudioPlayer, FrameEventListener, FrameEvent, FrameEventType
)
from .i18n import LanguagePack

logger = logging.getLogger(__name__)


class PlaybackCompletionListener(FrameEventListener):
    """Listener that triggers a callback when playback finishes."""
    
    def __init__(self, on_finished: Callable[[], None]):
        """Initialize listener.
        
        Args:
            on_finished: Callback to invoke when playback finishes
        """
        self.on_finished = on_finished
    
    def on_frame_event(self, event: FrameEvent):
        """Handle frame events.
        
        Args:
            event: FrameEvent from audio player
        """
        if event.event_type == FrameEventType.PLAYBACK_FINISHED:
            if self.on_finished:
                self.on_finished()


class SliderSession:
    """Manages a complete rating session for a participant.
    
    Orchestrates:
    1. Session configuration (participant, audio files, settings)
    2. Slider configuration (scale, categories, language)
    3. Audio playback with frame-synchronized recording
    4. JSON output with complete metadata
    
    Usage:
        session = SliderSession(
            config_file='config_listening_effort_de.yaml',
            participant_id='VP001',
            stimulus_list_file='stimuli.txt',
            output_dir='output/'
        )
        session.start()
    """
    
    def __init__(
        self,
        slider_config: Optional[SliderConfig] = None,
        config_file: Optional[str] = None,
        participant_id: str = "Unknown",
        stimulus_list_file: Optional[str] = None,
        output_dir: str = "output/",
        device_id: Optional[int] = None,
        blocksize: int = 256,
        buffersize: int = 4,
        language: str = "de",
    ):
        """Initialize rating session.
        
        Args:
            slider_config: SliderConfig instance (or load from config_file)
            config_file: Path to slider config YAML file
            participant_id: Unique participant identifier
            stimulus_list_file: Path to .txt file with audio filenames
            output_dir: Directory for saving JSON recordings
            device_id: Audio device index (None for default)
            blocksize: Audio samples per callback
            buffersize: Number of blocks in buffer
            language: Session language ('de' or 'en')
        """
        logger.info(f"Initializing session for participant: {participant_id}")
        
        # Load or validate slider config
        if slider_config is None:
            if config_file is None:
                logger.error("No slider_config or config_file provided")
                raise ValueError("Must provide either slider_config or config_file")
            slider_config = load_slider_config_from_yaml(config_file)
        
        self.slider_config = slider_config
        self.participant_id = participant_id
        self.stimulus_list_file = stimulus_list_file
        self.output_dir = output_dir
        self.device_id = device_id
        self.blocksize = blocksize
        self.buffersize = buffersize
        
        # Load localization
        self.i18n = LanguagePack()
        self.i18n.set_language(language)
        
        # Load stimulus list
        self.stimuli: List[str] = []
        self.current_stimulus_index = 0
        if stimulus_list_file:
            self._load_stimulus_list(stimulus_list_file)
        
        # Audio player
        self.audio_player: Optional[RatingAudioPlayer] = None
        self.is_playing = False
        
        # Current recording
        self.current_recorder: Optional[RatingRecorder] = None
        
        # Session ID
        self.session_id = datetime.utcnow().isoformat() + "Z"
        
        # Callbacks for UI coordination
        self.on_playback_started: Optional[Callable[[], None]] = None
        self.on_playback_finished: Optional[Callable[[], None]] = None
        self.on_stimulus_changed: Optional[Callable[[str], None]] = None
        self.on_session_finished: Optional[Callable[[], None]] = None
    
    def _load_stimulus_list(self, filepath: str):
        """Load stimulus filenames from .txt file.
        
        Args:
            filepath: Path to .txt file with filenames (one per line)
            
        Raises:
            FileNotFoundError: If file not found
        """
        logger.info(f"Loading stimulus list from: {filepath}")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.stimuli = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded {len(self.stimuli)} stimuli")
        except FileNotFoundError:
            logger.error(f"Stimulus list file not found: {filepath}")
            raise
    
    def get_current_stimulus(self) -> Optional[str]:
        """Get filename of current stimulus.
        
        Returns:
            Stimulus filename or None if finished
        """
        if self.current_stimulus_index < len(self.stimuli):
            return self.stimuli[self.current_stimulus_index]
        return None
    
    def has_next_stimulus(self) -> bool:
        """Check if there are more stimuli to play.
        
        Returns:
            True if more stimuli remain
        """
        return self.current_stimulus_index < len(self.stimuli)
    
    def prepare_stimulus(self, stimulus_file: str) -> RatingRecorder:
        """Prepare recording for a stimulus.
        
        Creates RatingRecorder and connects to audio player events.
        
        Args:
            stimulus_file: Path or filename of audio stimulus
            
        Returns:
            RatingRecorder instance
        """
        # Create recorder
        recorder = RatingRecorder(
            self.slider_config,
            participant_id=self.participant_id,
            stimulus_file=os.path.basename(stimulus_file),
            session_id=self.session_id,
        )
        
        # Note: Audio metadata will be set in start_playback() after getting actual file info
        self.current_recorder = recorder
        return recorder
    
    def start_playback(self, stimulus_file: str, slider_widget=None):
        """Start audio playback with synchronized recording.
        
        Args:
            stimulus_file: Path to audio file
            slider_widget: Optional UI slider widget to capture values during playback
            
        Raises:
            FileNotFoundError: If audio file not found
        """
        if not os.path.exists(stimulus_file):
            logger.error(f"Audio file not found: {stimulus_file}")
            raise FileNotFoundError(f"Audio file not found: {stimulus_file}")
        
        logger.info(f"Starting playback: {stimulus_file}")
        
        # Create audio player
        self.audio_player = RatingAudioPlayer(
            device=self.device_id,
            blocksize=self.blocksize,
            buffersize=self.buffersize,
        )
        
        # Prepare recorder
        recorder = self.prepare_stimulus(stimulus_file)
        
        # Update recorder with actual file metadata
        duration_sec = self.audio_player.get_file_duration(stimulus_file)
        sample_rate = self.audio_player.get_file_sample_rate(stimulus_file)
        recorder.set_audio_metadata(
            sample_rate=sample_rate or 48000,  # Use actual sample rate from file
            blocksize=self.blocksize,
            buffersize=self.buffersize,
            duration_sec=duration_sec,
        )
        
        # Set up callback-based recording (recorder is called directly from audio callback)
        self.audio_player.set_recorder_and_slider(recorder, slider_widget)
        self.current_adapter = None  # No longer using event-based adapter
        
        # Connect playback completion listener
        completion_listener = PlaybackCompletionListener(self._on_playback_finished)
        self.audio_player.add_listener(completion_listener)
        
        # Start playback in thread
        self.is_playing = True
        if self.on_playback_started:
            self.on_playback_started()
        
        thread = threading.Thread(target=self.audio_player.play, args=(stimulus_file,))
        thread.daemon = True
        thread.start()
        logger.debug(f"Playback thread started for {stimulus_file}")
    
    def stop_playback(self):
        """Stop current audio playback."""
        if self.audio_player:
            self.audio_player.stop()
        self.is_playing = False
    
    def _on_playback_finished(self):
        """Internal callback when playback finishes.
        
        Updates session state and calls user-provided callback.
        """
        logger.info("Playback finished")
        self.is_playing = False
        if self.on_playback_finished:
            self.on_playback_finished()
    
    def save_current_recording(self) -> Optional[str]:
        """Save current recording to JSON file.
        
        Returns:
            Path to saved JSON file, or None if no recording active
        """
        if not self.current_recorder:
            logger.warning("No active recording to save")
            return None
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Generate filename
        stimulus_base = os.path.splitext(
            os.path.basename(self.current_recorder.stimulus_file)
        )[0]
        filename = f"{self.participant_id}_{stimulus_base}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        logger.info(f"Saving recording to: {filepath}")
        
        try:
            # Save recording
            self.current_recorder.save_to_json(filepath)
            logger.info(f"Recording saved successfully: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save recording: {e}")
            raise
    
    def next_stimulus(self) -> bool:
        """Move to next stimulus.
        
        Returns:
            True if there are more stimuli, False if session complete
        """
        self.current_stimulus_index += 1
        
        if self.has_next_stimulus():
            if self.on_stimulus_changed:
                self.on_stimulus_changed(self.get_current_stimulus())
            return True
        else:
            if self.on_session_finished:
                self.on_session_finished()
            return False
    
    def end_session(self):
        """Finalize session."""
        self.stop_playback()
        if self.current_recorder:
            self.save_current_recording()


class SimpleSessionListener(FrameEventListener):
    """Simple listener for slider value updates from frame events.
    
    Bridges audio frame events to a slider update callback for UI feedback.
    """
    
    def __init__(self, slider_value_callback: Optional[Callable[[float], None]] = None):
        """Initialize listener.
        
        Args:
            slider_value_callback: Called with slider value on each frame
        """
        self.slider_value_callback = slider_value_callback
        self.current_slider_value = 0.0
    
    def set_slider_value(self, value: float):
        """Set current slider value to record.
        
        Args:
            value: Rating value from slider
        """
        self.current_slider_value = value
    
    def on_frame_event(self, event: FrameEvent):
        """Handle frame events.
        
        Args:
            event: FrameEvent from audio player
        """
        # Could be extended to handle UI updates, progress bars, etc.
        pass
