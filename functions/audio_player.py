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
            target_fs: int,
            calib_gain: list[float] | None = None):
        """Initialize AudioPlayer with audio device settings and optional calibration gain.

        Args:
            device_id: Audio device index for playback
            blocksize: Audio buffer size in samples
            target_fs: Target sampling rate in Hz (librosa will resample if needed)
            calib_gain: Per-channel amplitude gain [left, right] from calibration.
                        Defaults to [1.0, 1.0] (no adjustment).
        """
        self._device_id = device_id
        self._blocksize = blocksize
        self._target_fs = target_fs
        self._calib_gain = np.array(calib_gain if calib_gain is not None else [1.0, 1.0])

        self._idx_start = None
        self._audio = None
        self._done = None
        self._loop = None

    @property
    def calib_gain(self) -> np.ndarray:
        """Get per-channel calibration gain [left, right]."""
        return self._calib_gain

    @property
    def blocksize(self) -> int:
        """Get audio buffer blocksize in samples."""
        return self._blocksize

    @property
    def fs(self) -> int:
        """Get audio sampling frequency in Hz."""
        return self._target_fs

    def _callback(self, outdata, frames, time, status):
        """Audio stream callback for playback."""
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
        """Play audio stimulus with calibration gain applied.

        Args:
            filepath: Path to audio file to play
        """
        audio = librosa.load(filepath, sr=self._target_fs, mono=False)[0]
        if audio.ndim == 1:
            audio = np.stack([audio, audio])  # mono → stereo duplication

        self._audio = audio.T * self._calib_gain  # shape: (samples, 2), gain applied per channel

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
            target_fs: int,
            calib_gain: list[float] | None = None):
        """Initialize AudioPlayer with rating slider and calibration gain.

        Args:
            rating_slider: RatingSlider instance for recording ratings during playback
            device_id: Audio device index for playback
            blocksize: Audio buffer size in samples
            target_fs: Target sampling rate in Hz
            calib_gain: Per-channel amplitude gain [left, right] from calibration.
        """
        super().__init__(device_id, blocksize, target_fs, calib_gain)
        self._slider = rating_slider
        self.ratings = None

    def _callback(self, outdata, frames, time, status):
        """Extends parent callback with slider rating collection."""
        super()._callback(outdata, frames, time, status)
        self.ratings.append(self._slider.value)

    async def play_stimulus_and_record_ratings(self, filepath: str) -> list[float]:
        """Play audio stimulus and record slider ratings throughout playback.

        Args:
            filepath: Path to audio file to play

        Returns:
            List of slider ratings recorded during playback
        """
        self.ratings = []
        await super().play_stimulus(filepath)
        return self.ratings