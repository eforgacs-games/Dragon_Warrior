"""Player 2's controls (co-op, src/controls.py PLAYER_TWO_ACTIONS): the numpad and the second controller, read on the
second hero's turns in a fight."""
from unittest import TestCase
from unittest.mock import Mock, patch

import pygame
from pygame import K_KP0, K_KP2, K_KP8, K_KP_MINUS, K_KP_PERIOD, K_KP_PLUS, K_ESCAPE, K_k

from src.common import A_BUTTON_KEYS, B_BUTTON_KEYS, START_BUTTON_KEYS, UP_KEYS, reject_keys
from src.config.test_config import test_config
from src.controls import ACTIONS_BY_NAME, PLAYER_ONE, PLAYER_TWO, KeySet, input_player, player_input, reset_controls
from src.gamepad import Gamepad, Gamepads, PadState, direction_key
from src.party import new_hero
from tests import helpers
from tests.test_gamepad import FakeBackend, FakePad, pad


class TestTheKeys(TestCase):

    def setUp(self):
        reset_controls()
        self.addCleanup(reset_controls)

    def test_on_the_numpad(self):
        self.assertEqual(
            {'P2_A': K_KP0, 'P2_B': K_KP_PERIOD, 'P2_START': K_KP_PLUS, 'P2_SELECT': K_KP_MINUS, 'P2_UP': K_KP8,
             'P2_DOWN': K_KP2},
            {name: ACTIONS_BY_NAME[name].keys[0].key for name in ('P2_A', 'P2_B', 'P2_START', 'P2_SELECT', 'P2_UP',
                                                                 'P2_DOWN')})

    def test_the_nes_buttons_read_player_2s_keys(self):
        self.assertIn(K_k, A_BUTTON_KEYS)
        with player_input(PLAYER_TWO):
            self.assertEqual((K_KP0,), tuple(A_BUTTON_KEYS))  # no SMART A: that's player 1's keyboard
            self.assertEqual((K_KP8,), tuple(UP_KEYS))
            self.assertEqual((K_KP_PLUS,), tuple(START_BUTTON_KEYS))
            self.assertIn(K_KP_PERIOD, B_BUTTON_KEYS)
            self.assertNotIn(K_ESCAPE, reject_keys)  # B's second key is player 1's keyboard's
            self.assertIn(K_ESCAPE, KeySet('A', fixed=(K_ESCAPE,)))  # a key set's fixed keys stay
            self.assertEqual((), tuple(KeySet('OPTIONS')))  # this game's own actions are player 1's
        self.assertIn(K_k, A_BUTTON_KEYS)
        self.assertNotIn(K_KP0, A_BUTTON_KEYS)

    def test_back_to_player_1_after_an_exception(self):
        def fail():
            with player_input(PLAYER_TWO):
                raise ValueError
        self.assertRaises(ValueError, fail)
        self.assertEqual(PLAYER_ONE, input_player())


class TestTheSecondController(TestCase):

    def setUp(self):
        pygame.init()
        reset_controls()
        self.addCleanup(reset_controls)

    def test_presses_player_2s_keys(self):
        player_two = Gamepad(FakeBackend(), player=PLAYER_TWO, slot=1)
        player_two.direction = 'UP'
        keys = player_two.pad_keys(PadState(frozenset({'b', 'a', 'start', 'back'})))
        self.assertEqual({K_KP0, K_KP_PERIOD, K_KP_PLUS, K_KP_MINUS, K_KP8}, keys)
        self.assertEqual(K_KP2, direction_key('DOWN', PLAYER_TWO))

    def test_only_the_nes_buttons(self):
        player_two = Gamepad(FakeBackend(), player=PLAYER_TWO, slot=1)
        self.assertEqual(set(), player_two.pad_keys(PadState(frozenset({'leftshoulder', 'lefttrigger', 'y'}))))

    def test_the_second_plugged_in(self):
        first, second = FakePad(), FakePad()
        backend = FakeBackend(first, second)
        backend.open_nth = lambda slot: backend.pads[slot] if slot < len(backend.pads) else None
        player_one, player_two = Gamepad(backend), Gamepad(backend, player=PLAYER_TWO, slot=1)
        for gamepad in (player_one, player_two):
            gamepad.check_devices()
        self.assertIs(first, player_one.device)
        self.assertIs(second, player_two.device)

    def test_none_with_one_plugged_in(self):
        backend = FakeBackend(FakePad())
        backend.open_nth = Mock(return_value=None)
        player_two = Gamepad(backend, player=PLAYER_TWO, slot=1)
        player_two.check_devices()
        self.assertIsNone(player_two.device)
        backend.open_nth.assert_not_called()

    def test_the_speed_trigger_is_player_1s(self):
        player_two = Gamepad(FakeBackend(), player=PLAYER_TWO, slot=1)
        with patch('src.gamepad.step_game_speed') as step:
            player_two.update(pad('righttrigger'))
        step.assert_not_called()

    def test_both_read_together(self):
        one, two = Mock(held={1}), Mock(held={2})
        gamepads = Gamepads(one, two)
        gamepads.poll()
        one.poll.assert_called_once()
        two.poll.assert_called_once()
        self.assertEqual({1, 2}, gamepads.held)


@patch('src.battle_controller.Battle')
class TestTheSecondHerosTurn(TestCase):

    def setUp(self):
        pygame.init()
        self.addCleanup(patch.stopall)
        self.game = helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True})
        self.game.player.name = 'Ann'
        self.game.companion = new_hero(self.game, 'Gwen')
        self.controller = self.game.battle_ctrl
        patch.object(self.controller, 'start_fight', return_value=False).start()
        patch.object(self.controller, 'face_down_after_fight').start()
        patch.object(self.game.music_player, 'load_and_play_music').start()

    def test_on_player_2s_joypad(self, battle_class):
        battle = battle_class.return_value
        battle.enemy.hp = 5
        battle.enemy.name = 'Slime'
        turns = []

        def turn(run_away, current_battle):
            turns.append((self.game.player.name, input_player()))
            self.controller.turn_hero = self.game.companion if len(turns) == 1 else None
            if len(turns) == 3:
                current_battle.enemy.hp = 0
            return False
        with patch.object(self.controller, 'handle_battle_prompts', side_effect=turn):
            self.controller.fight_enemy('Slime')
        self.assertEqual([('Ann', PLAYER_ONE), ('Gwen', PLAYER_TWO), ('Ann', PLAYER_ONE)], turns)
        self.assertEqual(PLAYER_ONE, input_player())

    def test_the_enemys_turn_is_player_1s(self, battle_class):
        seen = []
        with patch.object(self.controller, 'enemy_move', side_effect=lambda battle: seen.append(input_player())), \
                patch('src.battle_controller.hero_random.randint', return_value=1), \
                player_input(PLAYER_TWO):
            self.controller.enemy_round(Mock())
        self.assertEqual([PLAYER_ONE], seen)
