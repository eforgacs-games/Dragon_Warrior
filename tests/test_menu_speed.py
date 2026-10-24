"""MENU SPEED (#440): the selection windows read their input on 1x timing whatever the game speed (src/waiting.py
menu_ticks), unless the option is FOLLOW GAME SPEED.

Every test here runs on a fake real clock (``pygame.time.get_ticks``, which both the game clock and the menu clock
read), not on a patched cursor clock, so the seam itself is what's tested: at 8x and 16x a held direction moves the
cursor, and a held A is read, on the same real frames as at 1x; with FOLLOW GAME SPEED, N times as soon.
"""
import math
from collections import defaultdict
from fractions import Fraction
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame
from pygame import KEYDOWN, K_DOWN, K_RETURN, K_e
from pygame.event import Event

from src.battle_controller import BattleController
from src.command_window import CommandWindow
from src.cursor import IN_A, IN_DOWN, BlinkingCursor
from src.selection import run_selection, stop_at_edges
from src.waiting import MENU_SPEED_FOLLOW, MENU_SPEED_NORMAL, NES_FPS, follow_menu_speed_option, game_speed, \
    game_ticks, menu_speed, menu_ticks, reset_game_speed, set_game_speed, set_virtual_joypad
from tests.test_battle_controller import make_battle, make_game

FIGHT, RUN = (0, 0), (1, 0)


class RealClock(TestCase):
    """A fake ``pygame.time.get_ticks``: ``self.real`` real NES frames (a Fraction) since tick 0, the first
    millisecond of the frame. ``wait`` (src/selection.py's wait_frames) moves it on as the real wait would: a number
    of game frames, each 1/N of a real frame at game speed N."""

    def setUp(self):
        pygame.init()
        pygame.event.clear()
        self.addCleanup(pygame.event.clear)
        reset_game_speed()
        self.addCleanup(reset_game_speed)
        self.config = {'MENU_SPEED': MENU_SPEED_NORMAL}
        follow_menu_speed_option(self.config)
        self.addCleanup(follow_menu_speed_option, None)
        self.real = Fraction(0)
        patch('src.waiting.time.get_ticks', side_effect=lambda: math.ceil(self.real * 1000 / Fraction(NES_FPS))).start()
        self.addCleanup(patch.stopall)

    def wait(self, frames=1, *_args, **_kwargs):
        self.real += Fraction(frames) / game_speed()

    def at_speed(self, speed: int, menu: str = MENU_SPEED_NORMAL) -> None:
        reset_game_speed()
        self.real = Fraction(0)
        self.config['MENU_SPEED'] = menu
        set_game_speed(speed)


