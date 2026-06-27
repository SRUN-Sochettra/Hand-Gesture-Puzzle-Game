import math

import cv2
import numpy as np

from config import COLORS, HAND_SPEED_METER_MAX


def draw_game(frame, game, fps, hand, debug=False, intro_seconds_left=0):
    height, width = frame.shape[:2]

    if debug:
        _draw_playfield(frame, game)

    hovered = game.hovered_shape()
    held = game.held_shape()

    snapped, total = game.progress()
    title = (
        f"L{game.level_number}/{game.total_levels} "
        f"{game.level_name}   "
        f"{snapped}/{total}   "
        f"{game.moves} moves   "
        f"{game.elapsed_seconds()}s"
    )
    _text(frame, title, (16, 34), scale=0.6)

    _text(
        frame,
        f"{fps:.0f} fps",
        (width - 96, 34),
        scale=0.55,
        color=COLORS["success"] if fps >= 24 else COLORS["yellow"],
    )

    for target in game.targets:
        is_target = held is not None and target.id == held.target_id
        _draw_shape(
            frame, target, game.shape_size,
            outline=True,
            target_ring=is_target,
            snap_distance=game.snap_distance,
        )

    for shape in game.shapes:
        _draw_shape(
            frame, shape, game.shape_size,
            outline=False,
            hovered=(hovered is not None and hovered.id == shape.id),
            snap_distance=game.snap_distance,
        )

    _draw_cursor(frame, game.cursor, game.is_pinching)

    if intro_seconds_left > 0:
        alpha = min(1.0, intro_seconds_left / 2.0)
        hint = "Pinch thumb + index to grab. Release on the matching target."
        _fading_text(frame, hint, (width // 2, height - 40), scale=0.6, alpha=alpha)

    if debug:
        _draw_speed_meter(frame, game.hand_speed, x=16, y=58)
        _draw_pinch_meter(frame, hand, x=width - 260, y=58)
        status = "hand ok" if hand.detected else "no hand"
        _text(
            frame, status,
            (width - 130, height - 18),
            scale=0.5,
            color=COLORS["success"] if hand.detected else COLORS["yellow"],
        )
        keys = "R reset  N next  H hud  D landmarks  Q quit"
        _text(frame, keys, (16, height - 18), scale=0.5)

    if game.won:
        _win_overlay(frame, game)


def _draw_playfield(frame, game):
    left, top, right, bottom = game.playfield()
    cv2.rectangle(frame, (left, top), (right, bottom), COLORS["playfield"], 1, cv2.LINE_AA)


def _draw_shape(frame, shape, size, outline=False, hovered=False, target_ring=False, snap_distance=60):
    x, y = int(shape.x), int(shape.y)
    half = size // 2
    color = COLORS[shape.color]

    if target_ring:
        cv2.circle(frame, (x, y), snap_distance, COLORS["yellow"], 2, cv2.LINE_AA)

    if hovered:
        cv2.circle(frame, (x, y), half + 12, COLORS["white"], 2, cv2.LINE_AA)

    if outline:
        _outline_shape(frame, shape.kind, x, y, size, color)
        return

    if shape.snapped:
        _filled_shape(frame, shape.kind, x + 4, y + 4, size, (20, 20, 20))

    _filled_shape(frame, shape.kind, x, y, size, color)
    cv2.circle(frame, (x - 14, y - 14), 6, COLORS["white"], -1, cv2.LINE_AA)


def _filled_shape(frame, kind, x, y, size, color):
    half = size // 2
    if kind == "square":
        cv2.rectangle(frame, (x - half, y - half), (x + half, y + half), color, -1, cv2.LINE_AA)
    elif kind == "circle":
        cv2.circle(frame, (x, y), half, color, -1, cv2.LINE_AA)
    else:
        cv2.fillPoly(frame, [_points(kind, x, y, size)], color, lineType=cv2.LINE_AA)


def _outline_shape(frame, kind, x, y, size, color):
    half = size // 2
    if kind == "square":
        cv2.rectangle(frame, (x - half, y - half), (x + half, y + half), color, 3, cv2.LINE_AA)
    elif kind == "circle":
        cv2.circle(frame, (x, y), half, color, 3, cv2.LINE_AA)
    else:
        cv2.polylines(frame, [_points(kind, x, y, size)], True, color, 3, cv2.LINE_AA)


def _points(kind, x, y, size):
    half = size // 2
    if kind == "triangle":
        return np.array(
            [(x, y - half), (x + half, y + half), (x - half, y + half)],
            np.int32,
        )
    if kind == "diamond":
        return np.array(
            [(x, y - half), (x + half, y), (x, y + half), (x - half, y)],
            np.int32,
        )
    points = []
    radius = half
    for i in range(5):
        angle = -math.pi / 2 + i * 2 * math.pi / 5
        px = int(x + math.cos(angle) * radius)
        py = int(y + math.sin(angle) * radius)
        points.append((px, py))
    return np.array(points, np.int32)


def _draw_cursor(frame, pos, grabbing):
    color = COLORS["cursor_grab"] if grabbing else COLORS["cursor_idle"]
    radius = 18 if grabbing else 13
    cv2.circle(frame, pos, radius, color, -1, cv2.LINE_AA)
    cv2.circle(frame, pos, radius, COLORS["white"], 2, cv2.LINE_AA)


def _draw_speed_meter(frame, speed, x, y):
    width, height = 220, 12
    ratio = min(speed / HAND_SPEED_METER_MAX, 1.0)
    filled = int(width * ratio)

    if ratio < 0.35:
        color = COLORS["success"]
    elif ratio < 0.7:
        color = COLORS["yellow"]
    else:
        color = COLORS["danger"]

    cv2.rectangle(frame, (x, y), (x + width, y + height), COLORS["panel"], -1)
    cv2.rectangle(frame, (x, y), (x + filled, y + height), color, -1)
    cv2.rectangle(frame, (x, y), (x + width, y + height), COLORS["white"], 1)

    cv2.putText(
        frame, f"speed {int(speed)}",
        (x + width + 10, y + height),
        cv2.FONT_HERSHEY_SIMPLEX, 0.45, COLORS["white"], 1, cv2.LINE_AA,
    )


def _draw_pinch_meter(frame, hand, x, y):
    width, height = 140, 12
    ratio = hand.pinch_ratio if hand.pinch_ratio is not None else 1.0
    ratio = min(max(ratio, 0.0), 1.0)
    filled = int(width * (1.0 - ratio))

    color = COLORS["cursor_grab"] if hand.detected and ratio < 0.4 else COLORS["yellow"]

    cv2.rectangle(frame, (x, y), (x + width, y + height), COLORS["panel"], -1)
    cv2.rectangle(frame, (x, y), (x + filled, y + height), color, -1)
    cv2.rectangle(frame, (x, y), (x + width, y + height), COLORS["white"], 1)

    label = f"pinch {ratio:.2f}" if hand.pinch_ratio is not None else "pinch -"
    cv2.putText(
        frame, label,
        (x + width + 10, y + height),
        cv2.FONT_HERSHEY_SIMPLEX, 0.45, COLORS["white"], 1, cv2.LINE_AA,
    )


def _win_overlay(frame, game):
    height, width = frame.shape[:2]

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, height), COLORS["black"], -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    if game.is_final_level:
        title = "GAME COMPLETE"
        next_text = "N: restart from L1   Q: quit"
    else:
        title = "LEVEL CLEAR"
        next_text = "N: next   R: replay"

    cv2.putText(
        frame, title,
        (width // 2 - 200, height // 2 - 30),
        cv2.FONT_HERSHEY_TRIPLEX, 1.6, COLORS["success"], 3, cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        f"{game.elapsed_seconds()}s   {game.moves} moves",
        (width // 2 - 130, height // 2 + 20),
        cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLORS["white"], 2, cv2.LINE_AA,
    )
    cv2.putText(
        frame, next_text,
        (width // 2 - 170, height // 2 + 60),
        cv2.FONT_HERSHEY_SIMPLEX, 0.65, COLORS["yellow"], 2, cv2.LINE_AA,
    )


def _text(frame, text, pos, scale=0.6, color=COLORS["white"]):
    x, y = pos
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 1 if scale < 0.55 else 2
    padding = 6

    size, baseline = cv2.getTextSize(text, font, scale, thickness)
    text_w, text_h = size

    overlay = frame.copy()
    cv2.rectangle(
        overlay,
        (x - padding, y - text_h - padding),
        (x + text_w + padding, y + baseline + padding),
        COLORS["black"],
        -1,
    )
    cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)
    cv2.putText(frame, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)


def _fading_text(frame, text, center, scale=0.6, alpha=1.0):
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 2

    size, _ = cv2.getTextSize(text, font, scale, thickness)
    text_w, text_h = size
    x = center[0] - text_w // 2
    y = center[1]
    padding = 8

    overlay = frame.copy()
    cv2.rectangle(
        overlay,
        (x - padding, y - text_h - padding),
        (x + text_w + padding, y + padding),
        COLORS["black"], -1,
    )
    cv2.addWeighted(overlay, 0.45 * alpha, frame, 1 - 0.45 * alpha, 0, frame)

    color = tuple(int(c * alpha) for c in COLORS["white"])
    cv2.putText(frame, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)