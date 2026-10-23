"""The frame recorder (src/frame_recorder.py), its F8 toggle in --dev (src/debug_tools.py) and the scripted recording
tool (tools/record_frames.py)."""
import os
import tempfile
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame
from pygame import Rect

from src.debug_tools import RECORDING_CAPTION, DebugTools
from src.frame_recorder import FrameRecorder, assert_no_flickers, assert_no_one_frame_flickers, changes, diff_frames, \
    find_flickers, find_one_frame_flickers, recording, report, save_recording
from tools import record_frames

RED, GREEN, BLUE = (255, 0, 0), (0, 255, 0), (0, 0, 255)


class RecorderTestCase(TestCase):

    def setUp(self):
        pygame.init()
        self.screen = pygame.display.set_mode((64, 48))
        self.screen.fill(RED)

    def show(self, *colors):
        """Present one frame of each color (the whole screen filled with it)."""
        for color in colors:
            self.screen.fill(color)
            pygame.display.flip()


class TestRecording(RecorderTestCase):

    def test_nothing_is_wrapped_unless_recording(self):
        flip, update = pygame.display.flip, pygame.display.update
        recorder = FrameRecorder()
        self.assertIs(pygame.display.flip, flip)
        with recorder:
            self.assertIsNot(pygame.display.flip, flip)
            self.assertIsNot(pygame.display.update, update)
        self.assertIs(pygame.display.flip, flip)
        self.assertIs(pygame.display.update, update)
        self.assertFalse(recorder.recording)

    def test_records_every_frame_with_who_presented_it(self):
        with recording() as frames:
            frames.label = 'opening'
            self.show(RED, RED)
            frames.label = ''
            pygame.display.update()
        self.assertEqual([0, 1, 2], [frame.index for frame in frames])
        self.assertEqual(['opening', 'opening', ''], [frame.label for frame in frames])
        self.assertEqual('test_frame_recorder.RecorderTestCase.show', frames[0].caller.replace('.<locals>', ''))
        self.assertIn('test_records_every_frame_with_who_presented_it', frames[2].caller)
        self.assertEqual((64, 48), frames[0].size)
        self.assertEqual(RED, tuple(frames[0].surface().get_at((5, 5)))[:3])
        # A frame that repeats the last one keeps no picture of its own
        self.assertIs(frames[0].compressed, frames[1].compressed)
        self.assertTrue(frames[0].same_picture(frames[2]))

    def test_update_shows_the_whole_screen_like_a_scaled_display(self):
        with recording() as frames:
            self.screen.fill(GREEN)
            pygame.display.update(Rect(0, 0, 8, 8))
        self.assertEqual(GREEN, tuple(frames[0].surface().get_at((40, 40)))[:3])

    def test_partial_updates(self):
        pygame.display.flip()
        with recording(partial_updates=True) as frames:
            pygame.display.flip()  # all red
            self.screen.fill(GREEN)
            pygame.display.update(Rect(0, 0, 8, 8))
            pygame.display.update([Rect(10, 10, 2, 2), None])
            pygame.display.update(30, 30, 1, 1)
        picture = frames[1].surface()
        self.assertEqual(GREEN, tuple(picture.get_at((7, 7)))[:3])
        self.assertEqual(RED, tuple(picture.get_at((40, 40)))[:3])
        self.assertEqual(GREEN, tuple(frames[2].surface().get_at((11, 11)))[:3])
        self.assertEqual(GREEN, tuple(frames[3].surface().get_at((30, 30)))[:3])
        self.assertEqual(RED, tuple(frames[3].surface().get_at((31, 31)))[:3])

    def test_max_frames(self):
        with recording(max_frames=2) as frames:
            self.show(RED, GREEN, BLUE)
        self.assertEqual(2, len(frames))

    def test_on_frame(self):
        seen = []
        with recording(on_frame=lambda frame: seen.append(frame.index)):
            self.show(RED, GREEN)
        self.assertEqual([0, 1], seen)


