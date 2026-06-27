"""All tunable constants. BGR color tuples (OpenCV)."""

from __future__ import annotations

# ---------- Window & camera ----------
WINDOW_NAME = "Gesture Puzzle Game"
CAMERA_INDEX = 1
CAMERA_FALLBACK_INDICES = (0, 1, 2)
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720

# ---------- MediaPipe ----------
MP_MODEL_COMPLEXITY = 0
MP_MAX_HANDS = 1
MP_MIN_DETECTION_CONFIDENCE = 0.6
MP_MIN_TRACKING_CONFIDENCE = 0.5
INFERENCE_WIDTH = 480

# ---------- Cursor filter (One Euro) ----------
CURSOR_MIN_CUTOFF = 1.0
CURSOR_BETA = 0.015
CURSOR_D_CUTOFF = 1.0

# ---------- Pinch detection ----------
PINCH_GRAB_THRESHOLD = 0.32
PINCH_RELEASE_THRESHOLD = 0.46
PINCH_RATIO_SMOOTHING = 0.5  # EMA factor on pinch ratio for stability
HAND_LOST_GRACE_SECONDS = 0.25

# ---------- Playfield ----------
PLAYFIELD_MARGIN_X = 0.10
PLAYFIELD_MARGIN_TOP = 0.16
PLAYFIELD_MARGIN_BOTTOM = 0.12

# ---------- Gameplay ----------
SNAP_LENIENCE_PER_100_PXS = 6.0
INTRO_HINT_SECONDS = 4.0
LEVEL_TRANSITION_SECONDS = 0.45

# ---------- Animation ----------
SHAPE_GRAB_SCALE = 1.18
SHAPE_HOVER_SCALE = 1.07
SHAPE_SCALE_SPEED = 14.0           # higher = snappier tween
TARGET_RING_PULSE_HZ = 2.5
CURSOR_SCALE_SPEED = 18.0

# ---------- Effects ----------
SNAP_PARTICLE_COUNT = 14
SNAP_PARTICLE_SPEED = 320.0
SNAP_PARTICLE_LIFETIME = 0.55
SNAP_RING_LIFETIME = 0.45
SNAP_RING_MAX_RADIUS = 90

# ---------- HUD ----------
HAND_SPEED_METER_MAX = 1400

# ---------- Colors (BGR) ----------
COLORS = {
    "bg_dim": (0, 0, 0),
    "surface": (28, 28, 34),
    "surface_alt": (44, 44, 52),
    "outline": (90, 90, 110),

    "text_primary": (245, 245, 245),
    "text_muted": (170, 170, 180),

    "success": (90, 220, 110),
    "warning": (0, 215, 245),
    "danger": (80, 80, 255),
    "accent": (235, 200, 80),

    "cursor_idle": (235, 200, 80),
    "cursor_grab": (90, 230, 110),

    "shape_red":    (60, 60, 235),
    "shape_blue":   (235, 150, 70),
    "shape_green":  (90, 200, 80),
    "shape_purple": (210, 90, 190),
    "shape_orange": (40, 145, 240),

    "shadow": (15, 15, 18),
}

# ---------- Shape catalogue ----------
ALL_SHAPES = [
    {"kind": "square",   "color": "shape_red"},
    {"kind": "circle",   "color": "shape_blue"},
    {"kind": "triangle", "color": "shape_green"},
    {"kind": "diamond",  "color": "shape_purple"},
    {"kind": "pentagon", "color": "shape_orange"},
]

# ---------- Levels ----------
LEVELS = [
    {"name": "Warm-up",         "shape_count": 3, "shape_size": 70,
     "grab_radius": 60, "snap_radius": 72, "targets_move": False,
     "speed_range": (0, 0), "move_axis": "none"},
    {"name": "Moving Targets",  "shape_count": 3, "shape_size": 66,
     "grab_radius": 58, "snap_radius": 66, "targets_move": True,
     "speed_range": (35, 70), "move_axis": "y"},
    {"name": "Four Shapes",     "shape_count": 4, "shape_size": 62,
     "grab_radius": 54, "snap_radius": 60, "targets_move": True,
     "speed_range": (55, 95), "move_axis": "y"},
    {"name": "Crosswind",       "shape_count": 4, "shape_size": 60,
     "grab_radius": 52, "snap_radius": 58, "targets_move": True,
     "speed_range": (65, 115), "move_axis": "xy"},
    {"name": "Final Challenge", "shape_count": 5, "shape_size": 56,
     "grab_radius": 48, "snap_radius": 54, "targets_move": True,
     "speed_range": (85, 145), "move_axis": "xy"},
]