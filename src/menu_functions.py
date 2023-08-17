import re
from typing import List

from pygame import display, QUIT, quit, KEYDOWN, K_RETURN, K_j, K_DOWN, K_s, K_UP, K_w, K_LEFT, K_a, K_RIGHT, K_d, \
    image, K_TAB, K_BACKSPACE, Rect, event
from pygame.time import get_ticks
from pygame.transform import scale

from data.text.intro_lookup_table import ControlInfo
from src.calculation import Calculation
from src.common import accept_keys
from src.directories import Directories
from src.sound import Sound
from src.text import draw_text


class NameSelection:
    def __init__(self, config):
        self.config = config
        self.calculation = Calculation(config)
        self.directories = Directories(config)
        self.control_info = ControlInfo(config)
        self.sound = Sound(self.config)
        self.name_selection_grid = (
            ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"),
            ("L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V"),
            ("W", "X", "Y", "Z", "-", "'", "!", "?", "(", ")", " "),
            ("a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k"),
            ("l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v"),
            ("w", "x", "y", "z", ",", ".", "1", "1", "0", "0", "0")
        )
        self.name_selection_image_lookup = {
            "A": self.directories.NAME_SELECTION_UPPER_A,
            "B": self.directories.NAME_SELECTION_UPPER_B,
            "C": self.directories.NAME_SELECTION_UPPER_C,
            "D": self.directories.NAME_SELECTION_UPPER_D,
            "E": self.directories.NAME_SELECTION_UPPER_E,
            "F": self.directories.NAME_SELECTION_UPPER_F,
            "G": self.directories.NAME_SELECTION_UPPER_G,
            "H": self.directories.NAME_SELECTION_UPPER_H,
            "I": self.directories.NAME_SELECTION_UPPER_I,
            "J": self.directories.NAME_SELECTION_UPPER_J,
            "K": self.directories.NAME_SELECTION_UPPER_K,
            "L": self.directories.NAME_SELECTION_UPPER_L,
            "M": self.directories.NAME_SELECTION_UPPER_M,
            "N": self.directories.NAME_SELECTION_UPPER_N,
            "O": self.directories.NAME_SELECTION_UPPER_O,
            "P": self.directories.NAME_SELECTION_UPPER_P,
            "Q": self.directories.NAME_SELECTION_UPPER_Q,
            "R": self.directories.NAME_SELECTION_UPPER_R,
            "S": self.directories.NAME_SELECTION_UPPER_S,
            "T": self.directories.NAME_SELECTION_UPPER_T,
            "U": self.directories.NAME_SELECTION_UPPER_U,
            "V": self.directories.NAME_SELECTION_UPPER_V,
            "W": self.directories.NAME_SELECTION_UPPER_W,
            "X": self.directories.NAME_SELECTION_UPPER_X,
            "Y": self.directories.NAME_SELECTION_UPPER_Y,
            "Z": self.directories.NAME_SELECTION_UPPER_Z,
            "-": self.directories.NAME_SELECTION_HYPHEN,
            "'": self.directories.NAME_SELECTION_SINGLE_QUOTE,
            "!": self.directories.NAME_SELECTION_EXCLAMATION_POINT,
            "?": self.directories.NAME_SELECTION_QUESTION_MARK,
            "(": self.directories.NAME_SELECTION_OPEN_PARENTHESIS,
            ")": self.directories.NAME_SELECTION_CLOSE_PARENTHESIS,
            " ": self.directories.NAME_SELECTION_SPACE,
            "a": self.directories.NAME_SELECTION_LOWER_A,
            "b": self.directories.NAME_SELECTION_LOWER_B,
            "c": self.directories.NAME_SELECTION_LOWER_C,
            "d": self.directories.NAME_SELECTION_LOWER_D,
            "e": self.directories.NAME_SELECTION_LOWER_E,
            "f": self.directories.NAME_SELECTION_LOWER_F,
            "g": self.directories.NAME_SELECTION_LOWER_G,
            "h": self.directories.NAME_SELECTION_LOWER_H,
            "i": self.directories.NAME_SELECTION_LOWER_I,
            "j": self.directories.NAME_SELECTION_LOWER_J,
            "k": self.directories.NAME_SELECTION_LOWER_K,
            "l": self.directories.NAME_SELECTION_LOWER_L,
            "m": self.directories.NAME_SELECTION_LOWER_M,
            "n": self.directories.NAME_SELECTION_LOWER_N,
            "o": self.directories.NAME_SELECTION_LOWER_O,
            "p": self.directories.NAME_SELECTION_LOWER_P,
            "q": self.directories.NAME_SELECTION_LOWER_Q,
            "r": self.directories.NAME_SELECTION_LOWER_R,
            "s": self.directories.NAME_SELECTION_LOWER_S,
            "t": self.directories.NAME_SELECTION_LOWER_T,
            "u": self.directories.NAME_SELECTION_LOWER_U,
            "v": self.directories.NAME_SELECTION_LOWER_V,
            "w": self.directories.NAME_SELECTION_LOWER_W,
            "x": self.directories.NAME_SELECTION_LOWER_X,
            "y": self.directories.NAME_SELECTION_LOWER_Y,
            "z": self.directories.NAME_SELECTION_LOWER_Z,
            ",": self.directories.NAME_SELECTION_COMMA,
            ".": self.directories.NAME_SELECTION_PERIOD,
            "1": self.directories.NAME_SELECTION_BACK,
            "0": self.directories.NAME_SELECTION_END,

        }

    def select_name(self, blink_start, screen, command_menu):
        current_item_row = 0
        current_item_column = 0
        blinking = True
        name = ""
        enable_joystick_input = False
        unselected_image = scale(image.load(self.directories.NAME_SELECTION_STATIC_IMAGE_LEN_0),
                                 (screen.get_width(), screen.get_height()))
        screen.blit(unselected_image, (0, 0)) if not self.config['NO_BLIT'] else None
        display.update(unselected_image.get_rect())
        command_menu.show_line_in_dialog_box(self.control_info.input_name_prompt, letter_by_letter=False,
                                             hide_arrow=False)
        screen.blit(unselected_image, (0, 0)) if not self.config['NO_BLIT'] else None
        display.update(unselected_image.get_rect())
        selected_image_lookup = {
            0: self.directories.NAME_SELECTION_STATIC_IMAGE_LEN_0,
            1: self.directories.NAME_SELECTION_STATIC_IMAGE_LEN_1,
            2: self.directories.NAME_SELECTION_STATIC_IMAGE_LEN_2,
            3: self.directories.NAME_SELECTION_STATIC_IMAGE_LEN_3,
            4: self.directories.NAME_SELECTION_STATIC_IMAGE_LEN_4,
            5: self.directories.NAME_SELECTION_STATIC_IMAGE_LEN_5,
            6: self.directories.NAME_SELECTION_STATIC_IMAGE_LEN_6,
            7: self.directories.NAME_SELECTION_STATIC_IMAGE_LEN_7,
            8: self.directories.NAME_SELECTION_STATIC_IMAGE_LEN_8,
        }
        while blinking:
            name = truncate_name(name)
            current_letter = self.name_selection_grid[current_item_row][current_item_column]
            current_letter_image_path = self.name_selection_image_lookup[current_letter]
            unselected_image = selected_image_lookup[len(name)]
            # screen.fill(BLACK)
            blink_start = self.reset_blink_start(blink_start)
            blink_with_name(blink_start, current_letter_image_path, name, screen, unselected_image, self.config)
            for current_event in event.get():
                if current_event.type == QUIT:
                    quit()
                elif current_event.type == KEYDOWN:
                    if current_event.key == K_TAB:
                        enable_joystick_input = toggle_joystick_input(command_menu, current_letter_image_path,
                                                                      enable_joystick_input, screen)
                    if enable_joystick_input:
                        if current_event.key in accept_keys:
                            self.sound.play_sound(self.directories.menu_button_sfx)
                            if current_letter == "0":
                                return name
                            elif current_letter == "1":
                                # back up cursor instead of deleting letters
                                name = name[:-1]
                            else:
                                name += current_letter
                        elif current_event.key == K_j:
                            # back up cursor instead of deleting letters
                            name = name[:-1]
                        elif current_event.key in (K_DOWN, K_s) and current_item_row + 1 < len(
                                self.name_selection_grid):
                            current_item_row += 1
                        elif current_event.key in (K_UP, K_w) and current_item_row > 0:
                            current_item_row -= 1
                        elif current_event.key in (K_LEFT, K_a) and current_item_column > 0:
                            current_item_column -= 1
                        elif current_event.key in (K_RIGHT, K_d) and current_item_column < len(
                                self.name_selection_grid[current_item_row]) - 1:
                            current_item_column += 1
                    else:
                        if current_event.key == K_BACKSPACE:
                            name = name[:-1]
                        elif current_event.key == K_RETURN:
                            if name:
                                current_letter = self.name_selection_grid[len(self.name_selection_grid) - 1][
                                    len(self.name_selection_grid[current_item_row]) - 1]
                                current_letter_image_path = self.name_selection_image_lookup[current_letter]
                                draw_image_with_name(current_letter_image_path, name, screen, self.config)
                                return name
                        elif any(current_event.unicode in sublist for sublist in
                                 self.name_selection_grid) and current_event.unicode not in ("0", "1"):
                            self.sound.play_sound(self.directories.menu_button_sfx)
                            name += current_event.unicode
                            current_item_coordinates = [(ix, iy) for ix, row in enumerate(self.name_selection_grid) for
                                                        iy, i in
                                                        enumerate(row) if
                                                        i == current_event.unicode]
                            current_item_row = current_item_coordinates[0][0]
                            current_item_column = current_item_coordinates[0][1]

    def reset_blink_start(self, blink_start):
        if self.calculation.convert_to_frames_since_start_time(blink_start) > 32:
            blink_start = get_ticks()
        return blink_start


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


