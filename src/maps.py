import inspect
import sys
from abc import ABC

import numpy as np
from pygame.sprite import Group, LayeredDirty
from pygame.transform import scale

from src.common import Direction, tantegel_castle_throne_room_music, KING_LORIK_PATH, get_image, \
    GUARD_PATH, MAN_PATH, tantegel_castle_courtyard_music, WOMAN_PATH, WISE_MAN_PATH, \
    SOLDIER_PATH, MERCHANT_PATH, PRINCESS_GWAELIN_PATH, DRAGONLORD_PATH, UNARMED_HERO_PATH, MAP_TILES_PATH, \
    overworld_music, village_music, dungeon_floor_1_music, dungeon_floor_2_music, dungeon_floor_3_music, dungeon_floor_4_music, dungeon_floor_5_music, \
    dungeon_floor_6_music, dungeon_floor_7_music, dungeon_floor_8_music
from src.config import TILE_SIZE, SCALE
from src.map_layouts import MapLayouts
from src.maps_functions import parse_map_tiles, warp_line, parse_animated_sprite_sheet, get_center_point
from src.player.player import Player
from src.sprites.animated_sprite import AnimatedSprite
from src.sprites.base_sprite import BaseSprite
from src.sprites.fixed_character import FixedCharacter
from src.sprites.roaming_character import RoamingCharacter

all_impassable_tiles = (
    'ROOF', 'WALL', 'WOOD', 'DOOR', 'WEAPON_SIGN', 'INN_SIGN', 'MOUNTAINS', 'WATER', 'BOTTOM_COAST', 'BOTTOM_LEFT_COAST', 'LEFT_COAST', 'TOP_LEFT_COAST',
    'TOP_COAST', 'TOP_RIGHT_COAST', 'RIGHT_COAST', 'BOTTOM_RIGHT_COAST', 'BOTTOM_TOP_LEFT_COAST', 'BOTTOM_TOP_COAST', 'BOTTOM_TOP_RIGHT_COAST', 'KING_LORIK',
    'DOWN_FACE_GUARD', 'LEFT_FACE_GUARD', 'UP_FACE_GUARD', 'RIGHT_FACE_GUARD', 'MAN', 'WOMAN', 'WISE_MAN', 'SOLDIER', 'MERCHANT')


