"""Hand-shape classifier + hold-to-fire detector."""

from __future__ import annotations

import math
from enum import Enum, auto

from config import (
    GESTURE_COOLDOWN, GESTURE_EXTENSION_RATIO, GESTURE_HOLD_SECONDS,
)


class Gesture(Enum):
    NONE = auto()
    PINCH = auto()
    OPEN_PALM = auto()
    POINT = auto()
    FIST = auto()


# MediaPipe landmark indices: thumb, index, middle, ring, pinky
_TIP = (4, 8, 12, 16, 20)
_PIP = (3, 6, 10, 14, 18)
_MCP = (2, 5, 9, 13, 17)


def _extended(lm, tip: int, pip: int, mcp: int) -> bool:
    t, p, m = lm[tip], lm[pip], lm[mcp]
    return (math.hypot(t.x - m.x, t.y - m.y)
            > math.hypot(p.x - m.x, p.y - m.y) * GESTURE_EXTENSION_RATIO)


def classify(landmarks, pinch_ratio: float | None,
             pinch_threshold: float = 0.34) -> Gesture:
    if pinch_ratio is not None and pinch_ratio < pinch_threshold:
        return Gesture.PINCH
    lm = landmarks.landmark
    ext = [_extended(lm, _TIP[i], _PIP[i], _MCP[i]) for i in range(5)]
    if all(ext[1:]):
        return Gesture.OPEN_PALM
    if ext[1] and not any(ext[2:]):
        return Gesture.POINT
    if not any(ext[1:]):
        return Gesture.FIST
    return Gesture.NONE


class HoldFireDetector:
    """Same gesture must persist GESTURE_HOLD_SECONDS to fire."""

    def __init__(self) -> None:
        self._current: Gesture = Gesture.NONE
        self._held_since: float = 0.0
        self._last_fire_at: float = -1.0

    def reset(self) -> None:
        self._current = Gesture.NONE
        self._held_since = 0.0

    def update(self, gesture: Gesture, now: float) -> Gesture | None:
        if gesture is not self._current:
            self._current = gesture
            self._held_since = now
            return None
        if now - self._last_fire_at < GESTURE_COOLDOWN:
            return None
        if (gesture not in (Gesture.NONE, Gesture.PINCH)
                and now - self._held_since >= GESTURE_HOLD_SECONDS):
            self._last_fire_at = now
            return gesture
        return None

    def hold_progress(self, now: float) -> float:
        if self._current in (Gesture.NONE, Gesture.PINCH):
            return 0.0
        if now - self._last_fire_at < GESTURE_COOLDOWN:
            return 0.0
        return min(1.0, (now - self._held_since) / GESTURE_HOLD_SECONDS)

    @property
    def current(self) -> Gesture:
        return self._current