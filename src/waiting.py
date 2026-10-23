"""Blocking waits that still let the player close the window.

A plain ``pygame.time.wait`` (or a ``while get_ticks() ...`` loop) doesn't read the event queue, so clicking the
window's X does nothing until the wait is over, and code that clears the queue afterwards throws the ``QUIT`` away.
These helpers only look for a ``QUIT`` event while they wait: every other event stays queued, exactly as it would
during ``time.wait``, so a caller that used to drop them still has to do that itself, with ``clear_events_keeping_quit``
(a plain ``event.clear()`` would throw away a ``QUIT`` that arrives just after the wait).

It also keeps the game speed (keys 1 to 4: 1x, 2x, 4x or 8x, a modern convenience, not NES behavior). At speed N the
game runs N times as fast: ``wait`` waits 1/N of the time, and ``game_ticks`` (the clock every timer in the game
reads) runs N times as fast as ``pygame.time.get_ticks``. Only timing changes: nothing that decides an outcome reads
the speed. Sounds and music play at their normal pitch and length, so a timed wait that lets a sound finish (the death
music) is shortened too, and the sound just carries on over whatever comes next. The music clips the NES waits for
with WaitForMusicEnd (the victory and level-up fanfares, the inn, the harp, ...) are waited for until they end
(MusicPlayer.wait_for_music_end).

The window zoom keys (Ctrl +, Ctrl -, Ctrl 0 and Ctrl with the mouse wheel, src/zoom.py) are taken out of the event loops
the same way, so they also work everywhere.

It is also where a virtual joypad (src/virtual_joypad.py, which auto-grind drives) plugs into the game's input: every
read of the keys goes through here or calls ``poll_virtual_joypad`` / ``with_virtual_keys`` first, so the joypad can
post its button presses and report its held keys from inside whichever loop is reading input (see those two).

This module imports nothing from ``src`` but src/zoom.py (which imports nothing from ``src``), so any module can use it
without an import cycle.
"""
import sys

from collections.abc import Collection
from typing import Any, Protocol

from pygame import K_1, K_2, K_3, K_4, KEYDOWN, QUIT, display, event, key, quit as pygame_quit, time

from src.zoom import handle_zoom_event

NES_FPS = 60
POLL_INTERVAL_MS = 16  # about one frame: how often the queue is checked for QUIT during a wait
SPEED_KEYS = {K_1: 1, K_2: 2, K_3: 4, K_4: 8}  # the speed each key sets: 1x, 2x, 4x, 8x

_speed = 1
# game_ticks() == _game_anchor + (get_ticks() - _real_anchor) * _speed, re-anchored on every speed change, so the game
# clock never jumps: it only starts running faster or slower from that moment on.
_real_anchor = 0
_game_anchor = 0
_rounding_carry = 0.0  # real milliseconds that rounding waits to whole milliseconds has left over (see _whole_real_ms)

# Who is reading input when the virtual joypad is polled: the map loop (Game.read_events and the hero's walking) or
# anything else (a dialog, a battle, a window or a wait)
MAP_CONTEXT = 'map'
WINDOW_CONTEXT = 'window'


class VirtualJoypadHook(Protocol):
    """What this module needs of a virtual joypad (src/virtual_joypad.py VirtualJoypad)."""
    held: set[int]

    def poll(self, context: str) -> None: ...


_virtual_joypad: VirtualJoypadHook | None = None  # the connected virtual joypad, if one is driving the game


def set_virtual_joypad(joypad: VirtualJoypadHook | None) -> None:
    """Connect a virtual joypad (or None to disconnect it). Only a connected one is polled, so there is nothing to do
    on any input read while none is."""
    global _virtual_joypad
    _virtual_joypad = joypad


def virtual_joypad() -> VirtualJoypadHook | None:
    return _virtual_joypad


def poll_virtual_joypad(context: str = WINDOW_CONTEXT) -> None:
    """Let the connected virtual joypad post the presses that are due on the game clock, and look at the keys the
    player pressed, before the caller reads the event queue. ``context`` says who is reading."""
    if _virtual_joypad is not None:
        _virtual_joypad.poll(context)


