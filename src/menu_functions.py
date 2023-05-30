import re
import sys
from typing import List

from pygame import display, QUIT, quit, KEYDOWN, K_RETURN, K_i, K_k, K_j, K_DOWN, K_s, K_UP, K_w, K_LEFT, K_a, K_RIGHT, K_d, image, K_TAB, K_BACKSPACE, Rect, \
    event
from pygame.time import get_ticks
from pygame.transform import scale

from data.text.intro_lookup_table import input_name_prompt
from src.common import NAME_SELECTION_UPPER_A, NAME_SELECTION_UPPER_B, NAME_SELECTION_UPPER_C, NAME_SELECTION_UPPER_D, NAME_SELECTION_UPPER_E, \
    NAME_SELECTION_UPPER_F, NAME_SELECTION_UPPER_G, NAME_SELECTION_UPPER_H, NAME_SELECTION_UPPER_I, NAME_SELECTION_UPPER_J, NAME_SELECTION_UPPER_K, \
    NAME_SELECTION_UPPER_L, NAME_SELECTION_UPPER_M, NAME_SELECTION_UPPER_N, NAME_SELECTION_UPPER_O, NAME_SELECTION_UPPER_P, NAME_SELECTION_UPPER_Q, \
    NAME_SELECTION_UPPER_R, NAME_SELECTION_UPPER_S, NAME_SELECTION_UPPER_T, NAME_SELECTION_UPPER_U, NAME_SELECTION_UPPER_V, NAME_SELECTION_UPPER_W, \
    NAME_SELECTION_UPPER_X, NAME_SELECTION_UPPER_Y, NAME_SELECTION_UPPER_Z, NAME_SELECTION_HYPHEN, NAME_SELECTION_SINGLE_QUOTE, \
    NAME_SELECTION_EXCLAMATION_POINT, NAME_SELECTION_QUESTION_MARK, NAME_SELECTION_OPEN_PARENTHESIS, NAME_SELECTION_CLOSE_PARENTHESIS, NAME_SELECTION_SPACE, \
    NAME_SELECTION_LOWER_A, NAME_SELECTION_LOWER_B, NAME_SELECTION_LOWER_C, NAME_SELECTION_LOWER_D, NAME_SELECTION_LOWER_E, NAME_SELECTION_LOWER_F, \
    NAME_SELECTION_LOWER_G, NAME_SELECTION_LOWER_H, NAME_SELECTION_LOWER_I, NAME_SELECTION_LOWER_J, NAME_SELECTION_LOWER_K, NAME_SELECTION_LOWER_L, \
    NAME_SELECTION_LOWER_M, NAME_SELECTION_LOWER_N, NAME_SELECTION_LOWER_O, NAME_SELECTION_LOWER_P, NAME_SELECTION_LOWER_Q, NAME_SELECTION_LOWER_R, \
    NAME_SELECTION_LOWER_S, NAME_SELECTION_LOWER_T, NAME_SELECTION_LOWER_U, NAME_SELECTION_LOWER_V, NAME_SELECTION_LOWER_W, NAME_SELECTION_LOWER_X, \
    NAME_SELECTION_LOWER_Y, NAME_SELECTION_LOWER_Z, NAME_SELECTION_COMMA, NAME_SELECTION_PERIOD, NAME_SELECTION_BACK, NAME_SELECTION_END, \
    convert_to_frames_since_start_time, play_sound, menu_button_sfx, NAME_SELECTION_STATIC_IMAGE_LEN_0, NAME_SELECTION_STATIC_IMAGE_LEN_1, \
    NAME_SELECTION_STATIC_IMAGE_LEN_2, NAME_SELECTION_STATIC_IMAGE_LEN_3, NAME_SELECTION_STATIC_IMAGE_LEN_4, NAME_SELECTION_STATIC_IMAGE_LEN_5, \
    NAME_SELECTION_STATIC_IMAGE_LEN_6, NAME_SELECTION_STATIC_IMAGE_LEN_7, NAME_SELECTION_STATIC_IMAGE_LEN_8
from src.text import draw_text

name_selection_array = (
    ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"),
    ("L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V"),
    ("W", "X", "Y", "Z", "-", "'", "!", "?", "(", ")", " "),
    ("a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k"),
    ("l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v"),
    ("w", "x", "y", "z", ",", ".", "1", "1", "0", "0", "0")
)

