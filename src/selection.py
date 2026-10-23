"""The one selection loop of the game's windows: Bank01 WndDoSelect, run until A or B answers it.

Every window that blocks until an entry is chosen (YES/NO, the shop lists, ITEM and SPELL, the title menu and its log
windows, the message speed windows) runs ``run_selection``. Once per pass it

- draws the window, but only when something it shows changed: the selected entry, or the cursor's blink
  (src/cursor.py BlinkingCursor), which only changes every 16 frames;
- waits for the next NES frame of game time (``next_frame``, the WaitForNMI of WndGetButtons), so the loop no longer
  spins at full speed: at game speed N the frames come N times as often, like every other wait (src/waiting.py);
- reads the events (``frame_events``): closing the window quits (quit_if_requested), the keys 1 to 5 set the game
  speed (handle_speed_key) and are no button to the window;
- maps keys to the NES buttons (``SELECTION_KEYS``: A is K and Enter, B is reject_keys, Escape included, and the
  D-pad; START is no button, as WndProcessInput skips it) and handles them: A or B answers (the arrow is drawn one
  last time and stays on, WndAPressed/WndBPressed), a direction asks ``move`` for the entry it goes to, and only a
  real move restarts the blink (WndUpdateCrsrPos).

What differs between the windows is a parameter: which buttons end the selection, which make the menu sound, which
keep the arrow on, where the cursor can go (``move``: stop at the edges, or toggle), extra keys that answer at once
(``hotkeys``, the Y and N of the confirmation prompt), and how keys are read:

- by key press (the default): every key press in the queue is handled, in order, the way these windows always read
  their keys, so a quick tap is never lost and a held key does nothing more;
- by joypad (``joypad=True``, src/cursor.py SelectionButtons): the NES reading, one button per press, a held button
  read again 11 frames after the cursor moved or every 16 frames, and a key held as the window opens ignored until it
  is let go.

The COMMAND window (src/command_window.py) and the battle's command window (src/battle_controller.py) don't block:
they are read one frame at a time from the map loop and the fight loop, so they keep their own step.
"""
from collections.abc import Callable, Collection, Iterable, Mapping
from typing import NamedTuple

from pygame import KEYDOWN, event, key
from pygame.event import Event

from src.common import A_BUTTON_KEYS, DOWN_KEYS, LEFT_KEYS, RIGHT_KEYS, UP_KEYS, reject_keys
from src.cursor import IN_A, IN_B, IN_DOWN, IN_LEFT, IN_RIGHT, IN_UP, BlinkingCursor, SelectionButtons, first_button
from src.waiting import handle_speed_key, poll_virtual_joypad, quit_if_requested, wait_frames, with_virtual_keys
from src.zoom import handle_zoom_event

ButtonKeys = tuple[tuple[int, tuple[int, ...]], ...]

# The joypad on the keyboard, in WndProcessInput's order (A, B, up, down, left, right). A is K, and Enter chooses too,
# as it always has in these windows; B is reject_keys, Escape included. START (I) and SELECT are no button: Bank01
# WndProcessInput skips them, so they don't choose.
SELECTION_KEYS: ButtonKeys = (
    (IN_A, A_BUTTON_KEYS),
    (IN_B, tuple(reject_keys)),
    (IN_UP, UP_KEYS),
    (IN_DOWN, DOWN_KEYS),
    (IN_LEFT, LEFT_KEYS),
    (IN_RIGHT, RIGHT_KEYS),
)
ANSWER_BUTTONS = (IN_A, IN_B)
# The YES/NO windows' entries (WND_YES, WND_NO)
YES, NO = 0, 1


class Answer(NamedTuple):
    """How a selection ended: the button (IN_A or IN_B) and the entry it answered with (its index)."""
    button: int
    entry: int

    @property
    def accepted(self) -> bool:
        return self.button == IN_A


def next_frame() -> None:
    """WaitForNMI: wait one NES frame of game time (1/60 s, 1/(60 N) s at game speed N), still quitting if the window
    is closed meanwhile (src/waiting.py wait). The game's NO_WAIT doesn't skip it: it is the loop's frame pacing, not
    a pause in the game."""
    wait_frames(1)


def frame_events() -> list[Event]:
    """The events queued since the last pass: quits if the window was closed (quit_if_requested), and takes out the
    presses of 1 to 5 after setting the game speed (handle_speed_key) and the zoom keys after zooming the window
    (handle_zoom_event, src/zoom.py), so no window reads them as a key."""
    events = []
    poll_virtual_joypad()
    for current_event in event.get():
        quit_if_requested(current_event)
        if not handle_speed_key(current_event) and not handle_zoom_event(current_event):
            events.append(current_event)
    return events


def key_buttons(pressed_key: int, keys: ButtonKeys = SELECTION_KEYS) -> int:
    """The NES buttons (JoypadBtns bits) a key stands for (0 for none)."""
    buttons = 0
    for button, button_keys in keys:
        if pressed_key in button_keys:
            buttons |= button
    return buttons


