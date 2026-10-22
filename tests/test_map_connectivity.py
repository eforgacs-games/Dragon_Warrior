"""
Every map can be reached, and every staircase leads somewhere sensible.

Builds the whole world through the game's own map loading (MapManager.change_map, which applies the Rainbow Bridge and
Charlock's hidden stairs the way the game does), then walks it tile by tile: through any tile the hero can step on, and
through every staircase, town gate and overworld entrance in each map's `staircases`. Doors count as open, since
Magic Keys can always be bought.

NES references (nmikstas disassembly): MapEntryTbl/MapTargetTbl (Bank03) for the links between maps, and the map data
in Bank00 for where the stairs are.
"""
import os
from collections import deque
from unittest import TestCase
from unittest.mock import patch

import pygame

from src.config.test_config import test_config
from src.constants import RAINBOW_BRIDGE_COORDINATES, RAINBOW_DROP_COORDINATES
from src.game import Game
from src.map_layouts import MapLayouts
from src.maps import CharlockB1, all_impassable_tiles, map_lookup

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

# Every concrete map, i.e. every NES map number from $01 to $1D (the Dragonlord's castle's sublevel 6 is split in two
# here, CharlockB7Wide and CharlockB7Narrow).
MAP_NAMES = sorted(MapLayouts().map_layout_lookup)
START = ('TantegelThroneRoom', (10, 13))
STAIR_TILES = ('BRICK_STAIR_DOWN', 'BRICK_STAIR_UP', 'GRASS_STAIR_DOWN')
# Overworld tiles that lead into a map
ENTRANCE_TILES = ('CASTLE', 'TOWN', 'CAVE', 'GRASS_STAIR_DOWN')
# Doors are opened with Magic Keys, which are always for sale
BLOCKING_TILES = tuple(tile for tile in all_impassable_tiles if tile != 'DOOR')
# NES MapEntryTbl: DL castle SL6(9,0) -> DL castle SL6(0,0) is one way. Going up from SL6(0,0) finds its earlier
# MapTargetTbl entry and leads back to SL5(5,5).
ONE_WAY_STAIRS = {('CharlockB7Narrow', (3, 12))}
# NES DLBFStatTbl: the Dragonlord sits at BF(16,24), CharlockB8 (28, 22), with large tiles (a counter, WOOD here) on
# three sides. The hero can walk up beside him at BF(17,24).
DRAGONLORD_AUDIENCE = ('CharlockB8', (28, 23))