class TestMenuClock(RealClock):

    def test_at_1x_it_is_the_game_clock(self):
        for menu in (MENU_SPEED_NORMAL, MENU_SPEED_FOLLOW):
            self.at_speed(1, menu)
            for _ in range(50):
                self.real += Fraction(1, 3)
                self.assertEqual(game_ticks(), menu_ticks())

    def test_normal_keeps_1x_time_at_every_speed(self):
        for speed in (2, 4, 8, 16):
            with self.subTest(speed=speed):
                self.at_speed(speed)
                start_game, start_menu = game_ticks(), menu_ticks()
                self.real += 60
                self.assertEqual(1, menu_speed())
                self.assertAlmostEqual(1000, menu_ticks() - start_menu, delta=1)
                self.assertAlmostEqual(1000 * speed, game_ticks() - start_game, delta=speed)

    def test_follow_game_speed_runs_at_the_game_speed(self):
        self.at_speed(8, MENU_SPEED_FOLLOW)
        start = menu_ticks()
        self.real += 60
        self.assertEqual(8, menu_speed())
        self.assertAlmostEqual(8000, menu_ticks() - start, delta=8)

    def test_it_never_jumps(self):
        # changing the game speed or the option only changes how fast it runs from then on
        self.at_speed(1)
        last = menu_ticks()
        for step, change in enumerate([lambda: set_game_speed(8), lambda: self.config.update(MENU_SPEED=MENU_SPEED_FOLLOW),
                                       lambda: set_game_speed(16), lambda: self.config.update(MENU_SPEED=MENU_SPEED_NORMAL),
                                       lambda: set_game_speed(2), lambda: self.config.update(MENU_SPEED=MENU_SPEED_FOLLOW),
                                       lambda: set_game_speed(1)]):
            self.real += 10
            before = menu_ticks()
            self.assertGreaterEqual(before, last)
            change()
            self.assertAlmostEqual(before, menu_ticks(), delta=1, msg=step)
            last = menu_ticks()

    def test_auto_grind_follows_the_game_speed(self):
        # a virtual joypad's presses are timed on the game clock, so the menus keep up with it
        self.at_speed(8)
        set_virtual_joypad(MagicMock())
        self.addCleanup(set_virtual_joypad, None)
        self.assertEqual(8, menu_speed())
        set_virtual_joypad(None)
        self.assertEqual(1, menu_speed())

    def test_without_the_option_the_menus_keep_1x(self):
        follow_menu_speed_option(None)
        self.at_speed(16)
        self.assertEqual(1, menu_speed())


class TestCommandWindow(RealClock):
    """The map COMMAND window, read once per pass of the map loop, which runs N passes per real frame at speed N."""

    def run_window(self, speed, menu=MENU_SPEED_NORMAL, held=0, opened_with=0, frames=60):
        """Open the window, then run the map loop for ``frames`` real frames with ``held`` down: the real frame of
        every move (the entry it moved to) and of the choice."""
        self.at_speed(speed, menu)
        window = CommandWindow()
        window.enable(opened_with)
        moves = []
        passes_per_frame = speed  # FrameClock: the map loop runs N times as often at game speed N
        with patch('src.command_window.held_buttons', side_effect=lambda: held):
            for _ in range(frames * passes_per_frame):
                self.real += Fraction(1, passes_per_frame)
                before = window.selected
                chosen = window.select([])
                if window.selected != before:
                    moves.append((self.real, window.selected))
                if chosen is not None:
                    moves.append((self.real, 'chosen'))
                    break
        return moves

    def test_a_held_direction_moves_at_the_1x_rate(self):
        normal = self.run_window(1, held=IN_DOWN)
        # held as the window opens, so read once the retrigger runs out (11 frames, WndDoSelect), then every 11 frames
        self.assertEqual([11, 22, 33], [frame for frame, _ in normal])
        for speed in (8, 16):
            with self.subTest(speed=speed):
                self.assertEqual(normal, self.run_window(speed, held=IN_DOWN))

    def test_a_held_a_is_not_read_again_early(self):
        # the A that opened the window, still held: ignored for 11 frames (WndBtnRetrig), at 1x and at 16x
        normal = self.run_window(1, held=IN_A, opened_with=IN_A)
        self.assertEqual([(11, 'chosen')], normal)
        for speed in (8, 16):
            with self.subTest(speed=speed):
                self.assertEqual(normal, self.run_window(speed, held=IN_A, opened_with=IN_A))

    def test_follow_game_speed_is_the_old_behaviour(self):
        normal = self.run_window(1, held=IN_DOWN)
        self.assertEqual([(frame / 8, entry) for frame, entry in normal],
                         self.run_window(8, MENU_SPEED_FOLLOW, held=IN_DOWN, frames=8))
        self.assertEqual([(Fraction(11, 16), 'chosen')],
                         self.run_window(16, MENU_SPEED_FOLLOW, held=IN_A, opened_with=IN_A, frames=2))

    def test_the_blink_keeps_1x(self):
        def blink(speed, menu=MENU_SPEED_NORMAL):
            self.at_speed(speed, menu)
            cursor = BlinkingCursor()
            shown = []
            for _ in range(64):
                self.real += 1
                shown.append(cursor.visible())
            return shown
        normal = blink(1)
        self.assertEqual([True] * 10 + [False] * 16 + [True] * 16, normal[:42])
        self.assertEqual(normal, blink(16))
        self.assertNotEqual(normal, blink(16, MENU_SPEED_FOLLOW))


