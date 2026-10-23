"""The controls: which keys (and which controller button) do what. Not NES (the NES pad is fixed).

Every button of the NES joypad and every extra action of this game (the game speed, the options, auto-grind ...) is an
*action* (``ACTIONS``), and the controls say which keyboard keys press it (up to ``KEY_SLOTS``) and which controller
button (``Controls``). The defaults are the keys the game has always used; the player changes them on the CONTROLS
screen (src/controls_screen.py), reached from the options overlay, and they are kept for the next time.

The rest of the game doesn't read the controls directly. It reads key sets (``KeySet``), such as src/common.py's
``A_BUTTON_KEYS``, which are live: ``key in A_BUTTON_KEYS`` asks the controls in use right now, so a change on the
CONTROLS screen applies at once everywhere, including in the tuples of keys built from them at import time
(``A_BUTTON_KEYS + START_BUTTON_KEYS`` is a key set too). A key set iterates, indexes and compares like the tuple of
its keys. The extra actions that care about modifiers (Shift+F1 saves a state, F1 loads it) are read with
``pressed(event, action)`` instead, which takes Shift, Ctrl and Alt into account.

A key binding is ``(key, modifiers)``: a pygame key code and a KMOD mask of the modifiers it is pressed with (0: none
needed). A binding with no modifiers is pressed whatever else is held, unless another binding for the same key with
held modifiers is pressed (Shift+F1 isn't also F1). The NES buttons and the directions take no modifiers: the game
reads them held as well as pressed, and ``key.get_pressed()`` has no modifiers.

They are kept with the global settings (src/settings.py, its "controls"; Game.__init__ reads them and saves every
change). There, the controls are the keys by action, each as its name in pygame (``K_F1`` is "F1", ``K_k`` is "k")
after "Shift+", "Ctrl+" or "Alt+" for the modifiers, and the controller button by its SDL GameController name
(src/gamepad.py):

    {"keys": {"A": ["k"], "B": ["j", "ESCAPE"], "LOAD_STATE_1": ["F1"], "SAVE_STATE_1": ["Shift+F1"], ...},
     "pad": {"A": "b", "B": "a", "START": "start", ...}}

An action missing from the file keeps its default keys (a newer version's actions, say), unless one of them was given
to another action. A key name that isn't a key, or one bound twice, is dropped.

This module imports nothing from ``src``, so src/common.py and src/waiting.py can use it.
"""
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, NamedTuple, Union, override

import pygame
from pygame import KMOD_ALT, KMOD_CTRL, KMOD_SHIFT

KEY_SLOTS = 2  # keyboard keys an action can have
MODIFIERS = ((KMOD_SHIFT, 'Shift'), (KMOD_CTRL, 'Ctrl'), (KMOD_ALT, 'Alt'))
MODIFIER_MASK = KMOD_SHIFT | KMOD_CTRL | KMOD_ALT


class Binding(NamedTuple):
    """A key and the modifiers it's pressed with (KMOD_SHIFT ..., 0 for none)."""
    key: int
    mod: int = 0


@dataclass(frozen=True, slots=True)
class Action:
    """Something a key or a button does: its name in the file, its label on the CONTROLS screen, its default keys and
    controller button, and whether it's one of the NES joypad's (``nes``: it must keep a key, and takes no
    modifiers)."""
    name: str
    label: str
    keys: tuple[Binding, ...] = ()
    pad: str | None = None
    nes: bool = False
    modifiers: bool = False  # whether a modifier held as it's bound is part of the binding


def _key(name: str) -> int:
    return getattr(pygame, f'K_{name}')


def _nes(name: str, label: str, keys: Sequence[str], pad: str | None) -> Action:
    return Action(name, label, tuple(Binding(_key(key_name)) for key_name in keys), pad, nes=True)


def _extra(name: str, label: str, keys: Sequence[str] = (), pad: str | None = None, mod: int = 0,
           modifiers: bool = True) -> Action:
    return Action(name, label, tuple(Binding(_key(key_name), mod) for key_name in keys), pad, modifiers=modifiers)


