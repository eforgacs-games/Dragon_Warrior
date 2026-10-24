from src.config.base_config import base_config

test_config = {
    **base_config,
    "MUSIC_ENABLED": False,
    "SOUND_ENABLED": False,
    "SPLASH_SCREEN_ENABLED": False,
    "INITIAL_DIALOG_ENABLED": False,
    "TEXT_SPEED": "Fast",  # the tests time dialog at the fastest speed
    "AUTOSAVE": False,  # no autosave files from the tests; tests/test_autosave.py turns it on in a temporary folder
    "NAME_CONFIRM": False,  # the name entry tests check the NES rules; tests/test_name_confirm.py turns it on
    "SETTINGS_PATH": None,  # never read or write the player's own settings file (src/settings.py)
}
