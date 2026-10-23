"""Blocking waits that still let the player close the window.

A plain ``pygame.time.wait`` (or a ``while get_ticks() ...`` loop) doesn't read the event queue, so clicking the
window's X does nothing until the wait is over, and code that clears the queue afterwards throws the ``QUIT`` away.
These helpers only look for a ``QUIT`` event while they wait: every other event stays queued, exactly as it would
during ``time.wait``, so a caller that used to drop them still has to do that itself, with ``clear_events_keeping_quit``
(a plain ``event.clear()`` would throw away a ``QUIT`` that arrives just after the wait).

It also keeps the game speed (keys 1 to 5: 1x, 2x, 4x, 8x or 16x, a modern convenience, not NES behavior). At speed N the
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
post its button presses and report its held keys from inside whichever loop is reading input (see those two). A
gamepad (src/gamepad.py) plugs in at the same two places, polled just before the virtual joypad, so its presses reach
the game, and auto-grind, as the player's own key presses.

This module imports nothing from ``src`` but src/zoom.py (which imports nothing from ``src``), so any module can use it
without an import cycle.

The selection windows don't speed up (#440): their cursor (src/cursor.py: the blink, the held button's retrigger, the
"let go first" of a button held as a window opens) and their loops (src/selection.py next_frame) run on the menu
clock, ``menu_ticks``, which keeps 1x time whatever the game speed, so a held direction doesn't race past the entries
and a press held a moment too long isn't read twice at 8x. With the MENU SPEED option (MENU_SPEED, src/options_overlay.py)
on FOLLOW GAME SPEED it runs at the game speed as it used to, and so it does while a virtual joypad (auto-grind)
drives the game, whose presses are timed on the game clock.
"""
import sys

from collections.abc import Callable, Collection, Iterator, Mapping
from time import perf_counter, sleep
from typing import Any, Protocol, override

from pygame import KEYDOWN, QUIT, display, event, key, quit as pygame_quit, time

from src.controls import SPEED_ACTIONS, action_keys, actions_for_event
from src.zoom import handle_zoom_event

# The NTSC NES's frame rate, 60.0988 Hz: the PPU draws 341 x 262 dots a frame, one fewer every other frame (89,341.5 on
# average), at a quarter of the 236.25 / 11 MHz master clock. Every timing in the game is a number of these frames
# (frame_at, frames_to_ms), and the main loop is paced at this rate times the game speed (FrameClock).
NES_FPS = 236.25e6 / 11 / 4 / 89341.5
POLL_INTERVAL_MS = 16  # about one frame: how often the queue is checked for QUIT during a wait


class _SpeedKeys(Mapping[int, int]):
    """The speed each speed key sets, as the keys are bound now (src/controls.py): by default 1 to 5 set 1x, 2x, 4x, 8x
    and 16x."""

    def _keys(self) -> dict[int, int]:
        return {speed_key: speed for name, speed in SPEED_ACTIONS.items() for speed_key in action_keys(name)}

    @override
    def __getitem__(self, speed_key: int) -> int:
        return self._keys()[speed_key]

    @override
    def __iter__(self) -> Iterator[int]:
        return iter(self._keys())

    @override
    def __len__(self) -> int:
        return len(self._keys())


SPEED_KEYS: Mapping[int, int] = _SpeedKeys()
GAME_SPEEDS = tuple(SPEED_ACTIONS.values())

_speed = 1
# game_ticks() == _game_anchor + (get_ticks() - _real_anchor) * _speed, re-anchored on every speed change, so the game
# clock never jumps: it only starts running faster or slower from that moment on.
_real_anchor = 0
_game_anchor = 0
_rounding_carry = 0.0  # real milliseconds that rounding waits to whole milliseconds has left over (see _whole_real_ms)
# Told the new speed after each change by set_game_speed (not reset_game_speed): the game saves it with the global
# settings (src/settings.py)
_speed_listener: Callable[[int], None] | None = None
# The options overlay's GAME SPEED switch (GAME_SPEED_KEYS, src/options_screen.py SWITCHES): off, keys 1 to 5 do nothing
# (they are still taken out of the event loops, so they never count as "any key"). Game.apply_option sets it.
_speed_keys_enabled = True

