import unittest
from unittest.mock import Mock, patch

import pygame

from src.battle import has_final_consonant, get_postposition, Battle, calculate_enemy_attack_damage, \
    randomize_enemy_hp
from src.config.test_config import test_config


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

        # NES CalcPlyrGold: 5 * (192 + 63) // 256 = 4 on the highest roll
        with patch('src.battle.random.randint', return_value=63):
            self.battle.enemy_defeated(cmd_menu, screen, player, music_enabled, enemy)
        self.assertEqual(player.total_experience, 10)
        self.assertEqual(player.gold, 4)

    def test_enemy_vanishes_and_victory_music_starts_right_after_the_done_well_line(self):
        # NES EnemyDefeated: "Thou hast done well in defeating the ENMY." has no WAIT, then ClearSpriteRAM erases the
        # enemy and MSC_VICTORY starts, all before the experience and gold lines
        events = []
        cmd_menu = Mock()
        cmd_menu.show_line_in_dialog_box.side_effect = lambda line, **kwargs: events.append(
            (line.split('\n')[0], kwargs.get('skip_text', False)))
        player = Mock(total_experience=0, gold=0, level=1, spells=[])
        enemy = Mock(xp=1, gold=2)
        enemy.name = 'Slime'
        with patch.object(self.battle, 'make_enemy_image_disappear', side_effect=lambda screen: events.append('erase')), \
                patch.object(self.battle.sound, 'play_sound', side_effect=lambda sound: events.append('victory')), \
                patch('src.battle.mixer'), patch.object(self.battle, 'check_player_level_up'):
            self.battle.enemy_defeated(cmd_menu, Mock(), player, True, enemy)
        done_well = self.battle.get_enemy_defeated_string(enemy).split('\n')[0]
        self.assertEqual(events[:3], [(done_well, True), 'erase', 'victory'])
        self.assertEqual(len(events), 4)  # then the experience and gold

    def test_get_enemy_draws_near_string(self):
        self.battle.enemy.name = 'Slime'
        expected_string = '슬라임이 나타났다!\n어떻게 하겠나?\n'
        self.assertEqual(expected_string, self.battle.get_enemy_draws_near_string())

        self.battle.enemy.name = 'Slime'
        self.battle.config['LANGUAGE'] = 'English'
        self.battle = Battle(self.battle.config, self.enemy_name, self.current_map)
        expected_string = 'A Slime draws near!\nCommand?\n'
        self.assertEqual(expected_string, self.battle.get_enemy_draws_near_string())

    def test_draws_near_uses_a_or_an_with_the_default_language(self):
        # NES TextBlock "A ENM2 draws near!": DoENM2 -> CheckAToAn adds 'n' before a vowel. The default config's
        # language must be the 'English' name for this rule to apply (it used to be the locale code 'en').
        config = {**self.battle.config, 'LANGUAGE': test_config['LANGUAGE']}
        self.assertEqual(test_config['LANGUAGE'], 'English')
        for enemy_name, expected in (('Slime', 'A Slime draws near!\nCommand?\n'),
                                     ('Axe Knight', 'An Axe Knight draws near!\nCommand?\n')):
            with self.subTest(enemy_name=enemy_name):
                battle = Battle(config, enemy_name, self.current_map)
                self.assertEqual(battle.get_enemy_draws_near_string(), expected)

    def player_damage(self, attack_power, enemy_defense, rolls, enemy_name='Slime'):
        player = Mock(attack_power=attack_power)
        enemy = Mock(defense=enemy_defense)
        enemy.name = enemy_name
        with patch('src.battle.random.randint', side_effect=rolls):
            return self.battle.calculate_attack_damage(Mock(), player, enemy)

    def test_player_normal_attack_range(self):
        # Attack 20 vs. defense 10: base 15, damage 3 to 7 (base / 4 to base / 2)
        self.assertEqual(self.player_damage(20, 10, [1, 0]), 3)
        self.assertEqual(self.player_damage(20, 10, [1, 255]), 7)
        for roll in range(256):
            self.assertTrue(3 <= self.player_damage(20, 10, [1, roll]) <= 7)

    def test_player_weak_attack_against_high_defense(self):
        # Attack 10 vs. Metal Slime defense 255: base < 2, so 0 or 1 damage
        self.assertEqual(self.player_damage(10, 255, [1, 0]), 0)
        self.assertEqual(self.player_damage(10, 255, [1, 1]), 1)
        # base exactly 2 is a normal attack
        self.assertEqual(self.player_damage(7, 10, [1, 0]), 0)
        self.assertEqual(self.player_damage(7, 10, [1, 255]), 1)

    def test_excellent_move(self):
        # 1 in 32 (roll of 0): attack - (attack // 2 * rand) // 256
        self.assertEqual(self.player_damage(40, 10, [0, 0]), 40)
        self.assertEqual(self.player_damage(40, 10, [0, 255]), 21)

    def test_no_excellent_move_against_dragonlord(self):
        for name in ('Dragonlord', 'Dragonlord 2'):
            with self.subTest(enemy=name):
                # The excellent-move roll of 0 is ignored; a normal attack is used instead
                self.assertEqual(self.player_damage(40, 10, [0, 0], enemy_name=name), 8)

    def test_battle_run_failed_sets_no_op(self):
        """Failed run attempt should not grant enemy a free extra turn via the outer loop."""
        cmd_menu = Mock()
        cmd_menu.game.enemy_move = Mock(return_value=False)
        player = Mock()
        player.agility = 1
        player.current_hp = 10
        player.is_dead = False
        current_battle = Mock()
        current_battle.enemy.is_asleep = False
        current_battle.enemy.defense = 255
        current_battle.no_op = False

        with patch('src.battle.random.randint', return_value=255):
            result = self.battle.battle_run(cmd_menu, player, current_battle)

        self.assertFalse(result)
        cmd_menu.game.enemy_move.assert_called_once_with(current_battle)

    def test_battle_run_blocked_but_enemy_flees_ends_battle(self):
        cmd_menu = Mock()
        cmd_menu.game.enemy_move = Mock(return_value=True)
        player = Mock()
        player.agility = 1
        current_battle = Mock()
        current_battle.enemy.is_asleep = False
        current_battle.enemy.defense = 255

        with patch('src.battle.random.randint', return_value=255):
            result = self.battle.battle_run(cmd_menu, player, current_battle)

        self.assertTrue(result)
        shown = [c.args[0] for c in cmd_menu.show_line_in_dialog_box.call_args_list]
        self.assertFalse(any("Command?" in line for line in shown))

    def test_battle_run_success_returns_true(self):
        cmd_menu = Mock()
        player = Mock()
        player.agility = 255
        player.current_hp = 10
        current_battle = Mock()
        current_battle.enemy.is_asleep = False
        current_battle.enemy.defense = 1

        with patch('src.battle.random.randint', return_value=1):
            result = self.battle.battle_run(cmd_menu, player, current_battle)

        self.assertTrue(result)

    def test_display_battle_window_fades_the_enemy_in(self):
        # NES LoadEnemyGFX fades the enemy in before "draws near" is shown
        drawer, cmd_menu = Mock(), Mock()
        order = []
        drawer.fade_in_enemy.side_effect = lambda *a: order.append('fade')
        cmd_menu.show_line_in_battle_dialog_box.side_effect = lambda *a: order.append('text')
        with patch.object(self.battle, 'transition_battle_background_image_effect'):
            self.battle.display_battle_window(Mock(), drawer, cmd_menu, Mock(), Mock(), (255, 255, 255), Mock())
        drawer.fade_in_enemy.assert_called_once()
        self.assertEqual(drawer.fade_in_enemy.call_args.args[1], 'Slime')
        self.assertEqual(order, ['fade', 'text'])


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


