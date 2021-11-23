from typing import Tuple

import numpy as np
from pygame import surface
from pygame.sprite import Group, LayeredDirty
from pygame.transform import scale

from map_layouts import MapLayouts
from src.common import Direction, tantegel_castle_throne_room_music, KING_LORIK_PATH, get_image, \
    GUARD_PATH, MAN_PATH, tantegel_castle_courtyard_music, WOMAN_PATH, WISE_MAN_PATH, \
    SOLDIER_PATH, MERCHANT_PATH, PRINCESS_GWAELIN_PATH, DRAGONLORD_PATH, UNARMED_HERO_PATH, MAP_TILES_PATH, \
    overworld_music, village_music
from src.config import TILE_SIZE, SCALE, COLOR_KEY
from src.sprites.animated_sprite import AnimatedSprite
from src.sprites.base_sprite import BaseSprite
# Tile Key:
# Index values for the map tiles corresponding to location on tile sheet.
from src.sprites.fixed_character import FixedCharacter
from src.sprites.roaming_character import RoamingCharacter

offset = TILE_SIZE // 2
all_impassable_tiles = (
    'ROOF', 'WALL', 'WOOD', 'DOOR', 'BARRIER', 'WEAPON_SIGN', 'INN_SIGN', 'MOUNTAINS', 'WATER', 'BOTTOM_COAST',
    'BOTTOM_LEFT_COAST', 'LEFT_COAST', 'TOP_LEFT_COAST', 'TOP_COAST', 'TOP_RIGHT_COAST', 'RIGHT_COAST',
    'BOTTOM_RIGHT_COAST', 'BOTTOM_TOP_LEFT_COAST', 'BOTTOM_TOP_COAST', 'BOTTOM_TOP_RIGHT_COAST', 'KING_LORIK',
    'DOWN_FACE_GUARD', 'LEFT_FACE_GUARD', 'UP_FACE_GUARD', 'RIGHT_FACE_GUARD', 'MAN', 'WOMAN', 'WISE_MAN', 'SOLDIER',
    'MERCHANT')


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


