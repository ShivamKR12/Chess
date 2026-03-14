# Chess

![GitHub release (latest by date)](https://img.shields.io/github/v/release/ShivamKR12/Chess)
![Actions Status](https://github.com/ShivamKR12/Chess/actions/workflows/build.yml/badge.svg)

A 3D chess game built with Panda3D, featuring interactive gameplay with mouse controls, piece movement validation, and visual effects.

## Features

* 3D chessboard rendered using Panda3D
* Mouse-based piece selection and movement
* Turn-based gameplay
* Valid move highlighting
* Capture animations
* Castling
* En passant
* Pawn promotion
* Checkmate detection
* Camera rotation between turns

---

## Requirements

* Python 3.8 or newer
* Panda3D

Install Panda3D using pip:

```bash
pip install panda3d
```

## Downloading the Game

Pre-built executables are available for download from the [Releases](https://github.com/ShivamKR12/Chess/releases) page. Choose the appropriate version for your operating system:

- Windows: `win_amd64/Chess.exe`
- macOS: `macosx_10_13_x86_64/Chess.app`
- Linux: `manylinux2014_x86_64/Chess`

Download the executable and run it directly.

## Building from Source

To build the game from source:

1. Clone the repository:
   ```
   git clone https://github.com/ShivamKR12/Chess.git
   cd Chess
   ```

2. Install dependencies:
   ```
   pip install panda3d
   ```

3. Run the setup script to build:
   ```
   python setup.py build
   ```

4. The built executables will be in the `build/` directory.

## Running the Game

To run from source:
```
python main.py
```

## Project Structure

```
Chess/
├── .github/
│   └── workflows
│       └── build.yml
├── .gitignore
├── main.py
├── panda3d-logo.ico
├── panda3d-logo.png
├── setup.py
├── models/
│   ├── square
│   ├── pawn
│   ├── rook
│   ├── knight
│   ├── bishop
│   ├── queen
│   └── king
├── requirements.txt
└── README.md
```

---

## Credits

This project is based on the Panda3D chessboard sample.

Original code and models were created by:

* Shao Zhang
* Phil Saltzman
* Eddie Canaan

Source: [Chess](https://github.com/panda3d/panda3d/blob/master/samples/chessboard/)

The original Panda3D sample provided the initial foundation for the chessboard rendering and mouse picking system used in this project.

---
