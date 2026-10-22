"""Blocking waits that still let the player close the window.

A plain ``pygame.time.wait`` (or a ``while get_ticks() ...`` loop) doesn't read the event queue, so clicking the
window's X does nothing until the wait is over, and code that clears the queue afterwards throws the ``QUIT`` away.
These helpers only look for a ``QUIT`` event while they wait: every other event stays queued, exactly as it would
during ``time.wait``, so a caller that used to drop them (``event.clear()``) still has to do that itself.

It also keeps the game speed (keys 1 to 4, a modern convenience, not NES behavior). At speed N the game runs N times
as fast: ``wait`` waits 1/N of the time, and ``game_ticks`` (the clock every timer in the game reads) runs N times as
fast as ``pygame.time.get_ticks``. Only timing changes: nothing that decides an outcome reads the speed. Sounds and music
play at their normal pitch and length, so a wait that lets a sound finish (the death music, the level-up fanfare) is
shortened too, and the sound just carries on over whatever comes next.

This module imports nothing from ``src``, so any module can use it without an import cycle.
"""
import sys

from pygame import K_1, K_2, K_3, K_4, KEYDOWN, QUIT, display, event, key, quit as pygame_quit, time

NES_FPS = 60
POLL_INTERVAL_MS = 16  # about one frame: how often the queue is checked for QUIT during a wait
SPEED_KEYS = {K_1: 1, K_2: 2, K_3: 3, K_4: 4}  # the speed each key sets: 1x to 4x

_speed = 1
# game_ticks() == _game_anchor + (get_ticks() - _real_anchor) * _speed, re-anchored on every speed change, so the game
# clock never jumps: it only starts running faster or slower from that moment on.
_real_anchor = 0
_game_anchor = 0


def game_speed() -> int:
    """The current game speed: 1 (normal) to 4 (four times as fast)."""
    return _speed


def game_ticks() -> int:
    """Milliseconds of game time: ``pygame.time.get_ticks``, but running N times as fast at speed N. Every timer that
    measures how long something has been on screen (blinking, dialog pacing, NPC steps, effects) reads this, so they
    all speed up together. At speed 1, from the start, it is exactly ``get_ticks``."""
    return int(_game_anchor + (time.get_ticks() - _real_anchor) * _speed)


def set_game_speed(speed: int) -> bool:
    """Set the game speed (1 to 4). Returns whether it changed."""
    global _speed, _real_anchor, _game_anchor
    if speed == _speed:
        return False
    now = time.get_ticks()
    _game_anchor = game_ticks()
    _real_anchor = now
    _speed = speed
    return True


def reset_game_speed() -> None:
    """Back to speed 1 with ``game_ticks() == get_ticks()`` (a new game, or a test): the game clock may jump."""
    global _speed, _real_anchor, _game_anchor
    _speed, _real_anchor, _game_anchor = 1, 0, 0


def scaled_ms(milliseconds: float) -> int:
    """How many real milliseconds ``milliseconds`` of game time take at the current speed (at least 1 if positive),
    for the few places that call ``pygame.time`` directly."""
    if milliseconds <= 0:
        return 0
    return max(1, round(milliseconds / _speed))


def handle_speed_key(current_event: event.Event) -> bool:
    """If ``current_event`` is a press of 1 to 4, set the game speed and return True."""
    if current_event.type == KEYDOWN and getattr(current_event, 'key', None) in SPEED_KEYS:
        set_game_speed(SPEED_KEYS[current_event.key])
        return True
    return False


def get_events(*args, **kwargs) -> list[event.Event]:
    """``pygame.event.get`` for the game's own event loops (battle, dialogs, menus, shops): presses of 1 to 4 set the
    game speed and are taken out, so they work everywhere and never count as "any key" to close a dialog."""
    return [current_event for current_event in event.get(*args, **kwargs) if not handle_speed_key(current_event)]


def poll_speed_keys() -> None:
    """Set the game speed from 1 to 4 while it's held. Reads the key state, not the queue, so nothing is taken off
    it: used during waits, which leave the queue alone."""
    pressed = key.get_pressed()
    for speed_key, speed in SPEED_KEYS.items():
        if pressed[speed_key]:
            set_game_speed(speed)
            return


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
    """Quit if the window has been closed, and change the game speed if 1 to 4 is held. Nothing is taken off the
    queue: ``event.peek`` only looks (and pumps), so other events stay queued, and tests that script ``event.get``
    aren't fed this check's calls."""
    if display.get_init():
        if event.peek(QUIT):
            quit_game()
        poll_speed_keys()


def wait(milliseconds: float, config: dict | None = None) -> None:
    """Wait ``milliseconds`` of game time (``milliseconds / N`` at speed N), quitting the game if the window is closed
    meanwhile. A speed change during the wait applies to the rest of it.

    :param config: When given, the wait is skipped if ``config['NO_WAIT']`` is set, the way the game's other waits
        are. Leave it out for a wait that never honored ``NO_WAIT``.
    """
    if config is not None and config.get('NO_WAIT'):
        return
    end = game_ticks() + milliseconds
    slept = 0.0  # game milliseconds the slices slept add up to
    while True:
        check_for_quit()
        # Stop at the deadline, or once the slices slept add up to the wait (so a mocked time.wait returns at once)
        remaining = min(end - game_ticks(), milliseconds - slept)
        if remaining <= 0:
            return
        speed = _speed
        slice_ms = max(1, int(min(remaining / speed, POLL_INTERVAL_MS)))
        time.wait(slice_ms)
        slept += slice_ms * speed


def wait_frames(frames: float, config: dict | None = None, fps: float = NES_FPS) -> None:
    """``wait`` for a number of frames (NES frames, 60 per second, unless ``fps`` says otherwise)."""
    wait(frames * 1000 / fps, config)