class DragonWarriorMap:
    def __init__(self, hero_images, layout):

        # Character variables

        self.scale = SCALE
        self.player = None
        self.player_sprites = None
        self.characters = []
        self.fixed_characters = []
        self.roaming_characters = []
        self.hero_images = hero_images
        self.character_sprites = []

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

        self.floor_tile_key = dict([
            ('ROOF', {'val': 0, 'group': Group()}),
            ('WALL', {'val': 1, 'group': Group()}),
            ('WOOD', {'val': 2, 'group': Group()}),
            ('BRICK', {'val': 3, 'group': Group()}),
            ('TREASURE_BOX', {'val': 4, 'group': Group()}),
            ('DOOR', {'val': 5, 'group': Group()}),
            ('BRICK_STAIR_DOWN', {'val': 6, 'group': Group()}),
            ('BRICK_STAIR_UP', {'val': 7, 'group': Group()}),
            ('BARRIER', {'val': 8, 'group': Group()}),
            ('WEAPON_SIGN', {'val': 9, 'group': Group()}),
            ('INN_SIGN', {'val': 10, 'group': Group()}),
            ('CASTLE', {'val': 11, 'group': Group()}),
            ('TOWN', {'val': 12, 'group': Group()}),
            ('GRASS', {'val': 13, 'group': Group()}),
            ('TREES', {'val': 14, 'group': Group()}),
            ('HILLS', {'val': 15, 'group': Group()}),
            ('MOUNTAINS', {'val': 16, 'group': Group()}),
            ('CAVE', {'val': 17, 'group': Group()}),
            ('GRASS_STAIR_DOWN', {'val': 18, 'group': Group()}),
            ('SAND', {'val': 19, 'group': Group()}),
            ('MARSH', {'val': 20, 'group': Group()}),
            ('BRIDGE', {'val': 21, 'group': Group()}),
            ('WATER', {'val': 22, 'group': Group()}),
            ('BOTTOM_COAST', {'val': 23, 'group': Group()}),
            ('BOTTOM_LEFT_COAST', {'val': 24, 'group': Group()}),
            ('LEFT_COAST', {'val': 25, 'group': Group()}),
            ('TOP_LEFT_COAST', {'val': 26, 'group': Group()}),
            ('TOP_COAST', {'val': 27, 'group': Group()}),
            ('TOP_RIGHT_COAST', {'val': 28, 'group': Group()}),
            ('RIGHT_COAST', {'val': 29, 'group': Group()}),
            ('BOTTOM_RIGHT_COAST', {'val': 30, 'group': Group()}),
            ('BOTTOM_TOP_LEFT_COAST', {'val': 31, 'group': Group()}),
            ('BOTTOM_TOP_RIGHT_COAST', {'val': 32, 'group': Group()}),
        ])
        self.character_key = dict([
            ('HERO', {'val': 33, 'four_sided': True, 'path': UNARMED_HERO_PATH, 'roaming': False, 'underlying_tile': self.hero_underlying_tile()}),
            ('KING_LORIK', {'val': 34, 'four_sided': False, 'path': KING_LORIK_PATH, 'roaming': False, 'underlying_tile': 'BRICK'}),
            ('DOWN_FACE_GUARD', {'val': 35, 'four_sided': True, 'path': GUARD_PATH, 'roaming': False, 'direction': Direction.DOWN.value, 'underlying_tile': 'BRICK'}),
            ('LEFT_FACE_GUARD', {'val': 36, 'four_sided': True, 'path': GUARD_PATH, 'roaming': False, 'direction': Direction.LEFT.value, 'underlying_tile': 'BRICK'}),
            ('UP_FACE_GUARD', {'val': 37, 'four_sided': True, 'path': GUARD_PATH, 'roaming': False, 'direction': Direction.UP.value, 'underlying_tile': 'BRICK'}),
            ('RIGHT_FACE_GUARD', {'val': 38, 'four_sided': True, 'path': GUARD_PATH, 'roaming': False, 'direction': Direction.RIGHT.value, 'underlying_tile': 'BRICK'}),
            ('ROAMING_GUARD', {'val': 39, 'four_sided': True, 'path': GUARD_PATH, 'roaming': True, 'direction': Direction.DOWN.value, 'underlying_tile': 'BRICK'}),
            ('MAN', {'val': 40, 'four_sided': True, 'path': MAN_PATH, 'roaming': False, 'direction': Direction.DOWN.value, 'underlying_tile': 'BRICK'}),
            ('WOMAN', {'val': 41, 'four_sided': True, 'path': WOMAN_PATH, 'roaming': False, 'direction': Direction.DOWN.value, 'underlying_tile': 'GRASS'}),
            ('WISE_MAN', {'val': 42, 'four_sided': True, 'path': WISE_MAN_PATH, 'roaming': False, 'direction': Direction.DOWN.value, 'underlying_tile': 'BRICK'}),
            ('SOLDIER', {'val': 43, 'four_sided': True, 'path': SOLDIER_PATH, 'roaming': False, 'direction': Direction.DOWN.value, 'underlying_tile': 'BRICK'}),
            ('MERCHANT', {'val': 44, 'four_sided': True, 'path': MERCHANT_PATH, 'roaming': False, 'direction': Direction.DOWN.value, 'underlying_tile': 'BRICK'}),
            ('PRINCESS_GWAELIN', {'val': 45, 'four_sided': False, 'path': PRINCESS_GWAELIN_PATH, 'roaming': False, 'direction': Direction.DOWN.value, 'underlying_tile': 'BRICK'}),
            ('DRAGONLORD', {'val': 46, 'four_sided': True, 'path': DRAGONLORD_PATH, 'roaming': False, 'direction': Direction.DOWN.value, 'underlying_tile': 'BRICK'}),
        ])
        self.tile_key = dict(list(self.floor_tile_key.items()) + list(self.character_key.items()))
        self.floor_sprite_groups = [val.get('group') for val in self.floor_tile_key.values() if self.get_tile_by_value(val['val']) == self.hero_underlying_tile() or any(val['val'] in row for row in self.layout)]

    def get_tile_by_value(self, position: int) -> str:
        return list(self.tile_key.keys())[position]

    def get_initial_character_location(self, character_name: str) -> np.ndarray:
        """
        Gets the initial location of any character specified.
        :param character_name: Name of the character to find
        :return:
        """
        hero_layout_position = np.asarray(
            np.where(self.layout_numpy_array == self.character_key[character_name]['val'])).T
        return hero_layout_position

    def get_staircase_locations(self):
        """
        Dynamically generates a list of staircase locations. Currently unused, but might be useful for staircase warps.
        :return:
        """
        # also needs BRICK_STAIR_UP and GRASS_STAIR_DOWN
        staircase_locations = np.asarray(np.where(self.layout_numpy_array == self.tile_key['BRICK_STAIR_DOWN']['val'])).T
        return staircase_locations

    # @timeit
    def load_map(self, player) -> None:
        tiles_in_current_loaded_map = set([self.get_tile_by_value(tile) for row in self.layout for tile in row])
        self.impassable_tiles = tuple(tiles_in_current_loaded_map & set(all_impassable_tiles))
        for y in range(len(self.layout)):
            for x in range(len(self.layout[y])):
                self.center_pt = get_center_point(x, y)
                if self.layout[y][x] <= 32:  # anything below 32 is a floor tile
                    self.map_floor_tiles(x, y)
                else:
                    self.map_character_tiles(y, x, player)

    # @timeit
    def map_character_tiles(self, row, column, player) -> None:
        current_tile = self.layout[row][column]
        for character, character_dict in self.character_key.items():
            if current_tile == character_dict['val']:
                self.map_character(character, character_dict, current_tile, player)

    def map_character(self, character, character_dict, current_tile, player):
        if current_tile == 33:  # 'HERO' value
            player.__init__(self.center_pt, self.hero_images)
            self.map_player(character_dict['underlying_tile'], player)
        else:
            self.map_npc(identifier=character, direction=character_dict.get('direction'),
                         underlying_tile=character_dict['underlying_tile'],
                         image_path=character_dict['path'], four_sided=character_dict['four_sided'], is_roaming=character_dict['roaming'])

    def map_npc(self, identifier, direction, underlying_tile, image_path, four_sided, is_roaming=False) -> None:
        sheet = get_image(image_path)
        character_sprites = LayeredDirty()
        sheet = scale(sheet, (sheet.get_width() * self.scale, sheet.get_height() * self.scale))
        images = parse_animated_sprite_sheet(sheet)
        if four_sided:
            if is_roaming:
                character = RoamingCharacter(self.center_pt, direction, images, identifier, None)
                character.position = self.get_initial_character_location(character.identifier)
                self.roaming_characters.append(character)
            else:
                character = FixedCharacter(self.center_pt, direction, images, identifier, None)
        else:
            character = AnimatedSprite(self.center_pt, Direction.DOWN.value, images, identifier, None)
        character_sprites.add(character)
        self.characters.append(character)
        self.add_tile_by_value_and_group(underlying_tile)
        self.character_sprites.append(character_sprites)

    def add_tile_by_value_and_group(self, underlying_tile) -> None:
        self.add_tile(tile_value=self.tile_key[underlying_tile]['val'],
                      tile_group=self.tile_key[underlying_tile]['group'])

    def map_player(self, underlying_tile, player) -> None:
        self.player = player
        self.player_sprites = LayeredDirty(self.player)
        self.player.direction = self.hero_initial_direction()
        self.add_tile_by_value_and_group(underlying_tile)
        self.characters.append(self.player)
        self.character_sprites.append(self.player_sprites)

    # @timeit
    def map_floor_tiles(self, x, y) -> None:
        for tile, tile_dict in self.floor_tile_key.items():
            if self.layout[y][x] < 33:
                if self.layout[y][x] == tile_dict['val']:
                    self.add_tile(tile_value=tile_dict['val'], tile_group=tile_dict['group'])

    def add_tile(self, tile_value, tile_group) -> None:
        if tile_value <= 10:
            tile = BaseSprite(self.center_pt, self.map_tiles[tile_value][0])
        elif 10 < tile_value <= 21:
            tile = BaseSprite(self.center_pt, self.map_tiles[tile_value - 11][1])
        elif 21 < tile_value < 33:
            tile = BaseSprite(self.center_pt, self.map_tiles[tile_value - 22][2])
        else:
            print("Invalid tile.")
            tile = None
        tile_group.add(tile)

    @property
    def hero_underlying_tile(self):
        raise NotImplementedError("Method not implemented.")

    @property
    def hero_initial_direction(self):
        raise NotImplementedError("Method not implemented")