class DragonWarriorMap:
    def __init__(self, layout, last_map=None):

        self.music_file_path = None
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

        self.initial_coordinates = ()
        self.tiles_in_current_loaded_map = None
        self.layout = layout
        self.center_pt = None
        self.map_tiles = parse_map_tiles(map_path=MAP_TILES_PATH)
        self.impassable_tiles = all_impassable_tiles
        self.tile_group_dict = {}
        self.staircases = {}
        self.height = len(self.layout) * TILE_SIZE
        self.width = len(self.layout[0]) * TILE_SIZE
        self.last_map = last_map

        # Tile Key:
        # Index values for the map tiles corresponding to location on tile sheet.

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
            # TODO(ELF): Pretty rough logic here. Need to make this more extensible.
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
        character_layout_position = np.asarray(
            np.where(np.array(self.layout) == self.character_key[character_name]['val'])).T
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
        return np.asarray(np.where(np.array(self.layout) == self.tile_key[tile]['val'])).T

    # @timeit
    def load_map(self, player, destination_coordinates) -> None:
        self.destination_coordinates = destination_coordinates
        self.tile_types_in_current_map = self.get_tiles_in_current_map()
        self.impassable_tiles = tuple(self.tile_types_in_current_map & set(all_impassable_tiles))
        for row in range(len(self.layout)):
            for column in range(len(self.layout[row])):
                self.center_pt = get_center_point(column, row)
                if self.layout[row][column] <= 32:  # anything below 32 is a floor tile
                    self.map_floor_tiles(column, row)
                else:
                    self.map_character_tiles(column, row, player)
        self.set_characters_initial_directions()

    def get_tiles_in_current_map(self) -> set:
        return set([self.get_tile_by_value(tile) for row in self.layout for tile in row] + [self.tile_key['HERO']['underlying_tile']])

    # @timeit
    def map_character_tiles(self, column, row, player) -> None:
        current_tile = self.layout[row][column]
        for character, character_dict in self.character_key.items():
            if current_tile == character_dict['val']:
                self.map_character(character, character_dict, current_tile, player, (row, column))

    def map_character(self, character, character_dict, current_tile, player, coordinates) -> None:
        if current_tile == self.character_key['HERO']['val']:
            # TODO(ELF): not the greatest thing to call the constructor every single time the character is mapped.
            #  instead, it should just pass the player object from map to map and keep all the attributes.
            super(Player, player).__init__(self.center_pt, player.direction_value, self.scale_sprite_sheet(UNARMED_HERO_PATH), identifier='HERO')
            self.map_player(character_dict['underlying_tile'], player, coordinates)
        else:
            self.map_npc(character, character_dict.get('direction'), character_dict['underlying_tile'], character_dict['path'], character_dict['four_sided'],
                         coordinates, character_dict['roaming'])

    def scale_sprite_sheet(self, image_path):
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
        self.add_tile(self.floor_tile_key[underlying_tile], self.center_pt)
        # self.layout[coordinates[0]][coordinates[1]] = self.floor_tile_key[underlying_tile]['val']

    def set_identifiers_for_duplicate_characters(self, character, identifier):
        character_count = [character_dict['tile_value'] for character_dict in self.characters.values()].count(self.character_key[identifier]['val']) + 1
        if character_count > 1:
            character.identifier = f'{identifier}_{character_count}'

    def map_player(self, underlying_tile, player, coordinates) -> None:
        self.player_sprites = LayeredDirty(player)
        player.direction_value = self.hero_initial_direction()
        self.add_tile(self.floor_tile_key[underlying_tile], self.center_pt)
        self.characters['HERO'] = {'character': player,
                                   'character_sprites': self.player_sprites,
                                   'tile_value': self.character_key['HERO']['val'],
                                   'coordinates': coordinates}
        self.layout[coordinates[0]][coordinates[1]] = self.floor_tile_key[underlying_tile]['val']

    # @timeit
    def map_floor_tiles(self, column, row) -> None:
        for tile_dict in self.floor_tile_key.values():
            if self.layout[row][column] == tile_dict['val']:
                self.add_tile(tile_dict, self.center_pt)
                break

    def add_tile(self, tile_dict, center_pt) -> None:
        tile_value = tile_dict['val']
        tile_group = tile_dict.get('group')
        if tile_group is None:
            self.floor_tile_key[self.get_tile_by_value(tile_value)]['group'] = Group()
        if tile_value <= 10:
            tile = BaseSprite(center_pt, self.map_tiles[tile_value][0])
        elif tile_value <= 21:
            tile = BaseSprite(center_pt, self.map_tiles[tile_value - 11][1])
        elif tile_value < 33:
            tile = BaseSprite(center_pt, self.map_tiles[tile_value - 22][2])
        self.floor_tile_key[self.get_tile_by_value(tile_value)]['group'].add(tile)

    @property
    def hero_underlying_tile(self):
        raise NotImplementedError("Method not implemented.")

    @property
    def hero_initial_direction(self):
        raise NotImplementedError("Method not implemented")

    def set_characters_initial_directions(self) -> None:
        raise NotImplementedError("Method not implemented")

    def set_character_initial_direction(self, character_identifier, direction) -> None:
        if self.characters.get(character_identifier):
            self.characters[character_identifier]['character'].direction_value = direction.value

    def set_town_to_overworld_warps(self) -> None:
        """Sets the exit location to the overworld (Alefgard) from within a town"""
        for staircase_dict in self.staircases.values():
            alefgard_staircases = Alefgard().staircases
            # TODO(ELF): Probably don't need this extra alefgard_lookup_dict - maybe remove it later
            alefgard_lookup_dict = {}
            for alefgard_coordinates, alefgard_staircase_dict in alefgard_staircases.items():
                alefgard_lookup_dict[alefgard_staircase_dict['map']] = alefgard_staircase_dict
                alefgard_lookup_dict[alefgard_staircase_dict['map']]['alefgard_coordinates'] = alefgard_coordinates
            if staircase_dict['map'] == 'Alefgard':
                staircase_dict['destination_coordinates'] = alefgard_lookup_dict[self.__class__.__name__]['alefgard_coordinates']

    def create_town_gates(self, north_gate=None, east_gate=None, west_gate=None, south_gate=None) -> None:
        alefgard_up_staircase = {'map': 'Alefgard', 'stair_direction': 'up'}
        staircases_keys = []
        staircases_keys += north_gate if north_gate is not None else []
        staircases_keys += east_gate if east_gate is not None else []
        staircases_keys += west_gate if west_gate is not None else []
        staircases_keys += south_gate if south_gate is not None else []
        staircases_values = [alefgard_up_staircase] * len(staircases_keys)
        self.staircases = dict(zip(staircases_keys, staircases_values))

    def assign_stair_directions(self):
        for staircase_coordinates, staircase_dict in self.staircases.items():
            layout_staircase_coordinates = self.layout[staircase_coordinates[0]][staircase_coordinates[1]]
            if layout_staircase_coordinates == 33:
                staircase_dict['stair_direction'] = 'up' if self.hero_underlying_tile() == 'BRICK_STAIR_UP' else 'down'
            elif layout_staircase_coordinates == 6:
                staircase_dict['stair_direction'] = 'down'
            elif layout_staircase_coordinates == 7:
                staircase_dict['stair_direction'] = 'up'
            elif layout_staircase_coordinates == 18:
                staircase_dict['stair_direction'] = 'down'


