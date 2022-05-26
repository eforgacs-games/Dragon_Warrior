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
