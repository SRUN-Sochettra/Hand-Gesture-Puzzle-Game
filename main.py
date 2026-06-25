import os
import time

# Reduce TensorFlow/MediaPipe console noise.
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import cv2

from config import CAMERA_HEIGHT, CAMERA_INDEX, CAMERA_WIDTH, WINDOW_NAME
from game import GesturePuzzleGame
from renderer import draw_game
from vision import HandTracker


def main():
    camera = cv2.VideoCapture(CAMERA_INDEX)

    if not camera.isOpened():
        print("Error: Cannot open webcam.")
        return

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    tracker = HandTracker()
    game = GesturePuzzleGame()

    previous_time = time.time()
    fps = 0.0

    try:
        while True:
            ok, frame = camera.read()

            if not ok:
                print("Warning: Failed to read webcam frame.")
                continue

            frame = cv2.flip(frame, 1)
            height, width = frame.shape[:2]

            game.resize(width, height)

            hand = tracker.process(frame, draw_landmarks=True)
            game.update(hand)

            now = time.time()
            delta = now - previous_time
            previous_time = now

            if delta > 0:
                fps = 1 / delta

            draw_game(frame, game, fps, hand)

            cv2.imshow(WINDOW_NAME, frame)

            key = cv2.waitKey(5) & 0xFF

            if key == ord("q"):
                break

            if key == ord("r"):
                game.reset_level()

            if key == ord("n"):
                game.next_level()

    finally:
        tracker.close()
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()