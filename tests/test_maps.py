import inspect
import os
from unittest import TestCase

from src import maps
from tests.test_game import TestMockMap

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ['SDL_AUDIODRIVER'] = 'dummy'


class TestDragonWarriorMap(TestCase):

    def setUp(self) -> None:
        self.dragon_warrior_map = TestMockMap()

    def test_get_initial_character_location(self):
        self.assertEqual(self.dragon_warrior_map.get_initial_character_location('HERO').take(0), 0)
        self.assertEqual(self.dragon_warrior_map.get_initial_character_location('HERO').take(1), 0)

    def test_music_path_in_every_map(self):
        for dw_map, map_class in inspect.getmembers(maps, inspect.isclass):
            if dw_map not in ('ABC', 'AnimatedSprite', 'BaseSprite', 'Direction', 'DragonWarriorMap', 'FixedCharacter', 'Group', 'LayeredDirty', 'MapLayouts', 'MapWithoutNPCs', 'RoamingCharacter'):
                initialized_map_class = map_class()
                self.assertTrue(hasattr(initialized_map_class, 'music_file_path'))
