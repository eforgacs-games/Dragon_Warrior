import inspect
import sys
from abc import ABC
from collections.abc import Callable
from typing import override

from pygame import surface
from pygame.sprite import Group, LayeredDirty
from pygame.transform import scale

from src.common import Graphics
from src.coordinates import Cell
from src.direction import Direction
from src.directories import Directories
from src.map_layouts import MapLayouts
from src.maps_functions import parse_map_tiles, warp_line, parse_animated_sprite_sheet, get_center_point, \
    covered_cells, low_hp_tile_image, bad_ending_tile_image, tile_from_quarters
from src.npcs import GWAELIN_RESCUE, NPC
from src.sprites.animated_sprite import AnimatedSprite
from src.sprites.base_sprite import BaseSprite
from src.sprites.fixed_character import FixedCharacter
from src.sprites.roaming_character import RoamingCharacter

all_impassable_tiles = (
    'ROOF', 'WALL', 'WOOD', 'DOOR', 'WEAPON_SIGN', 'INN_SIGN', 'MOUNTAINS', 'WATER', 'BOTTOM_COAST',
    'BOTTOM_LEFT_COAST', 'LEFT_COAST', 'TOP_LEFT_COAST', 'TOP_COAST', 'TOP_RIGHT_COAST', 'RIGHT_COAST',
    'BOTTOM_RIGHT_COAST', 'BOTTOM_TOP_LEFT_COAST', 'BOTTOM_TOP_COAST', 'BOTTOM_TOP_RIGHT_COAST', 'LEFT_RIGHT_COAST',
    'TOP_LEFT_RIGHT_COAST', 'KING_LORIK', 'GUARD', 'MAN', 'WOMAN', 'WISE_MAN', 'SOLDIER', 'MERCHANT')

# The tiles drawn with background palette 0, whose color 1 ($3F01) turns red while HP is low (AddPalByte/ChkLowHPPal,
# Bank03). The fifth byte of each block in GFXTilesTbl (Bank03, $F5B5) is its palette, and only these blocks use
# palette 0: Town ($07), Castle ($09), Bridge ($0A), Water ($0F) and the water blocks with shores ($18-$26). Every
# other block uses palette 1, 2 or 3, none of which contains $30 white in OverworldPal, TownPal or DungeonPal (Bank00).
LOW_HP_PALETTE_TILES = frozenset((
    'CASTLE', 'TOWN', 'BRIDGE', 'WATER', 'BOTTOM_COAST', 'BOTTOM_LEFT_COAST', 'LEFT_COAST', 'TOP_LEFT_COAST',
    'TOP_COAST', 'TOP_RIGHT_COAST', 'RIGHT_COAST', 'BOTTOM_RIGHT_COAST', 'BOTTOM_TOP_LEFT_COAST',
    'BOTTOM_TOP_RIGHT_COAST', 'LEFT_RIGHT_COAST', 'BOTTOM_TOP_COAST', 'TOP_LEFT_RIGHT_COAST'))

# NES GFXTilesTbl (Bank03, $F5B5): each quarter of a shore block shows the shores on its own two sides (the top left
# quarter is $F6, $46, $5A or $5E for none, top, left or both), so a shore block that tileset.png doesn't have is put
# together from the quarters of ones it does: (top left, top right, bottom left, bottom right). The overworld uses only
# these three of the five missing ones; the left, right and bottom ($25) and all-sides ($26) shores are never drawn.
COMPOSED_COAST_TILES = {
    'LEFT_RIGHT_COAST': ('LEFT_COAST', 'RIGHT_COAST', 'LEFT_COAST', 'RIGHT_COAST'),  # $1D: $5A, $5C, $5B, $5D
    'BOTTOM_TOP_COAST': ('TOP_COAST', 'TOP_COAST', 'BOTTOM_COAST', 'BOTTOM_COAST'),  # $20: $46, $4A, $58, $59
    'TOP_LEFT_RIGHT_COAST': ('TOP_LEFT_COAST', 'TOP_RIGHT_COAST', 'LEFT_COAST', 'RIGHT_COAST'),  # $1E: $5E, $6A, $5B, $5D
}


DOWN, UP, LEFT, RIGHT = Direction.DOWN, Direction.UP, Direction.LEFT, Direction.RIGHT