# NES map (and, for the split sublevel 6, its row) -> this game's map and its (row, column) offset from NES (x, y).
NES_MAPS = {
    'OVERWORLD': ('Alefgard', (7, 8)),
    'THRONEROOM': ('TantegelThroneRoom', (6, 10)),
    'TANTCSTL_GF': ('TantegelCourtyard', (7, 7)),
    'GARINHAM': ('Garinham', (0, 9)),
    'TANTCSTL_SL': ('TantegelCellar', (1, 1)),
    'RAIN': ('StaffOfRainCave', (2, 2)),
    'RAINBOW': ('MagicTemple', (2, 2)),
    'DLCSTL_GF': ('CharlockB1', (6, 7)),
    'DLCSTL_SL1': ('CharlockB2', (3, 3)),
    'DLCSTL_SL2': ('CharlockB3', (3, 3)),
    'DLCSTL_SL3': ('CharlockB4', (3, 3)),
    'DLCSTL_SL4': ('CharlockB5', (3, 3)),
    'DLCSTL_SL5': ('CharlockB6', (3, 3)),
    'DLCSTL_SL6_0': ('CharlockB7Narrow', (3, 3)),  # the corridor at y = 0
    'DLCSTL_SL6_6': ('CharlockB7Wide', (-1, 3)),  # the corridor at y = 6
    'DLCSTL_BF': ('CharlockB8', (4, 6)),
    'SWAMPCAVE': ('SwampCave', (6, 4)),
    'RCKMTN_B1': ('MountainCaveB1', (1, 1)),
    'RCKMTN_B2': ('MountainCaveB2', (1, 1)),
    'CVGAR_B1': ('GarinsGraveB1', (1, 1)),
    'CVGAR_B2': ('GarinsGraveB2', (1, 1)),
    'CVGAR_B3': ('GarinsGraveB3', (1, 1)),
    'CVGAR_B4': ('GarinsGraveB4', (1, 1)),
    'ERDRCK_B1': ('ErdricksCaveB1', (3, 3)),
    'ERDRCK_B2': ('ErdricksCaveB2', (1, 1)),
}
# NES MapEntryTbl -> MapTargetTbl (Bank03), as ((map, x, y), (map, x, y)), for every pair of stairs. The overworld
# entrances into towns and castles are left out: those are left through their gates, not by stairs.
# Taking one of these stairs down (or entering from the overworld) uses the entry table to find the target; going up
# uses the target table to find the first matching entry.
NES_MAP_LINKS = (
    (('OVERWORLD', 81, 1), ('RAIN', 4, 9)),
    (('OVERWORLD', 104, 44), ('SWAMPCAVE', 0, 0)),
    (('OVERWORLD', 104, 49), ('SWAMPCAVE', 0, 29)),
    (('OVERWORLD', 29, 57), ('RCKMTN_B1', 0, 7)),
    (('OVERWORLD', 108, 109), ('RAINBOW', 0, 4)),
    (('OVERWORLD', 28, 12), ('ERDRCK_B1', 0, 0)),
    (('TANTCSTL_GF', 29, 29), ('TANTCSTL_SL', 0, 4)),
    (('THRONEROOM', 8, 8), ('TANTCSTL_GF', 7, 7)),
    (('GARINHAM', 19, 0), ('CVGAR_B1', 6, 11)),
    (('DLCSTL_GF', 10, 1), ('DLCSTL_SL1', 9, 0)),
    (('DLCSTL_GF', 4, 14), ('DLCSTL_SL1', 8, 13)),
    (('DLCSTL_GF', 15, 14), ('DLCSTL_SL1', 17, 15)),
    (('DLCSTL_SL1', 15, 1), ('DLCSTL_SL2', 8, 0)),
    (('DLCSTL_SL1', 13, 7), ('DLCSTL_SL2', 4, 4)),
    (('DLCSTL_SL1', 19, 7), ('DLCSTL_SL2', 9, 8)),
    (('DLCSTL_SL1', 14, 9), ('DLCSTL_SL2', 8, 9)),
    (('DLCSTL_SL1', 2, 14), ('DLCSTL_SL2', 0, 1)),
    (('DLCSTL_SL1', 2, 4), ('DLCSTL_SL2', 0, 0)),
    (('DLCSTL_SL1', 8, 19), ('DLCSTL_SL2', 5, 0)),
    (('DLCSTL_SL2', 3, 0), ('DLCSTL_SL3', 7, 0)),
    (('DLCSTL_SL2', 9, 1), ('DLCSTL_SL3', 2, 2)),
    (('DLCSTL_SL2', 0, 8), ('DLCSTL_SL3', 5, 4)),
    (('DLCSTL_SL2', 1, 9), ('DLCSTL_SL3', 0, 9)),
    (('DLCSTL_SL3', 1, 6), ('DLCSTL_SL4', 0, 9)),
    (('DLCSTL_SL3', 7, 7), ('DLCSTL_SL4', 7, 7)),
    (('DLCSTL_SL4', 2, 2), ('DLCSTL_SL5', 9, 0)),
    (('DLCSTL_SL4', 8, 1), ('DLCSTL_SL5', 4, 0)),
    (('DLCSTL_SL5', 5, 5), ('DLCSTL_SL6', 0, 0)),
    (('DLCSTL_SL5', 0, 0), ('DLCSTL_SL6', 0, 6)),
    (('DLCSTL_SL6', 9, 0), ('DLCSTL_SL6', 0, 0)),
    (('DLCSTL_SL6', 9, 6), ('DLCSTL_BF', 10, 29)),
    (('RCKMTN_B1', 0, 0), ('RCKMTN_B2', 0, 0)),
    (('RCKMTN_B1', 6, 5), ('RCKMTN_B2', 6, 5)),
    (('RCKMTN_B1', 12, 12), ('RCKMTN_B2', 12, 12)),
    (('CVGAR_B1', 1, 18), ('CVGAR_B2', 11, 2)),
    (('CVGAR_B2', 1, 1), ('CVGAR_B3', 14, 1)),
    (('CVGAR_B2', 12, 1), ('CVGAR_B3', 18, 1)),
    (('CVGAR_B2', 5, 6), ('CVGAR_B3', 6, 11)),
    (('CVGAR_B2', 1, 10), ('CVGAR_B3', 2, 17)),
    (('CVGAR_B2', 12, 10), ('CVGAR_B3', 18, 13)),
    (('CVGAR_B3', 9, 5), ('CVGAR_B4', 0, 4)),
    (('CVGAR_B3', 10, 9), ('CVGAR_B4', 5, 4)),
    (('ERDRCK_B1', 9, 9), ('ERDRCK_B2', 8, 9)),
)


