import locale

SCALE = 2
LOCALE, CHARACTER_ENCODING = locale.getlocale()

# TODO: Put start map in config

prod_config = {
    "START_MAP": "TantegelThroneRoom",
    "FPS": 60,
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
    "ORCHESTRA_MUSIC_ENABLED": True,
    "SHOW_FPS": False,
    "LOCALE, CHARACTER_ENCODING": locale.getlocale(),
    "LANGUAGE": LOCALE.split("_")[0],
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

dev_config = {
    "START_MAP": "TantegelThroneRoom",
    # "START_MAP": "TantegelCourtyard"
    # "START_MAP": "Alefgard"

    # towns
    # "START_MAP": "Brecconary"
    # "START_MAP": "Garinham"
    # "START_MAP": "Kol"
    # "START_MAP": "Rimuldar"
    # "START_MAP": "Hauksness"
    # "START_MAP": "Cantlin"

    # caves

    # "START_MAP": "CharlockB1"
    # "START_MAP": "SwampCave"
    # "START_MAP": "MountainCaveB1"

    # "START_MAP": "MagicTemple"
    "FPS": 60,
    "SCALE": 2,
    "TILE_SIZE": 16 * SCALE,
    "NES_RES": (256, 240),
    "FULLSCREEN_ENABLED": False,
    "ENABLE_DARKNESS": True,
    "MUSIC_ENABLED": True,
    "SOUND_ENABLED": True,
    "SPLASH_SCREEN_ENABLED": False,
    "INITIAL_DIALOG_ENABLED": False,
    "FORCE_BATTLE": False,
    "NO_BATTLES": False,
    "ORCHESTRA_MUSIC_ENABLED": True,
    "SHOW_FPS": False,
    "LOCALE, CHARACTER_ENCODING": locale.getlocale(),
    "LANGUAGE": LOCALE.split("_")[0],
    # "LANGUAGE": 'Korean',
    # This prints out the current coordinates that the player is standing on.
    "SHOW_COORDINATES": False,
    "COLOR_KEY": (0, 128, 128),
    "TEXT_SPEED": "Fast",
    "NO_WAIT": False,
    "GOD_MODE": True,
    "RENDER_TEXT": True,
    "NO_BLIT": False

}

# TODO: Put test_config into tests folder
test_config = {
    "START_MAP": "TantegelThroneRoom",
    "FPS": 60,
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
    "ORCHESTRA_MUSIC_ENABLED": True,
    "SHOW_FPS": False,
    "LOCALE, CHARACTER_ENCODING": locale.getlocale(),
    "LANGUAGE": LOCALE.split("_")[0],
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