class MapWithoutNPCs(DragonWarriorMap, ABC):
    def set_characters_initial_directions(self):
        pass


class BasementWithNPCs(DragonWarriorMap, ABC):
    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self) -> int:
        return Direction.RIGHT.value


class BasementWithoutNPCs(MapWithoutNPCs):

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class TantegelThroneRoom(DragonWarriorMap):
    """
    This is the first map in the game, the Tantegel Castle throne room.
    """

    def __init__(self):
        super().__init__(MapLayouts().tantegel_throne_room)

        self.staircases = {
            (14, 18): {'map': 'TantegelCourtyard', 'destination_coordinates': (14, 14), 'direction': Direction.RIGHT.value}}
        self.music_file_path = tantegel_castle_throne_room_music
        self.initial_coordinates = (10, 13)
        self.assign_stair_directions()

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.UP.value

    def set_characters_initial_directions(self):
        pass


class TantegelCourtyard(DragonWarriorMap):
    """
    This is the courtyard of Tantegel Castle.
    """

    def __init__(self):
        super().__init__(MapLayouts().tantegel_courtyard)
        self.create_town_gates(
            # north_gate=warp_line((6, 6), (6, 35)),
            west_gate=warp_line((6, 6), (37, 6)),
            east_gate=warp_line((6, 37), (37, 37)),
            south_gate=warp_line((37, 9), (37, 26)))
        self.staircases[(14, 14)] = {'map': 'TantegelThroneRoom', 'destination_coordinates': (14, 18), 'direction': Direction.LEFT.value}
        self.staircases[(36, 36)] = {'map': 'TantegelCellar'}
        self.assign_stair_directions()
        self.set_town_to_overworld_warps()
        self.initial_coordinates = (14, 14)
        self.music_file_path = tantegel_castle_courtyard_music

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value

    def set_characters_initial_directions(self):
        self.set_character_initial_direction('WISE_MAN', Direction.LEFT)


class TantegelCellar(BasementWithNPCs):
    def __init__(self):
        super().__init__(MapLayouts().tantegel_underground)
        self.music_file_path = tantegel_castle_courtyard_music
        self.staircases = {(4, 1): {'map': 'TantegelCourtyard', 'destination_coordinates': (36, 36)}}
        self.assign_stair_directions()

    def set_characters_initial_directions(self):
        self.set_character_initial_direction('WISE_MAN', Direction.DOWN)


