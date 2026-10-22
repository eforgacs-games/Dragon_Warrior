from src.config.base_config import base_config

test_config = {
    **base_config,
    "MUSIC_ENABLED": False,
    "SOUND_ENABLED": False,
    "SPLASH_SCREEN_ENABLED": False,
    "INITIAL_DIALOG_ENABLED": False,
    "TEXT_SPEED": "Fast",  # the tests time dialog at the fastest speed
}
