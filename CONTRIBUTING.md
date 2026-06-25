# Contributing to Hand Gesture Puzzle Game

First off, thank you for taking the time to contribute! Contributions are what make the open-source community such an amazing place to learn, inspire, and create.

All types of contributions are welcome, from reporting bugs, suggesting new features, improving documentation, to writing code.

---

## Code of Conduct

This project and everyone participating in it is governed by the [Code of Conduct](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

---

## How Can I Contribute?

### Reporting Bugs

If you find a bug (such as unstable hand tracking on certain platforms, incorrect shape snapping, or rendering issues), please create a new issue and include:
* Your Operating System (Windows, macOS, Linux).
* Your Python and OpenCV/MediaPipe versions.
* Clear steps to reproduce the issue.
* Any error logs or warning messages from the console.

### Suggesting Features

If you have ideas to make the gameplay more fun or interactive:
1. Check the existing feature requests and planned features listed in the `README.md` (e.g. sound effects, score system, timer mode, obstacles).
2. Open a new issue describing your proposed feature, why it would be valuable, and how it could be designed/implemented.

### Code Contributions

If you'd like to fix a bug or implement a feature:

1. **Fork and Clone**: Fork the repository and clone it to your local machine.
2. **Setup Dev Environment**:
   * Use Python 3.11 (recommended).
   * Set up a virtual environment and install the dependencies:
     ```powershell
     python -m venv .venv
     # On Windows (PowerShell):
     .\.venv\Scripts\Activate.ps1
     # On macOS/Linux:
     source .venv/bin/activate
     
     pip install -r requirements.txt
     ```
3. **Keep Code Modular**:
   * Do not put everything in one file. Follow the established modular structure:
     * [config.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/config.py): Configuration, levels, speeds, and gesture thresholds.
     * [vision.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/vision.py): Hand tracking and pinch detection logic.
     * [game.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/game.py): Game loop states, level progression, shape movement, and targets.
     * [renderer.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/renderer.py): Screen rendering, UI design, color palettes, and overlay drawing.
     * [main.py](file:///d:/Users/ROG/Documents/School_Projects/Clones/hand-gesture-puzzle-game/main.py): Entry point, webcam capturing, and frame processing.
4. **Test Your Changes**: Run `python main.py` and ensure the game runs smoothly, tracking is stable, and no new warnings are generated.
5. **Code Style**: Keep code readable and follow standard Python guidelines (PEP 8).
6. **Submit a Pull Request (PR)**:
   * Describe your changes in detail.
   * Explain what problem it solves and refer to any open issues.

---

## Coding Guidelines

* **Webcam compatibility**: Make sure your modifications do not break basic webcam fallback setups.
* **Tuning values**: If a feature requires constants (like speed, color, window dimensions), add them to `config.py` rather than hardcoding them elsewhere.
* **Performance**: Since the game runs in real-time, avoid adding expensive operations inside the main loops or rendering loops that could lower the game's FPS. Keep track of the FPS indicator on screen to verify performance.
