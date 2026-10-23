"""
Measure the frame time of fixed scenes, headless, so performance work has numbers to compare (#241, #315).

    uv run python -m tools.benchmark                          # every scene at 1x and 8x, a Markdown table
    uv run python -m tools.benchmark --json before.json       # also save the results
    uv run python -m tools.benchmark --compare before.json after.json
    uv run python -m tools.benchmark --scenes brecconary,battle --speeds 8 --profile 15

Each scene starts from the throne_room checkpoint (data/checkpoints/), moved to the scene's map, with prod_config
(music and sound off, SDL's dummy video and audio drivers) and a fixed random seed. The main loop is the game's own
(Game.main), timed in two parts: the game logic (Game.run_due_frames, the map frames due) and the drawing
(Drawer.draw_all and display.flip). The scene's button presses are posted on the game clock (tools/scripted_input.py),
and it ends after its last step, or after --frames frames of game time for the scenes without steps.

Per scene and game speed it reports:
- the logic and draw times of a pass (mean / median / p95 / max, in ms). A pass that took longer than OWN_LOOP_MS ran
  a loop of its own (a battle, a dialog, a menu, a map change) and is counted under "Own loops" instead;
- Map FPS, the map frames run per real second, and Shown FPS, the frames presented per real second (at most one per
  frame of game time), each with its share of 60 x the speed;
- wall and CPU time (time.process_time): a CPU share near 100% while the game only waits is a busy loop;
- how many times display.flip and display.update were called.
"""
import argparse
import cProfile
import inspect
import os
import platform
import pstats
import random
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, UTC
from collections.abc import Callable, Iterator
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame  # noqa: E402 (the SDL drivers are chosen before pygame starts)

from src.checkpoints import read_checkpoint  # noqa: E402
from src.config.prod_config import prod_config  # noqa: E402
from src.waiting import NES_FPS, game_ticks, reset_game_speed, set_game_speed  # noqa: E402
from tools.benchmark_results import NOT_AVAILABLE, SceneResult, TimeStats, format_comparison, format_report, \
    results_from_json, results_to_json  # noqa: E402
from tools.scripted_input import SceneOver, ScriptedInput, parse_script  # noqa: E402

DEFAULT_FRAMES = 600  # frames of game time for a scene without steps: 10 s at 1x
DEFAULT_SPEEDS = (1, 8)
STEP_GAP = 30  # frames between two steps of a scene's script
# A pass longer than this ran a loop of its own: the same line FramePacer draws between slow drawing and a stall
OWN_LOOP_MS = 100
MAX_SCENE_SECONDS = 120


@dataclass(frozen=True)
class Scene:
    """Where a scene starts and what is pressed in it.

    :param map_name: The map to start on, with the hero at ``position`` (row, column), or the map's own start if None.
    :param script: The steps to press (tools/scripted_input.py). With none, the scene runs for --frames frames.
    :param tail: Frames to keep measuring after the last step.
    :param config: Changes to prod_config for this scene.
    """
    name: str
    description: str
    map_name: str
    position: tuple[int, int] | None = None
    script: str = ''
    tail: int = 0
    config: dict = field(default_factory=dict)


NO_FIGHTS = {'NO_BATTLES': True}
SCENES = (
    Scene('throne_room', "Tantegel throne room, standing", 'TantegelThroneRoom'),
    Scene('courtyard', "Tantegel courtyard, standing (NPCs walking)", 'TantegelCourtyard'),
    Scene('brecconary', "Brecconary, standing", 'Brecconary'),
    Scene('cantlin', "Cantlin, standing", 'Cantlin'),
    Scene('overworld', "Alefgard, walking left and right, no fights", 'Alefgard', (50, 47),
          script='left:64,right:64,left:64,right:64,left:64,right:64', config=NO_FIGHTS),
    Scene('battle', "A Slime fight on Alefgard: a step into it, then its first turns (A every 32 frames)",
          'Alefgard', (50, 47), script='left,wait:120,a*10', tail=60, config={'FORCE_BATTLE': True, 'FORCE_ENEMY': 'Slime'}),
    Scene('command_window', "Open and close the COMMAND window three times", 'TantegelThroneRoom',
          script='wait:30,a,wait:60,b,wait:60,a,wait:60,b,wait:60,a,wait:60,b', tail=60),
    Scene('dialog_wait', "King Lorik's greeting, then its ▼ wait for a button", 'TantegelThroneRoom',
          script='wait:30,a', tail=300, config={'INITIAL_DIALOG_ENABLED': True}),
    Scene('map_change', "Down the throne room stairs: fade out, load the courtyard, fade in", 'TantegelThroneRoom',
          (14, 17), script='wait:30,right', tail=300, config={'AUTO_STAIRS': True}),
)
SCENES_BY_NAME = {scene.name: scene for scene in SCENES}


