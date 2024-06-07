from pygame.time import get_ticks

from src.direction import Direction


class Calculation:
    def __init__(self, config):
        self.config = config

    def convert_to_frames(self, time_to_convert: int) -> int:
        return self.config["FPS"] * time_to_convert / 1000

    def convert_to_milliseconds(self, fps_to_convert: int) -> int:
        return fps_to_convert / self.config["FPS"] * 1000

    @staticmethod
    def get_next_tile_identifier(character_column: int, character_row: int, direction_value: int, current_map,
                                 offset: int = 1) -> str:
        """
        Retrieve the identifier (human-readable name) of the next tile in front of a particular character.
        :type character_column: int
        :type character_row: int
        :param character_column: The character's column within the map layout.
        :param character_row: The character's row within the map layout.
        :param direction_value: The direction which the character is facing.
        :param current_map: The current map class.
        :param offset: How many tiles offset of the character to check. Defaults to 1 (the next tile).
        :return: str: The next tile that the character will step on (e.g., 'BRICK').
        """
        if direction_value == Direction.UP.value:
            return get_tile_id_by_coordinates(character_column, character_row - offset, current_map)
        elif direction_value == Direction.DOWN.value:
            return get_tile_id_by_coordinates(character_column, character_row + offset, current_map)
        elif direction_value == Direction.LEFT.value:
            return get_tile_id_by_coordinates(character_column - offset, character_row, current_map)
        elif direction_value == Direction.RIGHT.value:
            return get_tile_id_by_coordinates(character_column + offset, character_row, current_map)

    def convert_to_frames_since_start_time(self, start_time):
        return self.convert_to_frames(get_ticks() - start_time)

    @staticmethod
    def get_distance_from_tantegel(column, row):
        # Tantegel Castle is located at (51, 50)
        return column - 51,  row - 50


def get_tile_id_by_coordinates(column: int, row: int, game_map) -> str:
    """
    Retrieve the tile name from the coordinates of the tile on the map.
    :param column: The column of the tile.
    :param row: The row of the tile.
    @rtype: str
    """
    if row < len(game_map.layout) and column < len(game_map.layout[0]):
        return game_map.get_tile_by_value(game_map.layout[row][column])
