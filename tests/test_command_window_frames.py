"""
The COMMAND window, opened with K (the A button) and drawn through real game frames, the way Game.main runs them.

The K press that opens the window must not also choose an entry: since K chooses in the window, passing that same
press on to it ran TALK at once, before the window was drawn, so it stayed black behind the dialog. The window now
reads the joypad like the NES (WndDoSelect, src/command_window.py): the press that opened it is ignored until it has
been let go.
"""
from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock, patch

import pygame
from pygame import KEYDOWN, KEYUP, K_k

from src.color import LOW_HP_RED, WHITE
from src.config.test_config import test_config
from src.game import Game
from src.menu import CommandMenu
from src.waiting import NES_FPS
from src.windows import COMMAND_TITLE_TILE_COLUMN, COMMAND_WINDOW

# The window's tiles (column, row from its top left corner) that must be drawn: the border, the title in the top
# border and the first and last entry of each column (CmdNonCmbtDat: entries at tile columns 2 and 10, rows 2 to 8)
BORDER_TILES = [(0, 0), (0, 4), (15, 4), (7, 9)]
TITLE_TILES = [(COMMAND_TITLE_TILE_COLUMN + i, 0) for i in range(len('COMMAND'))]
ENTRY_TILES = [(2, 2), (3, 2), (10, 2), (11, 2), (2, 8), (3, 8), (10, 8), (11, 8)]


class TestCommandWindowFrames(TestCase):

    def setUp(self):
        pygame.init()
        # Other tests turn RENDER_TEXT off in the shared test_config; the title is drawn text
        config = dict(test_config, NO_BLIT=False, NO_WAIT=True, RENDER_TEXT=True)
        # A chosen TALK would wait for a key in its dialog; record it instead
        self.talk = MagicMock()
        talk = patch.object(CommandMenu, 'talk', self.talk)
        talk.start()
        self.addCleanup(talk.stop)
        with patch('src.game.SCALED', 0):
            self.game = Game(config)
        # One NES frame per pass of the main loop, for the window's cursor and joypad reading
        self.frame_number = 0
        clock = patch('src.cursor.get_ticks', side_effect=lambda: -(-self.frame_number * 1000 // NES_FPS))
        clock.start()
        self.addCleanup(clock.stop)
        self.tile_size = config['TILE_SIZE']
        self.nes_tile = self.tile_size // 2

    def tearDown(self):
        pygame.event.clear()

    def frame(self) -> None:
        """One iteration of Game.main."""
        self.frame_number += 1
        game = self.game
        game.get_events()
        game.drawer.draw_all(game.screen, game.loop_count, game.big_map, game.current_map, game.player,
                             game.cmd_menu, game.foreground_rects, game.movement.sprites_animate, game.camera,
                             game.initial_dialog_enabled, game.events, game.skip_text,
                             game.story_flags.left_throne_room, game.game_state, game.color)
        pygame.display.flip()
        game.loop_count += 1

    def press_k(self) -> None:
        pygame.event.post(pygame.event.Event(KEYDOWN, key=K_k, mod=0, unicode='k', scancode=0))
        self.frame()
        pygame.event.post(pygame.event.Event(KEYUP, key=K_k, mod=0, unicode='k', scancode=0))

    def tile_has_color(self, column: int, row: int, color) -> bool:
        x = COMMAND_WINDOW.x * self.tile_size + column * self.nes_tile
        y = COMMAND_WINDOW.y * self.tile_size + row * self.nes_tile
        screen = self.game.screen
        return any(all(abs(a - b) <= 2 for a, b in zip(screen.get_at((x + i, y + j))[:3], color))
                   for i in range(self.nes_tile) for j in range(self.nes_tile))

    def assert_command_window_drawn(self, color) -> None:
        for name, tiles in (('border', BORDER_TILES), ('title', TITLE_TILES), ('entries', ENTRY_TILES)):
            for column, row in tiles:
                with self.subTest(part=name, column=column, row=row):
                    self.assertTrue(self.tile_has_color(column, row, color),
                                    f'COMMAND window {name} tile ({column}, {row}) has no {color} pixels')

    def open_command_window(self) -> None:
        for _ in range(3):
            self.frame()
        # Everyone is already on a tile, between two NPC turns (#289), so the window opens on the very frame K is
        # pressed (resolve_pending_freezes)
        with patch.object(self.game.movement, 'everyone_on_a_tile', return_value=True), \
                patch.object(type(self.game.movement.npc_schedule), 'between_turns', new_callable=PropertyMock,
                             return_value=True):
            self.press_k()
            self.assertTrue(self.game.cmd_menu.menu.is_enabled())
            for _ in range(3):
                self.frame()

    def check_opens_drawn(self, color) -> None:
        self.open_command_window()
        self.assertEqual(color, self.game.color)
        self.talk.assert_not_called()
        self.assert_command_window_drawn(color)
        # A new K press, once the window is up, still chooses (here TALK)
        self.frame()
        self.press_k()
        self.talk.assert_called_once()

    def test_command_window_is_drawn_when_opened_with_k(self):
        self.check_opens_drawn(WHITE)

    def test_command_window_is_drawn_when_opened_with_k_at_low_hp(self):
        self.game.player.current_hp = 1
        self.game.load_window_palette()
        self.check_opens_drawn(LOW_HP_RED)
