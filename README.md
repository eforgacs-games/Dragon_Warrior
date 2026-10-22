![Dragon Warrior](https://i.imgur.com/noZfPNO.gif)

![Python application](https://github.com/eforgacs-games/Dragon_Warrior/actions/workflows/python-app.yml/badge.svg)

# ABOUT


This is a clone of Dragon Warrior for the Nintendo Entertainment System, done in Python.


# REQUIREMENTS

[Python 3.10 to 3.13](https://www.python.org/) (pygame doesn't support 3.14 yet), [PyGame](https://www.pygame.org/news)

Dependency versions are pinned in `uv.lock`. With [uv](https://docs.astral.sh/uv/), `uv sync` installs them, plus the dev tools
(pytest, mypy, ruff), into `.venv`. Without uv, `pip install -r requirements.txt` installs the same game dependencies.

# INSTRUCTIONS


Run it from the command line using the interpreter. If you are in the
DragonWarrior directory, type:
python src/game.py

To run with the development config (god mode, no battles, coordinates visible), add `--dev`:
python src/game.py --dev

## Playtesting

To start from a point in the story, add `--checkpoint <name>`. A checkpoint is a save file in
`data/checkpoints/`: `throne_room`, `garins_grave`, `swamp_cave`, `rainbow_drop_shrine`, `rainbow_bridge`,
`charlock_throne`, `dragonlord`, `ending_gwaelin_returned` or `ending_carrying_gwaelin`. For example:
python src/game.py --dev --checkpoint rainbow_bridge

Saves made in a game started this way go to a temp folder, not to `src/saves/`.

With `--dev`, these debug keys are also on:
- F5 warps to any map.
- F6 gives an item or gold, sets your level, equips Erdrick's gear, or refills HP and MP.
- F7 loads another checkpoint.

Each one opens a list: type to filter, press Enter to pick, Esc to close.

[PLAYTEST.md](PLAYTEST.md) is a checklist for a pass through the whole game in about 40 minutes.

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
     pip install -r requirements.txt
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

1 / 2 / 3 / 4: Game speed (normal, 2x, 4x, 8x). This works anywhere, including battles, dialogs and
menus, and speeds up everything: walking, text, battle effects and pauses. Only timing changes, not what happens in
the game. Music and sound effects play at normal speed. The speed lasts until you close the game and isn't saved.

## Demo video



https://user-images.githubusercontent.com/23140027/165859033-1abe8a84-af2e-48c1-9d74-38cd700d98b5.mp4



## Run on Repl.it


For quick demonstration purposes, you can run this in the browser on repl.it, but ideally this should be run normally through the command line as delineated above, since performance suffers greatly in the browser. Additionally, the version of the code currently on repl.it does not have the latest code improvements that this repository does.

[![Run on Repl.it](https://repl.it/badge/github/eforgacs-games/DragonWarrior)]([https://repl.it/@eforgacs/DW](https://replit.com/@eforgacs/DragonWarrior))
