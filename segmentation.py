"""Silhouette rim via MediaPipe Selfie Segmentation."""

from __future__ import annotations

import logging

import cv2
import numpy as np

try:
    import mediapipe as mp
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

from config import (
    SILHOUETTE_EVERY_N_FRAMES, SILHOUETTE_INFERENCE_WIDTH,
)

log = logging.getLogger(__name__)


class Silhouette:
    def __init__(self) -> None:
        self._seg = None
        self._frame_count = 0
        self._cached_mask: np.ndarray | None = None
        if not _AVAILABLE:
            log.warning("MediaPipe not available; silhouette disabled.")
            return
        try:
            self._seg = mp.solutions.selfie_segmentation.SelfieSegmentation(
                model_selection=0
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Selfie Segmentation init failed: %s", exc)
            self._seg = None

    @property
    def available(self) -> bool:
        return self._seg is not None

    def mask_for(self, frame: np.ndarray) -> np.ndarray | None:
        if self._seg is None:
            return None
        h, w = frame.shape[:2]
        self._frame_count += 1
        if (self._frame_count % SILHOUETTE_EVERY_N_FRAMES == 0
                and self._cached_mask is not None
                and self._cached_mask.shape == (h, w)):
            return self._cached_mask

        scale = SILHOUETTE_INFERENCE_WIDTH / w
        if scale < 1.0:
            small = cv2.resize(frame, (SILHOUETTE_INFERENCE_WIDTH,
                                       int(h * scale)),
                               interpolation=cv2.INTER_AREA)
        else:
            small = frame

        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        try:
            result = self._seg.process(rgb)
        except Exception:  # noqa: BLE001
            return self._cached_mask

        small_mask = result.segmentation_mask
        if small_mask is None:
            return self._cached_mask

        binary = (small_mask > 0.55).astype(np.uint8) * 255
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN,
                                  np.ones((3, 3), np.uint8))
        full = cv2.resize(binary, (w, h), interpolation=cv2.INTER_LINEAR)
        full = (full > 127).astype(np.uint8) * 255
        self._cached_mask = full
        return full

    def close(self) -> None:
        if self._seg is not None:
            self._seg.close()
            self._seg = None