class TestSelectionWindow(RealClock):
    """A blocking selection window (src/selection.py run_selection: SPELL, ITEM, the shops, YES/NO, the title and
    options screens), read like the NES (joypad=True) or key press by key press."""

    def select(self, speed, menu=MENU_SPEED_NORMAL, held=(), passes=60, joypad=True):
        """The real frame of each draw of the window (the entry, and whether the arrow shows); RETURN is tapped after
        ``passes`` passes."""
        self.at_speed(speed, menu)
        held_keys = defaultdict(int, {held_key: 1 for held_key in held})
        draws = []
        count = [0]

        def get(*_args, **_kwargs):
            count[0] += 1
            if count[0] == passes:
                held_keys.clear()
            return [Event(KEYDOWN, key=K_RETURN)] if count[0] == passes + 2 else []
        with patch('src.selection.wait_frames', side_effect=self.wait), \
                patch('src.selection.event.get', side_effect=get), \
                patch('src.selection.key.get_pressed', side_effect=lambda: held_keys):
            run_selection(lambda index, visible: draws.append((self.real, index, visible)), move=stop_at_edges(8),
                          joypad=joypad)
        return draws

    def test_a_held_direction_moves_at_the_1x_rate(self):
        normal = self.select(1, held=(K_DOWN,))
        moves = [(frame, index) for frame, index, _ in normal if index]
        self.assertEqual([(11, 1), (22, 2), (33, 3), (44, 4), (55, 5)], moves[:5])
        for speed in (8, 16):
            with self.subTest(speed=speed):
                self.assertEqual(normal, self.select(speed, held=(K_DOWN,)))

    def test_a_held_a_is_not_read_again_early(self):
        # RETURN held as the window opens (the press that opened it) is read after 11 frames, at 1x and at 16x
        def chosen_at(speed, menu=MENU_SPEED_NORMAL):
            return self.select(speed, menu, held=(K_RETURN,), passes=1000)[-1][0]
        self.assertEqual(11, chosen_at(1))
        self.assertEqual(11, chosen_at(8))
        self.assertEqual(11, chosen_at(16))
        self.assertEqual(Fraction(11, 16), chosen_at(16, MENU_SPEED_FOLLOW))

    def test_one_pass_a_real_frame(self):
        for speed in (1, 8, 16):
            with self.subTest(speed=speed):
                self.assertEqual(62, self.select(speed, passes=60, joypad=False)[-1][0])
        self.assertEqual(Fraction(62, 16), self.select(16, MENU_SPEED_FOLLOW, passes=60, joypad=False)[-1][0])

    def test_the_blink_keeps_1x(self):
        normal = self.select(1, joypad=False)
        self.assertEqual([(0, 0, True), (11, 0, False), (27, 0, True), (43, 0, False), (59, 0, True)], normal[:5])
        self.assertEqual(normal, self.select(8, joypad=False))
        self.assertEqual([(frame / 8, index, visible) for frame, index, visible in normal],
                         self.select(8, MENU_SPEED_FOLLOW, joypad=False))