def held_buttons(keys: ButtonKeys = SELECTION_KEYS) -> int:
    """The buttons held right now (GetJoypadStatus), from the keyboard state."""
    pressed = with_virtual_keys(key.get_pressed())
    buttons = 0
    for button, button_keys in keys:
        if any(pressed[button_key] for button_key in button_keys):
            buttons |= button
    return buttons


def tapped_buttons(events: Iterable[Event], keys: ButtonKeys = SELECTION_KEYS) -> int:
    """The buttons pressed in these events, which may have been let go already."""
    buttons = 0
    for current_event in events:
        if current_event.type == KEYDOWN:
            buttons |= key_buttons(current_event.key, keys)
    return buttons


def stop_at_edges(count: int) -> Callable[[int, int], int]:
    """``move`` for a one-column window of ``count`` entries: up and down stop at the first and the last entry
    (WndUpPressed on the top row, WndDownPressed on the bottom row do nothing); left and right do nothing."""
    def move(index: int, button: int) -> int:
        if button == IN_UP:
            return max(0, index - 1)
        if button == IN_DOWN:
            return min(count - 1, index + 1)
        return index
    return move


def toggle(index: int, button: int) -> int:
    """``move`` for a two-entry window where up and down both switch to the other entry."""
    return 1 - index if button in (IN_UP, IN_DOWN) else index


def run_selection(draw: Callable[[int, bool], object], index: int = 0, *,
                  move: Callable[[int, int], int],
                  keys: ButtonKeys = SELECTION_KEYS,
                  joypad: bool = False,
                  hotkeys: Mapping[int, Answer] | None = None,
                  answers: Collection[int] = ANSWER_BUTTONS,
                  hold: Collection[int] = ANSWER_BUTTONS,
                  b_index: int | None = None,
                  sound: Callable[[], object] | None = None,
                  sound_buttons: Collection[int] = ANSWER_BUTTONS,
                  cursor: BlinkingCursor | None = None) -> Answer:
    """WndDoSelect: run a selection window until A or B answers it (see the module docstring).

    :param draw: ``draw(index, cursor_visible)`` draws the window with the cursor at the entry ``index``, shown or not
        (the blink). Called when the window opens, when either changes, and once more, visible, when it is answered.
    :param index: The entry the cursor starts on.
    :param move: ``move(index, button)``: the entry a direction button (IN_UP...) moves the cursor to.
    :param keys: The keys of each button.
    :param joypad: Read the buttons like the NES (SelectionButtons) rather than key press by key press.
    :param hotkeys: Keys that answer straight away, wherever the cursor is (key press reading only).
    :param answers: The buttons that end the selection. B not in it is ignored (it only makes its sound).
    :param hold: The answers that draw the arrow one last time, on (WndUpdateCrsrPos).
    :param b_index: The entry B answers with (and its arrow is drawn on); None for the one under the cursor.
    :param sound: Plays the menu sound, for the buttons in ``sound_buttons``, after the last draw.
    :param cursor: The cursor's blink; a new one (restarted now, WndInitSelect) by default.
    :return: The button that answered (IN_A or IN_B) and the entry.
    """
    cursor = BlinkingCursor() if cursor is None else cursor
    buttons = SelectionButtons(cursor) if joypad else None
    if buttons is not None:
        buttons.open(held_buttons(keys), ticks=cursor.start_ticks)  # WndInitSelect, the joypad read from scratch
    hotkeys = hotkeys or {}
    drawn: tuple[int, bool] | None = None
    while True:
        visible = cursor.visible()
        if drawn != (index, visible):
            draw(index, visible)
            drawn = (index, visible)
        next_frame()
        events = frame_events()
        if buttons is not None:
            pressed = first_button(buttons.read(held_buttons(keys), tapped_buttons(events, keys)))
            presses: list[tuple[int, int | None]] = [(pressed, None)] if pressed else []
        else:
            presses = []
            for current_event in events:
                if current_event.type != KEYDOWN:
                    continue
                if current_event.key in hotkeys:
                    presses.append(hotkeys[current_event.key])
                else:
                    button = first_button(key_buttons(current_event.key, keys))
                    if button:
                        presses.append((button, None))
        for button, answer_index in presses:
            if buttons is not None:
                buttons.handled(button)  # STA WndBtnRetrig
            if button in ANSWER_BUTTONS:
                if button not in answers:  # ignored, but for its sound
                    if sound is not None and button in sound_buttons:
                        sound()
                    continue
                if answer_index is None:
                    answer_index = b_index if button == IN_B and b_index is not None else index
                if button in hold:
                    # WndAPressed, WndBPressed: the arrow is drawn once more and stays on
                    cursor.hold()
                    draw(answer_index, True)
                if sound is not None and button in sound_buttons:
                    sound()
                return Answer(button, answer_index)
            moved_to = move(index, button)
            if moved_to != index:
                index = moved_to
                if buttons is not None:
                    buttons.moved()  # WndUpdateCrsrPos
                else:
                    cursor.restart()
