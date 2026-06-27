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
MP_MAX_HANDS = 1                        # initial; runtime can override
MP_MIN_DETECTION_CONFIDENCE = 0.6
MP_MIN_TRACKING_CONFIDENCE = 0.5
INFERENCE_WIDTH = 520

# ---------- Cursor filter (One Euro) ----------
CURSOR_MIN_CUTOFF = 1.3
CURSOR_BETA = 0.05
CURSOR_D_CUTOFF = 1.0

# ---------- Pinch ----------
PINCH_GRAB_THRESHOLD = 0.30
PINCH_RELEASE_THRESHOLD = 0.42
PINCH_RATIO_SMOOTHING = 0.65
HAND_LOST_GRACE_SECONDS = 0.32

# ---------- Playfield ----------
PLAYFIELD_MARGIN_X = 0.10
PLAYFIELD_MARGIN_TOP = 0.16
PLAYFIELD_MARGIN_BOTTOM = 0.12

# ---------- Gameplay ----------
SNAP_LENIENCE_PER_100_PXS = 10.0
INTRO_HINT_SECONDS = 4.0
LEVEL_TRANSITION_SECONDS = 0.45

# ---------- Animation ----------
SHAPE_GRAB_SCALE = 1.18
SHAPE_HOVER_SCALE = 1.07
SHAPE_SCALE_SPEED = 18.0
TARGET_RING_PULSE_HZ = 2.5
CURSOR_SCALE_SPEED = 22.0

# ---------- Effects ----------
SNAP_PARTICLE_COUNT = 14
SNAP_PARTICLE_SPEED = 320.0
SNAP_PARTICLE_LIFETIME = 0.55
SNAP_RING_LIFETIME = 0.45
SNAP_RING_MAX_RADIUS = 90

# ---------- HUD ----------
HAND_SPEED_METER_MAX = 1400

# ---------- Stability / pacing ----------
READY_STABLE_SECONDS = 0.35
PINCH_GRACE_SECONDS = 0.18
CURSOR_FADE_SECONDS = 0.35
TARGET_FPS = 60
CAMERA_FAIL_LIMIT = 10

# ---------- Background treatment ----------
BG_DESATURATION = 0.45
BG_DARKEN = 0.72
VIGNETTE_STRENGTH = 0.55
VIGNETTE_FALLOFF = 1.8

# ---------- Motion ----------
SHAKE_SNAP = 5.0
SHAKE_LEVEL_COMPLETE = 11.0
SHAKE_GAME_COMPLETE = 16.0

# ---------- Confetti ----------
CONFETTI_BURST_COUNT = 80
CONFETTI_LIFETIME = 2.8
CONFETTI_GRAVITY = 520.0

# ---------- Cursor trail ----------
TRAIL_MAX_POINTS = 22
TRAIL_LIFETIME = 0.32

# ---------- Spawn animation ----------
SHAPE_SPAWN_STAGGER = 0.08
SHAPE_SPAWN_BASE_DELAY = 0.15
TARGET_SPAWN_BASE_DELAY = 0.05
TARGET_SPAWN_STAGGER = 0.06
SHAPE_SPAWN_DURATION = 0.55
TARGET_SPAWN_DURATION = 0.55
SHAPE_SPAWN_OFFSCREEN = 380
TARGET_SPAWN_OFFSCREEN = 380

# ---------- Level intro card ----------
INTRO_CARD_SLIDE_IN = 0.35
INTRO_CARD_HOLD = 1.45
INTRO_CARD_SLIDE_OUT = 0.40

# ---------- Ghost replay ----------
GHOST_SAMPLE_HZ = 30
GHOST_TRAIL_LIFETIME = 0.18
GHOST_COLOR = (180, 220, 230)

# ---------- Silhouette ----------
SILHOUETTE_INFERENCE_WIDTH = 320
SILHOUETTE_EVERY_N_FRAMES = 2
SILHOUETTE_RIM_COLOR = (220, 200, 90)
SILHOUETTE_RIM_THICKNESS = 3
SILHOUETTE_PULSE_HZ = 0.6

