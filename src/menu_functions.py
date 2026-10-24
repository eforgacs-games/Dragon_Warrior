from functools import partial
from collections.abc import Callable, Collection

from pygame import display, KEYDOWN, K_RETURN, K_TAB, K_BACKSPACE, K_ESCAPE
from src.waiting import game_ticks as get_ticks  # game time: runs N times as fast at speed N

from data.text.intro_lookup_table import ControlInfo
from src.calculation import Calculation
from src.color import WHITE
from src.common import DOWN_KEYS, LEFT_KEYS, RIGHT_KEYS, START_BUTTON_KEYS, UP_KEYS, accept_keys, reject_keys
from src.cursor import BlinkingCursor
from src.gamepad import is_gamepad
from src.directories import Directories
from src.name_entry import EVERY_LOG_OPEN, LogWindow, NameEntry, render_name_entry_screen
from src.selection import frame_events, next_frame
from src.sound import Sound

# The alphabet window's cursor keys, with joystick input (WndUpPressed, WndDownPressed, WndDoLeftPressed,
# WndRightPressed), as the D-pad is bound (src/controls.py)
DIRECTION_MOVES: tuple[tuple[Collection[int], Callable[[NameEntry], bool]], ...] = (
    (UP_KEYS, NameEntry.move_up), (DOWN_KEYS, NameEntry.move_down),
    (LEFT_KEYS, NameEntry.move_left), (RIGHT_KEYS, NameEntry.move_right),
)


def direction_move(pressed_key: int) -> Callable[[NameEntry], bool] | None:
    """How a direction key moves the alphabet window's cursor (None if it isn't one)."""
    return next((move for keys, move in DIRECTION_MOVES if pressed_key in keys), None)


class NameSelection:
    """The name entry screen (src/name_entry.py), drawn from the NES window data and run like WndEnterName.

    With joystick input (Tab turns it on and off; a controller's buttons, src/gamepad.py, turn it on), the keys are the
    NES buttons: the arrows move the cursor, A enters the selected character, BACK or END, and B (J) is BACK. Without
    it, typing a character of the alphabet enters it (and moves the cursor to it), Backspace removes the last one and
    Return ends the name. In either mode, Escape leaves the name entry (select_name returns None) and the new quest is
    cancelled."""

    def __init__(self, config, log_window: LogWindow | None = None):
        """``log_window``: the open logs window behind the name entry and the log chosen in it (TitleMenu.
        select_adventure_log); by default every log open and none chosen."""
        self.config = config
        self.log_window = log_window or EVERY_LOG_OPEN
        self.calculation = Calculation(config)
        self.directories = Directories(config)
        self.control_info = ControlInfo(config)
        self.sound = Sound(self.config)

    def draw(self, screen, entry: NameEntry, cursor_visible: bool | None = True) -> None:
        """Draw the whole screen (see render_name_entry_screen), in the title screen's white."""
        if not self.config['NO_BLIT']:
            screen.blit(render_name_entry_screen(entry, WHITE, self.config['TILE_SIZE'] // 16, cursor_visible,
                                                 self.log_window), (0, 0))
        display.update(screen.get_rect())

    def select_name(self, blink_start, screen, command_menu) -> str | None:
        """The name entered, or None if Escape was pressed to leave the name entry (back to the title menu)."""
        # CONFIRM NAME (not NES): a full name waits on END, and START ends the name from anywhere
        confirm = bool(self.config.get('NAME_CONFIRM'))
        entry = NameEntry(confirm)
        enable_joystick_input = False
        # No cursor until the alphabet window's selection starts (WndDoSelect)
        self.draw(screen, entry, cursor_visible=None)
        command_menu.show_line_in_dialog_box(self.control_info.input_name_prompt, letter_by_letter=False,
                                             hide_arrow=False)
        self.draw(screen, entry, cursor_visible=None)
        # The alphabet window's cursor blinks like every NES window cursor (src/cursor.py), restarting whenever it
        # moves or A or B is pressed (WndUpdateCrsrPos)
        cursor = BlinkingCursor(blink_start)
        drawn_visible: bool | None = None
        while True:
            # The whole screen is drawn again only after a key press or when the cursor blinks, one pass per NES
            # frame (src/selection.py); the keys 1 to 5 set the game speed (no letter of the alphabet is a digit)
            if cursor.visible() != drawn_visible:
                drawn_visible = cursor.visible()
                self.draw(screen, entry, drawn_visible)
            next_frame()
            for current_event in frame_events():
                if current_event.type == KEYDOWN:
                    drawn_visible = None
                    if current_event.key == K_ESCAPE:
                        # Not the NES B button here (J is): Escape cancels the name entry, back to the title menu
                        return None
                    if is_gamepad(current_event):
                        # A controller (src/gamepad.py) can't type: its buttons are joystick input, without Tab
                        enable_joystick_input = True
                    if current_event.key == K_TAB:
                        enable_joystick_input = toggle_joystick_input(
                            command_menu, partial(self.draw, screen, entry, cursor.visible()), enable_joystick_input,
                            screen)
                    if enable_joystick_input:
                        if confirm and current_event.key in START_BUTTON_KEYS:
                            # START (I, or a controller's Start) ends the name, as Return does on the keyboard. On the
                            # NES START does nothing here (WndProcessInput skips it).
                            if entry.name:
                                self.sound.play_sound(self.directories.menu_button_sfx)
                                entry.move_to_end()
                                entry.end()
                        elif current_event.key in accept_keys:
                            # WndAPressed: the menu button sound, and the selection is processed (WndProcessChar)
                            self.sound.play_sound(self.directories.menu_button_sfx)
                            entry.select()
                            cursor.restart()
                        elif current_event.key in reject_keys:
                            # WndBPressed (J; Escape cancels above): back one character, without a sound
                            entry.back()
                            cursor.restart()
                        elif (move := direction_move(current_event.key)) is not None and move(entry):
                            cursor.restart()
                    else:
                        if current_event.key == K_BACKSPACE:
                            entry.erase()
                        elif current_event.key == K_RETURN:
                            if entry.name:
                                entry.move_to_end()
                                entry.end()
                        elif entry.move_to(current_event.unicode):
                            self.sound.play_sound(self.directories.menu_button_sfx)
                            entry.enter(current_event.unicode)
                            cursor.restart()
                    if entry.finished:
                        # END or the 8th character (WndMaxNameLength): the name is done, with the arrow on (held)
                        cursor.hold()
                        self.draw(screen, entry, cursor.visible())
                        return entry.name


