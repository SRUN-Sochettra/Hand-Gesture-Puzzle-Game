"""Particles, tweens, easings. No game logic, just visuals."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from config import (
    SNAP_PARTICLE_COUNT, SNAP_PARTICLE_LIFETIME, SNAP_PARTICLE_SPEED,
    SNAP_RING_LIFETIME, SNAP_RING_MAX_RADIUS,
)


# ---------- easings ----------
def ease_out_quad(t: float) -> float:
    return 1 - (1 - t) ** 2


def ease_in_out_quad(t: float) -> float:
    return 2 * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 2 / 2


def ease_out_back(t: float) -> float:
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


# ---------- tween primitive ----------
def tween_toward(current: float, target: float, speed: float, dt: float) -> float:
    """Exponential approach. Frame-rate independent. `speed` ~ 1/time-constant."""
    if speed <= 0 or dt <= 0:
        return target
    alpha = 1 - math.exp(-speed * dt)
    return current + (target - current) * alpha


# ---------- particles ----------
@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int]
    age: float = 0.0
    lifetime: float = SNAP_PARTICLE_LIFETIME
    size: float = 4.0

    @property
    def alive(self) -> bool:
        return self.age < self.lifetime

    @property
    def progress(self) -> float:
        return min(1.0, self.age / self.lifetime)


@dataclass
class Ring:
    x: float
    y: float
    color: tuple[int, int, int]
    age: float = 0.0
    lifetime: float = SNAP_RING_LIFETIME
    max_radius: float = SNAP_RING_MAX_RADIUS

    @property
    def alive(self) -> bool:
        return self.age < self.lifetime

    @property
    def progress(self) -> float:
        return min(1.0, self.age / self.lifetime)


@dataclass
class EffectSystem:
    particles: list[Particle] = field(default_factory=list)
    rings: list[Ring] = field(default_factory=list)

    def burst(self, x: float, y: float, color: tuple[int, int, int]) -> None:
        for i in range(SNAP_PARTICLE_COUNT):
            angle = (2 * math.pi * i / SNAP_PARTICLE_COUNT) + random.uniform(-0.15, 0.15)
            speed = SNAP_PARTICLE_SPEED * random.uniform(0.6, 1.2)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                color=color,
                size=random.uniform(3.0, 6.0),
            ))
        self.rings.append(Ring(x=x, y=y, color=color))

    def update(self, dt: float) -> None:
        for p in self.particles:
            p.age += dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            # Drag so they decelerate
            decay = math.exp(-3.5 * dt)
            p.vx *= decay
            p.vy *= decay
        self.particles = [p for p in self.particles if p.alive]

        for r in self.rings:
            r.age += dt
        self.rings = [r for r in self.rings if r.alive]

    def clear(self) -> None:
        self.particles.clear()
        self.rings.clear()