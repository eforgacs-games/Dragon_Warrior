from unittest import TestCase

import pygame

from src.color import BLACK, RED, WHITE
from src.config.test_config import test_config
from src.cursor import (CURSOR_TILE, IN_A, IN_DOWN, IN_START, IN_UP, BlinkingCursor,
                        SelectionButtons, cursor_visible_on_frame, draw_cursor_tile, first_button)
from src.directories import Directories
from src.waiting import NES_FPS
from tests.helpers import new_game


def ticks_at_frame(frame: int) -> int:
    """The first millisecond of an NES frame, counted from 0."""
    return -(-frame * 1000 // NES_FPS)


def tile_pixels(surface: pygame.Surface, x: int, y: int, nes_pixel: int = 1) -> tuple[str, ...]:
    """An 8x8 tile of surface as CURSOR_TILE strings: '#' for a lit pixel."""
    return tuple(''.join('#' if sum(surface.get_at((x + column * nes_pixel, y + row * nes_pixel))[:3]) > 300
                         else '.' for column in range(8)) for row in range(8))


class TestCursorBlink(TestCase):
    """NES UpdateCursorGFX: the arrow while FrameCounter AND #$1F < #$10, else a blank tile. WndInitSelect and
    WndUpdateCrsrPos set FrameCounter to 5."""

    def test_frame_counter_rule(self):
        self.assertEqual([True] * 16 + [False] * 16, [cursor_visible_on_frame(f) for f in range(32)])
        self.assertTrue(cursor_visible_on_frame(0x20))
        self.assertFalse(cursor_visible_on_frame(0xFF))

    def test_starts_visible_for_11_frames_then_16_off_and_16_on(self):
        cursor = BlinkingCursor(ticks=0)
        visible = [cursor.visible(ticks_at_frame(frame)) for frame in range(11 + 16 + 16 + 1)]
        self.assertEqual([True] * 11 + [False] * 16 + [True] * 16 + [False], visible)

    def test_frame_counter_starts_at_5(self):
        cursor = BlinkingCursor(ticks=1000)
        self.assertEqual(5, cursor.frame_counter(1000))
        self.assertEqual(6, cursor.frame_counter(1000 + ticks_at_frame(1)))
        # One byte, like the NES counter
        self.assertEqual((5 + 300) & 0xFF, cursor.frame_counter(1000 + ticks_at_frame(300)))

    def test_moving_restarts_the_blink_visible(self):
        cursor = BlinkingCursor(ticks=0)
        hidden_at = ticks_at_frame(20)
        self.assertFalse(cursor.visible(hidden_at))
        cursor.restart(hidden_at)
        self.assertTrue(cursor.visible(hidden_at))
        self.assertTrue(cursor.visible(hidden_at + ticks_at_frame(10)))
        self.assertFalse(cursor.visible(hidden_at + ticks_at_frame(11)))

    def test_chosen_entry_stays_on(self):
        # WndAPressed/WndBPressed: the arrow is drawn and nothing redraws it until the window opens again
        cursor = BlinkingCursor(ticks=0)
        cursor.hold()
        self.assertTrue(all(cursor.visible(ticks_at_frame(frame)) for frame in range(100)))
        reopened_at = ticks_at_frame(100)
        cursor.restart(reopened_at)
        self.assertFalse(cursor.visible(reopened_at + ticks_at_frame(11)))


class TestCursorTile(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_cursor_tile_is_the_nes_arrow(self):
        # TL_RIGHT_ARROW ($42), as it is in the NES screenshots: the battle command window with the cursor on FIGHT
        # differs from the one without a cursor only in tile (1, 2), by this tile
        directories = Directories(test_config)
        with_cursor = pygame.image.load(directories.BATTLE_MENU_FIGHT_PATH)
        without_cursor = pygame.image.load(directories.BATTLE_MENU_STATIC_PATH)
        self.assertEqual(CURSOR_TILE, tile_pixels(with_cursor, 8, 16))
        self.assertEqual(('.' * 8,) * 8, tile_pixels(without_cursor, 8, 16))
        # and so does every other screenshot with the cursor in it: YES of the YES/NO window
        self.assertEqual(CURSOR_TILE, tile_pixels(pygame.image.load(directories.CONFIRMATION_YES_BACKGROUND_PATH),
                                                  8, 16))

    def test_draws_the_tile_scaled(self):
        for scale in (1, 2, 3):
            with self.subTest(scale=scale):
                screen = pygame.Surface((40 * scale, 40 * scale))
                screen.fill(WHITE)
                rect = draw_cursor_tile(screen, 8 * scale, 16 * scale, scale, WHITE)
                self.assertEqual(pygame.Rect(8 * scale, 16 * scale, 8 * scale, 8 * scale), rect)
                self.assertEqual(CURSOR_TILE, tile_pixels(screen, 8 * scale, 16 * scale, scale))

    def test_hidden_is_a_blank_tile(self):
        screen = pygame.Surface((16, 16))
        draw_cursor_tile(screen, 0, 0, 1, WHITE)
        draw_cursor_tile(screen, 0, 0, 1, WHITE, visible=False)
        self.assertEqual(('.' * 8,) * 8, tile_pixels(screen, 0, 0))

    def test_drawn_in_the_window_color(self):
        # A background tile in palette 0: red at low HP like the rest of the window
        for color in (WHITE, RED):
            with self.subTest(color=color):
                screen = pygame.Surface((8, 8))
                draw_cursor_tile(screen, 0, 0, 1, color)
                colors = {tuple(screen.get_at((x, y)))[:3] for x in range(8) for y in range(8)}
                self.assertEqual({color, BLACK}, colors)


class TestCommandWindowCursor(TestCase):
    """The COMMAND window (CmdNonCmbtDat) draws the NES cursor in the tile before the selected entry."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        self.game = new_game()
        self.cmd_menu = self.game.cmd_menu

    def test_cursor_is_in_the_tile_before_the_selected_entry(self):
        from unittest.mock import patch
        config = self.game.game_state.config
        nes_tile = config['TILE_SIZE'] // 2
        scale = config['SCALE']
        self.cmd_menu.menu.enable()
        # TALK, STATUS, STAIRS, SEARCH at tile column 2, SPELL, ITEM, DOOR, TAKE at 10, on rows 2, 4, 6 and 8
        for entry, (column, row) in enumerate(((1, 2), (1, 4), (1, 6), (1, 8), (9, 2), (9, 4), (9, 6), (9, 8))):
            with self.subTest(entry=entry), patch.dict(config, NO_BLIT=False):
                self.cmd_menu.menu.selected = entry
                self.cmd_menu.draw_command_window()
                x, y = (6 * 2 + column) * nes_tile, (1 * 2 + row) * nes_tile
                self.assertEqual(CURSOR_TILE, tile_pixels(self.game.screen, x, y, scale))

    def test_opening_the_window_restarts_the_blink(self):
        self.cmd_menu.cursor.start_ticks -= 1000
        self.cmd_menu.menu.enable()
        self.assertTrue(self.cmd_menu.cursor.visible())
        self.assertLess(self.cmd_menu.cursor.frame_counter(), 0x10)

    def test_chosen_command_keeps_its_cursor_on(self):
        seen = []
        self.cmd_menu.cursor.start_ticks -= ticks_at_frame(20)  # in the "off" half of the blink
        self.assertFalse(self.cmd_menu.cursor.visible())
        self.cmd_menu.choose_command(lambda: seen.append(self.cmd_menu.cursor.visible()))
        self.assertEqual([True], seen)
        self.assertFalse(self.cmd_menu.cursor.held)


class TestSelectionButtons(TestCase):
    """Bank01 WndGetButtons: the joypad read once a frame, gated by WndBtnRetrig."""

    def setUp(self):
        self.cursor = BlinkingCursor(ticks=0)
        self.buttons = SelectionButtons(self.cursor)
        self.buttons.open(ticks=0)
        self.frame = 0

    def frames(self, count: int, held: int = 0) -> list[int]:
        """What the window reads on each of the next count frames."""
        presses = []
        for _ in range(count):
            self.frame += 1
            presses.append(self.buttons.read(held, ticks=ticks_at_frame(self.frame)))
        return presses

    def test_the_first_frame_after_opening_reads_nothing(self):
        # WndDoSelect sets JoypadBtns to IN_RIGHT, so the retrigger can't be cleared on the first frame
        self.assertEqual([0, IN_DOWN], self.frames(1) + self.frames(1, IN_DOWN))

    def test_a_button_held_as_the_window_opens_is_read_when_frame_counter_reaches_16(self):
        self.buttons.open(IN_DOWN, ticks=0)
        self.assertEqual([0] * 10 + [IN_DOWN], self.frames(11, IN_DOWN))

    def test_a_held_button_is_read_again_11_frames_after_a_move(self):
        self.frames(1)
        self.assertEqual([IN_DOWN], self.frames(1, IN_DOWN))
        self.buttons.handled(IN_DOWN)
        self.buttons.moved(ticks=ticks_at_frame(self.frame))  # FrameCounter = 5, then one frame not read
        self.assertEqual([0] * 10 + [IN_DOWN], self.frames(11, IN_DOWN))

    def test_a_held_button_that_did_nothing_is_read_every_16_frames(self):
        self.frames(1)
        self.frames(1, IN_UP)  # FrameCounter 7
        self.buttons.handled(IN_UP)  # on the top row: no move, so FrameCounter runs on
        self.assertEqual([0] * 8 + [IN_UP], self.frames(9, IN_UP))  # FrameCounter 16
        self.buttons.handled(IN_UP)
        self.assertEqual([0] * 15 + [IN_UP], self.frames(16, IN_UP))  # FrameCounter 32

    def test_letting_go_clears_the_retrigger(self):
        self.frames(1)
        self.frames(1, IN_DOWN)
        self.buttons.handled(IN_DOWN)
        self.assertEqual([0, IN_A], self.frames(1) + self.frames(1, IN_A))

    def test_a_tap_between_frames_is_read_on_the_next_frame(self):
        self.frames(1)
        self.assertEqual(0, self.buttons.read(0, taps=IN_DOWN, ticks=ticks_at_frame(self.frame)))  # same frame
        self.assertEqual([IN_DOWN], self.frames(1))

    def test_one_button_at_a_time_in_wnd_process_input_order(self):
        self.assertEqual(IN_A, first_button(IN_A | IN_UP | IN_DOWN))
        self.assertEqual(IN_UP, first_button(IN_UP | IN_DOWN))
        self.assertEqual(0, first_button(IN_START))  # SELECT and START are skipped