class CharlockB1(MapWithoutNPCs):
    """Main entrance to Charlock Castle."""

    def __init__(self):
        super().__init__(MapLayouts().charlock_b1)
        self.music_file_path = dungeon_floor_1_music
        self.create_town_gates(south_gate=(warp_line((26, 15), (26, 18))))
        self.set_town_to_overworld_warps()
        self.staircases[(7, 17)] = {'map': 'CharlockB2', 'destination_coordinates': (3, 12)}  # A
        self.staircases[(21, 11)] = {'map': 'CharlockB2', 'destination_coordinates': ()}  # B
        self.staircases[(21, 22)] = {'map': 'CharlockB2', 'destination_coordinates': ()}  # C
        self.assign_stair_directions()

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.UP.value


class CharlockB2(BasementWithoutNPCs):
    """First inner basement in Charlock Castle."""

    def __init__(self):
        super().__init__(MapLayouts().charlock_b2)
        self.music_file_path = dungeon_floor_2_music
        self.staircases = {(3, 12): {'map': 'CharlockB1', 'destination_coordinates': (7, 17)},  # A
                           (7, 5): {'map': 'CharlockB3', 'destination_coordinates': (3, 3)},  # D
                           (17, 5): {'map': 'CharlockB3', 'destination_coordinates': (4, 3)},  # E
                           (4, 18): {'map': 'CharlockB3', 'destination_coordinates': (3, 11)},  # F
                           (10, 16): {'map': 'CharlockB3', 'destination_coordinates': (7, 7)},  # G
                           (22, 11): {'map': 'CharlockB3', 'destination_coordinates': (3, 8)}}  # J
        self.assign_stair_directions()


class CharlockB3(BasementWithoutNPCs):
    def __init__(self):
        super().__init__(MapLayouts().charlock_b3)
        self.music_file_path = dungeon_floor_3_music
        self.staircases = {
            (1, 1): {'map': 'CharlockB2'},  # D
            (3, 11): {'map': 'CharlockB2', 'destination_coordinates': (4, 18)},  # F
            (7, 7): {'map': 'CharlockB2', 'destination_coordinates': (10, 16)},  # G
            (3, 8): {'map': 'CharlockB2', 'destination_coordinates': (22, 11)},  # J
            (3, 6): {'map': 'CharlockB4', 'destination_coordinates': (3, 10)},  # K
            (4, 12): {'map': 'CharlockB4', 'destination_coordinates': (5, 5)},  # L
            (11, 3): {'map': 'CharlockB4', 'destination_coordinates': (7, 8)},  # M
            (12, 4): {'map': 'CharlockB4', 'destination_coordinates': (12, 3)},  # N
        }
        self.assign_stair_directions()


class CharlockB4(BasementWithoutNPCs):
    def __init__(self):
        super().__init__(MapLayouts().charlock_b4)
        self.music_file_path = dungeon_floor_4_music
        self.staircases = {
            (3, 10): {'map': 'CharlockB3', 'destination_coordinates': (3, 6)},  # K
            (5, 5): {'map': 'CharlockB3', 'destination_coordinates': (4, 12)},  # L
            (7, 8): {'map': 'CharlockB3', 'destination_coordinates': (11, 3)},  # M
            (12, 3): {'map': 'CharlockB3', 'destination_coordinates': (12, 4)},  # N
            (9, 4): {'map': 'CharlockB5', 'destination_coordinates': (12, 3)},  # O
            (10, 10): {'map': 'CharlockB5', 'destination_coordinates': (10, 10)},  # P

        }
        self.assign_stair_directions()


class CharlockB5(BasementWithoutNPCs):
    def __init__(self):
        super().__init__(MapLayouts().charlock_b5)
        self.music_file_path = dungeon_floor_5_music
        self.staircases = {
            (4, 11): {'map': 'CharlockB6', 'destination_coordinates': (3, 7)},  # R
            (5, 5): {'map': 'CharlockB6', 'destination_coordinates': (3, 12)},  # Q
            (10, 10): {'map': 'CharlockB4', 'destination_coordinates': (10, 10)},  # P
            (12, 3): {'map': 'CharlockB4', 'destination_coordinates': (9, 4)}  # O
        }
        self.assign_stair_directions()


