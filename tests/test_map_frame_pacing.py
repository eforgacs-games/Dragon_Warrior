"""The map keeps pace with the game speed, and the dialog's down arrow blinks with it.

The map counts frames (a step is 16, as on the NES) while the dialogs, effects and blinking read the game clock
(src/waiting.py game_ticks). Game.run_due_frames runs the frames the game clock has gone through since the last draw,
so walking keeps up with everything else even when a draw takes longer than 1/(60 N) of a second.
"""
import os
from unittest.mock import MagicMock

from src.cursor import DIALOG_ARROW_BLINK_FRAMES, dialog_arrow_visible
from src.game import STEP_SYNC_FRAMES, Game
from src.waiting import NES_FPS, FramePacer, game_ticks, set_game_speed
from tests.test_game_speed import GameSpeedTestCase

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

MAX_FRAMES_PER_DRAW = STEP_SYNC_FRAMES // 2


class TestDialogArrowBlink(GameSpeedTestCase):

    def real_ms_until_the_arrow_changes(self) -> float:
        start = dialog_arrow_visible()
        start_real = self.clock.now
        while dialog_arrow_visible() == start:
            self.clock.now += 1
        return self.clock.now - start_real

    def test_blink_period_scales_with_the_game_speed(self):
        # Like the selection cursors (BlinkingCursor), not the 530 ms real-time USEREVENT timer it used to be
        half_period_ms = DIALOG_ARROW_BLINK_FRAMES * 1000 / NES_FPS
        for speed in (1, 2, 4, 8):
            with self.subTest(speed=speed):
                set_game_speed(speed)
                self.real_ms_until_the_arrow_changes()  # line up with a change
                for _ in range(3):
                    self.assertAlmostEqual(half_period_ms / speed, self.real_ms_until_the_arrow_changes(),
                                           delta=1)

    def test_on_and_off_for_the_same_number_of_frames(self):
        frame_ms = 1000 / NES_FPS
        self.assertTrue(dialog_arrow_visible(0))
        self.assertTrue(dialog_arrow_visible(int((DIALOG_ARROW_BLINK_FRAMES - 1) * frame_ms)))
        self.assertFalse(dialog_arrow_visible(int(DIALOG_ARROW_BLINK_FRAMES * frame_ms) + 1))
        self.assertFalse(dialog_arrow_visible(int((2 * DIALOG_ARROW_BLINK_FRAMES - 1) * frame_ms)))
        self.assertTrue(dialog_arrow_visible(int(2 * DIALOG_ARROW_BLINK_FRAMES * frame_ms) + 1))

    def test_the_game_reads_the_arrow_off_the_game_clock(self):
        set_game_speed(8)
        game = MagicMock()
        for _ in range(100):
            self.clock.now += 7
            self.assertEqual(dialog_arrow_visible(game_ticks()), Game.show_arrow.fget(game))


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
