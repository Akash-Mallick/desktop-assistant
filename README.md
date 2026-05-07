# AI Voice-Controlled Desktop Assistant

A fully offline-capable voice assistant for system automation and intelligent queries.

## Architecture

```
main.py
└── VoiceAssistant (core.py)
    ├── SpeechRecognizer (stt.py)   — Google STT via SpeechRecognition
    ├── TextToSpeech    (tts.py)    — pyttsx3 offline TTS
    ├── IntentClassifier (nlp.py)  — Rule-based + spaCy NLP
    ├── SkillRouter     (skills.py) — Intent → action dispatch
    └── CommandHistory  (history.py)— JSON persistence
```

## Quick Start

```bash
# 1. Clone / download the project
cd voice_assistant

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download the spaCy language model (optional but recommended)
python -m spacy download en_core_web_sm

# 5. Run
python main.py
```

## Supported Commands

| Category       | Example phrase                           |
|----------------|------------------------------------------|
| Open app       | "Hey Assistant, open Chrome"             |
| Close app      | "Hey Assistant, close Notepad"           |
| Web search     | "Hey Assistant, search for Python tips"  |
| Play music     | "Hey Assistant, play Bohemian Rhapsody"  |
| System info    | "Hey Assistant, what's my CPU usage?"    |
| File ops       | "Hey Assistant, create file notes.txt"   |
| Set reminder   | "Hey Assistant, remind me to call John in 5 minutes" |
| Time / date    | "Hey Assistant, what time is it?"        |
| Weather        | "Hey Assistant, weather in Delhi"        |
| Screenshot     | "Hey Assistant, take a screenshot"       |
| Clipboard      | "Hey Assistant, read clipboard"          |
| Volume         | "Hey Assistant, increase volume"         |

## Configuration

Edit `assistant/config.py` or set environment variables:

| Variable              | Default | Description                     |
|-----------------------|---------|---------------------------------|
| SR_ENERGY_THRESHOLD   | 4000    | Mic sensitivity                 |
| SR_DYNAMIC_ENERGY     | true    | Auto-adjust energy threshold    |
| TTS_RATE              | 175     | Speech rate (words per minute)  |
| TTS_VOICE_INDEX       | 0       | Voice index (0 = system default)|
| NLP_MODEL             | en_core_web_sm | spaCy model             |
| CONFIDENCE_THRESHOLD  | 0.55    | Minimum intent confidence       |
| DEBUG                 | false   | Verbose logging                 |

## Adding New Skills

1. Add a new intent rule in `assistant/nlp.py` → `INTENT_RULES`
2. Write a handler function `skill_my_intent(entities, assistant) -> str` in `assistant/skills.py`
3. Register it in `SkillRouter.__init__` inside `skills.py`

## Dependencies

- `SpeechRecognition` — audio capture + Google STT
- `pyttsx3` — cross-platform offline TTS
- `PyAudio` — microphone access
- `spaCy` — named entity recognition (optional)
- `psutil` — system metrics
- `pyautogui` — screenshot capture
- `pyperclip` — clipboard access
