"""Game state, app state machine, event emission."""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto

from config import (
    ALL_SHAPES, CAMERA_HEIGHT, CAMERA_WIDTH, HAND_LOST_GRACE_SECONDS, LEVELS,
    PINCH_GRAB_THRESHOLD, PINCH_RELEASE_THRESHOLD,
    PLAYFIELD_MARGIN_BOTTOM, PLAYFIELD_MARGIN_TOP, PLAYFIELD_MARGIN_X,
    SHAPE_GRAB_SCALE, SHAPE_HOVER_SCALE, SHAPE_SCALE_SPEED,
    SNAP_LENIENCE_PER_100_PXS,
)
from effects import tween_toward
from vision import HandFrame


# ---------- enums ----------
class GrabState(Enum):
    IDLE = auto()
    GRABBING = auto()


class AppState(Enum):
    READY = auto()           # waiting for hand to appear
    PLAYING = auto()
    PAUSED = auto()
    LEVEL_COMPLETE = auto()  # win overlay, awaiting N
    GAME_COMPLETE = auto()


# ---------- events ----------
@dataclass
class Event:
    kind: str  # "grab" | "release" | "snap" | "level_complete"
    data: dict = field(default_factory=dict)


# ---------- shapes & geometry ----------
@dataclass
class Shape:
    id: int
    kind: str
    color: str
    x: float
    y: float
    target_id: int | None = None
    snapped: bool = False
    vx: float = 0.0
    vy: float = 0.0
    scale: float = 1.0  # animated cosmetic scale


@dataclass
class Rect:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int: return self.right - self.left
    @property
    def height(self) -> int: return self.bottom - self.top


