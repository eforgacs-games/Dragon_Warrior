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

from src.settings import SETTINGS_ENV_VAR, SETTINGS_FILE_NAME

_settings_dir = tempfile.mkdtemp(prefix='dragon_warrior_test_settings_')
os.environ[SETTINGS_ENV_VAR] = os.path.join(_settings_dir, SETTINGS_FILE_NAME)
atexit.register(shutil.rmtree, _settings_dir, ignore_errors=True)