def nes_location(nes_map: str, x: int, y: int) -> tuple:
    """An NES map location as (map name, (row, column)) here."""
    if nes_map == 'DLCSTL_SL6':
        nes_map = f'DLCSTL_SL6_{y}'
    map_name, (row_offset, column_offset) = NES_MAPS[nes_map]
    return map_name, (y + row_offset, x + column_offset)


def set_story_flags(game, rainbow_bridge_built: bool, charlock_stairs_revealed: bool) -> None:
    """NES F_RNBW_BRDG and F_PSG_FOUND."""
    game.rainbow_bridge_built = rainbow_bridge_built
    game.charlock_stairs_revealed = charlock_stairs_revealed


def build_world(rainbow_bridge_built: bool, charlock_stairs_revealed: bool) -> dict:
    """Load every map through MapManager.change_map, as the game would with these story flags set."""
    with patch('src.game.SCALED'):
        game = Game(test_config)
    set_story_flags(game, rainbow_bridge_built, charlock_stairs_revealed)
    world = {}
    for map_name in MAP_NAMES:
        next_map = map_lookup[map_name](game.config)
        game.change_map(next_map, destination_coordinates=next_map.initial_coordinates)
        world[map_name] = game.current_map
    return world


def tile_name(world: dict, map_name: str, coordinates: tuple) -> str | None:
    current_map = world[map_name]
    row, column = coordinates
    if not (0 <= row < len(current_map.layout) and 0 <= column < len(current_map.layout[0])):
        return None
    return current_map.get_tile_by_value(current_map.layout[row][column])


def destination(world: dict, staircase: dict) -> tuple:
    """Where a staircase puts the hero: MapManager.change_map falls back on the map's initial coordinates."""
    return staircase.get('destination_coordinates') or world[staircase['map']].initial_coordinates


def explore(world: dict) -> dict:
    """Breadth-first search over (map, tile) from the hero's first tile in the throne room. Returns each reached
    (map, tile) mapped to the one it was reached from."""
    came_from: dict = {START: None}
    queue = deque([START])
    while queue:
        map_name, (row, column) = state = queue.popleft()
        current_map = world[map_name]
        next_states = [(map_name, (row + d_row, column + d_column))
                       for d_row, d_column in ((-1, 0), (1, 0), (0, -1), (0, 1))]
        staircase = current_map.staircases.get((row, column))
        if staircase is not None:
            next_states.append((staircase['map'], destination(world, staircase)))
        for next_state in next_states:
            tile = tile_name(world, *next_state)
            if next_state in came_from or tile is None or tile in BLOCKING_TILES:
                continue
            came_from[next_state] = state
            queue.append(next_state)
    return came_from


def maps_reached(reached: dict) -> set:
    return {map_name for map_name, _ in reached}


