import locale

SCALE = 2
LOCALE, ENCODING = locale.getlocale()


def language_from_locale(locale_name: str | None) -> str:
    """The game compares LANGUAGE against language names ('English', 'Korean'), not locale codes like 'en_US' or
    'ko_KR', so map the system locale to one of those names. Anything that isn't Korean plays in English."""
    if locale_name and locale_name.lower().startswith('ko'):
        return 'Korean'
    return 'English'


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
    "FIGHTERS_RING_ATTACK_BONUS": 0,  # 0 = NES (no effect); any other value is added to attack while worn
    "FORCE_ENEMY": None,  # e.g. "Metal Slime"; overrides the random enemy for the zone
    "NO_BATTLES": False,
    "NPCS_MAKE_WAY": True,  # not NES: a roaming NPC the hero walks into steps aside (MovementController.ask_npc_to_make_way)
    "ORCHESTRA_MUSIC_ENABLED": True,
    "SHOW_FPS": False,
    "LANGUAGE": language_from_locale(LOCALE),
    "SHOW_COORDINATES": False,
    "COLOR_KEY": (0, 128, 128),
    # "Fast", "Normal" or "Slow": NES MessageSpeed, 1, 2 or 3 frames per character. Normal, as a new NES quest starts
    # with (NewQuest); a game started or loaded from the title menu sets it per adventure log (src/options_screen.py)
    "TEXT_SPEED": "Normal",
    # "Classic": the NES dialog window, whose text scrolls; "Modern": each message replaces the last (not NES)
    "DIALOG_STYLE": "Classic",
    # "NES": screen fades step through the NES palette (PalFadeOut/PalFadeIn); "Smooth": a black overlay alpha fade
    # (not NES). See src/visual_effects.py screen_fade.
    "FADE_STYLE": "NES",
    "NO_WAIT": False,
    "GOD_MODE": False,
    "INVULNERABLE": False,
    "AUTO_STAIRS": True,  # STAIRS: True steps onto stairs to take them (not NES); False needs the STAIRS command (NES)
    "AUTO_BATTLE": False,
    # GRIND STOP (not NES): the HP at which auto-grind (G, src/auto_grind.py) stops: "RedHP" (the NES's low HP, where
    # the windows turn red), "HalfHP" or "ThreeQuartersHP"
    "AUTO_GRIND_STOP": "RedHP",
    "RENDER_TEXT": True,
    "NO_BLIT": False,
    "DEBUG_KEYS": False,  # F5-F7 warp, give and checkpoint menus (src/debug_tools.py); dev_config turns them on
    "CHECKPOINT": None,  # e.g. "rainbow_bridge": start from data/checkpoints/<name>.json (also --checkpoint)
    "SAVE_DIR": None,  # None saves to src/saves
}
