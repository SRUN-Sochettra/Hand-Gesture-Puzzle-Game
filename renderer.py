import math

import cv2
import numpy as np

from config import COLORS, HAND_SPEED_METER_MAX


def draw_game(frame, game, fps, hand):
    height, width = frame.shape[:2]

    hovered = game.hovered_shape()
    held = game.held_shape()

    _panel(frame, (0, 0), (width, 96), 0.45)

    snapped, total = game.progress()
    title = (
        f"Level {game.level_number}/{game.total_levels}: {game.level_name} | "
        f"{snapped}/{total} matched | Moves: {game.moves} | Time: {game.elapsed_seconds()}s"
    )

    _text(frame, title, (20, 42), scale=0.65)

    _text(
        frame,
        f"FPS: {fps:.0f}",
        (width - 120, 42),
        scale=0.62,
        color=COLORS["success"] if fps >= 24 else COLORS["yellow"],
    )

    _draw_speed_meter(frame, game.hand_speed, x=20, y=68)

    _text(frame, "Drag shapes", (28, 125), scale=0.55)
    _text(frame, "Drop targets", (width - 170, 125), scale=0.55)

    for target in game.targets:
        is_target = held is not None and target.id == held.target_id
        _draw_shape(
            frame,
            target,
            game.shape_size,
            outline=True,
            target_ring=is_target,
            snap_distance=game.snap_distance,
        )

    for shape in game.shapes:
        _draw_shape(
            frame,
            shape,
            game.shape_size,
            outline=False,
            hovered=(hovered is not None and hovered.id == shape.id),
            snap_distance=game.snap_distance,
        )

    _draw_cursor(frame, game.cursor, game.is_pinching)

    _panel(frame, (0, height - 58), (width, height), 0.5)

    instruction = "Pinch: grab/drop | R: restart level | N: next after win | Q: quit"
    _text(frame, instruction, (20, height - 22), scale=0.58)

    status = "Hand detected" if hand.detected else "Show your hand to the camera"

    if hand.pinch_ratio is not None:
        status += f" | Pinch: {hand.pinch_ratio:.2f}"

    _text(
        frame,
        status,
        (width - 390, height - 22),
        scale=0.55,
        color=COLORS["success"] if hand.detected else COLORS["yellow"],
    )

    if game.won:
        _win_overlay(frame, game)


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

    cv2.circle(frame, (x - 14, y - 14), 7, COLORS["white"], -1, cv2.LINE_AA)


def _filled_shape(frame, kind, x, y, size, color):
    half = size // 2

    if kind == "square":
        cv2.rectangle(
            frame,
            (x - half, y - half),
            (x + half, y + half),
            color,
            -1,
            cv2.LINE_AA,
        )

    elif kind == "circle":
        cv2.circle(frame, (x, y), half, color, -1, cv2.LINE_AA)

    else:
        cv2.fillPoly(frame, [_points(kind, x, y, size)], color, lineType=cv2.LINE_AA)


def _outline_shape(frame, kind, x, y, size, color):
    half = size // 2

    if kind == "square":
        cv2.rectangle(
            frame,
            (x - half, y - half),
            (x + half, y + half),
            color,
            3,
            cv2.LINE_AA,
        )

    elif kind == "circle":
        cv2.circle(frame, (x, y), half, color, 3, cv2.LINE_AA)

    else:
        cv2.polylines(frame, [_points(kind, x, y, size)], True, color, 3, cv2.LINE_AA)


def _points(kind, x, y, size):
    half = size // 2

    if kind == "triangle":
        return np.array(
            [
                (x, y - half),
                (x + half, y + half),
                (x - half, y + half),
            ],
            np.int32,
        )

    if kind == "diamond":
        return np.array(
            [
                (x, y - half),
                (x + half, y),
                (x, y + half),
                (x - half, y),
            ],
            np.int32,
        )

    # Pentagon
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
    radius = 20 if grabbing else 15

    cv2.circle(frame, pos, radius, color, -1, cv2.LINE_AA)
    cv2.circle(frame, pos, radius, COLORS["white"], 2, cv2.LINE_AA)


def _draw_speed_meter(frame, speed, x, y):
    width = 260
    height = 16

    ratio = min(speed / HAND_SPEED_METER_MAX, 1.0)
    filled = int(width * ratio)

    if ratio < 0.35:
        color = COLORS["success"]
        label = "steady"
    elif ratio < 0.7:
        color = COLORS["yellow"]
        label = "moving"
    else:
        color = COLORS["danger"]
        label = "fast"

    cv2.rectangle(
        frame,
        (x, y),
        (x + width, y + height),
        COLORS["panel"],
        -1,
        cv2.LINE_AA,
    )

    cv2.rectangle(
        frame,
        (x, y),
        (x + filled, y + height),
        color,
        -1,
        cv2.LINE_AA,
    )

    cv2.rectangle(
        frame,
        (x, y),
        (x + width, y + height),
        COLORS["white"],
        1,
        cv2.LINE_AA,
    )

    cv2.putText(
        frame,
        f"Hand speed: {int(speed)} px/s ({label})",
        (x + width + 14, y + height - 2),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        COLORS["white"],
        1,
        cv2.LINE_AA,
    )


def _win_overlay(frame, game):
    height, width = frame.shape[:2]

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, height), COLORS["black"], -1)
    cv2.addWeighted(overlay, 0.68, frame, 0.32, 0, frame)

    if game.is_final_level:
        title = "GAME COMPLETE!"
        next_text = "Press N to restart from Level 1 or Q to quit"
    else:
        title = "LEVEL CLEAR!"
        next_text = "Press N for next level or R to replay"

    cv2.putText(
        frame,
        title,
        (width // 2 - 250, height // 2 - 40),
        cv2.FONT_HERSHEY_TRIPLEX,
        1.8,
        COLORS["success"],
        3,
        cv2.LINE_AA,
    )

    cv2.putText(
        frame,
        f"Level {game.level_number}/{game.total_levels} completed in {game.elapsed_seconds()}s with {game.moves} moves",
        (width // 2 - 330, height // 2 + 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.85,
        COLORS["white"],
        2,
        cv2.LINE_AA,
    )

    cv2.putText(
        frame,
        next_text,
        (width // 2 - 300, height // 2 + 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        COLORS["yellow"],
        2,
        cv2.LINE_AA,
    )


def _panel(frame, top_left, bottom_right, alpha):
    overlay = frame.copy()
    cv2.rectangle(overlay, top_left, bottom_right, COLORS["black"], -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


def _text(frame, text, pos, scale=0.65, color=COLORS["white"]):
    x, y = pos
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 2
    padding = 8

    size, baseline = cv2.getTextSize(text, font, scale, thickness)
    text_w, text_h = size

    cv2.rectangle(
        frame,
        (x - padding, y - text_h - padding),
        (x + text_w + padding, y + baseline + padding),
        COLORS["panel"],
        -1,
    )

    cv2.putText(frame, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)