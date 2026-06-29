"""Pre-game pinch calibration. Two phases: relaxed hand, pinched hand."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto

from config import (
    CALIBRATION_HYSTERESIS_GAP, CALIBRATION_PHASE_SECONDS, CALIBRATION_WARMUP,
    PINCH_THRESHOLD_MAX, PINCH_THRESHOLD_MIN,
)

class CalibPhase(Enum):
    IDLE = auto()
    RELAXED = auto()
    PINCHED = auto()
    DONE = auto()

@dataclass
class Calibration:
    phase: CalibPhase = CalibPhase.IDLE
    started_at: float = 0.0
    relaxed: list[float] = field(default_factory=list)
    pinched: list[float] = field(default_factory=list)
    result: tuple[float, float] | None = None

    def start(self) -> None:
        self.phase = CalibPhase.RELAXED
        self.started_at = time.monotonic()
        self.relaxed.clear()
        self.pinched.clear()
        self.result = None

    def skip(self) -> None:
        self.phase = CalibPhase.DONE
        self.result = None

    @property
    def is_active(self) -> bool:
        return self.phase in (CalibPhase.RELAXED, CalibPhase.PINCHED)

    @property
    def is_done(self) -> bool:
        return self.phase is CalibPhase.DONE

    def phase_progress(self) -> float:
        if not self.is_active:
            return 0.0
        elapsed = time.monotonic() - self.started_at
        return min(1.0, elapsed / CALIBRATION_PHASE_SECONDS)

    def feed(self, ratio: float | None) -> None:
        if not self.is_active or ratio is None:
            return
        now = time.monotonic()
        elapsed = now - self.started_at
        bucket = (self.relaxed if self.phase is CalibPhase.RELAXED
                  else self.pinched)
        if elapsed > CALIBRATION_WARMUP:
            bucket.append(ratio)
        if elapsed > CALIBRATION_PHASE_SECONDS:
            if self.phase is CalibPhase.RELAXED:
                self.phase = CalibPhase.PINCHED
                self.started_at = now
            else:
                self._compute()
                self.phase = CalibPhase.DONE

    def _compute(self) -> None:
        if len(self.relaxed) < 8 or len(self.pinched) < 8:
            self.result = None
            return
        relaxed = sorted(self.relaxed)
        pinched = sorted(self.pinched)
        r_low = relaxed[max(0, len(relaxed) // 10)]
        p_high = pinched[min(len(pinched) - 1, (len(pinched) * 9) // 10)]
        if p_high >= r_low:
            self.result = None
            return
        grab = (r_low + p_high) / 2
        grab = max(PINCH_THRESHOLD_MIN, min(PINCH_THRESHOLD_MAX, grab))
        release = min(0.48, grab + CALIBRATION_HYSTERESIS_GAP)
        self.result = (grab, release)