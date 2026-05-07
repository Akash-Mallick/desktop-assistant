"""
NLP Intent Classifier.

Architecture (two-stage):
  1. Rule-based matcher  — fast, zero-shot, covers known intent patterns.
  2. spaCy NLP pipeline  — entity extraction + POS for slot filling.

Returns (intent: str, entities: dict, confidence: float).

Supported intents
-----------------
  open_app         — "open Chrome", "launch Spotify"
  close_app        — "close notepad", "kill Firefox"
  web_search       — "search for Python tutorials"
  play_music       — "play some jazz", "play Bohemian Rhapsody"
  system_info      — "what's my CPU usage", "battery status"
  file_operation   — "create file notes.txt", "delete report.docx"
  set_reminder     — "remind me to call John at 3 pm"
  get_time         — "what time is it", "what's today's date"
  get_weather      — "what's the weather in Delhi"
  take_screenshot  — "take a screenshot"
  clipboard_read   — "read clipboard"
  clipboard_write  — "copy this to clipboard: …"
  volume_control   — "increase volume", "set volume to 50"
  unknown          — fallback
"""

import re
import logging
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent rule definitions
# ---------------------------------------------------------------------------
# Each rule: (intent_name, [trigger_patterns], confidence_score)
# Patterns are checked via `re.search` on lowercased input.
# ---------------------------------------------------------------------------

INTENT_RULES = [
    ("open_app",        [r"\b(open|launch|start|run)\b"],            0.90),
    ("close_app",       [r"\b(close|quit|exit|kill|terminate)\b"],   0.90),
    ("web_search",      [r"\b(search|google|look up|find info)\b"],  0.88),
    ("play_music",      [r"\bplay\b"],                                0.85),
    ("system_info",     [r"\b(cpu|ram|memory|battery|disk|usage|performance)\b"], 0.87),
    ("file_operation",  [r"\b(create|delete|move|copy|rename)\b.*\b(file|folder|directory)\b"], 0.86),
    ("set_reminder",    [r"\b(remind|reminder|alert)\b"],             0.90),
    ("get_time",        [r"\b(time|clock|date|today|day)\b"],         0.88),
    ("get_weather",     [r"\bweather\b"],                             0.90),
    ("take_screenshot", [r"\b(screenshot|screen capture|snap)\b"],   0.95),
    ("clipboard_read",  [r"\bread.*(clipboard|copied)\b"],            0.88),
    ("clipboard_write", [r"\b(copy|write|put).*clipboard\b"],         0.85),
    ("volume_control",  [r"\b(volume|mute|unmute|louder|quieter|sound)\b"], 0.88),
]


class IntentClassifier:
    """Lightweight hybrid NLP pipeline."""

    def __init__(self, config):
        self.config = config
        self._nlp = self._load_spacy()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(self, text: str) -> Tuple[str, Dict[str, Any], float]:
        """
        Classify `text` into an intent with entity slots.

        Returns:
            (intent, entities, confidence)
        """
        text_lower = text.lower().strip()
        intent, confidence = self._rule_match(text_lower)
        entities = self._extract_entities(text, intent)
        return intent, entities, confidence

    # ------------------------------------------------------------------
    # Rule-based matching
    # ------------------------------------------------------------------

    def _rule_match(self, text: str) -> Tuple[str, float]:
        best_intent, best_conf = "unknown", 0.30

        for intent_name, patterns, conf in INTENT_RULES:
            if any(re.search(p, text) for p in patterns):
                if conf > best_conf:
                    best_intent, best_conf = intent_name, conf

        return best_intent, best_conf

    # ------------------------------------------------------------------
    # Entity extraction
    # ------------------------------------------------------------------

    def _extract_entities(self, text: str, intent: str) -> Dict[str, Any]:
        entities: Dict[str, Any] = {"raw": text}

        if self._nlp:
            doc = self._nlp(text)
            for ent in doc.ents:
                entities[ent.label_.lower()] = ent.text

        # Intent-specific slot extraction via regex
        slot_extractors = {
            "open_app":        self._slot_app_name,
            "close_app":       self._slot_app_name,
            "web_search":      self._slot_search_query,
            "play_music":      self._slot_music_query,
            "get_weather":     self._slot_location,
            "set_reminder":    self._slot_reminder,
            "volume_control":  self._slot_volume,
            "file_operation":  self._slot_filename,
        }

        extractor = slot_extractors.get(intent)
        if extractor:
            extra = extractor(text)
            entities.update(extra)

        return entities

    # ------------------------------------------------------------------
    # Slot extractors
    # ------------------------------------------------------------------

    @staticmethod
    def _slot_app_name(text: str) -> Dict:
        m = re.search(r"\b(?:open|launch|start|run|close|quit|kill|exit)\s+(\w[\w\s]*)", text, re.I)
        return {"app_name": m.group(1).strip()} if m else {}

    @staticmethod
    def _slot_search_query(text: str) -> Dict:
        m = re.search(r"\b(?:search|google|look up|find info(?:\s+on)?)\s+(?:for\s+)?(.+)", text, re.I)
        return {"query": m.group(1).strip()} if m else {}

    @staticmethod
    def _slot_music_query(text: str) -> Dict:
        m = re.search(r"\bplay\s+(.+)", text, re.I)
        return {"track": m.group(1).strip()} if m else {}

    @staticmethod
    def _slot_location(text: str) -> Dict:
        m = re.search(r"\bweather\s+(?:in|at|for)\s+(.+)", text, re.I)
        return {"location": m.group(1).strip()} if m else {}

    @staticmethod
    def _slot_reminder(text: str) -> Dict:
        m = re.search(r"\bremind(?:\s+me)?\s+(?:to\s+)?(.+?)(?:\s+at\s+(.+))?$", text, re.I)
        if m:
            return {"task": m.group(1).strip(), "time": (m.group(2) or "").strip() or None}
        return {}

    @staticmethod
    def _slot_volume(text: str) -> Dict:
        m = re.search(r"\b(?:set\s+volume\s+to|volume)\s+(\d+)", text, re.I)
        if m:
            return {"level": int(m.group(1))}
        if re.search(r"\b(increase|up|louder)\b", text, re.I):
            return {"direction": "up"}
        if re.search(r"\b(decrease|down|quieter|lower)\b", text, re.I):
            return {"direction": "down"}
        if re.search(r"\bmute\b", text, re.I):
            return {"action": "mute"}
        return {}

    @staticmethod
    def _slot_filename(text: str) -> Dict:
        m = re.search(r"\b(?:file|folder)\s+['\"]?(\S+)['\"]?", text, re.I)
        return {"filename": m.group(1)} if m else {}

    # ------------------------------------------------------------------
    # spaCy loader (optional dependency)
    # ------------------------------------------------------------------

    def _load_spacy(self):
        try:
            import spacy
            nlp = spacy.load(self.config.nlp_model)
            logger.info(f"spaCy model '{self.config.nlp_model}' loaded.")
            return nlp
        except ImportError:
            logger.warning("spaCy not installed — entity extraction limited to regex.")
        except OSError:
            logger.warning(
                f"spaCy model '{self.config.nlp_model}' not found. "
                f"Run: python -m spacy download {self.config.nlp_model}"
            )
        return None
