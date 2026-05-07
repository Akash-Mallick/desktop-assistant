"""
Command History — persists each interaction to a JSON log file.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


class CommandHistory:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self._records = self._load()

    def add(self, raw: str, intent: str, entities: Dict[str, Any], response: str) -> None:
        record = {
            "timestamp": datetime.now().isoformat(),
            "raw": raw,
            "intent": intent,
            "entities": {k: v for k, v in entities.items() if k != "raw"},
            "response": response,
        }
        self._records.append(record)
        self._save()

    def recent(self, n: int = 10):
        return self._records[-n:]

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning("History file corrupted — starting fresh.")
        return []

    def _save(self):
        try:
            with open(self.filepath, "w") as f:
                json.dump(self._records, f, indent=2)
        except IOError as e:
            logger.error(f"Could not save history: {e}")
