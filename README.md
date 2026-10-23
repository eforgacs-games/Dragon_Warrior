![Dragon Warrior](https://i.imgur.com/noZfPNO.gif)

![Python application](https://github.com/eforgacs-games/Dragon_Warrior/actions/workflows/python-app.yml/badge.svg)

# ABOUT


This is a clone of Dragon Warrior for the Nintendo Entertainment System, done in Python.


# DOWNLOAD

Builds for Windows, macOS (Apple Silicon) and Linux, which don't need Python, are on the
[Releases page](https://github.com/eforgacs-games/Dragon_Warrior/releases). Download the archive for your system,
unpack it and run:
- Windows: `DragonWarrior\DragonWarrior.exe`. The build isn't signed, so Windows SmartScreen may warn about it
  ("More info", then "Run anyway").
- macOS: `Dragon Warrior.app`. The build isn't signed, so the first time, right-click it and choose Open (or allow it in
  System Settings > Privacy & Security).
- Linux: `DragonWarrior/DragonWarrior`.

A downloaded build keeps its adventure logs in `%APPDATA%\Dragon Warrior\saves` (Windows),
`~/Library/Application Support/Dragon Warrior/saves` (macOS) or `~/.local/share/dragon-warrior/saves` (Linux, or
`$XDG_DATA_HOME/dragon-warrior/saves`). Run from source, the game saves in `src/saves/`.

## Making a release

Push a tag named `vX.Y.Z` from `main`:
```bash
git tag v1.0.0
git push origin v1.0.0
```
The [Release builds](.github/workflows/release.yml) workflow builds the game with PyInstaller
([dragon_warrior.spec](dragon_warrior.spec)) on Windows, macOS and Linux, checks that each build starts and finds all
of its files (`--smoke-test`), and publishes them as a GitHub Release for the tag, with notes generated from the merged
PRs. To try the builds without a release, run the workflow from the Actions tab (Run workflow): the builds are then
uploaded as the run's artifacts. PRs that change the build do the same.

To build locally: `uv sync --group build`, then `uv run pyinstaller dragon_warrior.spec --noconfirm`. The game is in
`dist/DragonWarrior/` (and `dist/Dragon Warrior.app` on macOS).


# REQUIREMENTS

[Python 3.13](https://www.python.org/) (pygame doesn't support 3.14 yet), [PyGame](https://www.pygame.org/news)

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
   - Install required packages. With [uv](https://docs.astral.sh/uv/), `uv sync` installs the game and dev
     dependencies (pytest, mypy, ruff) into `.venv`, and you can skip the virtual environment step above. Without uv:
     ```bash
     pip install -r requirements.txt pytest
     ```
     (`requirements.txt` only has the game's dependencies, so pytest is installed separately.)

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
   uv run pytest   # with uv
   pytest          # without uv, in the virtual environment
   ```

## Default Keys

WASD / ↑←↓→ : Move

K (A button): Open the command menu on the map; select a menu option

J (B button): Close a menu or window, or answer NO

Enter: Select a menu option, like K. On the map it's a shortcut instead of opening the command menu: it does TAKE
when standing on a treasure chest, DOOR when facing a door, or TALK when facing someone

Esc: Close a menu or window, or answer NO, like J. Esc also cancels name entry

I (Start): Pause

F1: Show the controls

F2 / F3 / F4 / F11: Turn auto-stairs, auto-battle, invulnerability or fullscreen on or off

1 / 2 / 3 / 4: Game speed (normal, 2x, 4x, 8x). This works anywhere, including battles, dialogs and
menus, and speeds up everything: walking, text, battle effects and pauses. Only timing changes, not what happens in
the game. Music and sound effects play at normal speed. The speed lasts until you close the game and isn't saved.

Ctrl + / Ctrl - (or hold Ctrl and turn the mouse wheel): Zoom the window in or out, in whole steps of the NES's
256x240 so the pixels stay crisp, from the game's own size (`SCALE`) up to what fits on your screen. Ctrl 0 puts it
back to the size it opened at. This works on every screen; it only changes the window's size, not what the game
shows. It does nothing in fullscreen (F11 keeps your zoom for when you leave fullscreen) and isn't saved.

## Demo video



https://user-images.githubusercontent.com/23140027/165859033-1abe8a84-af2e-48c1-9d74-38cd700d98b5.mp4
