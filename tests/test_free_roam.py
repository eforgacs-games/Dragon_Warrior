"""Free roam co-op (CO-OP on FREE ROAM, src/sessions.py, Game.start_free_roam): the heroes roam apart, each on their
half of the window, their own player's keys moving them, a fight for one while the other walks on."""
from collections import defaultdict
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import K_DOWN, K_KP0, K_KP6, K_KP8, KEYDOWN
from pygame.event import Event

from src.config.test_config import test_config
from src.game_options import COOP, COOP_FREE_ROAM, COOP_PARTY
from src.party import companion_of, free_roaming, heroes, new_hero
from src.sessions import use_session
from tests import helpers


class FreeRoamTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.addCleanup(patch.stopall)
        self.clock = helpers.fake_game_clock()
        self.game = helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True,
                                      'COOP': COOP_FREE_ROAM})
        self.game.game_state.is_initial_dialog = False
        self.ann = self.game.player
        self.ann.name = 'Ann'
        self.ann.gold = 120
        self.gwen = self.game.companion = new_hero(self.game, 'Gwen')
        patch.object(self.game.autosave, 'frame').start()
        self.held: dict[int, int] = defaultdict(int)
        movement_key = patch('src.movement.key').start()
        movement_key.get_pressed.return_value = self.held
        self.game.update_free_roam()
        self.addCleanup(self.stop_roaming)

    def stop_roaming(self):
        """Each hero's task ended with the test, not left waiting in its greenlet for the garbage collector."""
        if self.game.free_roam_active:
            self.game.stop_free_roam()

    def frames(self, count, events=()):
        for number in range(count):
            for current_event in (events if number == 0 else ()):
                pygame.event.post(current_event)
            self.game.free_roam_frame()
            self.clock.advance_frames(1)

    @property
    def gwens(self):
        return self.game.sessions[1]


class TestStartingAndStopping(FreeRoamTestCase):

    def test_two_screens_two_sessions(self):
        self.assertTrue(self.game.free_roam_active)
        self.assertEqual(2, len(self.game.sessions))
        width, height = self.game.screen.get_size()
        self.assertEqual((width * 2, height), pygame.display.get_surface().get_size())
        with use_session(self.gwens):
            self.assertIs(self.gwen, self.game.player)
            self.assertEqual((width, 0), self.game.screen.get_abs_offset())
            self.assertIs(self.game.current_map, self.game.main_session.current_map)  # where Ann is

    def test_the_gold_is_shared(self):
        self.assertEqual(120, self.gwen.gold)
        self.gwen.gold -= 20
        self.assertEqual(100, self.ann.gold)

    def test_each_session_is_one_hero(self):
        self.assertTrue(free_roaming(self.game))
        self.assertIsNone(companion_of(self.game))
        with use_session(self.gwens):
            self.assertEqual([self.gwen], heroes(self.game))
        self.assertEqual([self.ann], heroes(self.game))

    def test_party_again(self):
        self.game.config['COOP'] = COOP_PARTY
        self.game.update_free_roam()
        self.assertFalse(self.game.free_roam_active)
        self.assertEqual([self.game.main_session], self.game.sessions)
        self.assertEqual(self.game.screen.get_size(), pygame.display.get_surface().get_size())

    def test_not_without_a_second_hero(self):
        self.game.config['COOP'] = COOP_PARTY
        self.game.update_free_roam()
        self.game.companion = None
        self.game.config['COOP'] = COOP_FREE_ROAM
        self.game.update_free_roam()
        self.assertFalse(self.game.free_roam_active)

    def test_the_option(self):
        self.assertEqual(COOP_PARTY, COOP.default)
        self.assertIsNone(COOP.presets)


class TestStoppingEndsTheTasks(FreeRoamTestCase):

    def test_both_heroes_tasks_end_with_free_roam(self):
        self.frames(2)
        tasks = list(self.game.free_roam_tasks)
        self.game.stop_free_roam()
        self.assertTrue(all(task.done for task in tasks))


class TestEachPlayersKeys(FreeRoamTestCase):

    def test_each_hero_walks_their_own_way(self):
        ann, gwen = (self.ann.row, self.ann.column), (self.gwen.row, self.gwen.column)
        self.held.update({K_DOWN: 1, K_KP6: 1})  # player 1's down, player 2's right
        self.frames(40)
        self.assertEqual((ann[0] + 1, ann[1]), (self.ann.row, self.ann.column))
        self.assertEqual(gwen[0], self.gwen.row)
        self.assertGreater(self.gwen.column, gwen[1])

    def test_player_2s_a_opens_gwens_command_window(self):
        self.frames(1, events=[Event(KEYDOWN, key=K_KP0, mod=0)])
        with use_session(self.gwens):
            self.assertTrue(self.game.cmd_menu.launch_signaled or self.game.cmd_menu_requested)
        self.assertFalse(self.game.cmd_menu.launch_signaled or self.game.cmd_menu_requested)


class TestAFightForOne(FreeRoamTestCase):

    def test_ann_walks_on_while_gwen_fights(self):
        with use_session(self.gwens):
            self.game.battle_ctrl.queue_scripted_battle('Slime')
        fights = []
        with patch.object(type(self.game.battle_ctrl), 'fight_enemy', autospec=True,
                          side_effect=lambda controller, name: fights.append(controller.game.player.name) or
                          self.wait_in_the_fight()):
            ann_row = self.ann.row
            self.held.update({K_DOWN: 1})
            self.frames(40)
        self.assertEqual(['Gwen'], fights)
        self.assertGreater(self.ann.row, ann_row)  # Ann walked while Gwen's fight went on

    def wait_in_the_fight(self):
        from src.waiting import wait_frames
        self.assertFalse(self.game.free_roam_tasks[1].idle)
        # A switch back to PARTY waits for the fight to end
        self.game.config['COOP'] = COOP_PARTY
        self.game.update_free_roam()
        self.assertTrue(self.game.free_roam_active)
        self.game.config['COOP'] = COOP_FREE_ROAM
        wait_frames(30)


class TestPlayerTwosMenuInFreeRoam(FreeRoamTestCase):

    def test_not_the_party_window(self):
        with patch.object(self.game.hotkeys, 'open_player_two_menu') as party_window:
            self.frames(1, events=[Event(KEYDOWN, key=K_KP8, mod=0)])
        party_window.assert_not_called()


class TestTheirLook(FreeRoamTestCase):

    def test_green_from_the_start(self):
        from src.follower import COMPANION_GREEN
        image = self.gwen.image
        colors = {tuple(image.get_at((x, y)))[:3] for x in range(image.get_width()) for y in range(image.get_height())}
        self.assertIn(COMPANION_GREEN, colors)
