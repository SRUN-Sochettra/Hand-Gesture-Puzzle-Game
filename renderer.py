"""Pure rendering. No state mutation. ROI-based label drawing for speed."""

from __future__ import annotations

import math
import time

import cv2
import numpy as np

from config import (
    COLORS, HAND_SPEED_METER_MAX, TARGET_RING_PULSE_HZ,
)
from effects import EffectSystem
from game import AppState, GameState, Shape
from vision import HandFrame


# ---------- public ----------
def draw(
    frame,
    game: GameState,
    hand: HandFrame,
    fx: EffectSystem,
    fps: float,
    *,
    debug: bool = False,
    intro_alpha: float = 0.0,
    level_fade_alpha: float = 0.0,
) -> None:
    if debug:
        _playfield_outline(frame, game)

    held = game.held_shape()
    hovered = game.hovered_shape()

    for t in game.targets:
        snap_proximity = 0.0
        ringed = held is not None and t.id == held.target_id
        if ringed:
            held_shape = game.held_shape()
            if held_shape is not None:
                snap_proximity = game.snap_proximity(held_shape)
        _draw_target(frame, t, game.shape_size, ringed=ringed,
                     snap_radius=game.snap_radius, snap_proximity=snap_proximity)

    for s in game.shapes:
        _draw_shape(frame, s, game.shape_size,
                    hovered=(hovered is not None and hovered.id == s.id))

    _draw_particles(frame, fx)
    _draw_rings(frame, fx)

    if game.app_state is not AppState.READY:
        _draw_cursor(frame, game.cursor, game.cursor_scale, grabbing=game.is_pinching)

    _draw_status_bar(frame, game, fps)

    if intro_alpha > 0 and game.app_state is AppState.PLAYING:
        _intro_hint(frame, intro_alpha)

    if debug:
        _debug_overlay(frame, game, hand)

    if game.app_state is AppState.READY:
        _ready_overlay(frame, hand)
    elif game.app_state is AppState.PAUSED:
        _pause_overlay(frame)
    elif game.app_state in (AppState.LEVEL_COMPLETE, AppState.GAME_COMPLETE):
        _win_overlay(frame, game)

    if level_fade_alpha > 0:
        _solid_overlay(frame, COLORS["bg_dim"], level_fade_alpha)


# ---------- shapes ----------
def _draw_target(frame, t: Shape, size: int, *, ringed: bool,
                 snap_radius: int, snap_proximity: float) -> None:
    x, y = int(t.x), int(t.y)
    if ringed:
        # Pulse the ring when shape is near snap.
        pulse = 0.5 + 0.5 * math.sin(time.time() * 2 * math.pi * TARGET_RING_PULSE_HZ)
        intensity = 0.4 + 0.6 * snap_proximity
        ring_color = _blend(COLORS["outline"], COLORS["success"], intensity)
        radius = snap_radius + int(3 * pulse * (0.5 + snap_proximity))
        cv2.circle(frame, (x, y), radius, ring_color, 2, cv2.LINE_AA)
    _outline_shape(frame, t.kind, x, y, size, COLORS[t.color])


