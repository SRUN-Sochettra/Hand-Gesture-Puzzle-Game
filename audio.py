"""Tiny non-blocking sound cues. Windows-only; silent fallback elsewhere."""

from __future__ import annotations

import sys
import threading

from config import SHAPE_PITCHES

try:
    import winsound  # type: ignore
    _ENABLED = sys.platform == "win32"
except ImportError:
    _ENABLED = False


_SOUNDS: dict[str, list[tuple[int, int]]] = {
    "grab":           [(620, 28)],
    "release":        [(420, 28)],
    "level_complete": [(659, 90), (784, 90), (988, 90), (1175, 180)],
    "game_complete":  [(523, 90), (659, 90), (784, 90), (988, 90), (1319, 260)],
}


def play(name: str) -> None:
    if not _ENABLED:
        return
    seq = _SOUNDS.get(name)
    if seq:
        threading.Thread(target=_play_seq, args=(seq,), daemon=True).start()


def play_snap(color: str) -> None:
    """Per-shape pitch. Pentatonic = never sounds wrong."""
    if not _ENABLED:
        return
    pitch = SHAPE_PITCHES.get(color, 880)
    seq = [(pitch, 35), (pitch * 3 // 2, 55)]
    threading.Thread(target=_play_seq, args=(seq,), daemon=True).start()


def _play_seq(seq: list[tuple[int, int]]) -> None:
    for freq, dur in seq:
        try:
            winsound.Beep(freq, dur)
        except Exception:
            return