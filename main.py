import os
import time

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import cv2

from config import CAMERA_HEIGHT, CAMERA_INDEX, CAMERA_WIDTH, WINDOW_NAME
from game import GesturePuzzleGame
from renderer import draw_game
from vision import HandTracker


INTRO_DURATION = 5.0


def main():
    camera = cv2.VideoCapture(CAMERA_INDEX)
    if not camera.isOpened():
        print("Error: Cannot open webcam.")
        return

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    try:
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except Exception:
        pass

    tracker = HandTracker()
    game = GesturePuzzleGame()

    previous_time = time.time()
    fps = 0.0

    debug = False
    show_landmarks = False
    level_started_at = time.time()

    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                print("Warning: Failed to read webcam frame.")
                continue

            frame = cv2.flip(frame, 1)
            height, width = frame.shape[:2]

            game.resize(width, height)

            hand = tracker.process(frame, draw_landmarks=(debug and show_landmarks))
            game.update(hand)

            now = time.time()
            delta = now - previous_time
            previous_time = now
            if delta > 0:
                fps = 1 / delta

            intro_left = max(0.0, INTRO_DURATION - (now - level_started_at))

            draw_game(frame, game, fps, hand, debug=debug, intro_seconds_left=intro_left)

            cv2.imshow(WINDOW_NAME, frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            elif key == ord("r"):
                game.reset_level()
                level_started_at = time.time()
            elif key == ord("n"):
                game.next_level()
                level_started_at = time.time()
            elif key == ord("h"):
                debug = not debug
            elif key == ord("d"):
                show_landmarks = not show_landmarks

            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                break

    finally:
        tracker.close()
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()