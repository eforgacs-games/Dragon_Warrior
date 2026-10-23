"""Frames that used to flicker: the guards turning round right after the throne room faded in, and a closing dialog
window going black all at once before it shrank away."""
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import Rect

from src.config.test_config import test_config
from src.direction import Direction
from src.maps import Brecconary, map_lookup
from src.windows import DIALOG_WINDOW
from tests.helpers import new_game


class TransitionTestCase(TestCase):

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
        self.game = new_game()
        self.tile_size = self.game.config['TILE_SIZE']


class TestFadeInFrame(TransitionTestCase):

    def test_every_character_faces_its_way_in_the_frame_the_fade_in_starts_from(self):
        # The throne room's guards don't face down. draw_all draws the characters before animating them, so the
        # frame drawn before the fade showed their first image (facing down), and they turned round on the first frame
        # after it. Drawing the same frame again must change nothing.
        self.game = new_game({**test_config, 'INITIAL_DIALOG_ENABLED': True})
        game = self.game
        pictures = []

        def draw_again():
            game.drawer.draw_all(game.screen, game.loop_count, game.big_map, game.current_map, game.player,
                                 game.cmd_menu, game.foreground_rects, game.game_state.enable_animate, game.camera,
                                 game.initial_dialog_enabled, [], game.skip_text, game.story_flags.left_throne_room,
                                 game.game_state, game.color)

        def record_pictures(*_args, **_kwargs):
            pictures.append(pygame.image.tobytes(game.screen, 'RGB'))
            draw_again()
            pictures.append(pygame.image.tobytes(game.screen, 'RGB'))
        throne_room = map_lookup['TantegelThroneRoom'](game.config)
        with patch('src.map_manager.screen_fade', side_effect=record_pictures):
            game.map_mgr.change_map(throne_room, destination_coordinates=throne_room.initial_coordinates,
                                    fade_out_first=False)
        self.assertTrue(any(character_dict['character'].direction_value != Direction.DOWN.value
                            for character_dict in game.current_map.characters.values()))
        self.assertEqual(len(pictures), 2)
        self.assertTrue(pictures[0] == pictures[1], "the characters changed after the fade-in's first frame")


class TestWindowCloseFrames(TransitionTestCase):

    def test_closing_window_keeps_the_rows_not_yet_removed(self):
        # NES RemoveWindow puts the map back one row of blocks a frame, from the bottom up; the rows above still
        # show the window. This used to replace the whole window with a black box on the first frame.
        self.game.change_map(Brecconary(self.game.config), destination_coordinates=(29, 18),
                             direction=Direction.RIGHT.value)
        cmd_menu = self.game.cmd_menu
        cmd_menu.show_text_in_dialog_box("Welcome to the traveler's Inn.", skip_text=True, drop_up=False)
        window = Rect(*(value * self.tile_size for value in DIALOG_WINDOW))
        before = self.game.screen.subsurface(window).copy()
        frames = []
        real_update = pygame.display.update

        def record_update(*args, **kwargs):
            frames.append(self.game.screen.subsurface(window).copy())
            return real_update(*args, **kwargs)
        with patch('src.menu.display.update', side_effect=record_update):
            cmd_menu.window_drop_up_effect(*DIALOG_WINDOW)
        rows = DIALOG_WINDOW[3]

        def row_pixels(surface, row):
            return pygame.image.tobytes(surface.subsurface((0, row * self.tile_size, window.width, self.tile_size)),
                                        'RGB')

        def window_rows_left(frame):
            """How many rows, from the top, still show the window exactly as it was."""
            rows_left = 0
            while rows_left < rows and row_pixels(frame, rows_left) == row_pixels(before, rows_left):
                rows_left += 1
            return rows_left
        seen = []
        for frame in frames:
            rows_left = window_rows_left(frame)
            if not seen or seen[-1] != rows_left:
                seen.append(rows_left)
        # bottom row first, one row at a time; never a black window
        self.assertEqual(seen, list(range(rows - 1, -1, -1)))
