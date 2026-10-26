"""Run before any test module is imported.

The tests must never read or write the player's own settings file (src/settings.py). test_config keeps none
(SETTINGS_PATH None), and a test of the settings file points SETTINGS_PATH at a temporary folder; this is for anything
else that ends up with USER_SETTINGS (a test that makes a Game from prod_config, say): $DRAGON_WARRIOR_SETTINGS sends it
to a temporary folder of its own, removed when the run ends.
"""
import atexit
import os
import shutil
import tempfile
from unittest.mock import patch

import pytest

from src.display_filters import PRESENTER, SCALING_SMOOTH
from src.settings import SETTINGS_ENV_VAR, SETTINGS_FILE_NAME

_settings_dir = tempfile.mkdtemp(prefix='dragon_warrior_test_settings_')
os.environ[SETTINGS_ENV_VAR] = os.path.join(_settings_dir, SETTINGS_FILE_NAME)
atexit.register(shutil.rmtree, _settings_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def soundtrack_music_as_chosen():
    """The NES and SFC soundtracks' music is the chosen soundtrack's whether or not libgme is installed (without it, the
    game plays the orchestral recordings instead: src/directories.py playable_soundtrack), so the tests see the same
    music on every machine. The tests of that fallback patch it themselves."""
    with patch('src.directories.chiptune_available', return_value=True):
        yield


@pytest.fixture(autouse=True)
def display_filters_off():
    """The display filters (src/display_filters.py) replace pygame.display.flip and update while one is on: a test that
    turns one on doesn't leave them on for the next."""
    yield
    if PRESENTER.active:
        PRESENTER.configure(False, SCALING_SMOOTH)
