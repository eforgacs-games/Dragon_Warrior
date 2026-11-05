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


class TestNetworkPlay(FreeRoamTestCase):

    def test_player_2_sees_the_second_heros_half(self):
        from src.netplay import NetHost, player_two_view
        view = player_two_view(self.game)
        width, height = self.game.screen.get_size()
        self.assertEqual(pygame.Rect(width, 0, width, height), view)
        display_surface = pygame.display.get_surface()
        display_surface.fill((0, 0, 0))
        display_surface.fill((10, 20, 30), view)
        host = NetHost(scale=self.game.game_state.config['SCALE'], log=lambda message: None)
        host.view_of_player_two = lambda: player_two_view(self.game)
        host.capture(0.0)
        frame_width, frame_height, rgb = host._frame
        self.assertEqual((width // 2, height // 2), (frame_width, frame_height))
        self.assertEqual(bytes((10, 20, 30)), rgb[:3])

    def test_the_whole_game_without_free_roam(self):
        from src.netplay import player_two_view
        self.game.config['COOP'] = COOP_PARTY
        self.game.update_free_roam()
        self.assertIsNone(player_two_view(self.game))

    def test_player_2_hears_the_second_heros_play(self):
        from src.netplay import NetHost
        host = NetHost(scale=2, log=lambda message: None)
        host.heard_by_player_two = lambda: not self.game.free_roam_active or \
            self.game.current_session is not self.game.main_session
        host.client = object()
        host.audio('sfx', self.game.directories.menu_button_sfx, {})  # Ann's
        self.assertEqual([], host._audio)
        with use_session(self.gwens):
            host.audio('sfx', self.game.directories.menu_button_sfx, {})  # Gwen's
        self.assertEqual(1, len(host._audio))


class TestStatesWhileRoaming(FreeRoamTestCase):

    def test_no_save_states_or_rewind(self):
        from pygame import K_BACKSPACE, K_F1, KMOD_SHIFT
        self.game.config['SAVE_STATES'] = True
        self.game.config['REWIND'] = True
        with patch.object(self.game.rewind, 'start') as rewind:
            self.game.handle_keypresses(Event(KEYDOWN, key=K_F1, mod=KMOD_SHIFT))
            self.game.handle_keypresses(Event(KEYDOWN, key=K_BACKSPACE, mod=0))
        self.assertIsNone(self.game.state_request)
        rewind.assert_not_called()
class TestTheirLook(FreeRoamTestCase):

    def test_green_from_the_start(self):
        from src.follower import COMPANION_GREEN
        image = self.gwen.image
        colors = {tuple(image.get_at((x, y)))[:3] for x in range(image.get_width()) for y in range(image.get_height())}
        self.assertIn(COMPANION_GREEN, colors)


class TestSavingWhileRoaming(FreeRoamTestCase):

    def test_the_log_is_the_first_heros_whoever_is_at_the_king(self):
        import json
        import os
        import tempfile
        from src.maps import map_lookup
        with use_session(self.gwens), patch('src.map_manager.screen_fade'):
            self.game.map_mgr.change_map(map_lookup['Brecconary'](self.game.config), destination_coordinates=(23, 10))
        with tempfile.TemporaryDirectory() as save_dir, use_session(self.gwens):
            self.game.cmd_menu.directories.save_dir = save_dir
            self.ann.adventure_log = 2
            self.assertTrue(self.game.cmd_menu.save())
            with open(os.path.join(save_dir, 'save_slot_2.json')) as save_file:
                save = json.load(save_file)
        self.assertEqual('Ann', save['Name'])
        self.assertEqual('TantegelThroneRoom', save['CurrentMap'])  # where Ann is, not Gwen in Brecconary
        self.assertEqual('Gwen', save['Companion']['Name'])

    def test_the_autosave_is_the_first_heros(self):
        from src.autosave import Autosave
        autosave = self.game.autosave
        autosave.last_frame_at = 12345
        with use_session(self.gwens), patch.object(Autosave, 'write') as write:
            Autosave.frame(autosave)  # the real one (setUp patched the instance's)
        write.assert_not_called()
        self.assertEqual(12345, autosave.last_frame_at)  # not even counted: Gwen's frames aren't the autosave's

    def test_no_rewind_snapshots_while_roaming(self):
        self.game.config['REWIND'] = True
        self.assertFalse(self.game.rewind.enabled)


class TestFullscreen(FreeRoamTestCase):

    def test_both_halves_again(self):
        # F11 and every other change to the window make it again with set_screen (the dummy video driver can't make a
        # fullscreen window, so the window is made again as it is)
        width, height = self.game.screen.get_size()
        self.game.screen = self.game.set_screen(height, width)
        display_surface = pygame.display.get_surface()
        width, height = self.game.screen.get_size()
        self.assertEqual((width * 2, height), display_surface.get_size())
        self.assertIs(display_surface, self.game.screen.get_parent())
        with use_session(self.gwens):
            self.assertIs(display_surface, self.game.screen.get_parent())
            self.assertEqual((width, 0), self.game.screen.get_abs_offset())
            self.assertIs(self.game.screen, self.game.cmd_menu.screen)