# The MENU SPEED option (config['MENU_SPEED']): NORMAL keeps the selection windows at 1x; FOLLOW GAME SPEED runs them at
# the game speed (see the module docstring)
MENU_SPEED_NORMAL = 'Normal'
MENU_SPEED_FOLLOW = 'FollowGameSpeed'
MENU_SPEEDS = (MENU_SPEED_NORMAL, MENU_SPEED_FOLLOW)
_menu_speed_config: dict | None = None  # the config whose MENU_SPEED says how fast the menus run (follow_menu_speed_option)
# menu_ticks() == _menu_anchor + (get_ticks() - _menu_real_anchor) * _menu_rate, re-anchored whenever the rate changes
_menu_real_anchor = 0
_menu_anchor = 0
_menu_rate = 1

# Who is reading input when the virtual joypad is polled: the map loop (Game.read_events and the hero's walking) or
# anything else (a dialog, a battle, a window or a wait)
MAP_CONTEXT = 'map'
WINDOW_CONTEXT = 'window'


class VirtualJoypadHook(Protocol):
    """What this module needs of a virtual joypad (src/virtual_joypad.py VirtualJoypad)."""
    held: set[int]

    def poll(self, context: str) -> None: ...


_virtual_joypad: VirtualJoypadHook | None = None  # the connected virtual joypad, if one is driving the game


class GamepadHook(Protocol):
    """What this module needs of a gamepad (src/gamepad.py Gamepad)."""
    held: set[int]

    def poll(self) -> None: ...


_gamepad: GamepadHook | None = None  # the player's gamepad, if the game has connected one (src/gamepad.py)


def set_gamepad(gamepad: GamepadHook | None) -> None:
    """Connect the player's gamepad (or None to disconnect it): it is polled on every read of input, before the
    virtual joypad, so the keys it presses look like the player's to auto-grind."""
    global _gamepad
    _gamepad = gamepad


def gamepad() -> GamepadHook | None:
    return _gamepad


def set_virtual_joypad(joypad: VirtualJoypadHook | None) -> None:
    """Connect a virtual joypad (or None to disconnect it). Only a connected one is polled, so there is nothing to do
    on any input read while none is."""
    global _virtual_joypad
    _virtual_joypad = joypad
    _sync_menu_clock()  # the menus follow the game speed while it drives (menu_speed)


def virtual_joypad() -> VirtualJoypadHook | None:
    return _virtual_joypad


def poll_virtual_joypad(context: str = WINDOW_CONTEXT) -> None:
    """Let the connected virtual joypad post the presses that are due on the game clock, and look at the keys the
    player pressed, before the caller reads the event queue. ``context`` says who is reading. The gamepad, if one is
    connected, posts its presses first, so the virtual joypad sees them as the player's."""
    if _gamepad is not None:
        _gamepad.poll()
    if _virtual_joypad is not None:
        _virtual_joypad.poll(context)


class _WithVirtualKeys:
    """``key.get_pressed()``, with the gamepad's and the virtual joypad's held keys down as well."""

    def __init__(self, real: Any, held: frozenset[int]) -> None:
        self.real = real
        self.held = held

    def __getitem__(self, pressed_key: int) -> bool:
        return pressed_key in self.held or bool(self.real[pressed_key])


def with_virtual_keys(real: Any, context: str = WINDOW_CONTEXT) -> Any:
    """``real`` (what ``key.get_pressed()`` returned) with the keys the gamepad and the connected virtual joypad hold
    added, after polling them. With neither holding a key, ``real`` itself. The callers still call
    ``key.get_pressed()`` themselves, so the tests that patch it keep working."""
    if _gamepad is None and _virtual_joypad is None:
        return real
    poll_virtual_joypad(context)
    held: set[int] = set()
    if _gamepad is not None:
        held |= _gamepad.held
    if _virtual_joypad is not None:
        held |= _virtual_joypad.held
    if not held:
        return real
    return _WithVirtualKeys(real, frozenset(held))


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
    _sync_menu_clock(now)
    if _speed_listener is not None:
        _speed_listener(speed)
    return True


def set_speed_listener(listener: Callable[[int], None] | None) -> None:
    """Call ``listener`` with the new speed after every change set_game_speed makes (None: no one is told)."""
    global _speed_listener
    _speed_listener = listener


