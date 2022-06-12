from typing import List

from src.common import Direction, HOVERING_STATS_BACKGROUND_PATH, create_window
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
        if tile in current_map.tile_types_in_current_map:
            tile_dict['group'].draw(background)


def replace_characters_with_underlying_tiles(tile_types_to_draw: List[str], current_map_character_key) -> List[str]:
    for character in current_map_character_key.keys():
        if character in tile_types_to_draw:
            tile_types_to_draw = list(
                map(lambda x: x.replace(character, current_map_character_key[character]['underlying_tile']),
                    tile_types_to_draw))
    return tile_types_to_draw


def draw_stats_strings_with_alignments(stat_string, y_position, screen):
    if len(stat_string) >= 5:
        draw_text(stat_string, TILE_SIZE * 3.2, TILE_SIZE * y_position, screen)
    elif len(stat_string) > 4:
        draw_text(stat_string, TILE_SIZE * 3.2, TILE_SIZE * y_position, screen)
    elif len(stat_string) > 3:
        draw_text(stat_string, TILE_SIZE * 3.44, TILE_SIZE * y_position, screen)
    elif len(stat_string) > 2:
        draw_text(stat_string, TILE_SIZE * 3.67, TILE_SIZE * y_position, screen)
    elif len(stat_string) > 1:
        draw_text(stat_string, TILE_SIZE * 3.99, TILE_SIZE * y_position, screen)
    else:
        draw_text(stat_string, TILE_SIZE * 4.2, TILE_SIZE * y_position, screen)


def draw_hovering_stats_window(screen, player):
    create_window(1, 2, 4, 6, HOVERING_STATS_BACKGROUND_PATH, screen)
    draw_text(player.name[:4], TILE_SIZE * 2.99, TILE_SIZE * 2, screen)
    draw_stats_strings_with_alignments(f"{player.level}", 2.99, screen)
    draw_stats_strings_with_alignments(f"{player.current_hp}", 3.99, screen)
    draw_stats_strings_with_alignments(f"{player.current_mp}", 4.99, screen)
    draw_stats_strings_with_alignments(f"{player.gold}", 5.99, screen)
    draw_stats_strings_with_alignments(f"{player.total_experience}", 6.99, screen)
