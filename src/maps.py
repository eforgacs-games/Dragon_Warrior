import inspect
import sys
from abc import ABC
from typing import Callable, Dict

from pygame.sprite import Group, LayeredDirty
from pygame.transform import scale

from src.common import Graphics
from src.direction import Direction
from src.directories import Directories
from src.map_layouts import MapLayouts
from src.maps_functions import parse_map_tiles, warp_line, parse_animated_sprite_sheet, get_center_point
from src.sprites.animated_sprite import AnimatedSprite
from src.sprites.base_sprite import BaseSprite
from src.sprites.fixed_character import FixedCharacter
from src.sprites.roaming_character import RoamingCharacter

all_impassable_tiles = (
    'ROOF', 'WALL', 'WOOD', 'DOOR', 'WEAPON_SIGN', 'INN_SIGN', 'MOUNTAINS', 'WATER', 'BOTTOM_COAST',
    'BOTTOM_LEFT_COAST', 'LEFT_COAST', 'TOP_LEFT_COAST', 'TOP_COAST', 'TOP_RIGHT_COAST', 'RIGHT_COAST',
    'BOTTOM_RIGHT_COAST', 'BOTTOM_TOP_LEFT_COAST', 'BOTTOM_TOP_COAST', 'BOTTOM_TOP_RIGHT_COAST',
    'KING_LORIK', 'GUARD', 'MAN', 'WOMAN', 'WISE_MAN', 'SOLDIER', 'MERCHANT')


