"""Gamepad support (#382): a controller as the NES joypad. Not NES (the NES pad is the only input it has).

A controller doesn't get a code path of its own: it presses keyboard keys. Every read of input polls the gamepad
(src/waiting.py ``poll_virtual_joypad`` before the event queue is read, ``with_virtual_keys`` wherever
``key.get_pressed()`` is, the same two hooks auto-grind's virtual joypad uses, src/virtual_joypad.py). Each poll it

- finds the controller to read: the first one plugged in, opened again whenever controllers are plugged in or out
  (``check_devices``, which only compares ``pygame.joystick.get_count()`` when nothing changed, so with no controller
  a poll costs one call);
- reads its state (``PadState``: the buttons down, named the way SDL's GameController API names them, and the left
  stick) and turns it into the keys it stands for (``pad_keys``): each button presses the first key of the action
  it's bound to (src/controls.py: by default A is K, B is J, START is I, SELECT is U, and F1, Shift+F1 and Backspace
  for the save states and rewind), and the D-pad or the stick the first key of one direction at a time;
- posts a KEYDOWN for every key that went down since the last poll and a KEYUP for every one let go, and keeps the
  keys down in ``held``, which ``with_virtual_keys`` adds to the keyboard state.

So every loop (the map, menus, dialogs, battles, name entry, the title screens, the options overlay) reads the
controller exactly as it reads the keyboard, and a press is the player's own: it stops auto-grind as a key does
(AutoGrind.real_key), since the gamepad is polled before the virtual joypad looks at the queue. The events it posts
carry ``GAMEPAD``, so the name entry can tell a button from typing (src/menu_functions.py).

The mapping uses SDL's GameController API (pygame._sdl2.controller), whose database maps the common pads (Xbox,
PlayStation, Switch Pro, Steam Deck, 8BitDo ...) to one layout without setup; a device it doesn't know is read as a
plain joystick (``JOYSTICK_BUTTONS``). The game itself only sees ``Gamepad`` through ``PadBackend`` and ``PadDevice``,
so the tests feed it fake controllers.
"""
import os
from collections.abc import Iterable
from typing import Any, NamedTuple, Protocol

import pygame
from pygame import KEYDOWN, KEYUP, K_DOWN, K_LEFT, K_RIGHT, K_UP

from src import controls
from src.waiting import set_gamepad, step_game_speed

# SDL names the face buttons by where they are on an Xbox pad, whatever the pad's labels say ('a' bottom, 'b' right,
# 'x' left, 'y' top). Nintendo pads swap them to match their labels unless this hint is off; off, every pad is read
# by position, the same way.
os.environ.setdefault('SDL_GAMECONTROLLER_USE_BUTTON_LABELS', '0')

# Set on the events the gamepad posts
GAMEPAD = 'gamepad'

# The D-pad's directions (the NES joypad's, src/controls.py actions)
UP, DOWN, LEFT, RIGHT = 'UP', 'DOWN', 'LEFT', 'RIGHT'

# Which pad button does what is the player's (src/controls.py, the CONTROLS screen's PAD column). By default NES A and
# B are laid out the Nintendo way, by position: A is the right face button ('b'), B the bottom one ('a'); START is
# Start, SELECT is Back, the D-pad is the D-pad, the right trigger steps through the game speeds, the left and right
# shoulder buttons load and save state 1 (F1, Shift+F1) and the left trigger, held, rewinds (Backspace). A button
# presses its action's first key, with its modifiers, for as long as it's held: the save states read the KEYDOWN's
# modifiers, and the rewind runs from the KEYDOWN until the KEYUP. An action with no key has nothing to press.
DIRECTIONS = (UP, DOWN, LEFT, RIGHT)
# The action that steps through the game speeds (1x, 2x, 4x, 8x, 16x, then 1x again), done by the gamepad itself
# (src/waiting.py step_game_speed)
NEXT_SPEED = controls.NEXT_SPEED_ACTION


def d_pad() -> tuple[tuple[str, str], ...]:
    """The D-pad's buttons, in the order the NES reads them when two are down (CheckJoyUp ...: up wins over down, down
    over left, left over right, as on the keyboard, src/movement.py)."""
    pad = controls.current_controls().pad
    return tuple((button, direction) for direction in DIRECTIONS if (button := pad.get(direction)))


