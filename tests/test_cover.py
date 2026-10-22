import os
from collections import Counter
from unittest import TestCase
from unittest.mock import MagicMock

import pygame

from src import maps
from src.common import BLACK
from src.config.test_config import test_config
from src.drawer import draw_cover, get_player_block
from src.game import Game
from src.maps_functions import covered_cells
from tests.test_drawer import _make_drawer

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

TILE_SIZE = test_config['TILE_SIZE']


class TestCoveredCells(TestCase):

    def test_offsets_nes_coordinates(self):
        self.assertEqual(frozenset({(10, 12), (10, 13), (11, 12)}),
                         covered_cells({0: (2, 3), 1: range(2, 3)}, row_offset=10, column_offset=10))

    def test_no_rows(self):
        self.assertEqual(frozenset(), covered_cells({}, row_offset=8, column_offset=10))


class TestTownCoveredAreas(TestCase):
    """NES CoverDatPtr data for the four towns that have covered areas (Bank00 InitMapData)."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))
        cls.towns = {name: maps.map_lookup[name](test_config) for name in
                     ('Brecconary', 'Garinham', 'Cantlin', 'Rimuldar')}

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_covered_block_counts(self):
        # The number of nibbles with bit 3 set in each town's covered-area data
        self.assertEqual({'Brecconary': 68, 'Garinham': 144, 'Cantlin': 120, 'Rimuldar': 125},
                         {name: len(town.covered_area) for name, town in self.towns.items()})

    def test_brecconary_item_shop(self):
        brecconary = self.towns['Brecconary']
        self.assertFalse(brecconary.is_covered(30, 32))  # in front of the shop
        self.assertFalse(brecconary.is_covered(31, 32))  # the way in (NES 22,23)
        self.assertTrue(brecconary.is_covered(32, 32))  # inside
        self.assertTrue(brecconary.is_covered(33, 35))  # the shopkeeper
        self.assertTrue(brecconary.is_covered(31, 31))  # the shop's walls are under the roof too
        self.assertFalse(brecconary.is_covered(31, 37))

    def test_brecconary_fairy_water_shop(self):
        brecconary = self.towns['Brecconary']
        self.assertEqual('DOOR', brecconary.get_tile_by_value(brecconary.layout[14][31]))
        self.assertFalse(brecconary.is_covered(14, 31))  # the door (NES 21,6)
        self.assertTrue(brecconary.is_covered(13, 31))
        self.assertTrue(brecconary.is_covered(12, 34))  # the woman selling fairy water
        self.assertTrue(brecconary.is_covered(10, 30))
        self.assertFalse(brecconary.is_covered(9, 30))

    def test_garinham_door(self):
        garinham = self.towns['Garinham']
        self.assertEqual('DOOR', garinham.get_tile_by_value(garinham.layout[10][26]))
        self.assertFalse(garinham.is_covered(10, 26))
        self.assertTrue(garinham.is_covered(9, 26))
        self.assertTrue(garinham.is_covered(10, 25))
        self.assertFalse(garinham.is_covered(11, 26))

    def test_cantlin_and_rimuldar(self):
        self.assertTrue(self.towns['Cantlin'].is_covered(24, 15))  # the wizard in the middle of town (NES 15,16)
        self.assertFalse(self.towns['Cantlin'].is_covered(18, 11))
        self.assertTrue(self.towns['Rimuldar'].is_covered(31, 11))  # the wizard at NES 3,23
        self.assertFalse(self.towns['Rimuldar'].is_covered(27, 18))  # the way in (NES 10,19)

    def test_covered_area_is_inside_the_map(self):
        for name, town in self.towns.items():
            for row, column in town.covered_area:
                self.assertLess(row, len(town.layout), name)
                self.assertLess(column, len(town.layout[0]), name)

    def test_off_the_map_is_never_covered(self):
        self.assertFalse(self.towns['Brecconary'].is_covered(-1, -1))
        self.assertFalse(self.towns['Brecconary'].is_covered(1000, 1000))

    def test_other_maps_have_no_cover(self):
        pygame.display.set_mode((1, 1))
        for name in ('TantegelThroneRoom', 'TantegelCourtyard', 'Kol', 'Hauksness', 'Alefgard'):
            town = maps.map_lookup[name](test_config)
            self.assertEqual(frozenset(), town.covered_area, name)
            town.player_under_cover = True
            self.assertFalse(town.is_hidden_by_cover(0, 0), name)


class TestHiddenByCover(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))
        cls.brecconary = maps.map_lookup['Brecconary'](test_config)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_outside_hides_the_covered_blocks(self):
        self.brecconary.player_under_cover = False
        self.assertTrue(self.brecconary.is_hidden_by_cover(32, 32))
        self.assertFalse(self.brecconary.is_hidden_by_cover(30, 32))

    def test_inside_hides_the_uncovered_blocks(self):
        self.brecconary.player_under_cover = True
        self.assertFalse(self.brecconary.is_hidden_by_cover(32, 32))
        self.assertTrue(self.brecconary.is_hidden_by_cover(30, 32))
        self.assertTrue(self.brecconary.is_hidden_by_cover(0, 0))

    def test_npcs_cannot_cross_the_cover_boundary(self):
        self.assertTrue(self.brecconary.crosses_cover_boundary(31, 32, 32, 32))
        self.assertTrue(self.brecconary.crosses_cover_boundary(32, 32, 31, 32))
        self.assertFalse(self.brecconary.crosses_cover_boundary(32, 32, 32, 33))
        self.assertFalse(self.brecconary.crosses_cover_boundary(30, 32, 31, 32))

    def test_npc_crosses_cover_boundary(self):
        game = MagicMock()
        game.current_map = self.brecconary
        npc = MagicMock(row=32, column=32)
        game.get_next_coordinates.return_value = (32, 31)  # (column, row): stepping out of the shop
        self.assertTrue(Game.npc_crosses_cover_boundary(game, npc))
        game.get_next_coordinates.return_value = (33, 32)
        self.assertFalse(Game.npc_crosses_cover_boundary(game, npc))
        game.get_next_coordinates.return_value = None
        self.assertFalse(Game.npc_crosses_cover_boundary(game, npc))


class TestDrawCover(TestCase):
    """Which tiles are drawn as roof or blank in each state (NES ChkCoveredArea)."""

    ROOF_COLOR = (200, 0, 0)
    FLOOR_COLOR = (0, 0, 200)

    def setUp(self):
        self.current_map = MagicMock()
        self.current_map.config = test_config
        self.current_map.covered_area = frozenset({(0, 0), (0, 1)})
        self.current_map.floor_tile_key = {'ROOF': {'val': 0}}
        roof = pygame.Surface((TILE_SIZE, TILE_SIZE))
        roof.fill(self.ROOF_COLOR)
        self.current_map.map_tiles = [[roof]]
        self.current_map.is_hidden_by_cover = lambda row, column: maps.DragonWarriorMap.is_hidden_by_cover(
            self.current_map, row, column)
        self.current_map.is_covered = lambda row, column: (row, column) in self.current_map.covered_area
        self.background = pygame.Surface((TILE_SIZE * 3, TILE_SIZE))
        self.background.fill(self.FLOOR_COLOR)
        self.cells = [(0, 0), (0, 1), (0, 2)]

    def colors(self):
        return [tuple(self.background.get_at((column * TILE_SIZE + 1, 1)))[:3] for _, column in self.cells]

    def test_outside_draws_roof_over_covered_tiles(self):
        self.current_map.player_under_cover = False
        draw_cover(self.current_map, self.background, self.cells)
        self.assertEqual([self.ROOF_COLOR, self.ROOF_COLOR, self.FLOOR_COLOR], self.colors())

    def test_inside_blanks_uncovered_tiles(self):
        self.current_map.player_under_cover = True
        draw_cover(self.current_map, self.background, self.cells)
        self.assertEqual([self.FLOOR_COLOR, self.FLOOR_COLOR, BLACK], self.colors())

    def test_only_the_given_cells_are_drawn(self):
        self.current_map.player_under_cover = False
        draw_cover(self.current_map, self.background, [(0, 1)])
        self.assertEqual(Counter({self.FLOOR_COLOR: 2, self.ROOF_COLOR: 1}), Counter(self.colors()))


class TestNPCsUnderCover(TestCase):
    """NES $B957: NPCs on the other side of the cover from the hero aren't drawn."""

    def test_hidden_npcs_are_not_drawn(self):
        drawer = _make_drawer()
        current_map = MagicMock()
        current_map.is_hidden_by_cover = lambda row, column: (row, column) == (2, 2)
        characters = {}
        for identifier, position in (('HERO', (2, 2)), ('MERCHANT', (2, 2)), ('MAN', (5, 5))):
            sprites = MagicMock()
            sprites.draw.return_value = [identifier]
            characters[identifier] = {'character': MagicMock(row=position[0], column=position[1]),
                                      'character_sprites': sprites}
        current_map.characters = characters
        foreground_rects: list = []
        drawer.handle_sprite_drawing_and_animation(current_map, foreground_rects, MagicMock(), enable_animate=True)
        self.assertEqual(['HERO', 'MAN'], foreground_rects)
        characters['MERCHANT']['character_sprites'].draw.assert_not_called()
        characters['MERCHANT']['character'].animate.assert_called_once()


class TestGetPlayerBlock(TestCase):

    def test_standing_uses_the_rect(self):
        player = MagicMock(is_moving=False, row=1, column=1, rect=pygame.Rect(TILE_SIZE * 4, TILE_SIZE * 3, 1, 1))
        self.assertEqual((3, 4), get_player_block(player, TILE_SIZE))

    def test_moving_uses_the_block_the_step_began_on(self):
        # the NES switches only once the step is done (DoCoveredArea runs after CharXPos/CharYPos change)
        player = MagicMock(is_moving=True, row=5, column=6, rect=pygame.Rect(TILE_SIZE * 6, TILE_SIZE * 5 - 4, 1, 1))
        self.assertEqual((5, 6), get_player_block(player, TILE_SIZE))
