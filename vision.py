import math
from dataclasses import dataclass

import cv2
import mediapipe as mp

from config import (
    MAX_HANDS,
    MIN_DETECTION_CONFIDENCE,
    MIN_TRACKING_CONFIDENCE,
)

INFERENCE_WIDTH = 480

ACTIVE_AREA_X = 0.74
ACTIVE_AREA_Y = 0.70


@dataclass
class HandResult:
    detected: bool
    cursor: tuple[int, int] | None = None
    pinch_ratio: float | None = None


class HandTracker:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_styles = mp.solutions.drawing_styles

        self.hands = self.mp_hands.Hands(
            max_num_hands=MAX_HANDS,
            model_complexity=0,
            min_detection_confidence=MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=MIN_TRACKING_CONFIDENCE,
            static_image_mode=False,
        )

    def process(self, frame, draw_landmarks=False) -> HandResult:
        height, width = frame.shape[:2]

        if width > INFERENCE_WIDTH:
            inference_height = int(height * (INFERENCE_WIDTH / width))
            small = cv2.resize(
                frame,
                (INFERENCE_WIDTH, inference_height),
                interpolation=cv2.INTER_AREA,
            )
        else:
            small = frame

        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.hands.process(rgb)

        if not results.multi_hand_landmarks:
            return HandResult(detected=False)

        landmarks = results.multi_hand_landmarks[0]

        if draw_landmarks:
            self.mp_draw.draw_landmarks(
                frame,
                landmarks,
                self.mp_hands.HAND_CONNECTIONS,
                self.mp_styles.get_default_hand_landmarks_style(),
                self.mp_styles.get_default_hand_connections_style(),
            )

        return HandResult(
            detected=True,
            cursor=self._cursor_position(landmarks, width, height),
            pinch_ratio=self._pinch_ratio(landmarks),
        )

    def _cursor_position(self, landmarks, width, height):
        lm = landmarks.landmark

        thumb = lm[self.mp_hands.HandLandmark.THUMB_TIP]
        index = lm[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]

        nx = (thumb.x + index.x) / 2
        ny = (thumb.y + index.y) / 2

        margin_x = (1.0 - ACTIVE_AREA_X) / 2
        margin_y = (1.0 - ACTIVE_AREA_Y) / 2

        nx = (nx - margin_x) / ACTIVE_AREA_X
        ny = (ny - margin_y) / ACTIVE_AREA_Y

        nx = min(1.0, max(0.0, nx))
        ny = min(1.0, max(0.0, ny))

        x = int(nx * width)
        y = int(ny * height)

        return max(0, min(width - 1, x)), max(0, min(height - 1, y))

    def _pinch_ratio(self, landmarks):
        lm = landmarks.landmark

        thumb = lm[self.mp_hands.HandLandmark.THUMB_TIP]
        index = lm[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        wrist = lm[self.mp_hands.HandLandmark.WRIST]
        middle_mcp = lm[self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP]

        pinch_distance = math.hypot(thumb.x - index.x, thumb.y - index.y)
        hand_size = math.hypot(wrist.x - middle_mcp.x, wrist.y - middle_mcp.y)

        if hand_size <= 0:
            return None

        return pinch_distance / hand_size

    def close(self):
        self.hands.close()