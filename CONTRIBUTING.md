# Contributing

Pull requests welcome! The [README](README.md) covers playing the game; this page is for working on it.

## Setup

Install [uv](https://docs.astral.sh/uv/), then run `uv sync` from the repository root. It installs Python 3.13 (from
`.python-version`) if needed, then the locked dependencies from `uv.lock`, including the dev tools (pytest, mypy,
ruff, pre-commit), into `.venv`. A `.venv` made with an older Python is rebuilt.

Install libgme too, for the NES and SFC music (the README's [Installing libgme](README.md#installing-libgme)). The tests
that play its emulated music skip themselves without it (CI installs it, and sets `REQUIRE_LIBGME=1` so they fail
there instead of skipping); every other test runs the same with or without it. Without libgme the game still runs, but
the NES and SFC music options play the orchestral recordings instead, and the jingles (the inn, the fanfares, the death
and item tunes) are silent with every music option, keeping their timing. The release builds always bundle libgme.

Without uv, use [Python 3.13](https://www.python.org/) (pygame doesn't support 3.14 yet) and
`pip install -r requirements.txt`, which installs the same game dependencies (not the dev tools: add
`pip install pytest pytest-xdist pytest-timeout` to run the tests).

## Running the game

```bash
uv run python -m src.game                 # or python src/game.py, in the virtual environment
uv run python -m src.game --dev           # the development config
uv run python -m src.game --language Korean
```

- `--dev` runs with `src/config/dev_config.py`: god mode, no random battles, your coordinates printed in the
  terminal, no splash screen or opening dialog, darkness off, no autosave, and the debug keys below.
- `--language English` or `--language Korean` plays in that language (a language saved from the options overlay
  wins over it).
- `--smoke-test` loads every game file, plays a few scripted scenes headless and exits with 0, or 1 on any problem;
  the release workflow runs it on every build (`src/smoke_test.py`).

### Playtest checkpoints and debug keys

To start from a point in the story, add `--checkpoint <name>`. A checkpoint is a save file in
`data/checkpoints/`: `throne_room`, `garins_grave`, `swamp_cave`, `rainbow_drop_shrine`, `rainbow_bridge`,
`charlock_throne`, `dragonlord`, `ending_gwaelin_returned` or `ending_carrying_gwaelin`. For example:

```bash
uv run python -m src.game --dev --checkpoint rainbow_bridge
```

Saves made in a game started this way go to a temp folder, not to `src/saves/`.

With `--dev`, these debug keys are also on:
- F5 warps to any map.
- F6 gives an item or gold, sets your level, equips Erdrick's gear, or refills HP and MP.
- F7 loads another checkpoint.
- F8 starts and stops recording frames (see [Finding visual glitches](#finding-visual-glitches)).

F5 to F7 each open a list: type to filter, press Enter to pick, Esc to close.

[PLAYTEST.md](PLAYTEST.md) is a checklist for a pass through the whole game in about 40 minutes, using the
checkpoints.

### VS Code

Open the repository folder, run `uv sync` in the integrated terminal, and choose the interpreter in `.venv` (Python:
Select Interpreter). Then run `uv run python -m src.game` in the terminal, or open `src/game.py` and start it with
Run > Start Debugging (F5), as a Python file. `uv run pytest` runs the tests.

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

## Making a release

Push a tag named `vX.Y.Z` from `main`:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The [Release builds](.github/workflows/release.yml) workflow builds the game with PyInstaller
([dragon_warrior.spec](dragon_warrior.spec)) on Windows, macOS and Linux, with libgme built from source and bundled,
checks that each packaged build starts, loads all of its files and plays a few scripted scenes headless in English and
in Korean (`--smoke-test`, [src/smoke_test.py](src/smoke_test.py)), and publishes them as a GitHub Release for the
tag, with notes generated from the merged PRs. To try the builds without a release, run the workflow from the Actions
tab (Run workflow): the builds are then uploaded as the run's artifacts. PRs that change the build or data/ do the
same.

To build locally: `uv sync --group build`, then `uv run pyinstaller dragon_warrior.spec --noconfirm`. The game is in
`dist/DragonWarrior/` (and `dist/Dragon Warrior.app` on macOS). Check it the way CI does with
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy dist/DragonWarrior/DragonWarrior --smoke-test --language Korean`
(or `--language English`). A local build bundles libgme only if `GME_LIBRARY` (and `GME_LICENSE`) point at a build of
it, as the workflow sets them.

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

## Measuring performance

`tools/benchmark.py` plays fixed scenes headless (the throne room, the courtyard, Brecconary, Cantlin, walking on
Alefgard, a fight, the COMMAND window, a dialog's ▼ wait and a map change), each from the `throne_room` checkpoint
with a fixed random seed, at 1x and 8x. For each it reports the time of a pass of the main loop split into game logic
and drawing (mean / median / p95 / max), the map frames and the frames shown per second against 60 × the speed, CPU
time against real time (a busy wait shows up as a high CPU share), and the `display.flip` and `display.update` calls.
Run `uv run python -m tools.benchmark --help` for the scenes and options.

```bash
uv run python -m tools.benchmark --json before.json        # on main
uv run python -m tools.benchmark --json after.json         # on your branch
uv run python -m tools.benchmark --compare before.json after.json
# One scene, profiled: the 20 functions with the most time of their own
uv run python -m tools.benchmark --scenes brecconary --speeds 8 --profile 20
```

`--music NES` (or `SFC`, `Orchestra`) plays the scenes with the music on, so the CPU column includes the music: the
NES and SFC soundtracks are emulated on a thread of their own (`src/music_stream.py`).

Timings depend on the machine and on what else runs on it, so compare runs made on the same machine, close together,
and with `--repeat 3` (each scene's fastest run is kept) when the machine is busy.
