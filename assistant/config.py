"""
Configuration settings for the Voice Assistant.
Edit values here or set them in a .env file in the project root.
"""

import os
from dataclasses import dataclass, field
from typing import List

# ── Load .env FIRST, before any os.getenv() calls ──────────────────────────
# This must happen at module import time, before the dataclass fields below
# are evaluated — otherwise os.getenv() reads stale environment values.
try:
    from dotenv import load_dotenv
    load_dotenv()  # looks for .env in cwd and parent directories
except ImportError:
    pass  # python-dotenv not installed; rely on shell env vars


@dataclass
class Config:
    # Wake word(s) — any phrase in this list activates listening
    wake_words: List[str] = field(
        default_factory=lambda: ["hey assistant", "ok assistant", "hello assistant"]
    )

    # Speech Recognition
    sr_energy_threshold: int = int(os.getenv("SR_ENERGY_THRESHOLD", "4000"))
    sr_dynamic_energy: bool = os.getenv("SR_DYNAMIC_ENERGY", "true").lower() == "true"
    sr_pause_threshold: float = float(os.getenv("SR_PAUSE_THRESHOLD", "1.2"))
    sr_timeout: int = int(os.getenv("SR_TIMEOUT", "8"))
    sr_phrase_limit: int = int(os.getenv("SR_PHRASE_LIMIT", "15"))

    # Text-to-Speech
    tts_rate: int = int(os.getenv("TTS_RATE", "175"))
    tts_volume: float = float(os.getenv("TTS_VOLUME", "1.0"))
    tts_voice_index: int = int(os.getenv("TTS_VOICE_INDEX", "0"))

    # NLP / Intent Classification
    nlp_model: str = os.getenv("NLP_MODEL", "en_core_web_sm")
    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.55"))

    # Gemini AI
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    # General
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    history_file: str = os.getenv("HISTORY_FILE", "command_history.json")