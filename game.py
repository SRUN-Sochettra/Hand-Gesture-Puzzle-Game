import math
import random
import time
from dataclasses import dataclass

from config import (
    ALL_SHAPES,
    CAMERA_HEIGHT,
    CAMERA_WIDTH,
    HAND_LOST_GRACE_FRAMES,
    LEVELS,
    MIN_SMOOTHING,
    PINCH_GRAB_THRESHOLD,
    PINCH_RELEASE_THRESHOLD,
    PLAYFIELD_MARGIN_BOTTOM,
    PLAYFIELD_MARGIN_TOP,
    PLAYFIELD_MARGIN_X,
    SMOOTHING,
    SMOOTHING_SPEED_SCALE,
    SNAP_LENIENCE_PER_100PXS,
)


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


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def smooth_point(current, target, smoothing):
    return (
        int(current[0] * smoothing + target[0] * (1 - smoothing)),
        int(current[1] * smoothing + target[1] * (1 - smoothing)),
    )


class GesturePuzzleGame:
    def __init__(self):
        self.width = CAMERA_WIDTH
        self.height = CAMERA_HEIGHT
        self.level_index = 0

        self.shapes: list[Shape] = []
        self.targets: list[Shape] = []

        self.cursor = (self.width // 2, self.height // 2)
        self.raw_cursor = self.cursor

        self.held_id: int | None = None
        self.is_pinching = False
        self.was_pinching = False
        self.frames_without_hand = 0

        self.moves = 0
        self.started_at = time.time()
        self.finished_at: float | None = None
        self.last_update = time.time()

        self.hand_speed = 0.0

        self.reset_level()

    # ---------- level / state ----------
    @property
    def level(self):
        return LEVELS[self.level_index]

    @property
    def level_number(self):
        return self.level_index + 1

    @property
    def total_levels(self):
        return len(LEVELS)

    @property
    def level_name(self):
        return self.level["name"]

    @property
    def shape_size(self):
        return self.level["shape_size"]

    @property
    def grab_distance(self):
        return self.level["grab_distance"]

    @property
    def snap_distance(self):
        return self.level["snap_distance"]

    @property
    def is_final_level(self):
        return self.level_index == len(LEVELS) - 1

    @property
    def won(self):
        return all(shape.snapped for shape in self.shapes)

    def playfield(self):
        """(left, top, right, bottom) safe rect in pixel coords."""
        left = int(self.width * PLAYFIELD_MARGIN_X)
        right = int(self.width * (1.0 - PLAYFIELD_MARGIN_X))
        top = int(self.height * PLAYFIELD_MARGIN_TOP)
        bottom = int(self.height * (1.0 - PLAYFIELD_MARGIN_BOTTOM))
        return left, top, right, bottom

    def reset_level(self):
        self.shapes.clear()
        self.targets.clear()

        self.cursor = (self.width // 2, self.height // 2)
        self.raw_cursor = self.cursor

        self.held_id = None
        self.is_pinching = False
        self.was_pinching = False
        self.frames_without_hand = 0

        self.moves = 0
        self.started_at = time.time()
        self.finished_at = None
        self.last_update = time.time()
        self.hand_speed = 0.0

        self._create_level()

    def next_level(self):
        if not self.won:
            return

        self.level_index = 0 if self.is_final_level else self.level_index + 1
        self.reset_level()

    def resize(self, width, height):
        if width == self.width and height == self.height:
            return

        self.width = width
        self.height = height
        self.reset_level()

    # ---------- main update ----------
    def update(self, hand):
        now = time.time()
        dt = min(now - self.last_update, 0.05)
        self.last_update = now

        if not self.won:
            self._move_targets(dt)
            self._sync_snapped_shapes_with_targets()

        # Hand lost: keep held_id during a short grace period so motion blur
        # doesn't drop a real drag, but pinch state must NEVER persist across
        # a loss event — that's how you get phantom grabs when the hand
        # reappears.
        if not hand.detected:
            self.frames_without_hand += 1
            self.hand_speed *= 0.9

            self.is_pinching = False

            if self.frames_without_hand > HAND_LOST_GRACE_FRAMES:
                self.held_id = None
                self.was_pinching = False

            return

        self.frames_without_hand = 0
        self.raw_cursor = hand.cursor

        # Adaptive smoothing.
        raw_delta = dist(self.cursor, self.raw_cursor)
        relax = min(1.0, raw_delta / SMOOTHING_SPEED_SCALE)
        smoothing = SMOOTHING * (1.0 - relax) + MIN_SMOOTHING * relax

        old_cursor = self.cursor
        self.cursor = smooth_point(self.cursor, self.raw_cursor, smoothing)

        cursor_delta = dist(old_cursor, self.cursor)
        if dt > 0:
            instant_speed = cursor_delta / dt
            self.hand_speed = self.hand_speed * 0.75 + instant_speed * 0.25

        # Pinch with hysteresis. Guard against a missing ratio (partial
        # detection) — never carry a stale "True" forward in that case.
        ratio = hand.pinch_ratio
        if ratio is None:
            self.is_pinching = False
        elif self.is_pinching:
            self.is_pinching = ratio < PINCH_RELEASE_THRESHOLD
        else:
            self.is_pinching = ratio < PINCH_GRAB_THRESHOLD

        just_grabbed = self.is_pinching and not self.was_pinching
        just_released = not self.is_pinching and self.was_pinching

        if just_grabbed:
            hovered = self.hovered_shape()
            if hovered:
                self.held_id = hovered.id

        held = self.held_shape()

        if held and not self.won:
            held.x, held.y = self._clamp_to_playfield(self.cursor)

        if just_released and held:
            self.moves += 1
            self._try_snap(held)
            self.held_id = None

        self.was_pinching = self.is_pinching

    # ---------- helpers ----------
    def elapsed_seconds(self):
        end = self.finished_at if self.finished_at else time.time()
        return int(end - self.started_at)

    def progress(self):
        return sum(shape.snapped for shape in self.shapes), len(self.shapes)

    def held_shape(self):
        if self.held_id is None:
            return None
        return next((s for s in self.shapes if s.id == self.held_id), None)

    def hovered_shape(self):
        if self.won:
            return None

        nearest = None
        nearest_distance = float("inf")

        for shape in self.shapes:
            if shape.snapped:
                continue

            d = dist(self.cursor, (shape.x, shape.y))

            if d < self.grab_distance and d < nearest_distance:
                nearest = shape
                nearest_distance = d

        return nearest

    def target_for(self, shape):
        return next(t for t in self.targets if t.id == shape.target_id)

    def _clamp_to_playfield(self, point):
        left, top, right, bottom = self.playfield()
        half = self.shape_size // 2
        x = min(max(point[0], left + half), right - half)
        y = min(max(point[1], top + half), bottom - half)
        return x, y

    def _try_snap(self, shape):
        target = self.target_for(shape)
        target_speed = math.hypot(target.vx, target.vy)
        lenience = (target_speed / 100.0) * SNAP_LENIENCE_PER_100PXS

        if dist((shape.x, shape.y), (target.x, target.y)) <= self.snap_distance + lenience:
            shape.x = target.x
            shape.y = target.y
            shape.snapped = True

            if self.won and self.finished_at is None:
                self.finished_at = time.time()

    def _move_targets(self, dt):
        if not self.level["targets_move"]:
            return

        left, top, right, bottom = self.playfield()
        half = self.shape_size // 2

        band_width = min(280, (right - left) // 2)
        right_limit = right - half - 4
        top_limit = top + half + 4
        bottom_limit = bottom - half - 4
        left_limit = max(left + half + 4, right - band_width)

        for target in self.targets:
            target.x += target.vx * dt
            target.y += target.vy * dt

            if target.y <= top_limit:
                target.y = top_limit
                target.vy *= -1
            elif target.y >= bottom_limit:
                target.y = bottom_limit
                target.vy *= -1

            if target.x <= left_limit:
                target.x = left_limit
                target.vx *= -1
            elif target.x >= right_limit:
                target.x = right_limit
                target.vx *= -1

    def _sync_snapped_shapes_with_targets(self):
        for shape in self.shapes:
            if not shape.snapped:
                continue
            target = self.target_for(shape)
            shape.x = target.x
            shape.y = target.y

    # ---------- level setup ----------
    def _create_level(self):
        count = self.level["shape_count"]
        definitions = ALL_SHAPES[:count]

        left, top, right, bottom = self.playfield()
        half = self.shape_size // 2

        shape_x = left + half + 4
        target_x = right - half - 4

        usable_height = max(1, bottom - top - self.shape_size)
        spacing = usable_height // max(1, count - 1) if count > 1 else 0

        target_slots = list(range(count))
        shape_slots = list(range(count))
        random.shuffle(target_slots)
        random.shuffle(shape_slots)

        for i, definition in enumerate(definitions):
            target_y = top + half + spacing * target_slots[i]
            vx, vy = self._target_velocity()

            self.targets.append(
                Shape(
                    id=i,
                    kind=definition["kind"],
                    color=definition["color"],
                    x=target_x,
                    y=target_y,
                    vx=vx,
                    vy=vy,
                )
            )

        for i, definition in enumerate(definitions):
            shape_y = top + half + spacing * shape_slots[i]

            self.shapes.append(
                Shape(
                    id=i,
                    kind=definition["kind"],
                    color=definition["color"],
                    x=shape_x,
                    y=shape_y,
                    target_id=i,
                )
            )

    def _target_velocity(self):
        if not self.level["targets_move"]:
            return 0.0, 0.0

        speed = random.randint(
            self.level["target_speed_min"],
            self.level["target_speed_max"],
        )

        axis = self.level["move_axis"]

        if axis == "y":
            return 0.0, speed * random.choice([-1, 1])

        if axis == "xy":
            vx = speed * 0.55 * random.choice([-1, 1])
            vy = speed * random.choice([-1, 1])
            return vx, vy

        return 0.0, 0.0