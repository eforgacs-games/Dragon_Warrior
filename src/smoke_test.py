"""
`python src/game.py --smoke-test` (or `DragonWarrior --smoke-test` in a build, with `--language Korean` for the Korean
game): checks that the game finds and can load all of its files and that the emulated soundtracks (the NES's and the
SFC's, through libgme: src/chiptune.py) render every track, then plays a few hundred frames of it with scripted
button presses (SMOKE_SCENES) and exits with 0, or with 1 if anything is missing, doesn't load or raises. The release
workflow runs it on every build, headless (SDL_VIDEODRIVER and SDL_AUDIODRIVER set to dummy), to prove the build
bundles everything it needs: the fonts (the NES font for English, Unifont for Korean), the images, map tiles, music,
sounds, the libgme library and the translations a player meets in the first minutes. The scenes each play with
another soundtrack, so the music streams in the game with each.

The scenes are played through the virtual joypad (src/virtual_joypad.py, which auto-grind drives), so every loop of
the game (the map, a dialog, the COMMAND window, a battle) reads the presses as it reads the player's keys, in a build
as from source, with nothing patched.
"""
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pygame import K_DOWN, K_LEFT, K_RIGHT, K_UP, K_i, K_j, K_k, K_u, font, image, mixer
from pygame.event import Event

from src.catalog import compile_po, po_path
from src.checkpoints import CHECKPOINT_NAMES, checkpoint_hero_name, checkpoint_path, read_checkpoint
from src.chiptune import (ChiptuneError, Emulator, bundled_library_dirs, chiptune_library, parse_track_ref,
                          tagged_length_seconds)
from src.directories import CHIPTUNE_SOUNDTRACKS, CLIP_NAMES, MUSIC_NAMES, Directories, clip_paths, music_paths
from src.options_screen import AUTO_STAIRS_SAVE_KEY
from src.paths import data_path, is_frozen
from src.soundtrack import SOUNDTRACK_KEY, SOUNDTRACK_SAVE_KEY, SOUNDTRACKS, Soundtrack
from src.virtual_joypad import VirtualJoypad
from src.waiting import MAP_CONTEXT, reset_game_speed, set_game_speed

IMAGE_EXTENSIONS = ('.png', '.gif')
SOUND_EXTENSIONS = ('.mp3', '.wav')
FONT_EXTENSIONS = ('.ttf', '.otf')
# How much of each chiptune track check_chiptune_tracks renders: long enough to be past the silence a track can start
# with (the NES's end music has almost a second of it)
CHIPTUNE_CHECK_SECONDS = 2
CHIPTUNE_CHECK_SAMPLE_RATE = 44100
# A line the Korean catalog translates, to check it loaded
KOREAN_CHECK_LINE = "Thou art a fool!"


def game_file_paths(config: dict) -> set[str]:
    """Every file under data/ that Directories names, with every soundtrack (NES, SFC and orchestra), and Unifont's
    license."""
    paths: set[str] = set()
    data_dir = data_path()
    for chosen in SOUNDTRACKS:
        directories = Directories({**config, SOUNDTRACK_KEY: chosen})
        values = list(vars(directories).values()) + list(directories.item_menu_background_lookup.values()) + \
            [getattr(directories, name) for name in MUSIC_NAMES + CLIP_NAMES]
        paths.update(file_path(value) for value in values if isinstance(value, str) and value.startswith(data_dir)
                     and os.path.splitext(file_path(value))[1])
    paths.update(checkpoint_path(name) for name in CHECKPOINT_NAMES)
    # Unifont's license (SIL OFL 1.1) has to ship with the font
    paths.add(data_path('fonts', 'OFL-unifont.txt'))
    sparkle_dir = data_path('images', 'intro_banner', 'sparkle')
    if os.path.isdir(sparkle_dir):
        paths.update(os.path.join(sparkle_dir, name) for name in os.listdir(sparkle_dir))
    return paths


def file_path(path_or_track: str) -> str:
    """The file a path or a chiptune track reference ('...nsf#14') names."""
    track = parse_track_ref(path_or_track)
    return track.path if track else path_or_track