class TestMapConnectivity(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        cls.world_at_start = build_world(rainbow_bridge_built=False, charlock_stairs_revealed=False)
        cls.world_with_bridge = build_world(rainbow_bridge_built=True, charlock_stairs_revealed=False)
        cls.world_at_the_end = build_world(rainbow_bridge_built=True, charlock_stairs_revealed=True)
        cls.reached_at_start = explore(cls.world_at_start)
        cls.reached_with_bridge = explore(cls.world_with_bridge)
        cls.reached_at_the_end = explore(cls.world_at_the_end)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def all_staircases(self, world):
        for map_name in MAP_NAMES:
            for coordinates, staircase in world[map_name].staircases.items():
                yield map_name, coordinates, staircase

    # Every map

    def test_every_map_is_reachable_by_the_end_of_the_game(self):
        self.assertEqual(maps_reached(self.reached_at_the_end), set(MAP_NAMES))

    def test_only_charlock_is_out_of_reach_before_the_rainbow_bridge(self):
        charlock = {name for name in MAP_NAMES if name.startswith('Charlock')}
        self.assertEqual(maps_reached(self.reached_at_start), set(MAP_NAMES) - charlock)

    # Staircases

    def test_every_staircase_has_a_destination(self):
        for map_name, coordinates, staircase in self.all_staircases(self.world_at_the_end):
            with self.subTest(map=map_name, coordinates=coordinates):
                self.assertIn(staircase['map'], MAP_NAMES)
                self.assertIsNotNone(staircase.get('destination_coordinates'),
                                     "MapManager.change_map would fall back on the map's initial coordinates")

    def test_every_staircase_is_on_stairs_or_an_entrance(self):
        world = self.world_at_the_end
        for map_name, coordinates, staircase in self.all_staircases(world):
            tile = tile_name(world, map_name, coordinates)
            with self.subTest(map=map_name, coordinates=coordinates, tile=tile):
                if map_name == 'Alefgard':
                    self.assertIn(tile, ENTRANCE_TILES)
                elif tile not in STAIR_TILES:
                    # Otherwise it's a town gate (create_town_gates), which can only lead out to the overworld. Gates
                    # are whole lines along the map's edges, so some of them are on walls or water, or off the map.
                    self.assertEqual(staircase['map'], 'Alefgard')

    def test_every_staircase_lands_somewhere_walkable(self):
        world = self.world_at_the_end
        for map_name, coordinates, staircase in self.all_staircases(world):
            landing = destination(world, staircase)
            tile = tile_name(world, staircase['map'], landing)
            with self.subTest(map=map_name, coordinates=coordinates, to=(staircase['map'], landing), tile=tile):
                self.assertIsNotNone(tile, "off the map")
                self.assertNotIn(tile, BLOCKING_TILES)
                if map_name != 'Alefgard' and tile_name(world, map_name, coordinates) in STAIR_TILES:
                    # NES MapEntryTbl/MapTargetTbl link stairs to stairs (or to the overworld entrance)
                    self.assertIn(tile, STAIR_TILES + ENTRANCE_TILES)

    def test_stairs_lead_back_where_they_came_from(self):
        world = self.world_at_the_end
        for map_name, coordinates, staircase in self.all_staircases(world):
            if (map_name, coordinates) in ONE_WAY_STAIRS:
                continue
            if tile_name(world, map_name, coordinates) not in STAIR_TILES + ENTRANCE_TILES:
                continue  # a town gate: the many gate tiles all lead to one overworld tile
            target = world[staircase['map']]
            landing = destination(world, staircase)
            if tile_name(world, staircase['map'], landing) not in STAIR_TILES + ENTRANCE_TILES:
                continue  # an overworld entrance into a town, castle or Charlock: those are left by their gates
            with self.subTest(map=map_name, coordinates=coordinates, to=(staircase['map'], landing)):
                self.assertIn(landing, target.staircases)
                way_back = target.staircases[landing]
                self.assertEqual((way_back['map'], destination(world, way_back)), (map_name, coordinates))

    def test_every_stair_tile_leads_somewhere(self):
        world = self.world_at_the_end
        for map_name in MAP_NAMES:
            current_map = world[map_name]
            for row, tiles in enumerate(current_map.layout):
                for column, value in enumerate(tiles):
                    if current_map.get_tile_by_value(value) in STAIR_TILES:
                        with self.subTest(map=map_name, coordinates=(row, column)):
                            self.assertIn((row, column), current_map.staircases)

    def test_stairs_follow_the_nes_map_entrance_and_target_tables(self):
        world = self.world_at_the_end
        way_up: dict = {}
        for entrance, target in NES_MAP_LINKS:
            way_up.setdefault(target, entrance)  # NES: going up takes the first MapTargetTbl match
        for entrance, target in NES_MAP_LINKS:
            for (from_map, from_coordinates), (to_map, to_coordinates) in (
                    (nes_location(*entrance), nes_location(*target)),
                    (nes_location(*target), nes_location(*way_up[target]))):
                with self.subTest(nes=(entrance, target), map=from_map, coordinates=from_coordinates):
                    staircase = world[from_map].staircases.get(from_coordinates)
                    self.assertIsNotNone(staircase)
                    self.assertEqual((staircase['map'], staircase.get('destination_coordinates')),
                                     (to_map, to_coordinates))

    def test_the_way_down_to_the_dragonlord_follows_the_nes_tables(self):
        # NES MapEntryTbl/MapTargetTbl (Bank03): DL castle SL6(9,6) <-> DL castle BF(10,29)
        world = self.world_at_the_end
        self.assertEqual(world['CharlockB7Wide'].staircases[(5, 12)]['destination_coordinates'], (33, 16))
        self.assertEqual(world['CharlockB8'].staircases[(33, 16)]['destination_coordinates'], (5, 12))
        self.assertEqual(tile_name(world, 'CharlockB8', (33, 16)), 'BRICK_STAIR_UP')

    # The way to the Dragonlord

    def test_rainbow_bridge_connects_the_mainland_to_charlock(self):
        row, column = RAINBOW_BRIDGE_COORDINATES
        self.assertEqual(tile_name(self.world_at_start, 'Alefgard', (row, column)), 'WATER')
        self.assertEqual(tile_name(self.world_with_bridge, 'Alefgard', (row, column)), 'BRIDGE')
        self.assertIn(('Alefgard', RAINBOW_DROP_COORDINATES), self.reached_at_start)
        self.assertNotIn(('CharlockB1', (25, 17)), self.reached_at_start)
        self.assertIn(('CharlockB1', (25, 17)), self.reached_with_bridge)

    def test_the_dragonlord_is_out_of_reach_until_the_hidden_stairs_are_found(self):
        hidden_stairs = CharlockB1.HIDDEN_STAIRCASE_COORDINATES
        self.assertNotIn(hidden_stairs, self.world_with_bridge['CharlockB1'].staircases)
        self.assertNotIn(DRAGONLORD_AUDIENCE, self.reached_with_bridge)

    def test_the_dragonlord_can_be_reached_once_the_hidden_stairs_are_found(self):
        self.assertEqual(tile_name(self.world_at_the_end, 'CharlockB1', CharlockB1.HIDDEN_STAIRCASE_COORDINATES),
                         'BRICK_STAIR_DOWN')
        self.assertIn(DRAGONLORD_AUDIENCE, self.reached_at_the_end)
        route = []
        state = DRAGONLORD_AUDIENCE
        while state is not None:
            route.append(state[0])
            state = self.reached_at_the_end[state]
        floors: list = []
        for map_name in reversed(route):
            if not floors or floors[-1] != map_name:
                floors.append(map_name)
        # The shortest way goes down through every floor
        self.assertEqual([name for name in floors if name.startswith('Charlock')],
                         ['CharlockB1', 'CharlockB2', 'CharlockB3', 'CharlockB4', 'CharlockB5', 'CharlockB6',
                          'CharlockB7Wide', 'CharlockB8'])
