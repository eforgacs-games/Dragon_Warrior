"""The CONTROLS screen: rebind the keys and the controller buttons (src/controls.py). Not on the NES.

The options overlay's CONTROLS row opens it (src/options_overlay.py). One NES-style window fills the screen, titled
CONTROLS, with a row per action (src/controls.py ACTIONS) and three cells on each: the action's two keys and its
controller button, under the headings KEY 1, KEY 2 and PAD. The last row is RESET TO DEFAULTS. Ten rows show at a
time; the list scrolls as the cursor goes past the top or the bottom. A line at the bottom says what the buttons do,
or what just happened.

    +--CONTROLS-----------------------+
    |           KEY 1  KEY 2  PAD     |
    |                                 |
    |A BUTTON  >K             EAST    |
    |B BUTTON   J      ESC    SOUTH   |
    |...                              |
    | A:SET  SELECT:CLEAR  B:BACK     |
    +---------------------------------+

- Up and down move between the rows, left and right between the cells.
- A on a cell waits for the key (or, on PAD, the controller button) to bind there: the next key pressed is bound,
  with Shift, Ctrl or Alt if they are held (for the actions that take modifiers). A modifier key alone is bound when
  it is let go. If nothing is pressed for CAPTURE_MS, nothing changes.
- A key or button another action has is swapped: that action gets the key this cell had (Controls.bind_key), and the
  bottom line names it. An NES button never loses its last key: that change is refused, and the line says so.
- SELECT (or Delete) clears the cell, except an NES button's last key.
- A on RESET TO DEFAULTS puts every key and button back as they were.
- B closes the screen, back to the options overlay.

Whatever the keys are bound to, the arrows, Enter, Escape and Delete always move, choose, close and clear here, so a
player can't lock themselves out of the screen. Every change applies at once and is saved with the global settings
(``apply_controls``).
"""
from collections.abc import Callable
from typing import NamedTuple

from pygame import K_DELETE, K_DOWN, K_ESCAPE, K_KP_ENTER, K_LEFT, K_RETURN, K_RIGHT, K_UP, KEYDOWN, KEYUP, Rect, \
    Surface, display, event, time

from src.common import A_BUTTON_KEYS, B_BUTTON_KEYS, DOWN_KEYS, LEFT_KEYS, RIGHT_KEYS, SELECT_BUTTON_KEYS, UP_KEYS, \
    set_gettext_language
from src.color import BLACK
from src.controls import ACTIONS, ACTIONS_BY_NAME, KEY_CODES, KEY_SLOTS, Action, Binding, Controls, apply_controls, \
    current_controls, key_label, pad_connected, pad_label, read_pad_button
from src.cursor import BlinkingCursor
from src.selection import frame_events, next_frame
from src.translated_window import draw_translated_window
from src.waiting import quit_if_requested
from src.windows import Window, WindowLayout, WindowText
from src.zoom import handle_zoom_event

# The whole screen: 16 blocks wide and 15 high
CONTROLS_WINDOW = Window(0, 0, 16, 15)
CONTROLS_TITLE = WindowText("CONTROLS", 4, 0)
HEADING_ROW = 2
FIRST_ROW = 4  # the first action's tile row; the rows are double spaced
VISIBLE_ROWS = 10
HINT_ROW = 26
HINT_COLUMN = 2
LABEL_COLUMN = 1  # up to 10 tiles: the cursor is never on a label, only on the cells
# Each cell's cursor tile column; its text starts in the tile after it. KEY 1 and KEY 2 are 6 tiles, PAD 5.
CELL_CURSOR_COLUMNS = (11, 18, 25)
HEADINGS = ("KEY 1", "KEY 2", "PAD")
PAD_CELL = KEY_SLOTS  # the third cell
RESET_LABEL = "RESET TO DEFAULTS"
RESET_CURSOR_COLUMN = 1  # the reset row is chosen from any cell; its text starts after the cursor
CAPTURE_MS = 5000  # how long A on a cell waits for a key (real time)

# The keys that always work here, whatever is bound (see the module docstring)
FIXED_UP, FIXED_DOWN, FIXED_LEFT, FIXED_RIGHT = (K_UP,), (K_DOWN,), (K_LEFT,), (K_RIGHT,)
FIXED_CHOOSE = (K_RETURN, K_KP_ENTER)
FIXED_BACK = (K_ESCAPE,)
FIXED_CLEAR = (K_DELETE,)

