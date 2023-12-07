import locale

SCALE = 2
LANGUAGE, ENCODING = locale.getlocale()

test_config = {
    "START_MAP": "TantegelThroneRoom",
    "FPS": 60,
    "REPLIT_DATA_DIR": '..\\data',
    "SCALE": SCALE,
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
    "ORCHESTRA_MUSIC_ENABLED": True,
    "SHOW_FPS": False,
    "LANGUAGE": LANGUAGE.split("_")[0],
    # "LANGUAGE": 'Korean',
    # This prints out the current coordinates that the player is standing on.
    "SHOW_COORDINATES": False,
    "COLOR_KEY": (0, 128, 128),
    "TEXT_SPEED": "Fast",
    "NO_WAIT": False,
    "GOD_MODE": False,
    "RENDER_TEXT": True,
    "NO_BLIT": False
}
