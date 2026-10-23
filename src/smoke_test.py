"""
`python src/game.py --smoke-test` (or `DragonWarrior --smoke-test` in a build): checks that the game finds and can load
all of its files, starts it, draws the first frame of the map and exits. The release workflow runs it on every build,
headless (SDL_VIDEODRIVER and SDL_AUDIODRIVER set to dummy), to prove the build bundles everything it needs.
"""
import gettext
import json
import os

from pygame import image, mixer

from src.checkpoints import CHECKPOINT_NAMES, checkpoint_path
from src.directories import Directories
from src.paths import data_path

IMAGE_EXTENSIONS = ('.png', '.gif')
SOUND_EXTENSIONS = ('.mp3', '.wav')


def game_file_paths(config: dict) -> set[str]:
    """Every file under data/ that Directories names, with both music settings (NES and orchestra)."""
    paths: set[str] = set()
    data_dir = data_path()
    for orchestra in (False, True):
        directories = Directories({**config, 'ORCHESTRA_MUSIC_ENABLED': orchestra})
        values = list(vars(directories).values()) + list(directories.item_menu_background_lookup.values())
        paths.update(value for value in values if isinstance(value, str) and value.startswith(data_dir)
                     and os.path.splitext(value)[1])
    paths.update(checkpoint_path(name) for name in CHECKPOINT_NAMES)
    sparkle_dir = data_path('images', 'intro_banner', 'sparkle')
    if os.path.isdir(sparkle_dir):
        paths.update(os.path.join(sparkle_dir, name) for name in os.listdir(sparkle_dir))
    return paths


def check_game_files(config: dict) -> list[str]:
    """Loads every file the game uses; returns a description of each one that is missing or doesn't load."""
    problems = []
    if not os.path.isdir(data_path('images', 'intro_banner', 'sparkle')):
        problems.append(f"missing: {data_path('images', 'intro_banner', 'sparkle')}")
    for path in sorted(game_file_paths(config)):
        if not os.path.isfile(path):
            problems.append(f'missing: {path}')
            continue
        extension = os.path.splitext(path)[1].lower()
        try:
            if extension in IMAGE_EXTENSIONS:
                image.load(path)
            elif extension in SOUND_EXTENSIONS and mixer.get_init():
                mixer.music.load(path)
            elif extension == '.json':
                with open(path) as json_file:
                    json.load(json_file)
        except Exception as error:  # every failure is reported, not just the first
            problems.append(f"can't load {path}: {error}")
    for language in ('en', 'ko'):
        try:
            gettext.translation('base', localedir=data_path('text', 'locales'), languages=[language])
        except OSError as error:
            problems.append(f"can't load the {language} translations: {error}")
    return problems


def check_save_dir(save_dir: str) -> list[str]:
    """Creates the save folder if needed and checks a file can be written there."""
    try:
        os.makedirs(save_dir, exist_ok=True)
        probe = os.path.join(save_dir, '.smoke_test')
        with open(probe, 'w') as probe_file:
            probe_file.write('ok')
        os.remove(probe)
    except OSError as error:
        return [f"can't write to the save folder {save_dir}: {error}"]
    return []
