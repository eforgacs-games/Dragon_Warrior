"""
src/paths.py: the game finds data/ in the repository when run from source and in sys._MEIPASS in a PyInstaller build,
and saves to src/saves from source but to a per-user folder in a build. src/smoke_test.py: the release workflow's
--smoke-test check finds every game file from source, and reports the ones a build would be missing.
"""
import os
import sys
import tempfile
from os.path import dirname, join, realpath
from unittest import TestCase
from unittest.mock import MagicMock, patch

from src import paths
from src.chiptune import ChiptuneError
from src.config.test_config import test_config
from src.directories import Directories, clip_paths, music_paths
from src.paths import data_path, default_save_dir, is_frozen, project_root, user_config_dir, user_data_dir
from src.chiptune_soundtracks import MSC_END, MSC_VICTORY, nes_track
from src.smoke_test import check_chiptune_tracks, check_game_files, check_save_dir, game_file_paths, untagged_clips

REPO_ROOT = dirname(dirname(realpath(__file__)))
HOME = os.path.expanduser('~')


def config_without_save_dir() -> dict:
    """test_config without a SAVE_DIR (other tests, e.g. the checkpoint ones, may leave one in it)."""
    return {**test_config, 'SAVE_DIR': None}


class FrozenTestCase(TestCase):
    def freeze(self, meipass: str | None) -> None:
        """Patches sys as a PyInstaller build sets it: sys.frozen, and sys._MEIPASS for the folder it unpacks to."""
        patches = [patch.object(sys, 'frozen', True, create=True)]
        if meipass is not None:
            patches.append(patch.object(sys, '_MEIPASS', meipass, create=True))
        for frozen_patch in patches:
            frozen_patch.start()
            self.addCleanup(frozen_patch.stop)
        # the music tables are cached with the paths they were first made with: a build's are under its _MEIPASS
        for cached in (music_paths, clip_paths):
            cached.cache_clear()
            self.addCleanup(cached.cache_clear)


class TestFromSource(TestCase):
    def test_not_frozen(self):
        self.assertFalse(is_frozen())

    def test_data_is_in_the_repository(self):
        self.assertEqual(project_root(), REPO_ROOT)
        self.assertEqual(data_path('fonts', 'unifont.otf'), join(REPO_ROOT, 'data', 'fonts', 'unifont.otf'))
        self.assertTrue(os.path.isfile(data_path('fonts', 'unifont.otf')))

    def test_saves_stay_in_src_saves(self):
        self.assertEqual(default_save_dir(), join(REPO_ROOT, 'src', 'saves'))
        self.assertEqual(Directories(config_without_save_dir()).save_dir, join(REPO_ROOT, 'src', 'saves'))

    def test_save_dir_config_still_wins(self):
        self.assertEqual(Directories({**test_config, 'SAVE_DIR': '/somewhere'}).save_dir, '/somewhere')


class TestFrozen(FrozenTestCase):
    def test_data_is_in_meipass(self):
        with tempfile.TemporaryDirectory() as meipass:
            self.freeze(meipass)
            self.assertTrue(is_frozen())
            self.assertEqual(project_root(), meipass)
            self.assertEqual(data_path('sound', 'sfx'), join(meipass, 'data', 'sound', 'sfx'))

    def test_without_meipass_data_is_next_to_the_executable(self):
        self.freeze(None)
        with patch.object(sys, '_MEIPASS', None, create=True):
            self.assertEqual(project_root(), dirname(realpath(sys.executable)))

    def test_saves_go_to_the_user_data_dir(self):
        with tempfile.TemporaryDirectory() as meipass:
            self.freeze(meipass)
            self.assertEqual(default_save_dir(), join(user_data_dir(), 'saves'))
            self.assertFalse(default_save_dir().startswith(meipass))

    def test_directories_finds_files_in_meipass_and_saves_per_user(self):
        # The repository stands in for the unpacked build: it has data/ at the same paths
        self.freeze(REPO_ROOT)
        directories = Directories(config_without_save_dir())
        self.assertEqual(directories.save_dir, join(user_data_dir(), 'saves'))
        self.assertEqual(directories.UNIFONT_PATH, join(REPO_ROOT, 'data', 'fonts', 'unifont.otf'))
        self.assertEqual(directories.root_project_path, REPO_ROOT)
        # A checkpoint's SAVE_DIR still redirects the saves
        self.assertEqual(Directories({**test_config, 'SAVE_DIR': '/somewhere'}).save_dir, '/somewhere')


class TestUserDataDir(TestCase):
    def test_windows_uses_appdata(self):
        self.assertEqual(user_data_dir('win32', {'APPDATA': r'C:\Users\me\AppData\Roaming'}),
                         join(r'C:\Users\me\AppData\Roaming', paths.APP_NAME))

    def test_windows_without_appdata(self):
        self.assertEqual(user_data_dir('win32', {}), join(HOME, 'AppData', 'Roaming', paths.APP_NAME))

    def test_macos_uses_application_support(self):
        self.assertEqual(user_data_dir('darwin', {'XDG_DATA_HOME': '/ignored'}),
                         join(HOME, 'Library', 'Application Support', paths.APP_NAME))

    def test_linux_uses_xdg_data_home(self):
        self.assertEqual(user_data_dir('linux', {'XDG_DATA_HOME': '/data/home'}), join('/data/home', 'dragon-warrior'))

    def test_linux_defaults_to_local_share(self):
        expected = join(HOME, '.local', 'share', 'dragon-warrior')
        self.assertEqual(user_data_dir('linux', {}), expected)
        self.assertEqual(user_data_dir('linux', {'XDG_DATA_HOME': ''}), expected)
        # The XDG spec says a relative XDG_DATA_HOME is ignored
        self.assertEqual(user_data_dir('linux', {'XDG_DATA_HOME': 'relative/path'}), expected)

    def test_current_platform(self):
        self.assertEqual(user_data_dir(), user_data_dir(sys.platform, os.environ))


