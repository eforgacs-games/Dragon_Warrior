"""Answered selection windows (YES/NO, BUY/SELL, shop inventories) are taken off the screen the way the NES does it:
WindowSequence (Bank01) calls RemoveWindow (Bank00), which puts back what the window covered, the open background
windows (pop-up, COMMAND, dialog) or else the map, and touches nothing else."""
import hashlib
import os
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame  # noqa: E402
from pygame import KEYDOWN, K_RETURN, Rect  # noqa: E402
from pygame.event import Event  # noqa: E402

from data.text.dialog import confirmation_prompt  # noqa: E402
from src.config.test_config import test_config  # noqa: E402
from src.direction import Direction  # noqa: E402
from src.game import Game  # noqa: E402
from src.maps import Brecconary  # noqa: E402
from src.windows import BUY_SELL_WINDOW, COMMAND_WINDOW, YES_NO_WINDOW  # noqa: E402


def image_digest(surface) -> str:
    """A short stand-in for a surface's pixels, so a failed comparison doesn't diff megabytes."""
    return hashlib.sha1(pygame.image.tobytes(surface, 'RGB')).hexdigest()


def accept() -> Event:
    return Event(KEYDOWN, key=K_RETURN, unicode='\r')


class TestWindowRemoval(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = True
        test_config['NO_BLIT'] = False
        self.addCleanup(test_config.__setitem__, 'NO_BLIT', True)
        self.addCleanup(test_config.__setitem__, 'RENDER_TEXT', False)
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.game.change_map(Brecconary(self.game.config), destination_coordinates=(29, 18),
                             direction=Direction.RIGHT.value)
        self.cmd_menu = self.game.cmd_menu
        self.tile_size = self.game.config['TILE_SIZE']
        # The A button: the pop-up and the COMMAND window open (NES ShowNCCmdWindow), then a dialog window
        self.draw_frame()
        self.game.drawer.display_hovering_stats = True
        self.cmd_menu.launch_signaled = True
        for _ in range(3):
            self.draw_frame()
        self.assertTrue(self.cmd_menu.menu.is_enabled())
        # TALK is chosen (CommandMenu.choose_command, WndAPressed): its arrow stays on while the dialog runs
        self.cmd_menu.cursor.hold()
        self.draw_frame()
        self.cmd_menu.show_text_in_dialog_box("Welcome to the traveler's Inn.", skip_text=True, drop_up=False)
        pygame.event.clear()

    def draw_frame(self):
        game = self.game
        game.drawer.draw_all(game.screen, game.loop_count, game.big_map, game.current_map, game.player, game.cmd_menu,
                             game.foreground_rects, game.sprites_animate, game.camera, game.initial_dialog_enabled, [],
                             game.skip_text, game.story_flags.left_throne_room, game.game_state, game.color)
        game.loop_count += 1

    def rect(self, window) -> Rect:
        return Rect(window[0] * self.tile_size, window[1] * self.tile_size, window[2] * self.tile_size,
                    window[3] * self.tile_size)

    def screen_bytes(self) -> str:
        return image_digest(self.game.screen)

    def assert_window_removed(self, before: str, window) -> None:
        """Everything is as it was before the window opened: what it covered is back, and nothing else changed."""
        self.assertEqual(self.screen_bytes(), before)
        self.assertTrue(self.rect(window).colliderect(self.rect(COMMAND_WINDOW)))  # it did cover the COMMAND window

    def test_confirmation_prompt(self):
        # the window is gone before the answer is acted on, and only its area is redrawn: the map and the COMMAND window
        yes_no = self.rect(YES_NO_WINDOW)
        before = image_digest(self.game.screen.subsurface(yes_no))
        answered = []
        with patch('data.text.dialog.get', side_effect=[[accept()]]), \
                patch.object(self.cmd_menu, 'show_line_in_dialog_box'):
            confirmation_prompt(self.cmd_menu, "Dost thou want a room?",
                                lambda: answered.append(image_digest(self.game.screen.subsurface(yes_no))),
                                lambda: None, self.game.config, show_arrow=True, color=self.game.color)
        self.assertEqual(answered, [before])

    def test_prompt_yes_no(self):
        before = self.screen_bytes()
        pygame.event.post(accept())
        self.assertTrue(self.cmd_menu.prompt_yes_no())
        self.assert_window_removed(before, YES_NO_WINDOW)

    def test_buy_sell_window(self):
        before = self.screen_bytes()
        pygame.event.post(accept())
        dialog_lookup = self.cmd_menu.dialog_lookup
        self.assertEqual(dialog_lookup.select_from_text_menu(["BUY", "SELL"], BUY_SELL_WINDOW), 0)
        self.assert_window_removed(before, BUY_SELL_WINDOW)

    def test_cancelled_window_is_removed_too(self):
        before = self.screen_bytes()
        pygame.event.post(Event(KEYDOWN, key=pygame.K_ESCAPE, unicode='\x1b'))
        dialog_lookup = self.cmd_menu.dialog_lookup
        self.assertIsNone(dialog_lookup.select_from_text_menu(["BUY", "SELL"], BUY_SELL_WINDOW))
        self.assert_window_removed(before, BUY_SELL_WINDOW)
