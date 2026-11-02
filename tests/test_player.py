import io
from contextlib import redirect_stdout
from unittest import TestCase

import pygame

from src.config.test_config import test_config
from src.direction import Direction
from src.maps import MapWithoutNPCs
from src.player.player import Player
from src.player.player_stats import get_stats_for_level, levels_list

layout = [[3, 0, 3],
          [1, 2, 3],
          [3, 3, 3]]


class MockMap(MapWithoutNPCs):
    __test__ = False

    def __init__(self, config):
        super().__init__(layout, config, None, (0, 0))

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.DOWN.value


class TestPlayer(TestCase):

    @classmethod
    def setUpClass(cls):
        # MockMap converts tile images, which needs a video mode; don't rely on one left over from an earlier
        # test file, since that file may have called pygame.quit()
        pygame.init()
        pygame.display.set_mode((800, 600))

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        self.player = Player(center_point=None, images=None, current_map=MockMap(test_config),
                             god_mode=test_config['GOD_MODE'])

    def test_defense_power_is_half_agility_plus_gear(self):
        self.player.agility = 21
        self.player.armor = ""
        self.player.shield = ""
        self.player.update_defense_power()
        self.assertEqual(self.player.defense_power, 10)

        self.player.armor = "Magic Armor"
        self.player.update_defense_power()
        self.assertEqual(self.player.defense_power, 34)

        self.player.shield = "Silver Shield"
        self.player.update_defense_power()
        self.assertEqual(self.player.defense_power, 54)

    def test_dragon_scale_adds_two_defense(self):
        self.player.agility = 21
        self.player.wearing_dragon_scale = True
        self.player.update_defense_power()
        self.assertEqual(self.player.defense_power, 12)

    def test_fighters_ring_has_no_effect_by_default(self):
        self.player.weapon = "Club"
        self.player.wearing_fighters_ring = True
        self.player.update_attack_power()
        self.assertEqual(self.player.attack_power, self.player.strength + 4)

    def test_fighters_ring_attack_bonus_option(self):
        self.player.fighters_ring_attack_bonus = 2
        self.player.weapon = "Club"
        self.player.update_attack_power()
        self.assertEqual(self.player.attack_power, self.player.strength + 4)
        self.player.wearing_fighters_ring = True
        self.player.update_attack_power()
        self.assertEqual(self.player.attack_power, self.player.strength + 4 + 2)

    def test_unknown_weapon_is_reported_and_adds_nothing(self):
        """A weapon name that isn't in the weapons table (a typo, or an old save) is reported, and the attack power
        is the bare strength, as with no weapon."""
        self.player.weapon = "Wooden Spoon"
        output = io.StringIO()
        with redirect_stdout(output):
            self.player.update_attack_power()
        self.assertEqual("ERROR: Wooden Spoon is not a valid weapon.\n", output.getvalue())
        self.assertEqual(self.player.strength, self.player.attack_power)

    def test_no_weapon_is_not_reported(self):
        self.player.weapon = ""
        output = io.StringIO()
        with redirect_stdout(output):
            self.player.update_attack_power()
        self.assertEqual("", output.getvalue())
        self.assertEqual(self.player.strength, self.player.attack_power)

    def test_god_mode_starts_at_level_30_with_every_spell_and_99999_hp_mp_and_gold(self):
        player = Player(center_point=None, images=None, current_map=MockMap(test_config), god_mode=True)
        self.assertTrue(player.god_mode)
        self.assertEqual(65536, player.total_experience)
        self.assertEqual(30, player.level)
        level_30 = get_stats_for_level(player.name, 30)
        self.assertEqual((level_30['strength'], level_30['agility']), (player.strength, player.agility))
        every_spell = [row['spell'] for row in levels_list.values() if row['spell']]
        self.assertEqual(every_spell, player.spells)
        self.assertEqual((99_999, 99_999), (player.max_hp, player.current_hp))
        self.assertEqual((99_999, 99_999), (player.max_mp, player.current_mp))
        self.assertEqual(99_999, player.gold)

    def test_without_god_mode_the_hero_starts_at_level_1_with_nothing(self):
        player = Player(center_point=None, images=None, current_map=MockMap(test_config), god_mode=False)
        self.assertFalse(player.god_mode)
        self.assertEqual((0, 1, 0), (player.total_experience, player.level, player.gold))
        self.assertEqual([], player.spells)

    def test_set_initial_stats_fills_hp_and_mp_and_works_out_the_powers_for_the_name(self):
        """Ann = A $24 + n $17 + n $17 + blank $60 = $B2 -> %10: strength and max HP cut, bonus 0. At level 1 that's
        strength 4 * 9 // 10 = 3, agility 4, max HP 15 * 9 // 10 = 13 and max MP 0 (tests/test_player_stats.py).
        The placeholder name's stats (15 HP, strength 4) mustn't be left over."""
        self.player.current_hp, self.player.current_mp = 1, 7
        self.player.name = "Ann"
        self.player.set_initial_stats()
        self.assertEqual((3, 4, 13, 0), (self.player.strength, self.player.agility, self.player.max_hp,
                                         self.player.max_mp))
        self.assertEqual((13, 0), (self.player.current_hp, self.player.current_mp))
        self.assertEqual((3, 2), (self.player.attack_power, self.player.defense_power))

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