name_selection_image_lookup = {
    "A": NAME_SELECTION_UPPER_A,
    "B": NAME_SELECTION_UPPER_B,
    "C": NAME_SELECTION_UPPER_C,
    "D": NAME_SELECTION_UPPER_D,
    "E": NAME_SELECTION_UPPER_E,
    "F": NAME_SELECTION_UPPER_F,
    "G": NAME_SELECTION_UPPER_G,
    "H": NAME_SELECTION_UPPER_H,
    "I": NAME_SELECTION_UPPER_I,
    "J": NAME_SELECTION_UPPER_J,
    "K": NAME_SELECTION_UPPER_K,
    "L": NAME_SELECTION_UPPER_L,
    "M": NAME_SELECTION_UPPER_M,
    "N": NAME_SELECTION_UPPER_N,
    "O": NAME_SELECTION_UPPER_O,
    "P": NAME_SELECTION_UPPER_P,
    "Q": NAME_SELECTION_UPPER_Q,
    "R": NAME_SELECTION_UPPER_R,
    "S": NAME_SELECTION_UPPER_S,
    "T": NAME_SELECTION_UPPER_T,
    "U": NAME_SELECTION_UPPER_U,
    "V": NAME_SELECTION_UPPER_V,
    "W": NAME_SELECTION_UPPER_W,
    "X": NAME_SELECTION_UPPER_X,
    "Y": NAME_SELECTION_UPPER_Y,
    "Z": NAME_SELECTION_UPPER_Z,
    "-": NAME_SELECTION_HYPHEN,
    "'": NAME_SELECTION_SINGLE_QUOTE,
    "!": NAME_SELECTION_EXCLAMATION_POINT,
    "?": NAME_SELECTION_QUESTION_MARK,
    "(": NAME_SELECTION_OPEN_PARENTHESIS,
    ")": NAME_SELECTION_CLOSE_PARENTHESIS,
    " ": NAME_SELECTION_SPACE,
    "a": NAME_SELECTION_LOWER_A,
    "b": NAME_SELECTION_LOWER_B,
    "c": NAME_SELECTION_LOWER_C,
    "d": NAME_SELECTION_LOWER_D,
    "e": NAME_SELECTION_LOWER_E,
    "f": NAME_SELECTION_LOWER_F,
    "g": NAME_SELECTION_LOWER_G,
    "h": NAME_SELECTION_LOWER_H,
    "i": NAME_SELECTION_LOWER_I,
    "j": NAME_SELECTION_LOWER_J,
    "k": NAME_SELECTION_LOWER_K,
    "l": NAME_SELECTION_LOWER_L,
    "m": NAME_SELECTION_LOWER_M,
    "n": NAME_SELECTION_LOWER_N,
    "o": NAME_SELECTION_LOWER_O,
    "p": NAME_SELECTION_LOWER_P,
    "q": NAME_SELECTION_LOWER_Q,
    "r": NAME_SELECTION_LOWER_R,
    "s": NAME_SELECTION_LOWER_S,
    "t": NAME_SELECTION_LOWER_T,
    "u": NAME_SELECTION_LOWER_U,
    "v": NAME_SELECTION_LOWER_V,
    "w": NAME_SELECTION_LOWER_W,
    "x": NAME_SELECTION_LOWER_X,
    "y": NAME_SELECTION_LOWER_Y,
    "z": NAME_SELECTION_LOWER_Z,
    ",": NAME_SELECTION_COMMA,
    ".": NAME_SELECTION_PERIOD,
    "1": NAME_SELECTION_BACK,
    "0": NAME_SELECTION_END,

}


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