def button_bindings(buttons: Iterable[str]) -> dict[int, int]:
    """The key (and its modifiers) each action of these pad buttons presses: its first key."""
    pressed: dict[int, int] = {}
    held = set(buttons)
    pad = controls.current_controls().pad
    for action in controls.ACTIONS:
        button = pad.get(action.name)
        if action.name in DIRECTIONS or action.name == NEXT_SPEED or button is None or button not in held:
            continue
        binding = controls.first_binding(action.name)
        if binding is not None:
            pressed.setdefault(binding.key, binding.mod)
    return pressed


# The left stick: pushed past STICK_PRESS it presses a direction, and it lets go once back under STICK_RELEASE, so a
# stick resting near the edge doesn't flicker. The NES has no diagonals: the axis pushed furthest wins, and the
# direction held stays until the other axis is pushed AXIS_SWITCH_MARGIN further, so a stick held near 45 degrees
# doesn't jitter between the two.
STICK_PRESS = 0.5
STICK_RELEASE = 0.35
AXIS_SWITCH_MARGIN = 0.15
POLL_WAIT_MS = 10  # how often read_button looks at the pad
# How far a trigger is pulled before it counts as pressed
TRIGGER_PRESS = 0.5


def direction_key(direction: str) -> int:
    """The key a direction presses: its first key (an NES direction always has one, src/controls.py)."""
    binding = controls.first_binding(direction)
    return binding.key if binding is not None else DEFAULT_DIRECTION_KEYS[direction]


DEFAULT_DIRECTION_KEYS = {UP: K_UP, DOWN: K_DOWN, LEFT: K_LEFT, RIGHT: K_RIGHT}


class PadState(NamedTuple):
    """A controller as it is now: the buttons down (SDL GameController names, the D-pad and the triggers past
    TRIGGER_PRESS included) and the left stick, each axis from -1 to 1 (down is positive)."""
    buttons: frozenset[str] = frozenset()
    stick_x: float = 0.0
    stick_y: float = 0.0


def stick_direction(stick_x: float, stick_y: float, previous: str | None) -> str | None:
    """The direction the left stick presses (see STICK_PRESS), given the one pressed on the last poll."""
    across, along = abs(stick_x), abs(stick_y)
    if max(across, along) < (STICK_PRESS if previous is None else STICK_RELEASE):
        return None
    if previous in (LEFT, RIGHT):
        horizontal = along <= across + AXIS_SWITCH_MARGIN
    elif previous in (UP, DOWN):
        horizontal = across > along + AXIS_SWITCH_MARGIN
    else:
        horizontal = across > along
    if horizontal:
        return RIGHT if stick_x > 0 else LEFT
    return DOWN if stick_y > 0 else UP


def pad_direction(state: PadState, previous: str | None) -> str | None:
    """The one direction the pad presses: the D-pad's if it is pressed (NES order), else the left stick's."""
    for pad_button, direction in d_pad():
        if pad_button in state.buttons:
            return direction
    return stick_direction(state.stick_x, state.stick_y, previous)


class PadDevice(Protocol):
    """One controller."""

    def attached(self) -> bool: ...

    def read(self) -> PadState: ...

    def close(self) -> None: ...


class PadBackend(Protocol):
    """Where controllers come from."""

    def count(self) -> int:
        """How many are plugged in."""

    def open_first(self) -> PadDevice | None:
        """Open the first one that can be opened (None if none can)."""


