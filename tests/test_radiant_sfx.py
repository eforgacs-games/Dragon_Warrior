"""SFX_RADIANT is rendered from the NES sound data (tools/make_radiant_sfx.py), as the soundtrack has no recording."""
import os
import tempfile
import wave
from unittest import TestCase

from src.config.test_config import test_config
from src.directories import Directories
from tools.make_radiant_sfx import RADIANT_SFX, SAMPLE_RATE, main


class TestRadiantSfx(TestCase):

    def test_the_game_plays_the_rendered_sound(self):
        self.assertEqual('radiant.wav', os.path.basename(Directories(test_config).radiant_sfx))

    def test_it_lasts_the_nes_eight_frames(self):
        self.assertEqual(8, sum(frames for _, _, frames in RADIANT_SFX))
        with wave.open(Directories(test_config).radiant_sfx) as wav:
            seconds = wav.getnframes() / wav.getframerate()
        self.assertAlmostEqual(8 / 60.0988 + 0.01, seconds, places=2)  # and 10 ms for the filters to settle

    def test_the_committed_file_is_what_the_tool_renders(self):
        with tempfile.TemporaryDirectory() as folder:
            rendered = os.path.join(folder, 'radiant.wav')
            main(['--out', rendered])
            with wave.open(rendered) as new, wave.open(Directories(test_config).radiant_sfx) as committed:
                self.assertEqual(SAMPLE_RATE, committed.getframerate())
                self.assertEqual(new.readframes(new.getnframes()), committed.readframes(committed.getnframes()))
