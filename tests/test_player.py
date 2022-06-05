from unittest import TestCase

from src.player.player import Player
from test_game import MockMap


class TestPlayer(TestCase):

    def setUp(self):
        self.player = Player(center_point=None, images=None, current_map=MockMap())

    def test_get_level_by_experience(self):
        self.assertEqual(1, self.player.level)

        self.player.total_experience = 7
        self.player.level = self.player.get_level_by_experience()
        self.assertEqual(2, self.player.level)

        self.player.total_experience = 23
        self.player.level = self.player.get_level_by_experience()
        self.assertEqual(3, self.player.level)

        self.player.total_experience = 47
        self.player.level = self.player.get_level_by_experience()
        self.assertEqual(4, self.player.level)

        self.player.total_experience = 110
        self.player.level = self.player.get_level_by_experience()
        self.assertEqual(5, self.player.level)

        self.player.total_experience = 220
        self.player.level = self.player.get_level_by_experience()
        self.assertEqual(6, self.player.level)

        self.player.total_experience = 450
        self.player.level = self.player.get_level_by_experience()
        self.assertEqual(7, self.player.level)

        self.player.total_experience = 800
        self.player.level = self.player.get_level_by_experience()
        self.assertEqual(8, self.player.level)

        self.player.total_experience = 1300
        self.player.level = self.player.get_level_by_experience()
        self.assertEqual(9, self.player.level)

        self.player.total_experience = 2000
        self.player.level = self.player.get_level_by_experience()
        self.assertEqual(10, self.player.level)

        self.player.total_experience = 2900
        self.player.level = self.player.get_level_by_experience()
        self.assertEqual(11, self.player.level)
