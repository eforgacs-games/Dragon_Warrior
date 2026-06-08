import locale

SCALE = 2
LANGUAGE, ENCODING = locale.getlocale()

base_config = {
    "START_MAP": "TantegelThroneRoom",
    "FPS": 60,
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
    "SHOW_COORDINATES": False,
    "COLOR_KEY": (0, 128, 128),
    "TEXT_SPEED": "Fast",
    "NO_WAIT": False,
    "GOD_MODE": False,
    "INVULNERABLE": False,
    "AUTO_STAIRS": False,
    "AUTO_BATTLE": False,
    "RENDER_TEXT": True,
    "NO_BLIT": False,
}
