import json
import os

DB_FILE = "seen_jobs.json"


def load_seen_ids() -> set:
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                return set(json.loads(content))
    return set()


def save_seen_ids(seen_ids: set):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen_ids), f, indent=2)
