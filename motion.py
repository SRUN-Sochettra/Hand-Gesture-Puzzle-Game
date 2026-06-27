"""Screen shake. Trigger-and-forget. Decays naturally."""

from __future__ import annotations

import random


class ScreenShake:
    def __init__(self) -> None:
        self.intensity = 0.0
        self.duration = 0.0
        self.elapsed = 0.0

    def trigger(self, intensity: float = 7.0, duration: float = 0.18) -> None:
        remaining = self.intensity * (
            1.0 - self.elapsed / max(self.duration, 1e-6)
        )
        if intensity > remaining:
            self.intensity = intensity
            self.duration = duration
            self.elapsed = 0.0

    def update(self, dt: float) -> tuple[float, float]:
        if self.intensity <= 0:
            return 0.0, 0.0
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.intensity = 0.0
            return 0.0, 0.0
        t = self.elapsed / self.duration
        amp = self.intensity * (1.0 - t) ** 2
        return random.uniform(-amp, amp), random.uniform(-amp, amp)