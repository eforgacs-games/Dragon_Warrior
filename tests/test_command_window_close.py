"""Closing the COMMAND window leaves the rest of the screen where it was (the screen "jumped" as the window closed).

NES RemoveWindow (Bank00, $A7A2) redraws only the map blocks under a closing window, at their offsets from the hero
(StartSignedXPos), so they line up with the map around them and nothing else on the screen moves. Here every frame
drawn while the window closes must match, outside the window, the last frame drawn while it was open.
"""
from collections import defaultdict
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame
from pygame import K_DOWN, K_j, K_k

from src.config.test_config import test_config
from src.game import Game
from src.waiting import NES_FPS
from src.windows import COMMAND_WINDOW, POPUP_WINDOW
from tests.helpers import new_game


class StopMainLoop(Exception):
    pass


def keydown(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=pygame.KMOD_NONE, unicode='')


class TestCommandWindowClose(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = False  # draw for real: the frames are what's being tested
        self.addCleanup(test_config.__setitem__, 'NO_BLIT', True)
        self.game = new_game()
        self.game.game_state.is_initial_dialog = False
        self.game.handle_battles = MagicMock()  # type: ignore[method-assign]
        pygame.event.clear()

    def run_and_record(self, walk_loops: int):
        """Walk down for walk_loops passes of the main loop, then open the COMMAND window (A) and close it (B).
        Return the frames shown (every display.flip and display.update) during the last pass with the window open and
        during the pass that closes it."""
        game = self.game
        open_loop = walk_loops + 30  # the hero has long finished the step by then
        close_loop = open_loop + 5
        loop = 0
        frames: dict[str, list[pygame.Surface]] = {'open': [], 'closing': []}

        def record():
            if loop == close_loop - 1:
                frames['open'].append(game.screen.copy())
            elif loop == close_loop:
                frames['closing'].append(game.screen.copy())

        real_flip, real_update = pygame.display.flip, pygame.display.update

        def flip(*args, **kwargs):
            record()
            return real_flip(*args, **kwargs)

        def update(*args, **kwargs):
            record()
            return real_update(*args, **kwargs)

        def get_events():
            nonlocal loop
            loop += 1
            if loop > close_loop:
                raise StopMainLoop
            if loop == open_loop:
                pygame.event.post(keydown(K_k))
            elif loop == close_loop:
                self.assertTrue(game.cmd_menu.menu.is_enabled())
                pygame.event.post(keydown(K_j))
            held = defaultdict(int, {K_DOWN: 1} if loop <= walk_loops else {})
            with patch('src.game.key') as mock_key:
                mock_key.get_pressed.return_value = held
                Game.get_events(game)

        game.get_events = get_events  # type: ignore[method-assign]
        game.clock = MagicMock()  # don't wait for the frame rate
        # One NES frame per pass of the main loop, for the window's joypad reading (src/command_window.py)
        with patch('pygame.display.flip', flip), patch('pygame.display.update', update), \
                patch('src.cursor.get_ticks', side_effect=lambda: -(-loop * 1000 // NES_FPS)):
            try:
                game.main()
            except StopMainLoop:
                pass
        self.assertFalse(game.cmd_menu.menu.is_enabled())
        self.assertTrue(frames['open'])
        self.assertGreater(len(frames['closing']), 1, "the window closes over several frames (window_drop_up_effect)")
        return frames['open'][-1], frames['closing']

    def assert_nothing_outside_the_windows_moves(self, open_frame, closing_frames):
        tile_size = self.game.tile_size
        windows = [pygame.Rect(x * tile_size, y * tile_size, width * tile_size, height * tile_size)
                   for x, y, width, height in (COMMAND_WINDOW, POPUP_WINDOW)]
        # Every 4th pixel is plenty to catch the map drawn even 2 pixels off
        points = [(x, y) for x in range(0, open_frame.get_width(), 4) for y in range(0, open_frame.get_height(), 4)
                  if not any(window.collidepoint(x, y) for window in windows)]
        expected = [open_frame.get_at(point) for point in points]
        for number, frame in enumerate(closing_frames):
            moved = sum(frame.get_at(point) != pixel for point, pixel in zip(points, expected))
            self.assertEqual(0, moved, f"closing frame {number}: {moved} pixels outside the windows changed")

    def test_after_a_step(self):
        # Game.move used to give the menu the camera from before the step's last move: the map was drawn 2 pixels off
        self.game.load_checkpoint('swamp_cave')
        y = self.game.player.rect.y
        open_frame, closing_frames = self.run_and_record(walk_loops=3)
        self.assertEqual(y + self.game.tile_size, self.game.player.rect.y)
        self.assert_nothing_outside_the_windows_moves(open_frame, closing_frames)

    def test_after_a_map_change(self):
        # The menu used to keep the camera from when it was made: before a map change put the hero somewhere else
        self.game.load_checkpoint('swamp_cave')
        open_frame, closing_frames = self.run_and_record(walk_loops=0)
        self.assert_nothing_outside_the_windows_moves(open_frame, closing_frames)
