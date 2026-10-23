"""Frames that used to flicker: the guards turning round right after the throne room faded in, and a closing dialog
window going black all at once before it shrank away."""
from collections import defaultdict
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import KEYDOWN, K_k, Rect

from src.config.test_config import test_config
from src.direction import Direction
from src.maps import Brecconary, map_lookup
from src.menu import CommandMenu
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


class TestThroneRoomInputAfterFadeIn(TransitionTestCase):

    def test_a_button_held_as_the_throne_room_loads_waits_for_the_fade_in(self):
        # The press confirming BEGIN A NEW QUEST is still held (and queued) as the throne room loads. The frame the
        # fade-in starts from used to start King Lorik's speech: the screen cut from black to full brightness, then
        # the queued press could skip the first page's wait. NES StartAtThroneRoom fades in (PalFadeIn) before
        # FirstInputLoop reads the joypad.
        self.game = new_game({**test_config, 'INITIAL_DIALOG_ENABLED': True})
        game = self.game
        game.game_state.is_initial_dialog = True
        happened: list[str] = []
        real_flip = pygame.display.flip

        def flip(*args, **kwargs):
            lit = pygame.transform.average_color(game.screen)[:3] != (0, 0, 0)
            happened.append('lit frame' if lit else 'black frame')
            return real_flip(*args, **kwargs)

        def fade(fade_out, **_kwargs):
            happened.append('fade-out' if fade_out else 'fade-in')

        def dialog(*_args, **_kwargs):
            happened.append('dialog')

        held = defaultdict(int, {K_k: 1})
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(KEYDOWN, key=K_k, mod=0, unicode='k'))
        throne_room = map_lookup['TantegelThroneRoom'](game.config)
        with patch('pygame.display.flip', side_effect=flip), \
                patch('src.map_manager.screen_fade', side_effect=fade), \
                patch('pygame.key.get_pressed', return_value=held), \
                patch.object(CommandMenu, 'show_text_in_dialog_box', autospec=True, side_effect=dialog):
            game.map_mgr.change_map(throne_room, destination_coordinates=throne_room.initial_coordinates,
                                    fade_out_first=False)
            self.assertEqual(['black frame', 'fade-in'], happened)
            self.assertTrue(game.game_state.is_initial_dialog)
            # The press queued before the fade isn't read as a new one afterwards
            self.assertFalse(pygame.event.peek(KEYDOWN))
            # The first frame after the fade-in reads the button still held: the speech starts
            game.drawer.draw_all(game.screen, game.loop_count, game.big_map, game.current_map, game.player,
                                 game.cmd_menu, game.foreground_rects, game.game_state.enable_animate, game.camera,
                                 game.initial_dialog_enabled, [], game.skip_text, game.story_flags.left_throne_room,
                                 game.game_state, game.color)
        self.assertEqual(['black frame', 'fade-in', 'lit frame', 'dialog'], happened)


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
