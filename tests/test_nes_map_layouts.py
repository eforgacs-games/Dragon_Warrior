"""
Every map layout matches the NES map data tile by tile.

The NES data is MapDatTbl, the per-map data blocks (DLCstlGFDat, KolDat, RckMtnB2Dat, ...) and the overworld rows
(WrldMapPtrTbl, Row000-Row119) in Bank00 of the nmikstas disassembly, decoded by tests/nes_maps.py. The links between
maps are MapEntryTbl and MapTargetTbl in Bank03.
"""
import os
from unittest import TestCase

import pygame

from src import map_layouts
from src.config.test_config import test_config
from src.map_layouts import MapLayouts
from src.maps import map_lookup
from tests.nes_map_data import MAPS
from tests.nes_maps import NES_MAPS, OVERWORLD_SIZE, boundary_tile, decode_map, layout_location, nes_tiles

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

TILE_NAMES = {value: name for name, value in vars(map_layouts).items() if name.isupper() and isinstance(value, int)}

# The only places where a layout is meant to differ from the NES map data: (map, (row, column)) -> (tile here, NES
# tile, why). Treasure chests, doors and the Rainbow Bridge's water match the NES data, and are changed while the game
# runs, as on the NES (MapManager.apply_chest_history, the door history, MapManager.apply_rainbow_bridge).
INTENTIONAL_DIFFERENCES = {
    # NES GetBlockID reads the stairs at DL castle GF(10,1) as a force field until F_PSG_FOUND is set. Here the layout
    # has the force field, and CharlockB1.reveal_hidden_staircase puts the stairs in.
    ('CharlockB1', (7, 17)): ('BARRIER', 'BRICK_STAIR_DOWN', 'the hidden stairs behind the throne'),
    # NES Swamp cave(5,18) is Gwaelin's block, read as brick once F_DONE_GWAELIN is set. Here it's brick, with Gwaelin
    # as an NPC on it until she's rescued (MapManager.place_princess_gwaelin).
    ('SwampCave', (24, 9)): ('BRICK', 'PRINCESS_GWAELIN', "Gwaelin's block"),
}

# NES MapEntryTbl/MapTargetTbl: the overworld entrances into towns and castles, as (overworld (x, y), (map, (x, y))).
# The other overworld entrances are stairs, and tests/test_map_connectivity.py checks those.
OVERWORLD_ENTRANCES = (
    ((2, 2), ('Garinham', (0, 14))),
    ((104, 10), ('Kol', (19, 23))),
    ((48, 41), ('Brecconary', (0, 15))),
    ((43, 43), ('TantegelCourtyard', (11, 29))),
    ((48, 48), ('CharlockB1', (10, 19))),
    ((102, 72), ('Rimuldar', (29, 14))),
    ((25, 89), ('Hauksness', (0, 10))),
    ((73, 102), ('Cantlin', (15, 0))),
)
STAIR_TILES = ('BRICK_STAIR_DOWN', 'BRICK_STAIR_UP', 'GRASS_STAIR_DOWN')


def tile_name(value: int) -> str:
    """This game's tile name, with every coast counted as water: the NES works out the shores while drawing (DoWtrConv),
    and the map data only has water."""
    name = TILE_NAMES[value]
    return 'WATER' if name.endswith('_COAST') else name


def expected_tiles(map_name: str) -> dict:
    """{(row, column): NES tile} for every tile the NES map data covers in one of this game's maps."""
    tiles: dict = {}
    for number, _nes_name, name, offset, nes_rows in NES_MAPS:
        if name == map_name:
            tiles.update(nes_tiles(number, offset, nes_rows))
    return tiles


def nes_map_number(map_name: str) -> int:
    return next(number for number, _nes_name, name, _offset, _rows in NES_MAPS if name == map_name)