class DragonWarriorMap:
    def __init__(self, layout, config, music_file_path, initial_coordinates, last_map=None, staircases=None):

        self.config = config
        self.directories = Directories(config)
        self.graphics = Graphics(config)
        self.is_dark = None
        self.music_file_path = music_file_path
        self.destination_coordinates = None
        self.identifier = self.__class__.__name__

        # Character variables

        self.tile_types_in_current_map = []
        self.scale = self.config['SCALE']
        self.player = None
        self.player_sprites = None
        self.characters = {}
        self.fixed_characters = []
        self.roaming_characters = []
        self.roaming_character_list = []

        # Map variables

        self.initial_coordinates = initial_coordinates
        self.tiles_in_current_loaded_map = None
        self.layout = layout
        self.center_pt = None
        self.map_tiles = parse_map_tiles(map_path=self.directories.MAP_TILES_PATH,
                                         tile_size=config['TILE_SIZE'],
                                         graphics=self.graphics,
                                         configured_scale=config['SCALE'])
        self.impassable_tiles = all_impassable_tiles
        self.custom_underlying_tiles = {}
        self.npc_coordinates = {}
        self.tile_group_dict = {}
        if staircases is None:
            staircases = {}
        self.staircases = staircases
        self.height = len(self.layout) * config['TILE_SIZE']
        self.width = len(self.layout[0]) * config['TILE_SIZE']
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
            'HERO': {'val': 33, 'path': self.directories.UNARMED_HERO_PATH},
            'KING_LORIK': {'val': 34, 'path': self.directories.KING_LORIK_PATH},
            'GUARD': {'val': 35, 'path': self.directories.GUARD_PATH},
            'MAN': {'val': 36, 'path': self.directories.MAN_PATH},
            'WOMAN': {'val': 37, 'path': self.directories.WOMAN_PATH},
            'WISE_MAN': {'val': 38, 'path': self.directories.WISE_MAN_PATH},
            'SOLDIER': {'val': 39, 'path': self.directories.SOLDIER_PATH},
            'MERCHANT': {'val': 40, 'path': self.directories.MERCHANT_PATH},
            'PRINCESS_GWAELIN': {'val': 41, 'path': self.directories.PRINCESS_GWAELIN_PATH},
            'DRAGONLORD': {'val': 42, 'path': self.directories.DRAGONLORD_PATH}
        }
        for character, character_dict in self.character_key.items():
            if character in ('KING_LORIK', 'PRINCESS_GWAELIN'):
                character_dict['four_sided'] = False
            else:
                character_dict['four_sided'] = True
            character_dict['roaming'] = False
            character_dict['direction'] = Direction.DOWN.value
            if character == 'HERO':
                character_dict['underlying_tile'] = self.hero_underlying_tile()
            else:
                character_dict['underlying_tile'] = 'BRICK'
        self.tile_key = dict(list(self.floor_tile_key.items()) + list(self.character_key.items()))
        self._tile_key_list = list(self.tile_key.keys())

    def get_tile_by_value(self, position: int) -> str:
        """Returns the tile name from the integer value associated with it."""
        return self._tile_key_list[position]

    def load_map(self, player, destination_coordinates, tile_size) -> None:
        self.destination_coordinates = destination_coordinates
        self.tile_types_in_current_map = self.get_tiles_in_current_map()
        self.impassable_tiles = tuple(self.tile_types_in_current_map & set(all_impassable_tiles))
        for row in range(len(self.layout)):
            for column in range(len(self.layout[row])):
                self.center_pt = get_center_point(column, row, tile_size=tile_size)
                self.map_floor_tiles(column, row)
        for (npc_row, npc_col), character_name in self.npc_coordinates.items():
            self.center_pt = get_center_point(npc_col, npc_row, tile_size=tile_size)
            char_dict = self.character_key[character_name]
            identifier = self.set_identifiers_for_duplicate_characters(character_name)
            self.map_npc(identifier, char_dict.get('direction'), char_dict['underlying_tile'],
                         char_dict['path'], char_dict['four_sided'],
                         (npc_row, npc_col), identifier in self.roaming_character_list)
        hero_coords = destination_coordinates if destination_coordinates else self.initial_coordinates
        if hero_coords:
            hero_row, hero_col = hero_coords
            self.center_pt = get_center_point(hero_col, hero_row, tile_size=tile_size)
            AnimatedSprite.__init__(player, self.center_pt, player.direction_value,
                                    images=self.scale_sprite_sheet(self.directories.UNARMED_HERO_PATH),
                                    identifier='HERO')
            self.map_player(self.character_key['HERO']['underlying_tile'], player, hero_coords)
        self.set_characters_initial_directions()

    def get_tiles_in_current_map(self) -> set:
        return set(self.get_tile_by_value(tile) for row in self.layout for tile in row)

    def set_identifiers_for_duplicate_characters(self, character):
        character_count = [character_dict['tile_value'] for character_dict in self.characters.values()].count(
            self.character_key[character]['val']) + 1
        if character_count > 1:
            character = f'{character}_{character_count}'
        return character

    def scale_sprite_sheet(self, image_path):
        return parse_animated_sprite_sheet(scale(self.graphics.get_image(image_path), (
            self.graphics.get_image(image_path).get_width() * self.scale,
            self.graphics.get_image(image_path).get_height() * self.scale)), self.config)

    def map_npc(self, identifier, direction, underlying_tile, image_path, four_sided, coordinates,
                is_roaming) -> None:
        sheet = self.graphics.get_image(image_path)
        character_sprites: LayeredDirty = LayeredDirty()
        sheet = scale(sheet, (sheet.get_width() * self.scale, sheet.get_height() * self.scale))
        images = parse_animated_sprite_sheet(sheet, self.config)
        character: RoamingCharacter | FixedCharacter | AnimatedSprite
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
            character.row, character.column = coordinates  # type: ignore[attr-defined]
            self.fixed_characters.append(character)
        character_sprites.add(character)
        tile_value = \
            self.character_key["_".join(identifier.split("_")[0:-1]) if identifier[-1].isdigit() else identifier][
                'val']
        self.characters[character.identifier] = {'character': character,
                                                 'character_sprites': character_sprites,
                                                 'tile_value': tile_value,
                                                 'coordinates': coordinates
                                                 }
        if self.custom_underlying_tiles and self.custom_underlying_tiles.get(character.identifier):
            self.add_tile(self.floor_tile_key[self.custom_underlying_tiles[character.identifier]], self.center_pt)
        else:
            self.add_tile(self.floor_tile_key[underlying_tile], self.center_pt)

    def map_player(self, underlying_tile, player, coordinates) -> None:
        self.player_sprites = LayeredDirty(player)
        player.direction_value = self.hero_initial_direction()
        self.add_tile(self.floor_tile_key[underlying_tile], self.center_pt)
        self.characters['HERO'] = {'character': player,
                                   'character_sprites': self.player_sprites,
                                   'tile_value': self.character_key['HERO']['val'],
                                   'coordinates': coordinates}

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
        else:
            tile = None
        self.floor_tile_key[self.get_tile_by_value(tile_value)]['group'].add(tile)

    @property
    def hero_underlying_tile(self):
        raise NotImplementedError("Method not implemented.")

    @property
    def hero_initial_direction(self):
        raise NotImplementedError("Method not implemented")

    def set_characters_initial_directions(self) -> None:
        raise NotImplementedError("Method not implemented")

    def apply_dragonlord_defeated(self) -> None:
        """Change the map for after the Dragonlord's defeat (NES F_DGNLRD_DEAD), before it's loaded. Most maps don't
        change."""

    def set_character_initial_direction(self, character_identifier, direction) -> None:
        if self.characters.get(character_identifier):
            self.characters[character_identifier]['character'].direction_value = direction.value

    def set_town_to_overworld_warps(self) -> None:
        """Sets the exit location to the overworld (Alefgard) from within a town"""
        for staircase_dict in self.staircases.values():
            if staircase_dict['map'] == 'Alefgard':
                alefgard_staircases = Alefgard(self.config).staircases
                # Find the Alefgard staircase that leads to this town
                for alefgard_coordinates, alefgard_staircase_dict in alefgard_staircases.items():
                    if alefgard_staircase_dict['map'] == self.__class__.__name__:
                        staircase_dict['destination_coordinates'] = alefgard_coordinates
                        break

    def create_town_gates(self, north_gate=None, east_gate=None, west_gate=None, south_gate=None) -> None:
        alefgard_up_staircase = {'map': 'Alefgard', 'stair_direction': 'up'}
        staircases_keys: list[tuple] = []
        staircases_keys += north_gate if north_gate is not None else []
        staircases_keys += east_gate if east_gate is not None else []
        staircases_keys += west_gate if west_gate is not None else []
        staircases_keys += south_gate if south_gate is not None else []
        staircases_values = [alefgard_up_staircase] * len(staircases_keys)
        if not self.staircases:
            self.staircases = {}
            self.staircases = dict(zip(staircases_keys, staircases_values))
        else:
            self.staircases.update(dict(zip(staircases_keys, staircases_values)))

    def assign_stair_directions(self):
        for staircase_coordinates, staircase_dict in self.staircases.items():
            layout_staircase_coordinates = self.layout[staircase_coordinates[0]][staircase_coordinates[1]]
            if layout_staircase_coordinates == 6:
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


class CaveMap(DragonWarriorMap, ABC):
    def __init__(self, layout, config, music_file_path, initial_coordinates, staircases=None):
        super().__init__(layout, config, music_file_path, initial_coordinates,
                         staircases=staircases)
        self.is_dark = True


class TantegelThroneRoom(DragonWarriorMap):
    """
    This is the first map in the game, the Tantegel Castle throne room.
    """

    def __init__(self, config):
        super().__init__(MapLayouts().tantegel_throne_room, config,
                         Directories(config).tantegel_castle_throne_room_music, (10, 13),
                         staircases={
                             (14, 18): {'map': 'TantegelCourtyard', 'destination_coordinates': (14, 14),
                                        'direction': Direction.RIGHT.value}})
        self.npc_coordinates = {
            (9, 13): 'KING_LORIK',
            (11, 16): 'GUARD',
            (12, 13): 'GUARD',
            (12, 15): 'GUARD',
        }
        self.assign_stair_directions()
        self.roaming_character_list = ['GUARD']

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.UP.value

    def set_characters_initial_directions(self):
        self.set_character_initial_direction('GUARD_2', Direction.RIGHT)
        self.set_character_initial_direction('GUARD_3', Direction.LEFT)


