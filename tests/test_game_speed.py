"""The game speed (keys 1 to 4, src/waiting.py): every timed wait and timer runs N times as fast at speed N, the keys
work in battles and dialogs too, and the speed never changes what happens."""
import os
import random
from collections import defaultdict
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame
from pygame import K_1, K_2, K_3, K_4, K_RETURN, KEYDOWN, K_k
from pygame.event import Event

from src import waiting
from src.battle import Battle
from src.battle_controller import BattleController
from src.config.test_config import test_config
from src.game import Game
from src.menu import CommandMenu
from src.visual_effects import fade, player_hit_shake
from src.waiting import game_speed, game_ticks, get_events, reset_game_speed, set_game_speed, wait, wait_frames
from tests.mock_map import MockMap

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


class FakeClock:
    """Stands in for pygame.time's clock: real time only passes when something waits."""

    def __init__(self):
        self.now = 0.0

    def get_ticks(self) -> int:
        return int(self.now)

    def wait(self, milliseconds) -> int:
        self.now += milliseconds
        return int(milliseconds)

    def patches(self):
        """Patch pygame.time itself, so every module that reads it (through src.waiting or directly) sees this
        clock."""
        return [patch('pygame.time.get_ticks', self.get_ticks), patch('pygame.time.wait', self.wait),
                patch('pygame.time.delay', self.wait)]


def keydown(key_code):
    return Event(KEYDOWN, key=key_code)


class GameSpeedTestCase(TestCase):

    def setUp(self):
        reset_game_speed()
        self.addCleanup(reset_game_speed)
        self.clock = FakeClock()
        for clock_patch in self.clock.patches():
            clock_patch.start()
            self.addCleanup(clock_patch.stop)


class TestWait(GameSpeedTestCase):

    def test_wait_takes_one_nth_of_the_time_at_speed_n(self):
        for speed in (1, 2, 3, 4):
            with self.subTest(speed=speed):
                set_game_speed(speed)
                start = self.clock.now
                wait(1000)
                self.assertAlmostEqual(1000 / speed, self.clock.now - start, delta=2)

    def test_wait_frames_takes_one_nth_of_the_time_at_speed_n(self):
        set_game_speed(4)
        wait_frames(60)
        self.assertAlmostEqual(250, self.clock.now, delta=2)

    def test_no_wait_still_skips_the_wait(self):
        set_game_speed(2)
        wait(1000, {'NO_WAIT': True})
        self.assertEqual(0, self.clock.now)

    def test_a_speed_change_during_a_wait_applies_to_the_rest_of_it(self):
        def speed_up_halfway():
            if self.clock.now >= 500:
                set_game_speed(4)

        with patch('src.waiting.check_for_quit', side_effect=speed_up_halfway):
            wait(1000)
        # 500 ms at 1x, then the other 500 game ms at 4x
        self.assertAlmostEqual(500 + 125, self.clock.now, delta=16)

    def test_game_ticks_run_n_times_as_fast_and_never_jump(self):
        self.clock.now = 1000
        self.assertEqual(1000, game_ticks())  # at speed 1 it is get_ticks
        set_game_speed(3)
        self.assertEqual(1000, game_ticks())  # changing the speed doesn't move the clock
        self.clock.now += 100
        self.assertEqual(1300, game_ticks())
        set_game_speed(1)
        self.clock.now += 100
        self.assertEqual(1400, game_ticks())

    def test_scaled_ms(self):
        set_game_speed(4)
        self.assertEqual(5, waiting.scaled_ms(20))
        self.assertEqual(1, waiting.scaled_ms(1))
        self.assertEqual(0, waiting.scaled_ms(0))


