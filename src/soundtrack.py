"""The MUSIC setting: which soundtrack plays (not NES, the NES has only its own).

- NES: the NES music (data/sound/music/NES).
- SFC: the Super Famicom remake's soundtrack (data/sound/music/SFC).
- ORCHESTRA: the London Philharmonic Orchestra's recording (data/sound/music/orchestra), the default.

The jingles (the inn, the level up, the victory, the death and the rest) are the NES's with every soundtrack
(src/directories.py Directories); only the map, fight and story music changes (music_paths).

The setting used to be a switch, ORCHESTRA_MUSIC_ENABLED in the config and OrchestraMusic in the saves and save states:
on loads as ORCHESTRA and off as NES (soundtrack_from_legacy_switch).
"""
from enum import StrEnum
from typing import Any


class Soundtrack(StrEnum):
    NES = 'NES'
    SFC = 'SFC'
    ORCHESTRA = 'Orchestra'


# The config key, and the save file key (src/options_screen.py Options, kept per adventure log and in save states)
SOUNDTRACK_KEY = 'SOUNDTRACK'
SOUNDTRACK_SAVE_KEY = 'Soundtrack'
# The old on/off switch these replace: True was the orchestral soundtrack, False the NES's
LEGACY_ORCHESTRA_CONFIG_KEY = 'ORCHESTRA_MUSIC_ENABLED'
LEGACY_ORCHESTRA_SAVE_KEY = 'OrchestraMusic'

# The order the options overlay's MUSIC row goes round in
SOUNDTRACKS = (Soundtrack.NES, Soundtrack.SFC, Soundtrack.ORCHESTRA)
# As the game has always started: a new quest, a config or a save without the setting
DEFAULT_SOUNDTRACK = Soundtrack.ORCHESTRA


def parse_soundtrack(value: Any) -> Soundtrack | None:
    """The soundtrack a saved or configured value names ('NES', 'SFC' or 'Orchestra'); None if it names none."""
    try:
        return Soundtrack(value)
    except ValueError:
        return None


def soundtrack_from_legacy_switch(orchestra_music: Any) -> Soundtrack | None:
    """The old ORCHESTRA_MUSIC_ENABLED / OrchestraMusic switch: on is ORCHESTRA, off is NES; None if it isn't a bool."""
    if not isinstance(orchestra_music, bool):
        return None
    return Soundtrack.ORCHESTRA if orchestra_music else Soundtrack.NES


def soundtrack_from_save(save: dict) -> Soundtrack:
    """The log's (or save state's) soundtrack: its Soundtrack entry, or, for a save from before there were three, its
    OrchestraMusic switch; the default for a save with neither."""
    return (parse_soundtrack(save.get(SOUNDTRACK_SAVE_KEY))
            or soundtrack_from_legacy_switch(save.get(LEGACY_ORCHESTRA_SAVE_KEY))
            or DEFAULT_SOUNDTRACK)


def soundtrack(config: dict) -> Soundtrack:
    """The soundtrack the game plays: the config's old ORCHESTRA_MUSIC_ENABLED switch if it still sets one (as
    migrate_legacy_music_config reads it), its SOUNDTRACK otherwise."""
    return (soundtrack_from_legacy_switch(config.get(LEGACY_ORCHESTRA_CONFIG_KEY))
            or parse_soundtrack(config.get(SOUNDTRACK_KEY))
            or DEFAULT_SOUNDTRACK)


def migrate_legacy_music_config(config: dict) -> None:
    """A config that still sets the old ORCHESTRA_MUSIC_ENABLED switch (a custom config, or one built on base_config
    before SOUNDTRACK) gets the soundtrack it meant, so the options overlay's MUSIC row shows it. The switch wins over
    base_config's SOUNDTRACK default, since it was set on purpose."""
    legacy = soundtrack_from_legacy_switch(config.pop(LEGACY_ORCHESTRA_CONFIG_KEY, None))
    if legacy is not None:
        config[SOUNDTRACK_KEY] = legacy