class Gamepad:
    """The player's controller (see the module docstring)."""

    def __init__(self, backend: PadBackend) -> None:
        self.backend = backend
        self.device: PadDevice | None = None
        self.device_count = 0
        self.held: set[int] = set()
        self.direction: str | None = None
        self.speed_pressed = False
        self.polling = False

    def connect(self) -> None:
        """Start reading the controller on every read of input."""
        set_gamepad(self)

    def disconnect(self) -> None:
        """Stop reading it, letting go of every key it holds."""
        set_gamepad(None)
        self.press(set())
        if self.device is not None:
            self.device.close()
            self.device = None
        self.device_count = 0

    def poll(self) -> None:
        """See the module docstring."""
        if self.polling:
            return
        self.polling = True
        try:
            self.check_devices()
            self.update(self.device.read() if self.device is not None else None)
        finally:
            self.polling = False

    def check_devices(self) -> None:
        """Hot-plugging: when a controller is plugged in or out, keep the one in use if it still is, else let go of
        its keys and open the first one there is."""
        count = self.backend.count()
        if count == self.device_count and (self.device is None or self.device.attached()):
            return
        self.device_count = count
        if self.device is not None:
            if self.device.attached():
                return
            self.device.close()
            self.device = None
            self.press(set())
            self.direction = None
            self.speed_pressed = False
        if count:
            self.device = self.backend.open_first()

    def update(self, state: PadState | None) -> None:
        """Press and let go of the keys for the controller's state (None: no controller, nothing down)."""
        if state is None:
            self.direction = None
            self.speed_pressed = False
            self.press(set())
            return
        self.direction = pad_direction(state, self.direction)
        speed_button = controls.current_controls().pad.get(NEXT_SPEED)
        speed_pressed = speed_button is not None and speed_button in state.buttons
        if speed_pressed and not self.speed_pressed:
            step_game_speed()
        self.speed_pressed = speed_pressed
        bindings = button_bindings(state.buttons)
        self.press(self.pad_keys(state, bindings), bindings)

    def pad_keys(self, state: PadState, bindings: dict[int, int] | None = None) -> set[int]:
        """The keys the pad holds down: its buttons' actions' and its one direction's."""
        keys = set(button_bindings(state.buttons) if bindings is None else bindings)
        if self.direction is not None:
            keys.add(direction_key(self.direction))
        return keys

    def read_button(self, timeout_ms: int) -> str | None:
        """The next pad button pressed within ``timeout_ms`` (a D-pad button or a trigger counts; the stick doesn't),
        for the CONTROLS screen. Nothing is pressed for the game meanwhile, and the button is waited out (up to
        timeout_ms more), so it doesn't also press its key once the screen reads the pad again."""
        if self.device is None:
            return None
        self.polling = True
        try:
            baseline = set(self.device.read().buttons)
            deadline = pygame.time.get_ticks() + timeout_ms
            chosen: str | None = None
            while chosen is None and pygame.time.get_ticks() < deadline and self.device.attached():
                pygame.time.wait(POLL_WAIT_MS)
                pygame.event.pump()
                buttons = self.device.read().buttons
                new = sorted(set(buttons) - baseline)
                if new:
                    chosen = new[0]
                baseline &= set(buttons)  # a button let go can be pressed again
            release_by = pygame.time.get_ticks() + timeout_ms
            while chosen is not None and chosen in self.device.read().buttons and pygame.time.get_ticks() < release_by:
                pygame.time.wait(POLL_WAIT_MS)
                pygame.event.pump()
            # Whatever is still held stays held without a new press when polling goes on
            state = self.device.read()
            self.direction = pad_direction(state, self.direction)
            self.held = self.pad_keys(state)
            return chosen
        finally:
            self.polling = False

    def press(self, keys: set[int], modifiers: dict[int, int] | None = None) -> None:
        """Hold ``keys`` and nothing else: post a KEYUP for each held key not in them, then a KEYDOWN for each new
        one."""
        for released in sorted(self.held - keys):
            self.post(KEYUP, released)
        for pressed in sorted(keys - self.held):
            self.post(KEYDOWN, pressed, (modifiers or {}).get(pressed, 0))
        self.held = set(keys)

    @staticmethod
    def post(event_type: int, posted_key: int, mod: int = 0) -> None:
        if not pygame.display.get_init():
            return
        # No unicode: a button is no letter typed (the name entry types letters, src/menu_functions.py)
        attributes: dict[str, Any] = {'key': posted_key, 'mod': mod, 'scancode': 0, 'unicode': '', GAMEPAD: True}
        pygame.event.post(pygame.event.Event(event_type, attributes))


def is_gamepad(current_event: pygame.event.Event) -> bool:
    """Whether the gamepad posted this event."""
    return getattr(current_event, GAMEPAD, False) is True


# SDL's controllers (pygame._sdl2.controller)

SDL_BUTTONS: tuple[tuple[str, int], ...] = (
    ('a', pygame.CONTROLLER_BUTTON_A), ('b', pygame.CONTROLLER_BUTTON_B),
    ('x', pygame.CONTROLLER_BUTTON_X), ('y', pygame.CONTROLLER_BUTTON_Y),
    ('back', pygame.CONTROLLER_BUTTON_BACK), ('start', pygame.CONTROLLER_BUTTON_START),
    ('leftshoulder', pygame.CONTROLLER_BUTTON_LEFTSHOULDER),
    ('rightshoulder', pygame.CONTROLLER_BUTTON_RIGHTSHOULDER),
    ('dpup', pygame.CONTROLLER_BUTTON_DPAD_UP), ('dpdown', pygame.CONTROLLER_BUTTON_DPAD_DOWN),
    ('dpleft', pygame.CONTROLLER_BUTTON_DPAD_LEFT), ('dpright', pygame.CONTROLLER_BUTTON_DPAD_RIGHT),
)
SDL_TRIGGERS: tuple[tuple[str, int], ...] = (
    ('lefttrigger', pygame.CONTROLLER_AXIS_TRIGGERLEFT), ('righttrigger', pygame.CONTROLLER_AXIS_TRIGGERRIGHT))
