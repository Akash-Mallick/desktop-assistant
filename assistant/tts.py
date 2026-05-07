"""
Text-to-Speech module — wraps pyttsx3 for offline, cross-platform TTS.
"""

import logging
import threading
import pyttsx3
from .config import Config

logger = logging.getLogger(__name__)


class TextToSpeech:
    """
    Thread-safe TTS wrapper around pyttsx3.

    pyttsx3 engines are not always safe to share across threads, so we
    initialise a fresh engine per call in _say_worker when running
    threaded, or use the persistent engine for synchronous calls.
    """

    def __init__(self, config: Config):
        self.config = config
        self._lock = threading.Lock()
        self._engine = self._build_engine()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def say(self, text: str, block: bool = True) -> None:
        """
        Speak `text`.

        Args:
            text:  The string to speak.
            block: If True (default), block until speech finishes.
                   If False, speak in a background thread.
        """
        if block:
            self._speak(text)
        else:
            t = threading.Thread(target=self._speak, args=(text,), daemon=True)
            t.start()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _speak(self, text: str) -> None:
        with self._lock:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            except RuntimeError:
                # Engine state can corrupt after long sessions — rebuild it
                logger.warning("TTS engine reset required.")
                self._engine = self._build_engine()
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception as e:
                logger.error(f"TTS error: {e}")

    def _build_engine(self) -> pyttsx3.Engine:
        engine = pyttsx3.init()
        engine.setProperty("rate", self.config.tts_rate)
        engine.setProperty("volume", self.config.tts_volume)

        voices = engine.getProperty("voices")
        if voices and self.config.tts_voice_index < len(voices):
            engine.setProperty("voice", voices[self.config.tts_voice_index].id)

        return engine