class TantegelCourtyard(DragonWarriorMap):
    """
    This is the courtyard of Tantegel Castle.
    """

    def __init__(self, config):
        super().__init__(MapLayouts().tantegel_courtyard, config, Directories(config).tantegel_castle_courtyard_music,
                         (14, 14))
        self.create_town_gates(
            # does the north gate change later on?
            north_gate=warp_line((6, 6), (6, 35)),
            west_gate=warp_line((6, 6), (37, 6)),
            east_gate=warp_line((6, 37), (37, 37)),
            south_gate=warp_line((37, 9), (37, 26)))
        self.staircases[(14, 14)] = {'map': 'TantegelThroneRoom', 'destination_coordinates': (14, 18),
                                     'direction': Direction.LEFT.value}
        # NES MapEntryTbl/MapTargetTbl: Tant castle GF(29,29) -> Tant castle SL(0,4)
        self.staircases[(36, 36)] = {'map': 'TantegelCellar', 'destination_coordinates': (5, 1)}
        self.npc_coordinates = {
            (8, 31): 'MERCHANT',
            (12, 34): 'WOMAN',
            (13, 15): 'GUARD',
            (15, 9): 'MAN',
            (15, 15): 'GUARD',
            (18, 18): 'MAN',
            (19, 9): 'GUARD',
            (20, 15): 'WOMAN',
            (27, 22): 'GUARD',
            (28, 29): 'SOLDIER',
            (31, 14): 'MERCHANT',
            (32, 13): 'MERCHANT',
            (33, 27): 'WISE_MAN',
            (34, 16): 'GUARD',
            (34, 19): 'GUARD',
        }
        self.assign_stair_directions()
        self.set_town_to_overworld_warps()
        self.roaming_character_list = ['MAN_2', 'GUARD_3', 'WOMAN_2', 'MERCHANT_2', 'MERCHANT_3']
        self.custom_underlying_tiles = {
            'WOMAN': 'GRASS',
            'WOMAN_2': 'GRASS'
        }
        self.dragonlord_defeated = False

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value

    def apply_dragonlord_defeated(self):
        """NES GetNPCDataPointer: after the Dragonlord's defeat, the ground floor loads TaDLMobTbl and TaDLStatTbl.
        King Lorik waits in front of the throne room stairs between two rows of guards (with trumpets in the NES's
        last frame; there's no sprite for those, so they're plain guards). NES (x, y) is (y + 7, x + 7) here."""
        self.dragonlord_defeated = True
        self.npc_coordinates = {
            # TaDLStatTbl
            (14, 18): 'KING_LORIK',
            (16, 16): 'GUARD', (18, 16): 'GUARD', (20, 16): 'GUARD',  # trumpet guards, GUARD to GUARD_3
            (16, 19): 'GUARD', (18, 19): 'GUARD', (20, 19): 'GUARD',  # trumpet guards, GUARD_4 to GUARD_6
            (34, 16): 'GUARD', (34, 19): 'GUARD',  # gate guards, GUARD_7 and GUARD_8
            # TaDLMobTbl
            (9, 26): 'GUARD', (25, 25): 'GUARD', (19, 9): 'GUARD',  # GUARD_9 to GUARD_11
            (30, 21): 'MAN',
            (18, 32): 'SOLDIER', (28, 31): 'SOLDIER',
            (32, 13): 'MERCHANT',
        }
        self.roaming_character_list = ['GUARD_9', 'GUARD_10', 'GUARD_11', 'MAN', 'SOLDIER', 'SOLDIER_2', 'MERCHANT']
        self.custom_underlying_tiles = {}

    def set_characters_initial_directions(self):
        if self.dragonlord_defeated:
            self.set_character_initial_direction('GUARD_7', Direction.RIGHT)
            self.set_character_initial_direction('GUARD_8', Direction.LEFT)
            return
        self.set_character_initial_direction('GUARD_2', Direction.UP)
        self.set_character_initial_direction('GUARD_4', Direction.RIGHT)
        self.set_character_initial_direction('GUARD_5', Direction.RIGHT)
        self.set_character_initial_direction('GUARD_6', Direction.LEFT)
        self.set_character_initial_direction('WISE_MAN', Direction.LEFT)


class TantegelCellar(BasementWithNPCs):
    """Tantegel Castle's sublevel (NES MAP_TANTCSTL_SL). Layout coordinates are the NES ones + (1, 1)."""

    def __init__(self, config):
        super().__init__(MapLayouts().tantegel_underground, config, Directories(config).tantegel_castle_courtyard_music,
                         (5, 1), staircases={
                # NES MapTargetTbl: Tant castle SL(0,4) -> Tant castle GF(29,29)
                (5, 1): {'map': 'TantegelCourtyard', 'destination_coordinates': (36, 36)}})
        self.npc_coordinates = {
            (7, 5): 'WISE_MAN',
        }
        self.assign_stair_directions()

    def set_characters_initial_directions(self):
        self.set_character_initial_direction('WISE_MAN', Direction.DOWN)


class CharlockB1(MapWithoutNPCs):
    """Ground floor of Charlock Castle (NES MAP_DLCSTL_GF), with the Dragonlord's empty throne.

    Layout coordinates are the NES ones offset by (row + 6, column + 7)."""

    # NES DoSearch (SrchPassage): searching on the throne at GF(10,3) only hints at the wind; the secret passage is
    # behind it at GF(10,1).
    THRONE_COORDINATES = (9, 17)
    HIDDEN_STAIRCASE_COORDINATES = (7, 17)
    # NES MapEntryTbl/MapTargetTbl: DL castle GF(10,1) -> DL castle SL1(9,0).
    HIDDEN_STAIRCASE = {'map': 'CharlockB2', 'destination_coordinates': (3, 12)}  # A

    def __init__(self, config):
        # The hidden staircase (A) is only added by reveal_hidden_staircase(), so it can't be taken before it's found.
        super().__init__(MapLayouts().charlock_b1, config, Directories(config).dungeon_floor_1_music,
                         (25, 17), staircases={
                (20, 11): {'map': 'CharlockB2', 'destination_coordinates': (16, 11)},  # B: GF(4,14) -> SL1(8,13)
                (20, 22): {'map': 'CharlockB2', 'destination_coordinates': (18, 20)}  # C: GF(15,14) -> SL1(17,15)
            })
        self.create_town_gates(south_gate=(warp_line((26, 15), (26, 18))))
        self.set_town_to_overworld_warps()
        self.assign_stair_directions()

    def reveal_hidden_staircase(self):
        """Turn the force field behind the throne into the stairs down to CharlockB2 (NES DoSearch, F_PSG_FOUND)."""
        row, column = self.HIDDEN_STAIRCASE_COORDINATES
        self.layout[row][column] = self.floor_tile_key['BRICK_STAIR_DOWN']['val']
        self.staircases[self.HIDDEN_STAIRCASE_COORDINATES] = {**self.HIDDEN_STAIRCASE, 'stair_direction': 'down'}

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.UP.value


