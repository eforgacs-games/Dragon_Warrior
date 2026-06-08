from src.config.base_config import base_config

dev_config = {
    **base_config,
    # Uncomment to start on a specific map:
    "START_MAP": "TantegelThroneRoom",
    # "START_MAP": "TantegelCourtyard",
    # "START_MAP": "TantegelCellar",
    # "START_MAP": "Alefgard",
    # "START_MAP": "Brecconary",
    # "START_MAP": "Garinham",
    # "START_MAP": "Kol",
    # "START_MAP": "Rimuldar",
    # "START_MAP": "Hauksness",
    # "START_MAP": "Cantlin",
    # "START_MAP": "CharlockB1",
    # "START_MAP": "SwampCave",
    # "START_MAP": "MountainCaveB1",
    # "START_MAP": "GarinsGraveB1",
    # "START_MAP": "MagicTemple",

    "ENABLE_DARKNESS": False,
    "SPLASH_SCREEN_ENABLED": False,
    "INITIAL_DIALOG_ENABLED": False,
    "NO_BATTLES": True,
    "SHOW_COORDINATES": True,
    "GOD_MODE": True,
    # "LANGUAGE": 'Korean',
}
