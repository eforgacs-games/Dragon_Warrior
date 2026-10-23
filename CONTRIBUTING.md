Pull requests welcome!

## Setup

Install [uv](https://docs.astral.sh/uv/), then run `uv sync` from the repository root. It installs the locked
dependencies from `uv.lock`, including the dev tools (pytest, mypy, ruff), into `.venv`.

## Checks

CI (`.github/workflows/python-app.yml`) runs these on Python 3.10 and 3.13. Run them before opening a pull request:

```bash
uv run ruff check .
uv run mypy          # settings are in pyproject.toml
uv run pytest
```

The tests run headless: `tests/__init__.py` points SDL at its dummy video and audio drivers. Tests that need a `Game`
can make one with `new_game()` from `tests/helpers.py`.

## Dependencies

Change dependencies in `pyproject.toml` (or with `uv add`), then regenerate `requirements.txt`. CI fails if it doesn't
match `uv.lock`:

```bash
uv export --locked --no-dev --no-hashes --no-annotate -o requirements.txt
```

## Reference scripts

`reference/reference_utility_scripts/` has offline scripts that regenerate checked-in files from the NES data:
`make_text_beep.py` synthesizes `data/sound/sfx/text_beep.wav`, and `extract_nes_map_data.py` extracts
`tests/nes_map_data.py` from the nmikstas disassembly. Each one's docstring says how to run it.

## Finding visual glitches

`src/frame_recorder.py` records every frame the game presents (each `display.flip` and `display.update`), diffs
consecutive frames and flags one-frame flickers: a frame that differs from both neighbours while they match each
other. It wraps nothing unless it's recording.

- **A scripted scene, headless:** `tools/record_frames.py` plays a scene from a checkpoint (or the title screen) in
  real time and saves a PNG per change of picture plus `report.txt` (what changed, how many pixels and rows, where,
  and anything suspicious). Run `uv run python -m tools.record_frames --help` for the script steps.

  ```bash
  # King Lorik's opening speech, from the throne_room checkpoint
  uv run python -m tools.record_frames --checkpoint throne_room --script "wait:30,a,wait:300,a,wait:300,a,wait:300,a" --out /tmp/frames
  # Open the COMMAND window, choose TALK, close the dialog
  uv run python -m tools.record_frames --checkpoint garins_grave --script "wait:30,talk,wait:120,b" --out /tmp/frames
  ```

- **While playing:** with `--dev`, **F8** starts recording and **F8** again stops and saves the frames and report
  to a new folder in the system temp folder (`dragon_warrior_frames`); the path is printed in the terminal.
- **In tests:** record a transition and assert on it.

  ```python
  from src.frame_recorder import assert_no_one_frame_flickers, recording

  with recording() as frames:
      game.change_map(...)
  assert_no_one_frame_flickers(frames)
  ```

  `find_flickers(frames, max_length=2, region=...)` finds longer flickers or looks at part of the screen only, and
  each `Frame` gives its picture (`frame.surface()`). `tests/test_transition_frames.py` has examples.

A frame is one flip or update, and the game holds some pictures with a wait instead of drawing them again, so in a
real-time recording the report gives how long each flagged picture was on screen; under 2 frames (33 ms) is what the
eye catches. The recorder treats `display.update(rect)` as showing the whole screen, as it does on the game's SCALED
window (`FrameRecorder(partial_updates=True)` models a plain software display instead).