class TestRandomizeEnemyHp(unittest.TestCase):
    """Starting enemy HP, per the NES ModEnHitPoints routine."""

    def hp(self, enemy_class, roll):
        with patch('src.battle.random.randint', return_value=roll):
            return randomize_enemy_hp(enemy_class())

    def test_hp_is_75_to_100_percent_of_listed(self):
        from src.enemy import Golem
        # Golem: 70 HP -> 70 - (70 * rand // 256) // 4
        self.assertEqual(self.hp(Golem, 0), 70)
        self.assertEqual(self.hp(Golem, 255), 53)

    def test_dragonlord_final_form_always_full_hp(self):
        from src.enemy import Dragonlord2
        self.assertEqual(self.hp(Dragonlord2, 255), Dragonlord2().max_hp)

    def test_battle_uses_randomized_hp(self):
        config = {'LANGUAGE': 'English', 'TILE_SIZE': 32, 'MUSIC_ENABLED': False,
                  'ORCHESTRA_MUSIC_ENABLED': False, 'SOUND_ENABLED': False}
        with patch('src.battle.random.randint', return_value=255):
            battle = Battle(config, 'Golem', Mock())
        self.assertEqual(battle.enemy.hp, 53)
        self.assertEqual(battle.enemy.max_hp, 70)