class CharlockB2(BasementWithoutNPCs, CaveMap):
    """First basement of Charlock Castle (NES MAP_DLCSTL_SL1). Layout coordinates are the NES ones + (3, 3)."""

    def __init__(self, config):
        super().__init__(MapLayouts().charlock_b2, config, Directories(config).dungeon_floor_2_music, (3, 12),
                         staircases={
                             # Up to CharlockB1 (NES MapTargetTbl: DL castle SL1 -> DL castle GF)
                             (3, 12): {'map': 'CharlockB1', 'destination_coordinates': (7, 17)},  # A
                             (16, 11): {'map': 'CharlockB1', 'destination_coordinates': (20, 11)},  # B
                             (18, 20): {'map': 'CharlockB1', 'destination_coordinates': (20, 22)},  # C
                             # Down to CharlockB3 (NES MapEntryTbl: DL castle SL1 -> DL castle SL2)
                             (7, 5): {'map': 'CharlockB3', 'destination_coordinates': (3, 3)},  # D
                             (17, 5): {'map': 'CharlockB3', 'destination_coordinates': (4, 3)},  # E
                             (4, 18): {'map': 'CharlockB3', 'destination_coordinates': (3, 11)},  # F
                             (10, 16): {'map': 'CharlockB3', 'destination_coordinates': (7, 7)},  # G
                             (10, 22): {'map': 'CharlockB3', 'destination_coordinates': (11, 12)},  # H
                             (12, 17): {'map': 'CharlockB3', 'destination_coordinates': (12, 11)},  # I
                             (22, 11): {'map': 'CharlockB3', 'destination_coordinates': (3, 8)}})  # J
        self.assign_stair_directions()


class CharlockB3(BasementWithoutNPCs, CaveMap):
    def __init__(self, config):
        super().__init__(MapLayouts().charlock_b3, config, Directories(config).dungeon_floor_3_music, (3, 8),
                         staircases={
                             # Up to CharlockB2 (NES MapTargetTbl: DL castle SL2 -> DL castle SL1)
                             (3, 3): {'map': 'CharlockB2', 'destination_coordinates': (7, 5)},  # D
                             (4, 3): {'map': 'CharlockB2', 'destination_coordinates': (17, 5)},  # E
                             (3, 11): {'map': 'CharlockB2', 'destination_coordinates': (4, 18)},  # F
                             (7, 7): {'map': 'CharlockB2', 'destination_coordinates': (10, 16)},  # G
                             (11, 12): {'map': 'CharlockB2', 'destination_coordinates': (10, 22)},  # H
                             (12, 11): {'map': 'CharlockB2', 'destination_coordinates': (12, 17)},  # I
                             (3, 8): {'map': 'CharlockB2', 'destination_coordinates': (22, 11)},  # J
                             (3, 6): {'map': 'CharlockB4', 'destination_coordinates': (3, 10)},  # K
                             (4, 12): {'map': 'CharlockB4', 'destination_coordinates': (5, 5)},  # L
                             (11, 3): {'map': 'CharlockB4', 'destination_coordinates': (7, 8)},  # M
                             (12, 4): {'map': 'CharlockB4', 'destination_coordinates': (12, 3)},  # N
                         })
        self.assign_stair_directions()


class CharlockB4(BasementWithoutNPCs, CaveMap):
    def __init__(self, config):
        super().__init__(MapLayouts().charlock_b4, config, Directories(config).dungeon_floor_4_music, (3, 10),
                         staircases={
                             (3, 10): {'map': 'CharlockB3', 'destination_coordinates': (3, 6)},  # K
                             (5, 5): {'map': 'CharlockB3', 'destination_coordinates': (4, 12)},  # L
                             (7, 8): {'map': 'CharlockB3', 'destination_coordinates': (11, 3)},  # M
                             (12, 3): {'map': 'CharlockB3', 'destination_coordinates': (12, 4)},  # N
                             (9, 4): {'map': 'CharlockB5', 'destination_coordinates': (12, 3)},  # O
                             (10, 10): {'map': 'CharlockB5', 'destination_coordinates': (10, 10)},  # P

                         })
        self.assign_stair_directions()


class CharlockB5(BasementWithoutNPCs, CaveMap):
    def __init__(self, config):
        super().__init__(MapLayouts().charlock_b5, config, Directories(config).dungeon_floor_5_music, (12, 3),
                         staircases={
                             (4, 11): {'map': 'CharlockB6', 'destination_coordinates': (3, 7)},  # R
                             (5, 5): {'map': 'CharlockB6', 'destination_coordinates': (3, 12)},  # Q
                             (10, 10): {'map': 'CharlockB4', 'destination_coordinates': (10, 10)},  # P
                             (12, 3): {'map': 'CharlockB4', 'destination_coordinates': (9, 4)}  # O
                         })
        self.assign_stair_directions()


class CharlockB6(BasementWithoutNPCs, CaveMap):
    def __init__(self, config):
        super().__init__(MapLayouts().charlock_b6, config, Directories(config).dungeon_floor_6_music, (3, 12),
                         staircases={
                             (3, 12): {'map': 'CharlockB5', 'destination_coordinates': (5, 5)},  # Q
                             (3, 7): {'map': 'CharlockB5', 'destination_coordinates': (4, 11)},  # R
                             (3, 3): {'map': 'CharlockB7Wide', 'destination_coordinates': (5, 3)},  # T
                             (8, 8): {'map': 'CharlockB7Narrow', 'destination_coordinates': (3, 3)},  # S
                         })
        self.assign_stair_directions()


