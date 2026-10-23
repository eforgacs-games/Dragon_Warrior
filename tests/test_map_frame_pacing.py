"""The map keeps pace with the game speed, and the dialog's down arrow blinks with it.

The map counts frames (a step is 16, as on the NES) while the dialogs, effects and blinking read the game clock
(src/waiting.py game_ticks). Game.run_due_frames runs the frames the game clock has gone through since the last draw,
so walking keeps up with everything else even when a draw takes longer than 1/(60 N) of a second.
"""
import os
from unittest.mock import MagicMock, patch

from src.cursor import TXT_WAIT_START_FRAME, DialogArrowBlink, dialog_arrow_visible_on_frame
from src.game import STEP_SYNC_FRAMES, Game
from src.menu import CommandMenu
from src.waiting import NES_FPS, FramePacer, set_game_speed
from tests.test_game_speed import GameSpeedTestCase

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

MAX_FRAMES_PER_DRAW = STEP_SYNC_FRAMES // 2


class TestDialogArrowBlink(GameSpeedTestCase):
    """Bank01 DoWait / TxtWaitAnim: FrameCounter is set to $10, then the arrow is on while FrameCounter AND $1F is $10
    or more: 16 frames on, 16 off, starting on. It used to toggle every 530 real ms (a USEREVENT timer), at any speed."""

    def blink(self) -> list[bool]:
        """Whether the arrow is on, every real millisecond for 2 real seconds of one wait."""
        arrow = DialogArrowBlink()
        states = []
        for _ in range(2000):
            states.append(arrow.visible())
            self.clock.now += 1
        return states

    @staticmethod
    def runs(states: list[bool]) -> list[tuple[bool, int]]:
        """(state, real ms) for each run of the same state, the last (cut off) one left out."""
        result: list[tuple[bool, int]] = []
        for state in states:
            if result and result[-1][0] == state:
                result[-1] = (state, result[-1][1] + 1)
            else:
                result.append((state, 1))
        return result[:-1]

    def test_16_frames_on_16_off_starting_on(self):
        runs = self.runs(self.blink())
        self.assertTrue(runs[0][0])
        for state, length in runs:
            self.assertAlmostEqual(16 * 1000 / NES_FPS, length, delta=1)

    def test_blink_period_scales_with_the_game_speed(self):
        for speed in (1, 2, 4, 8):
            with self.subTest(speed=speed):
                set_game_speed(speed)
                runs = self.runs(self.blink())
                self.assertTrue(runs[0][0])
                for _, length in runs:
                    self.assertAlmostEqual(16 * 1000 / NES_FPS / speed, length, delta=1)

    def test_on_and_off_frames(self):
        self.assertEqual([True] * 16 + [False] * 16 + [True],
                         [dialog_arrow_visible_on_frame(TXT_WAIT_START_FRAME + frame) for frame in range(33)])

    def test_each_wait_starts_with_the_arrow_on(self):
        set_game_speed(8)
        menu = MagicMock()
        menu.read_dialog_events = MagicMock(side_effect=[False] * 5 + [True])
        drawn = []
        menu.draw_dialog_arrow = drawn.append
        for _ in range(3):
            self.clock.now += 37  # the arrow of a wait that started earlier could be off by now
            menu.read_dialog_events.side_effect = [False] * 5 + [True]
            drawn.clear()
            with patch('src.menu.is_any_key_held', return_value=False), patch('pygame.event.clear'):
                CommandMenu.wait_for_dialog_key(menu, shows_arrow=True, skip_text=False, temp_text_start=None,
                                                disable_sound=True)
            self.assertTrue(drawn[0])


class TestMapFramePacing(GameSpeedTestCase):

    def setUp(self):
        super().setUp()
        self.game = MagicMock()
        self.game.frame_pacer = FramePacer(max_frames=MAX_FRAMES_PER_DRAW)
        self.frames_run = 0

        def map_frame():
            self.frames_run += 1

        self.game.map_frame.side_effect = map_frame

    def run_main_loop(self, real_ms: float, ms_per_draw: float) -> int:
        """Run the main loop for real_ms of real time, each pass (its frames and the draw) taking ms_per_draw. Returns
        the frames run on the map."""
        end = self.clock.now + real_ms
        self.frames_run = 0
        while self.clock.now < end:
            Game.run_due_frames(self.game)
            self.clock.now += ms_per_draw
        return self.frames_run

    def test_the_map_keeps_pace_with_the_game_speed_when_drawing_is_slow(self):
        # The bug: one frame per draw, so at 8x (480 frames a second, 2.08 ms each) a 3 ms draw made walking about 30%
        # slower than the dialogs, effects and blinking
        for speed in (1, 2, 4, 8):
            for ms_per_draw in (1, 3, 5, 12):
                with self.subTest(speed=speed, ms_per_draw=ms_per_draw):
                    set_game_speed(speed)
                    self.run_main_loop(100, ms_per_draw)  # settle
                    self.assertAlmostEqual(NES_FPS * speed, self.run_main_loop(1000, ms_per_draw), delta=speed + 1)

    def test_normal_speed_is_60_frames_a_second(self):
        # pygame's Clock.tick(60) waits 16 ms, not 16.67: one frame a pass ran the map at 62.5 frames a second
        self.run_main_loop(100, 16)
        self.assertAlmostEqual(NES_FPS, self.run_main_loop(1000, 16), delta=1)

    def test_every_frame_runs_when_drawing_keeps_up(self):
        set_game_speed(8)
        self.run_main_loop(100, 1)
        counts = []
        for _ in range(200):
            before = self.frames_run
            Game.run_due_frames(self.game)
            counts.append(self.frames_run - before)
            self.clock.now += 1
        self.assertLessEqual(max(counts), 1)  # 1 ms passes are faster than 480 frames a second: never two frames a pass

    def test_no_more_than_half_a_step_between_two_draws(self):
        set_game_speed(8)
        Game.run_due_frames(self.game)
        self.clock.now += 60  # 28.8 frames of game time, but drawing this slowly the game slows down instead
        self.frames_run = 0
        Game.run_due_frames(self.game)
        self.assertEqual(MAX_FRAMES_PER_DRAW, self.frames_run)

    def test_a_battle_or_dialog_inside_a_frame_is_not_made_up_for(self):
        set_game_speed(8)
        self.run_main_loop(100, 2)

        def battle():
            self.frames_run += 1
            if self.frames_run == 1:
                self.clock.now += 5000  # the battle's own loop

        self.game.map_frame.side_effect = battle
        self.clock.now += 6  # three frames due
        self.frames_run = 0
        Game.run_due_frames(self.game)
        self.assertEqual(1, self.frames_run)  # the frames after the battle wait for the next pass
        self.clock.now += 2
        Game.run_due_frames(self.game)
        self.assertEqual(2, self.frames_run)  # one frame, not the 2400 the battle took

    def test_a_map_change_ends_the_frames_before_the_draw(self):
        set_game_speed(8)
        self.run_main_loop(100, 2)

        def stairs():
            self.frames_run += 1
            self.game.current_map = MagicMock()

        self.game.map_frame.side_effect = stairs
        self.clock.now += 10
        self.frames_run = 0
        Game.run_due_frames(self.game)
        self.assertEqual(1, self.frames_run)

    def test_the_events_are_read_even_when_no_frame_is_due(self):
        set_game_speed(1)
        Game.run_due_frames(self.game)
        self.game.read_events.reset_mock()
        self.frames_run = 0
        Game.run_due_frames(self.game)  # no time has passed
        self.assertEqual(0, self.frames_run)
        self.game.read_events.assert_called_once()
