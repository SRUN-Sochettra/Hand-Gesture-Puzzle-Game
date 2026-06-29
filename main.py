"""Entry point: camera, main loop, event routing, key bindings."""

from __future__ import annotations

import logging
import os
import time

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import cv2
import numpy as np

import audio
import persistence
import replay
from calibration import Calibration
from config import (
    CAMERA_FAIL_LIMIT, CAMERA_FALLBACK_INDICES, CAMERA_HEIGHT, CAMERA_INDEX,
    CAMERA_WIDTH, COLORS, INTRO_HINT_SECONDS, LEVEL_TRANSITION_SECONDS,
    SETTINGS_PANEL_LIFETIME, SHAKE_GAME_COMPLETE, SHAKE_LEVEL_COMPLETE,
    SHAKE_SNAP, TARGET_FPS, WINDOW_NAME,
)
from effects import EffectSystem
from game import AppState, GameState
from gestures import Gesture, HoldFireDetector
from motion import ScreenShake
from recording import VideoRecorder
from renderer import draw
from segmentation import Silhouette
from vision import HandTracker

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("gpgame")

_FRAME_BUDGET = 1.0 / TARGET_FPS

_CONFETTI_PALETTE = [
    COLORS["shape_red"], COLORS["shape_blue"], COLORS["shape_green"],
    COLORS["shape_purple"], COLORS["shape_orange"],
    COLORS["accent"], COLORS["primary"],
]


def _open_camera():
    indices = (CAMERA_INDEX, *[i for i in CAMERA_FALLBACK_INDICES
                               if i != CAMERA_INDEX])
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


def _apply_shake(frame, offset):
    dx, dy = offset
    if abs(dx) < 0.5 and abs(dy) < 0.5:
        return frame
    h, w = frame.shape[:2]
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_REPLICATE)


class App:
    """Owns mutable run state. Keeps main() readable."""

    def __init__(self) -> None:
        self.game = GameState()
        self.fx = EffectSystem()
        self.shake = ScreenShake()
        self.records = persistence.load()
        self.recorder = replay.Recorder()
        self.video = VideoRecorder()
        self.playback = replay.load_for_level(self.game.level_name)
        self.calibration = Calibration()
        self.gestures = HoldFireDetector()
        self.vignette_cache: dict = {}

        saved = persistence.load_calibration()
        if saved:
            self.game.pinch_grab_threshold = saved[0]
            self.game.pinch_release_threshold = saved[1]
            log.info("Loaded calibration: grab=%.2f release=%.2f", *saved)

        self.fps = 0.0
        self.level_started_at = time.monotonic()
        self.last_level_index = self.game.level_index
        self.is_new_best = False

        self.silhouette_on = True
        self.trail_on = True
        self.ghost_on = True
        self.debug = False
        self.show_landmarks = False
        self.settings_shown_at: float | None = None

    @property
    def gesture_hold_progress(self) -> float:
        return self.gestures.hold_progress(time.monotonic())

    def settings_state(self):
        if self.settings_shown_at is None:
            return None
        age = time.monotonic() - self.settings_shown_at
        if age > SETTINGS_PANEL_LIFETIME:
            return None
        alpha = max(0.0, 1.0 - (age - SETTINGS_PANEL_LIFETIME + 0.4) / 0.4)
        return {
            "visible": True,
            "alpha": min(1.0, alpha),
            "pinch": self.game.pinch_grab_threshold,
            "silhouette": self.silhouette_on,
            "trail": self.trail_on,
            "ghost": self.ghost_on,
        }

    def show_settings(self) -> None:
        self.settings_shown_at = time.monotonic()

    def reload_playback(self) -> None:
        self.playback = replay.load_for_level(self.game.level_name)

    def handle_events(self, frame_w: int) -> None:
        for ev in self.game.drain_events():
            kind = ev.kind
            if kind == "grab":
                audio.play("grab")
            elif kind == "release":
                audio.play("release")
            elif kind == "snap":
                self.fx.burst(ev.data["x"], ev.data["y"],
                              COLORS[ev.data["color"]])
                self.shake.trigger(SHAKE_SNAP, 0.14)
                audio.play_snap(ev.data["color"])
            elif kind == "level_complete":
                is_final = ev.data["final"]
                audio.play("game_complete" if is_final
                           else "level_complete")
                self.shake.trigger(
                    SHAKE_GAME_COMPLETE if is_final else SHAKE_LEVEL_COMPLETE,
                    0.3 if is_final else 0.22,
                )
                self.fx.confetti_burst(frame_w, _CONFETTI_PALETTE)
                if persistence.maybe_record(
                    self.records, ev.data["level_name"],
                    ev.data["seconds"], ev.data["moves"],
                ):
                    self.is_new_best = True
                    if not self.game.coop_mode:
                        replay.save_for_level(
                            ev.data["level_name"], self.recorder.serialize()
                        )
                        self.reload_playback()