class DragonWarriorMap:
    # Where the NES map (MapDatTbl, Bank00) is in this layout, which pads it: the layout (row, column) of NES (0, 0)
    # (an NES X,Y is at (Y + row, X + column) here), and the NES map's size in blocks, (columns, rows), i.e.
    # (MapWidth + 1, MapHeight + 1). Every map with NPCs has an origin. Without a size, the whole layout counts as the
    # NES map.
    nes_origin: Cell | None = None
    nes_size: tuple[int, int] | None = None
    # The map's NPCs (src/npcs.py), in the order of its NES NPC tables: the mobile one, then the static one
    npc_table: tuple[NPC, ...] = ()

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
        # The roaming NPCs, in the order of their mobile slots (MovementController.move_roaming_characters,
        # src/npc_schedule.py)
        self.roaming_characters = []
        # The NPCs load_map places: the NPC table, less any the story has taken off the map
        self.npcs: list[NPC] = list(self.npc_table)

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
        self.tile_group_dict = {}
        if staircases is None:
            staircases = {}
        self.staircases = staircases
        self.height = len(self.layout) * config['TILE_SIZE']
        self.width = len(self.layout[0]) * config['TILE_SIZE']
        self.last_map = last_map
        # NES covered areas (CoverDatPtr): the blocks of a town that sit under a roof. Only Brecconary, Garinham,
        # Cantlin and Rimuldar have any (Bank00 InitMapData, ChkMapBrecconary..ChkMapRimuldar).
        self.covered_area: frozenset[Cell] = frozenset()
        # NES CoverStatus: whether the hero is standing on a covered block.
        self.player_under_cover = False
        # Whether background palette 0's color 1 is the low HP red (set_low_hp_palette), and the red tiles, made the
        # first time they're needed.
        self.low_hp_palette = False
        self._low_hp_tile_images: dict[str, surface.Surface] = {}
        self._composed_tile_images: dict[str, surface.Surface] = {}
        # The window color once the bad ending's BadEndBGPal is loaded (load_bad_ending_palette), and its tiles
        self.bad_ending_window_color: tuple[int, int, int] | None = None
        self._bad_ending_tile_images: dict[str, surface.Surface] = {}

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
            'BOTTOM_TOP_RIGHT_COAST': {'val': 32},
            # Not in tileset.png: see COMPOSED_COAST_TILES
            'LEFT_RIGHT_COAST': {'val': 33},
            'BOTTOM_TOP_COAST': {'val': 34},
            'TOP_LEFT_RIGHT_COAST': {'val': 35},
        }
        self.character_key = {
            'HERO': {'val': 36, 'path': self.directories.UNARMED_HERO_PATH},
            'KING_LORIK': {'val': 37, 'path': self.directories.KING_LORIK_PATH},
            'GUARD': {'val': 38, 'path': self.directories.GUARD_PATH},
            'MAN': {'val': 39, 'path': self.directories.MAN_PATH},
            'WOMAN': {'val': 40, 'path': self.directories.WOMAN_PATH},
            'WISE_MAN': {'val': 41, 'path': self.directories.WISE_MAN_PATH},
            'SOLDIER': {'val': 42, 'path': self.directories.SOLDIER_PATH},
            'MERCHANT': {'val': 43, 'path': self.directories.MERCHANT_PATH},
            'PRINCESS_GWAELIN': {'val': 44, 'path': self.directories.PRINCESS_GWAELIN_PATH},
            'DRAGONLORD': {'val': 45, 'path': self.directories.DRAGONLORD_PATH}
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

    def in_nes_map(self, row: int, column: int) -> bool:
        """Whether a layout (row, column) is inside the NES map (NES ChkNPCMapLimit: 0 <= x <= MapWidth and
        0 <= y <= MapHeight)."""
        if self.nes_origin is None or self.nes_size is None:
            return 0 <= row < len(self.layout) and 0 <= column < len(self.layout[0])
        (origin_row, origin_column), (columns, rows) = self.nes_origin, self.nes_size
        return 0 <= column - origin_column < columns and 0 <= row - origin_row < rows

    def npc_position(self, npc: NPC) -> Cell:
        """The layout (row, column) of an NPC."""
        assert self.nes_origin is not None, f'{self.identifier} has NPCs, so it needs an nes_origin'
        origin_row, origin_column = self.nes_origin
        return npc.y + origin_row, npc.x + origin_column

    @property
    def npc_coordinates(self) -> dict[Cell, str]:
        """Layout (row, column) -> sprite type of each NPC load_map places."""
        return {self.npc_position(npc): npc.sprite for npc in self.npcs}

    @property
    def roaming_character_list(self) -> list[str]:
        """The identifiers of the roaming NPCs, in the order of the map's NES mobile NPC table (TantMobTbl etc.,
        Bank00), which is the order of the NES's mobile NPC slots."""
        return [npc.name for npc in self.npcs if npc.mobile]

    def npc(self, name: str) -> NPC | None:
        """The NPC table entry of the NPC with this identifier, if it's on the map."""
        return next((npc for npc in self.npcs if npc.name == name), None)

    def include_npc(self, name: str) -> None:
        """Put an NPC from the NPC table back among the NPCs load_map places, in its table position."""
        self.npcs = [npc for npc in self.npc_table if npc in self.npcs or npc.name == name]

    def exclude_npc(self, name: str) -> None:
        """Leave an NPC out of the ones load_map places."""
        self.npcs = [npc for npc in self.npcs if npc.name != name]

    def get_tile_by_value(self, position: int) -> str:
        """Returns the tile name from the integer value associated with it."""
        return self._tile_key_list[position]

    def load_map(self, player, destination_coordinates: Cell | None, tile_size) -> None:
        self.destination_coordinates = destination_coordinates
        self.tile_types_in_current_map = self.get_tiles_in_current_map()
        self.impassable_tiles = tuple(self.tile_types_in_current_map & set(all_impassable_tiles))
        for row in range(len(self.layout)):
            for column in range(len(self.layout[row])):
                self.center_pt = get_center_point(column, row, tile_size=tile_size)
                self.map_floor_tiles(column, row)
        for npc in self.npcs:
            npc_row, npc_col = self.npc_position(npc)
            self.center_pt = get_center_point(npc_col, npc_row, tile_size=tile_size)
            char_dict = self.character_key[npc.sprite]
            self.map_npc(npc.name, char_dict.get('direction'), char_dict['underlying_tile'],
                         char_dict['path'], char_dict['four_sided'],
                         (npc_row, npc_col), npc.mobile)
        # NES GetNPCDataPointer copies the mobile NPC table into the mobile slots in order, which is the order the
        # roaming NPCs were added in. An NPC keeps its slot until the map is loaded again, even if it's removed
        # (DialogLookup.remove_npc)
        for slot, roaming_character in enumerate(self.roaming_characters):
            roaming_character.slot = slot
        hero_coords = destination_coordinates or self.initial_coordinates
        if hero_coords:
            hero_row, hero_col = hero_coords
            self.center_pt = get_center_point(hero_col, hero_row, tile_size=tile_size)
            AnimatedSprite.__init__(player, self.center_pt, player.direction_value,
                                    images=self.scale_sprite_sheet(self.directories.UNARMED_HERO_PATH),
                                    identifier='HERO')
            self.map_player(self.character_key['HERO']['underlying_tile'], player, hero_coords)
        self.set_characters_initial_directions()

    def is_covered(self, row: int, column: int) -> bool:
        """NES CheckCoveredArea/HasCoverData: bit 3 of the block's covered-area nibble. Blocks off the map are never
        covered."""
        return (row, column) in self.covered_area

    def is_hidden_by_cover(self, row: int, column: int) -> bool:
        """
        NES ChkCoveredArea ($A9CD): a block whose cover status differs from the hero's (CoverStatus) isn't drawn as
        itself. From outside, covered blocks are drawn as roof (BLK_SML_TILES); from inside, every uncovered block is
        drawn blank (BLK_BLANK). NPCs on such blocks aren't drawn either (Bank00 $B957).
        """
        return bool(self.covered_area) and self.is_covered(row, column) != self.player_under_cover

    def crosses_cover_boundary(self, row: int, column: int, next_row: int, next_column: int) -> bool:
        """NES NPC movement ($B839-$B84F): an NPC can't step between a covered and an uncovered block."""
        return self.is_covered(row, column) != self.is_covered(next_row, next_column)

    def get_tiles_in_current_map(self) -> set:
        return set(self.get_tile_by_value(tile) for row in self.layout for tile in row)

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
        if not self.has_floor_tile(*coordinates):
            self.add_tile(self.floor_tile_key[underlying_tile], self.center_pt)

    def map_player(self, underlying_tile, player, coordinates) -> None:
        self.player_sprites = LayeredDirty(player)
        player.direction_value = self.hero_initial_direction()
        if not self.has_floor_tile(*coordinates):
            self.add_tile(self.floor_tile_key[underlying_tile], self.center_pt)
        self.characters['HERO'] = {'character': player,
                                   'character_sprites': self.player_sprites,
                                   'tile_value': self.character_key['HERO']['val'],
                                   'coordinates': coordinates}

    def has_floor_tile(self, row: int, column: int) -> bool:
        """Whether the layout already has a floor tile at (row, column), i.e. not a character's tile value.
        A character standing on such a block mustn't get a second tile there: with two tiles in one block, the one
        that shows depends on which tile types are being redrawn, so the block flips between them as characters move
        around (e.g. Brecconary's MAN_3 stands on brick, but also got a GRASS tile)."""
        return self.layout[row][column] < len(self.floor_tile_key)

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
        tile = BaseSprite(center_pt, self.floor_tile_image(tile_value)) if tile_value < len(self.floor_tile_key) else None
        self.floor_tile_key[self.get_tile_by_value(tile_value)]['group'].add(tile)

    def normal_tile_image(self, tile_value: int) -> surface.Surface:
        """The tileset image for a floor tile: tileset.png has 11 tiles to a row. The shore blocks it doesn't have are
        put together from the ones it does (COMPOSED_COAST_TILES), once."""
        tile_name = self.get_tile_by_value(tile_value)
        if tile_name not in COMPOSED_COAST_TILES:
            return self.map_tiles[tile_value % 11][tile_value // 11]
        if tile_name not in self._composed_tile_images:
            quarters = [self.normal_tile_image(self.floor_tile_key[source]['val'])
                        for source in COMPOSED_COAST_TILES[tile_name]]
            self._composed_tile_images[tile_name] = tile_from_quarters(*quarters)
        return self._composed_tile_images[tile_name]

    def floor_tile_image(self, tile_value: int) -> surface.Surface:
        """The image for a floor tile in the current background palette: palette 0 tiles are red while HP is low, and
        every tile is black but palette 0's color 1 in the bad ending."""
        tile_name = self.get_tile_by_value(tile_value)
        if self.bad_ending_window_color is not None:
            if tile_name not in self._bad_ending_tile_images:
                self._bad_ending_tile_images[tile_name] = bad_ending_tile_image(
                    self.normal_tile_image(tile_value), tile_name in LOW_HP_PALETTE_TILES, self.bad_ending_window_color)
            return self._bad_ending_tile_images[tile_name]
        if not self.low_hp_palette or tile_name not in LOW_HP_PALETTE_TILES:
            return self.normal_tile_image(tile_value)
        if tile_name not in self._low_hp_tile_images:
            self._low_hp_tile_images[tile_name] = low_hp_tile_image(self.normal_tile_image(tile_value))
        return self._low_hp_tile_images[tile_name]

    def set_low_hp_palette(self, low_hp: bool) -> bool:
        """Load background palette 0's color 1 as red (low HP) or white, the way AddPalByte's ChkLowHPPal (Bank03) does
        for the map as well as the windows: every palette 0 tile on the map swaps its image. Returns whether anything
        changed, so the caller only redraws the map when it did."""
        if low_hp == self.low_hp_palette:
            return False
        self.low_hp_palette = low_hp
        self.update_tile_images(LOW_HP_PALETTE_TILES)
        return True

    def load_bad_ending_palette(self, window_color: tuple[int, int, int]) -> None:
        """NES ChooseDrgnLrd (Bank03, LD515): BadEndBGPal replaces the background palettes, so every tile on the map
        changes (bad_ending_tile_image). The sprite palettes are left alone."""
        self.bad_ending_window_color = window_color
        self._bad_ending_tile_images.clear()
        self.update_tile_images(self.floor_tile_key)

    def update_tile_images(self, tile_names) -> None:
        """Give the map's tiles of these types their image in the current background palette (floor_tile_image)."""
        for tile_name in tile_names:
            tile_dict = self.floor_tile_key[tile_name]
            if tile_dict.get('group'):
                image = self.floor_tile_image(tile_dict['val'])
                for tile in tile_dict['group']:
                    tile.image = image

    @property
    def hero_underlying_tile(self):
        raise NotImplementedError("Method not implemented.")

    @property
    def hero_initial_direction(self):
        raise NotImplementedError("Method not implemented")

    def set_characters_initial_directions(self) -> None:
        """Turn each NPC the way its NPC table entry faces."""
        for npc in self.npcs:
            self.set_character_initial_direction(npc.name, npc.facing)

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
    """A map with an empty NPC table."""


class BasementWithNPCs(DragonWarriorMap, ABC):
    @override
    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    @override
    def hero_initial_direction(self) -> int:
        return Direction.RIGHT.value


class BasementWithoutNPCs(MapWithoutNPCs):

    @override
    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    @override
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

    # NES MAP_THRONEROOM (ThrnRoomDat): NES (x, y) is layout (y + 6, x + 10) here
    nes_origin, nes_size = (6, 10), (10, 10)
    npc_table = (
        # ThRmMobTbl
        NPC('GUARD', 7, 5, 0x65, mobile=True),
        # ThRmStatTbl
        NPC('KING_LORIK', 3, 3, 0x6E),
        NPC('GUARD_2', 3, 6, 0x23, RIGHT),
        NPC('GUARD_3', 5, 6, 0x24, LEFT),
        NPC('PRINCESS_GWAELIN', 6, 3, 0x6F),  # only once she's been returned (NES ChkGwaelinNPC)
    )

    def __init__(self, config):
        super().__init__(MapLayouts().tantegel_throne_room, config,
                         Directories(config).tantegel_castle_throne_room_music, (10, 13),
                         staircases={
                             (14, 18): {'map': 'TantegelCourtyard', 'destination_coordinates': (14, 14),
                                        'direction': Direction.RIGHT.value}})
        # Princess Gwaelin is added by MapManager.place_princess_gwaelin once she's been returned
        self.exclude_npc('PRINCESS_GWAELIN')
        self.assign_stair_directions()

    @override
    def hero_underlying_tile(self):
        return 'BRICK'

    @override
    def hero_initial_direction(self):
        return Direction.UP.value


class TantegelCourtyard(DragonWarriorMap):
    """
    This is the courtyard of Tantegel Castle.
    """

    # NES MAP_TANTCSTL_GF (TantGFDat): NES (x, y) is layout (y + 7, x + 7) here
    nes_origin, nes_size = (7, 7), (30, 30)
    npc_table = (
        # TantMobTbl
        NPC('WOMAN_2', 8, 13, 0x62, mobile=True),
        NPC('GUARD_7', 19, 2, 0x17, mobile=True),
        NPC('MAN_2', 11, 11, 0x1C, mobile=True),
        NPC('WISE_MAN_2', 17, 11, 0x1D, mobile=True),
        NPC('MERCHANT_2', 4, 21, 0x1F, mobile=True),
        NPC('SOLDIER_2', 25, 11, 0x16, mobile=True),
        NPC('GUARD_9', 18, 18, 0x72, mobile=True),
        NPC('GUARD_3', 2, 12, 0x1B, mobile=True),
        NPC('MERCHANT_3', 6, 25, 0x20, mobile=True),
        NPC('SOLDIER', 24, 21, 0x22, mobile=True),
        # TantStatTbl
        NPC('MERCHANT', 24, 1, 0x0E),  # magic keys
        NPC('WOMAN', 27, 5, 0x1A),
        NPC('GUARD', 8, 6, 0x19),
        NPC('MAN', 2, 8, 0x18),
        NPC('GUARD_2', 8, 8, 0x71, UP),
        NPC('GUARD_8', 26, 15, 0x1E, UP),
        NPC('GUARD_4', 15, 20, 0x63, RIGHT),
        NPC('WISE_MAN', 20, 26, 0x6A, LEFT),  # restores MP
        NPC('GUARD_5', 9, 27, 0x21, RIGHT),
        NPC('GUARD_6', 12, 27, 0x21, LEFT),
    )
    # NES GetNPCDataPointer: after the Dragonlord's defeat, the ground floor loads TaDLMobTbl and TaDLStatTbl. King
    # Lorik waits in front of the throne room stairs between two rows of guards (with trumpets in the NES's last frame;
    # there's no sprite for those, so they're plain guards, as are the two wizards: NES GetGuardType). Once the
    # Dragonlord is dead, Ending.npc_dialog decides what every NPC here says.
    npc_table_after_dragonlord = (
        # TaDLMobTbl
        NPC('GUARD_9', 19, 2, 0x17, mobile=True),
        NPC('MAN', 14, 23, 0x1C, mobile=True),
        NPC('SOLDIER', 25, 11, 0x16, mobile=True),
        NPC('GUARD_10', 18, 18, 0x72, mobile=True),
        NPC('GUARD_11', 2, 12, 0x1B, mobile=True),
        NPC('MERCHANT', 6, 25, 0x20, mobile=True),
        NPC('SOLDIER_2', 24, 21, 0x22, mobile=True),
        # TaDLStatTbl
        NPC('KING_LORIK', 11, 7, 0xFE),
        NPC('GUARD', 9, 9, 0xFD),  # trumpet guards
        NPC('GUARD_2', 9, 11, 0xFD),
        NPC('GUARD_3', 9, 13, 0xFD),
        NPC('GUARD_4', 12, 9, 0xFD),
        NPC('GUARD_5', 12, 11, 0xFD),
        NPC('GUARD_6', 12, 13, 0xFD),
        NPC('GUARD_7', 9, 27, 0xFD, RIGHT),  # gate guards
        NPC('GUARD_8', 12, 27, 0xFD, LEFT),
    )

    def __init__(self, config):
        super().__init__(MapLayouts().tantegel_courtyard, config, Directories(config).tantegel_castle_courtyard_music,
                         (14, 14))
        # The NES leaves the castle from the tiles just outside TantGFDat's 30 x 30 blocks
        self.create_town_gates(
            north_gate=warp_line((6, 6), (6, 37)),
            west_gate=warp_line((6, 6), (37, 6)),
            east_gate=warp_line((6, 37), (37, 37)),
            south_gate=warp_line((37, 6), (37, 37)))
        self.staircases[(14, 14)] = {'map': 'TantegelThroneRoom', 'destination_coordinates': (14, 18),
                                     'direction': Direction.LEFT.value}
        # NES MapEntryTbl/MapTargetTbl: Tant castle GF(29,29) -> Tant castle SL(0,4)
        self.staircases[(36, 36)] = {'map': 'TantegelCellar', 'destination_coordinates': (5, 1)}
        self.assign_stair_directions()
        self.set_town_to_overworld_warps()

    @override
    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    @override
    def hero_initial_direction(self):
        return Direction.RIGHT.value

    @override
    def apply_dragonlord_defeated(self):
        self.npcs = list(self.npc_table_after_dragonlord)


class TantegelCellar(BasementWithNPCs):
    """Tantegel Castle's sublevel (NES MAP_TANTCSTL_SL). Layout coordinates are the NES ones + (1, 1)."""

    nes_origin = (1, 1)
    npc_table = (
        # TaSLStatTbl (TaSLMobTbl is empty)
        NPC('WISE_MAN', 4, 6, 0x66),  # guarding the Stones of Sunlight
    )

    def __init__(self, config):
        super().__init__(MapLayouts().tantegel_underground, config, Directories(config).tantegel_castle_courtyard_music,
                         (5, 1), staircases={
                # NES MapTargetTbl: Tant castle SL(0,4) -> Tant castle GF(29,29)
                (5, 1): {'map': 'TantegelCourtyard', 'destination_coordinates': (36, 36)}})
        self.assign_stair_directions()


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
        # The NES leaves the castle from the tiles just outside DLCstlGFDat's 20 x 20 blocks
        self.create_town_gates(north_gate=warp_line((5, 6), (5, 27)),
                               east_gate=warp_line((5, 27), (26, 27)),
                               west_gate=warp_line((5, 6), (26, 6)),
                               south_gate=warp_line((26, 6), (26, 27)))
        self.set_town_to_overworld_warps()
        self.assign_stair_directions()

    def reveal_hidden_staircase(self):
        """Turn the force field behind the throne into the stairs down to CharlockB2 (NES DoSearch, F_PSG_FOUND)."""
        row, column = self.HIDDEN_STAIRCASE_COORDINATES
        self.layout[row][column] = self.floor_tile_key['BRICK_STAIR_DOWN']['val']
        self.staircases[self.HIDDEN_STAIRCASE_COORDINATES] = {**self.HIDDEN_STAIRCASE, 'stair_direction': 'down'}

    @override
    def hero_underlying_tile(self):
        return 'BRICK'

    @override
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

    nes_origin = (4, 6)
    # NES DLBFStatTbl (Bank00): the Dragonlord (wizard graphic), DgrnLrdDialog. DLBFMobTbl is empty. Charlock's other
    # floors (MAP_DLCSTL_GF and the sublevels) have no NPC tables at all.
    npc_table = (
        NPC('DRAGONLORD', 16, 24, 0x70),
    )

    def __init__(self, config):
        super().__init__(MapLayouts().charlock_b8, config, Directories(config).dungeon_floor_8_music,
                         (33, 16), staircases={
                # NES MapTargetTbl/MapEntryTbl: DL castle BF(10,29) -> DL castle SL6(9,6)
                (33, 16): {'map': 'CharlockB7Wide', 'destination_coordinates': (5, 12)}})
        self.assign_stair_directions()

    @override
    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    @override
    def hero_initial_direction(self):
        return Direction.RIGHT.value

    @override
    def apply_dragonlord_defeated(self):
        # NES LoadMobNPCDataLoop: the Dragonlord NPC isn't loaded once he's been defeated
        self.npcs = []


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
                (9, 10): {'map': 'Garinham', 'destination_coordinates': (15, 9)},
                # NES MapEntryTbl/MapTargetTbl: Overworld(104,10) -> Kol(19,23)
                (17, 112): {'map': 'Kol', 'destination_coordinates': (31, 29)},
                # cave
                (19, 36): {'map': 'ErdricksCaveB1', 'destination_coordinates': (3, 3)},
                (51, 112): {'map': 'SwampCave', 'destination_coordinates': (6, 4)},
                (56, 112): {'map': 'SwampCave', 'destination_coordinates': (35, 4)},
                (64, 37): {'map': 'MountainCaveB1', 'destination_coordinates': (8, 1)},
                (96, 33): {'map': 'Hauksness', 'destination_coordinates': (18, 9)},
                (79, 110): {'map': 'Rimuldar', 'destination_coordinates': (22, 37)},
                (109, 81): {'map': 'Cantlin', 'destination_coordinates': (8, 16)},
                (116, 116): {'map': 'MagicTemple', 'destination_coordinates': (6, 2)},
                (8, 89): {'map': 'StaffOfRainCave', 'destination_coordinates': (11, 6)},
            })
        for staircase_dict in self.staircases.values():
            staircase_dict['stair_direction'] = 'up'

    @override
    def hero_underlying_tile(self):
        return 'CASTLE'

    @override
    def hero_initial_direction(self):
        return Direction.DOWN.value if self.character_key['HERO'][
                                           'underlying_tile'] != 'GRASS_STAIR_DOWN' else Direction.LEFT.value


