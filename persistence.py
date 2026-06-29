"""Best-time records + calibration. Lives in ~/.gesture_puzzle_records.json."""

from __future__ import annotations

import json
from pathlib import Path

from config import CALIBRATION_FILE_KEY

_PATH = Path.home() / ".gesture_puzzle_records.json"


def load() -> dict:
    if not _PATH.exists():
        return {}
    try:
        res = json.loads(_PATH.read_text(encoding="utf-8"))
        return res if isinstance(res, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save(records: dict) -> None:
    try:
        _PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")
    except OSError:
        pass


def best_for(records: dict, level_name: str) -> dict | None:
    val = records.get(level_name)
    if isinstance(val, dict) and "seconds" in val and "moves" in val:
        return val
    return None


def maybe_record(records: dict, level_name: str,
                 seconds: int, moves: int) -> bool:
    current = best_for(records, level_name)
    new = (seconds, moves)
    if not current or new < (current["seconds"], current["moves"]):
        records[level_name] = {"seconds": seconds, "moves": moves}
        save(records)
        return True
    return False


def load_calibration() -> tuple[float, float] | None:
    data = load()
    cal = data.get(CALIBRATION_FILE_KEY)
    if not isinstance(cal, dict) or "grab" not in cal or "release" not in cal:
        return None
    return cal["grab"], cal["release"]


def save_calibration(grab: float, release: float) -> None:
    data = load()
    data[CALIBRATION_FILE_KEY] = {"grab": round(grab, 3),
                                  "release": round(release, 3)}
    save(data)