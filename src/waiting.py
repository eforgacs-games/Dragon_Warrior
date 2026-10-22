"""Blocking waits that still let the player close the window.

A plain ``pygame.time.wait`` (or a ``while get_ticks() ...`` loop) doesn't read the event queue, so clicking the
window's X does nothing until the wait is over, and code that clears the queue afterwards throws the ``QUIT`` away.
These helpers only look for a ``QUIT`` event while they wait: every other event stays queued, exactly as it would
during ``time.wait``, so a caller that used to drop them (``event.clear()``) still has to do that itself.

This module imports nothing from ``src``, so any module can use it without an import cycle.
"""
import sys

from pygame import QUIT, display, event, quit as pygame_quit, time

NES_FPS = 60
POLL_INTERVAL_MS = 16  # about one frame: how often the queue is checked for QUIT during a wait


def quit_game() -> None:
    """Close the game: the main loop's ``pygame.quit()``, then exit so the code after a wait doesn't run on a
    closed display."""
    pygame_quit()
    sys.exit()


def quit_if_requested(current_event: event.Event) -> None:
    """For event loops that read the queue themselves: quit if ``current_event`` is the window being closed."""
    if current_event.type == QUIT:
        quit_game()


def check_for_quit() -> None:
    """Quit if the window has been closed. Nothing is taken off the queue: ``event.peek`` only looks (and pumps), so
    other events stay queued, and tests that script ``event.get`` aren't fed this check's calls."""
    if display.get_init() and event.peek(QUIT):
        quit_game()


def wait(milliseconds: float, config: dict | None = None) -> None:
    """Wait ``milliseconds``, quitting the game if the window is closed meanwhile.

    :param config: When given, the wait is skipped if ``config['NO_WAIT']`` is set, the way the game's other waits
        are. Leave it out for a wait that never honored ``NO_WAIT``.
    """
    if config is not None and config.get('NO_WAIT'):
        return
    end = time.get_ticks() + milliseconds
    slept = 0
    while True:
        check_for_quit()
        # Stop at the deadline, or once the slices slept add up to the wait (so a mocked time.wait returns at once)
        remaining = min(end - time.get_ticks(), milliseconds - slept)
        if remaining <= 0:
            return
        slice_ms = max(1, int(min(remaining, POLL_INTERVAL_MS)))
        time.wait(slice_ms)
        slept += slice_ms


def wait_frames(frames: float, config: dict | None = None, fps: float = NES_FPS) -> None:
    """``wait`` for a number of frames (NES frames, 60 per second, unless ``fps`` says otherwise)."""
    wait(frames * 1000 / fps, config)
