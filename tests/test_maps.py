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
            # excluding non-map classes
            if dw_map not in (
                    'ABC', 'AnimatedSprite', 'BaseSprite', 'BasementWithNPCs', 'BasementWithoutNPCs', 'CaveMap',
                    'Direction', 'Directories', 'DragonWarriorMap', 'FixedCharacter',
                    'Graphics', 'Group', 'LayeredDirty', 'MapLayouts', 'MapWithoutNPCs', 'Player', 'RoamingCharacter'):
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
