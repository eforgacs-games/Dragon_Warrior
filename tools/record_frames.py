"""
Play a scripted scene headless and save every frame the game presents, with a report of what changed and what
flickered (src/frame_recorder.py).

    uv run python -m tools.record_frames --checkpoint throne_room --out /tmp/frames
    uv run python -m tools.record_frames --checkpoint garins_grave --script "a,a,wait:120,b" --out /tmp/frames
    uv run python -m tools.record_frames --title --script "wait:120,start,wait:60,a,..." --out /tmp/frames

The game runs with prod_config (music and sound off, SDL's dummy video and audio drivers) in real time, the way it
runs when played, from a checkpoint (data/checkpoints/, the default is throne_room, where the first button starts
King Lorik's opening speech) or, with --title, from the title screen.

The script is a comma-separated list of steps, run in order on the game clock (60 frames a second):
- a button: ``a``, ``b``, ``start``, ``select``, ``enter``, ``up``, ``down``, ``left`` or ``right``. A button is
  held for 2 frames, a direction for 16 (one step); ``right:48`` holds it for 48 frames (three steps).
- ``wait:N``: wait N frames.
- ``talk``: open the COMMAND window and choose TALK (``a``, then ``a``).
- ``NAME*N`` repeats a step N times, e.g. ``a*5``.
Each step is followed by --gap frames (30 by default) before the next. The recording ends --tail frames (120) after
the last step, or after --max-seconds.
"""
import argparse
import os
import random
import sys
import tempfile
import time

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame  # noqa: E402 (the SDL drivers are chosen before pygame starts)
from pygame import KEYDOWN, KEYUP, K_DOWN, K_LEFT, K_RETURN, K_RIGHT, K_UP, K_i, K_j, K_k, K_u  # noqa: E402

from src.checkpoints import CHECKPOINT_NAMES  # noqa: E402
from src.config.prod_config import prod_config  # noqa: E402
from src.frame_recorder import FRAME_RECORDINGS_DIR, REAL_TIME_FLICKER_MS, FrameRecorder, find_flickers, \
    save_recording  # noqa: E402
from src.waiting import NES_FPS, game_ticks, set_game_speed  # noqa: E402

BUTTON_KEYS = {'a': K_k, 'b': K_j, 'start': K_i, 'select': K_u, 'enter': K_RETURN,
               'up': K_UP, 'down': K_DOWN, 'left': K_LEFT, 'right': K_RIGHT}
DIRECTIONS = ('up', 'down', 'left', 'right')
BUTTON_HOLD_FRAMES = 2
STEP_FRAMES = 16  # a direction is held for one step unless the script says otherwise
MACROS = {'talk': ['a', 'a']}
# The most game time counted between two reads of input: the game reads it at least once a frame unless it's busy
STALL_MS = 50


class SceneOver(Exception):
    """Raised from inside the game's own loops to end the recording."""


def parse_script(script: str, gap: int) -> tuple[list[tuple[int, int, int, str]], int]:
    """Turn the script into key presses: (frame the key goes down, frame it's let go, key, the step's text), and the
    frame the last step ends on."""
    steps: list[str] = []
    for token in (token.strip().lower() for token in script.split(',')):
        if not token:
            continue
        name, _, count = token.partition('*')
        for _ in range(int(count) if count else 1):
            steps.extend(MACROS.get(name, [name]))
    presses = []
    frame = 0
    for number, step in enumerate(steps, start=1):
        name, _, argument = step.partition(':')
        if name == 'wait':
            frame += int(argument)
            continue
        if name not in BUTTON_KEYS:
            raise ValueError(f"Unknown script step {step!r}. Steps: wait:N, talk, {', '.join(BUTTON_KEYS)}")
        hold = int(argument) if argument else STEP_FRAMES if name in DIRECTIONS else BUTTON_HOLD_FRAMES
        presses.append((frame, frame + hold, BUTTON_KEYS[name], f'step {number}: {step}'))
        frame += hold + gap
    return presses, frame


class HeldKeys:
    """Stands in for ``pygame.key.get_pressed()``: the dummy video driver keeps no key state for posted events."""

    def __init__(self, held: set[int]) -> None:
        self.held = held

    def __getitem__(self, key: int) -> bool:
        return key in self.held


