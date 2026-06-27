"""Particles, tweens, easings, confetti, cursor trail."""

from __future__ import annotations

import collections
import math
import random
from dataclasses import dataclass, field

from config import (
    CONFETTI_BURST_COUNT, CONFETTI_GRAVITY, CONFETTI_LIFETIME,
    SNAP_PARTICLE_COUNT, SNAP_PARTICLE_LIFETIME, SNAP_PARTICLE_SPEED,
    SNAP_RING_LIFETIME, SNAP_RING_MAX_RADIUS,
    TRAIL_LIFETIME, TRAIL_MAX_POINTS,
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
class ConfettiPiece:
    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int]
    rotation: float
    rotation_speed: float
    size: float
    age: float = 0.0
    lifetime: float = CONFETTI_LIFETIME

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
    confetti: list[ConfettiPiece] = field(default_factory=list)
    trail: collections.deque = field(
        default_factory=lambda: collections.deque(maxlen=TRAIL_MAX_POINTS)
    )

    def burst(self, x: float, y: float, color: tuple[int, int, int]) -> None:
        for i in range(SNAP_PARTICLE_COUNT):
            angle = (2 * math.pi * i / SNAP_PARTICLE_COUNT
                     + random.uniform(-0.15, 0.15))
            speed = SNAP_PARTICLE_SPEED * random.uniform(0.6, 1.2)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                color=color,
                size=random.uniform(3.0, 6.0),
            ))
        self.rings.append(Ring(x=x, y=y, color=color))

    def confetti_burst(self, width: int,
                       palette: list[tuple[int, int, int]]) -> None:
        for _ in range(CONFETTI_BURST_COUNT):
            self.confetti.append(ConfettiPiece(
                x=random.uniform(0, width),
                y=random.uniform(-60, -10),
                vx=random.uniform(-90, 90),
                vy=random.uniform(40, 140),
                color=random.choice(palette),
                rotation=random.uniform(0, math.tau),
                rotation_speed=random.uniform(-6, 6),
                size=random.uniform(6, 11),
            ))

    def add_trail(self, x: int, y: int) -> None:
        self.trail.append([x, y, 0.0])

    def clear_trail(self) -> None:
        self.trail.clear()

    def update(self, dt: float) -> None:
        for p in self.particles:
            p.age += dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            decay = math.exp(-3.5 * dt)
            p.vx *= decay
            p.vy *= decay
        self.particles = [p for p in self.particles if p.alive]

        for r in self.rings:
            r.age += dt
        self.rings = [r for r in self.rings if r.alive]

        for c in self.confetti:
            c.age += dt
            c.x += c.vx * dt
            c.y += c.vy * dt
            c.vy += CONFETTI_GRAVITY * dt
            c.vx *= math.exp(-0.6 * dt)
            c.rotation += c.rotation_speed * dt
        self.confetti = [c for c in self.confetti if c.alive]

        for pt in self.trail:
            pt[2] += dt
        while self.trail and self.trail[0][2] > TRAIL_LIFETIME:
            self.trail.popleft()

    def clear(self) -> None:
        self.particles.clear()
        self.rings.clear()
        self.confetti.clear()
        self.trail.clear()