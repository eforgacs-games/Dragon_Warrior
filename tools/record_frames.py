"""
Play a scripted scene headless and save every frame the game presents, with a report of what changed and what
flickered (src/frame_recorder.py).

    uv run python -m tools.record_frames --checkpoint throne_room --out /tmp/frames
    uv run python -m tools.record_frames --checkpoint garins_grave --script "a,a,wait:120,b" --out /tmp/frames
    uv run python -m tools.record_frames --title --script "wait:120,start,wait:60,a,..." --out /tmp/frames

The game runs with prod_config (music and sound off, SDL's dummy video and audio drivers) in real time, the way it
runs when played, from a checkpoint (data/checkpoints/, the default is throne_room, where the first button starts
King Lorik's opening speech) or, with --title, from the title screen.

The script's steps (``a``, ``right:48``, ``wait:N``, ``talk``, ``a*5``, ...) are described in tools/scripted_input.py.
Each step is followed by --gap frames (30 by default) before the next. The recording ends --tail frames (120) after
the last step, or after --max-seconds.
"""
import argparse
import os
import random
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame  # noqa: E402 (the SDL drivers are chosen before pygame starts)

from src.checkpoints import CHECKPOINT_NAMES  # noqa: E402
from src.config.prod_config import prod_config  # noqa: E402
from src.frame_recorder import FRAME_RECORDINGS_DIR, REAL_TIME_FLICKER_MS, FrameRecorder, find_flickers, \
    save_recording  # noqa: E402
from src.waiting import set_game_speed  # noqa: E402
from tools.scripted_input import SceneOver, ScriptedInput, parse_script  # noqa: E402


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
    scripted = ScriptedInput(presses, last_frame + args.tail, args.max_seconds,
                             on_step=lambda text: setattr(recorder, 'label', text))
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
