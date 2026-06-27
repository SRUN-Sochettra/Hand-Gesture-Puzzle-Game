"""MediaPipe wrapper + One Euro Filter for cursor smoothing."""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass

import cv2
import mediapipe as mp

from config import (
    CURSOR_BETA, CURSOR_D_CUTOFF, CURSOR_MIN_CUTOFF, INFERENCE_WIDTH,
    MP_MAX_HANDS, MP_MIN_DETECTION_CONFIDENCE, MP_MIN_TRACKING_CONFIDENCE,
    MP_MODEL_COMPLEXITY, PINCH_RATIO_SMOOTHING,
)

log = logging.getLogger(__name__)


class _LowPass:
    def __init__(self) -> None:
        self._y: float | None = None

    def __call__(self, x: float, alpha: float) -> float:
        self._y = x if self._y is None else alpha * x + (1 - alpha) * self._y
        return self._y

    @property
    def last(self) -> float | None:
        return self._y


class OneEuroFilter:
    """1€ Filter (Casiez et al. CHI 2012)."""

    def __init__(self, min_cutoff: float = CURSOR_MIN_CUTOFF,
                 beta: float = CURSOR_BETA, d_cutoff: float = CURSOR_D_CUTOFF) -> None:
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._x = _LowPass()
        self._dx = _LowPass()
        self._last_t: float | None = None

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x: float, t: float) -> float:
        if self._last_t is None:
            self._last_t = t
            return self._x(x, 1.0)
        dt = max(1e-6, t - self._last_t)
        self._last_t = t
        prev = self._x.last if self._x.last is not None else x
        edx = self._dx((x - prev) / dt, self._alpha(self.d_cutoff, dt))
        cutoff = self.min_cutoff + self.beta * abs(edx)
        return self._x(x, self._alpha(cutoff, dt))

    def reset(self) -> None:
        self._x = _LowPass()
        self._dx = _LowPass()
        self._last_t = None


@dataclass(frozen=True)
class HandFrame:
    detected: bool
    cursor: tuple[int, int] | None = None
    pinch_ratio: float | None = None
    timestamp: float = 0.0


class HandTracker:
    def __init__(self) -> None:
        try:
            self._mp = mp.solutions.hands
            self._mp_draw = mp.solutions.drawing_utils
            self._mp_styles = mp.solutions.drawing_styles
            self._hands = self._mp.Hands(
                max_num_hands=MP_MAX_HANDS,
                model_complexity=MP_MODEL_COMPLEXITY,
                min_detection_confidence=MP_MIN_DETECTION_CONFIDENCE,
                min_tracking_confidence=MP_MIN_TRACKING_CONFIDENCE,
                static_image_mode=False,
            )
        except Exception as exc:
            raise RuntimeError(
                "Failed to initialize MediaPipe Hands. "
                "Install with: pip install mediapipe"
            ) from exc

        self._fx = OneEuroFilter()
        self._fy = OneEuroFilter()
        self._pinch_ema: float | None = None

    def process(self, frame, draw_landmarks: bool = False) -> HandFrame:
        h, w = frame.shape[:2]
        t = time.time()

        small = self._downscale(frame, w, h)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        result = self._hands.process(rgb)

        if not result.multi_hand_landmarks:
            self._pinch_ema = None
            return HandFrame(detected=False, timestamp=t)

        lms = result.multi_hand_landmarks[0]
        if draw_landmarks:
            self._mp_draw.draw_landmarks(
                frame, lms, self._mp.HAND_CONNECTIONS,
                self._mp_styles.get_default_hand_landmarks_style(),
                self._mp_styles.get_default_hand_connections_style(),
            )

        return HandFrame(
            detected=True,
            cursor=self._cursor(lms, w, h, t),
            pinch_ratio=self._smoothed_pinch(self._pinch_ratio(lms)),
            timestamp=t,
        )

    def reset_filter(self) -> None:
        self._fx.reset()
        self._fy.reset()
        self._pinch_ema = None

    def close(self) -> None:
        self._hands.close()

    # ---- internals ----
    @staticmethod
    def _downscale(frame, w: int, h: int):
        if w <= INFERENCE_WIDTH:
            return frame
        new_h = int(h * (INFERENCE_WIDTH / w))
        return cv2.resize(frame, (INFERENCE_WIDTH, new_h), interpolation=cv2.INTER_AREA)

    def _cursor(self, lms, w: int, h: int, t: float) -> tuple[int, int]:
        idx = lms.landmark[self._mp.HandLandmark.INDEX_FINGER_TIP]
        fx = self._fx(idx.x, t)
        fy = self._fy(idx.y, t)
        x = int(max(0.0, min(1.0, fx)) * (w - 1))
        y = int(max(0.0, min(1.0, fy)) * (h - 1))
        return x, y

    def _pinch_ratio(self, lms) -> float | None:
        lm = lms.landmark
        thumb = lm[self._mp.HandLandmark.THUMB_TIP]
        index = lm[self._mp.HandLandmark.INDEX_FINGER_TIP]
        wrist = lm[self._mp.HandLandmark.WRIST]
        middle = lm[self._mp.HandLandmark.MIDDLE_FINGER_MCP]
        pinch = math.hypot(thumb.x - index.x, thumb.y - index.y)
        size = math.hypot(wrist.x - middle.x, wrist.y - middle.y)
        return None if size <= 1e-5 else pinch / size

    def _smoothed_pinch(self, ratio: float | None) -> float | None:
        if ratio is None:
            self._pinch_ema = None
            return None
        a = PINCH_RATIO_SMOOTHING
        self._pinch_ema = ratio if self._pinch_ema is None else a * ratio + (1 - a) * self._pinch_ema
        return self._pinch_ema