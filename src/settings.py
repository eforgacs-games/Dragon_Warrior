"""The global settings: the player's own, kept from one launch to the next, in one small file. Not NES behavior.

They are the window zoom (Ctrl + / Ctrl -, src/zoom.py), fullscreen (F11, Game.handle_fullscreen_toggle), the game
speed (keys 1 to 5, src/waiting.py), the language, the display filters, the view and the dungeon map (the options
overlay's LANGUAGE, SCANLINES, SCALING, VIEW and DUNGEON MAP rows, src/options_overlay.py, src/display_filters.py,
src/view.py and src/dungeon_map.py).
They belong to whoever plays on this computer, not to an adventure, so they are kept apart from the adventure logs
(src/save_file.py), which carry the per-adventure options (message speed, dialog style and the rest).

The file is JSON, in the per-user config folder (src/paths.py user_config_dir), e.g. on Linux
~/.config/dragon-warrior/settings.json:

    {"version": 1, "zoom": 3, "fullscreen": false, "game_speed": 1, "language": "Korean", "scanlines": false,
     "scaling": "Smooth", "view": "NES", "dungeon_map": true}

"zoom" and "language" can be null: the window opens at its normal size, and the language comes from the system locale
(base_config language_from_locale). A saved language wins over the locale.

The game reads it once at start (Game.__init__), before the window opens, so the window comes up at the saved zoom and
in fullscreen if that was saved, and writes it whenever one of the settings changes. A missing file, one that isn't
JSON, or a value that makes no sense means the default for that setting; the game never fails to start over it. A file
that can't be written (a read-only folder) only prints a warning.

The config's SETTINGS_PATH says where the file is: USER_SETTINGS (prod and dev) for the user's config folder, or
$DRAGON_WARRIOR_SETTINGS if that is set; a path for that file; or None to keep nothing (test_config, the benchmark and
the frame recorder, which must never read or write the player's own settings).
"""
import json
import os
from collections.abc import Callable
from dataclasses import asdict, dataclass, fields, replace
from os.path import dirname, join
from typing import Any

from src.display_filters import SCALING_MODES, SCALING_SMOOTH
from src.paths import user_config_dir
from src.view import VIEW_NES, VIEWS

SETTINGS_FILE_NAME = 'settings.json'
SETTINGS_ENV_VAR = 'DRAGON_WARRIOR_SETTINGS'
USER_SETTINGS = 'user'  # SETTINGS_PATH: the file in the user's config folder (or $DRAGON_WARRIOR_SETTINGS)
FORMAT_VERSION = 1

LANGUAGES = ('English', 'Korean')
GAME_SPEEDS = (1, 2, 4, 8, 16)  # src/waiting.py SPEED_KEYS' values
MAX_ZOOM = 64  # anything bigger is a corrupt file, not a monitor


@dataclass(frozen=True, slots=True)
class Settings:
    zoom: int | None = None  # None: the window's normal size (NES_RES * SCALE)
    fullscreen: bool = False
    game_speed: int = 1
    language: str | None = None  # None: from the system locale
    scanlines: bool = False
    scaling: str = SCALING_SMOOTH  # src/display_filters.py SCALING_MODES
    view: str = VIEW_NES  # the VIEW row: src/view.py VIEWS
    dungeon_map: bool = True  # the DUNGEON MAP row: whether M shows the dungeon map (src/dungeon_map.py)

    def to_json(self) -> dict[str, Any]:
        return {'version': FORMAT_VERSION, **asdict(self)}

    @classmethod
    def from_json(cls, data: Any) -> 'Settings':
        """The settings in ``data`` (a parsed file). Each one that is missing or makes no sense is the default, so one
        bad value doesn't lose the others."""
        if not isinstance(data, dict):
            return cls()
        default = cls()
        values: dict[str, Any] = {}
        zoom = data.get('zoom')
        values['zoom'] = zoom if type(zoom) is int and 1 <= zoom <= MAX_ZOOM else default.zoom
        fullscreen = data.get('fullscreen')
        values['fullscreen'] = fullscreen if isinstance(fullscreen, bool) else default.fullscreen
        speed = data.get('game_speed')
        values['game_speed'] = speed if type(speed) is int and speed in GAME_SPEEDS else default.game_speed
        language = data.get('language')
        values['language'] = language if language in LANGUAGES else default.language
        scanlines = data.get('scanlines')
        values['scanlines'] = scanlines if isinstance(scanlines, bool) else default.scanlines
        scaling = data.get('scaling')
        values['scaling'] = scaling if scaling in SCALING_MODES else default.scaling
        view = data.get('view')
        values['view'] = view if view in VIEWS else default.view
        dungeon_map = data.get('dungeon_map')
        values['dungeon_map'] = dungeon_map if isinstance(dungeon_map, bool) else default.dungeon_map
        return cls(**values)


def default_settings_path() -> str:
    """$DRAGON_WARRIOR_SETTINGS if it is set, otherwise settings.json in the user's config folder."""
    return os.environ.get(SETTINGS_ENV_VAR) or join(user_config_dir(), SETTINGS_FILE_NAME)


def settings_path(config: dict) -> str | None:
    """The settings file the config's SETTINGS_PATH names (see the module docstring), or None to keep none."""
    path = config.get('SETTINGS_PATH')
    if path == USER_SETTINGS:
        return default_settings_path()
    return path or None


def load_settings(path: str | None) -> Settings:
    """The settings in the file, or the defaults if there is no file or it can't be read."""
    if not path:
        return Settings()
    try:
        with open(path, encoding='utf-8') as settings_file:
            data = json.load(settings_file)
    except (OSError, UnicodeDecodeError, ValueError):
        return Settings()
    return Settings.from_json(data)


def save_settings(path: str, settings: Settings) -> bool:
    """Write the settings to the file, making its folder if need be. Written to a temporary file first and then moved
    over the old one, so a crash halfway leaves the old file whole. Returns whether it was written."""
    temporary = f'{path}.tmp'
    try:
        os.makedirs(dirname(path) or '.', exist_ok=True)
        with open(temporary, 'w', encoding='utf-8') as settings_file:
            json.dump(settings.to_json(), settings_file, indent=2)
            settings_file.write('\n')
        os.replace(temporary, path)
    except OSError as error:
        print(f"Could not save the settings to {path}: {error}")
        return False
    return True


class SettingsStore:
    """The settings the game runs with and the file they're kept in (None: kept nowhere, only for this run)."""

    def __init__(self, path: str | None):
        self.path = path
        self.settings = load_settings(path)

    @classmethod
    def from_config(cls, config: dict) -> 'SettingsStore':
        return cls(settings_path(config))

    def update(self, **changes: Any) -> bool:
        """Change some settings (by their Settings field names) and write the file if anything changed. Returns whether
        anything changed."""
        unknown = set(changes) - {field.name for field in fields(Settings)}
        if unknown:
            raise TypeError(f"Unknown settings: {sorted(unknown)}")
        changed = replace(self.settings, **changes)
        if changed == self.settings:
            return False
        self.settings = changed
        if self.path:
            save_settings(self.path, changed)
        return True

    def updater(self, name: str) -> Callable[[Any], None]:
        """A function that sets one setting, for the listeners src/waiting.py and src/zoom.py call."""
        def update(value: Any) -> None:
            self.update(**{name: value})
        return update
