from typing import List

from src.config import TILE_SIZE


def get_opposite_direction(direction: int) -> int:
    if direction >= 2:
        return direction - 2
    else:
        return direction + 2


def convert_list_to_newline_separated_string(list_to_convert: List[str]) -> str:
    return '\n \n'.join([item for item in list_to_convert])


def draw_player_sprites(current_map, background, column, row):
    draw_character_sprites(current_map, background, column, row)


def draw_character_sprites(current_map, background, column, row, character_identifier='HERO'):
    background.blit(current_map.characters[character_identifier]['character_sprites'].sprites()[0].image,
                    (column * TILE_SIZE, row * TILE_SIZE))
