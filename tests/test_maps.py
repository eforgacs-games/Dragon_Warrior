import inspect
from unittest import TestCase

import pygame

from src import maps
from src.config.test_config import test_config
from tests.test_game import MockMap
from tests.helpers import new_game


class TestDragonWarriorMap(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()
        cls.screen = pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self) -> None:
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        self.game = new_game()
        self.dragon_warrior_map = MockMap(self.game.config)

    def test_initial_coordinates(self):
        self.assertEqual(self.dragon_warrior_map.initial_coordinates, (0, 0))

    def test_music_path_in_every_map(self):
        for dw_map, map_class in inspect.getmembers(maps, inspect.isclass):
            # excluding non-map classes (imported ones, like collections.abc.Callable, and the map base classes)
            if map_class.__module__ == maps.__name__ and dw_map not in (
                    'ABC', 'AnimatedSprite', 'BaseSprite', 'BasementWithNPCs', 'BasementWithoutNPCs', 'CaveMap',
                    'Direction', 'Directories', 'DragonWarriorMap', 'FixedCharacter',
                    'Graphics', 'Group', 'LayeredDirty', 'MapLayouts', 'MapWithoutNPCs', 'NPC', 'Player',
                    'RoamingCharacter'):
                initialized_map_class = map_class(self.game.config)
                self.assertTrue(hasattr(initialized_map_class, 'music_file_path'))

    def test_every_npc_stands_on_a_floor_tile(self):
        # Every NPC's block in the layout is a real floor tile (the NES map data), so map_npc never adds a second
        # "underlying" tile under an NPC
        for map_name, map_class in maps.map_lookup.items():
            if map_name in ('BasementWithNPCs', 'BasementWithoutNPCs', 'CaveMap', 'DragonWarriorMap', 'MapWithoutNPCs'):
                continue
            dw_map = map_class(self.game.config)
            for (row, column), character_name in dw_map.npc_coordinates.items():
                self.assertTrue(dw_map.has_floor_tile(row, column), f'{map_name} {character_name} at {row},{column}')


class TestComposedCoastTiles(TestCase):
    """The shore blocks tileset.png doesn't have are made of the quarters of ones it has, the way NES GFXTilesTbl's
    shore blocks share their 8x8 tiles (#316)."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))
        cls.alefgard = maps.Alefgard(test_config)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def image(self, tile_name):
        return self.alefgard.normal_tile_image(self.alefgard.floor_tile_key[tile_name]['val'])

    def quarter(self, tile_name, quarter_x, quarter_y):
        image = self.image(tile_name)
        half_width, half_height = image.get_width() // 2, image.get_height() // 2
        return pygame.image.tobytes(image.subsurface((quarter_x * half_width, quarter_y * half_height, half_width,
                                                      half_height)), 'RGBA')

    def test_each_quarter_comes_from_the_shore_block_with_the_same_two_sides(self):
        for tile_name, sources in maps.COMPOSED_COAST_TILES.items():
            for (quarter_x, quarter_y), source in zip(((0, 0), (1, 0), (0, 1), (1, 1)), sources):
                with self.subTest(tile=tile_name, quarter=(quarter_x, quarter_y)):
                    self.assertEqual(self.quarter(source, quarter_x, quarter_y),
                                     self.quarter(tile_name, quarter_x, quarter_y))

    def test_a_shore_on_both_sides_differs_from_one_side(self):
        self.assertNotEqual(pygame.image.tobytes(self.image('LEFT_RIGHT_COAST'), 'RGBA'),
                            pygame.image.tobytes(self.image('LEFT_COAST'), 'RGBA'))
        self.assertNotEqual(pygame.image.tobytes(self.image('BOTTOM_TOP_COAST'), 'RGBA'),
                            pygame.image.tobytes(self.image('TOP_COAST'), 'RGBA'))

    def test_the_overworld_draws_them(self):
        tiles = self.alefgard.get_tiles_in_current_map()
        self.assertLessEqual(set(maps.COMPOSED_COAST_TILES), tiles)
