import unittest
from unittest.mock import Mock, patch

import pygame

from src.battle import has_final_consonant, get_postposition, Battle


class TestBattleMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()
        cls.screen = pygame.display.set_mode((800, 600))  # Initialize display

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_has_final_consonant(self):
        self.assertTrue(has_final_consonant('갈'))
        self.assertFalse(has_final_consonant('가'))

    def test_get_postposition(self):
        self.assertEqual(get_postposition('갈', '을', '를'), '을')
        self.assertEqual(get_postposition('가', '을', '를'), '를')

    def setUp(self):
        config = {
            'LANGUAGE': 'Korean',
            'TILE_SIZE': 32,
            'MUSIC_ENABLED': True,
            'ORCHESTRA_MUSIC_ENABLED': False,
            'SOUND_ENABLED': False,
        }
        self.enemy_name = 'Slime'
        self.current_map = Mock()  # Mocking the map for simplicity
        self.battle = Battle(config, self.enemy_name, self.current_map)

    @patch('src.battle.Directories', autospec=True)
    @patch('pygame.mixer.music')
    def test_enemy_defeated(self, MockDirectories, mock_music):
        cmd_menu = Mock()
        screen = Mock()
        player = Mock()
        player.name = 'Hero'
        player.total_experience = 0
        player.gold = 0
        player.level = 1
        player.strength = 10
        player.agility = 10
        player.max_hp = 100
        player.max_mp = 10
        player.spells = []
        music_enabled = True
        enemy = Mock()
        enemy.name = 'Slime'
        enemy.xp = 10
        enemy.gold = 5
        levels_list = [{'total_exp': 0}, {'total_exp': 10}]

        self.battle.enemy_defeated(cmd_menu, screen, player, music_enabled, enemy)
        self.assertEqual(player.total_experience, 10)
        self.assertEqual(player.gold, 5)

    def test_get_enemy_draws_near_string(self):
        self.battle.enemy.name = 'Slime'
        expected_string = '슬라임이 나타났다!\n어떻게 하겠나?\n'
        self.assertEqual(expected_string, self.battle.get_enemy_draws_near_string())

        self.battle.enemy.name = 'Slime'
        self.battle.config['LANGUAGE'] = 'English'
        self.battle = Battle(self.battle.config, self.enemy_name, self.current_map)
        expected_string = 'A Slime draws near!\nCommand?\n'
        self.assertEqual(expected_string, self.battle.get_enemy_draws_near_string())

    def test_calculate_attack_damage(self):
        cmd_menu = Mock()
        player = Mock()
        player.attack_power = 20
        enemy = Mock()
        enemy.defense = 10

        damage = self.battle.calculate_attack_damage(cmd_menu, player, enemy)
        expected_lower_bound = round((player.attack_power - (enemy.defense / 2)) / 2)
        expected_upper_bound = round((player.attack_power - (enemy.defense / 2)) * 2)
        self.assertTrue(expected_lower_bound <= damage <= expected_upper_bound)


if __name__ == '__main__':
    unittest.main()