# Every action, in the CONTROLS screen's order. The controller's buttons are SDL GameController names: by position,
# 'a' is the bottom face button and 'b' the right one, so NES A is the right one and B the bottom, as on Nintendo's
# pads (src/gamepad.py).
ACTIONS: tuple[Action, ...] = (
    _nes('A', "A BUTTON", ('k',), 'b'),
    _nes('B', "B BUTTON", ('j', 'ESCAPE'), 'a'),
    _nes('START', "START", ('i',), 'start'),
    _nes('SELECT', "SELECT", ('u',), 'back'),
    _nes('UP', "UP", ('UP', 'w'), 'dpup'),
    _nes('DOWN', "DOWN", ('DOWN', 's'), 'dpdown'),
    _nes('LEFT', "LEFT", ('LEFT', 'a'), 'dpleft'),
    _nes('RIGHT', "RIGHT", ('RIGHT', 'd'), 'dpright'),
    # Enter: an extra A in the windows, and on the map TALK, TAKE or DOOR when one applies (Game.handle_enter_key)
    _extra('SMART_A', "SMART A", ('RETURN',), modifiers=False),
    # Tab: the options overlay, like SELECT (src/options_overlay.py)
    _extra('OPTIONS', "OPTIONS", ('TAB',), modifiers=False),
    _extra('HELP', "HELP", ('h',)),
    # Q: the quest journal (src/quest_journal.py)
    _extra('QUEST_JOURNAL', "JOURNAL", ('q',)),
    # M, or the pad's top face button: the dungeon map on a dark floor (src/dungeon_map.py)
    _extra('MAP', "MAP", ('m',), 'y'),
    _extra('AUTO_GRIND', "AUTO GRIND", ('g',)),
    _extra('AUTO_BATTLE', "AUTO FIGHT", ('F4',)),
    _extra('INVULNERABLE', "INVINCIBLE", ('F9',)),
    _extra('FULLSCREEN', "FULLSCREEN", ('F11',)),
    _extra('SPEED_1', "SPEED 1X", ('1',)),
    _extra('SPEED_2', "SPEED 2X", ('2',)),
    _extra('SPEED_4', "SPEED 4X", ('3',)),
    _extra('SPEED_8', "SPEED 8X", ('4',)),
    _extra('SPEED_16', "SPEED 16X", ('5',)),
    # Save states (src/save_state.py): Shift+F1 to F3 save one in slot 1 to 3, F1 to F3 load it
    _extra('LOAD_STATE_1', "LOAD 1", ('F1',), 'leftshoulder'),
    _extra('LOAD_STATE_2', "LOAD 2", ('F2',)),
    _extra('LOAD_STATE_3', "LOAD 3", ('F3',)),
    _extra('SAVE_STATE_1', "SAVE 1", ('F1',), 'rightshoulder', mod=KMOD_SHIFT),
    _extra('SAVE_STATE_2', "SAVE 2", ('F2',), mod=KMOD_SHIFT),
    _extra('SAVE_STATE_3', "SAVE 3", ('F3',), mod=KMOD_SHIFT),
    # Held on the map: rewind (src/rewind.py), until it's let go
    _extra('REWIND', "REWIND", ('BACKSPACE',), 'lefttrigger'),
    # The message log (src/message_log.py), on the map
    # L, or the pad's left face button (M and the top button are the dungeon map's, MAP)
    _extra('MESSAGE_LOG', "MSG LOG", ('l',), 'x'),
    # The next game speed, back to 1x after 16x
    _extra('NEXT_SPEED', "NEXT SPEED", (), 'righttrigger'),
)
ACTION_NAMES = tuple(action.name for action in ACTIONS)
ACTIONS_BY_NAME: dict[str, Action] = {action.name: action for action in ACTIONS}
# The game speed each speed action sets (src/waiting.py)
SPEED_ACTIONS = {'SPEED_1': 1, 'SPEED_2': 2, 'SPEED_4': 4, 'SPEED_8': 8, 'SPEED_16': 16}
# The save state slot each save state action saves or loads (Game.handle_save_state_keys)
SAVE_STATE_ACTIONS = {'SAVE_STATE_1': 1, 'SAVE_STATE_2': 2, 'SAVE_STATE_3': 3}
LOAD_STATE_ACTIONS = {'LOAD_STATE_1': 1, 'LOAD_STATE_2': 2, 'LOAD_STATE_3': 3}

