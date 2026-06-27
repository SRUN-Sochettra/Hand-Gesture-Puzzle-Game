"""Entry point: camera, main loop, event routing, key bindings."""

from __future__ import annotations

import logging
import os
import time

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import cv2

from config import (
    CAMERA_FALLBACK_INDICES, CAMERA_HEIGHT, CAMERA_INDEX, CAMERA_WIDTH,
    COLORS, INTRO_HINT_SECONDS, LEVEL_TRANSITION_SECONDS, WINDOW_NAME,
)
from effects import EffectSystem
from game import AppState, GameState
from renderer import draw
from vision import HandTracker

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("gpgame")


def _open_camera() -> cv2.VideoCapture | None:
    indices = (CAMERA_INDEX, *[i for i in CAMERA_FALLBACK_INDICES if i != CAMERA_INDEX])
    for idx in indices:
        cam = cv2.VideoCapture(idx)
        if cam.isOpened():
            cam.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            cam.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            try:
                cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except cv2.error:
                pass
            log.info("Opened camera index %d", idx)
            return cam
        cam.release()
        log.warning("Camera index %d unavailable", idx)
    return None


def _handle_events(game: GameState, fx: EffectSystem) -> None:
    for ev in game.drain_events():
        if ev.kind == "snap":
            fx.burst(ev.data["x"], ev.data["y"], COLORS[ev.data["color"]])
        # "grab"/"release"/"level_complete" reserved for future hooks (sound, etc.)


def main() -> None:
    cam = _open_camera()
    if cam is None:
        log.error("No webcam found. Tried indices: %s",
                  (CAMERA_INDEX, *CAMERA_FALLBACK_INDICES))
        return

    try:
        tracker = HandTracker()
    except RuntimeError as exc:
        log.error("%s", exc)
        cam.release()
        return

    game = GameState()
    fx = EffectSystem()

    fps = 0.0
    prev_t = time.time()
    level_started_at = time.time()
    last_level_index = game.level_index

    debug = False
    show_landmarks = False
    consecutive_failures = 0

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

    try:
        while True:
            ok, frame = cam.read()
            if not ok:
                consecutive_failures += 1
                if consecutive_failures > 30:
                    log.error("Camera read failed repeatedly. Exiting.")
                    break
                continue
            consecutive_failures = 0

            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            game.resize(w, h)

            hand = tracker.process(frame, draw_landmarks=(debug and show_landmarks))
            game.update(hand)
            _handle_events(game, fx)

            now = time.time()
            dt = now - prev_t
            prev_t = now
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / dt) if fps > 0 else 1.0 / dt

            # Update effects every frame regardless of pause (they're cosmetic).
            fx.update(dt)

            # Reset filter and trigger fade when the level changes.
            if game.level_index != last_level_index:
                tracker.reset_filter()
                fx.clear()
                level_started_at = now
                last_level_index = game.level_index

            since_level_start = now - level_started_at
            intro_alpha = max(0.0, min(1.0,
                              (INTRO_HINT_SECONDS - since_level_start) / 2.0))
            level_fade_alpha = max(0.0,
                                   1.0 - since_level_start / LEVEL_TRANSITION_SECONDS)

            draw(
                frame, game, hand, fx, fps,
                debug=debug,
                intro_alpha=intro_alpha,
                level_fade_alpha=level_fade_alpha,
            )

            cv2.imshow(WINDOW_NAME, frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            elif key == ord("r"):
                game.reset_level()
                tracker.reset_filter()
                fx.clear()
                level_started_at = now
            elif key == ord("n"):
                if game.app_state in (AppState.LEVEL_COMPLETE, AppState.GAME_COMPLETE):
                    game.next_level()
                    tracker.reset_filter()
                    fx.clear()
                    level_started_at = time.time()
                    last_level_index = game.level_index
            elif key == ord("p"):
                game.toggle_pause()
            elif key == ord("h"):
                debug = not debug
            elif key == ord("d"):
                show_landmarks = not show_landmarks
            elif key == 32:  # Space
                if game.app_state is AppState.READY and hand.detected:
                    pass  # auto-starts when hand is detected

            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                break
    finally:
        tracker.close()
        cam.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()