"""Game state, app state machine, event emission. Slot-based for co-op."""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto

from config import (
    ADAPTIVE_ENABLED, ADAPTIVE_FAIL_THRESHOLD, ADAPTIVE_GRAB_BUMP,
    ADAPTIVE_SPEED_SOFTEN, ALL_SHAPES, CAMERA_HEIGHT, CAMERA_WIDTH,
    COOP_DEFAULT, CURSOR_FADE_SECONDS, CURSOR_SCALE_SPEED,
    HAND_LOST_GRACE_SECONDS, LEVELS, PINCH_GRACE_SECONDS,
    PINCH_GRAB_THRESHOLD, PINCH_RELEASE_THRESHOLD, PINCH_THRESHOLD_MAX,
    PINCH_THRESHOLD_MIN, PINCH_THRESHOLD_STEP,
    PLAYFIELD_MARGIN_BOTTOM, PLAYFIELD_MARGIN_TOP, PLAYFIELD_MARGIN_X,
    READY_STABLE_SECONDS, SHAPE_GRAB_SCALE, SHAPE_HOVER_SCALE,
    SHAPE_SCALE_SPEED, SHAPE_SPAWN_BASE_DELAY, SHAPE_SPAWN_DURATION,
    SHAPE_SPAWN_OFFSCREEN, SHAPE_SPAWN_STAGGER, SNAP_LENIENCE_PER_100_PXS,
    TARGET_SPAWN_BASE_DELAY, TARGET_SPAWN_DURATION, TARGET_SPAWN_OFFSCREEN,
    TARGET_SPAWN_STAGGER,
)
from effects import ease_out_back, ease_out_quad, tween_toward
from vision import HandFrame


# ---------- enums ----------
class GrabState(Enum):
    IDLE = auto()
    GRABBING = auto()


class AppState(Enum):
    READY = auto()
    PLAYING = auto()
    PAUSED = auto()
    LEVEL_COMPLETE = auto()
    GAME_COMPLETE = auto()


# ---------- events ----------
@dataclass
class Event:
    kind: str
    data: dict = field(default_factory=dict)


# ---------- shapes ----------
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
    scale: float = 1.0
    held_by: str | None = None
    # Spawn animation
    home_x: float = 0.0
    home_y: float = 0.0
    spawn_start_x: float = 0.0
    spawn_start_y: float = 0.0
    spawn_delay: float = 0.0
    spawn_elapsed: float = 0.0
    spawn_duration: float = 0.55
    is_spawning: bool = True


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


# ---------- hand slot ----------
@dataclass
class HandSlot:
    handedness: str
    cursor: tuple[int, int] = (0, 0)
    cursor_scale: float = 1.0
    cursor_alpha: float = 1.0
    grab_state: GrabState = GrabState.IDLE
    held_id: int | None = None
    hand_speed_pxs: float = 0.0
    _pinch_missing_for: float = 0.0
    _hand_lost_at: float | None = None