class TantegelThroneRoom(DragonWarriorMap):
    """
    This is the first map in the game, the Tantegel Castle throne room.
    """

    def __init__(self, hero_images):
        super().__init__(hero_images, MapLayouts.tantegel_throne_room)
        self.staircases = {(14, 18): {'map': 'TantegelCourtyard', 'stair_direction': 'down'}}
        self.music_file_path = tantegel_castle_throne_room_music

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.UP.value


class TantegelCourtyard(DragonWarriorMap):
    """
    This is the courtyard of Tantegel Castle.
    """

    def __init__(self, hero_images):
        super().__init__(hero_images, MapLayouts.tantegel_courtyard)
        up_staircase = {'map': 'Alefgard', 'stair_direction': 'up'}
        staircases_keys = [(37, min(n, 26)) for n in range(9, 27)]
        staircases_values = [up_staircase] * len(staircases_keys)
        self.staircases = dict(zip(staircases_keys, staircases_values))
        self.music_file_path = tantegel_castle_courtyard_music

    def hero_underlying_tile(self):
        # TODO: Super TODO. Make characters have initial coordinates
        #  Instead of underlying tiles, set up the map with just the background tiles.
        #  Right now this implementation has a band-aid over it
        return 'BRICK_STAIR_UP'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class Alefgard(DragonWarriorMap):
    """
    This is Alefgard, the world by which the player travels between cities. The map is a 124 x 124 tile grid.
    """

    def __init__(self, hero_images):
        super().__init__(hero_images, MapLayouts.alefgard)
        self.music_file_path = overworld_music
        self.staircases = {
            (45, 52): {'map': 'Brecconary', 'stair_direction': 'up'},
            (47, 47): {'map': 'TantegelCourtyard', 'stair_direction': 'up'}}

    def hero_underlying_tile(self):
        return 'CASTLE'

    def hero_initial_direction(self):
        return Direction.DOWN.value


