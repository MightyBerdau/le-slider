import asyncio
import sounddevice as sd
import soundfile as sf

from .gui import RatingSlider

class AudioPlayer:
    def __init__(
            self,
            rating_slider: RatingSlider,
            device_id: int,
            blocksize: int):
        self._slider = rating_slider
        self._device_id = device_id
        self._blocksize = blocksize

        # Initialized in self.play_stimulus_and_record_ratings()
        self._idx_start = None # 0
        self.ratings = None # []
        self._audio = None
        self._fs = None
        self._done = None # asyncio.Event()
        self._loop = None # asyncio.get_event_loop()

    @property
    def blocksize(self) -> int:
        return self._blocksize
    
    @property
    def fs(self) -> int:
        return self._fs

    def _callback(self, outdata, frames, time, status):
        chunk = self._audio[self._idx_start : self._idx_start + frames]
        
        if len(chunk) < frames:
            outdata[:len(chunk)] = chunk
            outdata[len(chunk):] = 0
            self._loop.call_soon_threadsafe(self._done.set)
        else:
            outdata[:] = chunk
        
        self.ratings.append(self._slider.value)
        self._idx_start += frames

    async def play_stimulus_and_record_ratings(self, filepath: str):
        self._audio, self._fs = sf.read(filepath)
        
        self._done = asyncio.Event()
        self._loop = asyncio.get_event_loop()
        self._idx_start = 0
        self.ratings = []
        
        with sd.OutputStream(
            callback=self._callback,
            samplerate=self._fs,
            channels=self._audio.shape[1],
            blocksize=self._blocksize,
            device=self._device_id,
        ):
            await self._done.wait()
        return self.ratings