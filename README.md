# Hand Gesture Puzzle Game

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.11-green.svg)](https://www.python.org/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.21-purple.svg)](https://google.github.io/mediapipe/)

A webcam-based puzzle game controlled with real-time hand gestures. Use your hand to grab shapes, drag them across the screen, and drop them into matching moving targets.

Built with **Python**, **OpenCV**, and **MediaPipe Hands**.

---

## 🎮 Gameplay

The goal is simple:

1. **Show your hand** to the webcam.
2. **Pinch** your thumb and index finger together to grab a shape.
3. **Drag** the shape to the matching outline target.
4. **Release** the pinch to drop it.
5. Match all shapes to clear the level.

Later levels become harder with faster and moving targets.

---

## ✨ Features

- **Real-time hand tracking** using webcam
- **Pinch gesture detection** for intuitive grab/drop controls
- **Smooth cursor movement** with customizable smoothing
- **Shape matching puzzle** gameplay logic
- **5 progressive levels** with increasing difficulty
- **Moving targets** in advanced levels (vertical, horizontal, and diagonal motion)
- **Hand speed meter** and live **FPS display**
- **In-game controls** (Restart and Next-Level)
- **Modular and clean** project file structure

---

## ⌨️ Controls

| Action | Control |
|---|---|
| **Grab shape** | Pinch thumb + index finger |
| **Drop shape** | Release pinch |
| **Restart current level** | Press `R` |
| **Next level (after winning)** | Press `N` |
| **Quit game** | Press `Q` |

---

## 🏆 Levels

| Level | Name | Description |
|---|---|---|
| 1 | Warm-up | 3 static targets |
| 2 | Moving Targets | 3 vertically moving targets |
| 3 | Four Shapes | 4 faster moving targets |
| 4 | Crosswind | 4 targets moving vertically and horizontally |
| 5 | Final Challenge | 5 smaller shapes with faster XY movement |

---

## 📁 Project Structure

* [main.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/main.py) - Main game loop, webcam handling, and orchestration.
* [config.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/config.py) - Game settings, colors, levels, and tuning values.
* [game.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/game.py) - Game state, levels, snapping, and movement logic.
* [vision.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/vision.py) - MediaPipe hand tracking and pinch detection.
* [renderer.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/renderer.py) - Drawing UI, shapes, cursor, HUD, and text overlays.
* [requirements.txt](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/requirements.txt) - Python dependencies.

---

## ⚙️ Requirements

* **Python 3.11** (recommended)
* **Webcam** (internal or external)
* **Windows / macOS / Linux**
* Good lighting for reliable hand tracking

---

## 🚀 Installation & Setup

1. Clone or download the project, then open the folder in your terminal.
2. Create a virtual environment:
   ```powershell
   python -m venv .venv
   ```
3. Activate the virtual environment:
   * **Windows (PowerShell)**:
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   * **macOS/Linux**:
     ```bash
     source .venv/bin/activate
     ```
4. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

> [!NOTE]
> `requirements.txt` contains:
> ```txt
> mediapipe==0.10.21
> opencv-python
> numpy
> ```
> MediaPipe is pinned to `0.10.21` because this project uses the legacy `mp.solutions.hands` API.

---

## 🏃 Running the Game

With your virtual environment active, run:
```bash
python main.py
```

If your webcam does not open, check [config.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/config.py):
```python
CAMERA_INDEX = 0
```
Try changing it to `1` or `2` if you have multiple cameras connected.

---

## 🔧 Tuning Gameplay

Most gameplay settings are inside [config.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/config.py).

### Adjust Pinch Sensitivity
```python
PINCH_THRESHOLD = 0.38  # Make pinch easier
PINCH_THRESHOLD = 0.28  # Make pinch stricter
```

### Cursor Responsiveness & Smoothing
```python
SMOOTHING = 0.70  # Make cursor faster/more responsive
SMOOTHING = 0.85  # Make cursor smoother/less jittery
```

### Adjust Snapping Distance
Increase `snap_distance` inside any level in `config.py` to make matching easier:
```python
"snap_distance": 75
```

### Modify Target Speeds
Change speeds inside the levels dictionary to adjust target velocity:
```python
"target_speed_min": 35,
"target_speed_max": 75,
```

---

## 🧠 How It Works

1. **Landmark Extraction**: The game uses MediaPipe Hands to detect hand landmarks from the webcam input frame.
2. **Cursor Calculation**: The cursor coordinate is mapped using the midpoint between the thumb tip and the index finger tip.
3. **Pinch Detection**: A pinch is detected by measuring the Euclidean distance between the thumb and index finger tip, normalized by the overall hand size to ensure consistency regardless of distance from the camera.
4. **Collision and Snapping**:
   * Grabs a shape when the cursor collides with it while a pinch is active.
   * Moves the held shape along with the cursor coordinates.
   * Snaps the shape to a target outline if it matches and is within `snap_distance` when dropped.

---

## ⚠️ Known Issues & Troubleshooting

* **MediaPipe Warnings**: You may see TensorFlow Lite delegate logs or `absl::InitializeLog()` warnings in the terminal. These are normal and can be safely ignored.
* **Jittery Hand Tracking**:
  * Ensure your hand is well-lit and fully visible.
  * Avoid busy backgrounds or bright lights directly behind you.
  * Try tuning `MIN_DETECTION_CONFIDENCE` or `MIN_TRACKING_CONFIDENCE` in [config.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/config.py).
* **Pinch Calibration**: Adjust `PINCH_THRESHOLD` in [config.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/config.py) (higher values make grabbing easier; lower values make it tighter).

---

## 🔮 Future Improvements

Some ideas for features you could implement:
- [ ] Sound effects and background music
- [ ] Scoring system and level-wise scoreboard
- [ ] Countdown timer mode
- [ ] Obstacles or moving hazards that deflect shapes
- [ ] Level selection and pause menus
- [ ] Two-handed puzzle mode

---

## 🤝 Community & Contributing

Contributions are welcome! Please review our guidelines:
* **Guidelines**: See [CONTRIBUTING.md](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/CONTRIBUTING.md) for how to set up development and submit PRs.
* **Code of Conduct**: Read [CODE_OF_CONDUCT.md](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/CODE_OF_CONDUCT.md) to learn about our community pledges and standards.
* **Security Policy**: See [SECURITY.md](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/SECURITY.md) to report vulnerabilities.

---

## ✍️ Author

Created by **Srun Sochettra**.

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/LICENSE) file for details.