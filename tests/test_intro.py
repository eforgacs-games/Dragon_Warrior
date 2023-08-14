import os
from unittest import TestCase
from unittest.mock import patch, MagicMock

from pygame import Rect, event, KEYDOWN, K_i

from src.config import prod_config
from src.game import Game
from src.intro import show_intro_banner, Intro

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


class TestIntro(TestCase):

    @patch('src.game.Game.set_screen')
    def setUp(self, mock_set_screen) -> None:
        prod_config['NO_WAIT'] = True
        prod_config['RENDER_TEXT'] = False
        prod_config['NO_BLIT'] = True
        with patch('src.game.SCALED'):
            self.game = Game(prod_config)
        self.intro = Intro(prod_config)

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
        with patch.object(event, 'get', return_value=[mocked_i]) as mock_method:
            self.intro.show_start_screen(self.game.screen, 0, self.game.clock, self.game.game_state.config)

    # def test_show_start_screen_quit(self):
    #     mocked_quit = MagicMock()
    #     mocked_quit.type = QUIT
    #     with patch.object(event, 'get', return_value=[mocked_quit]) as mock_method:
    #         self.intro.show_start_screen(self.game.screen, get_ticks(), self.game.clock)
