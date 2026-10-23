"""The field COMMAND window (CmdNonCmbtDat) reads the joypad like the NES selection windows (Bank01 WndDoSelect,
WndGetButtons, WndProcessInput; src/command_window.py), one NES frame at a time."""
from collections import defaultdict
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame
from pygame import KEYDOWN, K_1, K_2, K_DOWN, K_ESCAPE, K_LEFT, K_RETURN, K_RIGHT, K_UP, K_i, K_j, K_k

from src.command_window import WND_ABORT, CommandWindow, tapped_buttons
from src.config.test_config import test_config
from src.cursor import IN_A, IN_B, IN_DOWN, IN_LEFT, IN_RIGHT, IN_START, IN_UP
from src.menu import COMMAND_METHODS, CommandMenu
from src.waiting import NES_FPS, game_speed, set_game_speed
from src.windows import COMMAND_ENTRIES
from tests.helpers import new_game

TALK, STATUS, STAIRS, SEARCH, SPELL, ITEM, DOOR, TAKE = range(8)


def ticks_at_frame(frame: int) -> int:
    """The first millisecond of an NES frame, counted from 0."""
    return -(-frame * 1000 // NES_FPS)


def keydown(pressed_key: int) -> pygame.event.Event:
    return pygame.event.Event(KEYDOWN, key=pressed_key, mod=0, unicode='')


class TestCommandWindowInput(TestCase):
    """WndProcessInput on the 2 columns of 4 rows of CmdNonCmbtDat."""

    def setUp(self):
        self.window = CommandWindow()
        self.window.enable()

    def press(self, button: int):
        return self.window.process_input(button)

    def test_entries_are_numbered_like_wnd_calc_sel_result(self):
        # WndCol * 4 + WndRow: NCC_TALK $00 ... NCC_TAKE $07, column by column
        self.assertEqual(("TALK", "STATUS", "STAIRS", "SEARCH", "SPELL", "ITEM", "DOOR", "TAKE"), COMMAND_ENTRIES)
        self.assertEqual(tuple(entry.lower() for entry in COMMAND_ENTRIES), COMMAND_METHODS)

    def test_down_and_up_move_one_row_and_stop_at_the_edges(self):
        visited = [self.window.selected]
        for _ in range(4):
            self.press(IN_DOWN)
            visited.append(self.window.selected)
        self.assertEqual([TALK, STATUS, STAIRS, SEARCH, SEARCH], visited)  # no wrapping to TALK
        for _ in range(4):
            self.press(IN_UP)
        self.assertEqual(TALK, self.window.selected)  # WndUpPressed: nothing on the top row

    def test_left_and_right_move_between_columns_and_stop_at_the_edges(self):
        self.press(IN_DOWN)
        self.press(IN_RIGHT)
        self.assertEqual(ITEM, self.window.selected)  # same row
        self.press(IN_RIGHT)
        self.assertEqual(ITEM, self.window.selected)  # WndRightPressed: nothing in the last column
        self.press(IN_LEFT)
        self.assertEqual(STATUS, self.window.selected)
        self.press(IN_LEFT)
        self.assertEqual(STATUS, self.window.selected)  # WndDoLeftPressed: nothing in column 0

    def test_every_entry_can_be_reached(self):
        moves = (IN_DOWN, IN_DOWN, IN_DOWN, IN_RIGHT, IN_UP, IN_UP, IN_UP)
        visited = [self.window.selected]
        for move in moves:
            self.press(move)
            visited.append(self.window.selected)
        self.assertEqual([TALK, STATUS, STAIRS, SEARCH, TAKE, DOOR, ITEM, SPELL], visited)

    def test_a_chooses_the_selected_entry_and_holds_the_arrow(self):
        self.press(IN_DOWN)
        self.press(IN_RIGHT)
        self.assertEqual(ITEM, self.press(IN_A))
        self.assertTrue(self.window.cursor.held)

    def test_b_aborts(self):
        self.assertEqual(WND_ABORT, self.press(IN_B))
        self.assertTrue(self.window.cursor.held)  # WndBPressed: WndUpdateCrsrPos

    def test_one_button_at_a_time_in_wnd_process_input_order(self):
        self.assertEqual(TALK, self.press(IN_A | IN_DOWN))  # A before the D-pad
        self.assertEqual(WND_ABORT, self.press(IN_B | IN_DOWN))  # B too
        self.window.enable()
        self.press(IN_UP | IN_DOWN)  # up first: nothing on the top row, and down isn't looked at
        self.assertEqual(TALK, self.window.selected)
        self.assertIsNone(self.press(IN_START))  # START (and SELECT) are skipped

    def test_only_a_real_move_restarts_the_blink(self):
        with patch.object(self.window.buttons, 'moved') as moved:
            self.press(IN_UP)  # top row: no move
            self.press(IN_LEFT)
            moved.assert_not_called()
            self.press(IN_DOWN)
            moved.assert_called_once()

    def test_opening_starts_on_talk_with_the_cursor_visible(self):
        # WndInitSelect: WndCol = WndRow = 0 and FrameCounter = 5, whatever was chosen last time
        self.press(IN_DOWN)
        self.press(IN_A)
        self.window.enable()
        self.assertEqual(TALK, self.window.selected)
        self.assertFalse(self.window.cursor.held)
        self.assertTrue(self.window.cursor.visible())

    def test_keys(self):
        for pressed_key, button in ((K_k, IN_A), (K_RETURN, IN_A), (K_j, IN_B), (K_ESCAPE, IN_B), (K_UP, IN_UP),
                                    (K_DOWN, IN_DOWN), (K_LEFT, IN_LEFT), (K_RIGHT, IN_RIGHT), (K_i, 0), (K_1, 0)):
            with self.subTest(key=pygame.key.name(pressed_key)):
                self.assertEqual(button, tapped_buttons([keydown(pressed_key)]))


class CommandWindowFrames(TestCase):
    """The game, run one NES frame at a time the way Game.main runs it (get_events, then Drawer.draw_all), with a fake
    clock, the keyboard state from key.get_pressed and key presses posted to the pygame event queue."""

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
        test_config['NO_BLIT'] = True
        self.frame_number = 0
        self.held: defaultdict = defaultdict(int)
        patch('src.cursor.get_ticks', side_effect=lambda: ticks_at_frame(self.frame_number)).start()
        patch('pygame.key.get_pressed', side_effect=lambda: self.held).start()
        self.addCleanup(patch.stopall)
        # Record the commands instead of running them
        self.chosen: list[str] = []
        self.arrow_while_running: list[tuple[bool, int]] = []  # whether the arrow was held, on which entry
        for name in COMMAND_METHODS:
            patch.object(CommandMenu, name, autospec=True,
                         side_effect=lambda menu, name=name: self.record(menu, name)).start()
        self.game = new_game()
        self.game.game_state.is_initial_dialog = False
        self.cmd_menu = self.game.cmd_menu
        for blocking in ('window_drop_down_effect', 'window_drop_up_effect'):
            patch.object(self.cmd_menu, blocking).start()
        pygame.event.clear()

    def record(self, menu: CommandMenu, name: str) -> None:
        self.chosen.append(name)
        self.arrow_while_running.append((menu.cursor.held, menu.menu.selected))

    def frame(self, *held_keys: int, pressed: tuple[int, ...] | None = None) -> None:
        """One NES frame later, with held_keys down (and pressed: posted as key presses, held_keys by default)."""
        self.frame_number += 1
        self.held = defaultdict(int, {held_key: 1 for held_key in held_keys})
        for pressed_key in held_keys if pressed is None else pressed:
            pygame.event.post(keydown(pressed_key))
        game = self.game
        game.get_events()
        game.drawer.draw_all(game.screen, game.loop_count, game.big_map, game.current_map, game.player,
                             game.cmd_menu, game.foreground_rects, game.movement.sprites_animate, game.camera,
                             game.initial_dialog_enabled, game.events, game.skip_text,
                             game.story_flags.left_throne_room, game.game_state, game.color)
        game.loop_count += 1

    def frames(self, count: int, *held_keys: int) -> None:
        for _ in range(count):
            self.frame(*held_keys, pressed=())

    def tap(self, pressed_key: int) -> None:
        """Two frames with nothing held (so the window reads the next press), then the key pressed for a frame."""
        self.frames(2)
        self.frame(pressed_key)

    def open_window(self) -> None:
        """Press A on the map and let go: the window opens on that frame (everyone is on a tile)."""
        with patch.object(self.game.movement, 'everyone_on_a_tile', return_value=True):
            self.frame(K_k)
        self.assertTrue(self.cmd_menu.menu.is_enabled())


class TestCommandWindowFrames(CommandWindowFrames):

    def test_the_a_press_that_opens_the_window_does_not_choose(self):
        self.open_window()
        self.frames(20)
        self.assertEqual([], self.chosen)
        self.assertTrue(self.cmd_menu.menu.is_enabled())

    def test_a_held_from_opening_chooses_talk_when_the_retrigger_times_out(self):
        # WndDoSelect: WndBtnRetrig = IN_RIGHT; it is cleared when FrameCounter AND #$0F is 0, 11 frames after
        # WndInitSelect set it to 5, and the A still held is read then
        with patch.object(self.game.movement, 'everyone_on_a_tile', return_value=True):
            self.frame(K_k)
        self.frames(10, K_k)
        self.assertEqual([], self.chosen)
        self.frames(1, K_k)
        self.assertEqual(['talk'], self.chosen)

    def test_every_entry_runs_its_command(self):
        moves = {TALK: (), STATUS: (K_DOWN,), STAIRS: (K_DOWN, K_DOWN), SEARCH: (K_DOWN, K_DOWN, K_DOWN),
                 SPELL: (K_RIGHT,), ITEM: (K_RIGHT, K_DOWN), DOOR: (K_RIGHT, K_DOWN, K_DOWN),
                 TAKE: (K_DOWN, K_DOWN, K_DOWN, K_RIGHT)}
        for entry, keys in moves.items():
            with self.subTest(entry=COMMAND_ENTRIES[entry]):
                self.chosen.clear()
                self.open_window()
                for pressed_key in keys:
                    self.tap(pressed_key)
                self.assertEqual(entry, self.cmd_menu.menu.selected)
                self.tap(K_k)
                self.assertEqual([COMMAND_METHODS[entry]], self.chosen)
                self.game.unlaunch_menu(self.cmd_menu)

    def test_enter_chooses_too(self):
        self.open_window()
        self.tap(K_DOWN)
        self.tap(K_RETURN)
        self.assertEqual(['status'], self.chosen)

    def test_chosen_command_runs_with_its_arrow_held(self):
        self.open_window()
        self.tap(K_DOWN)
        self.tap(K_k)
        self.assertEqual([(True, STATUS)], self.arrow_while_running)
        # The window is still up here (the recorded command doesn't close it): it selects again, blinking
        self.assertFalse(self.cmd_menu.cursor.held)

    def test_b_closes_the_window(self):
        for close_key in (K_j, K_ESCAPE):
            with self.subTest(key=pygame.key.name(close_key)):
                self.open_window()
                self.assertTrue(self.game.movement.world_frozen)
                self.tap(close_key)
                self.assertFalse(self.cmd_menu.menu.is_enabled())
                self.assertFalse(self.cmd_menu.launch_signaled)
                self.assertFalse(self.game.movement.world_frozen)
                self.cmd_menu.window_drop_up_effect.assert_called()
                self.assertEqual([], self.chosen)

    def test_b_on_the_map_does_nothing(self):
        self.tap(K_j)
        self.assertFalse(self.cmd_menu.launch_signaled)
        self.cmd_menu.window_drop_up_effect.assert_not_called()

    def test_a_press_right_after_a_move_is_not_read(self):
        # The move's WndUpdateCrsrPos waits a frame, and the retrigger only clears on a frame that starts with no
        # button held: A pressed on the next frame after letting go of DOWN is lost, as on the NES
        self.open_window()
        self.tap(K_DOWN)
        self.frames(1)
        self.frame(K_k)
        self.frames(5)
        self.assertEqual([], self.chosen)
        self.assertEqual(STATUS, self.cmd_menu.menu.selected)

    def test_held_direction_repeats_11_frames_after_each_move(self):
        # WndUpdateCrsrPos sets FrameCounter to 5 on every move, and the retrigger times out when it reaches 16
        self.open_window()
        self.frames(2)
        self.frame(K_DOWN)
        self.assertEqual(STATUS, self.cmd_menu.menu.selected)
        for entry in (STAIRS, SEARCH):
            self.frames(10, K_DOWN)
            self.assertEqual(entry - 1, self.cmd_menu.menu.selected)
            self.frames(1, K_DOWN)
            self.assertEqual(entry, self.cmd_menu.menu.selected)
        # On the bottom row DOWN does nothing, so nothing restarts the blink: read every 16 frames, still no move
        self.frames(40, K_DOWN)
        self.assertEqual(SEARCH, self.cmd_menu.menu.selected)

    def test_the_blink_restarts_on_a_move(self):
        self.open_window()
        self.frames(13)
        self.assertFalse(self.cmd_menu.cursor.visible())  # FrameCounter 18: off
        self.frame(K_DOWN)
        self.assertTrue(self.cmd_menu.cursor.visible())
        self.assertEqual(5, self.cmd_menu.cursor.frame_counter())

    def test_speed_keys_and_start_are_ignored(self):
        self.open_window()
        try:
            for pressed_key in (K_2, K_i, K_1):
                self.tap(pressed_key)
            self.assertEqual(1, game_speed())
        finally:
            set_game_speed(1)
        self.assertEqual(TALK, self.cmd_menu.menu.selected)
        self.assertEqual([], self.chosen)
        self.assertTrue(self.cmd_menu.menu.is_enabled())
        self.assertFalse(self.game.paused)  # START doesn't pause while a window is up (CheckInputs)


class TestCommandWindowDrawing(CommandWindowFrames):

    def test_drawn_every_frame_with_the_blinking_cursor(self):
        with patch.object(self.cmd_menu, 'draw_command_window', wraps=self.cmd_menu.draw_command_window) as draw:
            self.open_window()
            self.frames(3)
        self.assertEqual(4, draw.call_count)

    def test_translated_window_draws_its_text(self):
        # The NES font has no Korean: the border is generated and the title and entries are drawn as text
        self.cmd_menu._ = lambda text: {'COMMAND': '작전', 'TALK': '대화'}.get(text, text)
        self.assertFalse(self.cmd_menu.command_window_in_nes_font())
        with patch('src.menu.draw_text') as draw_text, patch('src.menu.draw_window', return_value=MagicMock()) as \
                draw_window, patch.dict(self.game.game_state.config, NO_BLIT=False):
            self.cmd_menu.draw_command_window()
        from src.windows import COMMAND_BORDER_LAYOUT
        self.assertIs(COMMAND_BORDER_LAYOUT, draw_window.call_args.args[1])
        drawn = [c.args[0] for c in draw_text.call_args_list]
        self.assertEqual(['작전', '대화', 'STATUS', 'STAIRS', 'SEARCH', 'SPELL', 'ITEM', 'DOOR', 'TAKE'], drawn)