# ---------- game ----------
class GameState:
    def __init__(self) -> None:
        self.width = CAMERA_WIDTH
        self.height = CAMERA_HEIGHT
        self.level_index = 0

        self.shapes: list[Shape] = []
        self.targets: list[Shape] = []

        self.cursor: tuple[int, int] = (self.width // 2, self.height // 2)
        self.cursor_scale: float = 1.0
        self.hand_speed_pxs: float = 0.0

        self.grab_state = GrabState.IDLE
        self.held_id: int | None = None
        self._hand_lost_at: float | None = None

        self.app_state = AppState.READY
        self.moves = 0
        self.started_at: float | None = None
        self.finished_at: float | None = None
        self._last_update = time.time()

        self._events: list[Event] = []

        self.reset_level(reset_app_state=True)

    # ---- level metadata ----
    @property
    def level(self) -> dict: return LEVELS[self.level_index]
    @property
    def level_number(self) -> int: return self.level_index + 1
    @property
    def total_levels(self) -> int: return len(LEVELS)
    @property
    def level_name(self) -> str: return self.level["name"]
    @property
    def shape_size(self) -> int: return self.level["shape_size"]
    @property
    def grab_radius(self) -> int: return self.level["grab_radius"]
    @property
    def snap_radius(self) -> int: return self.level["snap_radius"]
    @property
    def is_final_level(self) -> bool: return self.level_index == len(LEVELS) - 1
    @property
    def is_pinching(self) -> bool: return self.grab_state is GrabState.GRABBING
    @property
    def is_paused(self) -> bool: return self.app_state is AppState.PAUSED

    @property
    def all_matched(self) -> bool:
        return bool(self.shapes) and all(s.snapped for s in self.shapes)

    def playfield(self) -> Rect:
        return Rect(
            left=int(self.width * PLAYFIELD_MARGIN_X),
            top=int(self.height * PLAYFIELD_MARGIN_TOP),
            right=int(self.width * (1.0 - PLAYFIELD_MARGIN_X)),
            bottom=int(self.height * (1.0 - PLAYFIELD_MARGIN_BOTTOM)),
        )

    # ---- events ----
    def drain_events(self) -> list[Event]:
        out = self._events
        self._events = []
        return out

    # ---- lifecycle ----
    def reset_level(self, *, reset_app_state: bool = False) -> None:
        self.shapes.clear()
        self.targets.clear()
        self.cursor = (self.width // 2, self.height // 2)
        self.hand_speed_pxs = 0.0
        self.grab_state = GrabState.IDLE
        self.held_id = None
        self._hand_lost_at = None
        self.moves = 0
        self.started_at = None
        self.finished_at = None
        self._last_update = time.time()
        if reset_app_state:
            self.app_state = AppState.READY
        elif self.app_state in (AppState.LEVEL_COMPLETE, AppState.GAME_COMPLETE):
            self.app_state = AppState.PLAYING
            self.started_at = time.time()
        self._spawn_level()

    def next_level(self) -> None:
        if self.app_state is AppState.GAME_COMPLETE:
            self.level_index = 0
            self.reset_level(reset_app_state=True)
            return
        if self.app_state is not AppState.LEVEL_COMPLETE:
            return
        self.level_index += 1
        self.reset_level()

    def toggle_pause(self) -> None:
        if self.app_state is AppState.PLAYING:
            self.app_state = AppState.PAUSED
        elif self.app_state is AppState.PAUSED:
            self.app_state = AppState.PLAYING

    def resize(self, width: int, height: int) -> None:
        if width == self.width and height == self.height:
            return
        # Rescale shape positions proportionally rather than nuking the level.
        sx, sy = width / self.width, height / self.height
        self.width, self.height = width, height
        for s in self.shapes + self.targets:
            s.x *= sx
            s.y *= sy

    # ---- main update ----
    def update(self, hand: HandFrame) -> None:
        now = time.time()
        dt = min(now - self._last_update, 1 / 15)
        self._last_update = now

        if self.app_state is AppState.READY:
            self._update_ready(hand, now)
        elif self.app_state is AppState.PLAYING:
            self._update_playing(hand, dt, now)
        elif self.app_state is AppState.PAUSED:
            # Freeze world; still track cursor for visual continuity.
            if hand.detected and hand.cursor:
                self.cursor = hand.cursor
        # LEVEL_COMPLETE / GAME_COMPLETE: cursor still updates for polish.
        elif hand.detected and hand.cursor:
            self.cursor = hand.cursor

        self._animate(dt)

    # ---- state-specific updates ----
    def _update_ready(self, hand: HandFrame, now: float) -> None:
        if hand.detected and hand.cursor:
            self.cursor = hand.cursor
            self.app_state = AppState.PLAYING
            self.started_at = now
            self._last_update = now

    def _update_playing(self, hand: HandFrame, dt: float, now: float) -> None:
        self._move_targets(dt)
        self._sync_snapped_to_targets()

        if not hand.detected:
            self._on_hand_lost(now)
            return

        self._on_hand_present(hand, dt)

    def _on_hand_lost(self, now: float) -> None:
        if self._hand_lost_at is None:
            self._hand_lost_at = now
        self.grab_state = GrabState.IDLE
        self.hand_speed_pxs *= 0.9
        if now - self._hand_lost_at > HAND_LOST_GRACE_SECONDS:
            self.held_id = None

    def _on_hand_present(self, hand: HandFrame, dt: float) -> None:
        self._hand_lost_at = None
        prev = self.cursor
        self.cursor = hand.cursor or self.cursor

        if dt > 0:
            instant = math.hypot(self.cursor[0] - prev[0], self.cursor[1] - prev[1]) / dt
            self.hand_speed_pxs = self.hand_speed_pxs * 0.75 + instant * 0.25

        prev_state = self.grab_state
        self._update_pinch_state(hand.pinch_ratio)
        self._apply_pinch_transitions(prev_state)

    def _update_pinch_state(self, ratio: float | None) -> None:
        if ratio is None:
            self.grab_state = GrabState.IDLE
            return
        if self.grab_state is GrabState.GRABBING:
            if ratio >= PINCH_RELEASE_THRESHOLD:
                self.grab_state = GrabState.IDLE
        elif ratio < PINCH_GRAB_THRESHOLD:
            self.grab_state = GrabState.GRABBING

    def _apply_pinch_transitions(self, prev_state: GrabState) -> None:
        held = self.held_shape()

        # --- enter GRABBING ---
        if (prev_state is GrabState.IDLE
                and self.grab_state is GrabState.GRABBING
                and held is None):
            hovered = self.hovered_shape()
            if hovered is not None:
                self.held_id = hovered.id
                self._events.append(Event("grab", {"x": hovered.x, "y": hovered.y,
                                                   "color": hovered.color}))

        # --- continuous drag ---
        held = self.held_shape()
        if held is not None and self.grab_state is GrabState.GRABBING:
            held.x, held.y = self._clamp_to_playfield(self.cursor)

        # --- exit GRABBING ---
        if (prev_state is GrabState.GRABBING
                and self.grab_state is GrabState.IDLE
                and held is not None):
            self.moves += 1
            snapped = self._try_snap(held)
            if not snapped:
                self._events.append(Event("release", {"x": held.x, "y": held.y,
                                                      "color": held.color}))
            self.held_id = None

    # ---- queries ----
    def held_shape(self) -> Shape | None:
        if self.held_id is None:
            return None
        return next((s for s in self.shapes if s.id == self.held_id), None)

    def hovered_shape(self) -> Shape | None:
        if self.app_state is not AppState.PLAYING or self.held_id is not None:
            return None
        nearest: Shape | None = None
        nd = float("inf")
        for s in self.shapes:
            if s.snapped:
                continue
            d = math.hypot(self.cursor[0] - s.x, self.cursor[1] - s.y)
            if d < self.grab_radius and d < nd:
                nearest, nd = s, d
        return nearest

    def target_for(self, shape: Shape) -> Shape:
        return next(t for t in self.targets if t.id == shape.target_id)

    def progress(self) -> tuple[int, int]:
        return sum(s.snapped for s in self.shapes), len(self.shapes)

    def elapsed_seconds(self) -> int:
        if self.started_at is None:
            return 0
        end = self.finished_at if self.finished_at else time.time()
        return int(end - self.started_at)

    def snap_proximity(self, shape: Shape) -> float:
        """0..1 where 1 = within snap radius. Used for target ring pulse."""
        target = self.target_for(shape)
        d = math.hypot(shape.x - target.x, shape.y - target.y)
        if d >= self.snap_radius * 2:
            return 0.0
        return max(0.0, min(1.0, 1.0 - d / (self.snap_radius * 2)))

    # ---- helpers ----
    def _clamp_to_playfield(self, point: tuple[int, int]) -> tuple[int, int]:
        pf = self.playfield()
        half = self.shape_size // 2
        x = min(max(point[0], pf.left + half), pf.right - half)
        y = min(max(point[1], pf.top + half), pf.bottom - half)
        return x, y

    def _try_snap(self, shape: Shape) -> bool:
        target = self.target_for(shape)
        target_speed = math.hypot(target.vx, target.vy)
        lenience = (target_speed / 100.0) * SNAP_LENIENCE_PER_100_PXS
        d = math.hypot(shape.x - target.x, shape.y - target.y)
        if d > self.snap_radius + lenience:
            return False
        shape.x, shape.y = target.x, target.y
        shape.snapped = True
        self._events.append(Event("snap", {"x": shape.x, "y": shape.y,
                                           "color": shape.color}))
        if self.all_matched and self.finished_at is None:
            self.finished_at = time.time()
            self.app_state = (AppState.GAME_COMPLETE
                              if self.is_final_level else AppState.LEVEL_COMPLETE)
            self._events.append(Event("level_complete", {"final": self.is_final_level}))
        return True

    def _move_targets(self, dt: float) -> None:
        if not self.level["targets_move"]:
            return
        pf = self.playfield()
        half = self.shape_size // 2
        band = min(280, pf.width // 2)
        left_l = max(pf.left + half, pf.right - band)
        right_l = pf.right - half
        top_l = pf.top + half
        bot_l = pf.bottom - half

        for t in self.targets:
            t.x += t.vx * dt
            t.y += t.vy * dt
            if t.y <= top_l: t.y, t.vy = top_l, -t.vy
            elif t.y >= bot_l: t.y, t.vy = bot_l, -t.vy
            if t.x <= left_l: t.x, t.vx = left_l, -t.vx
            elif t.x >= right_l: t.x, t.vx = right_l, -t.vx

    def _sync_snapped_to_targets(self) -> None:
        for s in self.shapes:
            if not s.snapped:
                continue
            t = self.target_for(s)
            s.x, s.y = t.x, t.y

    # ---- animation ----
    def _animate(self, dt: float) -> None:
        held = self.held_shape()
        hovered = self.hovered_shape()

        for s in self.shapes:
            if s is held:
                target_scale = SHAPE_GRAB_SCALE
            elif s is hovered:
                target_scale = SHAPE_HOVER_SCALE
            else:
                target_scale = 1.0
            s.scale = tween_toward(s.scale, target_scale, SHAPE_SCALE_SPEED, dt)

        target_cursor_scale = 1.15 if self.is_pinching else 1.0
        from config import CURSOR_SCALE_SPEED
        self.cursor_scale = tween_toward(self.cursor_scale, target_cursor_scale,
                                         CURSOR_SCALE_SPEED, dt)

    # ---- level spawn ----
    def _spawn_level(self) -> None:
        count = self.level["shape_count"]
        defs = ALL_SHAPES[:count]
        pf = self.playfield()
        half = self.shape_size // 2
        shape_x = pf.left + half + 6
        target_x = pf.right - half - 6

        usable_h = max(1, pf.height - self.shape_size)
        spacing = usable_h // max(1, count - 1) if count > 1 else 0

        target_slots = list(range(count))
        shape_slots = list(range(count))
        random.shuffle(target_slots)
        random.shuffle(shape_slots)

        for i, d in enumerate(defs):
            vx, vy = self._random_velocity()
            self.targets.append(Shape(
                id=i, kind=d["kind"], color=d["color"],
                x=target_x, y=pf.top + half + spacing * target_slots[i],
                vx=vx, vy=vy,
            ))
        for i, d in enumerate(defs):
            self.shapes.append(Shape(
                id=i, kind=d["kind"], color=d["color"],
                x=shape_x, y=pf.top + half + spacing * shape_slots[i],
                target_id=i,
            ))

    def _random_velocity(self) -> tuple[float, float]:
        if not self.level["targets_move"]:
            return 0.0, 0.0
        lo, hi = self.level["speed_range"]
        speed = random.randint(lo, hi)
        sign = lambda: random.choice([-1, 1])
        axis = self.level["move_axis"]
        if axis == "y": return 0.0, speed * sign()
        if axis == "xy": return speed * 0.55 * sign(), speed * sign()
        return 0.0, 0.0