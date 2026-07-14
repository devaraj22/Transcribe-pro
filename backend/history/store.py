import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..config import settings
from ..utils import ensure_json_file


def load_history() -> List[Dict]:
    path = settings.HISTORY_FILE
    ensure_json_file(path)
    return json.loads(path.read_text(encoding="utf-8"))


def save_history(history: List[Dict]) -> None:
    settings.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    settings.HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def append_history(entry: Dict) -> None:
    history = load_history()
    entry_copy = entry.copy()
    entry_copy["timestamp"] = entry_copy.get("timestamp") or datetime.utcnow().isoformat() + "Z"
    history.insert(0, entry_copy)
    history = history[: settings.HISTORY_LIMIT]
    save_history(history)


def get_history() -> List[Dict]:
    return load_history()


def clear_history() -> None:
    save_history([])