class _WithVirtualKeys:
    """``key.get_pressed()``, with the virtual joypad's held keys down as well."""

    def __init__(self, real: Any, held: frozenset[int]) -> None:
        self.real = real
        self.held = held

    def __getitem__(self, pressed_key: int) -> bool:
        return pressed_key in self.held or bool(self.real[pressed_key])


def with_virtual_keys(real: Any, context: str = WINDOW_CONTEXT) -> Any:
    """``real`` (what ``key.get_pressed()`` returned) with the connected virtual joypad's held keys added, after
    polling it. Without a virtual joypad, ``real`` itself. The callers still call ``key.get_pressed()`` themselves, so
    the tests that patch it keep working."""
    if _virtual_joypad is None:
        return real
    _virtual_joypad.poll(context)
    joypad = _virtual_joypad
    if joypad is None or not joypad.held:
        return real
    return _WithVirtualKeys(real, frozenset(joypad.held))


def game_speed() -> int:
    """The current game speed: 1 (normal), 2, 4 or 8 (eight times as fast)."""
    return _speed


def game_ticks() -> int:
    """Milliseconds of game time: ``pygame.time.get_ticks``, but running N times as fast at speed N. Every timer that
    measures how long something has been on screen (blinking, dialog pacing, NPC steps, effects) reads this, so they
    all speed up together. At speed 1, from the start, it is exactly ``get_ticks``."""
    return int(_game_anchor + (time.get_ticks() - _real_anchor) * _speed)


def set_game_speed(speed: int) -> bool:
    """Set the game speed (a factor: 1, 2, 4 or 8). Returns whether it changed."""
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
    global _speed, _real_anchor, _game_anchor, _rounding_carry
    _speed, _real_anchor, _game_anchor, _rounding_carry = 1, 0, 0, 0.0


def _whole_real_ms(real_milliseconds: float) -> int:
    """Round to the whole milliseconds pygame can sleep, carrying the rounding error over to the next call. At 8x a
    frame is 2.08 ms and a fade step 0.625 ms, so rounding each one on its own would make a battle about 20% too slow
    (or too fast); with the carry, many short waits add up to the right total (0.625 ms: 1, 0, 1, 1, 0, ...)."""
    global _rounding_carry
    exact = real_milliseconds + _rounding_carry
    whole = max(0, round(exact))
    _rounding_carry = exact - whole
    return whole


def scaled_ms(milliseconds: float) -> int:
    """How many real milliseconds ``milliseconds`` of game time take at the current speed, for the few places that
    call ``pygame.time`` directly. Rounded with a carry (``_whole_real_ms``), so a short one may be 0."""
    if milliseconds <= 0:
        return 0
    return _whole_real_ms(milliseconds / _speed)


def handle_speed_key(current_event: event.Event) -> bool:
    """If ``current_event`` is a press of 1 to 4, set the game speed and return True."""
    if current_event.type == KEYDOWN and getattr(current_event, 'key', None) in SPEED_KEYS:
        set_game_speed(SPEED_KEYS[current_event.key])
        return True
    return False


def get_events(*args, **kwargs) -> list[event.Event]:
    """``pygame.event.get`` for the game's own event loops (battle, dialogs, menus, shops): presses of 1 to 4 set the
    game speed, and the zoom keys zoom the window (src/zoom.py); both are taken out, so they work everywhere and never
    count as "any key" to close a dialog."""
    poll_virtual_joypad()
    return [current_event for current_event in event.get(*args, **kwargs)
            if not handle_speed_key(current_event) and not handle_zoom_event(current_event)]


