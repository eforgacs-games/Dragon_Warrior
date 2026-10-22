import unittest
from unittest.mock import Mock, patch

import pygame

from src.battle import has_final_consonant, get_postposition, Battle, calculate_enemy_attack_damage


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


    def test_battle_run_failed_sets_no_op(self):
        """Failed run attempt should not grant enemy a free extra turn via the outer loop."""
        cmd_menu = Mock()
        cmd_menu.game.enemy_move = Mock()
        player = Mock()
        player.agility = 1
        player.current_hp = 10
        player.is_dead = False
        current_battle = Mock()
        current_battle.enemy.is_asleep = False
        current_battle.enemy.speed = 255
        current_battle.no_op = False

        with patch('src.battle.random.randint', return_value=255):
            result = self.battle.battle_run(cmd_menu, player, current_battle)

        self.assertFalse(result)
        cmd_menu.game.enemy_move.assert_called_once_with(current_battle)

    def test_battle_run_success_returns_true(self):
        cmd_menu = Mock()
        player = Mock()
        player.agility = 255
        player.current_hp = 10
        current_battle = Mock()
        current_battle.enemy.is_asleep = False
        current_battle.enemy.speed = 1

        with patch('src.battle.random.randint', return_value=1):
            result = self.battle.battle_run(cmd_menu, player, current_battle)

        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()


class TestCalculateEnemyAttackDamage(unittest.TestCase):
    """Enemy physical attack damage, per the NES EnCalcHitDmg routine."""

    def damage(self, attack, defense_power, random_number):
        player = Mock(defense_power=defense_power)
        enemy = Mock(attack=attack)
        with patch('src.battle.random.randint', return_value=random_number):
            return calculate_enemy_attack_damage(player, enemy)

    def test_normal_attack_range(self):
        # Poltergeist (attack 18) vs. defense 4: base 16, damage 4 to 8
        self.assertEqual(self.damage(18, 4, 0), 4)
        self.assertEqual(self.damage(18, 4, 255), 8)

    def test_normal_attack_always_within_quarter_to_half_of_base(self):
        for random_number in range(256):
            self.assertTrue(4 <= self.damage(18, 4, random_number) <= 8)

    def test_armor_reduces_damage(self):
        # Attack 100: no gear with 20 agility (defense 10) vs. Magic Armor + Silver Shield (defense 54)
        self.assertEqual(self.damage(100, 10, 255), 47)
        self.assertEqual(self.damage(100, 54, 255), 36)

    def test_weak_attack_when_defense_is_high(self):
        # Attack 18 vs. defense 54: weak attack, damage 0 to 3
        self.assertEqual(self.damage(18, 54, 0), 0)
        self.assertEqual(self.damage(18, 54, 255), 3)

    def test_weak_attack_threshold(self):
        # Attack 18: base 10 (defense 16) is a normal attack; base 9 (defense 18) is weak
        self.assertEqual(self.damage(18, 16, 0), 2)
        self.assertEqual(self.damage(18, 18, 0), 0)
