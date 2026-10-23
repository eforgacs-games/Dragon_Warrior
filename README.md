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

U (Select) or Tab: Open the options over the map, and close them again (J and Esc close them too). Up and down pick
a setting; left, right or K change it, and the change applies at once. Each adventure log saves its own the next time
you save with the king:
- MESSAGE SPEED: FAST, NORMAL or SLOW, the NES's own setting, which you also choose when you begin a quest or with
  CHANGE MESSAGE SPEED on the title menu

The rest are settings this game adds, none of them on the NES:
- DIALOG STYLE: CLASSIC (NES), the NES dialog window whose text scrolls, or MODERN, each message on a fresh window
- NPCS MAKE WAY: ON, a townsperson you walk into steps aside, or OFF (NES), they stay in your way
- FADE STYLE: NES, fades through the NES palette, or SMOOTH, a black fade
- STAIRS: STEP ON, stepping onto stairs takes them, or NES, only the STAIRS command does
- GRIND STOP: when auto-grind (G) stops: RED HP, the NES's low HP where the windows turn red (HP at or below a quarter
  of the maximum, plus 1), HALF HP or 3/4 HP

H: Show the controls

G: Auto-grind, not on the NES. On a map with random fights, the hero walks back and forth between his tile and a safe
one next to it and chooses FIGHT in every fight, moving every message on by itself, until a decision is yours: HP at
or below the GRIND STOP setting (checked at the start of every turn, so you get the battle's command window to HEAL
or RUN, and after every fight and step), the hero asleep or STOPSPELLed, a guardian or the Dragonlord, or a level up
(press G to go on). G or any other key stops it too; 1 to 5 still change the game speed. F4 auto-battle is ignored
while it runs.

F4 / F9 / F11: Turn auto-battle, invulnerability or fullscreen on or off

Shift + F1 / F2 / F3: Save state 1, 2 or 3, and F1 / F2 / F3: load it. Not on the NES: a save state is like an
emulator's, a complete snapshot of the game that loading puts back exactly (the map and where everyone stands, the
hero, every story flag, the opened doors and chests, the timers, the NPCs' movement and the random number generator,
so the same keys play out the same way again). It works on the map whenever START would pause the game, once the hero
has finished his step; not in a fight, a dialog or a menu. States are kept in the save folder as `state_1.json` to
`state_3.json`, apart from the adventure logs, which save as the NES does. A state saved by an older version of the
game, after its format has changed, is refused with a message. The game speed, auto-battle, invulnerability and
fullscreen aren't part of a state.

Backspace (hold): Rewind, not on the NES. On the map, the game keeps a snapshot like a save state's every 30 frames
(the last 60, about 30 seconds at normal speed) and one just before every fight. Holding Backspace steps back through
them, a few frames apart; let go and play goes on from the one on screen (the ones after it are forgotten). It works
when START would pause the game, not in a fight, a dialog or a menu; after a fight, rewinding goes back to just before
it. The snapshots are only kept in memory, for this session.

1 / 2 / 3 / 4 / 5: Game speed (normal, 2x, 4x, 8x, 16x). This works anywhere, including battles, dialogs and
menus, and speeds up everything: walking, text, battle effects and pauses. On the map the higher speeds go as fast as
the computer can draw it, up to the speed you chose. Only timing changes, not what happens in
the game. Music and sound effects play at normal speed. The speed lasts until you close the game and isn't saved.

Ctrl + / Ctrl - (or hold Ctrl and turn the mouse wheel): Zoom the window in or out, in whole steps of the NES's
256x240 so the pixels stay crisp, from the game's own size (`SCALE`) up to what fits on your screen. Ctrl 0 puts it
back to the size it opened at. This works on every screen; it only changes the window's size, not what the game
shows. It does nothing in fullscreen (F11 keeps your zoom for when you leave fullscreen) and isn't saved.

## Controller

A controller works everywhere the keyboard does, alongside it: plug it in before or while the game runs (with more
than one, the first is used). SDL's controller database maps the common pads (Xbox, PlayStation, Switch Pro, Steam
Deck, 8BitDo and others) without setup. The buttons are named here by where they are on the pad, whatever they're
labelled, as on the NES and SNES:

| Controller | Does |
| --- | --- |
| Right face button (Xbox B, PlayStation circle, Switch A) | A button (K) |
| Bottom face button (Xbox A, PlayStation cross, Switch B) | B button (J) |
| Start / Menu / Options | Start (I) |
| Back / View / Share / Minus | Select (U): the options |
| D-pad or left stick | Move (the arrows). The NES has no diagonals: the stick presses the way it is pushed furthest |
| Right trigger | Next game speed (1x, 2x, 4x, 8x, 16x, then 1x again) |
| Left shoulder button (LB, L1, L) | Load state 1 (F1) |
| Right shoulder button (RB, R1, R) | Save state 1 (Shift+F1) |
| Left trigger, held | Rewind (Backspace held) |

On the name entry screen a controller button switches to joystick input (the arrows and A pick the letters) without
Tab.

## Demo video



https://user-images.githubusercontent.com/23140027/165859033-1abe8a84-af2e-48c1-9d74-38cd700d98b5.mp4
