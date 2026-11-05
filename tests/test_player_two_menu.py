"""Player 2's command window on the map (src/player_two_menu.py): player 2's A opens the second hero's ITEM, SPELL and
STATUS, on player 2's joypad."""
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import K_KP0, K_KP2, K_k, KEYDOWN
from pygame.event import Event

from src.config.test_config import test_config
from src.controls import PLAYER_ONE, PLAYER_TWO, input_player, reset_controls
from src.map_hotkeys import MAP_REQUESTS
from src.party import new_hero
from src.player_two_menu import COMMANDS, open_player_two_menu
from tests import helpers


def key(pressed_key):
    return Event(KEYDOWN, key=pressed_key, mod=0)


class PlayerTwoMenuTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        reset_controls()
        self.addCleanup(reset_controls)
        self.addCleanup(patch.stopall)
        self.game = helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True})
        self.game.game_state.is_initial_dialog = False
        self.leader = self.game.player
        self.leader.name = 'Ann'
        self.companion = self.game.companion = new_hero(self.game, 'Gwen')
        patch.object(self.game.cmd_menu, 'play_menu_button_sound').start()


class TestTheKey(PlayerTwoMenuTestCase):

    def test_player_2s_a_opens_it(self):
        with patch.object(self.game.hotkeys, 'open_player_two_menu') as open_menu:
            self.game.handle_keypresses(key(K_KP0))
        open_menu.assert_called_once()
        self.assertFalse(self.game.player_two_menu_requested)

    def test_not_player_1s_a(self):
        with patch.object(self.game.hotkeys, 'open_player_two_menu') as open_menu, \
                patch.object(self.game.movement, 'resolve_pending_freezes'):
            self.game.handle_keypresses(key(K_k))
        open_menu.assert_not_called()

    def test_not_without_a_second_hero(self):
        self.game.companion = None
        with patch.object(self.game.hotkeys, 'open_player_two_menu') as open_menu:
            self.game.handle_keypresses(key(K_KP0))
        open_menu.assert_not_called()

    def test_the_play_time_counts(self):
        request = next(map_request for map_request in MAP_REQUESTS if map_request.flag == 'player_two_menu_requested')
        self.assertTrue(request.play)


class TestTheWindow(PlayerTwoMenuTestCase):

    def choose(self, entry, accepted=True):
        seen = []

        def record(*args):
            seen.append((self.game.player.name, input_player()))
        cmd_menu = self.game.cmd_menu
        with patch('src.player_two_menu.run_selection') as selection, \
                patch.object(cmd_menu, 'use_an_item', side_effect=record) as item, \
                patch.object(cmd_menu, 'cast_a_spell', side_effect=record) as spell, \
                patch.object(cmd_menu, 'show_status_of', side_effect=record) as status:
            selection.return_value.entry = entry
            selection.return_value.accepted = accepted
            open_player_two_menu(self.game)
        self.assertIs(self.leader, self.game.player)
        self.assertEqual(PLAYER_ONE, input_player())
        return seen, item, spell, status

    def test_item_spell_and_status_as_the_second_hero_on_player_2s_joypad(self):
        for entry, name in enumerate(COMMANDS):
            with self.subTest(command=name):
                seen, item, spell, status = self.choose(entry)
                self.assertEqual([('Gwen', PLAYER_TWO)], seen)
                self.assertEqual([name == 'ITEM', name == 'SPELL', name == 'STATUS'],
                                 [item.called, spell.called, status.called])
        status.assert_called_once_with([self.companion])

    def test_b_closes_it(self):
        seen, *_ = self.choose(0, accepted=False)
        self.assertEqual([], seen)

    def test_nothing_without_a_second_hero(self):
        self.game.companion = None
        with patch('src.player_two_menu.run_selection') as selection:
            open_player_two_menu(self.game)
        selection.assert_not_called()

    def test_player_2s_keys_move_and_choose(self):
        cmd_menu = self.game.cmd_menu
        presses = [[key(K_k)], [key(K_KP2)], [key(K_KP0)]] + [[]] * 40  # player 1's A does nothing here
        with patch('src.selection.frame_events', side_effect=presses), patch('src.selection.next_frame'), \
                patch.object(cmd_menu, 'cast_a_spell') as spell, patch.object(cmd_menu, 'use_an_item') as item:
            open_player_two_menu(self.game)
        spell.assert_called_once()
        item.assert_not_called()
