# Hand Gesture Puzzle Game

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.11-green.svg)](https://www.python.org/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.21-purple.svg)](https://google.github.io/mediapipe/)

A webcam-based puzzle game controlled with real-time hand gestures. Grab shapes, drag them across the screen, and drop them into matching moving targets.

Built with **Python**, **OpenCV**, and **MediaPipe Hands**.

---

## 🎮 Gameplay

1. **Show your hand** to the webcam.
2. **Pinch** your thumb and index finger together to grab a shape.
3. **Drag** the shape to the matching outline target.
4. **Release** the pinch to drop it.
5. **Hold Open Palm** for 1.2 seconds to pause or unpause the game.
6. **Hold Pointing Finger** for 1.2 seconds to go to the next level when the level is completed.

---

## ✨ Features

- **Real-Time Hand Tracking & Smoothing**: Uses MediaPipe Hands combined with a [OneEuroFilter](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/vision.py#L36) to ensure low-latency, jitter-free cursor movements.
- **Intelligent Gesture Control**: In-game gestures (Pinch, Open Palm, Point, Fist) mapped to gameplay commands using [HoldFireDetector](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/gestures.py#L47).
- **Interactive Pre-Game Calibration**: A two-phase calibration sequence (Relaxed vs. Pinched hand) to measure and configure custom pinch thresholds, which are saved across sessions.
- **Ghost Replay**: Automatically records your best run's cursor path and pinch state, playing it back as a ghost cursor on retries so you can compete against your best time.
- **Two-Player/Hand Co-op Mode**: Play with two hands (or two players) simultaneously, utilizing distinct cursor colors (Green for right hand, Blue for left hand).
- **Selfie Segmentation Silhouette**: Uses MediaPipe Selfie Segmentation to render a glowing contour outline around the player's body and hand on the background.
- **Pentatonic Audio Cues**: Tiny, non-blocking audio feedback (pitch-mapped shape snaps using pentatonic scales, grab/release ticks, and win fanfare). Windows-only (silent fallback elsewhere).
- **Dynamic Visual Effects**: Screen shakes, custom particle bursts on snapping, confetti showers, and smooth cursor trails.
- **Adaptive Difficulty**: Automatically slows down targets and increases grabbing/snapping tolerances if you restart or fail a level too many times.
- **Gameplay Recording**: Real-time recording of the game window to an MP4 video file stored in the `recordings/` folder.
- **Local Progress Persistence**: Auto-saves your level completion times and move counts locally to display high scores and best records.

---

## ⌨️ Controls

### Gestures (Hand Controls)
| Gesture | Action | Description |
|---|---|---|
| **Pinch (Thumb + Index)** | Grab / Drag shape | Hold the pinch to drag a shape; release to drop it. |
| **Open Palm** | Toggle Pause | Hold for 1.2 seconds during gameplay. |
| **Point (Index Finger)** | Next Level | Hold for 1.2 seconds on the victory screen. |

### Keyboard Hotkeys
| Key | Action |
|---|---|
| **`Q`** or **`Esc`** | **Quit Game** |
| **`R`** | **Restart Level** |
| **`N`** | **Next Level** (on victory screen) |
| **`P`** | **Toggle Pause** |
| **`H`** | **Toggle Debug HUD** (displays FPS, One Euro values, speeds) |
| **`D`** | **Toggle Hand Landmarks Drawing** |
| **`S`** | **Toggle Silhouette Outline** (Selfie Segmentation) |
| **`T`** | **Toggle Cursor Trail** |
| **`G`** | **Toggle Ghost Best-Time Replay** |
| **`2`** | **Toggle Two-Hand Co-op Mode** (restarts level with 2-hand tracking) |
| **`V`** | **Toggle Gameplay Video Recording** (saves to `recordings/`) |
| **`C`** | **Recalibrate Pinch Gesture** (Relaxed hand phase, then Pinched phase) |
| **`Spacebar`** | **Skip active Pinch Calibration** |
| **`,`** (comma) | **Lower Pinch Threshold** (makes grabbing tighter / stricter) |
| **`.`** (period) | **Raise Pinch Threshold** (makes grabbing easier) |
| **`?`** or **`/`** | **Show Settings Panel** |

---

## 🏆 Levels

| Level | Name | Description |
|---|---|---|
| 1 | Warm-up | 3 static shape targets to match. |
| 2 | Moving Targets | 3 targets moving vertically (`Y`-axis). |
| 3 | Four Shapes | 4 targets moving vertically at higher speeds. |
| 4 | Crosswind | 4 targets moving diagonally (`X` and `Y` axes). |
| 5 | Final Challenge | 5 smaller targets with fast, chaotic diagonal movement. |

---

## 📁 Project Structure

This project is modularly structured, dividing responsibilities across specialized scripts:

- **[main.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/main.py)**: Orchestrates the main loop, processes camera feeds, handles key presses, and routes events.
- **[config.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/config.py)**: Central configuration for colors, sizes, speeds, levels, keybindings, and physical tracking parameters.
- **[game.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/game.py)**: Defines the core [GameState](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/game.py#L103) state machine, shape snapping, slot-based co-op, and target movement.
- **[vision.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/vision.py)**: Wraps MediaPipe Hands, tracks coordinate cursors, and implements the noise-reducing [OneEuroFilter](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/vision.py#L36).
- **[renderer.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/renderer.py)**: Pure rendering module containing functions like [draw](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/renderer.py#L28) to draw shapes, overlays, HUD, cards, and debug menus.
- **[gestures.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/gestures.py)**: Classifies fingers and thumb to recognize Open Palm, Point, Fist, or Pinch gestures.
- **[calibration.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/calibration.py)**: Manages the states and mathematics of the pre-game pinch/release threshold calibration.
- **[effects.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/effects.py)**: Coordinates visual animations (tweens, particles, ripple rings, trails, and confetti bursts).
- **[audio.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/audio.py)**: Handles non-blocking, multi-threaded audio cues on Windows using `winsound`.
- **[motion.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/motion.py)**: Implements screen-shake tracking and decay.
- **[persistence.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/persistence.py)**: Reads and writes best records and custom calibrations to `~/.gesture_puzzle_records.json`.
- **[recording.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/recording.py)**: Captures game frames and writes them out to MP4 gameplay videos.
- **[replay.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/replay.py)**: Manages recording and reading ghost paths stored in `~/.gesture_puzzle_ghosts.json`.
- **[segmentation.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/segmentation.py)**: Processes and resizes selfies to create body silhouette masks.
- **[requirements.txt](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/requirements.txt)**: Direct library dependencies.

---

## ⚙️ Requirements

* **Python 3.11** (recommended)
* **Webcam** (internal or external USB)
* **Windows / macOS / Linux** (Audio feedback is currently supported on Windows only)
* Good lighting for reliable hand landmark tracking

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
> MediaPipe is pinned to `0.10.21` because this project utilizes the legacy `mp.solutions.hands` API.

---

## 🏃 Running the Game

With your virtual environment active, run:
```bash
python main.py
```

If your webcam does not open, check [config.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/config.py):
```python
CAMERA_INDEX = 1
```
Try changing it to `0`, `2`, etc., if you have multiple cameras connected or if the default index is incorrect.

---

## 🔧 Tuning Gameplay

Most gameplay settings are located inside [config.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/config.py).

### Adjust Pinch Sensitivity manually
```python
PINCH_GRAB_THRESHOLD = 0.30     # Lower means you must pinch tighter to grab
PINCH_RELEASE_THRESHOLD = 0.42  # Higher means you must open your hand wider to release
```

### Cursor Responsiveness & Smoothing
Adjust the parameters for the One Euro Filter:
```python
CURSOR_MIN_CUTOFF = 1.3  # Lower values decrease jitter but increase lag at low speeds
CURSOR_BETA = 0.05       # Higher values reduce lag at high speeds
```

### Modify Target Speeds
Change speeds inside the `LEVELS` list to adjust target velocity:
```python
"speed_range": (50, 85)
```

---

## 🤝 Community & Contributing

Contributions are welcome! Please review our guidelines:
* **Guidelines**: See [CONTRIBUTING.md](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/CONTRIBUTING.md) for how to set up development and submit PRs.
- **Code of Conduct**: Read [CODE_OF_CONDUCT.md](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/CODE_OF_CONDUCT.md) to learn about our community pledges and standards.
- **Security Policy**: See [SECURITY.md](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/SECURITY.md) to report vulnerabilities.

---

## ✍️ Authors

Created by **Srun Sochettra** for final project of a subject in the course.

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/LICENSE) file for details.
