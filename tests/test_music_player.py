import os
import unittest
from unittest.mock import patch

from pygame import mixer

from src.config.test_config import test_config
from src.directories import Directories
from src.music_player import MusicPlayer, clip_length_ms
from src.waiting import reset_game_speed, set_game_speed


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


class TestPlayUntilEnd(unittest.TestCase):
    """NES InitMusicSFX with a music clip, then WaitForMusicEnd (the inn's MSC_INN)."""

    CONFIG = {'MUSIC_ENABLED': True, 'SOUND_ENABLED': False, 'ORCHESTRA_MUSIC_ENABLED': False, 'NO_WAIT': False}

    def test_plays_once_and_waits_until_the_clip_ends(self):
        player = MusicPlayer(self.CONFIG)
        with patch('src.music_player.mixer') as mock_mixer, patch('src.music_player.wait') as mock_wait:
            mock_mixer.music.get_busy.side_effect = [True, True, True, False]
            player.play_until_end('inn.mp3', self.CONFIG)
        mock_mixer.music.stop.assert_called_once()
        mock_mixer.music.load.assert_called_once_with('inn.mp3')
        mock_mixer.music.play.assert_called_once_with()  # once, not looped
        self.assertEqual(mock_wait.call_count, 3)  # quit-safe waits until the music is no longer busy

    def test_wait_ends_with_the_music_at_any_game_speed(self):
        set_game_speed(4)
        self.addCleanup(reset_game_speed)
        player = MusicPlayer(self.CONFIG)
        with patch('src.music_player.mixer') as mock_mixer, patch('src.music_player.wait') as mock_wait:
            mock_mixer.music.get_busy.side_effect = [True] * 10 + [False]
            player.play_until_end('inn.mp3', self.CONFIG)
        self.assertEqual(mock_wait.call_count, 10)
        self.assertEqual(mock_mixer.music.get_busy.call_count, 11)

    def test_no_wait(self):
        player = MusicPlayer(self.CONFIG)
        with patch('src.music_player.mixer') as mock_mixer, patch('src.music_player.wait') as mock_wait:
            player.play_until_end('inn.mp3', {**self.CONFIG, 'NO_WAIT': True})
        mock_mixer.music.play.assert_called_once_with()
        mock_wait.assert_not_called()

    def test_music_off_still_waits_as_long_as_the_clip(self):
        config = {**self.CONFIG, 'MUSIC_ENABLED': False}
        player = MusicPlayer(config)
        with patch('src.music_player.mixer') as mock_mixer, patch('src.music_player.wait') as mock_wait, \
                patch('src.music_player.clip_length_ms', return_value=2391.0), \
                patch('src.music_player.game_ticks', return_value=1000):
            player.play_until_end('inn.mp3', config)
        mock_mixer.music.load.assert_not_called()
        mock_wait.assert_called_once_with(2391.0, config)

    def test_play_clip_returns_at_once_and_the_wait_comes_later(self):
        # NES EnemyDefeated: InitMusicSFX MSC_VICTORY, the experience and gold lines while it plays, then ChkLevelUp's
        # WaitForMusicEnd
        player = MusicPlayer(self.CONFIG)
        with patch('src.music_player.mixer') as mock_mixer, patch('src.music_player.wait') as mock_wait:
            mock_mixer.music.get_busy.side_effect = [True, True, False]
            player.play_clip('victory.mp3')
            mock_mixer.music.load.assert_called_once_with('victory.mp3')
            mock_mixer.music.play.assert_called_once_with()
            mock_wait.assert_not_called()
            player.wait_for_music_end(self.CONFIG)
        self.assertEqual(mock_wait.call_count, 2)

    def test_a_new_clip_replaces_the_one_playing(self):
        # NES DoLevelUp: MSC_LEVEL_UP cuts the victory music off, there is one music track
        player = MusicPlayer(self.CONFIG)
        with patch('src.music_player.mixer') as mock_mixer:
            player.play_clip('victory.mp3')
            player.play_clip('level_up.mp3')
        self.assertEqual(mock_mixer.music.stop.call_count, 2)
        self.assertEqual([c.args for c in mock_mixer.music.load.call_args_list], [('victory.mp3',), ('level_up.mp3',)])

    def test_music_off_waits_out_the_rest_of_the_clip(self):
        config = {**self.CONFIG, 'MUSIC_ENABLED': False}
        player = MusicPlayer(config)
        with patch('src.music_player.mixer') as mock_mixer, patch('src.music_player.wait') as mock_wait, \
                patch('src.music_player.clip_length_ms', return_value=5000.0), \
                patch('src.music_player.game_ticks', side_effect=[1000, 4000]):
            player.play_clip('victory.mp3')
            player.wait_for_music_end(config)
        mock_mixer.music.load.assert_not_called()
        mock_wait.assert_called_once_with(2000.0, config)  # 3000 of the 5000 ms have already gone by

    def test_wait_for_music_end_without_a_clip_does_nothing_with_the_music_off(self):
        config = {**self.CONFIG, 'MUSIC_ENABLED': False}
        with patch('src.music_player.wait') as mock_wait:
            MusicPlayer(config).wait_for_music_end(config)
        mock_wait.assert_not_called()

    def test_inn_jingle_is_the_nes_track(self):
        # MSC_INN ($15) is the soundtrack's track 21, between MSC_DEATH ($14, track 20) and MSC_PRNCS_LOVE ($16)
        directories = Directories(test_config)
        self.assertTrue(directories.inn_music.endswith('21 Dragon Quest 1 - Special Item.mp3'))
        self.assertTrue(os.path.exists(directories.inn_music))
        mixer.init()
        self.addCleanup(mixer.quit)
        self.assertTrue(2000 < clip_length_ms(directories.inn_music) < 3000)


if __name__ == '__main__':
    unittest.main()