def chiptune_tracks() -> list[str]:
    """Every chiptune track the game plays, of every emulated soundtrack."""
    tracks = {value for chosen in CHIPTUNE_SOUNDTRACKS
              for value in (*music_paths(chosen).values(), *clip_paths(chosen).values())}
    return sorted(track for track in tracks if parse_track_ref(track))


def untagged_clips() -> list[str]:
    """The chiptune tracks the game plays once (the clips and the ending) whose length can't be read: the NSF's
    playlist (.m3u) is missing or doesn't tag one, or an SPC's ID666 tag has none."""
    played_once = {value for chosen in CHIPTUNE_SOUNDTRACKS
                   for value in (*clip_paths(chosen).values(), music_paths(chosen)['ending_music'])}
    return [f'{track} has no tagged length' for track in sorted(played_once)
            if parse_track_ref(track) and tagged_length_seconds(track) is None]


def check_chiptune_tracks() -> list[str]:
    """Loads libgme and renders the first seconds of every chiptune track; returns what failed (libgme missing, a
    track that doesn't load, or one that renders only silence)."""
    library = chiptune_library()
    problems = untagged_clips()
    if library is None:
        return ["libgme isn't bundled or installed: the NES and SFC soundtracks can't play", *problems]
    if is_frozen() and os.path.dirname(library.path) not in bundled_library_dirs():
        problems.append(f"libgme isn't bundled: the build loaded {library.path}")
    frame_count = CHIPTUNE_CHECK_SECONDS * CHIPTUNE_CHECK_SAMPLE_RATE
    for ref in chiptune_tracks():
        track = parse_track_ref(ref)
        assert track is not None
        try:
            emulator = Emulator(library, track, CHIPTUNE_CHECK_SAMPLE_RATE)
            try:
                rendered = emulator.render(frame_count)
            finally:
                emulator.close()
        except (ChiptuneError, OSError) as error:
            problems.append(f"can't play {ref}: {error}")
            continue
        if not any(rendered):
            problems.append(f'{ref} renders only silence')
    return problems


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
            elif extension in FONT_EXTENSIONS:
                font.Font(path, 16).render('Ag', False, (255, 255, 255))
            elif extension == '.json':
                with open(path) as json_file:
                    json.load(json_file)
        except Exception as error:  # every failure is reported, not just the first
            problems.append(f"can't load {path}: {error}")
    problems.extend(check_chiptune_tracks())
    problems.extend(check_korean_translations())
    return problems


def check_korean_translations() -> list[str]:
    """Compiles the bundled Korean .po (as the game does when Korean is chosen) and translates a line with it. Not
    through load_translations' cache, so it checks the files of the build that's running."""
    try:
        translations = compile_po(po_path('ko'))
    except (OSError, ValueError) as error:
        return [f"can't load the Korean translations: {error}"]
    translated = translations.gettext(KOREAN_CHECK_LINE)
    if translated == KOREAN_CHECK_LINE:
        return [f"the Korean translations don't translate {KOREAN_CHECK_LINE!r}"]
    return []


def check_game_language(game: Any) -> list[str]:
    """The running game translates its text into the language it was started in (only Korean has a catalog)."""
    if game.config['LANGUAGE'] == 'Korean' and game._(KOREAN_CHECK_LINE) == KOREAN_CHECK_LINE:
        return [f"the game started in Korean doesn't translate {KOREAN_CHECK_LINE!r}"]
    return []


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


# Playing the game

BUTTON_KEYS = {'a': K_k, 'b': K_j, 'start': K_i, 'select': K_u,
               'up': K_UP, 'down': K_DOWN, 'left': K_LEFT, 'right': K_RIGHT}
DIRECTIONS = ('up', 'down', 'left', 'right')
BUTTON_HOLD_FRAMES = 2
STEP_FRAMES = 16  # a direction is held for one step unless the script says otherwise
STEP_GAP = 20  # frames between one step of a script and the next
SMOKE_SPEED = 8 # the game speed (keys 1 to 5) the scenes are played at, to keep the test short
SCENE_MAX_SECONDS = 60  # real time: a scene that runs longer is stuck (a wait that never ends)


