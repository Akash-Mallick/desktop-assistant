import logging
import os
import re
from typing import List, Dict

logger = logging.getLogger(__name__)

# Suppress the gRPC fork warnings from pyttsx3 + Gemini running together
os.environ.setdefault("GRPC_ENABLE_FORK_SUPPORT", "false")
os.environ.setdefault("GRPC_POLL_STRATEGY", "epoll1")

SYSTEM_PROMPT = """You are a helpful voice assistant named Assistant running on the user's desktop.

Rules you must always follow:
- Respond in 2 to 4 complete sentences. Never truncate mid-sentence.
- Use plain spoken English only — no markdown, no bullet points, no asterisks, no numbering.
- Never say "As an AI" or "I am a language model".
- For system tasks (open apps, files, volume), say: just say Hey Assistant followed by your command.
- Be friendly, accurate, and concise.
- Always finish your last sentence with a full stop.
"""


class GeminiAI:
    """
    Wrapper around the new google-genai SDK with rolling conversation memory.
    Falls back gracefully to the deprecated google-generativeai SDK if needed.
    """

    MAX_HISTORY_TURNS = 6

    def __init__(self, api_key: str | None = None, model: str = "gemini-3-flash-preview"):
        self._api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self._model_name = model
        self._history: List[Dict[str, str]] = []
        self._chat = None
        self._sdk = None          # "new" | "legacy" | None
        self._initialised = False

        if not self._api_key:
            logger.warning(
                "GEMINI_API_KEY not set. AI fallback disabled. "
                "Get a free key at https://aistudio.google.com/app/apikey"
            )
        else:
            self._initialised = self._setup()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        return self._initialised

    def ask(self, user_text: str) -> str:
        if not self._initialised:
            return (
                "The AI brain is not configured. "
                "Please set your GEMINI_API_KEY in your dot env file."
            )
        try:
            if self._sdk == "new":
                reply = self._ask_new_sdk(user_text)
            else:
                reply = self._ask_legacy_sdk(user_text)

            reply = self._clean_for_tts(reply)
            self._push_history(user_text, reply)
            logger.info(f"[Gemini] Q: {user_text[:60]} | A: {reply[:100]}")
            return reply

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return "I had trouble reaching the AI service. Please try again in a moment."

    def clear_history(self) -> None:
        self._history.clear()
        if self._sdk == "new" and self._chat:
            self._chat = self._new_chat_session()
        elif self._sdk == "legacy" and hasattr(self, "_legacy_model"):
            self._chat = self._legacy_model.start_chat(history=[])
        logger.info("Gemini conversation history cleared.")

    # ------------------------------------------------------------------
    # Setup — tries new SDK first, falls back to legacy
    # ------------------------------------------------------------------

    def _setup(self) -> bool:
        if self._try_new_sdk():
            return True
        if self._try_legacy_sdk():
            return True
        return False

    def _try_new_sdk(self) -> bool:
        try:
            from google import genai
            from google.genai import types

            self._genai = genai
            self._types = types
            self._client = genai.Client(api_key=self._api_key)
            self._chat = self._new_chat_session()
            self._sdk = "new"
            logger.info(f"Gemini AI ready via google-genai SDK ({self._model_name}).")
            return True
        except ImportError:
            logger.debug("google-genai not installed, trying legacy SDK.")
        except Exception as e:
            logger.debug(f"New SDK setup failed: {e}")
        return False

    def _try_legacy_sdk(self) -> bool:
        try:
            import warnings
            import google.generativeai as genai

            # Suppress the deprecation FutureWarning
            warnings.filterwarnings("ignore", category=FutureWarning, module="google")

            genai.configure(api_key=self._api_key)
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_output_tokens": 300,   # enough for 3-4 full sentences
            }
            self._legacy_model = genai.GenerativeModel(
                model_name=self._model_name,
                generation_config=generation_config,
                system_instruction=SYSTEM_PROMPT,
            )
            self._chat = self._legacy_model.start_chat(history=[])
            self._sdk = "legacy"
            logger.info(f"Gemini AI ready via legacy SDK ({self._model_name}).")
            return True
        except ImportError:
            logger.error(
                "No Gemini SDK found. Run: uv add google-genai"
            )
        except Exception as e:
            logger.error(f"Legacy SDK setup failed: {e}")
        return False

    # ------------------------------------------------------------------
    # Per-SDK query methods
    # ------------------------------------------------------------------

    def _ask_new_sdk(self, text: str) -> str:
        from google.genai import types

        # Rebuild history for stateless new SDK
        history = []
        for turn in self._history[-self.MAX_HISTORY_TURNS:]:
            history.append(types.Content(role="user",  parts=[types.Part(text=turn["user"])]))
            history.append(types.Content(role="model", parts=[types.Part(text=turn["assistant"])]))

        # Re-create chat with current history
        chat = self._client.chats.create(
            model=self._model_name,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
                max_output_tokens=300,
            ),
            history=history,
        )
        response = chat.send_message(text)
        return response.text.strip()

    def _ask_legacy_sdk(self, text: str) -> str:
        response = self._chat.send_message(text)
        return response.text.strip()

    def _new_chat_session(self):
        """Create a fresh chat session (new SDK)."""
        return self._client.chats.create(model=self._model_name)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _push_history(self, user: str, assistant: str) -> None:
        self._history.append({"user": user, "assistant": assistant})
        if len(self._history) > self.MAX_HISTORY_TURNS:
            self._history.pop(0)

    def _build_messages(self, user_text: str) -> List[Dict]:
        msgs = []
        for turn in self._history[-self.MAX_HISTORY_TURNS:]:
            msgs.append({"role": "user",  "parts": [turn["user"]]})
            msgs.append({"role": "model", "parts": [turn["assistant"]]})
        msgs.append({"role": "user", "parts": [user_text]})
        return msgs

    @staticmethod
    def _clean_for_tts(text: str) -> str:
        """Strip markdown symbols that sound bad when spoken aloud."""
        text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)  # bold / italic
        text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)        # inline code
        text = re.sub(r"#+\s*", "", text)                     # headers
        text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)       # links
        text = re.sub(r"[-*•]\s+", "", text)                  # bullet points
        text = re.sub(r"\n+", " ", text).strip()
        return text