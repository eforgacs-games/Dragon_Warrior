from functools import partial
from typing import Callable, List

from pygame import display, KEYDOWN, K_RETURN, K_DOWN, K_s, K_UP, K_w, K_LEFT, K_a, K_RIGHT, K_d, \
    K_TAB, K_BACKSPACE, K_ESCAPE, event
from src.waiting import game_ticks as get_ticks  # game time: runs N times as fast at speed N
from src.waiting import quit_if_requested

from data.text.intro_lookup_table import ControlInfo
from src.calculation import Calculation
from src.color import WHITE
from src.common import accept_keys, reject_keys
from src.cursor import BlinkingCursor
from src.directories import Directories
from src.name_entry import NameEntry, render_name_entry_screen
from src.sound import Sound

# The alphabet window's cursor keys, with joystick input (WndUpPressed, WndDownPressed, WndDoLeftPressed,
# WndRightPressed)
DIRECTION_KEYS: dict[int, Callable[[NameEntry], bool]] = {
    K_UP: NameEntry.move_up, K_w: NameEntry.move_up,
    K_DOWN: NameEntry.move_down, K_s: NameEntry.move_down,
    K_LEFT: NameEntry.move_left, K_a: NameEntry.move_left,
    K_RIGHT: NameEntry.move_right, K_d: NameEntry.move_right,
}


class NameSelection:
    """The name entry screen (src/name_entry.py), drawn from the NES window data and run like WndEnterName.

    With joystick input (Tab turns it on and off), the keys are the NES buttons: the arrows move the cursor, A enters
    the selected character, BACK or END, and B (J) is BACK. Without it, typing a character of the alphabet enters it (and
    moves the cursor to it), Backspace removes the last one and Return ends the name. In either mode, Escape leaves the
    name entry (select_name returns None) and the new quest is cancelled."""

    def __init__(self, config):
        self.config = config
        self.calculation = Calculation(config)
        self.directories = Directories(config)
        self.control_info = ControlInfo(config)
        self.sound = Sound(self.config)

    def draw(self, screen, entry: NameEntry, cursor_visible: bool | None = True) -> None:
        """Draw the whole screen (see render_name_entry_screen), in the title screen's white."""
        if not self.config['NO_BLIT']:
            screen.blit(render_name_entry_screen(entry, WHITE, self.config['TILE_SIZE'] // 16, cursor_visible), (0, 0))
        display.update(screen.get_rect())

    def select_name(self, blink_start, screen, command_menu) -> str | None:
        """The name entered, or None if Escape was pressed to leave the name entry (back to the title menu)."""
        entry = NameEntry()
        enable_joystick_input = False
        # No cursor until the alphabet window's selection starts (WndDoSelect)
        self.draw(screen, entry, cursor_visible=None)
        command_menu.show_line_in_dialog_box(self.control_info.input_name_prompt, letter_by_letter=False,
                                             hide_arrow=False)
        self.draw(screen, entry, cursor_visible=None)
        # The alphabet window's cursor blinks like every NES window cursor (src/cursor.py), restarting whenever it
        # moves or A or B is pressed (WndUpdateCrsrPos)
        cursor = BlinkingCursor(blink_start)
        while True:
            self.draw(screen, entry, cursor.visible())
            for current_event in event.get():
                quit_if_requested(current_event)
                if current_event.type == KEYDOWN:
                    if current_event.key == K_ESCAPE:
                        # Not the NES B button here (J is): Escape cancels the name entry, back to the title menu
                        return None
                    if current_event.key == K_TAB:
                        enable_joystick_input = toggle_joystick_input(
                            command_menu, partial(self.draw, screen, entry, cursor.visible()), enable_joystick_input,
                            screen)
                    if enable_joystick_input:
                        if current_event.key in accept_keys:
                            # WndAPressed: the menu button sound, and the selection is processed (WndProcessChar)
                            self.sound.play_sound(self.directories.menu_button_sfx)
                            entry.select()
                            cursor.restart()
                        elif current_event.key in reject_keys:
                            # WndBPressed (J; Escape cancels above): back one character, without a sound
                            entry.back()
                            cursor.restart()
                        elif current_event.key in DIRECTION_KEYS and DIRECTION_KEYS[current_event.key](entry):
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
    if direction >= 2:
        return direction - 2
    else:
        return direction + 2


def convert_list_to_newline_separated_string(list_to_convert: List[str]) -> str:
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