class CharlockB6(BasementWithoutNPCs):
    def __init__(self):
        super().__init__(MapLayouts().charlock_b6)
        self.music_file_path = dungeon_floor_6_music
        self.staircases = {
            (3, 12): {'map': 'CharlockB5', 'destination_coordinates': (5, 5)},  # Q
            (3, 7): {'map': 'CharlockB5', 'destination_coordinates': (4, 11)},  # R
            (3, 3): {'map': 'CharlockB7Wide', 'destination_coordinates': (5, 3)},  # T
            (8, 8): {'map': 'CharlockB7Narrow', 'destination_coordinates': (3, 3)},  # S

        }
        self.assign_stair_directions()


class CharlockB7Wide(BasementWithoutNPCs):
    """A wide hallway right before the last level of Charlock Castle."""

    def __init__(self):
        super().__init__(MapLayouts().charlock_b7_wide)
        self.music_file_path = dungeon_floor_7_music
        self.staircases = {
            (5, 3): {'map': 'CharlockB6', 'destination_coordinates': (3, 3)},  # T
            (5, 12): {'map': 'CharlockB8'}  # U
        }
        self.assign_stair_directions()


class CharlockB7Narrow(BasementWithoutNPCs):
    """A dead end path in Charlock Castle that loops unto itself."""

    def __init__(self):
        super().__init__(MapLayouts().charlock_b7_narrow)
        self.music_file_path = dungeon_floor_7_music
        self.staircases = {
            (3, 3): {'map': 'CharlockB6', 'destination_coordinates': (8, 8)},
            # (3, 12): {'map': 'CharlockB7Narrow', 'destination_coordinates': (3, 3)}
        }
        self.assign_stair_directions()


class CharlockB8(DragonWarriorMap):
    """Deepest level of Charlock Castle, and location of the Dragonlord."""

    def __init__(self):
        super().__init__(MapLayouts().charlock_b8)
        self.music_file_path = dungeon_floor_8_music
        self.staircases = {(33, 16): {'map': 'CharlockB7Wide', 'destination_coordinates': (5, 12)}}
        self.assign_stair_directions()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value

    def set_characters_initial_directions(self):
        self.set_character_initial_direction('DRAGONLORD', Direction.DOWN)


class Alefgard(MapWithoutNPCs):
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
            (55, 54): {'map': 'CharlockB1'},
            # villages
            (48, 54): {'map': 'Brecconary', 'destination_coordinates': (23, 10)},
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
        self.initial_coordinates = (50, 49)

    def hero_underlying_tile(self):
        return 'CASTLE'

    def hero_initial_direction(self):
        return Direction.DOWN.value if self.character_key['HERO']['underlying_tile'] != 'GRASS_STAIR_DOWN' else Direction.LEFT.value


class Brecconary(DragonWarriorMap):

    def __init__(self):
        super().__init__(MapLayouts().brecconary)
        self.create_town_gates(north_gate=warp_line((7, 23), (7, 26)),
                               east_gate=warp_line((21, 40), (25, 40)),
                               west_gate=warp_line((21, 9), (24, 9)))
        self.set_town_to_overworld_warps()
        self.music_file_path = village_music
        self.initial_coordinates = (23, 10)

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.RIGHT.value

    def set_characters_initial_directions(self):
        self.set_character_initial_direction('MERCHANT_2', Direction.LEFT)
        self.set_character_initial_direction('WOMAN', Direction.LEFT)


class Garinham(DragonWarriorMap):

    def __init__(self):
        super().__init__(MapLayouts().garinham)
        self.create_town_gates(west_gate=warp_line((13, 8), (15, 8)),
                               east_gate=warp_line((11, 29), (14, 29)))
        self.set_town_to_overworld_warps()
        self.music_file_path = village_music
        self.initial_coordinates = (14, 9)

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.RIGHT.value

    def set_characters_initial_directions(self):
        self.set_character_initial_direction('MERCHANT', Direction.LEFT)
        self.set_character_initial_direction('MERCHANT_2', Direction.LEFT)
        self.set_character_initial_direction('MERCHANT_3', Direction.UP)
        self.set_character_initial_direction('WISE_MAN', Direction.RIGHT)


