"""
Skill Router — dispatches classified intents to handler functions.

Each skill is a plain function: handler(entities, assistant) -> str
The returned string is spoken by the TTS engine.
"""

import logging
import os
import subprocess
import platform
import datetime
import webbrowser
import urllib.parse
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from .core import VoiceAssistant

logger = logging.getLogger(__name__)

OS = platform.system()  # "Windows" | "Darwin" | "Linux"


class SkillRouter:
    """Maps intent names to handler callables."""

    def __init__(self, assistant: "VoiceAssistant"):
        self.assistant = assistant
        self._registry = {
            "open_app":        skill_open_app,
            "close_app":       skill_close_app,
            "web_search":      skill_web_search,
            "play_music":      skill_play_music,
            "system_info":     skill_system_info,
            "file_operation":  skill_file_operation,
            "set_reminder":    skill_set_reminder,
            "get_time":        skill_get_time,
            "get_weather":     skill_get_weather,
            "take_screenshot": skill_take_screenshot,
            "clipboard_read":  skill_clipboard_read,
            "clipboard_write": skill_clipboard_write,
            "volume_control":  skill_volume_control,
            "unknown":         skill_unknown,
        }

    def handle(self, intent: str, entities: Dict[str, Any], raw: str) -> str:
        handler = self._registry.get(intent, skill_unknown)
        try:
            return handler(entities, self.assistant)
        except Exception as e:
            logger.error(f"Skill '{intent}' raised: {e}")
            return f"Sorry, I ran into a problem handling your {intent.replace('_', ' ')} request."


# ---------------------------------------------------------------------------
# Individual skill handlers
# ---------------------------------------------------------------------------

# Common spoken name → exact macOS .app name
APP_ALIASES = {
    "chrome":         "Google Chrome",
    "google chrome":  "Google Chrome",
    "safari":         "Safari",
    "firefox":        "Firefox",
    "edge":           "Microsoft Edge",
    "terminal":       "Terminal",
    "iterm":          "iTerm",
    "vscode":         "Visual Studio Code",
    "vs code":        "Visual Studio Code",
    "code":           "Visual Studio Code",
    "notes":          "Notes",
    "mail":           "Mail",
    "calendar":       "Calendar",
    "finder":         "Finder",
    "spotify":        "Spotify",
    "slack":          "Slack",
    "zoom":           "Zoom",
    "word":           "Microsoft Word",
    "excel":          "Microsoft Excel",
    "powerpoint":     "Microsoft PowerPoint",
    "calculator":     "Calculator",
    "preview":        "Preview",
    "photos":         "Photos",
    "music":          "Music",
    "vlc":            "VLC",
    "xcode":          "Xcode",
    "pycharm":        "PyCharm",
}


def _resolve_app_name(spoken: str) -> str:
    """Map spoken app name to its real system name via alias table."""
    return APP_ALIASES.get(spoken.lower().strip(), spoken)


def skill_open_app(entities: dict, _) -> str:
    app = entities.get("app_name", "")
    if not app:
        return "Which application would you like me to open?"

    resolved = _resolve_app_name(app)
    try:
        if OS == "Windows":
            os.startfile(resolved)
        elif OS == "Darwin":
            result = subprocess.run(
                ["open", "-a", resolved],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                logger.error(result.stderr.strip())
                return f"I couldn't find {resolved}. Check that it's installed in your Applications folder."
        else:
            subprocess.Popen([resolved.lower()])
        return f"Opening {resolved}."
    except Exception as e:
        logger.error(e)
        return f"I couldn't open {app}. Make sure it's installed."


def skill_close_app(entities: dict, _) -> str:
    app = entities.get("app_name", "")
    if not app:
        return "Which application should I close?"
    try:
        if OS == "Windows":
            subprocess.call(["taskkill", "/f", "/im", f"{app}.exe"])
        else:
            subprocess.call(["pkill", "-i", app])
        return f"Closed {app}."
    except Exception as e:
        logger.error(e)
        return f"Could not close {app}."


def skill_web_search(entities: dict, _) -> str:
    query = entities.get("query", entities.get("raw", ""))
    if not query:
        return "What would you like me to search for?"
    url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
    webbrowser.open(url)
    return f"Searching the web for {query}."


def skill_play_music(entities: dict, _) -> str:
    track = entities.get("track", "")
    if not track:
        return "What would you like to play?"
    query = urllib.parse.quote(track)
    webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
    return f"Looking up {track} on YouTube."


def skill_system_info(entities: dict, _) -> str:
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        battery = psutil.sensors_battery()
        parts = [
            f"CPU is at {cpu:.0f} percent.",
            f"RAM usage is {ram.percent:.0f} percent, "
            f"{ram.available // (1024**3)} gigabytes available.",
        ]
        if battery:
            status = "charging" if battery.power_plugged else "on battery"
            parts.append(f"Battery is at {battery.percent:.0f} percent and {status}.")
        return " ".join(parts)
    except ImportError:
        return "psutil is not installed. Run: pip install psutil"


def skill_file_operation(entities: dict, _) -> str:
    raw = entities.get("raw", "").lower()
    filename = entities.get("filename", "")
    if not filename:
        return "Please specify a file name."
    try:
        if "create" in raw:
            with open(filename, "w") as f:
                f.write("")
            return f"Created file {filename}."
        elif "delete" in raw:
            os.remove(filename)
            return f"Deleted {filename}."
        else:
            return f"I can create or delete files. What would you like to do with {filename}?"
    except Exception as e:
        logger.error(e)
        return f"File operation failed: {e}"


def skill_set_reminder(entities: dict, assistant) -> str:
    task = entities.get("task", "")
    time_str = entities.get("time", "")
    if not task:
        return "What would you like me to remind you about?"
    # Simple in-process reminder via threading
    import threading
    delay = _parse_time_offset(time_str)
    if delay > 0:
        def _remind():
            import time
            time.sleep(delay)
            assistant.speak(f"Reminder: {task}")
        threading.Thread(target=_remind, daemon=True).start()
        return f"Reminder set for '{task}' in {delay // 60} minutes."
    return f"Reminder noted for '{task}'. I'll remind you soon."


def skill_get_time(entities: dict, _) -> str:
    now = datetime.datetime.now()
    return (
        f"It is {now.strftime('%I:%M %p')} on "
        f"{now.strftime('%A, %B %d, %Y')}."
    )


def skill_get_weather(entities: dict, _) -> str:
    location = entities.get("location", "your location")
    url = f"https://wttr.in/{urllib.parse.quote(location)}?format=3"
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=5) as resp:
            result = resp.read().decode().strip()
        return result if result else f"Could not fetch weather for {location}."
    except Exception as e:
        logger.error(e)
        webbrowser.open(f"https://www.google.com/search?q=weather+{urllib.parse.quote(location)}")
        return f"Opening weather for {location} in your browser."


