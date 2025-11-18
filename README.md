![Dragon Warrior](https://i.imgur.com/noZfPNO.gif)

![Python application](https://github.com/eforgacs-games/Dragon_Warrior/actions/workflows/python-app.yml/badge.svg)

# ABOUT


This is a clone of Dragon Warrior for the Nintendo Entertainment System, done in Python.


# REQUIREMENTS

[Python 3.10 (or higher)](https://www.python.org/), [PyGame](https://www.pygame.org/news), [PyGame Menu](https://github.com/ppizarror/pygame-menu)

# INSTRUCTIONS


Run it from the command line using the interpreter. If you are in the
DragonWarrior directory, type:
python src/game.py

## Running in VS Code

If you're using Visual Studio Code:

1. **Open the project folder** in VS Code (File > Open Folder > select the Dragon_Warrior directory)

2. **Install dependencies**:
   - Open the integrated terminal (View > Terminal or Ctrl+`)
   - Create a virtual environment (optional but recommended):
     ```bash
     python -m venv venv
     # On Windows:
     venv\Scripts\activate
     # On macOS/Linux:
     source venv/bin/activate
     ```
   - Install required packages:
     ```bash
     pip install pygame pygame-menu
     ```

3. **Run the game**:
   - **Option 1 - Using the terminal**: In the VS Code terminal, run:
     ```bash
     python src/game.py
     ```
   - **Option 2 - Using Run/Debug**:
     - Press F5 or click Run > Start Debugging
     - If prompted, select "Python File"
     - Navigate to src/game.py and run it

4. **Run tests** (optional):
   ```bash
   pytest
   ```

## Default Keys

WASD / ↑←↓→ : Move

K: Open Command Menu

J: Close Command Menu

Enter: Select menu option

I: Pause

## Demo video



https://user-images.githubusercontent.com/23140027/165859033-1abe8a84-af2e-48c1-9d74-38cd700d98b5.mp4



## Run on Repl.it


For quick demonstration purposes, you can run this in the browser on repl.it, but ideally this should be run normally through the command line as delineated above, since performance suffers greatly in the browser. Additionally, the version of the code currently on repl.it does not have the latest code improvements that this repository does.

[![Run on Repl.it](https://repl.it/badge/github/eforgacs-games/DragonWarrior)](https://repl.it/@eforgacs/DW)
