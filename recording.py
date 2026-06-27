"""MP4 gameplay capture via cv2.VideoWriter."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import cv2

from config import RECORDING_DIR, RECORDING_FPS

log = logging.getLogger(__name__)


class VideoRecorder:
    def __init__(self) -> None:
        self.dir = Path(RECORDING_DIR)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._writer: cv2.VideoWriter | None = None
        self._path: Path | None = None
        self._frame_count = 0

    @property
    def is_recording(self) -> bool:
        return self._writer is not None

    @property
    def path(self) -> Path | None:
        return self._path

    def start(self, frame) -> Path | None:
        if self.is_recording:
            return self._path
        h, w = frame.shape[:2]
        ts = time.strftime("%Y%m%d-%H%M%S")
        self._path = self.dir / f"gpgame-{ts}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._writer = cv2.VideoWriter(str(self._path), fourcc,
                                       RECORDING_FPS, (w, h))
        if not self._writer.isOpened():
            log.error("Failed to open VideoWriter at %s", self._path)
            self._writer = None
            self._path = None
            return None
        self._frame_count = 0
        log.info("Recording to %s", self._path)
        return self._path

    def write(self, frame) -> None:
        if self._writer is not None:
            self._writer.write(frame)
            self._frame_count += 1

    def stop(self) -> Path | None:
        if self._writer is None:
            return None
        self._writer.release()
        path = self._path
        log.info("Saved %s (%d frames)", path, self._frame_count)
        self._writer = None
        self._path = None
        return path