def poll_speed_keys() -> None:
    """Set the game speed while one of the keys 1 to 4 is held. Reads the key state, not the queue, so nothing is taken off
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


def clear_events_keeping_quit() -> None:
    """``event.clear()`` for the waits that drop whatever was pressed meanwhile, without dropping a window close: quit
    if one is queued, then clear the rest. ``event.peek`` reads the OS's new events into the queue (pumps) and the
    clear doesn't, so a ``QUIT`` that arrives after the check stays queued for the next loop instead of being thrown
    away with the keys."""
    if event.peek(QUIT):
        quit_game()
    event.clear(pump=False)


def check_for_quit() -> None:
    """Quit if the window has been closed, and change the game speed if 1 to 4 is held. Nothing is taken off the
    queue: ``event.peek`` only looks (and pumps), so other events stay queued, and tests that script ``event.get``
    aren't fed this check's calls."""
    if display.get_init():
        if event.peek(QUIT):
            quit_game()
        poll_speed_keys()
        poll_virtual_joypad()


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
        real_slice = min(remaining / speed, POLL_INTERVAL_MS)
        slice_ms = _whole_real_ms(real_slice)  # what rounding leaves over is carried to the next slice or wait
        if slice_ms:
            time.wait(slice_ms)
        slept += real_slice * speed


def wait_until(deadline: float, config: dict | None = None) -> None:
    """``wait`` until the game clock reaches ``deadline`` (a ``game_ticks`` value). Taking the deadline before drawing
    and waiting until it after, a frame lasts one frame however long the drawing took."""
    wait(max(0.0, deadline - game_ticks()), config)


def wait_frames(frames: float, config: dict | None = None, fps: float = NES_FPS) -> None:
    """``wait`` for a number of frames (NES frames, 60 per second, unless ``fps`` says otherwise)."""
    wait(frames * 1000 / fps, config)


class FramePacer:
    """How many frames the map loop runs before it draws the map again (Game.run_due_frames).

    The map counts frames, as the NES does: a step takes 16 of them, and so does each NPC turn (src/npc_schedule.py).
    Running one frame per draw at 60 * N FPS only keeps up with the game clock (``game_ticks``, which the dialogs,
    effects and blinking read) while drawing a frame takes under 1/(60 N) of a second, about 2 ms at 8x; and
    ``Clock.tick`` rounds the frame time down to whole milliseconds (16 ms, 62.5 FPS, at 1x). So the map runs the frames
    the game clock has gone through since it last drew: N frames for every 1/60 of a real second, however long a draw
    takes. Every frame still runs, in order, so steps and NPC turns are exactly as many frames as before; only the
    drawing of some of them is skipped when drawing is slow."""

    def __init__(self, max_frames: int, stall_ms: int = 100):
        """
        :param max_frames: The most frames run between two draws. The frames past that are dropped: the game slows
            down rather than jump ahead.
        :param stall_ms: A gap longer than this between two draws (real milliseconds) is something that took over
            the screen in the middle of a frame, a battle, a dialog, a menu or a map change, not slow drawing: the
            frames the game clock went through meanwhile aren't made up for, just the next one runs.
        """
        self.max_frames = max_frames
        self.stall_ms = stall_ms
        self._last_frame: int | None = None
        self._last_real = 0

    def frames_due(self) -> int:
        """How many frames to run now, before the next draw (0 if the last draw came before a frame was due)."""
        frame = game_ticks() * NES_FPS // 1000
        real = time.get_ticks()
        if self._last_frame is None or self.stalled(real):
            due = 1
        else:
            due = max(0, min(frame - self._last_frame, self.max_frames))
        self._last_frame, self._last_real = frame, real
        return due

    def stalled(self, now: int | None = None) -> bool:
        """Whether more than ``stall_ms`` real milliseconds have gone by since ``frames_due``."""
        return (time.get_ticks() if now is None else now) - self._last_real > self.stall_ms


def is_any_key_held(keys: Collection[int]) -> bool:
    """Whether one of ``keys`` is down right now, for the NES waits that read JoypadBtns as it is (so a button held
    since before the wait counts) rather than waiting for a new press."""
    pressed = with_virtual_keys(key.get_pressed())
    return any(pressed[pressed_key] for pressed_key in keys)