class SceneOver(Exception):
    """Raised from inside whichever loop of the game is reading input, once a scene's script has been played."""


@dataclass
class SceneLog:
    """What happened while a scene ran."""
    maps: list[str] = field(default_factory=list)
    fights: list[Any] = field(default_factory=list)  # the src/battle.py Battle of each fight
    window_polls: int = 0  # reads of input by a dialog, a window or a battle rather than the map loop

    def saw_map(self, identifier: str) -> None:
        if not self.maps or self.maps[-1] != identifier:
            self.maps.append(identifier)


@dataclass(frozen=True)
class SmokeScene:
    """A short scripted scene.

    :param script: Comma-separated steps: a button (``a``, ``b``, ``start``, ``select`` or a direction, a direction
        being held for one step), a button held for N frames (``right:48``, three steps), or ``wait:N`` (N frames).
        Each press is followed by STEP_GAP frames.
    :param save_changes: Changes to the throne_room checkpoint's save, e.g. to start somewhere else.
    :param config: Changes to the game's config for this scene.
    :param check: Returns what went wrong in the scene, given the game and what was seen while it ran (None: nothing
        to check but that it ran).
    """
    name: str
    script: str
    save_changes: dict = field(default_factory=dict)
    config: dict = field(default_factory=dict)
    check: Callable[[Any, SceneLog], list[str]] | None = None


def parse_smoke_script(script: str) -> tuple[list[tuple[int, int, int]], int]:
    """The script's presses as (frame, key, frames held), and the frame the script ends on."""
    presses = []
    frame = 0
    for step in (step.strip().lower() for step in script.split(',')):
        if not step:
            continue
        name, _, argument = step.partition(':')
        if name == 'wait':
            frame += int(argument)
            continue
        if name not in BUTTON_KEYS:
            raise ValueError(f"Unknown smoke test step {step!r}")
        hold = int(argument) if argument else STEP_FRAMES if name in DIRECTIONS else BUTTON_HOLD_FRAMES
        presses.append((frame, BUTTON_KEYS[name], hold))
        frame += hold + STEP_GAP
    return presses, frame


class ScriptDriver:
    """Drives the virtual joypad (a src/virtual_joypad.py JoypadDriver) through a scene's script, keeps a SceneLog,
    and raises SceneOver once the script is over (or TimeoutError when the scene runs too long in real time)."""

    def __init__(self, game: Any, script: str, log: SceneLog, max_seconds: float = SCENE_MAX_SECONDS) -> None:
        self.game = game
        self.presses, self.end_frame = parse_smoke_script(script)
        self.log = log
        self.max_seconds = max_seconds
        self.deadline = time.monotonic() + max_seconds

    def update(self, joypad: VirtualJoypad, context: str) -> None:
        self.log.saw_map(self.game.current_map.identifier)
        battle = self.game.cmd_menu.current_battle
        if battle is not None and battle not in self.log.fights:
            self.log.fights.append(battle)
        if context != MAP_CONTEXT:
            self.log.window_polls += 1
        while self.presses and self.presses[0][0] <= joypad.now:
            _frame, pressed_key, hold = self.presses.pop(0)
            joypad.tap(pressed_key, hold)
        if not self.presses and joypad.now >= self.end_frame:
            raise SceneOver
        if time.monotonic() > self.deadline:
            raise TimeoutError(f"the scene was still running after {self.max_seconds} s (at frame {joypad.now} of "
                               f"{self.end_frame})")

    def real_key(self, _current_event: Event) -> bool:
        return True


def expect_maps(*identifiers: str) -> Callable[[Any, SceneLog], list[str]]:
    """A scene check: the hero was on each of these maps."""
    def check(_game: Any, log: SceneLog) -> list[str]:
        missed = [identifier for identifier in identifiers if identifier not in log.maps]
        return [f"never reached {', '.join(missed)} (maps seen: {', '.join(log.maps)})"] if missed else []
    return check


def expect_window(_game: Any, log: SceneLog) -> list[str]:
    """A scene check: a window or dialog was open and read the presses."""
    return [] if log.window_polls else ["no window or dialog opened"]


def expect_fight(_game: Any, log: SceneLog) -> list[str]:
    """A scene check: a fight started."""
    return [] if log.fights else ["no fight started"]