class Brecconary(DragonWarriorMap):

    def __init__(self, hero_images):
        super().__init__(hero_images, MapLayouts.brecconary)
        # up_staircase = {'map': Alefgard(self.hero_images), 'stair_direction': 'up'}
        up_staircase = {'map': 'Alefgard', 'stair_direction': 'up'}
        west_gate = [(min(n, 24), 9) for n in range(21, 25)]
        north_gate = [(7, min(n, 26)) for n in range(23, 27)]
        east_gate = [(min(n, 25), 40) for n in range(21, 26)]
        staircases_keys = west_gate + north_gate + east_gate
        staircases_values = [up_staircase] * len(staircases_keys)
        self.staircases = dict(zip(staircases_keys, staircases_values))
        self.music_file_path = village_music

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


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


def get_next_coordinates(character_column, character_row, direction):
    match direction:
        case Direction.UP.value:
            return character_row - 1, character_column
        case Direction.DOWN.value:
            return character_row + 1, character_column
        case Direction.LEFT.value:
            return character_row, character_column - 1
        case Direction.RIGHT.value:
            return character_row, character_column + 1


def get_character_position(character):
    character.column, character.row = character.rect.x // TILE_SIZE, character.rect.y // TILE_SIZE


map_lookup = {
    "TantegelThroneRoom": TantegelThroneRoom,
    "TantegelCourtyard": TantegelCourtyard,
    "Alefgard": Alefgard,
    "Brecconary": Brecconary
}