SDL_AXIS_MAX = 32767

# A joystick SDL has no mapping for: button number -> pad button. A guess, as there is no standard: the common layout
# of USB pads with face buttons 0 to 3, then select and start (6 and 7 on XInput-like pads, 8 and 9 on others).
JOYSTICK_BUTTONS: dict[int, str] = {0: 'a', 1: 'b', 2: 'x', 3: 'y', 6: 'back', 7: 'start', 8: 'back', 9: 'start'}
JOYSTICK_HAT_BUTTONS = {(0, 1): 'dpup', (0, -1): 'dpdown', (-1, 0): 'dpleft', (1, 0): 'dpright'}


def sdl_controller_module() -> Any:
    """pygame._sdl2.controller, initialized, or None if it can't be."""
    try:
        from pygame._sdl2 import controller
        if not controller.get_init():
            controller.init()
        return controller
    except (ImportError, pygame.error):
        return None


class ControllerDevice:
    """A controller SDL knows the layout of (pygame._sdl2.controller.Controller)."""

    def __init__(self, controller: Any) -> None:
        self.controller = controller

    def attached(self) -> bool:
        try:
            return bool(self.controller.attached())
        except pygame.error:
            return False

    def read(self) -> PadState:
        controller = self.controller
        buttons = {name for name, number in SDL_BUTTONS if controller.get_button(number)}
        buttons.update(name for name, axis in SDL_TRIGGERS
                       if controller.get_axis(axis) / SDL_AXIS_MAX > TRIGGER_PRESS)
        return PadState(frozenset(buttons), controller.get_axis(pygame.CONTROLLER_AXIS_LEFTX) / SDL_AXIS_MAX,
                        controller.get_axis(pygame.CONTROLLER_AXIS_LEFTY) / SDL_AXIS_MAX)

    def close(self) -> None:
        try:
            self.controller.quit()
        except pygame.error:
            pass


class JoystickDevice:
    """A joystick SDL has no controller mapping for (pygame.joystick), read with JOYSTICK_BUTTONS, the first hat and
    the first two axes."""

    def __init__(self, joystick: Any) -> None:
        self.joystick = joystick
        self.opened_with = pygame.joystick.get_count()

    def attached(self) -> bool:
        """pygame.joystick can't tell whether this one is still plugged in, so any controller plugged in or out counts
        as this one gone: the first one is opened again."""
        try:
            return bool(self.joystick.get_init()) and pygame.joystick.get_count() == self.opened_with
        except pygame.error:
            return False

    def read(self) -> PadState:
        joystick = self.joystick
        buttons = {name for number, name in JOYSTICK_BUTTONS.items()
                   if number < joystick.get_numbuttons() and joystick.get_button(number)}
        if joystick.get_numhats():
            hat_x, hat_y = joystick.get_hat(0)
            for hat, name in JOYSTICK_HAT_BUTTONS.items():
                if (hat[0] and hat[0] == hat_x) or (hat[1] and hat[1] == hat_y):
                    buttons.add(name)
        stick_x = joystick.get_axis(0) if joystick.get_numaxes() > 0 else 0.0
        stick_y = joystick.get_axis(1) if joystick.get_numaxes() > 1 else 0.0
        return PadState(frozenset(buttons), stick_x, stick_y)

    def close(self) -> None:
        try:
            self.joystick.quit()
        except pygame.error:
            pass


class SdlBackend:
    """The controllers plugged into the computer."""

    def count(self) -> int:
        if not pygame.joystick.get_init():
            return 0
        return pygame.joystick.get_count()

    def open_first(self) -> PadDevice | None:
        controller = sdl_controller_module()
        for index in range(self.count()):
            try:
                if controller is not None and controller.is_controller(index):
                    return ControllerDevice(controller.Controller(index))
                joystick = pygame.joystick.Joystick(index)
                joystick.init()
                return JoystickDevice(joystick)
            except pygame.error:
                continue
        return None


_gamepad: Gamepad | None = None


def connect_gamepad() -> Gamepad:
    """Read the player's controller from now on (the game calls this once, at the start). Plugged in or not: one
    plugged in later is found then."""
    global _gamepad
    if _gamepad is None:
        _gamepad = Gamepad(SdlBackend())
    _gamepad.connect()
    gamepad = _gamepad
    controls.set_pad_reader(gamepad.read_button, lambda: gamepad.device is not None)
    return _gamepad
