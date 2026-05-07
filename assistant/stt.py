"""
Speech-to-Text module — wraps the SpeechRecognition library.

Two listening modes:
  passive  — low-overhead ambient capture for wake-word detection
  command  — focused, higher-timeout capture for full commands
"""

import logging
import speech_recognition as sr
from .config import Config

logger = logging.getLogger(__name__)


class SpeechRecognizer:
    """Wraps SpeechRecognition with Google STT backend."""

    def __init__(self, config: Config):
        self.config = config
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = config.sr_energy_threshold
        self.recognizer.dynamic_energy_threshold = config.sr_dynamic_energy
        self.recognizer.pause_threshold = config.sr_pause_threshold
        self.mic = sr.Microphone()

        # Calibrate ambient noise once at startup
        logger.info("Calibrating microphone for ambient noise (2 s)…")
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
        logger.info("Microphone ready.")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def listen_passive(self) -> str | None:
        """
        Short, non-blocking listen for wake word detection.
        Returns transcribed text or None on failure.
        """
        return self._capture(timeout=self.config.sr_timeout, phrase_limit=3)

    def listen_command(self) -> str | None:
        """
        Longer listen window for full command utterances.
        Returns transcribed text or None on failure.
        """
        return self._capture(
            timeout=self.config.sr_timeout,
            phrase_limit=self.config.sr_phrase_limit,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _capture(self, timeout: int, phrase_limit: int) -> str | None:
        try:
            with self.mic as source:
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit,
                )
            text = self.recognizer.recognize_google(audio)
            return text.strip()

        except sr.WaitTimeoutError:
            logger.debug("Microphone timeout — no speech detected.")
        except sr.UnknownValueError:
            logger.debug("Could not understand audio.")
        except sr.RequestError as e:
            logger.error(f"Google STT service error: {e}")
        except Exception as e:
            logger.exception(f"Unexpected STT error: {e}")

        return None