# ---------- game ----------
class GameState:
    def __init__(self) -> None:
        self.width = CAMERA_WIDTH
        self.height = CAMERA_HEIGHT
        self.level_index = 0

        self.shapes: list[Shape] = []
        self.targets: list[Shape] = []

        self.coop_mode: bool = COOP_DEFAULT
        self.slots: dict[str, HandSlot] = {
            "Right": HandSlot(
                handedness="Right",
                cursor=(self.width // 2, self.height // 2),
            ),
        }

        self.app_state = AppState.READY
        self.moves = 0
        self.started_at: float | None = None
        self.finished_at: float | None = None
        self._last_update = time.monotonic()
        self._ready_streak: float = 0.0

        self.pinch_grab_threshold: float = PINCH_GRAB_THRESHOLD
        self.pinch_release_threshold: float = PINCH_RELEASE_THRESHOLD

        # Adaptive difficulty (session-only)
        self._adaptive_resets: dict[int, int] = {}
        self._level_speed_mult: dict[int, float] = {}

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
    def is_softened(self) -> bool:
        return self._level_speed_mult.get(self.level_index, 1.0) < 1.0

    @property
    def grab_radius(self) -> int:
        return self.level["grab_radius"] + (
            ADAPTIVE_GRAB_BUMP if self.is_softened else 0)

    @property
    def snap_radius(self) -> int:
        return self.level["snap_radius"] + (
            ADAPTIVE_GRAB_BUMP if self.is_softened else 0)

    @property
    def is_final_level(self) -> bool:
        return self.level_index == len(LEVELS) - 1

    @property
    def is_pinching(self) -> bool:
        return any(s.grab_state is GrabState.GRABBING
                   for s in self.slots.values())

    @property
    def is_paused(self) -> bool:
        return self.app_state is AppState.PAUSED

    @property
    def all_matched(self) -> bool:
        return bool(self.shapes) and all(s.snapped for s in self.shapes)

    @property
    def primary_slot(self) -> HandSlot:
        return self.slots.get("Right") or next(iter(self.slots.values()))

    # Back-compat shims (renderer + main read these)
    @property
    def cursor(self) -> tuple[int, int]: return self.primary_slot.cursor
    @property
    def cursor_scale(self) -> float: return self.primary_slot.cursor_scale
    @property
    def cursor_alpha(self) -> float: return self.primary_slot.cursor_alpha
    @property
    def hand_speed_pxs(self) -> float: return self.primary_slot.hand_speed_pxs

    def playfield(self) -> Rect:
        return Rect(
            left=int(self.width * PLAYFIELD_MARGIN_X),
            top=int(self.height * PLAYFIELD_MARGIN_TOP),
            right=int(self.width * (1.0 - PLAYFIELD_MARGIN_X)),
            bottom=int(self.height * (1.0 - PLAYFIELD_MARGIN_BOTTOM)),
        )

    # ---- events ----
    def drain_events(self) -> list:
        out = self._events
        self._events = []
        return out

    # ---- pinch threshold ----
    def adjust_pinch_threshold(self, delta: int) -> None:
        new = self.pinch_grab_threshold + delta * PINCH_THRESHOLD_STEP
        new = max(PINCH_THRESHOLD_MIN, min(PINCH_THRESHOLD_MAX, new))
        self.pinch_grab_threshold = new
        self.pinch_release_threshold = min(0.48, new + 0.12)

    # ---- lifecycle ----
    def reset_level(self, *, reset_app_state: bool = False) -> None:
        # Count this as a "fail" reset for adaptive difficulty
        if (self.app_state is AppState.PLAYING
                and self.started_at is not None
                and not self.all_matched
                and ADAPTIVE_ENABLED):
            self._adaptive_resets[self.level_index] = (
                self._adaptive_resets.get(self.level_index, 0) + 1
            )
            if (self._adaptive_resets[self.level_index]
                    >= ADAPTIVE_FAIL_THRESHOLD):
                self._level_speed_mult[self.level_index] = (
                    ADAPTIVE_SPEED_SOFTEN
                )

        self.shapes.clear()
        self.targets.clear()
        for slot in self.slots.values():
            slot.cursor = (self.width // 2, self.height // 2)
            slot.grab_state = GrabState.IDLE
            slot.held_id = None
            slot._hand_lost_at = None
            slot._pinch_missing_for = 0.0
            slot.hand_speed_pxs = 0.0
        self.moves = 0
        self.started_at = None
        self.finished_at = None
        self._last_update = time.monotonic()
        self._ready_streak = 0.0
        if reset_app_state:
            self.app_state = AppState.READY
        elif self.app_state in (AppState.LEVEL_COMPLETE,
                                AppState.GAME_COMPLETE):
            self.app_state = AppState.PLAYING
            self.started_at = time.monotonic()
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
        sx, sy = width / self.width, height / self.height
        self.width, self.height = width, height
        for s in self.shapes + self.targets:
            s.x *= sx
            s.y *= sy

    # ---- main update ----
    def update(self, hand: HandFrame) -> None:
        now = time.monotonic()
        dt = min(now - self._last_update, 1 / 15)
        self._last_update = now

        self._sync_slots()

        if self.app_state is AppState.READY:
            self._update_ready(hand, now, dt)
        elif self.app_state is AppState.PLAYING:
            self._update_playing(hand, dt, now)
        elif self.app_state is AppState.PAUSED:
            for slot in self.slots.values():
                data = hand.by_handedness(slot.handedness)
                if data and data.cursor:
                    slot.cursor = data.cursor
        else:
            for slot in self.slots.values():
                data = hand.by_handedness(slot.handedness)
                if data and data.cursor:
                    slot.cursor = data.cursor

        self._animate(dt)

    def _sync_slots(self) -> None:
        want = {"Right", "Left"} if self.coop_mode else {"Right"}
        # Remove slots no longer needed
        for label in list(self.slots.keys()):
            if label not in want:
                held = self.slots[label].held_id
                if held is not None:
                    s = next((sh for sh in self.shapes if sh.id == held), None)
                    if s:
                        s.held_by = None
                del self.slots[label]
        # Add missing slots
        for label in want:
            if label not in self.slots:
                self.slots[label] = HandSlot(
                    handedness=label,
                    cursor=(self.width // 2, self.height // 2),
                )

    # ---- READY ----
    def _update_ready(self, hand: HandFrame, now: float, dt: float) -> None:
        primary = hand.primary
        if primary and primary.cursor:
            self.primary_slot.cursor = primary.cursor
            self.primary_slot.cursor_alpha = 1.0
            self._ready_streak += dt
            if self._ready_streak >= READY_STABLE_SECONDS:
                self.app_state = AppState.PLAYING
                self.started_at = now
                self._last_update = now
        else:
            self._ready_streak = 0.0

    # ---- PLAYING ----
    def _update_playing(self, hand: HandFrame, dt: float, now: float) -> None:
        self._move_targets(dt)
        self._sync_snapped_to_targets()
        for slot in self.slots.values():
            data = hand.by_handedness(slot.handedness)
            if data is None or data.cursor is None:
                self._on_slot_lost(slot, now, dt)
            else:
                self._on_slot_present(slot, data, dt)

    def _on_slot_lost(self, slot: HandSlot, now: float, dt: float) -> None:
        if slot._hand_lost_at is None:
            slot._hand_lost_at = now
        slot.cursor_alpha = max(0.0,
                                slot.cursor_alpha - dt / CURSOR_FADE_SECONDS)
        slot.hand_speed_pxs *= 0.9
        if now - slot._hand_lost_at > HAND_LOST_GRACE_SECONDS:
            slot.grab_state = GrabState.IDLE
            if slot.held_id is not None:
                s = next((sh for sh in self.shapes
                          if sh.id == slot.held_id), None)
                if s and s.held_by == slot.handedness:
                    s.held_by = None
            slot.held_id = None

    def _on_slot_present(self, slot: HandSlot, data, dt: float) -> None:
        slot._hand_lost_at = None
        slot.cursor_alpha = min(1.0,
                                slot.cursor_alpha + dt / CURSOR_FADE_SECONDS)
        prev = slot.cursor
        slot.cursor = data.cursor
        if dt > 0:
            inst = math.hypot(slot.cursor[0] - prev[0],
                              slot.cursor[1] - prev[1]) / dt
            slot.hand_speed_pxs = slot.hand_speed_pxs * 0.75 + inst * 0.25

        prev_state = slot.grab_state
        self._update_slot_pinch(slot, data.pinch_ratio, dt)
        self._apply_slot_pinch_transitions(slot, prev_state)

    def _update_slot_pinch(self, slot: HandSlot,
                           ratio: float | None, dt: float) -> None:
        if ratio is None:
            slot._pinch_missing_for += dt
            if slot._pinch_missing_for > PINCH_GRACE_SECONDS:
                slot.grab_state = GrabState.IDLE
            return
        slot._pinch_missing_for = 0.0
        if slot.grab_state is GrabState.GRABBING:
            if ratio >= self.pinch_release_threshold:
                slot.grab_state = GrabState.IDLE
        elif ratio < self.pinch_grab_threshold:
            slot.grab_state = GrabState.GRABBING

    def _apply_slot_pinch_transitions(self, slot: HandSlot,
                                      prev_state: GrabState) -> None:
        held = self._held_by_slot(slot)

        # Enter GRABBING
        if (prev_state is GrabState.IDLE
                and slot.grab_state is GrabState.GRABBING
                and held is None):
            hovered = self._hover_for_slot(slot)
            if hovered is not None and hovered.held_by is None:
                slot.held_id = hovered.id
                hovered.held_by = slot.handedness
                self._events.append(Event("grab", {
                    "x": hovered.x, "y": hovered.y, "color": hovered.color,
                }))

        # Continuous drag
        held = self._held_by_slot(slot)
        if held is not None and slot.grab_state is GrabState.GRABBING:
            held.x, held.y = self._clamp_to_playfield(slot.cursor)

        # Exit GRABBING
        if (slot.grab_state is GrabState.IDLE
                and held is not None):
            self.moves += 1
            snapped = self._try_snap(held)
            if not snapped:
                self._events.append(Event("release", {
                    "x": held.x, "y": held.y, "color": held.color,
                }))
            held.held_by = None
            slot.held_id = None

    # ---- queries ----
    def _held_by_slot(self, slot: HandSlot) -> Shape | None:
        if slot.held_id is None:
            return None
        return next((s for s in self.shapes if s.id == slot.held_id), None)

    def _hover_for_slot(self, slot: HandSlot) -> Shape | None:
        nearest: Shape | None = None
        nd = float("inf")
        for s in self.shapes:
            if s.snapped or s.is_spawning or s.held_by is not None:
                continue
            d = math.hypot(slot.cursor[0] - s.x, slot.cursor[1] - s.y)
            if d < self.grab_radius and d < nd:
                nearest, nd = s, d
        return nearest

    def held_shape(self) -> Shape | None:
        return self._held_by_slot(self.primary_slot)

    def hovered_shape(self) -> Shape | None:
        if self.app_state is not AppState.PLAYING:
            return None
        if self.primary_slot.held_id is not None:
            return None
        return self._hover_for_slot(self.primary_slot)

    def all_held_shapes(self) -> list:
        return [s for s in self.shapes if s.held_by is not None]

    def target_for(self, shape: Shape) -> Shape:
        return next(t for t in self.targets if t.id == shape.target_id)

    def progress(self) -> tuple[int, int]:
        return sum(s.snapped for s in self.shapes), len(self.shapes)

    def elapsed_seconds(self) -> int:
        if self.started_at is None:
            return 0
        end = self.finished_at if self.finished_at else time.monotonic()
        return int(end - self.started_at)

    def snap_proximity(self, shape: Shape) -> float:
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
        self._events.append(Event("snap", {
            "x": shape.x, "y": shape.y, "color": shape.color,
        }))
        if self.all_matched and self.finished_at is None:
            self.finished_at = time.monotonic()
            self.app_state = (AppState.GAME_COMPLETE
                              if self.is_final_level
                              else AppState.LEVEL_COMPLETE)
            self._events.append(Event("level_complete", {
                "final": self.is_final_level,
                "level_name": self.level_name,
                "seconds": self.elapsed_seconds(),
                "moves": self.moves,
            }))
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
            if t.is_spawning:
                continue
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
        for entity in (*self.shapes, *self.targets):
            if entity.is_spawning:
                self._animate_spawn(entity, dt)

        # Scale animation: held shapes (any slot) get GRAB_SCALE,
        # primary-hovered gets HOVER_SCALE, others tween to 1.0
        primary_hover = self.hovered_shape()
        held_ids = {sl.held_id for sl in self.slots.values()
                    if sl.held_id is not None}

        for s in self.shapes:
            if s.is_spawning:
                continue
            if s.id in held_ids:
                target_scale = SHAPE_GRAB_SCALE
            elif s is primary_hover:
                target_scale = SHAPE_HOVER_SCALE
            else:
                target_scale = 1.0
            s.scale = tween_toward(s.scale, target_scale,
                                   SHAPE_SCALE_SPEED, dt)

        # Per-slot cursor scale
        for slot in self.slots.values():
            target = (1.15 if slot.grab_state is GrabState.GRABBING
                      else 1.0)
            slot.cursor_scale = tween_toward(slot.cursor_scale, target,
                                             CURSOR_SCALE_SPEED, dt)

    def _animate_spawn(self, entity: Shape, dt: float) -> None:
        entity.spawn_elapsed += dt
        if entity.spawn_elapsed < entity.spawn_delay:
            entity.x = entity.spawn_start_x
            entity.y = entity.spawn_start_y
            entity.scale = 0.0
            return
        t = (entity.spawn_elapsed - entity.spawn_delay) / entity.spawn_duration
        if t >= 1.0:
            entity.x = entity.home_x
            entity.y = entity.home_y
            entity.scale = 1.0
            entity.is_spawning = False
            return
        eased = ease_out_back(t)
        entity.x = (entity.spawn_start_x
                    + (entity.home_x - entity.spawn_start_x) * eased)
        entity.y = (entity.spawn_start_y
                    + (entity.home_y - entity.spawn_start_y) * eased)
        entity.scale = ease_out_quad(t)

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
            home_y = pf.top + half + spacing * target_slots[i]
            start_x = self.width + TARGET_SPAWN_OFFSCREEN + i * 40
            vx, vy = self._random_velocity()
            self.targets.append(Shape(
                id=i, kind=d["kind"], color=d["color"],
                x=start_x, y=home_y,
                home_x=target_x, home_y=home_y,
                spawn_start_x=start_x, spawn_start_y=home_y,
                vx=vx, vy=vy, scale=0.0,
                spawn_delay=TARGET_SPAWN_BASE_DELAY + i * TARGET_SPAWN_STAGGER,
                spawn_duration=TARGET_SPAWN_DURATION,
            ))

        for i, d in enumerate(defs):
            home_y = pf.top + half + spacing * shape_slots[i]
            start_x = -SHAPE_SPAWN_OFFSCREEN - i * 40
            self.shapes.append(Shape(
                id=i, kind=d["kind"], color=d["color"],
                x=start_x, y=home_y,
                home_x=shape_x, home_y=home_y,
                spawn_start_x=start_x, spawn_start_y=home_y,
                target_id=i, scale=0.0,
                spawn_delay=SHAPE_SPAWN_BASE_DELAY + i * SHAPE_SPAWN_STAGGER,
                spawn_duration=SHAPE_SPAWN_DURATION,
            ))

    def _random_velocity(self) -> tuple[float, float]:
        if not self.level["targets_move"]:
            return 0.0, 0.0
        lo, hi = self.level["speed_range"]
        mult = self._level_speed_mult.get(self.level_index, 1.0)
        speed = random.randint(int(lo * mult), int(hi * mult))
        sign = lambda: random.choice([-1, 1])  # noqa: E731
        axis = self.level["move_axis"]
        if axis == "y":
            return 0.0, speed * sign()
        if axis == "xy":
            return speed * 0.55 * sign(), speed * sign()
        return 0.0, 0.0