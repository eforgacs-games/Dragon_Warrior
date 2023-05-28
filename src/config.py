import locale
import sys

SCALE = 2
LOCALE, CHARACTER_ENCODING = locale.getlocale()

prod_config = {
    "FPS": sys.maxsize,
    "REPLIT_DATA_DIR": '..\\data',
    "SCALE": 2,
    "TILE_SIZE": 16 * SCALE,
    "NES_RES": (256, 240),
    "FULLSCREEN_ENABLED": False,
    "ENABLE_DARKNESS": True,
    "MUSIC_ENABLED": True,
    "SOUND_ENABLED": True,
    "SPLASH_SCREEN_ENABLED": True,
    "INITIAL_DIALOG_ENABLED": True,
    "FORCE_BATTLE": False,
    "NO_BATTLES": False,
    "ORCHESTRA_MUSIC_ENABLED": False,
    "SHOW_FPS": False,
    "LOCALE, CHARACTER_ENCODING": locale.getlocale(),
    "LANGUAGE": LOCALE.split("_")[0],
    "# LANGUAGE": 'Korean',
    # This prints out the current coordinates that the player is standing on.,
    "SHOW_COORDINATES": False,
    "COLOR_KEY": (0, 128, 128),
    "TEXT_SPEED": "Fast",
    "NO_WAIT": False
}
dev_config = {
    "FPS": 60,
    "SCALE": 2,
    "TILE_SIZE": 16 * SCALE,
    "NES_RES": (256, 240),
    "FULLSCREEN_ENABLED": False,
    "DEV_MODE": False,
    "ENABLE_DARKNESS": True,
    "MUSIC_ENABLED": False,
    "SOUND_ENABLED": False,
    "SPLASH_SCREEN_ENABLED": False,
    "INITIAL_DIALOG_ENABLED": False,
    "FORCE_BATTLE": False,
    "NO_BATTLES": False,
    "ORCHESTRA_MUSIC_ENABLED": False,
    "SHOW_FPS": False,
    "LOCALE, CHARACTER_ENCODING": locale.getlocale(),
    "LANGUAGE": LOCALE.split("_")[0],
    "# LANGUAGE": 'Korean',
    # This prints out the current coordinates that the player is standing on.,
    "SHOW_COORDINATES": False,
    "COLOR_KEY": (0, 128, 128),
    "TEXT_SPEED": "Fast",
    "NO_WAIT": False
}
