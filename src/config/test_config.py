from src.config.base_config import base_config
from src.soundtrack import Soundtrack

test_config = {
    **base_config,
    "MUSIC_ENABLED": False,
    "SOUND_ENABLED": False,
    # The orchestral recordings, not base_config's NES soundtrack: a test that turns the music on and then closes
    # pygame itself would leave the chiptune stream's thread (src/music_stream.py) queueing on a closed mixer. The tests
    # of the NES and SFC music choose them themselves.
    "SOUNDTRACK": Soundtrack.ORCHESTRA,
    "SPLASH_SCREEN_ENABLED": False,
    "INITIAL_DIALOG_ENABLED": False,
    "TEXT_SPEED": "Fast",  # the tests time dialog at the fastest speed
    "AUTOSAVE": False,  # no autosave files from the tests; tests/test_autosave.py turns it on in a temporary folder
    "NAME_CONFIRM": False,  # the name entry tests check the NES rules; tests/test_name_confirm.py turns it on
    "SETTINGS_PATH": None,  # never read or write the player's own settings file (src/settings.py)
}