def skill_take_screenshot(entities: dict, _) -> str:
    try:
        import pyautogui
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(os.path.expanduser("~"), f"screenshot_{ts}.png")
        pyautogui.screenshot(path)
        return f"Screenshot saved to {path}."
    except ImportError:
        return "pyautogui is not installed. Run: pip install pyautogui"
    except Exception as e:
        return f"Screenshot failed: {e}"


def skill_clipboard_read(entities: dict, _) -> str:
    try:
        import pyperclip
        content = pyperclip.paste()
        return f"Clipboard contains: {content[:200]}" if content else "Clipboard is empty."
    except ImportError:
        return "pyperclip is not installed. Run: pip install pyperclip"


def skill_clipboard_write(entities: dict, _) -> str:
    raw = entities.get("raw", "")
    m_content = raw.split("clipboard", 1)
    content = m_content[-1].strip(" :") if len(m_content) > 1 else ""
    if not content:
        return "What should I copy to the clipboard?"
    try:
        import pyperclip
        pyperclip.copy(content)
        return "Copied to clipboard."
    except ImportError:
        return "pyperclip is not installed. Run: pip install pyperclip"


def skill_volume_control(entities: dict, _) -> str:
    action = entities.get("action", "")
    direction = entities.get("direction", "")
    level = entities.get("level")

    if OS == "Darwin":
        if level is not None:
            os.system(f"osascript -e 'set volume output volume {level}'")
            return f"Volume set to {level}."
        if direction == "up":
            os.system("osascript -e 'set volume output volume (output volume of (get volume settings) + 10)'")
            return "Volume increased."
        if direction == "down":
            os.system("osascript -e 'set volume output volume (output volume of (get volume settings) - 10)'")
            return "Volume decreased."
        if action == "mute":
            os.system("osascript -e 'set volume with output muted'")
            return "Muted."
    elif OS == "Linux":
        if direction == "up":
            os.system("amixer -D pulse sset Master 10%+")
            return "Volume increased."
        if direction == "down":
            os.system("amixer -D pulse sset Master 10%-")
            return "Volume decreased."
        if action == "mute":
            os.system("amixer -D pulse sset Master toggle")
            return "Toggled mute."
    elif OS == "Windows":
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            if action == "mute":
                volume.SetMute(1, None)
                return "Muted."
        except Exception as e:
            logger.error(e)

    return "Volume adjusted."


def skill_unknown(entities: dict, _) -> str:
    return (
        "I didn't understand that command. You can ask me to open apps, "
        "search the web, check the time, take screenshots, and more."
    )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _parse_time_offset(time_str: str) -> int:
    """Parse a rough time expression to seconds offset. Returns 0 if unparseable."""
    if not time_str:
        return 0
    import re
    m = re.search(r"(\d+)\s*(minute|min|hour|second|sec)", time_str, re.I)
    if m:
        val = int(m.group(1))
        unit = m.group(2).lower()
        if "hour" in unit:
            return val * 3600
        if "min" in unit:
            return val * 60
        return val
    return 0