# The config every scene starts from, before its own changes: no random fights, fast text
SCENE_CONFIG = {'INITIAL_DIALOG_ENABLED': False, 'NO_BATTLES': True, 'FORCE_BATTLE': False, 'FORCE_ENEMY': None,
                'TEXT_SPEED': 'Fast'}
# The adventure log options every scene's save has, before its own changes: STAIRS on stepping. They're the log's, so
# loading the save sets them (src/options_screen.py); a save without them loads with the NES's.
SCENE_SAVE_OPTIONS = {AUTO_STAIRS_SAVE_KEY: True}
SMOKE_SCENES = (
    # A step down to the guard below, TALK to him (a dialog, in the NES font or Unifont), then the COMMAND window
    # opened and closed
    SmokeScene('throne_room', 'wait:20,down,down,wait:30,a,wait:40,a,wait:120,a,wait:60,a,wait:40,b,wait:30',
               save_changes={SOUNDTRACK_SAVE_KEY: Soundtrack.NES.value}, check=expect_window),
    # Right, three steps, onto the throne room's stairs and down to the courtyard (a fade, a new map, its tiles, NPCs
    # and music), then on into the courtyard. The direction is held well past the three steps, as a player would: a
    # loaded machine runs fewer map frames per frame of game time, and the steps take longer.
    SmokeScene('stairs', 'wait:20,right:150,wait:60',
               save_changes={'PlayerRow': 14, 'PlayerColumn': 15, SOUNDTRACK_SAVE_KEY: Soundtrack.SFC.value},
               check=expect_maps('TantegelThroneRoom', 'TantegelCourtyard')),
    # Walking left on Alefgard into a Slime fight (the battle window, the enemy, battle music and sounds), then FIGHT.
    # Held for several steps: after a map change the first step may not roll for a fight (Game.handle_battles compares
    # the steps taken since the change with the count at the last roll). Left in the battle's command window keeps
    # FIGHT chosen.
    SmokeScene('overworld_fight', 'wait:20,left:100,wait:120,a,wait:10,a,wait:120,a,wait:10,a,wait:120',
               save_changes={'CurrentMap': 'Alefgard', 'PlayerRow': 50, 'PlayerColumn': 47,
                             SOUNDTRACK_SAVE_KEY: Soundtrack.ORCHESTRA.value},
               config={'NO_BATTLES': False, 'FORCE_BATTLE': True, 'FORCE_ENEMY': 'Slime'},
               check=expect_fight),
)


def play_scene(game: Any, scene: SmokeScene, max_seconds: float = SCENE_MAX_SECONDS) -> list[str]:
    """Load the scene's start into the game and play its script in Game.main's loop. Returns what went wrong; an
    exception from the game is raised."""
    game.config.update({**SCENE_CONFIG, **scene.config})
    save = {**read_checkpoint('throne_room'), **SCENE_SAVE_OPTIONS, **scene.save_changes}
    save['Name'] = checkpoint_hero_name(save['Name'], game.config['LANGUAGE'])  # 검객 in Korean
    game.load_game(save)
    game.initial_dialog_enabled = bool(game.config.get('INITIAL_DIALOG_ENABLED'))
    log = SceneLog()
    joypad = VirtualJoypad(ScriptDriver(game, scene.script, log, max_seconds))
    joypad.connect()
    try:
        game.main()
    except SceneOver:  # the script is over: the scene ran to its end
        problems = scene.check(game, log) if scene.check else []
        return [f'{scene.name}: {problem}' for problem in problems]
    finally:
        joypad.disconnect()
    return [f"{scene.name}: the game left its main loop before the scene was over"]


def play_smoke_scenes(game: Any, scenes: tuple[SmokeScene, ...] = SMOKE_SCENES) -> list[str]:
    """Play each scene in turn in the same game, at SMOKE_SPEED. Returns what went wrong; an exception from the game
    is raised."""
    problems = check_game_language(game)
    set_game_speed(SMOKE_SPEED)
    try:
        for scene in scenes:
            problems.extend(play_scene(game, scene))
    finally:
        reset_game_speed()
    return problems