class TestNESMapData(TestCase):
    """The decoded NES data itself."""

    def test_every_map_has_its_mapdattbl_size(self):
        for number, (label, columns, rows, data) in MAPS.items():
            with self.subTest(map=label):
                decoded = decode_map(number)
                self.assertEqual(len(decoded), rows)
                self.assertEqual({len(row) for row in decoded}, {columns})
                self.assertEqual(len(data), rows)

    def test_the_overworld_is_120_by_120(self):
        overworld = decode_map(0x01)
        self.assertEqual(len(overworld), OVERWORLD_SIZE)
        self.assertEqual({len(row) for row in overworld}, {OVERWORLD_SIZE})

    def test_landmarks(self):
        # Tantegel Castle at Overworld(43,43), the Rainbow Bridge's water at (64,49) (NES ChkRnbwBrdg), the Dragonlord's
        # throne room stairs at DL castle GF(10,1), Gwaelin in the Swamp cave at (5,18)
        overworld = decode_map(0x01)
        self.assertEqual(overworld[43][43], 'CASTLE')
        self.assertEqual(overworld[49][64], 'WATER')
        self.assertEqual(decode_map(0x02)[1][10], 'BRICK_STAIR_DOWN')
        self.assertEqual(decode_map(0x15)[18][5], 'PRINCESS_GWAELIN')


class TestNESMapLayouts(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.layouts = MapLayouts().map_layout_lookup

    def test_every_map_is_compared(self):
        self.assertEqual({name for _number, _nes_name, name, _offset, _rows in NES_MAPS}, set(self.layouts))

    def test_every_layout_matches_the_nes_map_data(self):
        for map_name, layout in self.layouts.items():
            with self.subTest(map=map_name):
                mismatches = []
                for (row, column), nes_tile in sorted(expected_tiles(map_name).items()):
                    self.assertTrue(0 <= row < len(layout) and 0 <= column < len(layout[row]),
                                    f'NES tile at {(row, column)} is off the layout')
                    here = tile_name(layout[row][column])
                    if here != nes_tile and (map_name, (row, column)) not in INTENTIONAL_DIFFERENCES:
                        mismatches.append(((row, column), here, nes_tile))
                self.assertEqual(mismatches, [], '(row, column), tile here, NES tile')

    def test_the_intentional_differences_are_still_needed(self):
        for (map_name, (row, column)), (here, nes_tile, why) in INTENTIONAL_DIFFERENCES.items():
            with self.subTest(map=map_name, coordinates=(row, column), why=why):
                self.assertEqual(tile_name(self.layouts[map_name][row][column]), here)
                self.assertEqual(expected_tiles(map_name)[(row, column)], nes_tile)

    def test_outside_the_nes_map_is_the_boundary_block(self):
        # NES MapDatTbl: the boundary block is what's shown past the map's edges
        for map_name, layout in self.layouts.items():
            with self.subTest(map=map_name):
                covered = expected_tiles(map_name)
                boundary = boundary_tile(nes_map_number(map_name))
                outside = {(row, column): tile_name(value) for row, values in enumerate(layout)
                           for column, value in enumerate(values) if (row, column) not in covered}
                self.assertEqual({coordinates: tile for coordinates, tile in outside.items() if tile != boundary}, {})


class TestNESMapWarps(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))
        # The display stays up afterwards: tests/test_player.py, which runs next, needs one and doesn't set it up
        cls.maps = {name: map_class(test_config) for name, map_class in map_lookup.items()
                    if name in MapLayouts().map_layout_lookup}

    def test_overworld_entrances_land_where_the_nes_puts_the_hero(self):
        alefgard = self.maps['Alefgard']
        for (x, y), (map_name, (target_x, target_y)) in OVERWORLD_ENTRANCES:
            with self.subTest(map=map_name):
                entrance = layout_location('Alefgard', x, y)
                landing = layout_location(map_name, target_x, target_y)
                self.assertEqual(alefgard.staircases[entrance]['map'], map_name)
                self.assertEqual(alefgard.staircases[entrance]['destination_coordinates'], landing)

    def test_leaving_a_town_starts_just_outside_the_nes_map(self):
        # The NES leaves a town, castle or Charlock's ground floor for the overworld when the hero steps off the map
        for map_name, current_map in self.maps.items():
            covered = expected_tiles(map_name)
            rows = [row for row, _column in covered]
            columns = [column for _row, column in covered]
            top, bottom, left, right = min(rows), max(rows), min(columns), max(columns)
            for (row, column), staircase in current_map.staircases.items():
                in_layout = 0 <= row < len(current_map.layout) and 0 <= column < len(current_map.layout[0])
                if staircase['map'] != 'Alefgard' or (
                        in_layout and current_map.get_tile_by_value(current_map.layout[row][column]) in STAIR_TILES):
                    continue
                with self.subTest(map=map_name, gate=(row, column)):
                    self.assertNotIn((row, column), covered)
                    self.assertTrue(row in (top - 1, bottom + 1) or column in (left - 1, right + 1))
