"""
Scripted button presses for the headless tools (tools/record_frames.py, tools/benchmark.py): a script of steps is
turned into key presses, and ``ScriptedInput`` posts them on the game clock from inside whichever loop of the game is
reading input at the time.

The script is a comma-separated list of steps, run in order on the game clock (60 frames a second):
- a button: ``a``, ``b``, ``start``, ``select``, ``enter``, ``up``, ``down``, ``left`` or ``right``. A button is
  held for 2 frames, a direction for 16 (one step); ``right:48`` holds it for 48 frames (three steps).
- ``wait:N``: wait N frames.
- ``talk``: open the COMMAND window and choose TALK (``a``, then ``a``).
- ``NAME*N`` repeats a step N times, e.g. ``a*5``.
Each step is followed by a gap of frames before the next.
"""
import time
from typing import Callable
from unittest.mock import patch

import pygame
from pygame import KEYDOWN, KEYUP, K_DOWN, K_LEFT, K_RETURN, K_RIGHT, K_UP, K_i, K_j, K_k, K_u

from src.waiting import NES_FPS, game_ticks

BUTTON_KEYS = {'a': K_k, 'b': K_j, 'start': K_i, 'select': K_u, 'enter': K_RETURN,
               'up': K_UP, 'down': K_DOWN, 'left': K_LEFT, 'right': K_RIGHT}
DIRECTIONS = ('up', 'down', 'left', 'right')
BUTTON_HOLD_FRAMES = 2
STEP_FRAMES = 16  # a direction is held for one step unless the script says otherwise
MACROS = {'talk': ['a', 'a']}
# The most game time counted between two reads of input: the game reads it at least once a frame unless it's busy
STALL_MS = 50

# (frame the key goes down, frame it's let go, key, the step's text)
Press = tuple[int, int, int, str]


class SceneOver(Exception):
    """Raised from inside the game's own loops to end the scene."""


def parse_script(script: str, gap: int) -> tuple[list[Press], int]:
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
    (and whenever the caller calls it), so the presses land in whichever loop of the game is running then. Raises
    ``SceneOver`` once the last step and ``end_frame`` have passed, or after ``max_seconds`` of real time.

    :param on_step: Called with the step's text when its key goes down.
    """

    def __init__(self, presses: list[Press], end_frame: int, max_seconds: float,
                 on_step: Callable[[str], None] | None = None) -> None:
        self.on_step = on_step
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
                if self.on_step:
                    self.on_step(text)
            else:
                self.held.discard(key)
            pygame.event.post(pygame.event.Event(KEYDOWN if down else KEYUP, key=key, mod=0, scancode=0,
                                                 unicode=pygame.key.name(key) if len(pygame.key.name(key)) == 1 else ''))
        if (not self.timeline and now >= self.end_frame) or time.monotonic() > self.deadline:
            raise SceneOver

    def install(self) -> list:
        """Hook the game's input reads. Returns the patches, to stop."""
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
