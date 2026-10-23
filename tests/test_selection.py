"""src/selection.py: the selection loop every blocking window runs (WndDoSelect)."""
import time as real_time
from collections import defaultdict
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame
from pygame import K_1, K_3, K_DOWN, K_ESCAPE, K_LEFT, K_RETURN, K_UP, K_i, K_j, K_k, K_n, K_q, K_s, K_w, K_y, \
    KEYDOWN, KEYUP, QUIT
from pygame.event import Event

from src.cursor import IN_A, IN_B, IN_DOWN, IN_LEFT, IN_RIGHT, IN_UP
from src.selection import NO, YES, Answer, frame_events, key_buttons, run_selection, stop_at_edges, toggle
from src.waiting import NES_FPS, game_speed, reset_game_speed


def press(key: int) -> Event:
    return Event(KEYDOWN, key=key)


class SelectionTestCase(TestCase):
    """run_selection with a scripted event queue (one batch per pass) and a game clock that moves one NES frame per
    pass (next_frame), so the cursor's blink and the joypad reading see exact frames."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((64, 64))

    def setUp(self):
        reset_game_speed()
        self.addCleanup(reset_game_speed)
        self.clock = 0
        self.frames = 0
        self.held = defaultdict(int)
        self.draws: list[tuple[int, bool]] = []

        def next_frame(*_args, **_kwargs):
            self.frames += 1
            self.clock = -(-self.frames * 1000 // NES_FPS)
        patch('src.cursor.get_ticks', lambda: self.clock).start()
        patch('src.selection.wait_frames', side_effect=next_frame).start()
        patch('src.selection.key.get_pressed', side_effect=lambda: self.held).start()
        self.addCleanup(patch.stopall)

    def draw(self, index: int, visible: bool) -> None:
        self.draws.append((index, visible))

    def select(self, *batches, **kwargs) -> Answer:
        """Run the selection with each batch of events coming off the queue in turn (then empty batches)."""
        queue = [list(batch) for batch in batches]
        self.passes = 0

        def get(*_args, **_kwargs):
            self.passes += 1
            if self.passes > 1000:
                raise AssertionError("still selecting")
            return queue.pop(0) if queue else []
        kwargs.setdefault('move', stop_at_edges(3))
        with patch('src.selection.event.get', side_effect=get):
            return run_selection(self.draw, **kwargs)


class TestKeys(SelectionTestCase):

    def test_key_buttons(self):
        # A is accept_keys (Enter, I and K), B is reject_keys (Escape and J), and the D-pad
        for key, button in ((K_RETURN, IN_A), (K_k, IN_A), (K_i, IN_A), (K_j, IN_B), (K_ESCAPE, IN_B),
                            (K_UP, IN_UP), (K_w, IN_UP), (K_DOWN, IN_DOWN), (K_s, IN_DOWN), (K_LEFT, IN_LEFT),
                            (K_q, 0), (K_1, 0)):
            with self.subTest(key=pygame.key.name(key)):
                self.assertEqual(button, key_buttons(key))
        self.assertEqual(IN_RIGHT, key_buttons(pygame.K_d))

    def test_a_answers_with_the_entry_under_the_cursor(self):
        for key in (K_RETURN, K_k, K_i):
            with self.subTest(key=pygame.key.name(key)):
                self.assertEqual(Answer(IN_A, 0), self.select([press(key)]))
                self.assertTrue(self.select([press(key)]).accepted)

    def test_b_and_escape_answer_b(self):
        for key in (K_j, K_ESCAPE):
            with self.subTest(key=pygame.key.name(key)):
                answer = self.select([press(K_DOWN)], [press(key)])
                self.assertEqual(Answer(IN_B, 1), answer)
                self.assertFalse(answer.accepted)

    def test_other_keys_and_key_ups_do_nothing(self):
        self.assertEqual(Answer(IN_A, 0), self.select([press(K_q), Event(KEYUP, key=K_DOWN)], [press(K_RETURN)]))
        self.assertEqual(2, self.passes)

    def test_directions_stop_at_the_edges(self):
        self.assertEqual(2, self.select([press(K_DOWN)] * 5 + [press(K_RETURN)]).entry)
        self.assertEqual(0, self.select([press(K_DOWN), press(K_UP), press(K_w), press(K_RETURN)]).entry)
        self.assertEqual(0, self.select([press(K_LEFT), press(pygame.K_RIGHT), press(K_RETURN)]).entry)

    def test_every_press_of_a_batch_counts_until_one_answers(self):
        # down, then A at the new entry; the presses after the answer are dropped (#97: no second answer)
        self.assertEqual(Answer(IN_A, 1), self.select([press(K_DOWN), press(K_RETURN), press(K_DOWN)]))

    def test_toggle(self):
        self.assertEqual(1, toggle(0, IN_UP))
        self.assertEqual(0, toggle(1, IN_DOWN))
        self.assertEqual(1, toggle(1, IN_LEFT))
        self.assertEqual(NO, self.select([press(K_UP), press(K_RETURN)], move=toggle).entry)

    def test_hotkeys_answer_wherever_the_cursor_is(self):
        hotkeys = {K_y: Answer(IN_A, YES), K_n: Answer(IN_B, NO)}
        self.assertEqual(Answer(IN_A, YES), self.select([press(K_DOWN), press(K_y)], hotkeys=hotkeys))
        self.assertEqual(Answer(IN_B, NO), self.select([press(K_n)], hotkeys=hotkeys))
        # the arrow is drawn on the entry answered
        self.assertEqual((NO, True), self.draws[-1])

    def test_b_index(self):
        self.assertEqual(Answer(IN_B, NO), self.select([press(K_ESCAPE)], b_index=NO))
        self.assertEqual((NO, True), self.draws[-1])
        self.assertEqual(Answer(IN_A, YES), self.select([press(K_RETURN)], b_index=NO))

    def test_b_ignored_but_for_its_sound(self):
        sound = MagicMock()
        answer = self.select([press(K_ESCAPE)], [press(K_DOWN), press(K_RETURN)], answers=(IN_A,), sound=sound)
        self.assertEqual(Answer(IN_A, 1), answer)
        self.assertEqual(2, sound.call_count)

    def test_sound_buttons(self):
        sound = MagicMock()
        self.select([press(K_ESCAPE)], sound=sound, sound_buttons=(IN_A,))
        sound.assert_not_called()
        self.select([press(K_RETURN)], sound=sound, sound_buttons=(IN_A,))
        sound.assert_called_once()

    def test_the_sound_plays_after_the_last_draw(self):
        order = []
        with patch.object(self, 'draw', side_effect=lambda *args: order.append('draw')):
            self.select([press(K_RETURN)], sound=lambda: order.append('sound'))
        self.assertEqual(['draw', 'draw', 'sound'], order)

    def test_the_answer_holds_the_arrow_on(self):
        self.select([press(K_DOWN)], [press(K_RETURN)])
        self.assertEqual([(0, True), (1, True), (1, True)], self.draws)
        self.draws.clear()
        self.select([press(K_RETURN)], hold=())
        self.assertEqual([(0, True)], self.draws)

    def test_quit(self):
        with patch('src.waiting.quit_game', side_effect=SystemExit) as quit_game, self.assertRaises(SystemExit):
            self.select([press(K_DOWN), Event(QUIT)])
        quit_game.assert_called_once()

    def test_speed_keys_set_the_speed_and_are_no_key(self):
        self.assertEqual(Answer(IN_A, 0), self.select([press(K_3)], [press(K_RETURN)]))
        self.assertEqual(4, game_speed())

    def test_frame_events(self):
        events = [press(K_1), press(K_RETURN), Event(KEYUP, key=K_RETURN)]
        with patch('src.selection.event.get', return_value=events):
            self.assertEqual(events[1:], frame_events())
        self.assertEqual(1, game_speed())


class TestBlinkAndPacing(SelectionTestCase):

    def test_one_frame_per_pass(self):
        # WaitForNMI: every pass waits for the next frame before it reads the keys
        self.select(*([[]] * 40), [press(K_RETURN)])
        self.assertEqual(41, self.passes)
        self.assertEqual(41, self.frames)

    def test_draws_only_when_something_changed(self):
        # 11 frames on, 16 off, 16 on: the window is drawn when it opens and at each change, not on every pass
        self.select(*([[]] * 42), [press(K_RETURN)])
        self.assertEqual([(0, True), (0, False), (0, True), (0, True)], self.draws)

    def test_a_move_restarts_the_blink(self):
        self.select(*([[]] * 12), [press(K_DOWN)], [press(K_RETURN)])
        self.assertEqual([(0, True), (0, False), (1, True), (1, True)], self.draws)

    def test_a_move_that_goes_nowhere_does_not(self):
        self.select(*([[]] * 12), [press(K_UP)], [press(K_RETURN)])
        self.assertEqual([(0, True), (0, False), (0, True)], self.draws)

    def test_real_time_pacing(self):
        # The real clock, not the test's: at most one pass per frame, so the loop doesn't spin
        patch.stopall()
        reset_game_speed()
        passes = 0
        start = real_time.perf_counter()

        def get(*_args, **_kwargs):
            nonlocal passes
            passes += 1
            return [press(K_RETURN)] if real_time.perf_counter() - start >= 0.25 else []
        with patch('src.selection.event.get', side_effect=get):
            run_selection(lambda *_: None, move=toggle)
        elapsed = real_time.perf_counter() - start
        self.assertLessEqual(passes, elapsed * NES_FPS + 2)
        self.assertGreaterEqual(passes, 5)


class TestJoypad(SelectionTestCase):
    """joypad=True: the NES reading (src/cursor.py SelectionButtons)."""

    def test_a_tap(self):
        self.assertEqual(Answer(IN_A, 1), self.select([], [], [press(K_DOWN)], [], [], [], [press(K_RETURN)], joypad=True))

    def test_a_key_held_as_the_window_opens_is_ignored_until_let_go(self):
        self.held[K_RETURN] = 1
        queue = [[]] * 5

        def get(*_args, **_kwargs):
            if not queue:
                self.held[K_RETURN] = 0
                queue.extend([[], [press(K_ESCAPE)]])
            return queue.pop(0)
        with patch('src.selection.event.get', side_effect=get):
            self.assertEqual(Answer(IN_B, 0), run_selection(self.draw, joypad=True, move=toggle))

    def test_one_button_per_frame(self):
        # WndProcessInput: only the first of A, B, up, down, left, right
        self.assertEqual(Answer(IN_A, 0), self.select([], [], [press(K_DOWN), press(K_RETURN)], joypad=True))

    def test_speed_keys_and_quit(self):
        self.assertEqual(Answer(IN_A, 0), self.select([], [], [press(K_3)], [], [press(K_k)], joypad=True))
        self.assertEqual(4, game_speed())
        with patch('src.waiting.quit_game', side_effect=SystemExit), self.assertRaises(SystemExit):
            self.select([Event(QUIT)], joypad=True)
