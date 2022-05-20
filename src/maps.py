import inspect
import sys
from abc import ABC
from typing import Tuple

import numpy as np
from pygame import surface
from pygame.sprite import Group, LayeredDirty
from pygame.transform import scale

from src.common import Direction, tantegel_castle_throne_room_music, KING_LORIK_PATH, get_image, \
    GUARD_PATH, MAN_PATH, tantegel_castle_courtyard_music, WOMAN_PATH, WISE_MAN_PATH, \
    SOLDIER_PATH, MERCHANT_PATH, PRINCESS_GWAELIN_PATH, DRAGONLORD_PATH, UNARMED_HERO_PATH, MAP_TILES_PATH, \
    overworld_music, village_music, dungeon_floor_4_music, dungeon_floor_1_music, dungeon_floor_2_music, dungeon_floor_3_music, dungeon_floor_5_music, \
    dungeon_floor_6_music, dungeon_floor_7_music, dungeon_floor_8_music
from src.config import TILE_SIZE, SCALE, COLOR_KEY
from src.map_layouts import MapLayouts
from src.sprites.animated_sprite import AnimatedSprite
from src.sprites.base_sprite import BaseSprite
# Tile Key:
# Index values for the map tiles corresponding to location on tile sheet.
from src.sprites.fixed_character import FixedCharacter
from src.sprites.roaming_character import RoamingCharacter

offset = TILE_SIZE // 2
all_impassable_tiles = (
    'ROOF', 'WALL', 'WOOD', 'DOOR', 'WEAPON_SIGN', 'INN_SIGN', 'MOUNTAINS', 'WATER', 'BOTTOM_COAST', 'BOTTOM_LEFT_COAST', 'LEFT_COAST', 'TOP_LEFT_COAST',
    'TOP_COAST', 'TOP_RIGHT_COAST', 'RIGHT_COAST', 'BOTTOM_RIGHT_COAST', 'BOTTOM_TOP_LEFT_COAST', 'BOTTOM_TOP_COAST', 'BOTTOM_TOP_RIGHT_COAST', 'KING_LORIK',
    'DOWN_FACE_GUARD', 'LEFT_FACE_GUARD', 'UP_FACE_GUARD', 'RIGHT_FACE_GUARD', 'MAN', 'WOMAN', 'WISE_MAN', 'SOLDIER', 'MERCHANT')
up_staircase = {'map': 'Alefgard', 'stair_direction': 'up'}


def parse_animated_sprite_sheet(sheet: surface.Surface) -> Tuple[list, list, list, list]:
    """
    Parses sprite sheets and creates image lists. If is_roaming is True
    the sprite will have four lists of images, one for each direction. If
    is_roaming is False then there will be one list of 2 images.
    """
    sheet.set_colorkey(COLOR_KEY)
    sheet.convert_alpha()

    facing_down, facing_left, facing_up, facing_right = [], [], [], []

    for i in range(0, 2):

        rect = (i * TILE_SIZE, 0, TILE_SIZE, TILE_SIZE)
        facing_down.append(sheet.subsurface(rect))

        is_four_sided = sheet.get_size()[0] % 128 == 0
        if is_four_sided:
            # is_four_sided
            rect = ((i + 2) * TILE_SIZE, 0, TILE_SIZE, TILE_SIZE)
            facing_left.append(sheet.subsurface(rect))

            rect = ((i + 4) * TILE_SIZE, 0, TILE_SIZE, TILE_SIZE)
            facing_up.append(sheet.subsurface(rect))

            rect = ((i + 6) * TILE_SIZE, 0, TILE_SIZE, TILE_SIZE)
            facing_right.append(sheet.subsurface(rect))

    return facing_down, facing_left, facing_up, facing_right


def get_center_point(x, y):
    return (x * TILE_SIZE) + offset, (y * TILE_SIZE) + offset


