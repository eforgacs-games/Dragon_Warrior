import os
from unittest import TestCase

from pygame import Rect
from pygame.time import get_ticks

from src.common import INTRO_BANNER_PATH, convert_to_frames_since_start_time
from src.game import Game
from src.intro import show_intro_banner, banner_sparkle, repeated_sparkle, Intro

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ['SDL_AUDIODRIVER'] = 'dummy'


class TestIntro(TestCase):

    def setUp(self) -> None:
        self.game = Game()
        self.intro = Intro()

    def test_show_intro_banner(self):
        self.assertIsInstance(show_intro_banner(INTRO_BANNER_PATH, self.game.screen), Rect)

    def test_repeated_sparkle(self):
        self.assertIsInstance(repeated_sparkle(self.game.screen, get_ticks(), False), int)

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