class CharlockB7Wide(BasementWithoutNPCs, CaveMap):
    """A wide hallway right before the last level of Charlock Castle.

    The lower corridor of NES MAP_DLCSTL_SL6: layout coordinates are the NES ones + (-1, 3)."""

    def __init__(self, config):
        super().__init__(MapLayouts().charlock_b7_wide, config, Directories(config).dungeon_floor_7_music, (5, 3),
                         staircases={
                             (5, 3): {'map': 'CharlockB6', 'destination_coordinates': (3, 3)},  # T
                             # NES MapEntryTbl/MapTargetTbl: DL castle SL6(9,6) -> DL castle BF(10,29)
                             (5, 12): {'map': 'CharlockB8', 'destination_coordinates': (33, 16)}  # U
                         })
        self.assign_stair_directions()


class CharlockB7Narrow(BasementWithoutNPCs, CaveMap):
    """A dead end path in Charlock Castle that loops unto itself."""

    def __init__(self, config):
        super().__init__(MapLayouts().charlock_b7_narrow, config, Directories(config).dungeon_floor_7_music, (3, 3),
                         staircases={
                             (3, 3): {'map': 'CharlockB6', 'destination_coordinates': (8, 8)},
                             # NES MapEntryTbl: DL castle SL6(9,0) -> DL castle SL6(0,0), a one-way loop (going up
                             # from SL6(0,0) finds its earlier MapTargetTbl entry, back to SL5(5,5))
                             (3, 12): {'map': 'CharlockB7Narrow', 'destination_coordinates': (3, 3)}
                         })
        self.assign_stair_directions()


class CharlockB8(DragonWarriorMap):
    """Deepest level of Charlock Castle, and location of the Dragonlord (NES MAP_DLCSTL_BF).

    Layout coordinates are the NES ones offset by (row + 4, column + 6)."""

    def __init__(self, config):
        super().__init__(MapLayouts().charlock_b8, config, Directories(config).dungeon_floor_8_music,
                         (33, 16), staircases={
                # NES MapTargetTbl/MapEntryTbl: DL castle BF(10,29) -> DL castle SL6(9,6)
                (33, 16): {'map': 'CharlockB7Wide', 'destination_coordinates': (5, 12)}})
        self.npc_coordinates = {
            (28, 22): 'DRAGONLORD',
        }
        self.assign_stair_directions()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value

    def apply_dragonlord_defeated(self):
        # NES LoadMobNPCDataLoop: the Dragonlord NPC isn't loaded once he's been defeated
        self.npc_coordinates = {}

    def set_characters_initial_directions(self):
        self.set_character_initial_direction('DRAGONLORD', Direction.DOWN)


class Alefgard(MapWithoutNPCs):
    """
    This is Alefgard, the world by which the player travels between castles, villages, and dungeons.
    """

    def __init__(self, config):
        super().__init__(MapLayouts().alefgard, config, Directories(config).overworld_music,
                         (50, 51), staircases={
                # (row, column)
                # castles
                (50, 51): {'map': 'TantegelCourtyard', 'destination_coordinates': (36, 18),
                           'direction': Direction.UP.value},
                (55, 56): {'map': 'CharlockB1', 'destination_coordinates': (25, 17)},
                # villages
                (48, 56): {'map': 'Brecconary', 'destination_coordinates': (23, 10)},
                (9, 10): {'map': 'Garinham', 'destination_coordinates': (14, 9)},
                (17, 112): {'map': 'Kol', 'destination_coordinates': (30, 29)},
                # cave
                (19, 36): {'map': 'ErdricksCaveB1', 'destination_coordinates': (3, 3)},
                (51, 112): {'map': 'SwampCave', 'destination_coordinates': (6, 4)},
                (56, 112): {'map': 'SwampCave', 'destination_coordinates': (35, 4)},
                (64, 37): {'map': 'MountainCaveB1', 'destination_coordinates': (8, 1)},
                (96, 33): {'map': 'Hauksness', 'destination_coordinates': (18, 9)},
                (79, 110): {'map': 'Rimuldar', 'destination_coordinates': (22, 37)},
                (109, 81): {'map': 'Cantlin', 'destination_coordinates': (8, 15)},
                (116, 116): {'map': 'MagicTemple', 'destination_coordinates': (6, 2)},
                (8, 89): {'map': 'StaffOfRainCave', 'destination_coordinates': (11, 6)},
            })
        for staircase_dict in self.staircases.values():
            staircase_dict['stair_direction'] = 'up'

    def hero_underlying_tile(self):
        return 'CASTLE'

    def hero_initial_direction(self):
        return Direction.DOWN.value if self.character_key['HERO'][
                                           'underlying_tile'] != 'GRASS_STAIR_DOWN' else Direction.LEFT.value


class Brecconary(DragonWarriorMap):

    def __init__(self, config):
        super().__init__(MapLayouts().brecconary, config, Directories(config).village_music,
                         (23, 10))
        self.create_town_gates(north_gate=warp_line((7, 23), (7, 26)),
                               east_gate=warp_line((21, 40), (25, 40)),
                               west_gate=warp_line((21, 9), (24, 9)))
        self.set_town_to_overworld_warps()
        self.npc_coordinates = {
            (9, 38): 'SOLDIER',
            (12, 15): 'MERCHANT',
            (12, 34): 'WOMAN',
            (15, 14): 'WOMAN',
            (18, 30): 'MAN',
            (18, 34): 'WISE_MAN',
            (21, 11): 'MAN',
            (29, 20): 'MERCHANT',
            (31, 30): 'MAN',
            (33, 35): 'MERCHANT',
            (34, 13): 'SOLDIER',
            (34, 20): 'GUARD',
        }
        self.custom_underlying_tiles = {
            'SOLDIER': 'TREES',
            'WOMAN': 'BRICK',
            'WOMAN_2': 'GRASS',
            'MAN_2': 'TREES',
            'MAN_3': 'GRASS',
        }

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.RIGHT.value

    def set_characters_initial_directions(self):
        self.set_character_initial_direction('MERCHANT_2', Direction.LEFT)
        self.set_character_initial_direction('WOMAN', Direction.LEFT)
        self.set_character_initial_direction('MAN_3', Direction.UP)
        self.set_character_initial_direction('MERCHANT_3', Direction.LEFT)
        self.set_character_initial_direction('GUARD', Direction.UP)


