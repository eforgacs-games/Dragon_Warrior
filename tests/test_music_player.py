import os
import unittest
from unittest.mock import patch, MagicMock

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from src.music_player import MusicPlayer


class TestMusicPlayerInitialization(unittest.TestCase):

    def test_music_enabled_true(self):
        config = {'MUSIC_ENABLED': True, 'SOUND_ENABLED': False, 'ORCHESTRA_MUSIC_ENABLED': False}
        player = MusicPlayer(config)
        self.assertTrue(player.music_enabled)

    def test_music_enabled_false(self):
        config = {'MUSIC_ENABLED': False, 'SOUND_ENABLED': False, 'ORCHESTRA_MUSIC_ENABLED': False}
        player = MusicPlayer(config)
        self.assertFalse(player.music_enabled)

    def test_sound_enabled(self):
        config = {'MUSIC_ENABLED': False, 'SOUND_ENABLED': True, 'ORCHESTRA_MUSIC_ENABLED': False}
        player = MusicPlayer(config)
        self.assertTrue(player.sound_enabled)

    def test_orchestra_music_enabled(self):
        config = {'MUSIC_ENABLED': False, 'SOUND_ENABLED': False, 'ORCHESTRA_MUSIC_ENABLED': True}
        player = MusicPlayer(config)
        self.assertTrue(player.orchestra_music_enabled)

    def test_default_volume(self):
        config = {'MUSIC_ENABLED': True, 'SOUND_ENABLED': False, 'ORCHESTRA_MUSIC_ENABLED': False}
        player = MusicPlayer(config)
        self.assertAlmostEqual(player.music_volume, 0.5)


class TestMusicPlayerControls(unittest.TestCase):

    def setUp(self):
        self.config = {'MUSIC_ENABLED': True, 'SOUND_ENABLED': False, 'ORCHESTRA_MUSIC_ENABLED': False}
        self.player = MusicPlayer(self.config)

    @patch('src.music_player.mixer')
    def test_load_and_play_music_when_enabled(self, mock_mixer):
        self.player.load_and_play_music('some/path.mp3')
        mock_mixer.music.stop.assert_called_once()
        mock_mixer.music.load.assert_called_once_with('some/path.mp3')
        mock_mixer.music.set_volume.assert_called_once_with(0.5)
        mock_mixer.music.play.assert_called_once_with(-1)

    @patch('src.music_player.mixer')
    def test_load_and_play_music_when_disabled(self, mock_mixer):
        self.player.music_enabled = False
        self.player.load_and_play_music('some/path.mp3')
        mock_mixer.music.stop.assert_called_once()
        mock_mixer.music.load.assert_called_once_with('some/path.mp3')
        mock_mixer.music.play.assert_not_called()

    @patch('src.music_player.mixer')
    def test_load_and_play_custom_loop(self, mock_mixer):
        self.player.load_and_play_music('some/path.mp3', loop=0)
        mock_mixer.music.play.assert_called_once_with(0)

    @patch('src.music_player.mixer')
    def test_stop_music(self, mock_mixer):
        MusicPlayer.stop_music()
        mock_mixer.music.stop.assert_called_once()

    @patch('src.music_player.mixer')
    def test_pause_music(self, mock_mixer):
        MusicPlayer.pause_music()
        mock_mixer.music.pause.assert_called_once()

    @patch('src.music_player.mixer')
    def test_unpause_music(self, mock_mixer):
        MusicPlayer.unpause_music()
        mock_mixer.music.unpause.assert_called_once()

    @patch('src.music_player.mixer')
    def test_fadeout_music(self, mock_mixer):
        MusicPlayer.fadeout_music(1000)
        mock_mixer.music.fadeout.assert_called_once_with(1000)

    @patch('src.music_player.mixer')
    def test_set_music_volume(self, mock_mixer):
        self.player.set_music_volume(0.8)
        self.assertAlmostEqual(self.player.music_volume, 0.8)
        mock_mixer.music.set_volume.assert_called_once_with(0.8)

    def test_get_music_volume_default(self):
        result = self.player.get_music_volume()
        self.assertAlmostEqual(result, 0.5)

    @patch('src.music_player.mixer')
    def test_get_music_volume_after_set(self, mock_mixer):
        self.player.set_music_volume(0.3)
        self.assertAlmostEqual(self.player.get_music_volume(), 0.3)

    @patch('src.music_player.mixer')
    def test_set_volume_zero(self, mock_mixer):
        self.player.set_music_volume(0.0)
        self.assertAlmostEqual(self.player.music_volume, 0.0)

    @patch('src.music_player.mixer')
    def test_set_volume_max(self, mock_mixer):
        self.player.set_music_volume(1.0)
        self.assertAlmostEqual(self.player.music_volume, 1.0)

    @patch('src.music_player.mixer')
    def test_load_and_play_stops_previous_music(self, mock_mixer):
        self.player.load_and_play_music('track1.mp3')
        self.player.load_and_play_music('track2.mp3')
        self.assertEqual(mock_mixer.music.stop.call_count, 2)


if __name__ == '__main__':
    unittest.main()
