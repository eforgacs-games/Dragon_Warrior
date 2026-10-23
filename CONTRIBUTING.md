Pull requests welcome!

## Setup

Install [uv](https://docs.astral.sh/uv/), then run `uv sync` from the repository root. It installs Python 3.13 (from
`.python-version`) if needed, then the locked dependencies from `uv.lock`, including the dev tools (pytest, mypy,
ruff, pre-commit), into `.venv`. A `.venv` made with an older Python is rebuilt.

## Checks

CI (`.github/workflows/python-app.yml`) runs these on Python 3.13. Run them before opening a pull request:

```bash
uv run ruff check .
uv run mypy          # settings are in pyproject.toml
uv run pytest
```

`uv run pytest -n auto` runs the tests in parallel with [pytest-xdist](https://pytest-xdist.readthedocs.io/), one
worker per CPU, as CI does; plain `uv run pytest` runs them in one process. Each worker is its own process, so tests
that write files must use their own temporary directory (`tempfile.TemporaryDirectory()`), not a fixed path, and tests
whose result depends on a random roll must patch the roll or seed `random` themselves rather than rely on what ran
before them.

The tests run headless: `tests/__init__.py` points SDL at its dummy video and audio drivers. Tests that need a `Game`
can make one with `new_game()` from `tests/helpers.py`.

### Timeout

Each test has 60 seconds ([pytest-timeout](https://github.com/pytest-dev/pytest-timeout), `timeout` in
`pyproject.toml`), counting its setup (including `setUpClass`) and teardown. A test that goes over fails with the stack of
where it was stuck, so a wait loop that never ends fails that one test instead of hanging the whole run. The slowest
tests take about 25 seconds on CI's runners and under 10 locally; one that legitimately needs longer can say so with `@pytest.mark.timeout(N)`. CI lists the
10 slowest tests at the end of its pytest log, and `uv run pytest --durations=10` does the same locally. To debug a test
without being cut off, pass `--timeout=0`.

### Coverage

CI measures line coverage of `src/` and fails if the total drops below 95% (`--cov-fail-under` in
`.github/workflows/python-app.yml`). To see it locally, with the lines each module misses:

```bash
uv run pytest -n auto --cov=src --cov-report=term-missing
```

## Pre-commit hook

[pre-commit](https://pre-commit.com/) can run the checks on every `git commit`: ruff and mypy (through `uv run`, so the
same versions and settings as CI), plus trailing-whitespace, YAML and large-file checks. It's in the dev dependencies;
install the hook once per clone:

```bash
uv run pre-commit install
```

`uv run pre-commit run --all-files` runs it on the whole tree without committing. The hook doesn't run the tests, which
take a while; run pytest before opening a pull request. `git commit --no-verify` skips the hook.

## Dependencies

Change dependencies in `pyproject.toml` (or with `uv add`), then regenerate `requirements.txt`. CI fails if it doesn't
match `uv.lock`:

```bash
uv export --locked --no-dev --no-hashes --no-annotate -o requirements.txt
```

## Translations

The Korean text is in `data/text/locales/ko/LC_MESSAGES/base.po`. Editing it is all there is to do: the game compiles
it in memory when it runs (`src/catalog.py`), so there's no `.mo` file to build or commit (`*.mo` is ignored).

`tests/test_translations.py` fails when new text has no Korean translation. To add empty entries for it to the end of
`base.po`, ready to fill in:

```bash
uv run python data/text/locales/catalog_tools.py add
```

`catalog_tools.py missing` lists the untranslated text without changing anything.

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