class TestSpeedKeys(GameSpeedTestCase):

    def test_get_events_takes_the_speed_keys_out_and_sets_the_speed(self):
        other = keydown(K_k)
        with patch('pygame.event.get', return_value=[keydown(K_3), other]):
            self.assertEqual([other], get_events())
        self.assertEqual(3, game_speed())

    def test_keys_held_during_a_wait_set_the_speed(self):
        with patch('src.waiting.display.get_init', return_value=True), \
                patch('src.waiting.event.peek', return_value=False), \
                patch('src.waiting.key.get_pressed', return_value=defaultdict(int, {K_4: 1})):
            wait(400)
        self.assertEqual(4, game_speed())
        self.assertLess(self.clock.now, 400 / 4 + 20)  # and the rest of the wait ran at the new speed

    @patch('src.battle_controller.display')
    def test_keys_work_during_a_battle(self, mock_display):
        game = MagicMock()
        game.auto_battle = False
        game.game_state.config = {"TILE_SIZE": 32}
        game.player.is_asleep = False
        controller = BattleController(game)
        battle = MagicMock(turn=0, last_turn=0)
        for key_code, speed in ((K_2, 2), (K_4, 4), (K_1, 1), (K_3, 3)):
            with self.subTest(speed=speed), patch('pygame.event.get', return_value=[keydown(key_code)]):
                self.assertFalse(controller.handle_battle_prompts(False, battle))
                self.assertEqual(speed, game_speed())
                self.assertEqual(0, battle.turn)  # the key isn't a battle command

    def test_keys_work_during_a_dialog_without_closing_it(self):
        menu = MagicMock()
        menu.game.show_arrow = True
        pressed = [[keydown(K_2)], [keydown(K_RETURN)]]
        with patch('pygame.event.get', side_effect=pressed) as get, patch('pygame.event.clear'):
            CommandMenu.wait_for_dialog_key(menu, shows_arrow=True, skip_text=False, temp_text_start=None,
                                            disable_sound=True)
        self.assertEqual(2, game_speed())
        self.assertEqual(2, get.call_count)  # the 2 didn't close the dialog: it waited for the RETURN


class TestBattleTiming(GameSpeedTestCase):
    """A real battle turn (the hero's attack and the enemy's), with its effects and messages, takes 1/N of the time at
    speed N, and comes out the same."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.game.current_map = MockMap(self.game.config)
        self.game.current_map.load_map(self.game.player, (0, 0), self.game.game_state.config["TILE_SIZE"])
        super().setUp()
        config = self.game.game_state.config
        # Waits and effects on (but nothing drawn to the dummy screen that would cost real time)
        self.addCleanup(config.update, {'NO_WAIT': config['NO_WAIT'], 'NO_BLIT': config['NO_BLIT'],
                                        'TEXT_SPEED': config['TEXT_SPEED']})
        config.update({'NO_WAIT': False, 'NO_BLIT': False, 'TEXT_SPEED': 'Normal'})

    def battle_turn(self, speed):
        """Run one turn at speed; return (real time it took, what happened)."""
        set_game_speed(speed)
        random.seed(1234)
        player = self.game.player
        player.current_hp = player.max_hp = 50
        battle = Battle(self.game.config, 'Slime', self.game.current_map)
        battle.enemy.hp = 100
        player.attack_power = 20  # so the hero hits (and the enemy flashes)
        controller = self.game.battle_ctrl
        start = self.clock.now
        # The player's key presses to move the messages on take no time here
        with patch.object(controller.sound, 'play_sound'), patch.object(controller.cmd_menu.sound, 'play_sfx'), \
                patch.object(controller.cmd_menu.sound, 'stop_sfx'), \
                patch.object(controller.cmd_menu, 'wait_for_dialog_key'):
            self.game.drawer.fade_in_enemy(self.game.screen, 'Slime')
            controller.hero_attack(battle)
            controller.enemy_move(battle)
            player_hit_shake(self.game.screen, self.game.game_state.config)
            fade(fade_out=True, screen=self.game.screen, config=self.game.game_state.config)
        outcome = (battle.enemy.hp, player.current_hp, random.random())
        self.game.cmd_menu.dialog_buffer.clear()
        return self.clock.now - start, outcome

    def test_a_battle_turn_takes_one_nth_of_the_time_and_comes_out_the_same(self):
        normal_time, normal_outcome = self.battle_turn(1)
        self.assertGreater(normal_time, 1000)  # sanity check: the effects and messages really waited
        for speed in (2, 3, 4):
            with self.subTest(speed=speed):
                elapsed, outcome = self.battle_turn(speed)
                self.assertAlmostEqual(normal_time / speed, elapsed, delta=normal_time / speed * 0.1)
                self.assertEqual(normal_outcome, outcome)  # damage and RNG draws don't depend on the speed
