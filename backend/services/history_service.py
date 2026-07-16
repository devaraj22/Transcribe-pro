import os
import json
from datetime import datetime

# Path to the history file as outlined in the storage blueprint
HISTORY_FILE_PATH = os.path.join("storage", "history.json")
MAX_HISTORY_ITEMS = 5

def initialize_history_file():
    """Ensures history.json exists and is structured as a valid list."""
    os.makedirs(os.path.dirname(HISTORY_FILE_PATH), exist_ok=True)
    if not os.path.exists(HISTORY_FILE_PATH):
        with open(HISTORY_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)

def get_all_history() -> list:
    """Reads and returns the complete log from history.json."""
    initialize_history_file()
    try:
        with open(HISTORY_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to read history.json: {e}")
        return []

def append_to_history(job_id: str, title: str, status: str = "complete"):
    """
    Appends a new transcription record to history.json.
    Enforces a hard ceiling of 5 maximum items, removing the oldest entry if exceeded.
    """
    initialize_history_file()
    history = get_all_history()
    
    # Structure the new log item
    new_entry = {
        "job_id": job_id,
        "title": title if title else f"Transcription Job - {job_id[:8]}",
        "status": status,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Insert at the beginning of the list (most recent first)
    history.insert(0, new_entry)
    
    # Enforce the 5-item capacity log ceiling
    if len(history) > MAX_HISTORY_ITEMS:
        print(f"🧹 History limit reached ({MAX_HISTORY_ITEMS}). Evicting oldest entry.")
        history = history[:MAX_HISTORY_ITEMS]
        
    # Write structural update back to disk
    try:
        with open(HISTORY_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)
        return True
    except Exception as e:
        print(f"❌ Failed to write update to history.json: {e}")
        return False