def _draw_shape(frame, s: Shape, size: int, *, hovered: bool) -> None:
    x, y = int(s.x), int(s.y)
    size_anim = int(size * s.scale)

    # Drop shadow
    if not s.snapped:
        _filled_shape(frame, s.kind, x + 4, y + 5, size_anim, COLORS["shadow"])

    # Glow when picked up: faint ring outside the shape
    if s.scale > 1.05 and not s.snapped:
        glow_alpha = min(1.0, (s.scale - 1.0) / 0.18)
        _soft_ring(frame, (x, y), size_anim // 2 + 8, COLORS[s.color], glow_alpha * 0.5)

    _filled_shape(frame, s.kind, x, y, size_anim, COLORS[s.color])

    if hovered and not s.snapped:
        cv2.circle(frame, (x, y), size_anim // 2 + 10,
                   COLORS["text_primary"], 2, cv2.LINE_AA)


# ---------- effects ----------
def _draw_particles(frame, fx: EffectSystem) -> None:
    for p in fx.particles:
        fade = 1.0 - p.progress
        r = max(1, int(p.size * (1.0 - 0.6 * p.progress)))
        color = tuple(int(c * fade) for c in p.color)
        cv2.circle(frame, (int(p.x), int(p.y)), r, color, -1, cv2.LINE_AA)


def _draw_rings(frame, fx: EffectSystem) -> None:
    for r in fx.rings:
        t = r.progress
        radius = int(r.max_radius * (0.3 + 0.7 * t))
        fade = 1.0 - t
        color = tuple(int(c * fade) for c in r.color)
        thickness = max(1, int(3 * (1 - t * 0.7)))
        cv2.circle(frame, (int(r.x), int(r.y)), radius, color, thickness, cv2.LINE_AA)


# ---------- cursor ----------
def _draw_cursor(frame, pos: tuple[int, int], scale: float, *, grabbing: bool) -> None:
    color = COLORS["cursor_grab"] if grabbing else COLORS["cursor_idle"]
    base_r = 14 if grabbing else 10
    r = int(base_r * scale)
    cv2.circle(frame, pos, r + 4, COLORS["bg_dim"], -1, cv2.LINE_AA)
    cv2.circle(frame, pos, r, color, -1, cv2.LINE_AA)
    cv2.circle(frame, pos, r, COLORS["text_primary"], 2, cv2.LINE_AA)


# ---------- HUD ----------
def _draw_status_bar(frame, game: GameState, fps: float) -> None:
    w = frame.shape[1]
    snapped, total = game.progress()
    left = (f"L{game.level_number}/{game.total_levels}  {game.level_name}   "
            f"{snapped}/{total}   {game.moves} moves   {game.elapsed_seconds()}s")
    _label(frame, left, (16, 30), scale=0.6)

    fps_color = COLORS["success"] if fps >= 24 else COLORS["warning"]
    _label(frame, f"{fps:.0f} fps", (w - 100, 30), scale=0.55, color=fps_color)


def _intro_hint(frame, alpha: float) -> None:
    h, w = frame.shape[:2]
    _fading_label(frame, "Pinch thumb + index to grab. Release on the matching target.",
                  (w // 2, h - 36), scale=0.6, alpha=alpha)


def _debug_overlay(frame, game: GameState, hand: HandFrame) -> None:
    h, w = frame.shape[:2]
    _speed_bar(frame, game.hand_speed_pxs, x=16, y=52)
    _pinch_bar(frame, hand, x=w - 260, y=52)
    _label(frame, "hand ok" if hand.detected else "no hand",
           (w - 130, h - 16), scale=0.5,
           color=COLORS["success"] if hand.detected else COLORS["warning"])
    _label(frame, "R reset  N next  P pause  H hud  D landmarks  Q quit",
           (16, h - 16), scale=0.5)


# ---------- overlays ----------
def _ready_overlay(frame, hand: HandFrame) -> None:
    h, w = frame.shape[:2]
    _solid_overlay(frame, COLORS["bg_dim"], 0.55)
    title = "Show your hand to begin"
    sub = "MediaPipe is searching..." if not hand.detected else "Got it. Starting..."
    _centered_text(frame, title, h // 2 - 20, scale=1.2, color=COLORS["text_primary"])
    sub_color = COLORS["text_muted"] if not hand.detected else COLORS["success"]
    _centered_text(frame, sub, h // 2 + 30, scale=0.7, color=sub_color)


def _pause_overlay(frame) -> None:
    h, w = frame.shape[:2]
    _solid_overlay(frame, COLORS["bg_dim"], 0.55)
    _centered_text(frame, "PAUSED", h // 2 - 10, scale=1.6, color=COLORS["warning"])
    _centered_text(frame, "P to resume   R to restart   Q to quit",
                   h // 2 + 40, scale=0.65, color=COLORS["text_muted"])


def _win_overlay(frame, game: GameState) -> None:
    h, w = frame.shape[:2]
    # Time-based fade-in (use finished_at as the anchor)
    elapsed_since_win = max(0.0, time.time() - (game.finished_at or time.time()))
    alpha = min(1.0, elapsed_since_win / 0.4)
    _solid_overlay(frame, COLORS["bg_dim"], 0.6 * alpha)

    title = "GAME COMPLETE" if game.is_final_level else "LEVEL CLEAR"
    sub = ("N: restart from L1     Q: quit"
           if game.is_final_level else "N: next     R: replay")
    color = tuple(int(c * alpha) for c in COLORS["success"])
    sub_color = tuple(int(c * alpha) for c in COLORS["warning"])
    stat_color = tuple(int(c * alpha) for c in COLORS["text_primary"])

    _centered_text(frame, title, h // 2 - 30, scale=1.5, color=color,
                   font=cv2.FONT_HERSHEY_TRIPLEX, thickness=3)
    _centered_text(frame, f"{game.elapsed_seconds()}s   {game.moves} moves",
                   h // 2 + 20, scale=0.8, color=stat_color, thickness=2)
    _centered_text(frame, sub, h // 2 + 60, scale=0.65, color=sub_color, thickness=2)


def _playfield_outline(frame, game: GameState) -> None:
    pf = game.playfield()
    cv2.rectangle(frame, (pf.left, pf.top), (pf.right, pf.bottom),
                  COLORS["outline"], 1, cv2.LINE_AA)


# ---------- primitives ----------
def _filled_shape(frame, kind: str, x: int, y: int, size: int, color) -> None:
    half = size // 2
    if kind == "square":
        cv2.rectangle(frame, (x - half, y - half), (x + half, y + half), color, -1, cv2.LINE_AA)
    elif kind == "circle":
        cv2.circle(frame, (x, y), half, color, -1, cv2.LINE_AA)
    else:
        cv2.fillPoly(frame, [_polygon(kind, x, y, size)], color, lineType=cv2.LINE_AA)


def _outline_shape(frame, kind: str, x: int, y: int, size: int, color) -> None:
    half = size // 2
    if kind == "square":
        cv2.rectangle(frame, (x - half, y - half), (x + half, y + half), color, 3, cv2.LINE_AA)
    elif kind == "circle":
        cv2.circle(frame, (x, y), half, color, 3, cv2.LINE_AA)
    else:
        cv2.polylines(frame, [_polygon(kind, x, y, size)], True, color, 3, cv2.LINE_AA)


def _polygon(kind: str, x: int, y: int, size: int) -> np.ndarray:
    half = size // 2
    if kind == "triangle":
        return np.array([(x, y - half), (x + half, y + half),
                         (x - half, y + half)], np.int32)
    if kind == "diamond":
        return np.array([(x, y - half), (x + half, y),
                         (x, y + half), (x - half, y)], np.int32)
    pts = []
    for i in range(5):
        a = -math.pi / 2 + i * 2 * math.pi / 5
        pts.append((int(x + math.cos(a) * half), int(y + math.sin(a) * half)))
    return np.array(pts, np.int32)


def _soft_ring(frame, center: tuple[int, int], radius: int, color, alpha: float) -> None:
    """Cheap glow: ROI alpha-blend a ring."""
    cx, cy = center
    r = radius
    x1, y1 = max(0, cx - r - 4), max(0, cy - r - 4)
    x2 = min(frame.shape[1], cx + r + 4)
    y2 = min(frame.shape[0], cy + r + 4)
    if x2 <= x1 or y2 <= y1:
        return
    roi = frame[y1:y2, x1:x2]
    overlay = roi.copy()
    cv2.circle(overlay, (cx - x1, cy - y1), r, color, 4, cv2.LINE_AA)
    cv2.addWeighted(overlay, alpha, roi, 1 - alpha, 0, roi)


# ---------- bars ----------
def _speed_bar(frame, speed: float, *, x: int, y: int) -> None:
    w, h = 220, 10
    ratio = min(speed / HAND_SPEED_METER_MAX, 1.0)
    color = (COLORS["success"] if ratio < 0.35
             else COLORS["warning"] if ratio < 0.7 else COLORS["danger"])
    _bar(frame, x, y, w, h, ratio, color)
    cv2.putText(frame, f"speed {int(speed)}", (x + w + 10, y + h),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, COLORS["text_primary"], 1, cv2.LINE_AA)


def _pinch_bar(frame, hand: HandFrame, *, x: int, y: int) -> None:
    w, h = 140, 10
    ratio = hand.pinch_ratio if hand.pinch_ratio is not None else 1.0
    ratio = min(max(ratio, 0.0), 1.0)
    fill = 1.0 - ratio
    color = (COLORS["cursor_grab"] if hand.detected and ratio < 0.4
             else COLORS["warning"])
    _bar(frame, x, y, w, h, fill, color)
    label = f"pinch {ratio:.2f}" if hand.pinch_ratio is not None else "pinch -"
    cv2.putText(frame, label, (x + w + 10, y + h),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, COLORS["text_primary"], 1, cv2.LINE_AA)


def _bar(frame, x: int, y: int, w: int, h: int, ratio: float, color) -> None:
    cv2.rectangle(frame, (x, y), (x + w, y + h), COLORS["surface"], -1)
    cv2.rectangle(frame, (x, y), (x + int(w * ratio), y + h), color, -1)
    cv2.rectangle(frame, (x, y), (x + w, y + h), COLORS["text_muted"], 1)


# ---------- text (ROI-based, no full-frame copy) ----------
def _label(frame, text: str, pos: tuple[int, int], *,
           scale: float = 0.6, color=None) -> None:
    color = color or COLORS["text_primary"]
    x, y = pos
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 1 if scale < 0.55 else 2
    pad = 6
    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)

    x1, y1 = max(0, x - pad), max(0, y - th - pad)
    x2 = min(frame.shape[1], x + tw + pad)
    y2 = min(frame.shape[0], y + baseline + pad)
    if x2 > x1 and y2 > y1:
        roi = frame[y1:y2, x1:x2]
        roi[:] = (roi * 0.55).astype(np.uint8)  # darken in place; no copy

    cv2.putText(frame, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)


def _fading_label(frame, text: str, center: tuple[int, int], *,
                  scale: float, alpha: float) -> None:
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 2
    (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
    x = center[0] - tw // 2
    y = center[1]
    pad = 8

    x1, y1 = max(0, x - pad), max(0, y - th - pad)
    x2 = min(frame.shape[1], x + tw + pad)
    y2 = min(frame.shape[0], y + pad)
    if x2 > x1 and y2 > y1:
        roi = frame[y1:y2, x1:x2]
        darken = 1.0 - 0.5 * alpha
        roi[:] = (roi * darken).astype(np.uint8)

    color = tuple(int(c * alpha) for c in COLORS["text_primary"])
    cv2.putText(frame, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)


def _centered_text(frame, text: str, y: int, *, scale: float,
                   color, font=cv2.FONT_HERSHEY_SIMPLEX, thickness: int = 2) -> None:
    w = frame.shape[1]
    (tw, _), _ = cv2.getTextSize(text, font, scale, thickness)
    cv2.putText(frame, text, ((w - tw) // 2, y),
                font, scale, color, thickness, cv2.LINE_AA)


def _solid_overlay(frame, color, alpha: float) -> None:
    overlay = np.full_like(frame, color, dtype=np.uint8)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


def _blend(a, b, t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))