def main() -> None:
    cam = _open_camera()
    if cam is None:
        log.error("No webcam found.")
        return

    try:
        tracker = HandTracker(max_hands=1)
    except RuntimeError as exc:
        log.error("%s", exc)
        cam.release()
        return

    silhouette = Silhouette()
    app = App()
    prev_t = time.monotonic()
    consecutive_failures = 0
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

    app.calibration.start()

    try:
        while True:
            frame_start = time.monotonic()
            ok, frame = cam.read()
            if not ok:
                consecutive_failures += 1
                if consecutive_failures > CAMERA_FAIL_LIMIT:
                    log.error("Camera read failed repeatedly. Exiting.")
                    break
                continue
            consecutive_failures = 0

            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            app.game.resize(w, h)

            hand = tracker.process(
                frame, draw_landmarks=(app.debug and app.show_landmarks),
                pinch_threshold=app.game.pinch_grab_threshold,
            )

            # --- Calibration takes over ---
            if app.calibration.is_active:
                ratio = (hand.primary.pinch_ratio
                         if hand.primary else None)
                app.calibration.feed(ratio)
                draw(frame, app.game, hand, app.fx, app.fps,
                     calibration=app.calibration,
                     vignette_cache=app.vignette_cache,
                     recording=app.video.is_recording)
                if app.video.is_recording:
                    app.video.write(frame)
                cv2.imshow(WINDOW_NAME, frame)
                key = cv2.waitKey(1) & 0xFF
                if key == 27:
                    break
                elif key == 32:
                    app.calibration.skip()
                prev_t = time.monotonic()
                continue

            # Apply calibration result once on completion
            if app.calibration.is_done and app.calibration.result is not None:
                grab, release = app.calibration.result
                app.game.pinch_grab_threshold = grab
                app.game.pinch_release_threshold = release
                persistence.save_calibration(grab, release)
                app.calibration.result = None
                tracker.reset_filter()
                log.info("Calibration applied: grab=%.2f release=%.2f",
                         grab, release)

            # --- Normal game flow ---
            sil_mask = (silhouette.mask_for(frame)
                        if app.silhouette_on and silhouette.available
                        else None)

            app.game.update(hand)

            now = time.monotonic()
            primary = hand.primary
            fired = None
            if primary is not None:
                fired = app.gestures.update(primary.gesture, now)
            else:
                app.gestures.reset()
            if fired is not None:
                if fired is Gesture.OPEN_PALM and app.game.app_state in (
                    AppState.PLAYING, AppState.PAUSED,
                ):
                    app.game.toggle_pause()
                elif fired is Gesture.POINT and app.game.app_state in (
                    AppState.LEVEL_COMPLETE, AppState.GAME_COMPLETE,
                ):
                    app.game.next_level()
                    tracker.reset_filter()
                    app.fx.clear()
                    app.level_started_at = time.monotonic()
                    app.last_level_index = app.game.level_index
                    app.is_new_best = False
                    app.recorder.reset()
                    app.reload_playback()

            if (app.trail_on and app.game.is_pinching
                    and primary is not None and primary.cursor):
                app.fx.add_trail(*primary.cursor)
            elif not app.game.is_pinching and app.fx.trail:
                app.fx.clear_trail()

            if (app.game.app_state is AppState.PLAYING
                    and not app.game.coop_mode and primary is not None):
                app.recorder.sample(now, app.game.cursor[0],
                                    app.game.cursor[1],
                                    app.game.is_pinching)

            app.handle_events(w)

            dt = now - prev_t
            prev_t = now
            if dt > 0:
                app.fps = (0.9 * app.fps + 0.1 * (1.0 / dt)
                           if app.fps > 0 else 1.0 / dt)
            app.fx.update(dt)

            if app.game.level_index != app.last_level_index:
                tracker.reset_filter()
                app.fx.clear()
                app.level_started_at = now
                app.last_level_index = app.game.level_index
                app.is_new_best = False
                app.recorder.reset()
                app.reload_playback()

            since_level_start = now - app.level_started_at
            intro_alpha = max(0.0, min(
                1.0, (INTRO_HINT_SECONDS - since_level_start) / 2.0))
            level_fade_alpha = max(
                0.0, 1.0 - since_level_start / LEVEL_TRANSITION_SECONDS)
            intro_card_t = (since_level_start
                            if app.game.app_state is AppState.PLAYING
                            else None)

            ghost_state = None
            if (app.ghost_on and not app.game.coop_mode
                    and app.game.app_state is AppState.PLAYING
                    and not app.playback.empty):
                ghost_state = app.playback.at(since_level_start)

            draw(
                frame, app.game, hand, app.fx, app.fps,
                debug=app.debug,
                intro_alpha=intro_alpha,
                level_fade_alpha=level_fade_alpha,
                best_record=persistence.best_for(app.records,
                                                 app.game.level_name),
                is_new_best=app.is_new_best,
                intro_card_t=intro_card_t,
                vignette_cache=app.vignette_cache,
                silhouette_mask=sil_mask,
                ghost_state=ghost_state,
                settings_state=app.settings_state(),
                gesture_hold=app.gesture_hold_progress,
                coop_mode=app.game.coop_mode,
                recording=app.video.is_recording,
            )

            frame = _apply_shake(frame, app.shake.update(dt))

            if app.video.is_recording:
                app.video.write(frame)

            cv2.imshow(WINDOW_NAME, frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            elif key == ord("r"):
                app.game.reset_level()
                tracker.reset_filter()
                app.fx.clear()
                app.level_started_at = now
                app.is_new_best = False
                app.recorder.reset()
            elif key == ord("n") and app.game.app_state in (
                AppState.LEVEL_COMPLETE, AppState.GAME_COMPLETE,
            ):
                app.game.next_level()
                tracker.reset_filter()
                app.fx.clear()
                app.level_started_at = time.monotonic()
                app.last_level_index = app.game.level_index
                app.is_new_best = False
                app.recorder.reset()
                app.reload_playback()
            elif key == ord("p"):
                app.game.toggle_pause()
            elif key == ord("h"):
                app.debug = not app.debug
            elif key == ord("d"):
                app.show_landmarks = not app.show_landmarks
            elif key == ord("s"):
                app.silhouette_on = not app.silhouette_on
                app.show_settings()
            elif key == ord("t"):
                app.trail_on = not app.trail_on
                app.show_settings()
            elif key == ord("g"):
                app.ghost_on = not app.ghost_on
                app.show_settings()
            elif key == ord("2"):
                app.game.coop_mode = not app.game.coop_mode
                tracker.set_max_hands(2 if app.game.coop_mode else 1)
                app.game.reset_level()
                app.level_started_at = time.monotonic()
                app.show_settings()
                log.info("Co-op mode: %s", app.game.coop_mode)
            elif key == ord("v"):
                if app.video.is_recording:
                    path = app.video.stop()
                    log.info("Saved video to %s", path)
                else:
                    app.video.start(frame)
                app.show_settings()
            elif key == ord("c"):
                app.calibration.start()
            elif key == ord(","):
                app.game.adjust_pinch_threshold(-1)
                persistence.save_calibration(app.game.pinch_grab_threshold,
                                             app.game.pinch_release_threshold)
                app.show_settings()
            elif key == ord("."):
                app.game.adjust_pinch_threshold(+1)
                persistence.save_calibration(app.game.pinch_grab_threshold,
                                             app.game.pinch_release_threshold)
                app.show_settings()
            elif key in (ord("?"), ord("/")):
                app.show_settings()

            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                break

            slack = _FRAME_BUDGET - (time.monotonic() - frame_start)
            if slack > 0.001:
                time.sleep(slack)
    finally:
        if app.video.is_recording:
            app.video.stop()
        silhouette.close()
        tracker.close()
        cam.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()