def toggle_joystick_input(command_menu, current_letter_image_path, enable_joystick_input, screen):
    if enable_joystick_input:
        enable_joystick_input = False
        # TODO(ELF): adding the drop-up effect here shows the Tantegel Throne Room while the effect happens -
        #  make it work with a black screen.
        command_menu.show_text_in_dialog_box("Joystick input disabled.", temp_text_start=get_ticks(), drop_up=False)
        if not command_menu.game.game_state.config['NO_BLIT']:
            screen.blit(scale(image.load(current_letter_image_path), (screen.get_width(), screen.get_height())), (0, 0))
            display.flip()
    else:
        enable_joystick_input = True
        command_menu.show_text_in_dialog_box("Joystick input enabled.", temp_text_start=get_ticks(), drop_up=False)
        if not command_menu.game.game_state.config['NO_BLIT']:
            screen.blit(scale(image.load(current_letter_image_path), (screen.get_width(), screen.get_height())), (0, 0))
            display.flip()
    return enable_joystick_input


def truncate_name(name):
    if len(name) > 8:
        last_char = name[-1]
        name = re.sub(r".$", last_char, name[:8])
    return name


def blink_with_name(blink_start, current_letter_image_path, name, screen, static_image, config):
    calculation = Calculation(config)
    if calculation.convert_to_frames_since_start_time(blink_start) <= 16:
        draw_image_with_name(current_letter_image_path, name, screen, config)
    elif 16 < calculation.convert_to_frames_since_start_time(blink_start) <= 32:
        draw_image_with_name(static_image, name, screen, config)
    display.update(
        Rect(screen.get_rect().left, screen.get_rect().centerx // 1.7, screen.get_width(), screen.get_height() * .46))


def draw_image_with_name(current_letter_image_path, name, screen, config):
    selected_image = scale(image.load(current_letter_image_path), (screen.get_width(), screen.get_height()))
    screen.blit(selected_image, (0, 0)) if not config['NO_BLIT'] else None
    draw_text(name, config['TILE_SIZE'] * 6.01, config['TILE_SIZE'] * 4.3, screen, config, alignment='left',
              letter_by_letter=False)