def get_opposite_direction(direction: int) -> int:
    """DOWN <-> UP and LEFT <-> RIGHT (the directions are numbered 0-3 around, so the opposite is 2 along)."""
    return (direction + 2) % 4


def convert_list_to_newline_separated_string(list_to_convert: list[str]) -> str:
    return '\n \n'.join([item for item in list_to_convert])


def draw_player_sprites(current_map, background, column, row, config):
    draw_character_sprites(current_map, background, column, row, config)


def draw_character_sprites(current_map, background, column, row, config, character_identifier='HERO'):
    if not config['NO_BLIT']:
        background.blit(current_map.characters[character_identifier]['character_sprites'].sprites()[0].image,
                        (column * config['TILE_SIZE'], row * config['TILE_SIZE']))


def toggle_joystick_input(command_menu, redraw: Callable[[], None], enable_joystick_input, screen):
    """Turn joystick input on or off, saying so in a dialog box, then redraw the name entry screen over it."""
    if enable_joystick_input:
        enable_joystick_input = False
        # TODO(ELF): adding the drop-up effect here shows the Tantegel Throne Room while the effect happens -
        #  make it work with a black screen.
        command_menu.show_text_in_dialog_box(command_menu._("Joystick input disabled."), temp_text_start=get_ticks(),
                                             drop_up=False)
        if not command_menu.game.game_state.config['NO_BLIT']:
            redraw()
            display.flip()
    else:
        enable_joystick_input = True
        command_menu.show_text_in_dialog_box(command_menu._("Joystick input enabled."), temp_text_start=get_ticks(),
                                             drop_up=False)
        if not command_menu.game.game_state.config['NO_BLIT']:
            redraw()
            display.flip()
    return enable_joystick_input
