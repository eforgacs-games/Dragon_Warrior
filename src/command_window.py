"""The field COMMAND window's selection (Bank01 CmdNonCmbtDat, opened by Bank03 ShowNCCmdWindow), read from the joypad
like every NES selection window: WndDoSelect, WndGetButtons and WndProcessInput (src/cursor.py SelectionButtons).

- WndDoSelect: WndInitSelect puts the cursor on TALK (WndCol = WndRow = 0) every time the window opens, and the
  joypad is read from scratch, so the A press that opened the window, still held, isn't read until it is let go, or
  for 11 frames if it never is (WndBtnRetrig = JoypadBtns = IN_RIGHT).
- WndProcessInput: only the first of A, B, up, down, left and right pressed is handled (SELECT and START are skipped).
  The cursor stops at the window's edges; it doesn't wrap: WndUpPressed does nothing on the top row, WndDownPressed
  on the bottom row ((WndHeight - 3) / 2), WndDoLeftPressed in column 0 and WndRightPressed in the last column
  (WndSelNumCols - 1). Only a real move calls WndUpdateCrsrPos, which restarts the cursor's blink.
- WndAPressed returns WndSelResults, WndCalcSelResult's WndCol * 4 rows + WndRow (NCC_TALK $00 to NCC_TAKE $07);
  WndBPressed returns WND_ABORT. Both draw the arrow one last time (WndUpdateCrsrPos), so it stays on.
"""
from collections.abc import Callable, Collection, Iterable

from pygame import KEYDOWN, key
from pygame.event import Event

from src.common import A_BUTTON_KEYS, DOWN_KEYS, LEFT_KEYS, RIGHT_KEYS, UP_KEYS, reject_keys
from src.cursor import IN_A, IN_B, IN_DOWN, IN_LEFT, IN_RIGHT, IN_UP, BlinkingCursor, SelectionButtons, first_button
from src.windows import COMMAND_COLUMNS, COMMAND_ROWS
from src.waiting import with_virtual_keys

# Defines WND_ABORT ($FF): the selection result of WndBPressed
WND_ABORT = 0xFF

# The joypad on the keyboard. K is A, and Enter also chooses (it always has in this window). START (I) doesn't:
# WndProcessInput skips it.
COMMAND_WINDOW_BUTTON_KEYS: tuple[tuple[int, Collection[int]], ...] = (
    (IN_A, A_BUTTON_KEYS),
    (IN_B, reject_keys),
    (IN_UP, UP_KEYS),
    (IN_DOWN, DOWN_KEYS),
    (IN_LEFT, LEFT_KEYS),
    (IN_RIGHT, RIGHT_KEYS),
)


def keyboard_buttons(is_down: Callable[[int], object]) -> int:
    """The joypad buttons (JoypadBtns bits) whose keys ``is_down(key)`` says are down."""
    buttons = 0
    for button, button_keys in COMMAND_WINDOW_BUTTON_KEYS:
        if any(is_down(button_key) for button_key in button_keys):
            buttons |= button
    return buttons


def held_buttons() -> int:
    """The buttons held right now (GetJoypadStatus), from the keyboard state."""
    pressed = with_virtual_keys(key.get_pressed())
    return keyboard_buttons(lambda button_key: pressed[button_key])


def tapped_buttons(events: Iterable[Event]) -> int:
    """The buttons pressed in these events, which may have been let go already. Other keys (the speed keys 1 to 5,
    START) are no button, so the window ignores them."""
    buttons = 0
    for current_event in events:
        if current_event.type == KEYDOWN:
            buttons |= keyboard_buttons(lambda button_key: button_key == current_event.key)
    return buttons


class CommandWindow:
    """Whether the COMMAND window is up and selecting, and its cursor: the selected entry (WndSelResults order, see
    src/windows.py COMMAND_ENTRIES), the blink (BlinkingCursor) and the joypad reading (SelectionButtons)."""

    def __init__(self) -> None:
        self.cursor = BlinkingCursor()
        self.buttons = SelectionButtons(self.cursor)
        self.selected = 0
        self.enabled = False

    def is_enabled(self) -> bool:
        return self.enabled

    def enable(self, held: int = 0) -> None:
        """WndDoSelect: WndInitSelect (the cursor on TALK, visible, its blink restarted), then the joypad read from
        scratch. ``held`` is the buttons held as the window opens."""
        self.selected = 0
        self.buttons.open(held)
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    @property
    def column(self) -> int:
        return self.selected // COMMAND_ROWS

    @property
    def row(self) -> int:
        return self.selected % COMMAND_ROWS

    def select(self, events: Iterable[Event]) -> int | None:
        """One frame of WndDoSelectLoop: WndGetButtons then WndProcessInput. Returns the entry chosen with A, WND_ABORT
        for B, or None while still selecting."""
        return self.process_input(self.buttons.read(held_buttons(), tapped_buttons(events)))

    def process_input(self, presses: int) -> int | None:
        """WndProcessInput (see the module docstring)."""
        button = first_button(presses)
        if not button:
            return None
        self.buttons.handled(button)  # STA WndBtnRetrig
        if button in (IN_A, IN_B):
            self.cursor.hold()  # WndUpdateCrsrPos: the arrow is drawn once more and stays on
            return self.selected if button == IN_A else WND_ABORT
        column, row = self.column, self.row
        if button == IN_UP:
            row = max(0, row - 1)
        elif button == IN_DOWN:
            row = min(COMMAND_ROWS - 1, row + 1)
        elif button == IN_LEFT:
            column = max(0, column - 1)
        elif button == IN_RIGHT:
            column = min(COMMAND_COLUMNS - 1, column + 1)
        selected = column * COMMAND_ROWS + row
        if selected != self.selected:
            self.selected = selected
            self.buttons.moved()  # WndUpdateCrsrPos
        return None
