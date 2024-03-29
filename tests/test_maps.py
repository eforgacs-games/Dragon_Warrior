import inspect
import os
from unittest import TestCase
from unittest.mock import patch

from src import maps
from src.config.test_config import test_config
from src.game import Game
from tests.test_game import MockMap

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


class TestDragonWarriorMap(TestCase):

    @patch('src.game.Game.set_screen')
    def setUp(self, mock_set_screen) -> None:
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