class Garinham(DragonWarriorMap):

    def __init__(self, config):
        super().__init__(MapLayouts().garinham, config, Directories(config).village_music, (14, 9),
                         staircases={
                             (0, 28): {'map': 'GarinsGraveB1', 'destination_coordinates': (12, 7),
                                       'stair_direction': 'down'},
                         })
        self.create_town_gates(west_gate=warp_line((13, 8), (15, 8)),
                               east_gate=warp_line((11, 29), (14, 29)))
        self.set_town_to_overworld_warps()
        self.npc_coordinates = {
            (1, 23): 'WISE_MAN',
            (5, 12): 'GUARD',
            (5, 14): 'GUARD',
            (6, 18): 'MERCHANT',
            (10, 11): 'WISE_MAN',
            (11, 14): 'MERCHANT',
            (12, 20): 'WOMAN',
            (15, 26): 'MERCHANT',
            (17, 11): 'WISE_MAN',
            (18, 19): 'MERCHANT',
        }
        self.custom_underlying_tiles = {
            'WOMAN': 'TREES',
            'WISE_MAN': 'SAND',
        }
        self.roaming_character_list = ['WOMAN', 'WISE_MAN_2']

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.RIGHT.value

    def set_characters_initial_directions(self):
        self.set_character_initial_direction('MERCHANT_2', Direction.LEFT)
        self.set_character_initial_direction('MERCHANT_3', Direction.LEFT)
        self.set_character_initial_direction('MERCHANT_4', Direction.UP)
        self.set_character_initial_direction('WISE_MAN_2', Direction.RIGHT)
        self.set_character_initial_direction('WISE_MAN_3', Direction.RIGHT)
        self.set_character_initial_direction('GUARD', Direction.RIGHT)
        self.set_character_initial_direction('GUARD_2', Direction.LEFT)


class Kol(DragonWarriorMap):

    def __init__(self, config):
        super().__init__(MapLayouts().kol, config, Directories(config).village_music, (30, 29))
        self.create_town_gates(north_gate=warp_line((7, 8), (7, 33)),
                               east_gate=warp_line((7, 33), (32, 33)),
                               west_gate=warp_line((7, 8), (32, 8)),
                               south_gate=warp_line((32, 8), (32, 33)))
        self.set_town_to_overworld_warps()
        self.npc_coordinates = {
            (9, 11): 'WISE_MAN',
            (9, 22): 'WOMAN',
            (12, 29): 'MERCHANT',
            (14, 16): 'SOLDIER',
            (16, 29): 'WISE_MAN',
            (17, 23): 'GUARD',
            (20, 15): 'MAN',
            (20, 32): 'MERCHANT',
            (21, 30): 'SOLDIER',
            (22, 24): 'MAN',
            (23, 21): 'WOMAN',
            (27, 30): 'WISE_MAN',
            (29, 24): 'MERCHANT',
            (31, 11): 'GUARD',
        }
        self.custom_underlying_tiles = {
            'WOMAN': 'TREES',
            'WOMAN_2': 'SAND',
            'MAN': 'TREES',
            'MAN_2': 'SAND',
            'SOLDIER': 'TREES',
            'GUARD': 'SAND',
            'WISE_MAN_2': 'GRASS',
            'WISE_MAN_3': 'SAND'
        }
        self.roaming_character_list = ['WISE_MAN_2', 'WOMAN_2', 'MAN', 'MAN_2', 'SOLDIER', 'GUARD', 'WISE_MAN_2',
                                       'WISE_MAN_3']

    def hero_underlying_tile(self):
        return 'SAND'

    def hero_initial_direction(self):
        return Direction.UP.value

    def set_characters_initial_directions(self):
        self.set_character_initial_direction('MERCHANT', Direction.UP)
        self.set_character_initial_direction('MERCHANT_2', Direction.LEFT)
        self.set_character_initial_direction('MERCHANT_3', Direction.LEFT)


class Rimuldar(DragonWarriorMap):

    def __init__(self, config):
        super().__init__(MapLayouts().rimuldar, config, Directories(config).village_music, (14, 9))
        self.create_town_gates(north_gate=warp_line((6, 0), (6, len(self.layout[0]))),
                               east_gate=warp_line((0, 38), (len(self.layout), 38)),
                               west_gate=warp_line((0, 7), (len(self.layout), 7)),
                               south_gate=warp_line((36, 0), (36, len(self.layout[0]))))
        self.set_town_to_overworld_warps()
        self.npc_coordinates = {
            (12, 10): 'MERCHANT',
            (15, 12): 'WISE_MAN',
            (15, 31): 'MERCHANT',
            (16, 23): 'WOMAN',
            (21, 14): 'WISE_MAN',
            (26, 24): 'MERCHANT',
            (31, 11): 'WISE_MAN',
            (31, 28): 'WISE_MAN',
        }
        self.custom_underlying_tiles = {
            'MERCHANT': 'GRASS',
            'WISE_MAN_2': 'GRASS'
        }

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.LEFT.value

    def set_characters_initial_directions(self):
        self.set_character_initial_direction('WISE_MAN', Direction.UP)
        self.set_character_initial_direction('WISE_MAN_2', Direction.LEFT)
        self.set_character_initial_direction('WISE_MAN_3', Direction.RIGHT)
        self.set_character_initial_direction('MERCHANT', Direction.UP)
        self.set_character_initial_direction('MERCHANT_3', Direction.RIGHT)
        self.set_character_initial_direction('WOMAN', Direction.UP)


