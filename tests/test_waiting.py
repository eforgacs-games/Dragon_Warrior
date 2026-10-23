from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import KEYDOWN, K_RETURN, QUIT
from pygame.event import Event

from src.config.test_config import test_config
from src.waiting import NES_FPS, check_for_quit, quit_if_requested, reset_game_speed, wait, wait_frames, wait_until
from tests.helpers import new_game


class TestWait(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((64, 64))

    def setUp(self):
        reset_game_speed()  # these waits are timed in real milliseconds, at normal speed
        pygame.event.clear()
        # A QUIT a wait only peeked at stays queued: don't leave it for the next test in this process (pytest-xdist
        # runs other files' tests after these)
        self.addCleanup(pygame.event.clear)
        quit_patch = patch('src.waiting.pygame_quit')
        self.pygame_quit = quit_patch.start()
        self.addCleanup(quit_patch.stop)

    def test_returns_after_the_given_time(self):
        start = pygame.time.get_ticks()
        wait(60)
        elapsed = pygame.time.get_ticks() - start
        self.assertGreaterEqual(elapsed, 60)
        self.assertLess(elapsed, 500)

    def test_wait_frames_converts_nes_frames(self):
        with patch('src.waiting.wait') as mock_wait:
            wait_frames(30, {'NO_WAIT': False})
        mock_wait.assert_called_once_with(30 * 1000 / NES_FPS, {'NO_WAIT': False})  # 499.2 ms

    def test_wait_until_waits_out_only_what_is_left(self):
        with patch('src.waiting.game_ticks', return_value=1000), patch('src.waiting.wait') as mock_wait:
            wait_until(1050, {'NO_WAIT': False})
            wait_until(900, {'NO_WAIT': False})  # already past: no waiting
        self.assertEqual([((50, {'NO_WAIT': False}),), ((0.0, {'NO_WAIT': False}),)],
                         [c[:1] for c in mock_wait.call_args_list])

    def test_no_wait_returns_at_once(self):
        with patch('src.waiting.time.wait') as mock_time_wait:
            start = pygame.time.get_ticks()
            wait(5000, {'NO_WAIT': True})
            wait_frames(300, {'NO_WAIT': True})
        mock_time_wait.assert_not_called()
        self.assertLess(pygame.time.get_ticks() - start, 100)

    def test_without_config_no_wait_is_ignored(self):
        # Waits that never checked NO_WAIT keep waiting when they're given no config
        with patch('src.waiting.time.wait') as mock_time_wait:
            wait(32)
        self.assertEqual(sum(c.args[0] for c in mock_time_wait.call_args_list), 32)

    def test_quit_during_wait_quits_the_game(self):
        pygame.event.post(Event(QUIT))
        with self.assertRaises(SystemExit):
            wait(5000)
        self.pygame_quit.assert_called_once()

    def test_other_events_stay_queued(self):
        pygame.event.post(Event(KEYDOWN, key=K_RETURN))
        wait(20)
        self.assertEqual([e.key for e in pygame.event.get(KEYDOWN)], [K_RETURN])

    def test_check_for_quit_without_quit_does_nothing(self):
        check_for_quit()
        self.pygame_quit.assert_not_called()

    def test_quit_if_requested(self):
        quit_if_requested(Event(KEYDOWN, key=K_RETURN))
        self.pygame_quit.assert_not_called()
        with self.assertRaises(SystemExit):
            quit_if_requested(Event(QUIT))
        self.pygame_quit.assert_called_once()


class TestQuitDuringGameWaits(TestCase):
    """Closing the window during one of the game's long waits closes the game."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()
        pygame.display.set_mode((800, 600))

    def setUp(self):
        config = {**test_config, 'NO_WAIT': False, 'RENDER_TEXT': False, 'NO_BLIT': True}
        self.game = new_game(config)
        self.game.player.name = "Edward"
        pygame.event.clear()
        self.addCleanup(pygame.event.clear)  # nor a QUIT these tests post
        patcher = patch('src.waiting.pygame_quit')
        patcher.start()
        self.addCleanup(patcher.stop)

    def post_quit(self):
        pygame.event.post(Event(QUIT))

    def test_quit_during_death_music(self):
        self.game.player.current_hp = 0
        self.post_quit()
        with patch.object(self.game, 'drawer'), patch.object(self.game, 'music_player'), \
                patch('src.game.display'), \
                patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text, \
                self.assertRaises(SystemExit):
            self.game.handle_death()
        show_text.assert_not_called()

    def test_quit_right_after_the_death_music_still_quits(self):
        # The window closed after the wait's last check for QUIT: the clear that drops the keys pressed during the
        # music used to drop it too
        self.game.player.current_hp = 0
        with patch.object(self.game, 'drawer'), \
                patch.object(self.game, 'music_player',
                             **{'play_until_end.side_effect': lambda *args: self.post_quit()}), \
                patch('src.game.display'), \
                patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text, \
                self.assertRaises(SystemExit):
            self.game.handle_death()
        show_text.assert_not_called()

    def test_quit_right_after_the_kings_opening_words_still_quits(self):
        drawer = self.game.drawer
        self.game.game_state.is_initial_dialog = True
        with patch.object(drawer, 'run_automatic_initial_dialog', side_effect=lambda *args: self.post_quit()), \
                self.assertRaises(SystemExit):
            drawer.handle_initial_dialog(True, self.game.cmd_menu, [], False, False)

    def test_quit_right_after_the_kings_words_after_death_still_quits(self):
        drawer = self.game.drawer
        self.game.game_state.is_post_death_dialog = True
        with patch.object(drawer, 'run_automatic_post_death_dialog', side_effect=lambda *args: self.post_quit()), \
                self.assertRaises(SystemExit):
            drawer.handle_post_death_dialog(self.game.game_state, self.game.cmd_menu, [], False)

    def test_keys_after_the_kings_words_are_still_dropped(self):
        drawer = self.game.drawer
        self.game.game_state.is_initial_dialog = True
        keydown = Event(KEYDOWN, key=K_RETURN)
        with patch.object(drawer, 'run_automatic_initial_dialog', side_effect=lambda *args: pygame.event.post(keydown)):
            drawer.handle_initial_dialog(True, self.game.cmd_menu, [], False, False)
        self.assertEqual([], pygame.event.get(KEYDOWN))

    def test_keys_pressed_during_death_music_are_dropped(self):
        self.game.player.current_hp = 0
        pygame.event.post(Event(KEYDOWN, key=K_RETURN))
        with patch.object(self.game, 'drawer'), patch.object(self.game, 'music_player') as music_player, \
                patch('src.game.display'), patch.object(self.game.cmd_menu, 'show_text_in_dialog_box'):
            self.game.handle_death()
        music_player.play_until_end.assert_called_once()  # the death music, played to the end
        self.assertEqual(pygame.event.get(KEYDOWN), [])

    def test_quit_during_gwaelins_love_jingle(self):
        dialog_lookup = self.game.cmd_menu.dialog_lookup
        self.post_quit()
        with patch.object(self.game.music_player, 'load_and_play_music') as load_and_play_music, \
                self.assertRaises(SystemExit):
            dialog_lookup.play_gwaelins_love_music()
        load_and_play_music.assert_not_called()  # quit while waiting for the clip to end (WaitForMusicEnd)

    def test_quit_while_gwaelin_embraces_the_hero(self):
        dialog_lookup = self.game.cmd_menu.dialog_lookup
        self.post_quit()
        with patch.object(self.game.cmd_menu, 'show_line_in_dialog_box'), \
                patch.object(self.game.music_player, 'load_and_play_music') as load_and_play_music, \
                self.assertRaises(SystemExit):
            dialog_lookup.embrace_princess_gwaelin()
        load_and_play_music.assert_not_called()  # quit during the Gwaelin's Love clip, before the map music

    def test_quit_during_credits(self):
        self.post_quit()
        with self.assertRaises(SystemExit):
            self.game.ending.wait_frames(160)

    def test_quit_during_inn_sleep(self):
        dialog_lookup = self.game.cmd_menu.dialog_lookup
        self.post_quit()
        with patch.object(self.game.cmd_menu, 'show_line_in_dialog_box'), \
                patch('data.text.dialog_lookup_table.screen_fade'), patch.object(dialog_lookup.sound, 'play_sound'), \
                self.assertRaises(SystemExit):
            dialog_lookup.inn_sleep(6)