def warp_line(lower_bound, upper_bound):
    # check if vertical
    if lower_bound[0] != upper_bound[0]:
        return vertical_warp_line(lower_bound, upper_bound)
    elif lower_bound[1] != upper_bound[1]:
        return horizontal_warp_line(lower_bound, upper_bound)
    else:
        print("Invalid warp line coordinates.")


def horizontal_warp_line(left_point, right_point):
    return [(right_point[0], min(n, right_point[1])) for n in range(left_point[1], right_point[1] + 1)]


def vertical_warp_line(top_point, bottom_point):
    return [(min(n, bottom_point[0]), bottom_point[1]) for n in range(top_point[0], bottom_point[0] + 1)]


def parse_map_tiles(map_path):
    map_sheet = get_image(map_path).convert()
    map_tile_sheet = scale(map_sheet, (map_sheet.get_width() * SCALE, map_sheet.get_height() * SCALE))
    map_tiles = []
    width, height = map_tile_sheet.get_size()

    for x in range(0, width // TILE_SIZE):
        row = []
        map_tiles.append(row)

        for y in range(0, height // TILE_SIZE):
            rect = (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            row.append(map_tile_sheet.subsurface(rect))
    return map_tiles


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


def set_character_position(character):
    character.column, character.row = character.rect.x // TILE_SIZE, character.rect.y // TILE_SIZE


class DragonWarriorMap:
    def __init__(self, layout, last_map=None):

        self.destination_coordinates = None
        self.identifier = self.__class__.__name__

        # Character variables

        self.tile_types_in_current_map = []
        self.scale = SCALE
        self.player = None
        self.player_sprites = None
        self.characters = {}
        self.fixed_characters = []
        self.roaming_characters = []

        # Map variables

        self.tiles_in_current_loaded_map = None
        self.layout = layout
        self.layout_numpy_array = np.array(self.layout)
        self.center_pt = None
        self.map_tiles = parse_map_tiles(map_path=MAP_TILES_PATH)
        self.impassable_tiles = all_impassable_tiles
        self.tile_group_dict = {}
        self.staircases = {}
        self.height = len(self.layout) * TILE_SIZE
        self.width = len(self.layout[0]) * TILE_SIZE
        self.last_map = last_map

        self.floor_tile_key = {
            'ROOF': {'val': 0},
            'WALL': {'val': 1},
            'WOOD': {'val': 2},
            'BRICK': {'val': 3},
            'TREASURE_BOX': {'val': 4},
            'DOOR': {'val': 5},
            'BRICK_STAIR_DOWN': {'val': 6},
            'BRICK_STAIR_UP': {'val': 7},
            'BARRIER': {'val': 8},
            'WEAPON_SIGN': {'val': 9},
            'INN_SIGN': {'val': 10},
            'CASTLE': {'val': 11},
            'TOWN': {'val': 12},
            'GRASS': {'val': 13},
            'TREES': {'val': 14},
            'HILLS': {'val': 15},
            'MOUNTAINS': {'val': 16},
            'CAVE': {'val': 17},
            'GRASS_STAIR_DOWN': {'val': 18},
            'SAND': {'val': 19},
            'MARSH': {'val': 20},
            'BRIDGE': {'val': 21},
            'WATER': {'val': 22},
            'BOTTOM_COAST': {'val': 23},
            'BOTTOM_LEFT_COAST': {'val': 24},
            'LEFT_COAST': {'val': 25},
            'TOP_LEFT_COAST': {'val': 26},
            'TOP_COAST': {'val': 27},
            'TOP_RIGHT_COAST': {'val': 28},
            'RIGHT_COAST': {'val': 29},
            'BOTTOM_RIGHT_COAST': {'val': 30},
            'BOTTOM_TOP_LEFT_COAST': {'val': 31},
            'BOTTOM_TOP_RIGHT_COAST': {'val': 32}
        }
        self.character_key = {
            'HERO': {'val': 33, 'path': UNARMED_HERO_PATH},
            'KING_LORIK': {'val': 34, 'path': KING_LORIK_PATH},
            'DOWN_FACE_GUARD': {'val': 35, 'path': GUARD_PATH, 'direction': Direction.DOWN.value},
            'LEFT_FACE_GUARD': {'val': 36, 'path': GUARD_PATH, 'direction': Direction.LEFT.value},
            'UP_FACE_GUARD': {'val': 37, 'path': GUARD_PATH, 'direction': Direction.UP.value},
            'RIGHT_FACE_GUARD': {'val': 38, 'path': GUARD_PATH, 'direction': Direction.RIGHT.value},
            'ROAMING_GUARD': {'val': 39, 'path': GUARD_PATH, 'direction': Direction.DOWN.value},
            'MAN': {'val': 40, 'path': MAN_PATH, 'direction': Direction.DOWN.value},
            'WOMAN': {'val': 41, 'path': WOMAN_PATH, 'direction': Direction.DOWN.value, 'underlying_tile': 'GRASS'},
            'WISE_MAN': {'val': 42, 'path': WISE_MAN_PATH, 'direction': Direction.DOWN.value},
            'SOLDIER': {'val': 43, 'path': SOLDIER_PATH, 'direction': Direction.DOWN.value},
            'MERCHANT': {'val': 44, 'path': MERCHANT_PATH, 'direction': Direction.DOWN.value},
            'PRINCESS_GWAELIN': {'val': 45, 'path': PRINCESS_GWAELIN_PATH, 'direction': Direction.DOWN.value},
            'DRAGONLORD': {'val': 46, 'path': DRAGONLORD_PATH, 'direction': Direction.DOWN.value}
        }
        for character, character_dict in self.character_key.items():
            if character in ('KING_LORIK', 'PRINCESS_GWAELIN'):
                character_dict['four_sided'] = False
            else:
                character_dict['four_sided'] = True
            character_dict['roaming'] = True if character == 'ROAMING_GUARD' else False
            if character == 'HERO':
                character_dict['underlying_tile'] = self.hero_underlying_tile()
            elif character == 'WOMAN':
                character_dict['underlying_tile'] = 'GRASS'
            else:
                character_dict['underlying_tile'] = 'BRICK'
        self.tile_key = dict(list(self.floor_tile_key.items()) + list(self.character_key.items()))

    def get_tile_by_value(self, position: int) -> str:
        """Returns the tile name from the integer value associated with it."""
        return list(self.tile_key.keys())[position]

    def get_initial_character_location(self, character_name: str) -> np.ndarray:
        """
        Gets the initial location of any character specified.
        :param character_name: Name of the character to find
        :return:
        """
        # TODO(ELF): Only works if there is only one of these characters. Make work with multiple.
        character_layout_position = np.asarray(
            np.where(self.layout_numpy_array == self.character_key[character_name]['val'])).T
        return character_layout_position

    def get_staircase_locations(self):
        """
        Dynamically generates a list of staircase locations. Currently unused, but might be useful for staircase warps.
        :return:
        """
        # also needs BRICK_STAIR_UP and GRASS_STAIR_DOWN
        brick_stair_down_staircase_locations = self.find_tile_in_layout_by_value('BRICK_STAIR_DOWN')
        brick_stair_up_staircase_locations = self.find_tile_in_layout_by_value('BRICK_STAIR_UP')
        grass_stair_down_staircase_locations = self.find_tile_in_layout_by_value('GRASS_STAIR_DOWN')
        return brick_stair_down_staircase_locations + brick_stair_up_staircase_locations + grass_stair_down_staircase_locations

    def find_tile_in_layout_by_value(self, tile):
        return np.asarray(np.where(self.layout_numpy_array == self.tile_key[tile]['val'])).T

    # @timeit
    def load_map(self, player, destination_coordinates) -> None:
        self.destination_coordinates = destination_coordinates
        self.tile_types_in_current_map = self.get_tiles_in_current_map()
        self.impassable_tiles = tuple(self.tile_types_in_current_map & set(all_impassable_tiles))
        for y in range(len(self.layout)):
            for x in range(len(self.layout[y])):
                self.center_pt = get_center_point(x, y)
                if self.layout[y][x] <= 32:  # anything below 32 is a floor tile
                    self.map_floor_tiles(x, y)
                else:
                    self.map_character_tiles(y, x, player)
        self.set_characters_initial_directions()
        self.set_custom_underlying_tiles()

    def get_tiles_in_current_map(self):
        tiles_in_current_map = set([self.get_tile_by_value(tile) for row in self.layout for tile in row])
        tiles_in_current_map.add(self.tile_key['HERO']['underlying_tile'])
        # TODO(ELF): Add underlying tile of player to draw list
        return tiles_in_current_map

    # @timeit
    def map_character_tiles(self, row, column, player) -> None:
        current_tile = self.layout[row][column]
        for character, character_dict in self.character_key.items():
            if current_tile == character_dict['val']:
                self.map_character(character, character_dict, current_tile, player, (row, column))

    def map_character(self, character, character_dict, current_tile, player, coordinates):
        if current_tile == self.character_key['HERO']['val']:
            if not self.player:
                player.__init__(self.center_pt, self.scale_spritesheet(UNARMED_HERO_PATH))
            self.map_player(character_dict['underlying_tile'], player, coordinates)
        else:
            self.map_npc(character, character_dict.get('direction'), character_dict['underlying_tile'], character_dict['path'], character_dict['four_sided'],
                         coordinates, character_dict['roaming'])

    def scale_spritesheet(self, image_path):
        return parse_animated_sprite_sheet(
            scale(get_image(image_path), (get_image(image_path).get_width() * self.scale, get_image(image_path).get_height() * self.scale)))

    def map_npc(self, identifier, direction, underlying_tile, image_path, four_sided, coordinates, is_roaming=False) -> None:
        sheet = get_image(image_path)
        character_sprites = LayeredDirty()
        sheet = scale(sheet, (sheet.get_width() * self.scale, sheet.get_height() * self.scale))
        images = parse_animated_sprite_sheet(sheet)
        if four_sided:
            if is_roaming:
                character = RoamingCharacter(self.center_pt, direction, images, identifier)
                character.row, character.column = coordinates
                self.roaming_characters.append(character)
            else:
                character = FixedCharacter(self.center_pt, direction, images, identifier)
                character.row, character.column = coordinates
                self.fixed_characters.append(character)
        else:
            character = AnimatedSprite(self.center_pt, Direction.DOWN.value, images, identifier)
            character.row, character.column = coordinates
            self.fixed_characters.append(character)
        character_sprites.add(character)
        # self.character_key[identifier]['val']
        self.set_identifiers_for_duplicate_characters(character, identifier)
        self.characters[character.identifier] = {'character': character,
                                                 'character_sprites': character_sprites,
                                                 'tile_value': self.character_key[identifier]['val'],
                                                 'coordinates': coordinates}
        self.add_tile(self.floor_tile_key[underlying_tile])
        self.layout[coordinates[0]][coordinates[1]] = self.floor_tile_key[underlying_tile]['val']

    def set_identifiers_for_duplicate_characters(self, character, identifier):
        character_count = [character_dict['tile_value'] for character_dict in self.characters.values()].count(self.character_key[identifier]['val']) + 1
        if character_count > 1:
            character.identifier = f'{identifier}_{character_count}'

    def map_player(self, underlying_tile, player, coordinates) -> None:
        self.player = player
        self.player_sprites = LayeredDirty(self.player)
        self.player.direction = self.hero_initial_direction()
        self.add_tile(self.floor_tile_key[underlying_tile])
        self.characters['HERO'] = {'character': self.player,
                                   'character_sprites': self.player_sprites,
                                   'tile_value': self.character_key['HERO']['val'],
                                   'coordinates': coordinates}
        self.layout[coordinates[0]][coordinates[1]] = self.floor_tile_key[underlying_tile]['val']

    # @timeit
    def map_floor_tiles(self, x, y) -> None:
        for tile_dict in self.floor_tile_key.values():
            if self.layout[y][x] < 33 and self.layout[y][x] == tile_dict['val']:
                self.add_tile(tile_dict)
                break

    def add_tile(self, tile_dict) -> None:
        tile_value = tile_dict.get('val')
        tile_group = tile_dict.get('group')
        if tile_group is None:
            self.floor_tile_key[self.get_tile_by_value(tile_value)]['group'] = Group()
        if tile_value <= 10:
            tile = BaseSprite(self.center_pt, self.map_tiles[tile_value][0])
        elif tile_value <= 21:
            tile = BaseSprite(self.center_pt, self.map_tiles[tile_value - 11][1])
        elif tile_value < 33:
            tile = BaseSprite(self.center_pt, self.map_tiles[tile_value - 22][2])
        else:
            print("Invalid tile.")
            return
        self.floor_tile_key[self.get_tile_by_value(tile_value)]['group'].add(tile)

    @property
    def hero_underlying_tile(self):
        raise NotImplementedError("Method not implemented.")

    @property
    def hero_initial_direction(self):
        raise NotImplementedError("Method not implemented")

    def set_characters_initial_directions(self):
        raise NotImplementedError("Method not implemented")

    def set_character_initial_direction(self, character_identifier, direction):
        self.characters[character_identifier]['character'].direction = direction.value

    def set_custom_underlying_tiles(self):
        raise NotImplementedError("Method not implemented")

    def set_town_to_overworld_warps(self):
        """Sets the exit location to the overworld (Alefgard) from within a town"""
        for staircase_dict in self.staircases.values():
            alefgard_staircases = Alefgard().staircases
            # TODO(ELF): Probably don't need this extra alefgard_lookup_dict - maybe remove it later
            alefgard_lookup_dict = {}
            for alefgard_coordinates, alefgard_staircase_dict in alefgard_staircases.items():
                alefgard_lookup_dict[alefgard_staircase_dict.get('map')] = alefgard_staircase_dict
                alefgard_lookup_dict[alefgard_staircase_dict.get('map')]['alefgard_coordinates'] = alefgard_coordinates
            if staircase_dict['map'] == 'Alefgard':
                staircase_dict['destination_coordinates'] = alefgard_lookup_dict[self.__class__.__name__]['alefgard_coordinates']

    def create_town_gates(self, north_gate=None, east_gate=None, west_gate=None, south_gate=None):
        staircases_keys = []
        staircases_keys += north_gate if north_gate is not None else []
        staircases_keys += east_gate if east_gate is not None else []
        staircases_keys += west_gate if west_gate is not None else []
        staircases_keys += south_gate if south_gate is not None else []
        staircases_values = [up_staircase] * len(staircases_keys)
        self.staircases = dict(zip(staircases_keys, staircases_values))


class MapWithoutNPCs(DragonWarriorMap, ABC):
    def set_characters_initial_directions(self):
        pass

    def set_custom_underlying_tiles(self):
        pass


class TantegelThroneRoom(DragonWarriorMap):
    """
    This is the first map in the game, the Tantegel Castle throne room.
    """

    def __init__(self):
        super().__init__(MapLayouts().tantegel_throne_room)

        self.staircases = {
            (14, 18): {'map': 'TantegelCourtyard', 'stair_direction': 'down', 'destination_coordinates': (14, 14), 'direction': Direction.RIGHT.value}}
        self.music_file_path = tantegel_castle_throne_room_music

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.UP.value

    def set_characters_initial_directions(self):
        pass

    def set_custom_underlying_tiles(self):
        pass


class TantegelCourtyard(DragonWarriorMap):
    """
    This is the courtyard of Tantegel Castle.
    """

    def __init__(self):
        super().__init__(MapLayouts().tantegel_courtyard)
        alefgard = {'map': 'Alefgard', 'stair_direction': 'up'}
        #  TODO(ELF): replace staircases_keys with call to function warp_line, and get coordinates for warp_line (37, 9) - (37, 26)
        staircases_keys = [(37, min(n, 26)) for n in range(9, 27)]
        # staircase_keys = warp_line((37, 9), (37, 26))
        staircases_values = [alefgard] * len(staircases_keys)
        self.staircases = dict(zip(staircases_keys, staircases_values))
        self.staircases[(14, 14)] = {'map': 'TantegelThroneRoom', 'stair_direction': 'up', 'destination_coordinates': (14, 18),
                                     'direction': Direction.LEFT.value}
        self.staircases[(36, 36)] = {'map': 'TantegelUnderground', 'stair_direction': 'down'}
        self.set_town_to_overworld_warps()
        self.music_file_path = tantegel_castle_courtyard_music

    def hero_underlying_tile(self):
        # TODO: Super TODO. Make characters have initial coordinates
        #  Instead of underlying tiles, set up the map with just the background tiles.
        #  Right now this implementation has a band-aid over it
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value

    def set_characters_initial_directions(self):
        self.set_character_initial_direction('WISE_MAN', Direction.LEFT)

    def set_custom_underlying_tiles(self):
        pass


class TantegelUnderground(DragonWarriorMap):
    def __init__(self):
        super().__init__(MapLayouts().tantegel_underground)
        self.music_file_path = tantegel_castle_courtyard_music
        self.staircases = {(4, 1): {'map': 'TantegelCourtyard', 'stair_direction': 'up', 'destination_coordinates': (36, 36)}}

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value

    def set_characters_initial_directions(self):
        pass
        # self.set_character_initial_direction('WISE_MAN', Direction.DOWN)

    def set_custom_underlying_tiles(self):
        pass


class CharlockB1(MapWithoutNPCs):
    def __init__(self):
        super().__init__(MapLayouts().charlock_b1)
        self.music_file_path = dungeon_floor_1_music

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.UP.value


class CharlockB2(MapWithoutNPCs):
    def __init__(self):
        super().__init__(MapLayouts().charlock_b2)
        self.music_file_path = dungeon_floor_2_music

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class CharlockB3(MapWithoutNPCs):
    def __init__(self):
        super().__init__(MapLayouts().charlock_b3)
        self.music_file_path = dungeon_floor_3_music

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class CharlockB4(MapWithoutNPCs):
    def __init__(self):
        super().__init__(MapLayouts().charlock_b4)
        self.music_file_path = dungeon_floor_4_music

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class CharlockB5(MapWithoutNPCs):
    def __init__(self):
        super().__init__(MapLayouts().charlock_b5)
        self.music_file_path = dungeon_floor_5_music

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_DOWN'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class CharlockB6(MapWithoutNPCs):
    def __init__(self):
        super().__init__(MapLayouts().charlock_b6)
        self.music_file_path = dungeon_floor_6_music

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class CharlockB7(MapWithoutNPCs):
    def __init__(self):
        super().__init__(MapLayouts().charlock_b7)
        self.music_file_path = dungeon_floor_7_music

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class CharlockB8(MapWithoutNPCs):
    def __init__(self):
        super().__init__(MapLayouts().charlock_b8)
        self.music_file_path = dungeon_floor_8_music

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class Alefgard(DragonWarriorMap):
    """
    This is Alefgard, the world by which the player travels between castles, villages, and dungeons.
    """

    def __init__(self):
        super().__init__(MapLayouts().alefgard)
        self.music_file_path = overworld_music
        self.staircases = {
            # (row, column)
            # castles
            (50, 49): {'map': 'TantegelCourtyard', 'destination_coordinates': (36, 18), 'direction': Direction.UP.value},
            # villages
            (48, 54): {'map': 'Brecconary'},
            (9, 8): {'map': 'Garinham'},
            (17, 110): {'map': 'Kol'},
            # cave
            (19, 34): {'map': 'ErdricksCaveB1'},
            (51, 110): {'map': 'SwampCave', 'destination_coordinates': (6, 4)},
            (56, 110): {'map': 'SwampCave', 'destination_coordinates': (36, 4)},
            (64, 35): {'map': 'MountainCaveB1'},
            (96, 31): {'map': 'Hauksness'},
            (79, 108): {'map': 'Rimuldar'},
            (109, 79): {'map': 'Cantlin'},
            (116, 114): {'map': 'MagicTemple'},
            (8, 87): {'map': 'StaffOfRainCave'},
        }
        for staircase_dict in self.staircases.values():
            staircase_dict['stair_direction'] = 'up'

    def hero_underlying_tile(self):
        return 'CASTLE'

    def hero_initial_direction(self):
        return Direction.DOWN.value if self.character_key['HERO']['underlying_tile'] != 'GRASS_STAIR_DOWN' else Direction.LEFT.value

    def set_characters_initial_directions(self):
        pass

    def set_custom_underlying_tiles(self):
        pass


class Brecconary(DragonWarriorMap):

    def __init__(self):
        super().__init__(MapLayouts().brecconary)
        self.create_town_gates(north_gate=warp_line((7, 23), (7, 26)),
                               east_gate=warp_line((21, 40), (25, 40)),
                               west_gate=warp_line((21, 9), (24, 9)))
        self.set_town_to_overworld_warps()
        self.music_file_path = village_music

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.RIGHT.value

    def set_characters_initial_directions(self):
        self.set_character_initial_direction('MERCHANT_2', Direction.LEFT)
        self.set_character_initial_direction('WOMAN', Direction.LEFT)

    def set_custom_underlying_tiles(self):
        # TODO(ELF): Setting underlying tiles like this as is doesn't work.
        pass
        # self.characters['WOMAN']['character'].underlying_tile = 'BRICK'


class Garinham(DragonWarriorMap):

    def __init__(self):
        super().__init__(MapLayouts().garinham)
        self.create_town_gates(west_gate=warp_line((13, 8), (15, 8)),
                               east_gate=warp_line((11, 29), (14, 29)))
        self.set_town_to_overworld_warps()
        self.music_file_path = village_music

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.RIGHT.value

    def set_characters_initial_directions(self):
        self.set_character_initial_direction('MERCHANT', Direction.LEFT)
        self.set_character_initial_direction('MERCHANT_2', Direction.LEFT)
        self.set_character_initial_direction('MERCHANT_3', Direction.UP)
        self.set_character_initial_direction('WISE_MAN', Direction.RIGHT)

    def set_custom_underlying_tiles(self):
        pass


class Kol(DragonWarriorMap):

    def __init__(self):
        super().__init__(MapLayouts().kol)
        self.music_file_path = village_music
        self.create_town_gates(north_gate=warp_line((7, 8), (7, 33)),
                               east_gate=warp_line((7, 33), (32, 33)),
                               west_gate=warp_line((7, 8), (32, 8)),
                               south_gate=warp_line((32, 8), (32, 33))
                               )
        self.set_town_to_overworld_warps()

    def hero_underlying_tile(self):
        return 'SAND'

    def hero_initial_direction(self):
        return Direction.UP.value

    def set_characters_initial_directions(self):
        pass

    def set_custom_underlying_tiles(self):
        pass


class Rimuldar(DragonWarriorMap):

    def __init__(self):
        super().__init__(MapLayouts().rimuldar)
        self.create_town_gates(
            north_gate=warp_line((6, 0), (6, len(self.layout[0]))),
            east_gate=warp_line((0, 38), (len(self.layout), 38)),
            west_gate=warp_line((0, 7), (len(self.layout), 7)),
            south_gate=warp_line((36, 0), (36, len(self.layout[0]))))
        self.set_town_to_overworld_warps()
        self.music_file_path = village_music

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.LEFT.value

    def set_characters_initial_directions(self):
        pass

    def set_custom_underlying_tiles(self):
        pass


class Hauksness(MapWithoutNPCs):

    def __init__(self):
        super().__init__(MapLayouts().hauksness)
        self.music_file_path = dungeon_floor_4_music
        self.create_town_gates(north_gate=warp_line((7, 9), (7, 28)),
                               east_gate=warp_line((0, 29), (len(self.layout), 29)),
                               west_gate=warp_line((0, 8), (len(self.layout), 8)),
                               south_gate=warp_line((28, 9), (28, 28))
                               )
        self.set_town_to_overworld_warps()

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class Cantlin(DragonWarriorMap):

    def __init__(self):
        super().__init__(MapLayouts().cantlin)
        self.music_file_path = village_music
        self.create_town_gates(north_gate=warp_line((7, 0), (7, 29))
                               # west_gate = warp_line((21, 9), (24, 9))
                               # east_gate = warp_line((21, 40), (25, 40))
                               )
        self.set_town_to_overworld_warps()

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.DOWN.value

    def set_characters_initial_directions(self):
        pass

    def set_custom_underlying_tiles(self):
        pass


class ErdricksCaveB1(MapWithoutNPCs):
    def __init__(self):
        super().__init__(MapLayouts().erdricks_cave_b1)
        self.music_file_path = dungeon_floor_1_music
        self.staircases = {(1, 1): {'map': 'Alefgard', 'stair_direction': 'up'},
                           (10, 10): {'map': 'ErdricksCaveB2', 'stair_direction': 'down'}}
        self.set_town_to_overworld_warps()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class ErdricksCaveB2(MapWithoutNPCs):
    def __init__(self):
        super().__init__(MapLayouts().erdricks_cave_b2)
        self.music_file_path = dungeon_floor_2_music
        self.staircases = {(10, 9): {'map': 'ErdricksCaveB1', 'stair_direction': 'up'}}

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class SwampCave(DragonWarriorMap):
    def __init__(self):
        super().__init__(MapLayouts().swamp_cave)
        self.music_file_path = dungeon_floor_1_music
        self.staircases = {(6, 4): {'map': 'Alefgard', 'stair_direction': 'up', 'destination_coordinates': (51, 110)},
                           (36, 4): {'map': 'Alefgard', 'stair_direction': 'up', 'destination_coordinates': (56, 110)}}

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value

    def set_characters_initial_directions(self):
        pass

    def set_custom_underlying_tiles(self):
        pass


class MountainCaveB1(MapWithoutNPCs):
    def __init__(self):
        super().__init__(MapLayouts().mountain_cave_b1)
        self.music_file_path = dungeon_floor_1_music
        self.staircases = {}
        self.set_town_to_overworld_warps()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class StaffOfRainCave(DragonWarriorMap):
    def __init__(self):
        super().__init__(MapLayouts().staff_of_rain_cave)
        self.music_file_path = tantegel_castle_courtyard_music
        self.staircases = {(11, 6): {'map': 'Alefgard', 'stair_direction': 'up'}}
        self.set_town_to_overworld_warps()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value

    def set_characters_initial_directions(self):
        self.set_character_initial_direction('WISE_MAN', Direction.RIGHT)

    def set_custom_underlying_tiles(self):
        pass


class MagicTemple(DragonWarriorMap):
    def __init__(self):
        super().__init__(MapLayouts().magic_temple)
        self.music_file_path = tantegel_castle_courtyard_music
        self.staircases = {(6, 2): {'map': 'Alefgard', 'stair_direction': 'up'}}
        self.set_town_to_overworld_warps()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value

    def set_characters_initial_directions(self):
        self.set_character_initial_direction('WISE_MAN', Direction.LEFT)

    def set_custom_underlying_tiles(self):
        pass


# Lookup of all map names with their associated class
map_lookup = {map_name: map_class for map_name, map_class in inspect.getmembers(sys.modules[__name__], inspect.isclass)}
