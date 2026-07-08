"""Study session history — saved as JSON next to the app."""

import json
import os
from datetime import datetime
from pathlib import Path

HISTORY_FILE = Path(__file__).resolve().parent.parent / "history.json"

MAX_SESSIONS = 20


def _load():
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save(sessions):
    HISTORY_FILE.write_text(json.dumps(sessions, indent=2), encoding="utf-8")


def add_session(topic: str, score: str, guide_len: int, correct: int, total: int):
    sessions = _load()
    sessions.insert(0, {
        "topic": topic,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "score": score,
        "correct": correct,
        "total": total,
        "guide_len": guide_len,
    })
    sessions = sessions[:MAX_SESSIONS]
    _save(sessions)


def get_sessions():
    return _load()