class Kol(DragonWarriorMap):

    def __init__(self):
        super().__init__(MapLayouts().kol)
        self.music_file_path = village_music
        self.create_town_gates(north_gate=warp_line((7, 8), (7, 33)),
                               east_gate=warp_line((7, 33), (32, 33)),
                               west_gate=warp_line((7, 8), (32, 8)),
                               south_gate=warp_line((32, 8), (32, 33)))
        self.set_town_to_overworld_warps()
        self.initial_coordinates = (30, 29)

    def hero_underlying_tile(self):
        return 'SAND'

    def hero_initial_direction(self):
        return Direction.UP.value

    def set_characters_initial_directions(self):
        pass


class Rimuldar(DragonWarriorMap):

    def __init__(self):
        super().__init__(MapLayouts().rimuldar)
        self.create_town_gates(north_gate=warp_line((6, 0), (6, len(self.layout[0]))),
                               east_gate=warp_line((0, 38), (len(self.layout), 38)),
                               west_gate=warp_line((0, 7), (len(self.layout), 7)),
                               south_gate=warp_line((36, 0), (36, len(self.layout[0]))))
        self.set_town_to_overworld_warps()
        self.music_file_path = village_music
        self.initial_coordinates = (22, 37)

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.LEFT.value

    def set_characters_initial_directions(self):
        pass


class Hauksness(MapWithoutNPCs):

    def __init__(self):
        super().__init__(MapLayouts().hauksness)
        self.music_file_path = dungeon_floor_4_music
        self.create_town_gates(north_gate=warp_line((7, 9), (7, 28)),
                               east_gate=warp_line((0, 29), (len(self.layout), 29)),
                               west_gate=warp_line((0, 8), (len(self.layout), 8)),
                               south_gate=warp_line((28, 9), (28, 28)))
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


class ErdricksCaveB1(MapWithoutNPCs):
    def __init__(self):
        super().__init__(MapLayouts().erdricks_cave_b1)
        self.music_file_path = dungeon_floor_1_music
        self.staircases = {(1, 1): {'map': 'Alefgard'},
                           (10, 10): {'map': 'ErdricksCaveB2'}}
        self.assign_stair_directions()
        self.set_town_to_overworld_warps()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class ErdricksCaveB2(MapWithoutNPCs):
    def __init__(self):
        super().__init__(MapLayouts().erdricks_cave_b2)
        self.music_file_path = dungeon_floor_2_music
        self.staircases = {(10, 9): {'map': 'ErdricksCaveB1'}}
        self.assign_stair_directions()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class SwampCave(DragonWarriorMap):
    def __init__(self):
        super().__init__(MapLayouts().swamp_cave)
        self.music_file_path = dungeon_floor_1_music
        self.staircases = {(6, 4): {'map': 'Alefgard', 'destination_coordinates': (51, 110)},
                           (36, 4): {'map': 'Alefgard', 'destination_coordinates': (56, 110)}}
        self.assign_stair_directions()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value

    def set_characters_initial_directions(self):
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
        self.staircases = {(11, 6): {'map': 'Alefgard'}}
        self.assign_stair_directions()
        self.set_town_to_overworld_warps()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value

    def set_characters_initial_directions(self):
        self.set_character_initial_direction('WISE_MAN', Direction.RIGHT)


class MagicTemple(DragonWarriorMap):
    def __init__(self):
        super().__init__(MapLayouts().magic_temple)
        self.music_file_path = tantegel_castle_courtyard_music
        self.staircases = {(6, 2): {'map': 'Alefgard'}}
        self.assign_stair_directions()
        self.set_town_to_overworld_warps()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value

    def set_characters_initial_directions(self):
        self.set_character_initial_direction('WISE_MAN', Direction.LEFT)


# Lookup of all map names with their associated class
map_lookup = {map_name: map_class for map_name, map_class in inspect.getmembers(sys.modules[__name__], inspect.isclass)}
