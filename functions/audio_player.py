"""
Abstract audio player interface with event system for rating collection.

Provides RatingAudioPlayer base class that emits frame events for recording,
enabling clean separation between audio playback and rating slider.
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, List
from dataclasses import dataclass
import threading
import enum
import logging
import time
import sounddevice as sd
import soundfile as sf
import queue
import sys

logger = logging.getLogger(__name__)


class FrameEventType(enum.Enum):
    """Types of frame events emitted during playback."""
    FRAME_START = "frame_start"      # Playback of a frame starts
    FRAME_RENDERED = "frame_rendered"  # Frame sent to audio device
    PLAYBACK_STARTED = "playback_started"
    PLAYBACK_STOPPED = "playback_stopped"
    PLAYBACK_FINISHED = "playback_finished"
    ERROR = "error"


@dataclass
class FrameEvent:
    """Event emitted for each audio frame during playback."""
    event_type: FrameEventType
    frame_index: int              # Sequential frame number (0-based)
    timestamp_sec: float          # Time relative to playback start
    blocksize: int                # Samples in this block
    sample_rate: int              # Sampling rate in Hz
    error_message: Optional[str] = None  # For ERROR events


class FrameEventListener(ABC):
    """Interface for objects that listen to frame events."""
    
    @abstractmethod
    def on_frame_event(self, event: FrameEvent):
        """Called when a frame event occurs.
        
        Args:
            event: FrameEvent with details about the frame
        """
        pass


class RatingAudioPlayer(ABC):
    """Audio player with event system for synchronized rating recording.
    
    Plays back audio files using sounddevice backend with frame-by-frame
    event emission for recording synchronization.
    
    Typical usage:
        player = RatingAudioPlayer(device=0, blocksize=256, buffersize=4)
        recorder = RatingRecorder(...)
        player.add_listener(recorder)  # Recorder subscribes to events
        player.play(filepath)           # Events emitted during playback
    """
    
    def __init__(
        self,
        device: Optional[int] = None,
        blocksize: int = 256,
        buffersize: int = 4,
        filepath: Optional[str] = None,
    ):
        """Initialize audio player.
        
        Args:
            device: Audio device ID (None for default)
            blocksize: Samples per audio callback/frame
            buffersize: Number of blocks to buffer
            filepath: Path to audio file (optional, can be set later)
        """
        self.device = device
        self.blocksize = blocksize
        self.buffersize = buffersize
        self._filepath = filepath
        
        self._listeners: List[FrameEventListener] = []
        self._is_playing = False
        self._frame_count = 0
        self._stop_event = threading.Event()
        self._playback_start_time = None  # Time when playback started (device time)
        self._frame_count_callback = 0    # Frame counter in callback for accurate timing
        self._recorder = None             # Recorder for direct callback-based recording
        self._slider_widget = None        # Slider widget for value capture
        self.q = None
        self.event = None
        self.fs = None
    
    def add_listener(self, listener: FrameEventListener):
        """Subscribe a listener to frame events.
        
        Args:
            listener: Object implementing FrameEventListener interface
        """
        if listener not in self._listeners:
            self._listeners.append(listener)
    
    def remove_listener(self, listener: FrameEventListener):
        """Unsubscribe a listener from frame events.
        
        Args:
            listener: Listener to remove
        """
        if listener in self._listeners:
            self._listeners.remove(listener)
    
    def _emit_frame_event(self, event: FrameEvent):
        """Emit a frame event to all registered listeners.
        
        Args:
            event: FrameEvent to broadcast
        """
        for listener in self._listeners:
            try:
                listener.on_frame_event(event)
            except Exception as e:
                # Log listener errors but continue processing
                print(f"Error in listener callback: {e}")
    
    def _emit_playback_started(self):
        """Emit playback started event."""
        self._is_playing = True
        self._frame_count = 0
        self._stop_event.clear()
        
        event = FrameEvent(
            event_type=FrameEventType.PLAYBACK_STARTED,
            frame_index=0,
            timestamp_sec=0.0,
            blocksize=self.blocksize,
            sample_rate=0,  # Will be set by subclass if known
        )
        self._emit_frame_event(event)
    
    def set_recorder_and_slider(self, recorder, slider_widget):
        """Set recorder and slider widget for callback-based recording.
        
        Recording happens directly in the audio callback for perfect synchronization.
        
        Args:
            recorder: RatingRecorder instance
            slider_widget: UI slider widget for value capture
        """
        self._recorder = recorder
        self._slider_widget = slider_widget
    
    def _emit_playback_finished(self):
        """Emit playback finished event."""
        self._is_playing = False
        
        event = FrameEvent(
            event_type=FrameEventType.PLAYBACK_FINISHED,
            frame_index=self._frame_count,
            timestamp_sec=(self._frame_count * self.blocksize) / 44100,  # Approximate
            blocksize=self.blocksize,
            sample_rate=0,
        )
        self._emit_frame_event(event)
    
    def _emit_error(self, message: str):
        """Emit error event.
        
        Args:
            message: Error description
        """
        event = FrameEvent(
            event_type=FrameEventType.ERROR,
            frame_index=self._frame_count,
            timestamp_sec=0.0,
            blocksize=0,
            sample_rate=0,
            error_message=message,
        )
        self._emit_frame_event(event)
    
    def is_playing(self) -> bool:
        """Check if audio is currently playing.
        
        Returns:
            True if playback is active
        """
        return self._is_playing
    
    def stop(self):
        """Request playback to stop.
        
        Sets internal stop event that subclass checks in playback loop.
        """
        self._stop_event.set()
    
    def should_stop(self) -> bool:
        """Check if stop has been requested.
        
        Returns:
            True if stop_event is set
        """
        return self._stop_event.is_set()
    
    def get_file_duration(self, filepath: Optional[str] = None) -> float:
        """Get duration of audio file in seconds.
        
        Args:
            filepath: Path to audio file (uses self._filepath if not provided)
            
        Returns:
            Duration in seconds, or 0.0 if file cannot be read
        """
        try:
            audio_filepath = filepath or self._filepath
            if not audio_filepath:
                return 0.0
            with sf.SoundFile(audio_filepath) as f:
                return f.frames / f.samplerate if f.samplerate > 0 else 0.0
        except Exception as e:
            logger.warning(f"Could not determine file duration: {e}")
            return 0.0
    
    def get_file_sample_rate(self, filepath: Optional[str] = None) -> int:
        """Get sample rate of audio file in Hz.
        
        Args:
            filepath: Path to audio file (uses self._filepath if not provided)
            
        Returns:
            Sample rate in Hz, or 0 if file cannot be read
        """
        try:
            audio_filepath = filepath or self._filepath
            if not audio_filepath:
                return 0
            with sf.SoundFile(audio_filepath) as f:
                return f.samplerate
        except Exception as e:
            logger.warning(f"Could not determine file sample rate: {e}")
            return 0
    
    # Properties (backward compatibility)
    @property
    def filepath(self):
        return self._filepath

    @filepath.setter
    def filepath(self, filepath):
        self._filepath = filepath

    def callback(self, outdata, frames, time, status):
        """Audio callback for sounddevice stream.
        
        Called by sounddevice for each audio frame. Pulls data from queue,
        records slider values with device-accurate timing, and fills output buffer.
        """
        assert frames == self.blocksize
        if status.output_underflow:
            logger.debug('Output underflow: playback falling behind')
        if status.output_overflow:
            logger.warning('Output overflow: input data arriving too fast')
        
        try:
            frame_duration = (frames / self.fs) if self.fs > 0 else 0.005
            timeout = frame_duration * 2
            data = self.q.get(timeout=timeout)
        except queue.Empty:
            logger.debug('Queue empty, padding with silence')
            outdata[:] = b'\x00' * len(outdata)
            return
        
        # Calculate elapsed time based on frame count for accurate, unique timestamps
        # (device time only updates every N callbacks, causing duplicate timestamps)
        elapsed_sec = (self._frame_count_callback * self.blocksize) / self.fs if self.fs > 0 else 0.0
        
        # Record slider value directly with frame-accurate timing
        if self._recorder and self._slider_widget and hasattr(self._slider_widget, 'value'):
            self._recorder.add_frame(self._slider_widget.value, timestamp_rel_sec=elapsed_sec)
        
        # Emit frame event for listeners (for backward compatibility)
        event = FrameEvent(
            event_type=FrameEventType.FRAME_RENDERED,
            frame_index=self._frame_count_callback,
            timestamp_sec=elapsed_sec,
            blocksize=self.blocksize,
            sample_rate=self.fs,
        )
        self._emit_frame_event(event)
        self._frame_count_callback += 1
        
        if len(data) < len(outdata):
            outdata[:len(data)] = data
            outdata[len(data):] = b'\x00' * (len(outdata) - len(data))
            raise sd.CallbackStop
        else:
            outdata[:] = data

    def play(self, filepath: Optional[str] = None):
        """Play an audio file.
        
        Args:
            filepath: Path to audio file. If None, uses self._filepath
        """
        if filepath:
            self._filepath = filepath
        
        self.run(stop_event=None)
    
    def run(self, stop_event: Optional[threading.Event] = None):
        """Plays back audio from self._filepath
        
        Args:
            stop_event: Threading event to signal stop (backward compat)
        """
        logger.info('Starting playback!')
        # Use a larger queue to handle variable callback timing
        queue_maxsize = max(32, self.buffersize * 8)
        self.q = queue.Queue(maxsize=queue_maxsize)
        self.event = threading.Event()
        
        try:
            self._emit_playback_started()
            
            with sf.SoundFile(self._filepath) as f:
                self.fs = f.samplerate
                logger.info(f"Audio file: {self._filepath}, sample_rate={self.fs}, channels={f.channels}, duration={f.frames / self.fs:.2f}s")
                
                # Pre-fill buffer with more data to ensure smooth start
                frames_prefilled = 0
                target_prefill = min(queue_maxsize // 2, 32)  # Pre-fill half of queue or 32 frames, whichever is smaller
                for i in range(target_prefill):
                    data = f.buffer_read(self.blocksize, dtype='float32')
                    if data is None or len(data) == 0:
                        break
                    try:
                        self.q.put_nowait(data)
                        frames_prefilled += 1
                    except queue.Full:
                        logger.debug(f"Queue full during pre-fill at block {i}")
                        break
                logger.info(f"Pre-filled buffer with {frames_prefilled} blocks (target: {target_prefill})")
                
                # Create audio stream
                stream = sd.RawOutputStream(
                    samplerate=self.fs,
                    blocksize=self.blocksize,
                    device=self.device,
                    channels=f.channels,
                    dtype='float32',
                    callback=self.callback,
                    finished_callback=self.event.set,
                )
                
                with stream:
                    timeout = max(1.0, self.blocksize * queue_maxsize / self.fs)
                    logger.info(f"Audio stream started (device={self.device}), timeout={timeout:.2f}s")
                    
                    blocks_read = frames_prefilled
                    max_retries = 5
                    retry_count = 0
                    while not (stop_event and stop_event.is_set()) and not self.should_stop():
                        try:
                            data = f.buffer_read(self.blocksize, dtype='float32')
                            if data is None or len(data) == 0:
                                logger.debug(f"End of audio file reached after {blocks_read} blocks")
                                break
                            
                            # Attempt to put data in queue with retry logic
                            put_success = False
                            for attempt in range(max_retries):
                                try:
                                    self.q.put(data, timeout=timeout)
                                    # Note: Frame rendering event is now emitted from callback with accurate timing
                                    blocks_read += 1
                                    retry_count = 0  # Reset retry counter on success
                                    put_success = True
                                    break
                                except queue.Full:
                                    if attempt < max_retries - 1:
                                        # Exponential backoff: 0.01, 0.02, 0.04, 0.08, 0.16 seconds
                                        wait_time = 0.01 * (2 ** attempt)
                                        logger.debug(f"Queue full at block {blocks_read}, attempt {attempt + 1}/{max_retries}, waiting {wait_time:.3f}s")
                                        time.sleep(wait_time)
                                    else:
                                        retry_count += 1
                                        logger.error(f"Queue full at block {blocks_read} - max retries exceeded ({retry_count} consecutive failures)")
                                        if retry_count >= 3:
                                            # Too many consecutive failures, likely device issue
                                            logger.error("Too many queue failures, aborting playback")
                                            raise
                                        # Try one more time with longer timeout
                                        try:
                                            self.q.put(data, timeout=timeout * 2)
                                            put_success = True
                                            retry_count = 0
                                        except queue.Full:
                                            logger.error(f"Final retry failed for block {blocks_read}")
                                            raise
                            
                            if not put_success:
                                break
                                
                        except KeyboardInterrupt:
                            logger.warning("Playback interrupted!")
                            break
                    
                    logger.info(f"Read {blocks_read} total blocks, waiting for stream to finish...")
                    # Wait for stream to finish with timeout
                    stream_finished = self.event.wait(timeout=5.0)
                    if not stream_finished:
                        logger.warning("Stream finished callback did not complete within timeout")
                    logger.info("Stream finished")
                    
        except Exception as e:
            error_msg = type(e).__name__ + ': ' + str(e)
            logger.error(f"Playback error: {error_msg}", exc_info=True)
            self._emit_error(error_msg)
        finally:
            if self.event:
                self.event.set()
            self._playback_start_time = None  # Reset for next playback
            self._frame_count_callback = 0
            self._emit_playback_finished()
            logger.info("Playback completed")



