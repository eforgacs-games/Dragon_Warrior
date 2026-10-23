from unittest import TestCase
from unittest.mock import patch, MagicMock

import pygame
from pygame import Rect, event, KEYDOWN, K_i, QUIT

from src.config.test_config import test_config
from src.game import Game
from src.intro import show_intro_banner, Intro


class TestIntro(TestCase):

    @classmethod
    def setUpClass(cls):
        # set_screen is patched below, so set a video mode here; images can't be converted without one, and an
        # earlier test file may already have called pygame.quit()
        pygame.init()
        pygame.display.set_mode((800, 600))

    @patch('src.game.Game.set_screen')
    def setUp(self, mock_set_screen) -> None:
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.intro = Intro(test_config)

    def test_show_intro_banner(self):
        self.assertIsInstance(show_intro_banner(self.game.directories.INTRO_BANNER_PATH, self.game.screen, no_blit=True), Rect)

    @patch('src.intro.Intro.banner_sparkle')
    # @patch(pygame.time, )
    def test_repeated_sparkle(self, mock_banner_sparkle):
        self.intro.repeated_sparkle(self.game.screen, 0, False, 1)
        mock_banner_sparkle.assert_not_called()
        return_value = self.intro.repeated_sparkle(self.game.screen, 0, False, 5000)
        self.assertIsInstance(return_value, (int, float))
        mock_banner_sparkle.assert_called_once()

    # def test_banner_sparkle(self):
    #     banner_sparkle(True, self.game.screen)

    @patch('src.intro.Intro.banner_sparkle')
    def test_handle_all_sparkles(self, mock_banner_sparkle):
        start_time = 1
        self.assertFalse(self.intro.first_long_sparkle_done)
        self.assertFalse(self.intro.first_short_sparkle_done)
        self.assertFalse(self.intro.second_short_sparkle_done)
        # 32.04, 160.02, 192.0 frames_since_banner_launch
        with patch('src.calculation.get_ticks', side_effect=[535, 2668, 3201]):
            self.intro.handle_all_sparkles(start_time, self.game.screen)
            self.assertTrue(self.intro.first_long_sparkle_done)
            self.assertFalse(self.intro.first_short_sparkle_done)
            self.assertFalse(self.intro.second_short_sparkle_done)

            self.intro.handle_all_sparkles(start_time, self.game.screen)
            self.assertTrue(self.intro.first_long_sparkle_done)
            self.assertTrue(self.intro.first_short_sparkle_done)
            self.assertFalse(self.intro.second_short_sparkle_done)

            self.intro.handle_all_sparkles(start_time, self.game.screen)
            self.assertTrue(self.intro.first_long_sparkle_done)
            self.assertTrue(self.intro.first_short_sparkle_done)
            self.assertTrue(self.intro.second_short_sparkle_done)

    def test_draw_banner_text(self):
        self.intro.draw_banner_text(self.game.screen)

    def test_show_start_screen(self):
        mocked_i = MagicMock()
        mocked_i.type = KEYDOWN
        mocked_i.key = K_i
        with patch.object(event, 'get', return_value=[mocked_i]):
            self.intro.show_start_screen(self.game.screen, 0, self.game.clock, self.game.game_state.config)

    def test_closing_the_window_on_the_title_screens_quits_the_game(self):
        # They used to call pygame.quit() and carry on, so the next display update raised "video system not
        # initialized"
        config = self.game.game_state.config
        for screen_name, show_screen in (
                ('start screen', lambda: self.intro.show_start_screen(self.game.screen, 0, self.game.clock, config)),
                ('dragon banner', lambda: self.intro.show_intro_dragon_banner_with_text(self.game.screen,
                                                                                        self.game.clock, config))):
            with self.subTest(screen_name), patch.object(event, 'get', side_effect=[[event.Event(QUIT)]]), \
                    patch('src.waiting.pygame_quit') as pygame_quit, self.assertRaises(SystemExit):
                show_screen()
            pygame_quit.assert_called_once()
