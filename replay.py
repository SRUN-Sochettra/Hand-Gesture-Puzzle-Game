"""Ghost replay: record cursor path + pinch state, play back on retry."""

from __future__ import annotations

import bisect
import json
from dataclasses import dataclass, field
from pathlib import Path

from config import GHOST_SAMPLE_HZ

_PATH = Path.home() / ".gesture_puzzle_ghosts.json"
_SAMPLE_INTERVAL = 1.0 / GHOST_SAMPLE_HZ


@dataclass
class Recorder:
    samples: list[tuple[float, int, int, int]] = field(default_factory=list)
    _last_sample_t: float = -1.0
    _started_at: float | None = None

    def reset(self) -> None:
        self.samples.clear()
        self._last_sample_t = -1.0
        self._started_at = None

    def sample(self, now: float, x: int, y: int, grabbing: bool) -> None:
        if self._started_at is None:
            self._started_at = now
        rel_t = now - self._started_at
        if rel_t - self._last_sample_t < _SAMPLE_INTERVAL:
            return
        self._last_sample_t = rel_t
        self.samples.append(
            (round(rel_t, 3), int(x), int(y), 1 if grabbing else 0)
        )

    def serialize(self) -> list:
        return [list(s) for s in self.samples]


class Playback:
    """Query ghost state at elapsed time. O(log n) lookup."""

    def __init__(self, samples: list[list]) -> None:
        self.samples = [s for s in samples if isinstance(s, (list, tuple)) and len(s) >= 4]
        self._times = [s[0] for s in self.samples]

    @property
    def empty(self) -> bool:
        return not self.samples

    def at(self, elapsed: float) -> tuple[int, int, bool] | None:
        if not self.samples or elapsed < 0:
            return None
        idx = bisect.bisect_right(self._times, elapsed) - 1
        if idx < 0:
            return None
        if idx >= len(self.samples) - 1:
            s = self.samples[-1]
            return s[1], s[2], bool(s[3])
        a = self.samples[idx]
        b = self.samples[idx + 1]
        span = max(1e-6, b[0] - a[0])
        t = (elapsed - a[0]) / span
        x = int(a[1] + (b[1] - a[1]) * t)
        y = int(a[2] + (b[2] - a[2]) * t)
        return x, y, bool(a[3])


def load_all() -> dict[str, list[list]]:
    if not _PATH.exists():
        return {}
    try:
        res = json.loads(_PATH.read_text(encoding="utf-8"))
        return res if isinstance(res, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_for_level(level_name: str, samples: list[list]) -> None:
    data = load_all()
    data[level_name] = samples
    try:
        _PATH.write_text(json.dumps(data, separators=(",", ":")),
                         encoding="utf-8")
    except OSError:
        pass


def load_for_level(level_name: str) -> Playback:
    return Playback(load_all().get(level_name, []))