@dataclass
class SceneMeter:
    """What a scene's run measured, as it runs."""
    logic_ms: list[float] = field(default_factory=list)
    draw_ms: list[float] = field(default_factory=list)
    own_loop_ms: list[float] = field(default_factory=list)
    map_frames: int = 0
    shown_frames: int = 0
    flips: int = 0
    updates: int = 0
    last_shown_frame: int | None = None

    def add_pass(self, logic_ms: float, draw_ms: float) -> None:
        if logic_ms + draw_ms > OWN_LOOP_MS:
            self.own_loop_ms.append(logic_ms + draw_ms)
        else:
            self.logic_ms.append(logic_ms)
            self.draw_ms.append(draw_ms)

    def add_cut_pass(self, elapsed_ms: float) -> None:
        """A pass the end of the scene cut short: only a loop of its own is counted (as far as it got)."""
        if elapsed_ms > OWN_LOOP_MS:
            self.own_loop_ms.append(elapsed_ms)

    def count_present(self) -> None:
        """A display.flip or display.update: it shows a new frame if it's the first in this frame of game time."""
        frame = game_ticks() * NES_FPS // 1000
        if frame != self.last_shown_frame:
            self.shown_frames += 1
            self.last_shown_frame = frame

    def result(self, scene: Scene, speed: int, wall_seconds: float, cpu_seconds: float) -> SceneResult:
        frame_ms = [logic + draw for logic, draw in zip(self.logic_ms, self.draw_ms)]
        return SceneResult(scene=scene.name, speed=speed, passes=len(frame_ms), logic_ms=TimeStats.of(self.logic_ms),
                           draw_ms=TimeStats.of(self.draw_ms), frame_ms=TimeStats.of(frame_ms),
                           own_loop_passes=len(self.own_loop_ms), own_loop_seconds=sum(self.own_loop_ms) / 1000,
                           map_frames=self.map_frames, shown_frames=self.shown_frames, wall_seconds=wall_seconds,
                           cpu_seconds=cpu_seconds, flips=self.flips, updates=self.updates)


# The driver: the few calls into the game. Older commits had other signatures (see the fallbacks), which is all a
# comparison with them needs.

def run_logic(game) -> None:
    """The game logic of one pass of the main loop: the map frames due (Game.run_due_frames), or before frame pacing
    (#337) the single frame Game.get_events ran."""
    if hasattr(game, 'run_due_frames'):
        game.run_due_frames()
    else:
        game.get_events()


def draw(game, animate: bool) -> None:
    """Drawer.draw_all for the main loop: draw_all(game, animate), or before #354 its 15 arguments."""
    if 'game' in inspect.signature(game.drawer.draw_all).parameters:
        game.drawer.draw_all(game, animate)
        return
    game.drawer.draw_all(game.screen, game.loop_count, game.big_map, game.current_map, game.player, game.cmd_menu,
                         game.foreground_rects, animate, game.camera, game.initial_dialog_enabled, game.events,
                         game.skip_text, game.story_flags.left_throne_room, game.game_state, game.color)


def sprites_animate(game) -> bool:
    """MovementController.sprites_animate, or before #354 Game.sprites_animate."""
    if hasattr(getattr(game, 'movement', None), 'sprites_animate'):
        return game.movement.sprites_animate
    return game.sprites_animate


def map_frame_method(game) -> str:
    """The method that runs exactly one map frame."""
    return 'map_frame' if hasattr(game, 'map_frame') else 'get_events'


def scene_config(scene: Scene, save_dir: str) -> dict:
    return {**prod_config, 'MUSIC_ENABLED': False, 'SOUND_ENABLED': False, 'SPLASH_SCREEN_ENABLED': False,
            'INITIAL_DIALOG_ENABLED': False, 'SAVE_DIR': save_dir, **scene.config}


