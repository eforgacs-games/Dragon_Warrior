from pygame import K_i, K_k, K_DOWN, K_s, K_UP, K_w, K_RETURN, KEYDOWN, event, Rect
from pygame.time import get_ticks

from src.common import Direction, BLACK, \
    convert_to_frames_since_start_time, play_sound, menu_button_sfx
from src.config import TILE_SIZE
from src.drawer import Drawer


def set_character_position(character):
    character.column, character.row = character.rect.x // TILE_SIZE, character.rect.y // TILE_SIZE


def get_next_coordinates(character_column, character_row, direction, offset_from_character=1):
    match direction:
        case Direction.UP.value:
            return character_row - offset_from_character, character_column
        case Direction.DOWN.value:
            return character_row + offset_from_character, character_column
        case Direction.LEFT.value:
            return character_row, character_column - offset_from_character
        case Direction.RIGHT.value:
            return character_row, character_column + offset_from_character


def select_from_vertical_menu(blink_start, screen, unselected_image, selected_image, other_selected_images):
    # TODO(ELF): very similar to open_store_inventory() - maybe try to merge them if you can
    current_item_index = 0
    if other_selected_images:
        all_selected_images = [selected_image] + other_selected_images
    else:
        all_selected_images = [selected_image]
    blinking = True
    while blinking:
        screen.fill(BLACK)
        if convert_to_frames_since_start_time(blink_start) > 32:
            blink_start = get_ticks()
        Drawer.alternate_blink(all_selected_images[current_item_index], unselected_image, blink_start, screen)
        for current_event in event.get():
            if current_event.type == KEYDOWN:
                if current_event.key in (K_RETURN, K_i, K_k):
                    play_sound(menu_button_sfx)
                    return current_item_index
                elif current_event.key in (K_DOWN, K_s) and current_item_index < len(all_selected_images) - 1:
                    current_item_index += 1
                    blink_start = get_ticks()
                elif current_event.key in (K_UP, K_w) and current_item_index > 0:
                    current_item_index -= 1
                    blink_start = get_ticks()


def get_surrounding_rect(character):
    left = character.rect.left - TILE_SIZE
    top = character.rect.top - TILE_SIZE
    return Rect(left, top, TILE_SIZE * 2.04, TILE_SIZE * 2.04)
