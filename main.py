"""
AI Voice-Controlled Desktop Assistant
Entry point — orchestrates speech recognition, NLP, and TTS.
"""

import logging
import sys
from assistant.core import VoiceAssistant
from assistant.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("assistant.log"),
    ],
)

logger = logging.getLogger(__name__)


def main():
    logger.info("Starting AI Voice-Controlled Desktop Assistant...")
    config = Config()
    assistant = VoiceAssistant(config)

    print("\n" + "=" * 55)
    print("  AI Voice-Controlled Desktop Assistant")
    print("  Say 'Hey Assistant' to wake, 'Exit' to quit")
    print("=" * 55 + "\n")

    try:
        assistant.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Shutting down.")
        assistant.speak("Goodbye! Have a great day.")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