class ScriptedInput:
    """Posts the script's key presses when they're due on the game clock. ``poll`` runs whenever the game reads input
    or presents a frame, so the presses land in whichever loop of the game is running then."""

    def __init__(self, presses: list[tuple[int, int, int, str]], end_frame: int, recorder: FrameRecorder,
                 max_seconds: float) -> None:
        self.recorder = recorder
        self.end_frame = end_frame
        self.deadline = time.monotonic() + max_seconds
        self.held: set[int] = set()
        # (frame, is key down, key, text), in time order
        self.timeline = sorted([(down, True, key, text) for down, _up, key, text in presses] +
                               [(up, False, key, text) for _down, up, key, text in presses], key=lambda item: item[0])
        self.elapsed_ms = 0
        self.last_ticks: int | None = None

    def frame_now(self) -> int:
        """Frames of game time since the scene started, leaving out the time the game was busy without reading input
        (loading a map), so a step lands as long after the one before as the script says."""
        now = game_ticks()
        if self.last_ticks is not None:
            self.elapsed_ms += min(now - self.last_ticks, STALL_MS)
        self.last_ticks = now
        return self.elapsed_ms * NES_FPS // 1000

    def poll(self) -> None:
        now = self.frame_now()
        while self.timeline and self.timeline[0][0] <= now:
            _frame, down, key, text = self.timeline.pop(0)
            if down:
                self.held.add(key)
                self.recorder.label = text
            else:
                self.held.discard(key)
            pygame.event.post(pygame.event.Event(KEYDOWN if down else KEYUP, key=key, mod=0, scancode=0,
                                                 unicode=pygame.key.name(key) if len(pygame.key.name(key)) == 1 else ''))
        if (not self.timeline and now >= self.end_frame) or time.monotonic() > self.deadline:
            raise SceneOver

    def install(self) -> list:
        """Hook the game's input reads. Returns the patches, to stop."""
        from unittest.mock import patch
        real = {name: getattr(pygame.event, name) for name in ('get', 'peek', 'poll', 'wait')}

        def polled(function):
            def read(*args, **kwargs):
                self.poll()
                return function(*args, **kwargs)
            return read
        patches = [patch.object(pygame.event, name, polled(function)) for name, function in real.items()]
        patches.append(patch('src.game.get', polled(real['get'])))
        patches.append(patch.object(pygame.key, 'get_pressed', lambda: HeldKeys(self.held)))
        for current_patch in patches:
            current_patch.start()
        return patches


def make_config(args) -> dict:
    config = {**prod_config, 'MUSIC_ENABLED': False, 'SOUND_ENABLED': False}
    if args.title:
        # The title screen lists the save slots: use an empty folder, not the real ones in src/saves
        config.update(SPLASH_SCREEN_ENABLED=True, SAVE_DIR=tempfile.mkdtemp(prefix='dragon_warrior_record_'))
    else:
        config.update(SPLASH_SCREEN_ENABLED=False, CHECKPOINT=args.checkpoint)
    return config


def record(args) -> int:
    from unittest.mock import patch

    from src.game import Game
    random.seed(args.seed)
    presses, last_frame = parse_script(args.script, args.gap)
    recorder = FrameRecorder(max_frames=args.max_frames)
    scripted = ScriptedInput(presses, last_frame + args.tail, recorder, args.max_seconds)
    recorder.on_frame = lambda _frame: scripted.poll()
    # Without SCALED, which can't always make its renderer headless. The recorder still takes every display.update as
    # showing the whole screen, as it does on the game's SCALED window.
    with patch('src.game.SCALED', 0):
        game = Game(make_config(args))
    set_game_speed(args.speed)
    patches = scripted.install()
    recorder.start()
    try:
        game.main()
    except SceneOver:
        pass
    finally:
        recorder.stop()
        for current_patch in patches:
            current_patch.stop()
    text = save_recording(recorder, args.out, all_frames=args.all_frames)
    flickers = find_flickers(recorder, max_ms=REAL_TIME_FLICKER_MS)
    print(text.split('\n')[0])
    print(f"Saved the frames and report.txt to {args.out}")
    print(f"{len(flickers)} one-frame flicker(s) on screen for under 2 frames")
    for flicker in flickers:
        print(f"- {flicker.describe()}")
    return 1 if flickers and args.fail_on_flicker else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='python -m tools.record_frames', description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    start = parser.add_mutually_exclusive_group()
    start.add_argument('--checkpoint', choices=CHECKPOINT_NAMES, default='throne_room',
                       help="the checkpoint to start from (default: throne_room)")
    start.add_argument('--title', action='store_true', help="start from the title screen instead of a checkpoint")
    parser.add_argument('--script', default='', help="the steps to play, e.g. \"talk,wait:120,a\" (see above)")
    parser.add_argument('--out', default=os.path.join(FRAME_RECORDINGS_DIR, 'scene'),
                        help=f"where to save the PNGs and report.txt (default {os.path.join(FRAME_RECORDINGS_DIR, 'scene')})")
    parser.add_argument('--gap', type=int, default=30, help="frames between steps (default 30)")
    parser.add_argument('--tail', type=int, default=120, help="frames to keep recording after the last step")
    parser.add_argument('--max-seconds', type=float, default=120, help="stop after this many real seconds")
    parser.add_argument('--max-frames', type=int, default=20000, help="keep at most this many frames")
    parser.add_argument('--seed', type=int, default=0, help="random seed, so encounters and fights repeat (default 0)")
    parser.add_argument('--speed', type=int, choices=(1, 2, 4, 8), default=1, help="game speed (keys 1 to 4)")
    parser.add_argument('--all-frames', action='store_true',
                        help="save a PNG for every frame, not just each frame that changed the picture")
    parser.add_argument('--fail-on-flicker', action='store_true', help="exit with 1 if a one-frame flicker is found")
    args = parser.parse_args(argv)
    try:
        return record(args)
    finally:
        pygame.quit()


if __name__ == '__main__':
    sys.exit(main())