def set_speed_keys_enabled(enabled: bool) -> None:
    """Switch keys 1 to 5 on or off (GAME_SPEED_KEYS). Switching them off also goes back to normal speed, which isn't
    saved: the global settings keep the speed chosen with the keys, for when they're on again."""
    global _speed_keys_enabled, _speed_listener
    _speed_keys_enabled = enabled
    if not enabled:
        listener, _speed_listener = _speed_listener, None
        try:
            set_game_speed(1)
        finally:
            _speed_listener = listener


def speed_keys_enabled() -> bool:
    return _speed_keys_enabled


def reset_game_speed() -> None:
    """Back to speed 1 with ``game_ticks() == get_ticks()`` (a new game, or a test): the game clock may jump. So may
    the menu clock, which is back to ``get_ticks()`` too. The speed keys are switched back on; a new Game then sets
    them from its config."""
    global _speed, _real_anchor, _game_anchor, _rounding_carry, _menu_real_anchor, _menu_anchor, _menu_rate, \
        _speed_keys_enabled
    _speed, _real_anchor, _game_anchor, _rounding_carry = 1, 0, 0, 0.0
    _menu_real_anchor, _menu_anchor, _menu_rate = 0, 0, 1
    _speed_keys_enabled = True


def follow_menu_speed_option(config: dict | None) -> None:
    """Read the MENU SPEED option from ``config['MENU_SPEED']`` from now on (Game.__init__), whenever it changes; None:
    the menus keep 1x time (NORMAL)."""
    global _menu_speed_config
    _menu_speed_config = config
    _sync_menu_clock()


def menu_speed() -> int:
    """How many times as fast as 1x the selection windows run: 1 (MENU SPEED NORMAL), or the game speed with FOLLOW GAME
    SPEED or while a virtual joypad drives the game."""
    if _virtual_joypad is not None or (
            _menu_speed_config is not None and _menu_speed_config.get('MENU_SPEED') == MENU_SPEED_FOLLOW):
        return _speed
    return 1


def _sync_menu_clock(now: int | None = None) -> None:
    """Re-anchor the menu clock if its rate (menu_speed) has changed, so it never jumps: it only runs faster or slower
    from then on. A change of the option is seen at the next read of the clock, at most a frame later."""
    global _menu_real_anchor, _menu_anchor, _menu_rate
    rate = menu_speed()
    if rate == _menu_rate:
        return
    now = time.get_ticks() if now is None else now
    _menu_anchor += (now - _menu_real_anchor) * _menu_rate
    _menu_real_anchor = now
    _menu_rate = rate


def menu_ticks() -> int:
    """Milliseconds of menu time, the clock of the selection windows' cursor (src/cursor.py): ``pygame.time.get_ticks``,
    running ``menu_speed()`` times as fast. At speed 1, from the start, it is exactly ``get_ticks`` (and
    ``game_ticks``)."""
    now = time.get_ticks()
    _sync_menu_clock(now)
    return int(_menu_anchor + (now - _menu_real_anchor) * _menu_rate)