# Every controller button the CONTROLS screen can bind (SDL GameController names) and its label there, by position
# ('a' bottom, 'b' right, 'x' left, 'y' top, whatever the pad's labels say)
PAD_BUTTONS: dict[str, str] = {
    'a': "SOUTH", 'b': "EAST", 'x': "WEST", 'y': "NORTH",
    'back': "BACK", 'start': "START",
    'leftshoulder': "LB", 'rightshoulder': "RB", 'lefttrigger': "LT", 'righttrigger': "RT",
    'dpup': "D-UP", 'dpdown': "D-DN", 'dpleft': "D-LT", 'dpright': "D-RT",
}


# Key names, both ways: pygame's own constant names without K_ (K_F1 is "F1"), the first in sorted order for a key
# with more than one (K_KP0 and K_KP_0)
def _key_names() -> tuple[dict[int, str], dict[str, int]]:
    by_code: dict[int, str] = {}
    by_name: dict[str, int] = {}
    for constant in sorted(dir(pygame)):
        if not constant.startswith('K_'):
            continue
        code = getattr(pygame, constant)
        if not isinstance(code, int):
            continue
        name = constant[2:]
        by_name[name] = code
        by_code.setdefault(code, name)
    return by_code, by_name


KEY_NAMES, KEY_CODES = _key_names()


def binding_name(binding: Binding) -> str:
    """The binding as it's written in the file: "Shift+F1", "k"."""
    prefix = ''.join(f'{label}+' for mask, label in MODIFIERS if binding.mod & mask)
    return prefix + KEY_NAMES.get(binding.key, str(binding.key))


# Short names for keys whose pygame name is long, for the CONTROLS screen and the help
KEY_LABELS = {
    'RETURN': "ENTER", 'ESCAPE': "ESC", 'BACKSPACE': "BKSP", 'DELETE': "DEL", 'INSERT': "INS", 'PAGEUP': "PGUP",
    'PAGEDOWN': "PGDN", 'CAPSLOCK': "CAPS", 'NUMLOCK': "NUMLK", 'SCROLLOCK': "SCRLK", 'PRINT': "PRTSC",
    'LSHIFT': "LSHIFT", 'RSHIFT': "RSHIFT", 'LCTRL': "LCTRL", 'RCTRL': "RCTRL", 'LALT': "LALT", 'RALT': "RALT",
    'LGUI': "LMETA", 'RGUI': "RMETA", 'KP_ENTER': "KPENT", 'KP_PLUS': "KP+", 'KP_MINUS': "KP-",
    'KP_MULTIPLY': "KP*", 'KP_DIVIDE': "KP/", 'KP_PERIOD': "KP.", 'KP_EQUALS': "KP=", 'SPACE': "SPACE",
    'MENU': "MENU", 'SCROLLLOCK': "SCRLK", 'SYSREQ': "SYSRQ", 'CURRENCYUNIT': "CURR", 'CURRENCYSUBUNIT': "SUBCUR",
}
# The help has room for some of them in full
LONG_KEY_LABELS = {'BACKSPACE': "BACKSPACE", 'DELETE': "DELETE", 'INSERT': "INSERT", 'PAGEUP': "PAGE UP",
                   'PAGEDOWN': "PAGE DOWN"}
CELL_WIDTH = 6  # tiles for a key on the CONTROLS screen
SHORT_MODIFIERS = {KMOD_SHIFT: "S+", KMOD_CTRL: "C+", KMOD_ALT: "A+"}
LONG_MODIFIERS = {KMOD_SHIFT: "SHIFT+", KMOD_CTRL: "CTRL+", KMOD_ALT: "ALT+"}


