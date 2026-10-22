import os
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame
from pygame import KEYDOWN, K_RETURN, event

from src.config.test_config import test_config
from src.game import Game
from tests.mock_map import MockMap

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


class TestCommandMenu(TestCase):

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
        self.game.current_map = MockMap(self.game.config)
        self.game.current_map.load_map(self.game.player, (0, 0), self.game.game_state.config["TILE_SIZE"])

    # def test_take(self):
    # pygame.key.get_pressed = create_key_mock(pygame.K_s)
    # self.game.cmd_menu.take()
    # pygame.key.get_pressed = create_key_mock(pygame.K_k)
    # self.assertEqual(self.game.current_map.tile_key['BRICK']['val'],
    #                  self.game.current_map.layout[0][1])

    def test_npc_is_across_counter(self):
        self.assertFalse(self.game.cmd_menu.npc_is_across_counter(self.game.current_map.characters['HERO']))

    def test_dragon_scale(self):
        defense_before = self.game.player.defense_power
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text:
            self.game.cmd_menu.dragon_scale()
            self.assertTrue(self.game.player.wearing_dragon_scale)
            self.assertEqual(self.game.player.defense_power, defense_before + 2)
            self.assertEqual(show_text.call_args.args[0],
                             f"{self.game.player.name} donned the scale of the dragon.")

            self.game.cmd_menu.dragon_scale()
            self.assertEqual(self.game.player.defense_power, defense_before + 2)
            self.assertEqual(show_text.call_args.args[0], "Thou art already wearing the scale of the dragon.")

    def test_fighters_ring_has_no_stat_effect(self):
        attack_before = self.game.player.attack_power
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text:
            self.game.cmd_menu.fighters_ring()
            self.assertTrue(self.game.player.wearing_fighters_ring)
            self.assertEqual(show_text.call_args.args[0], f"{self.game.player.name} put on the Fighter's Ring.")

            self.game.cmd_menu.fighters_ring()
            self.assertEqual(show_text.call_args.args[0],
                             f"{self.game.player.name} adjusted the position of the Fighter's Ring.")
        self.assertEqual(self.game.player.attack_power, attack_before)

    def test_fighters_ring_with_attack_bonus_option(self):
        self.game.player.fighters_ring_attack_bonus = 2
        attack_before = self.game.player.attack_power
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box'):
            self.game.cmd_menu.fighters_ring()
            self.game.cmd_menu.fighters_ring()
        self.assertEqual(self.game.player.attack_power, attack_before + 2)

    def test_take_item(self):
        self.assertEqual([], self.game.player.inventory)
        mocked_return = MagicMock()
        mocked_return.type = KEYDOWN
        mocked_return.key = K_RETURN
        with patch.object(event, 'get', return_value=[mocked_return]) as mock_method:
            self.game.cmd_menu.take_item("test_item")
        self.assertIn("test_item", self.game.player.inventory)

    def test_take_gold(self):
        self.assertEqual(0, self.game.player.gold)
        mocked_return = MagicMock()
        mocked_return.type = KEYDOWN
        mocked_return.key = K_RETURN
        with patch.object(event, 'get', return_value=[mocked_return]) as mock_method:
            self.game.cmd_menu.take_gold({'item': 'GOLD', 'amount': 120})
        self.assertEqual(120, self.game.player.gold)

    def cast_sleep(self, enemy, roll):
        battle = MagicMock(no_op=False)
        battle.enemy = enemy
        self.game.cmd_menu.current_battle = battle
        with patch('src.menu.random.randint', return_value=roll), \
                patch.object(self.game.cmd_menu, 'show_line_in_dialog_box') as show_line:
            self.game.cmd_menu.sleep()
        return battle, [c.args[0] for c in show_line.call_args_list]

    def test_sleep_puts_enemy_to_sleep(self):
        from src.enemy import Slime
        slime = Slime()
        battle, messages = self.cast_sleep(slime, roll=0)
        self.assertTrue(slime.is_asleep)
        self.assertTrue(battle.no_op)
        self.assertEqual(messages, ['Thou hast put the Slime to sleep.', 'The Slime is asleep.'])

    def test_sleep_fails_against_resistance(self):
        # Metal Slime resists sleep 15/16: only a roll of 15 succeeds
        from src.enemy import MetalSlime
        metal_slime = MetalSlime()
        battle, messages = self.cast_sleep(metal_slime, roll=14)
        self.assertFalse(metal_slime.is_asleep)
        self.assertFalse(battle.no_op)
        self.assertEqual(messages, ['The spell will not work.'])
        self.cast_sleep(metal_slime, roll=15)
        self.assertTrue(metal_slime.is_asleep)

    def test_sleep_outside_battle(self):
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text:
            self.game.cmd_menu.sleep()
        self.assertEqual(show_text.call_args.args[0], 'But nothing happened.')

    def test_casting_with_low_mp_outside_battle_does_not_crash(self):
        self.game.player.spells = ["HEAL"]
        self.game.player.current_mp = 0
        mocked_return = MagicMock()
        mocked_return.type = KEYDOWN
        mocked_return.key = K_RETURN
        with patch.object(event, 'get', return_value=[mocked_return]), \
                patch.object(self.game.cmd_menu, 'show_line_in_dialog_box') as show_line:
            self.game.cmd_menu.display_item_menu('spells')
        self.assertEqual(show_line.call_args.args[0], 'Thy MP is too low.')