# ---------- Settings panel ----------
SETTINGS_PANEL_LIFETIME = 2.5
PINCH_THRESHOLD_MIN = 0.22
PINCH_THRESHOLD_MAX = 0.42
PINCH_THRESHOLD_STEP = 0.02

# ---------- Calibration ----------
CALIBRATION_PHASE_SECONDS = 2.2
CALIBRATION_WARMUP = 0.5
CALIBRATION_HYSTERESIS_GAP = 0.12
CALIBRATION_FILE_KEY = "_calibration"

# ---------- Adaptive difficulty ----------
ADAPTIVE_ENABLED = True
ADAPTIVE_SPEED_SOFTEN = 0.75
ADAPTIVE_FAIL_THRESHOLD = 2
ADAPTIVE_GRAB_BUMP = 4

# ---------- Gestures ----------
GESTURE_HOLD_SECONDS = 0.55
GESTURE_COOLDOWN = 1.0
GESTURE_EXTENSION_RATIO = 1.15

# ---------- Two-hand co-op ----------
COOP_DEFAULT = False
COOP_CURSOR_COLOR_RIGHT = (110, 240, 150)
COOP_CURSOR_COLOR_LEFT = (110, 180, 245)

# ---------- Recording ----------
RECORDING_DIR = "recordings"
RECORDING_FPS = 60

# ---------- Audio ----------
SHAPE_PITCHES = {
    "shape_red":    523,
    "shape_blue":   659,
    "shape_green":  784,
    "shape_purple": 988,
    "shape_orange": 1175,
}

# ---------- Colors (BGR) ----------
COLORS = {
    "bg_dim":       (12, 10, 14),
    "surface":      (28, 24, 32),
    "surface_alt":  (44, 38, 52),
    "surface_hi":   (62, 54, 74),
    "outline":      (90, 82, 108),
    "outline_hi":   (140, 130, 162),

    "text_primary":   (240, 238, 245),
    "text_secondary": (190, 185, 200),
    "text_muted":     (135, 130, 152),

    "success":  (130, 220, 140),
    "warning":  (90, 200, 245),
    "danger":   (90, 90, 240),
    "accent":   (80, 180, 220),
    "primary":  (180, 200, 90),

    "cursor_idle":  (180, 220, 90),
    "cursor_grab":  (110, 240, 150),

    "shape_red":    (88, 80, 230),
    "shape_blue":   (220, 160, 80),
    "shape_green":  (130, 200, 110),
    "shape_purple": (210, 110, 195),
    "shape_orange": (60, 165, 245),

    "shadow": (8, 6, 12),
}

# ---------- Typography ----------
# (font_code, scale, thickness). Codes: 1=PLAIN, 2=DUPLEX, 4=TRIPLEX
TYPE = {
    "caption": (2, 0.45, 1),
    "body":    (2, 0.55, 1),
    "lead":    (2, 0.70, 2),
    "h3":      (2, 0.90, 2),
    "h2":      (4, 1.25, 2),
    "h1":      (4, 1.75, 3),
    "mono":    (1, 1.10, 1),
}

# ---------- Layout ----------
RADIUS_CARD = 18
RADIUS_CHIP = 10

# ---------- Shapes ----------
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
     "grab_radius": 62, "snap_radius": 72, "targets_move": False,
     "speed_range": (0, 0),    "move_axis": "none"},
    {"name": "Moving Targets",  "shape_count": 3, "shape_size": 66,
     "grab_radius": 60, "snap_radius": 68, "targets_move": True,
     "speed_range": (30, 60),  "move_axis": "y"},
    {"name": "Four Shapes",     "shape_count": 4, "shape_size": 62,
     "grab_radius": 56, "snap_radius": 62, "targets_move": True,
     "speed_range": (50, 85),  "move_axis": "y"},
    {"name": "Crosswind",       "shape_count": 4, "shape_size": 60,
     "grab_radius": 54, "snap_radius": 60, "targets_move": True,
     "speed_range": (60, 100), "move_axis": "xy"},
    {"name": "Final Challenge", "shape_count": 5, "shape_size": 56,
     "grab_radius": 50, "snap_radius": 56, "targets_move": True,
     "speed_range": (75, 125), "move_axis": "xy"},
]