class Brecconary(DragonWarriorMap):

    # NES MAP_BRECCONARY (BrecconaryDat): NES (x, y) is layout (y + 8, x + 10) here
    nes_origin, nes_size = (8, 10), (30, 30)
    npc_table = (
        # BrecMobTbl
        NPC('WISE_MAN_2', 9, 4, 0x2B, mobile=True),
        NPC('SOLDIER_4', 12, 19, 0x5D, mobile=True),
        NPC('MERCHANT_4', 15, 9, 0x2E, mobile=True),
        NPC('MAN_5', 25, 22, 0x31, mobile=True),
        NPC('MAN_4', 10, 14, 0x2C, mobile=True),
        NPC('WOMAN', 24, 4, 0x0F, mobile=True),  # Fairy Water
        NPC('GUARD_2', 26, 15, 0x2F, mobile=True),
        NPC('WOMAN_3', 15, 24, 0x2D, mobile=True),
        NPC('SOLDIER_3', 19, 18, 0x30, mobile=True),
        NPC('SOLDIER_2', 3, 26, 0x27, mobile=True),
        # BrecStatTbl
        NPC('MERCHANT', 5, 4, 0x01),  # weapons and armor shop
        NPC('SOLDIER', 28, 1, 0x25),
        NPC('WOMAN_2', 4, 7, 0x29),
        NPC('MAN', 20, 10, 0x26),
        NPC('WISE_MAN', 24, 10, 0x67),  # removes curses
        NPC('MAN_2', 1, 13, 0x2A),
        NPC('MERCHANT_2', 10, 21, 0x12, LEFT),  # the inn
        NPC('MAN_3', 20, 23, 0x28, UP),
        NPC('MERCHANT_3', 25, 25, 0x08, LEFT),  # item shop
        NPC('GUARD', 10, 26, 0x64, UP),  # searching for Gwaelin
    )

    def __init__(self, config):
        super().__init__(MapLayouts().brecconary, config, Directories(config).village_music,
                         (23, 10))
        self.create_town_gates(north_gate=warp_line((7, 23), (7, 26)),
                               east_gate=warp_line((21, 40), (25, 40)),
                               west_gate=warp_line((21, 9), (24, 9)))
        self.set_town_to_overworld_warps()
        # NES BrecCvrdDatPtr -> TantSLDat ($8D24): the upper right building (fairy water) and the lower right one
        # (item shop). NES X,Y is at (Y + 8, X + 10) here.
        self.covered_area = covered_cells({
            **{y: range(20, 28) for y in range(2, 6)},
            6: (20, *range(22, 28)),  # 21,6 is the door
            23: (21, *range(23, 27)),  # 22,23 is the way in
            **{y: range(21, 27) for y in range(24, 28)},
        }, row_offset=8, column_offset=10)

    @override
    def hero_underlying_tile(self):
        return 'BRICK'

    @override
    def hero_initial_direction(self):
        return Direction.RIGHT.value