def scene_save(scene: Scene) -> dict:
    """The throne_room checkpoint, moved to the scene's map (load_game starts at the map's own start for no row)."""
    save = read_checkpoint('throne_room')
    row, column = scene.position or (None, None)
    save.update(CurrentMap=scene.map_name, PlayerRow=row, PlayerColumn=column)
    return save


def start_game(scene: Scene, save_dir: str):
    from src.game import Game
    # Without SCALED, which can't always make its renderer headless (as tools/record_frames.py)
    with patch('src.game.SCALED', 0):
        game = Game(scene_config(scene, save_dir))
    game.load_game(scene_save(scene))
    return game


@contextmanager
def measured(game, meter: SceneMeter) -> Iterator[None]:
    """Count display.flip, display.update and the map frames while the scene runs."""
    real_flip, real_update = pygame.display.flip, pygame.display.update
    method = map_frame_method(game)
    real_map_frame = getattr(game, method)

    def flip():
        meter.flips += 1
        meter.count_present()
        return real_flip()

    def update(*args, **kwargs):
        meter.updates += 1
        meter.count_present()
        return real_update(*args, **kwargs)

    def map_frame(*args, **kwargs):
        meter.map_frames += 1
        return real_map_frame(*args, **kwargs)

    with patch.object(pygame.display, 'flip', flip), patch.object(pygame.display, 'update', update), \
            patch.object(game, method, map_frame):
        yield


def main_loop(game, meter: SceneMeter, scripted: ScriptedInput) -> None:
    """Game.main's loop, timed. Runs until the script raises SceneOver, which can come in the middle of a pass (in a
    battle, say): that pass counts as a loop of its own if it was already long enough to be one."""
    draw(game, game.game_state.enable_animate)
    pygame.display.flip()
    while True:
        game.clock.tick(game.fps)
        scripted.poll()
        started = time.perf_counter()
        try:
            run_logic(game)
            logic_done = time.perf_counter()
            draw(game, sprites_animate(game))
            pygame.display.flip()
        except SceneOver:
            meter.add_cut_pass((time.perf_counter() - started) * 1000)
            raise
        drawn = time.perf_counter()
        game.loop_count += 1
        meter.add_pass((logic_done - started) * 1000, (drawn - logic_done) * 1000)


def scene_length(scene: Scene, frames: int) -> tuple[list, int]:
    """The scene's key presses, and the frame of game time it ends on."""
    presses, script_end = parse_script(scene.script, STEP_GAP)
    return presses, script_end + scene.tail if scene.script else frames


def run_scene(scene: Scene, speed: int, frames: int, seed: int,
              profiler: cProfile.Profile | None = None) -> SceneResult:
    """Play the scene at the game speed and measure it. A scene the game can't run (an older commit) is n/a."""
    random.seed(seed)
    reset_game_speed()
    meter = SceneMeter()
    try:
        with tempfile.TemporaryDirectory(prefix='dragon_warrior_benchmark_') as save_dir:
            game = start_game(scene, save_dir)
            set_game_speed(speed)
            wall_seconds, cpu_seconds = play(game, scene, frames, meter, profiler)
    except (Exception, SystemExit) as error:
        return SceneResult(scene=scene.name, speed=speed, status=f'{NOT_AVAILABLE}: {type(error).__name__}: {error}')
    finally:
        reset_game_speed()
    return meter.result(scene, speed, wall_seconds, cpu_seconds)


def play(game, scene: Scene, frames: int, meter: SceneMeter, profiler: cProfile.Profile | None) -> tuple[float, float]:
    """Run the main loop with the scene's presses until the scene is over. Returns the real and CPU seconds it took."""
    presses, end_frame = scene_length(scene, frames)
    scripted = ScriptedInput(presses, end_frame, MAX_SCENE_SECONDS)
    wall_start, cpu_start = time.perf_counter(), time.process_time()
    with ExitStack() as stack:
        stack.enter_context(measured(game, meter))
        for current_patch in scripted.install():
            stack.callback(current_patch.stop)
        if profiler:
            profiler.enable()
            stack.callback(profiler.disable)
        try:
            main_loop(game, meter, scripted)
        except SceneOver:
            pass
    return time.perf_counter() - wall_start, time.process_time() - cpu_start