class TestBattleCommandWindow(RealClock):
    """The battle's command window, one pass of the fight loop per frame of menu time (src/selection.py next_frame)."""

    def setUp(self):
        super().setUp()
        self.game = make_game()
        patch('src.battle_controller.display').start()
        patch('src.battle_controller.time').start()
        patch('src.selection.wait_frames', side_effect=self.wait).start()
        patch('src.battle_controller.random.random', return_value=0.99).start()
        self.held = defaultdict(int)
        patch('src.battle_controller.key.get_pressed', side_effect=lambda: self.held).start()

    def run_window(self, speed, menu=MENU_SPEED_NORMAL, held=(), opened_with=(), frames=40):
        """The real frame of every move of the cursor (and where to), and of the command chosen."""
        self.at_speed(speed, menu)
        controller = BattleController(self.game)
        battle = make_battle()
        self.held = defaultdict(int, {held_key: 1 for held_key in opened_with})
        events = []
        with patch.object(controller, 'fight') as fight, patch.object(controller, 'enemy_move', return_value=False):
            controller.handle_battle_prompts(False, battle)  # opens the window
            self.held = defaultdict(int, {held_key: 1 for held_key in held})
            while self.real < frames and not fight.called:
                before = (controller.battle_menu_row, controller.battle_menu_column)
                controller.handle_battle_prompts(False, battle)
                after = (controller.battle_menu_row, controller.battle_menu_column)
                if after != before:
                    events.append((self.real, after))
            if fight.called:
                events.append((self.real, 'FIGHT'))
        return events

    def test_a_held_direction_moves_at_the_1x_rate(self):
        normal = self.run_window(1, held=(K_DOWN,), opened_with=())
        self.assertEqual([(2, RUN)], normal)  # read on the first frame with nothing held as it opened
        for speed in (8, 16):
            with self.subTest(speed=speed):
                self.assertEqual(normal, self.run_window(speed, held=(K_DOWN,)))

    def test_a_held_a_is_not_read_again_early(self):
        normal = self.run_window(1, held=(K_RETURN,), opened_with=(K_RETURN,))
        self.assertEqual([(11, 'FIGHT')], normal)
        for speed in (8, 16):
            with self.subTest(speed=speed):
                self.assertEqual(normal, self.run_window(speed, held=(K_RETURN,), opened_with=(K_RETURN,)))
        self.assertEqual([(Fraction(11, 8), 'FIGHT')],
                         self.run_window(8, MENU_SPEED_FOLLOW, held=(K_RETURN,), opened_with=(K_RETURN,)))


class TestNameEntry(RealClock):
    """The name entry's alphabet window reads key presses (no held repeat), so what keeps 1x is its pacing and its
    cursor's blink."""

    def blink(self, speed, menu=MENU_SPEED_NORMAL):
        """The real frame of every draw of the alphabet window's cursor (shown or not); 'e' then RETURN end it."""
        from src.config.test_config import test_config
        from src.menu_functions import NameSelection
        self.at_speed(speed, menu)
        selection = NameSelection({**test_config, 'NO_BLIT': True})
        shown = []
        count = [0]

        def get(*_args, **_kwargs):
            count[0] += 1
            if count[0] == 50:
                return [Event(KEYDOWN, key=K_e, unicode='e', mod=0)]
            return [Event(KEYDOWN, key=K_RETURN, unicode='\r', mod=0)] if count[0] == 52 else []
        command_menu = MagicMock()
        with patch('src.selection.wait_frames', side_effect=self.wait), \
                patch('src.selection.event.get', side_effect=get), \
                patch.object(selection, 'draw', side_effect=lambda _screen, _entry, cursor_visible=True:
                             shown.append((self.real, cursor_visible))), \
                patch.object(selection.sound, 'play_sound'):
            self.assertEqual('E', selection.select_name(menu_ticks(), MagicMock(), command_menu).upper())
        return shown

    def test_the_blink_keeps_1x(self):
        normal = self.blink(1)
        self.assertEqual([(0, None), (0, None), (0, True), (11, False), (27, True), (43, False)], normal[:6])
        for speed in (8, 16):
            with self.subTest(speed=speed):
                self.assertEqual(normal, self.blink(speed))
        self.assertEqual([(frame / 16, visible) for frame, visible in normal], self.blink(16, MENU_SPEED_FOLLOW))