class Garinham(DragonWarriorMap):

    # NES MAP_GARINHAM (GarinhamDat): NES (x, y) is layout (y + 1, x + 9) here
    nes_origin, nes_size = (1, 9), (20, 20)
    npc_table = (
        # GarMobTbl
        NPC('WOMAN', 12, 4, 0x3E, mobile=True),
        NPC('WOMAN_2', 12, 12, 0x43, mobile=True),
        NPC('WISE_MAN_2', 12, 8, 0x3F, mobile=True),
        NPC('WISE_MAN_3', 2, 10, 0x42, mobile=True),
        NPC('MAN', 11, 7, 0x3D, mobile=True),
        NPC('MAN_2', 18, 12, 0x44, mobile=True),
        NPC('SOLDIER', 7, 17, 0x41, mobile=True),
        # GarStatTbl
        NPC('WISE_MAN', 14, 1, 0x3A),
        NPC('GUARD', 3, 5, 0x3B, RIGHT),
        NPC('GUARD_2', 5, 5, 0x3B, LEFT),
        NPC('MERCHANT', 9, 6, 0x3C),
        NPC('MERCHANT_2', 5, 11, 0x09, LEFT),  # item shop
        NPC('MERCHANT_3', 17, 15, 0x13, LEFT),  # the inn
        NPC('WISE_MAN_4', 2, 17, 0x40, RIGHT),
        NPC('MERCHANT_4', 10, 18, 0x02, UP),  # weapons and armor shop
    )

    def __init__(self, config):
        super().__init__(MapLayouts().garinham, config, Directories(config).village_music, (15, 9),
                         staircases={
                             (1, 28): {'map': 'GarinsGraveB1', 'destination_coordinates': (12, 7),
                                       'stair_direction': 'down'},
                         })
        # The NES leaves the town from the tiles just outside GarinhamDat's 20 x 20 blocks
        self.create_town_gates(north_gate=warp_line((0, 8), (0, 29)),
                               east_gate=warp_line((0, 29), (21, 29)),
                               west_gate=warp_line((0, 8), (21, 8)),
                               south_gate=warp_line((21, 8), (21, 29)))
        self.set_town_to_overworld_warps()
        # NES GarinCvrdDatPtr -> DgnLrdSL4Dat ($8EE6): the whole top of town. NES X,Y is at (Y + 1, X + 9) here.
        self.covered_area = covered_cells({
            **{y: range(20) for y in range(3, 10)},
            10: (15, 16, 18, 19),  # 17,10 is the door
        }, row_offset=1, column_offset=9)

    @override
    def hero_underlying_tile(self):
        return 'BRICK'

    @override
    def hero_initial_direction(self):
        return Direction.RIGHT.value