def select_name(blink_start, screen, command_menu, config):
    current_item_row = 0
    current_item_column = 0
    blinking = True
    name = ""
    enable_joystick_input = False
    unselected_image = scale(image.load(NAME_SELECTION_STATIC_IMAGE_LEN_0), (screen.get_width(), screen.get_height()))
    screen.blit(unselected_image, (0, 0)) if not config['NO_BLIT'] else None
    display.update(unselected_image.get_rect())
    command_menu.show_text_in_dialog_box(input_name_prompt, drop_down=False, drop_up=False, letter_by_letter=False)
    screen.blit(unselected_image, (0, 0)) if not config['NO_BLIT'] else None
    display.update(unselected_image.get_rect())
    selected_image_lookup = {
        0: NAME_SELECTION_STATIC_IMAGE_LEN_0,
        1: NAME_SELECTION_STATIC_IMAGE_LEN_1,
        2: NAME_SELECTION_STATIC_IMAGE_LEN_2,
        3: NAME_SELECTION_STATIC_IMAGE_LEN_3,
        4: NAME_SELECTION_STATIC_IMAGE_LEN_4,
        5: NAME_SELECTION_STATIC_IMAGE_LEN_5,
        6: NAME_SELECTION_STATIC_IMAGE_LEN_6,
        7: NAME_SELECTION_STATIC_IMAGE_LEN_7,
        8: NAME_SELECTION_STATIC_IMAGE_LEN_8,
    }
    while blinking:
        name = truncate_name(name)
        current_letter = name_selection_array[current_item_row][current_item_column]
        current_letter_image_path = name_selection_image_lookup[current_letter]
        unselected_image = selected_image_lookup[len(name)]
        # screen.fill(BLACK)
        blink_start = reset_blink_start(blink_start)
        blink_with_name(blink_start, current_letter_image_path, name, screen, unselected_image, config)
        for current_event in event.get():
            if current_event.type == QUIT:
                quit()
                sys.exit()
            elif current_event.type == KEYDOWN:
                if current_event.key == K_TAB:
                    enable_joystick_input = toggle_joystick_input(command_menu, current_letter_image_path, enable_joystick_input, screen)
                if enable_joystick_input:
                    if current_event.key in (K_RETURN, K_i, K_k):
                        play_sound(menu_button_sfx)
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
                    elif current_event.key in (K_DOWN, K_s) and current_item_row + 1 < len(name_selection_array):
                        current_item_row += 1
                    elif current_event.key in (K_UP, K_w) and current_item_row > 0:
                        current_item_row -= 1
                    elif current_event.key in (K_LEFT, K_a) and current_item_column > 0:
                        current_item_column -= 1
                    elif current_event.key in (K_RIGHT, K_d) and current_item_column < len(name_selection_array[current_item_row]) - 1:
                        current_item_column += 1
                else:
                    if current_event.key == K_BACKSPACE:
                        name = name[:-1]
                    elif current_event.key == K_RETURN:
                        if name:
                            current_letter = name_selection_array[len(name_selection_array) - 1][len(name_selection_array[current_item_row]) - 1]
                            current_letter_image_path = name_selection_image_lookup[current_letter]
                            draw_image_with_name(current_letter_image_path, name, screen, config)
                            return name
                    elif any(current_event.unicode in sublist for sublist in name_selection_array) and current_event.unicode not in ("0", "1"):
                        play_sound(menu_button_sfx)
                        name += current_event.unicode
                        current_item_coordinates = [(ix, iy) for ix, row in enumerate(name_selection_array) for iy, i in enumerate(row) if
                                                    i == current_event.unicode]
                        current_item_row = current_item_coordinates[0][0]
                        current_item_column = current_item_coordinates[0][1]


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


def reset_blink_start(blink_start):
    if convert_to_frames_since_start_time(blink_start) > 32:
        blink_start = get_ticks()
    return blink_start


def truncate_name(name):
    if len(name) > 8:
        last_char = name[-1]
        name = re.sub(r".$", last_char, name[:8])
    return name


def blink_with_name(blink_start, current_letter_image_path, name, screen, static_image, config):
    if convert_to_frames_since_start_time(blink_start) <= 16:
        draw_image_with_name(current_letter_image_path, name, screen, config)
    elif 16 < convert_to_frames_since_start_time(blink_start) <= 32:
        draw_image_with_name(static_image, name, screen, config)
    display.update(Rect(screen.get_rect().left, screen.get_rect().centerx // 1.7, screen.get_width(), screen.get_height() * .46))


def draw_image_with_name(current_letter_image_path, name, screen, config):
    selected_image = scale(image.load(current_letter_image_path), (screen.get_width(), screen.get_height()))
    screen.blit(selected_image, (0, 0)) if not config['NO_BLIT'] else None
    draw_text(name, config['TILE_SIZE'] * 6.01, config['TILE_SIZE'] * 4.3, screen, config, alignment='left',
              letter_by_letter=False)
