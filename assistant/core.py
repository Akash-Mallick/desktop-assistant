"""
Core orchestrator — ties together STT, TTS, NLP, skill handlers, and Gemini AI.
"""

import logging
import time
from .config import Config
from .stt import SpeechRecognizer
from .tts import TextToSpeech
from .nlp import IntentClassifier
from .skills import SkillRouter
from .history import CommandHistory
from .gemini import GeminiAI

logger = logging.getLogger(__name__)


class VoiceAssistant:
    """
    Main controller that runs the listen → understand → act → respond loop.

    Flow:
        1. Listen for audio via microphone
        2. Detect wake word; if found, enter command mode
        3. Transcribe the command utterance
        4. Classify intent + extract entities via NLP
        5a. If intent matches a skill → run the skill handler
        5b. If intent is 'unknown' or low confidence → ask Gemini AI
        6. Speak the response via TTS
        7. Log to history; loop back to step 1
    """

    def __init__(self, config: Config):
        self.config = config
        self.stt = SpeechRecognizer(config)
        self.tts = TextToSpeech(config)
        self.nlp = IntentClassifier(config)
        self.router = SkillRouter(self)
        self.history = CommandHistory(config.history_file)
        self.ai = GeminiAI(
            api_key=config.gemini_api_key,
            model=config.gemini_model,
        )
        self._running = False

        if self.ai.available:
            logger.info("Gemini AI fallback: ENABLED")
        else:
            logger.warning("Gemini AI fallback: DISABLED (no API key)")

    def speak(self, text: str) -> None:
        logger.info(f"[TTS] {text}")
        self.tts.say(text)

    def run(self) -> None:
        self._running = True
        greeting = "Assistant ready."
        if self.ai.available:
            greeting += " Gemini AI is connected. Ask me anything."
        else:
            greeting += " Say 'Hey Assistant' to begin."
        self.speak(greeting)

        while self._running:
            try:
                self._listen_for_wake_word()
            except Exception as e:
                logger.error(f"Loop error: {e}")
                time.sleep(1)

    def stop(self) -> None:
        self._running = False

    def _listen_for_wake_word(self) -> None:
        audio_text = self.stt.listen_passive()
        if audio_text is None:
            return
        if self._is_wake_word(audio_text):
            logger.info("Wake word detected.")
            self.speak("Yes, listening.")
            self._handle_command()

    def _is_wake_word(self, text: str) -> bool:
        text_lower = text.lower().strip()
        return any(w in text_lower for w in self.config.wake_words)

    def _handle_command(self) -> None:
        raw = self.stt.listen_command()
        if raw is None:
            self.speak("I didn't catch that. Please try again.")
            return

        logger.info(f"[STT] {raw}")

        if any(kw in raw.lower() for kw in ("exit", "quit", "goodbye", "shut down")):
            self.speak("Shutting down. Goodbye!")
            self.stop()
            return

        if "clear history" in raw.lower() or "forget conversation" in raw.lower():
            self.ai.clear_history()
            self.speak("Conversation context cleared.")
            return

        intent, entities, confidence = self.nlp.classify(raw)
        logger.info(f"[NLP] intent={intent}, entities={entities}, conf={confidence:.2f}")

        if intent != "unknown" and confidence >= self.config.confidence_threshold:
            logger.info(f"[Router] Matched skill: {intent}")
            response = self.router.handle(intent, entities, raw)
        else:
            logger.info(f"[Router] No skill match → Gemini (conf={confidence:.2f})")
            response = self._ask_gemini(raw)

        self.speak(response)
        self.history.add(raw, intent, entities, response)

    def _ask_gemini(self, text: str) -> str:
        if self.ai.available:
            logger.info(f"[Gemini] Querying: {text}")
            return self.ai.ask(text)
        return (
            "I didn't understand that command, and the AI brain isn't configured. "
            "Set your GEMINI_API_KEY to enable smart responses."
        )