def run_benchmark(scenes: list[Scene], speeds: list[int], frames: int, seed: int, repeat: int = 1,
                  profile_lines: int = 0,
                  on_result: Callable[[SceneResult], None] = lambda _result: None) -> list[SceneResult]:
    """Each scene at each speed, ``repeat`` times, keeping the best run of each (see best_run)."""
    results = []
    for scene in scenes:
        for speed in speeds:
            profiler = cProfile.Profile() if profile_lines else None
            result = best_run([run_scene(scene, speed, frames, seed, profiler) for _ in range(repeat)])
            results.append(result)
            on_result(result)
            if profiler:
                print_profile(profiler, f'{scene.name} at {speed}x', profile_lines)
    return results


def best_run(runs: list[SceneResult]) -> SceneResult:
    """The run with the shortest mean frame time: what else ran on the machine only ever makes a run slower."""
    return min(runs, key=lambda run: (not run.ran, run.frame_ms.mean))


def print_profile(profiler: cProfile.Profile, title: str, lines: int) -> None:
    print(f'\ncProfile, {title}, by own time:')
    pstats.Stats(profiler, stream=sys.stdout).sort_stats('tottime').print_stats(lines)


def git_commit() -> str:
    try:
        return subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return 'unknown'


def run_metadata(args) -> dict:
    return {'commit': git_commit(), 'date': datetime.now(UTC).isoformat(timespec='seconds'),
            'python': platform.python_version(), 'pygame': pygame.version.ver, 'machine': platform.machine(),
            'processor': platform.processor() or platform.machine(), 'frames': args.frames, 'seed': args.seed,
            'repeat': args.repeat}


def parse_names(text: str) -> list[Scene]:
    names = [name.strip() for name in text.split(',') if name.strip()]
    unknown = [name for name in names if name not in SCENES_BY_NAME]
    if unknown:
        raise argparse.ArgumentTypeError(f"Unknown scene(s) {', '.join(unknown)}. Scenes: {', '.join(SCENES_BY_NAME)}")
    return [SCENES_BY_NAME[name] for name in names]


def parse_speeds(text: str) -> list[int]:
    speeds = [int(speed) for speed in text.split(',') if speed.strip()]
    if not speeds or any(speed not in (1, 2, 4, 8) for speed in speeds):
        raise argparse.ArgumentTypeError("Speeds are 1, 2, 4 or 8, e.g. 1,8")
    return speeds


def make_parser() -> argparse.ArgumentParser:
    scene_list = '\n'.join(f'  {scene.name}: {scene.description}' for scene in SCENES)
    parser = argparse.ArgumentParser(prog='python -m tools.benchmark', description=__doc__,
                                     epilog=f'Scenes:\n{scene_list}',
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--scenes', type=parse_names, default=list(SCENES),
                        help="comma-separated scene names (default: all of them)")
    parser.add_argument('--speeds', type=parse_speeds, default=list(DEFAULT_SPEEDS),
                        help="comma-separated game speeds (default: 1,8)")
    parser.add_argument('--frames', type=int, default=DEFAULT_FRAMES,
                        help=f"frames of game time for the scenes without steps (default {DEFAULT_FRAMES})")
    parser.add_argument('--seed', type=int, default=0, help="random seed (default 0)")
    parser.add_argument('--repeat', type=int, default=1,
                        help="run each scene this many times and keep the run with the shortest mean frame time")
    parser.add_argument('--json', metavar='OUT', help="also write the results to this JSON file")
    parser.add_argument('--profile', type=int, metavar='LINES', default=0,
                        help="run each scene under cProfile and print its LINES slowest functions by own time")
    parser.add_argument('--compare', nargs=2, metavar=('BEFORE', 'AFTER'),
                        help="print a table comparing two --json files, and run nothing")
    return parser


def compare_files(before_path: str, after_path: str) -> str:
    with open(before_path) as before_file, open(after_path) as after_file:
        before, before_metadata = results_from_json(before_file.read())
        after, after_metadata = results_from_json(after_file.read())
    title = f"Before: {before_metadata.get('commit', before_path)}, after: {after_metadata.get('commit', after_path)}"
    return f'{title}\n\n{format_comparison(before, after)}'


def print_progress(result: SceneResult) -> None:
    print(f'{result.scene} at {result.speed}x: {result.status}', file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    if args.compare:
        print(compare_files(*args.compare))
        return 0
    try:
        results = run_benchmark(args.scenes, args.speeds, args.frames, args.seed, args.repeat, args.profile,
                                print_progress)
    finally:
        pygame.quit()
    print(format_report(results))
    if args.json:
        with open(args.json, 'w') as json_file:
            json_file.write(results_to_json(results, run_metadata(args)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
