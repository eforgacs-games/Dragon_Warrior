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