class Kol(DragonWarriorMap):
    """Kol (NES MAP_KOL). Layout coordinates are the NES ones offset by (row + 8, column + 10)."""

    # NES MAP_KOL (KolDat): NES (x, y) is layout (y + 8, x + 10) here
    nes_origin, nes_size = (8, 10), (24, 24)
    npc_table = (
        # KolMobTbl
        NPC('MAN_2', 14, 13, 0x36, mobile=True),
        NPC('MAN', 5, 12, 0x30, mobile=True),
        NPC('GUARD', 12, 10, 0x37, mobile=True),
        NPC('WISE_MAN_3', 2, 12, 0x5E, mobile=True),  # the flute question
        NPC('WISE_MAN_4', 20, 19, 0x38, mobile=True),
        NPC('SOLDIER', 6, 7, 0x35, mobile=True),
        NPC('WOMAN_2', 11, 14, 0x2E, mobile=True),
        NPC('MERCHANT_3', 7, 19, 0x5F, mobile=True),  # the southern island question
        NPC('WISE_MAN_2', 20, 8, 0x39, mobile=True),
        # KolStatTbl
        NPC('WISE_MAN', 1, 1, 0x68),  # Erdrick's Sword
        NPC('WOMAN', 12, 1, 0x32),
        NPC('MERCHANT', 19, 4, 0x11, UP),  # the inn
        NPC('MERCHANT_2', 22, 12, 0x00, LEFT),  # weapons and armor shop
        NPC('SOLDIER_2', 20, 13, 0x33),
        NPC('MERCHANT_4', 14, 21, 0x07, LEFT),  # item shop
        NPC('GUARD_2', 1, 23, 0x34),
    )

    def __init__(self, config):
        super().__init__(MapLayouts().kol, config, Directories(config).village_music, (31, 29))
        # The NES leaves the town from the tiles just outside KolDat's 24 x 24 blocks
        self.create_town_gates(north_gate=warp_line((7, 9), (7, 34)),
                               east_gate=warp_line((7, 34), (32, 34)),
                               west_gate=warp_line((7, 9), (32, 9)),
                               south_gate=warp_line((32, 9), (32, 34)))
        self.set_town_to_overworld_warps()

    @override
    def hero_underlying_tile(self):
        return 'SAND'

    @override
    def hero_initial_direction(self):
        return Direction.UP.value