class TestSmokeTest(FrozenTestCase):
    def test_finds_every_game_file_from_source(self):
        # every chiptune track renders: tests/test_chiptune_soundtracks.py, where libgme is installed
        with patch('src.smoke_test.check_chiptune_tracks', return_value=[]):
            self.assertEqual(check_game_files(test_config), [])

    def test_a_build_must_play_the_music_with_its_own_libgme(self):
        with tempfile.TemporaryDirectory() as meipass:
            self.freeze(meipass)
            for library_path, problems in ((join(meipass, 'libgme.so.0'), []),
                                           ('libgme.so.0', ["libgme isn't bundled: the build loaded libgme.so.0"])):
                with self.subTest(library=library_path), \
                        patch('src.smoke_test.chiptune_library', return_value=MagicMock(path=library_path)), \
                        patch('src.smoke_test.chiptune_tracks', return_value=[]), \
                        patch('src.smoke_test.untagged_clips', return_value=[]):
                    self.assertEqual(problems, check_chiptune_tracks())

    def test_every_clip_must_have_its_length(self):
        self.assertEqual([], untagged_clips())
        with patch('src.smoke_test.tagged_length_seconds', return_value=None):
            problems = untagged_clips()
        self.assertIn(f"{nes_track(MSC_VICTORY)} has no tagged length", problems)
        self.assertIn(f"{nes_track(MSC_END)} has no tagged length", problems)

    def test_a_build_without_libgme_fails(self):
        with patch('src.smoke_test.chiptune_library', return_value=None):
            self.assertEqual(["libgme isn't bundled or installed: the NES and SFC soundtracks can't play"],
                             check_chiptune_tracks())

    def test_a_silent_or_broken_track_fails(self):
        emulator = MagicMock()
        emulator.render.side_effect = [bytes(8), ChiptuneError('bad track')]
        with patch('src.smoke_test.chiptune_library', return_value=MagicMock(path='libgme.so.0')), \
                patch('src.smoke_test.chiptune_tracks', return_value=['a.spc', 'b.spc']), \
                patch('src.smoke_test.Emulator', return_value=emulator):
            self.assertEqual(['a.spc renders only silence', "can't play b.spc: bad track"], check_chiptune_tracks())

    def test_checks_every_soundtrack_and_the_checkpoints(self):
        file_paths = game_file_paths(test_config)
        self.assertIn(data_path('sound', 'music', 'orchestra', '05 Fight.mp3'), file_paths)
        self.assertIn(data_path('sound', 'music', 'SFC', 'a_monster_draws_near.spc'), file_paths)
        self.assertIn(data_path('sound', 'music', 'NES', 'dragon_warrior.nsf'), file_paths)
        self.assertIn(data_path('checkpoints', 'rainbow_bridge.json'), file_paths)
        self.assertIn(data_path('fonts', 'unifont.otf'), file_paths)
        self.assertIn(data_path('fonts', 'OFL-unifont.txt'), file_paths)

    def test_reports_what_a_build_is_missing(self):
        with tempfile.TemporaryDirectory() as meipass:
            # A build with only the fonts (Directories loads two of them as it starts)
            os.makedirs(join(meipass, 'data'))
            os.symlink(join(REPO_ROOT, 'data', 'fonts'), join(meipass, 'data', 'fonts'))
            self.freeze(meipass)
            # Set as src/checkpoints.py is imported, which in a build is after sys._MEIPASS is set
            with patch('src.checkpoints.CHECKPOINTS_DIR', data_path('checkpoints')):
                problems = check_game_files(test_config)
        self.assertIn(f"missing: {join(meipass, 'data', 'images', 'tileset.png')}", problems)
        self.assertIn(f"missing: {join(meipass, 'data', 'checkpoints', 'throne_room.json')}", problems)
        self.assertTrue(any(problem.startswith("can't load the Korean translations") for problem in problems))
        self.assertFalse(any('unifont' in problem for problem in problems))

    def test_save_dir_must_be_writable(self):
        with tempfile.TemporaryDirectory() as parent:
            self.assertEqual(check_save_dir(join(parent, 'new', 'saves')), [])
            self.assertTrue(os.path.isdir(join(parent, 'new', 'saves')))
            self.assertEqual(os.listdir(join(parent, 'new', 'saves')), [])
            a_file = join(parent, 'file')
            open(a_file, 'w').close()
            self.assertEqual(len(check_save_dir(join(a_file, 'saves'))), 1)


class TestUserConfigDir(TestCase):
    """Where the global settings file goes (src/settings.py)."""

    def test_windows_and_macos_share_the_data_dir(self):
        self.assertEqual(user_config_dir('win32', {'APPDATA': r'C:\Users\me\AppData\Roaming'}),
                         join(r'C:\Users\me\AppData\Roaming', paths.APP_NAME))
        self.assertEqual(user_config_dir('darwin', {'XDG_CONFIG_HOME': '/ignored'}),
                         join(HOME, 'Library', 'Application Support', paths.APP_NAME))

    def test_linux_uses_xdg_config_home(self):
        self.assertEqual(user_config_dir('linux', {'XDG_CONFIG_HOME': '/config/home'}),
                         join('/config/home', 'dragon-warrior'))

    def test_linux_defaults_to_dot_config(self):
        expected = join(HOME, '.config', 'dragon-warrior')
        self.assertEqual(user_config_dir('linux', {}), expected)
        self.assertEqual(user_config_dir('linux', {'XDG_CONFIG_HOME': 'relative/path'}), expected)