def menu_frame_in_game_frames() -> int:
    """How many NES frames of game time one frame of menu time lasts: the game speed over the menu speed (1 at 1x,
    8 at 8x with MENU SPEED NORMAL, 1 with FOLLOW GAME SPEED)."""
    return max(1, _speed // menu_speed())


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
    """If ``current_event`` is a press of a speed key (1 to 5, or the NEXT SPEED key if one is bound), set the game
    speed (if the keys are on: the GAME SPEED switch) and return True."""
    if current_event.type != KEYDOWN:
        return False
    for name in actions_for_event(current_event):
        if name in SPEED_ACTIONS:
            if _speed_keys_enabled:
                set_game_speed(SPEED_ACTIONS[name])
            return True
        if name == 'NEXT_SPEED':
            if _speed_keys_enabled:
                set_game_speed(next_game_speed())
            return True
    return False


def next_game_speed() -> int:
    """The game speed after the current one, back to 1x after the fastest."""
    later = [speed for speed in GAME_SPEEDS if speed > _speed]
    return later[0] if later else GAME_SPEEDS[0]


def get_events(*args, **kwargs) -> list[event.Event]:
    """``pygame.event.get`` for the game's own event loops (battle, dialogs, menus, shops): presses of 1 to 5 set the
    game speed, and the zoom keys zoom the window (src/zoom.py); both are taken out, so they work everywhere and never
    count as "any key" to close a dialog."""
    poll_virtual_joypad()
    return [current_event for current_event in event.get(*args, **kwargs)
            if not handle_speed_key(current_event) and not handle_zoom_event(current_event)]


def poll_speed_keys() -> None:
    """Set the game speed while one of the keys 1 to 5 is held. Reads the key state, not the queue, so nothing is taken off
    it: used during waits, which leave the queue alone."""
    if not _speed_keys_enabled:
        return
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
    """Quit if the window has been closed, and change the game speed if 1 to 5 is held. Nothing is taken off the
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


def frame_at(milliseconds: float) -> int:
    """The NES frame, counted from 0, that a time in milliseconds (a ``game_ticks`` value, or a time since something
    started) falls in."""
    return int(milliseconds * NES_FPS // 1000)


def frames_to_ms(frames: float) -> float:
    """How many milliseconds a number of NES frames last."""
    return frames * 1000 / NES_FPS


def wait_frames(frames: float, config: dict | None = None, fps: float = NES_FPS) -> None:
    """``wait`` for a number of frames (NES frames, NES_FPS a second, unless ``fps`` says otherwise)."""
    wait(frames * 1000 / fps, config)


class FramePacer:
    """How many frames the map loop runs before it draws the map again (Game.run_due_frames).

    The map counts frames, as the NES does: a step takes 16 of them, and so does each NPC turn (src/npc_schedule.py).
    Running one frame per draw at NES_FPS * N only keeps up with the game clock (``game_ticks``, which the dialogs,
    effects and blinking read) while drawing a frame takes under 1/(NES_FPS N) of a second, about 2 ms at 8x. So the
    map runs the frames the game clock has gone through since it last drew: N frames for every 1/NES_FPS of a real
    second, however long a draw takes. Every frame still runs, in order, so steps and NPC turns are exactly as many
    frames as before; only the drawing of some of them is skipped when drawing is slow."""

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
        frame = frame_at(game_ticks())
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


class FrameClock:
    """Paces the main loop (Game.main): each pass waits until a new NES frame has begun on the game clock, so the map
    is drawn once for each frame FramePacer runs, NES_FPS times a second at normal speed (N times that at speed N).

    ``pygame.time.Clock.tick`` can't do that: it takes whole milliseconds, so ``tick(60)`` waited 16 ms, about 62.5
    passes a second, and one pass in about 25 had no new frame to show. Here the frame boundaries come from the game
    clock itself, so the passes keep in step with the frames however long each sleep or draw really takes, and never
    drift from them. A pass that comes after its frame has already begun (slow drawing, or a loop of its own such as a
    battle) doesn't wait at all, and the passes it missed aren't run one after another: FramePacer runs the map frames
    they would have."""

    def __init__(self, sleep: Callable[[float], None] = sleep, now: Callable[[], float] = perf_counter):
        """
        :param sleep: Sleeps a number of seconds (``time.sleep``).
        :param now: Real seconds (``time.perf_counter``): a wait never lasts more than two frames of real time, even if
            the game clock stands still (as tests can make it).
        """
        self.sleep = sleep
        self.now = now
        self._last_frame: int | None = None

    def tick(self) -> None:
        """Wait until a frame begins that the last pass didn't start in, unless one already has."""
        frame = frame_at(game_ticks())
        if self._last_frame is not None and frame <= self._last_frame:
            next_frame = self._last_frame + 1
            give_up = self.now() + 2 / (NES_FPS * _speed)
            while frame < next_frame and self.now() < give_up:
                # game milliseconds until the frame begins, in real seconds; at least a fifth of a millisecond, as the
                # game clock only counts whole milliseconds
                self.sleep(max(frames_to_ms(next_frame) - game_ticks(), 0.2) / _speed / 1000)
                frame = frame_at(game_ticks())
        self._last_frame = frame


def is_any_key_held(keys: Collection[int]) -> bool:
    """Whether one of ``keys`` is down right now, for the NES waits that read JoypadBtns as it is (so a button held
    since before the wait counts) rather than waiting for a new press."""
    pressed = with_virtual_keys(key.get_pressed())
    return any(pressed[pressed_key] for pressed_key in keys)