HINT = "A:SET  SELECT:CLEAR  B:BACK"
PRESS_KEY = "PRESS A KEY"
PRESS_PAD_BUTTON = "PRESS A PAD BUTTON"
NO_PAD = "NO CONTROLLER"
CHANGED_TOO = "{}: CHANGED TOO"
NEEDS_A_KEY = "{}: NEEDS A KEY"
DEFAULTS_RESTORED = "DEFAULTS RESTORED"
# Modifier keys: alone, they are bound when let go (a Shift held for Shift+F1 isn't bound on its own)
MODIFIER_KEY_NAMES = ('LSHIFT', 'RSHIFT', 'LCTRL', 'RCTRL', 'LALT', 'RALT', 'LGUI', 'RGUI')


MODIFIER_KEYS = frozenset(KEY_CODES[name] for name in MODIFIER_KEY_NAMES)


class Cell(NamedTuple):
    """Where the cursor is: the row (an action, or len(ACTIONS) for RESET TO DEFAULTS) and the cell (0 and 1 the keys,
    2 the controller button)."""
    row: int
    column: int


def cell_text(controls: Controls, action: Action, column: int) -> str:
    """What a cell shows: the key or the button, or "-" for none."""
    if column == PAD_CELL:
        return pad_label(controls.pad.get(action.name))
    keys = controls.action_keys(action.name)
    return key_label(keys[column]) if column < len(keys) else '-'


def first_shown_row(row: int, top: int) -> int:
    """The first row shown, scrolled so ``row`` is on screen."""
    if row < top:
        return row
    if row >= top + VISIBLE_ROWS:
        return row - VISIBLE_ROWS + 1
    return top


def controls_layout(controls: Controls, cell: Cell, top: int, hint: str) -> WindowLayout:
    """The window: the headings, the rows from ``top``, the bottom line, and the cursor's tile (its one entry)."""
    texts = [WindowText(heading, column + 1, HEADING_ROW) for heading, column in zip(HEADINGS, CELL_CURSOR_COLUMNS)]
    rows = len(ACTIONS) + 1
    for row in range(top, min(rows, top + VISIBLE_ROWS)):
        tile_row = FIRST_ROW + 2 * (row - top)
        if row == len(ACTIONS):
            texts.append(WindowText(RESET_LABEL, RESET_CURSOR_COLUMN + 1, tile_row))
            continue
        action = ACTIONS[row]
        texts.append(WindowText(action.label, LABEL_COLUMN, tile_row))
        for column, cursor_column in enumerate(CELL_CURSOR_COLUMNS):
            texts.append(WindowText(cell_text(controls, action, column), cursor_column + 1, tile_row))
    if hint:
        texts.append(WindowText(hint, HINT_COLUMN, HINT_ROW))
    cursor_column = RESET_CURSOR_COLUMN if cell.row == len(ACTIONS) else CELL_CURSOR_COLUMNS[cell.column]
    return WindowLayout(window=CONTROLS_WINDOW, title=CONTROLS_TITLE, texts=tuple(texts),
                        cursor_tiles=((cursor_column, FIRST_ROW + 2 * (cell.row - top)),))


def screen_texts() -> list[str]:
    """Every text the screen can show but the keys and the buttons, for the translation catalog."""
    return [CONTROLS_TITLE.text, *HEADINGS, RESET_LABEL, HINT, PRESS_KEY, PRESS_PAD_BUTTON, NO_PAD, CHANGED_TOO,
            NEEDS_A_KEY, DEFAULTS_RESTORED, *[action.label for action in ACTIONS]]


def changed_action(before: Controls, after: Controls, own: str) -> str | None:
    """The action other than ``own`` whose keys or button a change also changed (a swap)."""
    for action in ACTIONS:
        if action.name != own and (before.action_keys(action.name) != after.action_keys(action.name) or
                                   before.pad.get(action.name) != after.pad.get(action.name)):
            return action.name
    return None


