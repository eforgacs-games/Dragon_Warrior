from typing import List

from src.common import Direction
from src.config import TILE_SIZE


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