class Rimuldar(DragonWarriorMap):

    # NES MAP_RIMULDAR (RimuldarDat): NES (x, y) is layout (y + 8, x + 8) here
    nes_origin, nes_size = (8, 8), (30, 30)
    npc_table = (
        # RimMobTbl
        NPC('WOMAN_3', 6, 21, 0x59, mobile=True),
        NPC('MAN_2', 11, 8, 0x30, mobile=True),
        NPC('MAN_4', 6, 23, 0x5A, mobile=True),
        NPC('WOMAN_2', 22, 14, 0x56, mobile=True),
        NPC('SOLDIER_3', 5, 25, 0x5B, mobile=True),
        NPC('SOLDIER', 23, 11, 0x52, mobile=True),
        NPC('MAN_3', 14, 11, 0x55, mobile=True),
        NPC('SOLDIER_4', 16, 26, 0x69, mobile=True),  # the Fighter's Ring
        NPC('GUARD', 8, 16, 0x54, mobile=True),
        NPC('SOLDIER_2', 24, 19, 0x57, mobile=True),
        # RimStatTbl
        NPC('MAN', 27, 0, 0x51),  # Orwick
        NPC('MERCHANT', 2, 4, 0x4F, UP),
        NPC('WISE_MAN', 4, 7, 0x0D, UP),  # magic keys
        NPC('MERCHANT_2', 23, 7, 0x06),  # weapons and armor shop
        NPC('WOMAN', 15, 8, 0x50, UP),
        NPC('WISE_MAN_2', 6, 13, 0x53, LEFT),
        NPC('MERCHANT_3', 16, 18, 0x15, RIGHT),  # the inn
        NPC('WISE_MAN_3', 3, 23, 0x61, RIGHT),  # the magic temple question
        NPC('WISE_MAN_4', 20, 23, 0x58),
        NPC('WOMAN_4', 0, 26, 0x5C),  # Orwick's girlfriend
    )

    def __init__(self, config):
        super().__init__(MapLayouts().rimuldar, config, Directories(config).village_music, (14, 9))
        # Layout coordinates are the NES ones offset by (row + 8, column + 8). The NES leaves the town from the tiles
        # just outside RimuldarDat's 30 x 30 blocks.
        self.create_town_gates(north_gate=warp_line((7, 0), (7, len(self.layout[0]))),
                               east_gate=warp_line((0, 38), (len(self.layout), 38)),
                               west_gate=warp_line((0, 7), (len(self.layout), 7)),
                               south_gate=warp_line((38, 0), (38, len(self.layout[0]))))
        self.set_town_to_overworld_warps()
        # NES RimCvrdDatPtr -> GarinCaveB3Dat+$E ($9170): the upper left building and the lower left one.
        # NES X,Y is at (Y + 8, X + 8) here.
        self.covered_area = covered_cells({
            2: range(4, 7),
            3: range(5, 7),
            4: range(4, 7),
            **{y: range(2, 7) for y in range(5, 9)},
            19: (*range(2, 10), 12),
            **{y: range(2, 13) for y in range(20, 28)},
        }, row_offset=8, column_offset=8)

    @override
    def hero_underlying_tile(self):
        return 'BRICK'

    @override
    def hero_initial_direction(self):
        return Direction.LEFT.value


