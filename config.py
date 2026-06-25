CAMERA_INDEX = 1
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
WINDOW_NAME = "Gesture Puzzle Game"

# Lower = faster cursor, higher = smoother cursor.
SMOOTHING = 0.78

# Pinch sensitivity. Higher = easier grab, lower = stricter.
PINCH_THRESHOLD = 0.34

# Hand speed meter.
# Speed is measured from smoothed cursor movement in pixels per second.
HAND_SPEED_METER_MAX = 1400

MAX_HANDS = 1
MIN_DETECTION_CONFIDENCE = 0.75
MIN_TRACKING_CONFIDENCE = 0.75

TARGET_TOP_MARGIN = 130
TARGET_BOTTOM_MARGIN = 95

COLORS = {
    "red": (44, 44, 239),
    "blue": (246, 130, 59),
    "green": (94, 197, 34),
    "purple": (210, 80, 180),
    "orange": (35, 140, 245),

    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "dark": (28, 28, 34),
    "panel": (35, 35, 42),
    "gray": (130, 130, 130),

    "yellow": (0, 240, 255),
    "cursor_idle": (0, 230, 255),
    "cursor_grab": (0, 255, 90),
    "success": (80, 230, 90),
    "danger": (80, 80, 255),
}

ALL_SHAPES = [
    {"kind": "square", "color": "red"},
    {"kind": "circle", "color": "blue"},
    {"kind": "triangle", "color": "green"},
    {"kind": "diamond", "color": "purple"},
    {"kind": "pentagon", "color": "orange"},
]

LEVELS = [
    {
        "name": "Warm-up",
        "shape_count": 3,
        "shape_size": 68,
        "grab_distance": 82,
        "snap_distance": 72,
        "targets_move": False,
        "target_speed_min": 0,
        "target_speed_max": 0,
        "move_axis": "none",
    },
    {
        "name": "Moving Targets",
        "shape_count": 3,
        "shape_size": 66,
        "grab_distance": 80,
        "snap_distance": 68,
        "targets_move": True,
        "target_speed_min": 35,
        "target_speed_max": 70,
        "move_axis": "y",
    },
    {
        "name": "Four Shapes",
        "shape_count": 4,
        "shape_size": 64,
        "grab_distance": 78,
        "snap_distance": 62,
        "targets_move": True,
        "target_speed_min": 55,
        "target_speed_max": 95,
        "move_axis": "y",
    },
    {
        "name": "Crosswind",
        "shape_count": 4,
        "shape_size": 62,
        "grab_distance": 76,
        "snap_distance": 58,
        "targets_move": True,
        "target_speed_min": 65,
        "target_speed_max": 115,
        "move_axis": "xy",
    },
    {
        "name": "Final Challenge",
        "shape_count": 5,
        "shape_size": 58,
        "grab_distance": 74,
        "snap_distance": 54,
        "targets_move": True,
        "target_speed_min": 85,
        "target_speed_max": 145,
        "move_axis": "xy",
    },
]