class ControlsScreen:
    """The screen, run until it's closed (see the module docstring)."""

    def __init__(self, game):
        self.game = game
        self.config: dict = game.game_state.config
        self._: Callable[[str], str] = set_gettext_language(self.config.get('LANGUAGE'))
        self.cell = Cell(0, 0)
        self.top = 0
        self.hint = HINT

    @staticmethod
    def is_key(pressed_key: int, bound, fixed: tuple[int, ...]) -> bool:
        return pressed_key in fixed or pressed_key in bound

    def run(self) -> None:
        """Show the screen and read the buttons once a frame until it's closed."""
        cursor = BlinkingCursor()
        drawn: tuple | None = None
        while True:
            visible = cursor.visible()
            shown = (self.cell, self.top, self.hint, visible, repr(current_controls()))
            if shown != drawn:
                self.draw(visible)
                drawn = shown
            next_frame()
            for current_event in frame_events():
                if current_event.type != KEYDOWN:
                    continue
                if self.handle_key(current_event.key):
                    return
                cursor.restart()

    def handle_key(self, pressed_key: int) -> bool:
        """Handle a key press on the screen. Returns True when it closes the screen."""
        rows = len(ACTIONS) + 1
        row, column = self.cell
        if self.is_key(pressed_key, B_BUTTON_KEYS, FIXED_BACK):
            return True
        if self.is_key(pressed_key, UP_KEYS, FIXED_UP) or self.is_key(pressed_key, DOWN_KEYS, FIXED_DOWN):
            row = max(0, min(rows - 1, row + (-1 if self.is_key(pressed_key, UP_KEYS, FIXED_UP) else 1)))
            self.move_to(Cell(row, column))
        elif self.is_key(pressed_key, LEFT_KEYS, FIXED_LEFT) or self.is_key(pressed_key, RIGHT_KEYS, FIXED_RIGHT):
            step = -1 if self.is_key(pressed_key, LEFT_KEYS, FIXED_LEFT) else 1
            self.move_to(Cell(row, max(0, min(len(CELL_CURSOR_COLUMNS) - 1, column + step))))
        elif self.is_key(pressed_key, A_BUTTON_KEYS, FIXED_CHOOSE):
            self.play_sound()
            if row == len(ACTIONS):
                self.reset()
            else:
                self.capture(ACTIONS[row], column)
        elif self.is_key(pressed_key, SELECT_BUTTON_KEYS, FIXED_CLEAR) and row < len(ACTIONS):
            self.clear(ACTIONS[row], column)
        return False

    def move_to(self, cell: Cell) -> None:
        self.cell = cell
        self.top = first_shown_row(cell.row, self.top)
        self.hint = HINT

    def play_sound(self) -> None:
        self.game.sound.play_sound(self.game.directories.menu_button_sfx)

    def change(self, action: Action, edit: Callable[[Controls], bool]) -> None:
        """Make a change to a copy of the controls; apply it if it changed anything, and say what else it changed or
        that it was refused."""
        before = current_controls()
        after = before.copy()
        _ = self._
        if not edit(after):
            self.hint = _(NEEDS_A_KEY).format(_(action.label)) if action.nes and self.cell.column < KEY_SLOTS else HINT
            return
        apply_controls(after)
        other = changed_action(before, after, action.name)
        self.hint = _(CHANGED_TOO).format(_(ACTIONS_BY_NAME[other].label)) if other else HINT

    def capture(self, action: Action, column: int) -> None:
        """Wait for the key or the button to bind to the cell (see the module docstring)."""
        if column == PAD_CELL:
            self.hint = PRESS_PAD_BUTTON
            self.draw(True)
            button = read_pad_button(CAPTURE_MS)
            if button is None:
                self.hint = HINT if pad_connected() else NO_PAD
                return
            self.change(action, lambda controls: controls.bind_pad(action.name, button))
            return
        self.hint = PRESS_KEY
        self.draw(True)
        binding = self.read_key()
        if binding is None:
            self.hint = HINT
            return
        self.change(action, lambda controls: controls.bind_key(action.name, column, binding))

    def read_key(self) -> Binding | None:
        """The next key pressed, with the modifiers held (a modifier alone when it's let go), or None if nothing is
        pressed for CAPTURE_MS. The game speed keys are read as keys here, not as speeds."""
        deadline = time.get_ticks() + CAPTURE_MS
        modifier_down: int | None = None
        while time.get_ticks() < deadline:
            next_frame()
            for current_event in event.get():
                quit_if_requested(current_event)
                if handle_zoom_event(current_event) or getattr(current_event, 'gamepad', False):
                    continue
                if current_event.type == KEYDOWN:
                    if current_event.key in MODIFIER_KEYS:
                        modifier_down = current_event.key
                        continue
                    return Binding(current_event.key, getattr(current_event, 'mod', 0))
                if current_event.type == KEYUP and current_event.key == modifier_down:
                    return Binding(current_event.key)
        return None

    def clear(self, action: Action, column: int) -> None:
        if column == PAD_CELL:
            self.change(action, lambda controls: controls.bind_pad(action.name, None))
        else:
            self.change(action, lambda controls: controls.clear_key(action.name, column))

    def reset(self) -> None:
        apply_controls(Controls.defaults())
        self.hint = DEFAULTS_RESTORED

    def draw(self, cursor_visible: bool) -> None:
        if self.config.get('NO_BLIT'):
            return
        screen: Surface = self.game.screen
        layout = controls_layout(current_controls(), self.cell, self.top, self.hint)
        screen.fill(BLACK)
        draw_translated_window(screen, layout, self.game.color, self.config, self._, cursor_index=0,
                               cursor_visible=cursor_visible)
        display.update(Rect(0, 0, screen.get_width(), screen.get_height()))
