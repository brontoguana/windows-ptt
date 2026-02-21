import numpy as np
import sounddevice as sd
import threading
from collections import deque

from ptt.config import SAMPLE_RATE, CHANNELS, DTYPE, BLOCK_SIZE


class AudioRecorder:
    def __init__(self):
        self._buffer = deque()
        self._is_recording = False
        self._lock = threading.Lock()
        self._stream = None
        self._healthy = False

    def init_stream(self):
        """Open the audio stream. Raises RuntimeError if no mic found."""
        self._close_stream()

        try:
            device_info = sd.query_devices(kind='input')
            print(f"Using audio device: {device_info['name']}")
        except Exception:
            self._healthy = False
            raise RuntimeError(
                "No audio input device found. Please connect a microphone."
            )

        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                blocksize=BLOCK_SIZE,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._healthy = True
        except Exception as e:
            self._healthy = False
            raise RuntimeError(f"Failed to open audio stream: {e}")

    def try_reinit(self) -> bool:
        """Try to reinitialize the stream. Returns True if successful."""
        try:
            self.init_stream()
            return True
        except RuntimeError:
            return False

    @property
    def is_healthy(self) -> bool:
        """Check if the audio stream is active and working."""
        if not self._healthy or self._stream is None:
            return False
        try:
            return self._stream.active
        except Exception:
            self._healthy = False
            return False

    def _close_stream(self):
        """Safely close any existing stream."""
        if self._stream is not None:
            try:
                self._stream.stop()
            except Exception:
                pass
            try:
                self._stream.close()
            except Exception:
                pass
            self._stream = None
            self._healthy = False

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            # Stream error (device disconnected, etc.)
            self._healthy = False
        if self._is_recording:
            self._buffer.append(indata.copy())

    def start_recording(self):
        with self._lock:
            self._buffer.clear()
            self._is_recording = True

    def get_snapshot(self) -> np.ndarray:
        """Return a copy of audio recorded so far WITHOUT stopping recording."""
        with self._lock:
            if not self._buffer:
                return np.array([], dtype=np.float32)
            audio = np.concatenate(list(self._buffer), axis=0)
        return np.squeeze(audio)

    def stop_recording(self) -> np.ndarray:
        with self._lock:
            self._is_recording = False
            if not self._buffer:
                return np.array([], dtype=np.float32)
            audio = np.concatenate(list(self._buffer), axis=0)
            self._buffer.clear()
        return np.squeeze(audio)

    def shutdown(self):
        self._close_stream()