class Hauksness(MapWithoutNPCs):
    """Hauksness (NES MAP_HAUKSNESS, $03). It has no NPCs: the NES LoadMap code (ChkMapDungeon, Bank00) only
    loads NPCs for maps MAP_TANTCSTL_GF to MAP_RAINBOW, and there's no Hauksness entry in NPCMobPtrTbl or
    NPCStatPtrTbl."""

    # NES MAP_HAUKSNESS (HauksnessDat): NES (x, y) is layout (y + 8, x + 9) here
    nes_origin, nes_size = (8, 9), (20, 20)

    def __init__(self, config):
        super().__init__(MapLayouts().hauksness, config, Directories(config).dungeon_floor_4_music,
                         (18, 9))
        self.create_town_gates(north_gate=warp_line((7, 9), (7, 28)),
                               east_gate=warp_line((0, 29), (len(self.layout), 29)),
                               west_gate=warp_line((0, 8), (len(self.layout), 8)),
                               south_gate=warp_line((28, 9), (28, 28)))
        self.set_town_to_overworld_warps()

    @override
    def hero_underlying_tile(self):
        return 'BRICK'

    @override
    def hero_initial_direction(self):
        return Direction.RIGHT.value


class Cantlin(DragonWarriorMap):

    # NES MAP_CANTLIN (CantlinDat): NES (x, y) is layout (y + 8, x + 1) here
    nes_origin, nes_size = (8, 1), (30, 30)
    npc_table = (
        # CantMobTbl
        NPC('MAN_2', 20, 15, 0x4B, mobile=True),
        NPC('GUARD', 5, 6, 0x60, mobile=True),
        NPC('MERCHANT_5', 25, 17, 0x4C, mobile=True),
        NPC('WOMAN_2', 4, 14, 0x49, mobile=True),
        NPC('MERCHANT_2', 22, 5, 0x03, mobile=True),  # weapons and armor shop 1
        NPC('WOMAN_3', 9, 16, 0x4A, mobile=True),
        NPC('WISE_MAN_4', 14, 28, 0x6B, mobile=True),  # Erdrick's Token
        NPC('GUARD_2', 15, 6, 0x48, mobile=True),
        NPC('MERCHANT_6', 3, 26, 0x4E, mobile=True),
        NPC('GUARD_3', 22, 9, 0x4D, mobile=True),
        # CantStatTbl
        NPC('MERCHANT', 8, 3, 0x14),  # the inn
        NPC('WISE_MAN', 27, 6, 0x0C),  # magic keys
        NPC('MAN', 2, 7, 0x0A, RIGHT),  # item shop 1
        NPC('MERCHANT_3', 2, 12, 0x45, RIGHT),
        NPC('MERCHANT_4', 7, 12, 0x0B, LEFT),  # item shop 2
        NPC('GUARD_4', 24, 12, 0x05, RIGHT),  # weapons and armor shop 3
        NPC('WOMAN', 22, 13, 0x10, LEFT),  # Fairy Water
        NPC('WISE_MAN_2', 15, 16, 0x46),
        NPC('WISE_MAN_3', 22, 22, 0x47),
        NPC('MERCHANT_7', 27, 26, 0x04, LEFT),  # weapons and armor shop 2
    )

    def __init__(self, config):
        super().__init__(MapLayouts().cantlin, config, Directories(config).village_music, (8, 16))
        # The NES leaves the town from the tiles just outside CantlinDat's 30 x 30 blocks
        self.create_town_gates(north_gate=warp_line((7, 0), (7, 31)),
                               east_gate=warp_line((7, 31), (38, 31)),
                               west_gate=warp_line((7, 0), (38, 0)),
                               south_gate=warp_line((38, 0), (38, 31)))
        self.set_town_to_overworld_warps()
        # NES CantCvrdDatPtr -> SwampCaveDat+$32 ($8FAE): two small rooms at the top and the middle of town.
        # NES X,Y is at (Y + 8, X + 1) here.
        self.covered_area = covered_cells({
            1: (1, 2, 3, 26, 27, 28),
            2: (1, 2, 26, 27, 28),
            3: (1, 2, 3, 26, 28),
            **{y: range(11, 19) for y in range(11, 24)},
        }, row_offset=8, column_offset=1)

    @override
    def hero_underlying_tile(self):
        return 'BRICK'

    @override
    def hero_initial_direction(self):
        return Direction.DOWN.value


class ErdricksCaveB1(MapWithoutNPCs, CaveMap):
    def __init__(self, config):
        super().__init__(MapLayouts().erdricks_cave_b1, config, Directories(config).dungeon_floor_1_music, (1, 1),
                         staircases={(3, 3): {'map': 'Alefgard'},
                                     (12, 12): {'map': 'ErdricksCaveB2',
                                                'destination_coordinates': (
                                                    10, 9)}})
        self.assign_stair_directions()
        self.set_town_to_overworld_warps()

    @override
    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    @override
    def hero_initial_direction(self):
        return Direction.RIGHT.value


class ErdricksCaveB2(MapWithoutNPCs, CaveMap):
    def __init__(self, config):
        super().__init__(MapLayouts().erdricks_cave_b2, config, Directories(config).dungeon_floor_2_music, (10, 9),
                         staircases={
                             (10, 9): {'map': 'ErdricksCaveB1', 'destination_coordinates': (12, 12)}})
        self.assign_stair_directions()

    @override
    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    @override
    def hero_initial_direction(self):
        return Direction.RIGHT.value


