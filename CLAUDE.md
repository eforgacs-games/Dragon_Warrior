# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python implementation of Dragon Warrior (Dragon Quest) for the NES, built using Pygame. It's a complete RPG with battles, maps, NPCs, sound, music, and multilingual support. Python 3.13 only (`requires-python = ">=3.13,<3.14"`; pygame 2.6.1 has no 3.14 wheels).

### NES accuracy
The goal is to match the NES game. Formulas, messages and behavior are checked against the hand-made disassembly at https://github.com/nmikstas/dragon-warrior-disassembly (`source_files/Bank00.asm`–`Bank03.asm`, `Dragon_Warrior_Defines.asm`), and the code cites the NES routine it follows (e.g. `# NES PlyrCalcHitDmg`). Features the NES doesn't have are optional settings with an NES value.

## Development Commands

### Running the Game
- **Main game**: `uv run python -m src.game` (or `python src/game.py`). Flags: `--dev` (`dev_config`), `--checkpoint <name>` (start from a playtest checkpoint; see `PLAYTEST.md`), `--language English|Korean`, `--smoke-test` (load every game file, play a few scenes headless, exit 0 or 1; the release workflow runs it)
- **Entry point**: `uv run python -m src.main` starts the game with `prod_config` and no flags (`python src/main.py` fails: it doesn't put the repository root on `sys.path` the way `src/game.py` does)

### Testing
- **Run all tests**: `uv run pytest` (add `-n auto` to run them in parallel with pytest-xdist, as CI does)
- **Run specific test**: `uv run pytest tests/test_<module_name>.py`
- CI fails below 95% coverage, and any single test that runs over 60 s fails (pytest-timeout)

### Linting
- **Lint**: `uv run ruff check .` (settings in `pyproject.toml`; `--fix` applies safe fixes)
- **Type check**: `uv run mypy` (settings in `pyproject.toml`). CI runs ruff, mypy and pytest.

### Dependencies
- **Install**: `uv sync` (managed by uv, locked in `uv.lock`). `requirements.txt` is generated from the lock with `uv export` (the command is in its header); CI fails if it's out of date, except on Dependabot's PRs, where a CI job regenerates and commits it.
- **Core dependency**: pygame. pygame-menu was removed (#299); menus and windows are drawn by `src/window_renderer.py`.

## Architecture

### Configuration System
Three environment configurations in `src/config/`, each built on `base_config.py`:
- `prod_config.py`: Production settings (default)
- `dev_config.py`: Development settings, used with `--dev`: god mode, no battles, coordinates visible, debug keys, no splash screen or opening dialog, darkness off, no autosave, starts in the throne room (`START_MAP`)
- `test_config.py`: Test environment settings

### Core Game Loop
The main `Game` class in `src/game.py` orchestrates:
- Event handling and input processing
- Runtime state in `GameState` and story progress in `StoryFlags` (see below)
- Map rendering and transitions
- Battle system integration
- Sound and music management

### Key Modules

**Player System** (`src/player/`):
- `player.py`: Main Player class extending AnimatedSprite
- `player_stats.py`: Level progression, stat calculations, experience handling

**Map System**:
- `maps.py`: DragonWarriorMap class for map rendering and collision
- `map_layouts.py`: Static map tile definitions
- `maps_functions.py`: Map parsing utilities

**Battle System**:
- `battle.py`: one battle: enemy setup, damage formulas, running away, victory
- `battle_controller.py`: the battle loop, player commands and the enemy's turn
- `encounters.py`: random encounters after each step

**Other key modules** (`src/` has many more; this list isn't complete):
- `map_manager.py`: map changes, staircases and warps
- `menu.py`: the command menu, spells and items
- `story_flags.py`: story progress (`StoryFlags`), saved with the game
- `save_state.py`: full snapshots of the game on the map (not an NES feature)
- `window_renderer.py`: draws NES windows tile by tile
- `npc_movement.py`: where roaming NPCs may step
- `checkpoints.py`: named playtest checkpoints in `data/checkpoints/`

**Sprite System** (`src/sprites/`):
- `base_sprite.py`: Core sprite functionality
- `animated_sprite.py`: Animation handling
- `fixed_character.py`: NPCs and static characters
- `roaming_character.py`: Moving characters

**Data Organization**:
- `data/images/`: All game sprites and UI elements
- `data/sound/`: Music (`NES`, `SFC` and `orchestra` soundtracks, chosen by the `SOUNDTRACK` setting) and sound effects
- `data/text/`: Dialog, internationalization (English/Korean support)
- `data/fonts/`: Game fonts
- `data/checkpoints/`: Playtest checkpoint saves (see `PLAYTEST.md`)

### Game State
`GameState` (`src/game_state.py`) is a class holding runtime flags (movement, roaming, initial dialog, light radius and so on), not an enum of screens. Story progress is in `StoryFlags` (`src/story_flags.py`).

### Testing Strategy
- Unit tests in `tests/` directory
- Each major module has corresponding test file
- Tests are written as unittest `TestCase` classes with pygame dummy drivers, and run with pytest
- CI (GitHub Actions) runs ruff, mypy and pytest

## Key Development Notes

### Audio/Video Setup
Tests use dummy SDL drivers to avoid requiring display/audio hardware:
```python
os.environ['SDL_VIDEODRIVER'] = 'dummy' 
os.environ['SDL_AUDIODRIVER'] = 'dummy'
```

### Configuration Usage
Different configs enable rapid development:
- Use `dev_config` (`--dev`) for debugging: god mode, no battles, visible coordinates, debug keys
- Use `test_config` for unit testing
- Use `prod_config` for normal gameplay

### Map Development
Maps are defined as 2D arrays in `map_layouts.py` with tile IDs corresponding to sprites in the tileset. New maps require:
1. Layout definition
2. Tileset sprite mapping
3. NPC/character placement
4. Music assignment

### Internationalization
Text system supports multiple languages via gettext. Dialog is stored in `data/text/dialog_lookup_table.py` with translation files in `data/text/locales/`.