import inspect
import os
from unittest import TestCase
from unittest.mock import patch

import pygame

from src import maps
from src.config.test_config import test_config
from src.game import Game
from tests.test_game import MockMap

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


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
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.dragon_warrior_map = MockMap(self.game.config)

    def test_get_initial_character_location(self):
        self.assertEqual(self.dragon_warrior_map.get_initial_character_location('HERO'), (0, 0))

    def test_music_path_in_every_map(self):
        for dw_map, map_class in inspect.getmembers(maps, inspect.isclass):
            # excluding non-map classes
            if dw_map not in (
                    'ABC', 'AnimatedSprite', 'BaseSprite', 'BasementWithNPCs', 'BasementWithoutNPCs', 'CaveMap',
                    'Direction', 'Directories', 'DragonWarriorMap', 'FixedCharacter',
                    'Graphics', 'Group', 'LayeredDirty', 'MapLayouts', 'MapWithoutNPCs', 'Player', 'RoamingCharacter'):
                initialized_map_class = map_class(self.game.config)
                self.assertTrue(hasattr(initialized_map_class, 'music_file_path'))
