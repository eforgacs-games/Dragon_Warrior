import os
from unittest import TestCase
from unittest.mock import patch, MagicMock

from pygame import Rect, event, KEYDOWN, K_i
from pygame.time import get_ticks

from src.common import INTRO_BANNER_PATH, convert_to_frames_since_start_time, convert_to_milliseconds
from src.game import Game
from src.intro import show_intro_banner, repeated_sparkle, Intro, draw_banner_text

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ['SDL_AUDIODRIVER'] = 'dummy'


class TestIntro(TestCase):

    def setUp(self) -> None:
        self.game = Game()
        self.intro = Intro()

    def test_show_intro_banner(self):
        self.assertIsInstance(show_intro_banner(INTRO_BANNER_PATH, self.game.screen), Rect)

    def test_repeated_sparkle(self):
        start_time = get_ticks()
        while get_ticks() - start_time < convert_to_milliseconds(256):
            self.assertIsInstance(repeated_sparkle(self.game.screen, start_time, False), (int, float))

    # def test_banner_sparkle(self):
    #     banner_sparkle(True, self.game.screen)

    def test_handle_all_sparkles(self):
        start_time = get_ticks()
        self.assertFalse(self.intro.first_long_sparkle_done)
        while convert_to_frames_since_start_time(start_time) <= 193:
            self.intro.handle_all_sparkles(start_time, self.game.screen)
            if convert_to_frames_since_start_time(start_time) >= 33:
                self.assertTrue(self.intro.first_long_sparkle_done)
            if convert_to_frames_since_start_time(start_time) >= 161:
                self.assertTrue(self.intro.first_short_sparkle_done)
        self.assertTrue(self.intro.second_short_sparkle_done)

    def test_draw_banner_text(self):
        draw_banner_text(self.game.screen)

    def test_show_start_screen(self):
        mocked_i = MagicMock()
        mocked_i.type = KEYDOWN
        mocked_i.key = K_i
        with patch.object(event, 'get', return_value=[mocked_i]) as mock_method:
            self.intro.show_start_screen(self.game.screen, get_ticks(), self.game.clock)

    # def test_show_start_screen_quit(self):
    #     mocked_quit = MagicMock()
    #     mocked_quit.type = QUIT
    #     with patch.object(event, 'get', return_value=[mocked_quit]) as mock_method:
    #         self.intro.show_start_screen(self.game.screen, get_ticks(), self.game.clock)