class TestComparing(RecorderTestCase):

    def test_diff_frames(self):
        with recording() as frames:
            pygame.display.flip()
            self.screen.fill(GREEN, Rect(3, 5, 4, 2))
            self.screen.set_at((60, 40), BLUE)
            pygame.display.flip()
        diff = diff_frames(frames[0], frames[1])
        self.assertEqual(9, diff.pixels)
        self.assertEqual(3, diff.rows)
        self.assertEqual(Rect(3, 5, 58, 36), diff.bounds)
        self.assertIn('9 pixels in 3 rows', diff.describe())
        self.assertIsNone(diff_frames(frames[0], frames[0]).bounds)
        self.assertEqual([1], [change.after.index for change in changes(frames)])

    def test_one_frame_flicker(self):
        with recording() as frames:
            self.show(RED, RED, GREEN, RED, BLUE, BLUE, GREEN, GREEN, BLUE)
        flickers = find_one_frame_flickers(frames)
        self.assertEqual([2], [flicker.frames[0].index for flicker in flickers])
        self.assertEqual((1, 3), (flickers[0].before.index, flickers[0].after.index))
        # GREEN shown for two frames between BLUEs is found when two frames count
        self.assertEqual([2, 6], [flicker.frames[0].index for flicker in find_flickers(frames, max_length=2)])
        with self.assertRaisesRegex(AssertionError, r'1 flicker\(s\) in 9 frames:\nframe 2 '):
            assert_no_one_frame_flickers(frames)
        with self.assertRaises(AssertionError):
            assert_no_flickers(frames, max_length=2)

    def test_a_flicker_of_a_few_different_pictures(self):
        with recording() as frames:
            self.show(RED, GREEN, BLUE, RED)
        self.assertEqual([], find_one_frame_flickers(frames))
        self.assertEqual([(1, 2)], [tuple(frame.index for frame in flicker.frames)
                                    for flicker in find_flickers(frames, max_length=2)])

    def test_no_flicker(self):
        with recording() as frames:
            self.show(RED, GREEN, GREEN, BLUE, RED)
        assert_no_one_frame_flickers(frames)
        assert_no_one_frame_flickers([])

    def test_region(self):
        with recording() as frames:
            for color in (RED, GREEN, RED):
                self.screen.fill(color, Rect(0, 0, 8, 8))
                pygame.display.flip()
        self.assertEqual(1, len(find_one_frame_flickers(frames)))
        assert_no_one_frame_flickers(frames, region=Rect(10, 10, 20, 20))

    def test_max_ms(self):
        ticks = iter([0, 16, 32, 100, 116, 132])
        with patch('src.frame_recorder.game_ticks', side_effect=lambda: next(ticks)), recording() as frames:
            self.show(RED, GREEN, RED, BLUE, GREEN, BLUE)
        self.assertEqual([1, 4], [flicker.frames[0].index for flicker in find_flickers(frames)])
        self.assertEqual(16, find_flickers(frames)[0].duration_ms)
        self.assertEqual([], find_flickers(frames, max_ms=10))


class TestSaving(RecorderTestCase):

    def test_report_and_files(self):
        with recording() as frames:
            self.show(RED, RED, GREEN, RED)
        text = report(frames)
        self.assertIn('4 frames presented, 3 changes of picture', text)
        self.assertIn('frame 2 (', text)
        self.assertIn('differs from frame 1 before it and frame 3 after it', text)
        self.assertIn('No frames were presented', report([]))
        with tempfile.TemporaryDirectory() as out_dir:
            self.assertEqual(text, save_recording(frames, out_dir))
            self.assertEqual(['frame_00000.png', 'frame_00002.png', 'frame_00003.png', 'report.txt'],
                             sorted(os.listdir(out_dir)))
            self.assertEqual(GREEN, tuple(pygame.image.load(os.path.join(out_dir, 'frame_00002.png')).get_at((0, 0)))[:3])
        with tempfile.TemporaryDirectory() as out_dir:
            save_recording(frames, out_dir, all_frames=True)
            self.assertEqual(5, len(os.listdir(out_dir)))


class TestDevToggle(RecorderTestCase):

    def test_f8_starts_and_stops_recording(self):
        flip = pygame.display.flip
        game = MagicMock()
        game.cmd_menu.menu.is_enabled.return_value = True  # F8 works even with a window open
        tools = DebugTools(game)
        pygame.display.set_caption('Dragon Warrior')
        tools.handle_keydown(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F8))
        try:
            self.assertIsNotNone(tools.frame_recorder)
            self.assertEqual('Dragon Warrior' + RECORDING_CAPTION, pygame.display.get_caption()[0])
            self.show(RED, GREEN)
        finally:
            with tempfile.TemporaryDirectory() as out_dir:
                with patch('builtins.print'):
                    self.assertEqual(out_dir, tools.toggle_frame_recording(out_dir))
                self.assertEqual(['frame_00000.png', 'frame_00001.png', 'report.txt'], sorted(os.listdir(out_dir)))
        self.assertIsNone(tools.frame_recorder)
        self.assertIs(pygame.display.flip, flip)
        self.assertEqual('Dragon Warrior', pygame.display.get_caption()[0])


class TestRecordFramesTool(TestCase):

    def test_parse_script(self):
        presses, end = record_frames.parse_script('wait:10, a, right:32, talk, b*2', gap=5)
        k, right, j = pygame.K_k, pygame.K_RIGHT, pygame.K_j
        self.assertEqual([(10, 12, k, 'step 2: a'), (17, 49, right, 'step 3: right:32'), (54, 56, k, 'step 4: a'),
                          (61, 63, k, 'step 5: a'), (68, 70, j, 'step 6: b'), (75, 77, j, 'step 7: b')], presses)
        self.assertEqual(82, end)
        self.assertEqual(16, record_frames.parse_script('up', gap=0)[1])
        with self.assertRaisesRegex(ValueError, 'Unknown script step'):
            record_frames.parse_script('jump', gap=0)

    def test_records_a_scene(self):
        # Open the COMMAND window from a checkpoint, in real time
        with tempfile.TemporaryDirectory() as out_dir, patch('builtins.print'):
            self.assertEqual(0, record_frames.main(['--checkpoint', 'swamp_cave', '--script', 'wait:40,a', '--gap', '0',
                                                    '--tail', '30', '--speed', '2', '--out', out_dir]))
            with open(os.path.join(out_dir, 'report.txt')) as report_file:
                text = report_file.read()
        self.assertIn('window_drop_down_effect, step 2: a)', text)
