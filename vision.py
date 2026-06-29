"""MediaPipe wrapper + One Euro Filter. Multi-hand aware."""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field

import cv2
import mediapipe as mp

from config import (
    CURSOR_BETA, CURSOR_D_CUTOFF, CURSOR_MIN_CUTOFF, INFERENCE_WIDTH,
    MP_MIN_DETECTION_CONFIDENCE, MP_MIN_TRACKING_CONFIDENCE,
    MP_MODEL_COMPLEXITY, PINCH_RATIO_SMOOTHING,
)
from gestures import Gesture, classify as classify_gesture

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
                 beta: float = CURSOR_BETA,
                 d_cutoff: float = CURSOR_D_CUTOFF) -> None:
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
class HandData:
    handedness: str
    cursor: tuple[int, int]
    pinch_ratio: float | None
    gesture: Gesture
    raw_landmarks: object


@dataclass(frozen=True)
class HandFrame:
    detected: bool
    hands: tuple = field(default_factory=tuple)
    timestamp: float = 0.0

    @property
    def primary(self) -> HandData | None:
        return self.hands[0] if self.hands else None

    @property
    def cursor(self):
        return self.primary.cursor if self.primary else None

    @property
    def pinch_ratio(self):
        return self.primary.pinch_ratio if self.primary else None

    def by_handedness(self, label: str) -> HandData | None:
        return next((h for h in self.hands if h.handedness == label), None)


class HandTracker:
    def __init__(self, max_hands: int = 1) -> None:
        try:
            self._mp = mp.solutions.hands
            self._mp_draw = mp.solutions.drawing_utils
            self._mp_styles = mp.solutions.drawing_styles
            self._hands = self._build(max_hands)
        except Exception as exc:
            raise RuntimeError(
                "Failed to initialize MediaPipe Hands. "
                "Install with: pip install mediapipe"
            ) from exc

        self._filters: dict[str, tuple[OneEuroFilter, OneEuroFilter]] = {}
        self._pinch_emas: dict[str, float] = {}

    def _build(self, max_hands: int):
        return self._mp.Hands(
            max_num_hands=max_hands,
            model_complexity=MP_MODEL_COMPLEXITY,
            min_detection_confidence=MP_MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=MP_MIN_TRACKING_CONFIDENCE,
            static_image_mode=False,
        )

    def set_max_hands(self, n: int) -> None:
        if self._hands is not None:
            self._hands.close()
        self._hands = self._build(n)
        self.reset_filter()

    def process(self, frame, draw_landmarks: bool = False,
                pinch_threshold: float = 0.34) -> HandFrame:
        h, w = frame.shape[:2]
        t = time.monotonic()
        small = self._downscale(frame, w, h)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        result = self._hands.process(rgb)

        if not result.multi_hand_landmarks:
            self._pinch_emas.clear()
            return HandFrame(detected=False, timestamp=t)

        hands_out: list[HandData] = []
        handed = result.multi_handedness or []
        for i, lms in enumerate(result.multi_hand_landmarks):
            label = (handed[i].classification[0].label
                     if i < len(handed) else f"Hand{i}")
            if draw_landmarks:
                self._mp_draw.draw_landmarks(
                    frame, lms, self._mp.HAND_CONNECTIONS,
                    self._mp_styles.get_default_hand_landmarks_style(),
                    self._mp_styles.get_default_hand_connections_style(),
                )
            cursor = self._cursor_for(label, lms, w, h, t)
            ratio = self._smoothed_pinch_for(label, self._pinch_ratio(lms))
            gesture = classify_gesture(lms, ratio, pinch_threshold)
            hands_out.append(HandData(
                handedness=label, cursor=cursor, pinch_ratio=ratio,
                gesture=gesture, raw_landmarks=lms,
            ))

        # Right first for stable solo semantics.
        hands_out.sort(key=lambda hd: 0 if hd.handedness == "Right" else 1)
        return HandFrame(detected=True, hands=tuple(hands_out), timestamp=t)

    def reset_filter(self) -> None:
        for fx, fy in self._filters.values():
            fx.reset()
            fy.reset()
        self._pinch_emas.clear()

    def close(self) -> None:
        if self._hands is not None:
            self._hands.close()

    # ---- internals ----
    @staticmethod
    def _downscale(frame, w: int, h: int):
        if w <= INFERENCE_WIDTH:
            return frame
        new_h = int(h * (INFERENCE_WIDTH / w))
        return cv2.resize(frame, (INFERENCE_WIDTH, new_h),
                          interpolation=cv2.INTER_AREA)

    def _cursor_for(self, label, lms, w, h, t):
        if label not in self._filters:
            self._filters[label] = (OneEuroFilter(), OneEuroFilter())
        fx, fy = self._filters[label]
        idx = lms.landmark[self._mp.HandLandmark.INDEX_FINGER_TIP]
        x = int(max(0.0, min(1.0, fx(idx.x, t))) * (w - 1))
        y = int(max(0.0, min(1.0, fy(idx.y, t))) * (h - 1))
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

    def _smoothed_pinch_for(self, label, ratio):
        if ratio is None:
            self._pinch_emas.pop(label, None)
            return None
        a = PINCH_RATIO_SMOOTHING
        prev = self._pinch_emas.get(label)
        new = ratio if prev is None else a * ratio + (1 - a) * prev
        self._pinch_emas[label] = new
        return new