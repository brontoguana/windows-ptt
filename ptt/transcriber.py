import threading
import numpy as np
from faster_whisper import WhisperModel

from ptt.config import (
    WHISPER_MODEL_SIZE,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
    WHISPER_LANGUAGE,
    WHISPER_BEAM_SIZE,
)


class Transcriber:
    def __init__(self):
        self._model = None
        self._lock = threading.Lock()

    def load_model(self):
        self._model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )

    def transcribe(self, audio: np.ndarray) -> str:
        """Synchronous transcription. Thread-safe (uses a lock)."""
        if audio.size == 0:
            return ""
        with self._lock:
            segments, _info = self._model.transcribe(
                audio,
                language=WHISPER_LANGUAGE,
                beam_size=WHISPER_BEAM_SIZE,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=300),
            )
            text = " ".join(segment.text.strip() for segment in segments)
        return text.strip()

    def transcribe_async(self, audio: np.ndarray, callback):
        """Transcribe in a background thread, call callback(text) when done."""
        if audio.size == 0:
            callback("")
            return

        thread = threading.Thread(
            target=self._transcribe_worker,
            args=(audio, callback),
            daemon=True,
        )
        thread.start()

    def _transcribe_worker(self, audio: np.ndarray, callback):
        text = self.transcribe(audio)
        callback(text)