def key_label(binding: Binding, short: bool = True) -> str:
    """The key as the CONTROLS screen shows it (``short``: at most 6 characters, "S+F1") or the help does
    ("SHIFT+F1"): upper case, with short names for the long ones (Enter, Esc ...)."""
    name = KEY_NAMES.get(binding.key, '?')
    if not short and name in LONG_KEY_LABELS:
        label = LONG_KEY_LABELS[name]
    elif name in KEY_LABELS:
        label = KEY_LABELS[name]
    elif 32 < binding.key < 127:
        label = chr(binding.key).upper()  # a printable key is its character: ";", "["
    else:
        label = name.upper().replace('_', '')
    modifiers = SHORT_MODIFIERS if short else LONG_MODIFIERS
    prefix = ''.join(text for mask, text in modifiers.items() if binding.mod & mask)
    if short:
        # A cell is 6 tiles: a longer name is cut short, to what's left after the modifiers
        label = label[:CELL_WIDTH - len(prefix)]
    return prefix + label


def keys_label(name: str, separator: str = '/') -> str:
    """An action's keys for the help: "J/ESC" ("-" if it has none)."""
    return separator.join(key_label(binding, short=False) for binding in _controls.action_keys(name)) or '-'


def directions_label(arrows: str = "ARROWS") -> str:
    """The D-pad's keys for the help, slot by slot: "ARROWS/WASD" by default (``arrows`` is the word for the arrow
    keys), else each slot's four keys, up, down, left, right ("I/K/J/L")."""
    labels = []
    for slot in range(KEY_SLOTS):
        bindings = [_controls.action_keys(name)[slot] if slot < len(_controls.action_keys(name)) else None
                    for name in ('UP', 'DOWN', 'LEFT', 'RIGHT')]
        if all(binding is None for binding in bindings):
            continue
        codes = tuple(binding.key if binding else None for binding in bindings)
        if codes == (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
            labels.append(arrows)
        elif codes == (pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d):
            labels.append("WASD")
        else:
            labels.append(','.join(key_label(binding, short=False) if binding else '-' for binding in bindings))
    return '/'.join(labels)


def group_label(names: Sequence[str], compact: str) -> str:
    """Keys that go together for the help (the speeds, the save state slots): ``compact`` ("1-5") while they all have
    their default keys, else each one's first key ("-" for none)."""
    if all(_controls.action_keys(name) == list(ACTIONS_BY_NAME[name].keys) for name in names):
        return compact
    firsts = [_controls.action_keys(name)[:1] for name in names]
    return '/'.join(key_label(first[0], short=False) if first else '-' for first in firsts)


def pad_is_default(name: str) -> bool:
    """Whether the action has its default controller button (the help then names it as it always has)."""
    return _controls.pad.get(name) == ACTIONS_BY_NAME[name].pad


def pad_name(name: str) -> str:
    """The action's controller button for the help ("-" for none)."""
    return pad_label(_controls.pad.get(name))


def pad_label(button: str | None) -> str:
    """A controller button as the CONTROLS screen shows it ("-" for none)."""
    return PAD_BUTTONS.get(button, '-') if button else '-'


def parse_binding(text: Any) -> Binding | None:
    """A binding written as binding_name writes it (None if it isn't one)."""
    if not isinstance(text, str):
        return None
    *prefixes, name = text.split('+')
    mod = 0
    for prefix in prefixes:
        masks = [mask for mask, label in MODIFIERS if label == prefix]
        if not masks:
            return None
        mod |= masks[0]
    code = KEY_CODES.get(name)
    return None if code is None else Binding(code, mod)


def normalized(binding: Binding, action: Action) -> Binding:
    """The binding as the action keeps it: its modifiers only the ones that count (Shift, Ctrl, Alt; one mask for
    left and right), and none at all for an action that takes none."""
    if not action.modifiers:
        return Binding(binding.key)
    mod = 0
    for mask, _label in MODIFIERS:
        if binding.mod & mask:
            mod |= mask
    return Binding(binding.key, mod)


def bindings_clash(first: Binding, first_action: Action, second: Binding, second_action: Action) -> bool:
    """Whether two bindings would both be pressed by one key press: the same key with the same modifiers, or the same
    key at all when either action ignores modifiers."""
    if first.key != second.key:
        return False
    return first.mod == second.mod or not first_action.modifiers or not second_action.modifiers


@dataclass(slots=True)
class Controls:
    """The keys and controller button of each action (see the module docstring)."""
    keys: dict[str, list[Binding]] = field(default_factory=dict)
    pad: dict[str, str | None] = field(default_factory=dict)

    @classmethod
    def defaults(cls) -> 'Controls':
        return cls({action.name: list(action.keys) for action in ACTIONS},
                   {action.name: action.pad for action in ACTIONS})

    def copy(self) -> 'Controls':
        return Controls({name: list(bindings) for name, bindings in self.keys.items()}, dict(self.pad))

    def is_default(self) -> bool:
        return self == Controls.defaults()

    def action_keys(self, name: str) -> list[Binding]:
        return self.keys.get(name, [])

    def owner_of(self, binding: Binding, action: Action,
                 ignore: tuple[str, int] | None = None) -> tuple[str, int] | None:
        """The action (other than ``action``) and slot already holding a key that clashes with ``binding``, leaving
        out the slot ``ignore``."""
        for other in ACTIONS:
            if other.name == action.name:
                continue
            for slot, bound in enumerate(self.action_keys(other.name)):
                if (other.name, slot) != ignore and bindings_clash(binding, action, bound, other):
                    return other.name, slot
        return None

    def pad_owner_of(self, button: str, name: str) -> str | None:
        """The action (other than ``name``) the controller button is bound to."""
        return next((other for other, bound in self.pad.items() if bound == button and other != name), None)

    def bind_key(self, name: str, slot: int, binding: Binding) -> bool:
        """Put the key in the action's slot (the next free slot if ``slot`` is past its keys). If another action has
        it, the two swap: that action gets the key this slot had, so no NES button is left without a key. If this
        slot was empty, the other action loses the key, unless it's an NES button whose only key it is: then nothing
        changes. Returns whether the controls changed."""
        action = ACTIONS_BY_NAME[name]
        binding = normalized(binding, action)
        own = self.keys.setdefault(name, [])
        slot = min(slot, len(own), KEY_SLOTS - 1)
        previous = own[slot] if slot < len(own) else None
        if previous == binding:
            return False
        if binding in own:
            # The action has it already, in its other slot: the two slots swap
            other_slot = own.index(binding)
            if previous is None:
                return False
            own[slot], own[other_slot] = binding, previous
            return True
        # On a copy, so a refused change leaves everything as it was. Every key that clashes goes: the first one
        # (usually the only one; Shift+F1 and F1 both clash with an NES button's F1) is swapped if it can be.
        trial = self.copy()
        trial_own = trial.keys[name]
        if previous is None:
            trial_own.append(binding)
        else:
            trial_own[slot] = binding
        swap_offered = previous is not None
        while (owner := trial.owner_of(binding, action)) is not None:
            owner_name, owner_slot = owner
            owner_action = ACTIONS_BY_NAME[owner_name]
            owner_keys = trial.keys[owner_name]
            swapped = normalized(previous, owner_action) if swap_offered and previous is not None else None
            swap_offered = False
            if swapped is not None and swapped not in owner_keys and trial.owner_of(swapped, owner_action) is None:
                owner_keys[owner_slot] = swapped
            elif owner_action.nes and len(owner_keys) == 1:
                return False
            else:
                del owner_keys[owner_slot]
        self.keys = trial.keys
        return True

    def clear_key(self, name: str, slot: int) -> bool:
        """Take the key out of the action's slot, unless it's an NES button's only key. Returns whether it changed."""
        own = self.keys.get(name, [])
        if slot >= len(own) or (ACTIONS_BY_NAME[name].nes and len(own) == 1):
            return False
        del own[slot]
        return True

    def bind_pad(self, name: str, button: str | None) -> bool:
        """Bind the controller button to the action (None: no button). Another action with that button swaps: it gets
        this action's button. Returns whether the controls changed."""
        previous = self.pad.get(name)
        if previous == button:
            return False
        if button is not None:
            owner = self.pad_owner_of(button, name)
            if owner is not None:
                self.pad[owner] = previous
        self.pad[name] = button
        return True

    def to_json(self) -> dict[str, Any]:
        return {'keys': {name: [binding_name(binding) for binding in self.action_keys(name)] for name in ACTION_NAMES},
                'pad': {name: self.pad.get(name) for name in ACTION_NAMES}}

    @classmethod
    def from_json(cls, data: Any) -> 'Controls':
        """The controls in ``data`` (see the module docstring): the defaults for whatever is missing or makes no
        sense, so one bad entry doesn't lose the others."""
        controls = cls.defaults()
        if not isinstance(data, Mapping):
            return controls
        keys = data.get('keys')
        if isinstance(keys, Mapping):
            saved: dict[str, list[Binding]] = {}
            for action in ACTIONS:
                entries = keys.get(action.name)
                if not isinstance(entries, list):
                    continue
                bindings: list[Binding] = []
                for entry in entries:
                    binding = parse_binding(entry)
                    if binding is None:
                        continue
                    binding = normalized(binding, action)
                    if binding in bindings or any(
                            bindings_clash(binding, action, bound, ACTIONS_BY_NAME[other])
                            for other, bounds in saved.items() for bound in bounds):
                        continue
                    bindings.append(binding)
                if bindings or not action.nes:
                    saved[action.name] = bindings[:KEY_SLOTS]
            # The actions the file doesn't have keep the default keys no saved action took
            for action in ACTIONS:
                if action.name in saved:
                    continue
                saved[action.name] = [binding for binding in action.keys if not any(
                    bindings_clash(binding, action, bound, ACTIONS_BY_NAME[other])
                    for other, bounds in saved.items() for bound in bounds)]
            controls.keys = saved
        pads = data.get('pad')
        if isinstance(pads, Mapping):
            taken: set[str] = set()
            for action in ACTIONS:
                if action.name not in pads:
                    continue
                button = pads[action.name]
                controls.pad[action.name] = button if button in PAD_BUTTONS and button not in taken else None
            # The defaults of the actions the file doesn't have, unless a saved one took that button
            taken = {button for name, button in controls.pad.items() if name in pads and button}
            for action in ACTIONS:
                if action.name not in pads:
                    controls.pad[action.name] = action.pad if action.pad not in taken else None
        return controls


# The controls in use
_controls = Controls.defaults()
_version = 0  # counts the changes, so the key sets know when to look again


_listener: Callable[[Controls], None] | None = None  # told of every change the player makes (to save it)
# Reads the next controller button pressed within a time in ms, for the CONTROLS screen (src/gamepad.py), and says
# whether a controller is plugged in
_pad_reader: Callable[[int], str | None] | None = None
_pad_connected: Callable[[], bool] | None = None


def current_controls() -> Controls:
    """The controls in use (don't change them: change a copy and set_controls or apply_controls it)."""
    return _controls


def apply_controls(controls: Controls) -> None:
    """The player changed the controls (the CONTROLS screen): use them, and tell the listener, which saves them."""
    set_controls(controls)
    if _listener is not None:
        _listener(_controls.copy())


def set_controls_listener(listener: Callable[[Controls], None] | None) -> None:
    global _listener
    _listener = listener


def set_pad_reader(reader: Callable[[int], str | None] | None, connected: Callable[[], bool] | None = None) -> None:
    """What reads a controller button for the CONTROLS screen (None: no controller support)."""
    global _pad_reader, _pad_connected
    _pad_reader, _pad_connected = reader, connected


def read_pad_button(timeout_ms: int) -> str | None:
    """The next controller button pressed (its SDL GameController name), or None if none is within ``timeout_ms`` or
    there is no controller."""
    return _pad_reader(timeout_ms) if _pad_reader is not None and pad_connected() else None


def pad_connected() -> bool:
    return _pad_connected is not None and _pad_connected()


def set_controls(controls: Controls) -> None:
    """Use these controls from now on (a copy: changing ``controls`` afterwards changes nothing)."""
    global _controls, _version
    _controls = controls.copy()
    _version += 1


def reset_controls() -> None:
    """Back to the default controls (a new game, or a test)."""
    set_controls(Controls.defaults())


def action_keys(name: str) -> tuple[int, ...]:
    """The keys of an action, in its slots' order."""
    return tuple(binding.key for binding in _controls.action_keys(name))


def actions_for_event(current_event: Any) -> list[str]:
    """The actions a key press presses (see the module docstring for the modifiers)."""
    pressed_key = getattr(current_event, 'key', None)
    if pressed_key is None:
        return []
    held = getattr(current_event, 'mod', 0)
    mod = 0
    for mask, _label in MODIFIERS:  # either Shift is Shift
        if held & mask:
            mod |= mask
    exact: list[str] = []
    plain: list[str] = []
    for action in ACTIONS:
        for binding in _controls.action_keys(action.name):
            if binding.key != pressed_key:
                continue
            if binding.mod and mod & binding.mod == binding.mod:
                exact.append(action.name)
            elif not binding.mod:
                plain.append(action.name)
    return exact or plain


def pressed(current_event: Any, name: str) -> bool:
    """Whether this event is a press of one of the action's keys (with its modifiers)."""
    return getattr(current_event, 'type', None) == pygame.KEYDOWN and name in actions_for_event(current_event)


def first_binding(name: str) -> Binding | None:
    """The action's first key (what the controller presses for it), or None if it has none."""
    keys = _controls.action_keys(name)
    return keys[0] if keys else None


class KeySet(Sequence[int]):
    """The keys of some actions, as they are bound right now, plus some fixed keys: used like a tuple of keys (see the
    module docstring)."""

    def __init__(self, *names: str, fixed: Iterable[int] = ()):
        unknown = [name for name in names if name not in ACTIONS_BY_NAME]
        if unknown:
            raise ValueError(f"Unknown actions: {unknown}")
        self.names = names
        self.fixed = tuple(fixed)
        self._cache_version = -1
        self._cache: tuple[int, ...] = ()

    def keys(self) -> tuple[int, ...]:
        if self._cache_version != _version:
            keys: list[int] = []
            for name in self.names:
                keys += [key for key in action_keys(name) if key not in keys]
            keys += [key for key in self.fixed if key not in keys]
            self._cache = tuple(keys)
            self._cache_version = _version
        return self._cache

    @override
    def __contains__(self, item: object) -> bool:
        return item in self.keys()

    @override
    def __iter__(self) -> Iterator[int]:
        return iter(self.keys())

    @override
    def __len__(self) -> int:
        return len(self.keys())

    @override
    def __getitem__(self, index):  # type: ignore[override]
        return self.keys()[index]

    def __add__(self, other: Union['KeySet', Iterable[int]]) -> 'KeySet':
        if isinstance(other, KeySet):
            return KeySet(*self.names, *[name for name in other.names if name not in self.names],
                          fixed=self.fixed + other.fixed)
        return KeySet(*self.names, fixed=self.fixed + tuple(other))

    # As a set of keys, with sets of keys (the virtual joypad's held keys)
    def __and__(self, other: Iterable[int]) -> frozenset[int]:
        return frozenset(self.keys()) & frozenset(other)

    __rand__ = __and__

    def __sub__(self, other: Iterable[int]) -> frozenset[int]:
        return frozenset(self.keys()) - frozenset(other)

    def __rsub__(self, other: Iterable[int]) -> frozenset[int]:
        return frozenset(other) - frozenset(self.keys())

    @override
    def __eq__(self, other: object) -> bool:
        if isinstance(other, KeySet):
            return self.keys() == other.keys()
        if isinstance(other, tuple):
            return self.keys() == other
        return NotImplemented

    @override
    def __hash__(self) -> int:
        return hash((self.names, self.fixed))

    @override
    def __repr__(self) -> str:
        return f"KeySet({', '.join(self.names)}: {self.keys()})"
