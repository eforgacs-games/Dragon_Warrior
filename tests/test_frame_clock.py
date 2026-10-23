"""The NES frame rate (#315): NES_FPS is the NTSC NES's 60.0988 Hz, and FrameClock paces the main loop at it."""
import random
import time
from unittest import TestCase
from unittest.mock import patch

import pygame

from src.waiting import NES_FPS, FrameClock, frame_at, frames_to_ms, game_ticks, reset_game_speed, set_game_speed


class FakeTime:
    """pygame's millisecond clock and a sleep that moves it on, oversleeping by up to ``oversleep_ms`` as a real sleep
    does, plus ``work_ms`` of drawing after each pass."""

    def __init__(self, oversleep_ms: float = 0.8, seed: int = 315):
        self.ms = 0.0
        self.oversleep_ms = oversleep_ms
        self.random = random.Random(seed)
        self.sleeps: list[float] = []

    def get_ticks(self) -> int:
        return int(self.ms)

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.ms += seconds * 1000 + self.random.uniform(0, self.oversleep_ms)

    def now(self) -> float:
        return self.ms / 1000


class FrameClockTestCase(TestCase):

    def setUp(self):
        reset_game_speed()
        self.addCleanup(reset_game_speed)
        self.time = FakeTime()
        patcher = patch('pygame.time.get_ticks', self.time.get_ticks)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.clock = FrameClock(sleep=self.time.sleep, now=self.time.now)

    def run_passes(self, passes: int, work_ms: float = 3.0) -> list[int]:
        """The game clock's frame at the start of each pass."""
        frames = []
        for _ in range(passes):
            self.clock.tick()
            frames.append(frame_at(game_ticks()))
            self.time.ms += work_ms
        return frames


class TestNESFrameRate(TestCase):

    def test_the_ntsc_nes_frame_rate(self):
        # 236.25 / 11 MHz master clock, a PPU dot every 4 cycles, 341 x 262 - 0.5 dots a frame
        self.assertAlmostEqual(60.0988, NES_FPS, places=4)
        self.assertAlmostEqual(16.6393, frames_to_ms(1), places=4)

    def test_frame_at(self):
        self.assertEqual(0, frame_at(16))
        self.assertEqual(1, frame_at(17))  # the second frame begins at 16.64 ms
        self.assertEqual(60, frame_at(999))  # not 59: 60 frames begin within the first second
        self.assertEqual(7237, frame_at(frames_to_ms(7237) + 0.01))  # the end music's length: 120.42 s, not 120.62

    def test_every_frame_is_its_whole_length(self):
        for frame in range(0, 20000, 7):
            self.assertEqual(frame, frame_at(frames_to_ms(frame) + 0.001))
            self.assertEqual(frame - 1, frame_at(frames_to_ms(frame) - 0.001))


class TestFrameClock(FrameClockTestCase):

    def test_one_pass_per_frame_without_drift(self):
        # 100 seconds of passes: each starts in the frame after the last one's, and the last is where the game clock
        # says frame 6010 is, not where 60 a second (or 62.5, Clock.tick(60)'s 16 ms) would have it
        frames = self.run_passes(6010)
        self.assertEqual(list(range(frames[0], frames[0] + 6010)), frames)
        self.assertLess(self.time.ms - frames_to_ms(frames[-1]), 5)
        self.assertAlmostEqual(6010 / NES_FPS, self.time.ms / 1000, delta=0.02)

    def test_n_times_as_many_passes_at_speed_n(self):
        for speed in (2, 4, 8):
            with self.subTest(speed=speed):
                set_game_speed(speed)
                self.clock = FrameClock(sleep=self.time.sleep, now=self.time.now)
                started = self.time.ms
                frames = self.run_passes(1000, work_ms=0.5)
                self.assertEqual(list(range(frames[0], frames[0] + 1000)), frames)
                self.assertAlmostEqual(1000 / (NES_FPS * speed), (self.time.ms - started) / 1000, delta=0.02)

    def test_a_late_pass_does_not_wait_or_catch_up(self):
        self.run_passes(3)
        self.time.ms += 100  # a battle took over the screen
        self.time.sleeps.clear()
        self.clock.tick()
        self.assertEqual([], self.time.sleeps)
        frame = frame_at(game_ticks())
        self.time.ms += 3
        self.assertEqual([frame + 1, frame + 2], self.run_passes(2))  # then one pass a frame again, without a burst

    def test_slow_drawing_skips_passes_not_frames(self):
        # Drawing takes 25 ms: a pass can only start every other frame or so, and never waits
        frames = self.run_passes(100, work_ms=25)
        self.assertTrue(all(later > earlier for earlier, later in zip(frames, frames[1:])))
        self.assertAlmostEqual(25 * 100 / frames_to_ms(1), frames[-1] - frames[0], delta=3)

    def test_a_stopped_game_clock_does_not_hang(self):
        self.clock.tick()
        with patch('pygame.time.get_ticks', return_value=0):
            self.clock.tick()  # the frame never begins: gives up after two frames of real time
        self.assertLess(self.time.ms, 3 * frames_to_ms(1))


class TestFrameClockRealTime(TestCase):

    def test_sixty_passes_take_a_second(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        reset_game_speed()
        self.addCleanup(reset_game_speed)
        clock = FrameClock()
        clock.tick()
        started = time.perf_counter()
        for _ in range(60):
            clock.tick()
        # 60 frames are 0.998 s; a loaded machine can oversleep the last one
        self.assertAlmostEqual(60 / NES_FPS, time.perf_counter() - started, delta=0.1)
