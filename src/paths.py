"""
Where the game finds its files, run from source or from a PyInstaller build (see dragon_warrior.spec and
.github/workflows/release.yml).

From source, everything is relative to the repository: data/ for the game's files and src/saves/ for the saves.
A PyInstaller build unpacks data/ next to the code in sys._MEIPASS, which may be read-only (Program Files, a macOS .app)
and, for a one-file build, is deleted when the game exits. So a build keeps its saves in a per-user data folder instead.
"""
import os
import sys
from collections.abc import Mapping
from os.path import dirname, join, realpath

APP_NAME = 'Dragon Warrior'


def is_frozen() -> bool:
    """Whether the game runs from a PyInstaller build rather than from source."""
    return bool(getattr(sys, 'frozen', False))


def project_root() -> str:
    """The folder that holds data/ (and src/): the repository from source, sys._MEIPASS in a PyInstaller build."""
    if is_frozen():
        bundle_dir = getattr(sys, '_MEIPASS', None)
        return bundle_dir or dirname(realpath(sys.executable))
    return dirname(dirname(realpath(__file__)))


def data_path(*parts: str) -> str:
    """A path under data/, e.g. data_path('fonts', 'unifont.ttf')."""
    return join(project_root(), 'data', *parts)


def user_data_dir(platform: str | None = None, environ: Mapping[str, str] | None = None) -> str:
    """
    The per-user folder for the game's own files, as platformdirs' user_data_dir would give it:
    - Windows: %APPDATA%\\Dragon Warrior
    - macOS: ~/Library/Application Support/Dragon Warrior
    - elsewhere: $XDG_DATA_HOME/dragon-warrior, by default ~/.local/share/dragon-warrior
    """
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    if platform.startswith('win'):
        base = environ.get('APPDATA') or join(os.path.expanduser('~'), 'AppData', 'Roaming')
        return join(base, APP_NAME)
    if platform == 'darwin':
        return join(os.path.expanduser('~'), 'Library', 'Application Support', APP_NAME)
    # The XDG spec says to ignore a relative XDG_DATA_HOME
    xdg_data_home = environ.get('XDG_DATA_HOME', '')
    if not os.path.isabs(xdg_data_home):
        xdg_data_home = join(os.path.expanduser('~'), '.local', 'share')
    return join(xdg_data_home, 'dragon-warrior')


def default_save_dir() -> str:
    """Where the adventure logs go unless the config's SAVE_DIR says otherwise: src/saves/ from source, the per-user
    data folder in a build."""
    if is_frozen():
        return join(user_data_dir(), 'saves')
    return join(project_root(), 'src', 'saves')