class Hauksness(MapWithoutNPCs):

    def __init__(self, config):
        super().__init__(MapLayouts().hauksness, config, Directories(config).dungeon_floor_4_music,
                         (18, 9))
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

    def __init__(self, config):
        super().__init__(MapLayouts().cantlin, config, Directories(config).village_music, (8, 15))
        self.create_town_gates(north_gate=warp_line((7, 0), (7, 29))
                               # west_gate = warp_line((21, 9), (24, 9))
                               # east_gate = warp_line((21, 40), (25, 40))
                               )
        self.set_town_to_overworld_warps()
        # NES CantMobTbl and CantStatTbl (Bank00). An NPC at NES X,Y is at (Y + 8, X) here.
        self.npc_coordinates = {
            (11, 8): 'MERCHANT',  # static shopkeeper at 8,3: the inn (dialog byte $14)
            (13, 22): 'MERCHANT',  # mobile shopkeeper at 22,5: weapons and armor shop 1 ($03)
            (14, 5): 'GUARD',  # mobile guard at 5,6 ($60)
            (14, 15): 'GUARD',  # mobile guard at 15,6 ($48)
            (14, 27): 'WISE_MAN',  # static wizard at 27,6: magic keys ($0C)
            (15, 2): 'MAN',  # static male villager at 2,7: item shop 1 ($0A)
            (17, 22): 'GUARD',  # mobile guard at 22,9 ($4D)
            (20, 2): 'MERCHANT',  # static shopkeeper at 2,12 ($45)
            (20, 7): 'MERCHANT',  # static shopkeeper at 7,12: item shop 2 ($0B)
            (20, 24): 'GUARD',  # static guard at 24,12: weapons and armor shop 3 ($05)
            (21, 22): 'WOMAN',  # static female villager at 22,13: Fairy Water ($10)
            (22, 4): 'WOMAN',  # mobile female villager at 4,14 ($49)
            (23, 20): 'MAN',  # mobile male villager at 20,15 ($4B)
            (24, 9): 'WOMAN',  # mobile female villager at 9,16 ($4A)
            (24, 15): 'WISE_MAN',  # static wizard at 15,16 ($46)
            (25, 25): 'MERCHANT',  # mobile shopkeeper at 25,17 ($4C)
            (30, 22): 'WISE_MAN',  # static wizard at 22,22 ($47)
            (34, 3): 'MERCHANT',  # mobile shopkeeper at 3,26 ($4E)
            (34, 27): 'MERCHANT',  # static shopkeeper at 27,26: weapons and armor shop 2 ($04)
            (36, 14): 'WISE_MAN',  # mobile wizard at 14,28 ($6B)
        }
        self.custom_underlying_tiles = {
            'WISE_MAN_2': 'GRASS'
        }
        # The NPCs from CantMobTbl
        self.roaming_character_list = ['MERCHANT_2', 'GUARD', 'GUARD_2', 'GUARD_3', 'WOMAN_2', 'MAN_2', 'WOMAN_3',
                                       'MERCHANT_5', 'MERCHANT_6', 'WISE_MAN_4']

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.DOWN.value

    def set_characters_initial_directions(self):
        # The DD bits of each NES table entry; every NPC not listed here faces down
        self.set_character_initial_direction('MAN', Direction.RIGHT)
        self.set_character_initial_direction('MERCHANT_3', Direction.RIGHT)
        self.set_character_initial_direction('MERCHANT_4', Direction.LEFT)
        self.set_character_initial_direction('MERCHANT_7', Direction.LEFT)
        self.set_character_initial_direction('WOMAN', Direction.LEFT)
        self.set_character_initial_direction('GUARD_4', Direction.RIGHT)


class ErdricksCaveB1(MapWithoutNPCs, CaveMap):
    def __init__(self, config):
        super().__init__(MapLayouts().erdricks_cave_b1, config, Directories(config).dungeon_floor_1_music, (1, 1),
                         staircases={(3, 3): {'map': 'Alefgard'},
                                     (12, 12): {'map': 'ErdricksCaveB2',
                                                'destination_coordinates': (
                                                    10, 9)}})
        self.assign_stair_directions()
        self.set_town_to_overworld_warps()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class ErdricksCaveB2(MapWithoutNPCs, CaveMap):
    def __init__(self, config):
        super().__init__(MapLayouts().erdricks_cave_b2, config, Directories(config).dungeon_floor_2_music, (10, 9),
                         staircases={
                             (10, 9): {'map': 'ErdricksCaveB1', 'destination_coordinates': (12, 12)}})
        self.assign_stair_directions()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class SwampCave(CaveMap):
    """The Swamp Cave (NES MAP_SWAMPCAVE). Layout coordinates are the NES ones + (6, 4)."""

    def __init__(self, config):
        super().__init__(MapLayouts().swamp_cave, config, Directories(config).dungeon_floor_1_music,
                         # NES MapTargetTbl/MapEntryTbl: Swamp cave(0,0) -> Overworld(104,44) and
                         # Swamp cave(0,29) -> Overworld(104,49), the two cave tiles
                         staircases={(6, 4): {'map': 'Alefgard', 'destination_coordinates': (51, 112)},
                                     (35, 4): {'map': 'Alefgard', 'destination_coordinates': (56, 112)}},
                         initial_coordinates=(6, 4))
        self.npc_coordinates = {
            (24, 9): 'PRINCESS_GWAELIN',
        }
        self.assign_stair_directions()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value

    def set_characters_initial_directions(self):
        pass


