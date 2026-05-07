import asyncio
import librosa
import numpy as np
import sounddevice as sd

from .gui import RatingSlider

class AudioPlayerBase():
    def __init__(
            self,
            device_id: int,
            blocksize: int,
            target_fs: int):
        """Initialize AudioPlayer with audio device and rating slider.
        
        Args:
            rating_slider: RatingSlider instance for recording ratings
            device_id: Audio device index for playback
            blocksize: Audio buffer size in samples
            target_fs: Target sampling rate in Hz for audio playback (librosa will resample if needed)
        """
        self._device_id = device_id
        self._blocksize = blocksize
        self._target_fs = target_fs

        # Initialized in self.play_stimulus_and_record_ratings()
        self._idx_start = None # 0
        self._audio = None
        self._done = None # asyncio.Event()
        self._loop = None # asyncio.get_event_loop()

    @property
    def blocksize(self) -> int:
        """Get audio buffer blocksize in samples."""
        return self._blocksize
    
    @property
    def fs(self) -> int:
        """Get audio sampling frequency in Hz."""
        return self._target_fs

    def _callback(self, outdata, frames, time, status):
        """Audio stream callback for playback and rating collection.
        
        Called by the audio stream to output audio data and record slider ratings
        at regular intervals.
        
        Args:
            outdata: Audio output buffer to fill
            frames: Number of frames requested
            time: Current time information
            status: Status information from audio stream
        """
        chunk = self._audio[self._idx_start : self._idx_start + frames]
        
        if len(chunk) < frames:
            outdata[:len(chunk)] = chunk
            outdata[len(chunk):] = 0
            self._loop.call_soon_threadsafe(self._done.set)
        else:
            outdata[:] = chunk
        
        self._idx_start += frames
    
    def stop(self):
        """Stop playback early by signaling the done event."""
        if self._done is not None and self._loop is not None:
            self._loop.call_soon_threadsafe(self._done.set)

    async def play_stimulus(self, filepath: str) -> None:
        """Play audio stimulus.
        
        Uses librosa to load and automatically resample audio to target sampling rate.
        
        Args:
            filepath: Path to audio file to play
        """
        # Load audio with librosa, automatically resampling to target_fs
        # librosa.load returns (channels, samples) for stereo (mono=False)
        audio = librosa.load(filepath, sr=self._target_fs, mono=False)[0]
        if audio.ndim == 1:
            audio = np.stack([audio, audio])  # mono → stereo duplication
        
        self._audio = audio.T # shape: (samples, channels)

        self._done = asyncio.Event()
        self._loop = asyncio.get_event_loop()
        self._idx_start = 0
        
        with sd.OutputStream(
            callback=self._callback,
            samplerate=self._target_fs,
            channels=self._audio.shape[1],
            blocksize=self._blocksize,
            device=self._device_id,
        ):
            await self._done.wait()

class AudioPlayer(AudioPlayerBase):
    def __init__(
            self,
            rating_slider: RatingSlider,
            device_id: int,
            blocksize: int,
            target_fs: int):
        """Initialize AudioPlayer with audio device and rating slider.
        
        Extends AudioPlayerBase to add real-time slider rating collection during
        audio playback. When audio plays through the audio stream callback, the
        current slider value is captured at each callback invocation.
        
        Args:
            rating_slider: RatingSlider instance for recording ratings during playback
            device_id: Audio device index for playback
            blocksize: Audio buffer size in samples
            target_fs: Target sampling rate in Hz for audio playback (librosa will resample if needed)
        """
        super().__init__(device_id, blocksize, target_fs)
        self._slider = rating_slider
        self.ratings = None # []

    def _callback(self, outdata, frames, time, status):
        """Audio stream callback that extends parent with rating collection.
        
        Overrides AudioPlayerBase._callback to add slider rating recording
        functionality. After the parent class fills the output buffer and
        handles playback mechanics, this override immediately captures the
        current slider value for later analysis.
        
        Args:
            outdata: Audio output buffer to fill
            frames: Number of frames requested
            time: Current time information
            status: Status information from audio stream
        """
        super()._callback(outdata, frames, time, status)
        self.ratings.append(self._slider.value)

    async def play_stimulus_and_record_ratings(self, filepath: str) -> list[float]:
        """Play audio stimulus and record slider ratings throughout playback.
        
        Uses librosa to load and automatically resample audio to target sampling rate.
        
        Args:
            filepath: Path to audio file to play
            
        Returns:
            List of slider ratings recorded during playback
        """
        self.ratings = []
        await super().play_stimulus(filepath)
        return self.ratings