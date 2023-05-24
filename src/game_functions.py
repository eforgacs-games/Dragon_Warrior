from typing import List

from pygame import image, display, K_i, K_k, K_DOWN, K_s, K_UP, K_w, K_RETURN, KEYDOWN, event, Rect
from pygame.time import get_ticks
from pygame.transform import scale

from src.common import Direction, HOVERING_STATS_BACKGROUND_PATH, create_window, BLACK, \
    convert_to_frames_since_start_time, play_sound, menu_button_sfx, RED, WHITE
from src.config import TILE_SIZE
from src.text import draw_text


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


def draw_all_tiles_in_current_map(current_map, background) -> None:
    for tile, tile_dict in current_map.floor_tile_key.items():
        if tile in current_map.tile_types_in_current_map and tile_dict.get('group'):
            tile_dict['group'].draw(background)


def replace_characters_with_underlying_tiles(tile_types_to_draw: List[str], current_map_character_key) -> List[str]:
    for character in current_map_character_key.keys():
        if character in tile_types_to_draw:
            tile_types_to_draw = list(
                map(lambda x: x.replace(character, current_map_character_key[character]['underlying_tile']),
                    tile_types_to_draw))
    return tile_types_to_draw


def draw_stats_strings_with_alignments(stat_string, y_position, screen, color=WHITE):
    if len(stat_string) > 4:
        draw_text(stat_string, TILE_SIZE * 3.2, TILE_SIZE * y_position, screen, color=color, alignment='center', letter_by_letter=False)
    elif len(stat_string) > 3:
        draw_text(stat_string, TILE_SIZE * 3.44, TILE_SIZE * y_position, screen, color=color, alignment='center', letter_by_letter=False)
    elif len(stat_string) > 2:
        draw_text(stat_string, TILE_SIZE * 3.67, TILE_SIZE * y_position, screen, color=color, alignment='center', letter_by_letter=False)
    elif len(stat_string) > 1:
        draw_text(stat_string, TILE_SIZE * 3.99, TILE_SIZE * y_position, screen, color=color, alignment='center', letter_by_letter=False)
    else:
        draw_text(stat_string, TILE_SIZE * 4.2, TILE_SIZE * y_position, screen, color=color, alignment='center', letter_by_letter=False)


def draw_hovering_stats_window(screen, player, color=WHITE):
    create_window(1, 2, 4, 6, HOVERING_STATS_BACKGROUND_PATH, screen, color)
    draw_text(player.name[:4], TILE_SIZE * 2.99, TILE_SIZE * 2, screen, color=color, alignment='center', letter_by_letter=False)
    draw_stats_strings_with_alignments(f"{player.level}", 2.99, screen, color=color)
    draw_stats_strings_with_alignments(f"{player.current_hp}", 3.99, screen, color=color)
    draw_stats_strings_with_alignments(f"{player.current_mp}", 4.99, screen, color=color)
    draw_stats_strings_with_alignments(f"{player.gold}", 5.99, screen, color=color)
    draw_stats_strings_with_alignments(f"{player.total_experience}", 6.99, screen, color=color)


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
        alternate_blink(all_selected_images[current_item_index], unselected_image, blink_start, screen)
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


def alternate_blink(image_1, image_2, right_arrow_start, screen):
    while convert_to_frames_since_start_time(right_arrow_start) <= 16:
        selected_image = scale(image.load(image_1), (screen.get_width(), screen.get_height()))
        screen.blit(selected_image, (0, 0))
        # draw_text(">BEGIN A NEW QUEST", screen.get_width() / 2, screen.get_height() / 3, self.screen)
        display.update(selected_image.get_rect())
    while 16 < convert_to_frames_since_start_time(right_arrow_start) <= 32:
        unselected_image = scale(image.load(image_2), (screen.get_width(), screen.get_height()))
        screen.blit(unselected_image, (0, 0))
        # draw_text(" BEGIN A NEW QUEST", screen.get_width() / 2, screen.get_height() / 3, self.screen)
        display.update(unselected_image.get_rect())


def get_surrounding_rect(character):
    left = character.rect.left - TILE_SIZE
    top = character.rect.top - TILE_SIZE
    return Rect(left, top, TILE_SIZE * 2.04, TILE_SIZE * 2.04)