class GarinsGraveB1(MapWithoutNPCs, CaveMap):
    def __init__(self, config):
        super().__init__(MapLayouts().garins_grave_b1, config, Directories(config).dungeon_floor_1_music, (12, 7),
                         staircases={
                             (19, 2): {'map': 'GarinsGraveB2', 'destination_coordinates': (3, 12),
                                       'stair_direction': 'down'},
                             (12, 7): {'map': 'Garinham', 'destination_coordinates': (0, 28), 'stair_direction': 'up'},
                         })
        self.assign_stair_directions()
        self.set_town_to_overworld_warps()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class GarinsGraveB2(MapWithoutNPCs, CaveMap):
    def __init__(self, config):
        super().__init__(MapLayouts().garins_grave_b2, config, Directories(config).dungeon_floor_1_music, (3, 12),
                         staircases={
                             (3, 12): {'map': 'GarinsGraveB1', 'destination_coordinates': (19, 2),
                                       'stair_direction': 'up'},  # A
                             (2, 13): {'map': 'GarinsGraveB3', 'destination_coordinates': (2, 19)},  # B
                             (2, 2): {'map': 'GarinsGraveB3', 'destination_coordinates': (2, 15)},  # C
                             (7, 6): {'map': 'GarinsGraveB3', 'destination_coordinates': (12, 7)},  # D
                             (11, 2): {'map': 'GarinsGraveB3', 'destination_coordinates': (18, 3)},  # E
                             (11, 13): {'map': 'GarinsGraveB3', 'destination_coordinates': (14, 19)},  # F

                         })
        self.assign_stair_directions()
        self.set_town_to_overworld_warps()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class GarinsGraveB3(MapWithoutNPCs, CaveMap):
    def __init__(self, config):
        super().__init__(MapLayouts().garins_grave_b3, config, Directories(config).dungeon_floor_1_music, (2, 19),
                         staircases={
                             (2, 19): {'map': 'GarinsGraveB2', 'destination_coordinates': (2, 13),
                                       'stair_direction': 'up'},  # B
                             (2, 15): {'map': 'GarinsGraveB2', 'destination_coordinates': (2, 2),
                                       'stair_direction': 'up'},  # C
                             (12, 7): {'map': 'GarinsGraveB2', 'destination_coordinates': (7, 6),
                                       'stair_direction': 'up'},  # D
                             (18, 3): {'map': 'GarinsGraveB2', 'destination_coordinates': (11, 2),
                                       'stair_direction': 'up'},  # E
                             (14, 19): {'map': 'GarinsGraveB2', 'destination_coordinates': (11, 13),
                                        'stair_direction': 'up'},  # F
                             (6, 10): {'map': 'GarinsGraveB4', 'destination_coordinates': (5, 1),
                                       'stair_direction': 'down'},  # G
                             (10, 11): {'map': 'GarinsGraveB4', 'destination_coordinates': (5, 6),
                                        'stair_direction': 'down'},  # H
                         })
        self.assign_stair_directions()
        self.set_town_to_overworld_warps()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class GarinsGraveB4(MapWithoutNPCs, CaveMap):
    def __init__(self, config):
        super().__init__(MapLayouts().garins_grave_b4, config, Directories(config).dungeon_floor_1_music, (5, 1),
                         staircases={
                             (5, 1): {'map': 'GarinsGraveB3', 'destination_coordinates': (6, 10),
                                      'stair_direction': 'up'},  # G
                             (5, 6): {'map': 'GarinsGraveB3', 'destination_coordinates': (10, 11),
                                      'stair_direction': 'up'},  # H
                         })
        self.assign_stair_directions()
        self.set_town_to_overworld_warps()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class MountainCaveB1(MapWithoutNPCs, CaveMap):
    """Rock Mountain Cave B1 (NES MAP_RCKMTN_B1). Layout coordinates are the NES ones + (1, 1)."""

    def __init__(self, config):
        super().__init__(MapLayouts().mountain_cave_b1, config, Directories(config).dungeon_floor_1_music, (7, 1),
                         staircases={
                             (8, 1): {'map': 'Alefgard', 'destination_coordinates': (64, 37)},
                             # NES MapEntryTbl/MapTargetTbl: Rock mtn B1(0,0), (6,5) and (12,12) -> Rock mtn B2, same
                             # coordinates
                             (1, 1): {'map': 'MountainCaveB2', 'destination_coordinates': (1, 1)},
                             (6, 7): {'map': 'MountainCaveB2', 'destination_coordinates': (6, 7)},
                             (13, 13): {'map': 'MountainCaveB2', 'destination_coordinates': (13, 13)},
                         })
        self.assign_stair_directions()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class MountainCaveB2(MapWithoutNPCs, CaveMap):
    """Rock Mountain Cave B2 (NES MAP_RCKMTN_B2). Layout coordinates are the NES ones + (1, 1)."""

    def __init__(self, config):
        super().__init__(MapLayouts().mountain_cave_b2, config, Directories(config).dungeon_floor_1_music, (1, 1),
                         staircases={
                             # NES MapTargetTbl: Rock mtn B2(0,0), (6,5) and (12,12) -> Rock mtn B1, same coordinates
                             (1, 1): {'map': 'MountainCaveB1', 'destination_coordinates': (1, 1)},
                             (6, 7): {'map': 'MountainCaveB1', 'destination_coordinates': (6, 7)},
                             (13, 13): {'map': 'MountainCaveB1', 'destination_coordinates': (13, 13)},
                         })
        self.assign_stair_directions()
        self.set_town_to_overworld_warps()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class StaffOfRainCave(DragonWarriorMap):
    def __init__(self, config):
        super().__init__(MapLayouts().staff_of_rain_cave, config, Directories(config).tantegel_castle_courtyard_music,
                         (11, 6), staircases={(11, 6): {'map': 'Alefgard'}})
        self.npc_coordinates = {
            (6, 6): 'WISE_MAN',
        }
        self.assign_stair_directions()
        self.set_town_to_overworld_warps()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value

    def set_characters_initial_directions(self):
        self.set_character_initial_direction('WISE_MAN', Direction.RIGHT)


class MagicTemple(DragonWarriorMap):
    def __init__(self, config):
        super().__init__(MapLayouts().magic_temple, config, Directories(config).tantegel_castle_courtyard_music,
                         (6, 2), staircases={(6, 2): {'map': 'Alefgard'}})
        self.npc_coordinates = {
            (7, 6): 'WISE_MAN',
        }
        self.assign_stair_directions()
        self.set_town_to_overworld_warps()

    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value

    def set_characters_initial_directions(self):
        self.set_character_initial_direction('WISE_MAN', Direction.LEFT)


# Lookup of all map names with their associated class
map_lookup: Dict[str, Callable[..., DragonWarriorMap]] = {
    map_name: map_class for map_name, map_class in inspect.getmembers(sys.modules[__name__], inspect.isclass)
    if issubclass(map_class, DragonWarriorMap)}