class SwampCave(CaveMap):
    """The Swamp Cave (NES MAP_SWAMPCAVE). Layout coordinates are the NES ones + (6, 4)."""

    nes_origin = (6, 4)
    # On the NES Gwaelin isn't an NPC: she's block $6 (BLK_PRINCESS) of SwampCaveDat (Bank00), and DoTalkResults
    # (Bank03) starts her rescue when the player talks to that block. GetBlockID turns her into brick once
    # F_DONE_GWAELIN is set (MapManager.place_princess_gwaelin). She never moves or turns.
    npc_table = (
        NPC('PRINCESS_GWAELIN', 5, 18, GWAELIN_RESCUE),
    )

    def __init__(self, config):
        super().__init__(MapLayouts().swamp_cave, config, Directories(config).dungeon_floor_1_music,
                         # NES MapTargetTbl/MapEntryTbl: Swamp cave(0,0) -> Overworld(104,44) and
                         # Swamp cave(0,29) -> Overworld(104,49), the two cave tiles
                         staircases={(6, 4): {'map': 'Alefgard', 'destination_coordinates': (51, 112)},
                                     (35, 4): {'map': 'Alefgard', 'destination_coordinates': (56, 112)}},
                         initial_coordinates=(6, 4))
        self.assign_stair_directions()

    @override
    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    @override
    def hero_initial_direction(self):
        return Direction.RIGHT.value


class GarinsGraveB1(MapWithoutNPCs, CaveMap):
    def __init__(self, config):
        super().__init__(MapLayouts().garins_grave_b1, config, Directories(config).dungeon_floor_1_music, (12, 7),
                         staircases={
                             (19, 2): {'map': 'GarinsGraveB2', 'destination_coordinates': (3, 12),
                                       'stair_direction': 'down'},
                             (12, 7): {'map': 'Garinham', 'destination_coordinates': (1, 28), 'stair_direction': 'up'},
                         })
        self.assign_stair_directions()
        self.set_town_to_overworld_warps()

    @override
    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    @override
    def hero_initial_direction(self):
        return Direction.RIGHT.value


class GarinsGraveB2(MapWithoutNPCs, CaveMap):
    def __init__(self, config):
        super().__init__(MapLayouts().garins_grave_b2, config, Directories(config).dungeon_floor_2_music, (3, 12),
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

    @override
    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    @override
    def hero_initial_direction(self):
        return Direction.RIGHT.value


class GarinsGraveB3(MapWithoutNPCs, CaveMap):
    def __init__(self, config):
        super().__init__(MapLayouts().garins_grave_b3, config, Directories(config).dungeon_floor_3_music, (2, 19),
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

    @override
    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    @override
    def hero_initial_direction(self):
        return Direction.RIGHT.value


class GarinsGraveB4(MapWithoutNPCs, CaveMap):
    def __init__(self, config):
        super().__init__(MapLayouts().garins_grave_b4, config, Directories(config).dungeon_floor_4_music, (5, 1),
                         staircases={
                             (5, 1): {'map': 'GarinsGraveB3', 'destination_coordinates': (6, 10),
                                      'stair_direction': 'up'},  # G
                             (5, 6): {'map': 'GarinsGraveB3', 'destination_coordinates': (10, 11),
                                      'stair_direction': 'up'},  # H
                         })
        self.assign_stair_directions()
        self.set_town_to_overworld_warps()

    @override
    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    @override
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

    @override
    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    @override
    def hero_initial_direction(self):
        return Direction.RIGHT.value


class MountainCaveB2(MapWithoutNPCs, CaveMap):
    """Rock Mountain Cave B2 (NES MAP_RCKMTN_B2). Layout coordinates are the NES ones + (1, 1)."""

    def __init__(self, config):
        super().__init__(MapLayouts().mountain_cave_b2, config, Directories(config).dungeon_floor_2_music, (1, 1),
                         staircases={
                             # NES MapTargetTbl: Rock mtn B2(0,0), (6,5) and (12,12) -> Rock mtn B1, same coordinates
                             (1, 1): {'map': 'MountainCaveB1', 'destination_coordinates': (1, 1)},
                             (6, 7): {'map': 'MountainCaveB1', 'destination_coordinates': (6, 7)},
                             (13, 13): {'map': 'MountainCaveB1', 'destination_coordinates': (13, 13)},
                         })
        self.assign_stair_directions()
        self.set_town_to_overworld_warps()

    @override
    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    @override
    def hero_initial_direction(self):
        return Direction.RIGHT.value


class StaffOfRainCave(DragonWarriorMap):
    """The Staff of Rain shrine (NES MAP_RAIN). Layout coordinates are the NES ones + (2, 2)."""

    nes_origin = (2, 2)
    npc_table = (
        # RainStatTbl (RainMobTbl is empty)
        NPC('WISE_MAN', 4, 4, 0x6C, RIGHT),  # RainStaffDialog
    )

    def __init__(self, config):
        super().__init__(MapLayouts().staff_of_rain_cave, config, Directories(config).tantegel_castle_courtyard_music,
                         (11, 6), staircases={(11, 6): {'map': 'Alefgard'}})
        self.assign_stair_directions()
        self.set_town_to_overworld_warps()

    @override
    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    @override
    def hero_initial_direction(self):
        return Direction.RIGHT.value


class MagicTemple(DragonWarriorMap):
    """The Rainbow Drop shrine (NES MAP_RAINBOW). Layout coordinates are the NES ones + (2, 2)."""

    nes_origin = (2, 2)
    npc_table = (
        # RnbwStatTbl (RnbwMobTbl is empty)
        NPC('WISE_MAN', 4, 5, 0x6D, LEFT),  # RnbwDrpDialog
    )

    def __init__(self, config):
        super().__init__(MapLayouts().magic_temple, config, Directories(config).tantegel_castle_courtyard_music,
                         (6, 2), staircases={(6, 2): {'map': 'Alefgard'}})
        self.assign_stair_directions()
        self.set_town_to_overworld_warps()

    @override
    def hero_underlying_tile(self):
        return 'BRICK_STAIR_UP'

    @override
    def hero_initial_direction(self):
        return Direction.RIGHT.value


# Lookup of all map names with their associated class
map_lookup: dict[str, Callable[..., DragonWarriorMap]] = {
    map_name: map_class for map_name, map_class in inspect.getmembers(sys.modules[__name__], inspect.isclass)
    if issubclass(map_class, DragonWarriorMap)}
