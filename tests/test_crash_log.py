"""The crash log (src/crash_log.py, #435)."""
import io
import os
import subprocess
import sys
import tempfile
from collections import deque
from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock, patch

from src import crash_log
from src.crash_log import MAX_CRASH_LOGS, RecentOutput, can_show_dialog, crash_message, crash_report, excepthook, \
    game_version, show_dialog, write_crash_log
from src.paths import project_root


def raised() -> tuple:
    try:
        {}['missing']
    except KeyError as error:
        return type(error), error, error.__traceback__
    raise AssertionError


class TestCrashReport(TestCase):

    def test_what_the_report_holds(self):
        report = crash_report(*raised(), lines=['Loaded adventure log 1', 'Entering Brecconary'],
                              now=datetime(2026, 10, 24, 3, 4, 5))
        self.assertIn('Time: 2026-10-24T03:04:05', report)
        self.assertIn(f'Version: {game_version()}', report)
        self.assertIn('OS: ', report)
        self.assertIn('Python: ', report)
        self.assertIn('Traceback (most recent call last):', report)
        self.assertIn("KeyError: 'missing'", report)
        self.assertIn('in raised', report)
        self.assertTrue(report.rstrip().endswith('Last 2 lines of output:\nLoaded adventure log 1\nEntering Brecconary'))

    def test_no_output(self):
        self.assertIn('No output before the crash.', crash_report(*raised(), lines=[]))

    def test_the_version_is_pyprojects(self):
        with open(os.path.join(project_root(), 'pyproject.toml')) as pyproject:
            version = next(line for line in pyproject if line.startswith('version = ')).split('"')[1]
        self.assertEqual(f'{version} (source)', game_version())
        with patch('src.crash_log.project_root', return_value='/nowhere'):
            self.assertEqual('unknown (source)', game_version())


class TestWriteCrashLog(TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp()

    def test_a_log_in_the_folder(self):
        path = write_crash_log('the report', self.folder, now=datetime(2026, 10, 24, 3, 4, 5))
        self.assertEqual(os.path.join(self.folder, 'crash-20261024-030405.log'), path)
        with open(path, encoding='utf-8') as log:
            self.assertEqual('the report', log.read())

    def test_in_the_settings_folder_by_default(self):
        with patch('src.crash_log.user_config_dir', return_value=self.folder):
            path = write_crash_log('report')
        self.assertEqual(self.folder, os.path.dirname(path))

    def test_only_the_newest_are_kept(self):
        for second in range(MAX_CRASH_LOGS + 3):
            write_crash_log(str(second), self.folder, now=datetime(2026, 10, 24, 3, 4, second))
        open(os.path.join(self.folder, 'settings.json'), 'w').close()  # anything else stays
        write_crash_log('last', self.folder, now=datetime(2026, 10, 24, 3, 5, 0))
        logs = sorted(name for name in os.listdir(self.folder) if name.startswith('crash-'))
        self.assertEqual(MAX_CRASH_LOGS, len(logs))
        self.assertEqual('crash-20261024-030500.log', logs[-1])
        self.assertEqual('crash-20261024-030404.log', logs[0])
        self.assertIn('settings.json', os.listdir(self.folder))

    def test_the_temporary_folder_if_the_settings_folder_cant_be_written(self):
        blocked = os.path.join(self.folder, 'a file, not a folder')
        open(blocked, 'w').close()
        with patch('src.crash_log.tempfile.gettempdir', return_value=self.folder):
            path = write_crash_log('report', os.path.join(blocked, 'settings'))
        self.assertEqual(self.folder, os.path.dirname(path))


class TestRecentOutput(TestCase):

    def test_keeps_the_last_lines_and_passes_them_on(self):
        lines: deque[str] = deque(maxlen=3)
        real = io.StringIO()
        output = RecentOutput(lines, real)
        output.write('one\ntwo\nthr')
        output.write('ee\nfour\nfive')
        self.assertEqual(['two', 'three', 'four'], list(lines))
        self.assertEqual('five', output.pending())
        self.assertEqual('one\ntwo\nthree\nfour\nfive', real.getvalue())

    def test_with_no_console(self):
        # A windowed build: sys.stdout and sys.stderr are None
        lines: deque[str] = deque(maxlen=3)
        output = RecentOutput(lines, None)
        self.assertEqual(4, output.write('hi\n\n'))
        output.flush()
        self.assertEqual(['hi', ''], list(lines))
        with self.assertRaises(AttributeError):
            output.fileno()


class TestExceptHook(TestCase):

    def test_writes_the_log_after_the_traceback(self):
        calls = []
        with patch('sys.__excepthook__', side_effect=lambda *_: calls.append('traceback')), \
                patch('src.crash_log.handle_crash', side_effect=lambda *_: calls.append('log')):
            excepthook(*raised())
        self.assertEqual(['traceback', 'log'], calls)

    def test_ctrl_c_is_not_a_crash(self):
        with patch('sys.__excepthook__'), patch('src.crash_log.handle_crash') as handle_crash:
            excepthook(KeyboardInterrupt, KeyboardInterrupt(), None)
        handle_crash.assert_not_called()

    def test_handle_crash_says_where_the_log_is(self):
        folder = tempfile.mkdtemp()
        stderr = io.StringIO()
        with patch('src.crash_log.user_config_dir', return_value=folder), patch('sys.stderr', stderr), \
                patch('src.crash_log.can_show_dialog', return_value=True), \
                patch('src.crash_log.show_dialog') as dialog:
            path = crash_log.handle_crash(*raised())
        assert path is not None
        self.assertTrue(os.path.isfile(path))
        self.assertIn(crash_message(path), stderr.getvalue())
        dialog.assert_called_once_with(crash_message(path))

    def test_no_dialog_headless_or_in_the_smoke_test(self):
        self.assertFalse(can_show_dialog({'SDL_VIDEODRIVER': 'dummy'}, ['game.py']))
        self.assertFalse(can_show_dialog({}, ['DragonWarrior', '--smoke-test']))
        self.assertTrue(can_show_dialog({}, ['DragonWarrior']))

    def test_the_message_says_how_to_report_it(self):
        message = crash_message('/home/ed/.config/dragon-warrior/crash-1.log')
        self.assertIn('/home/ed/.config/dragon-warrior/crash-1.log', message)
        self.assertIn('github.com/eforgacs-games/Dragon_Warrior/issues', message)


class TestShowDialog(TestCase):

    def setUp(self):
        patch('pygame.quit').start()
        self.addCleanup(patch.stopall)

    def test_macos(self):
        run = MagicMock()
        self.assertTrue(show_dialog('the message', 'darwin', run))
        command = run.call_args.args[0]
        self.assertEqual('osascript', command[0])
        self.assertEqual(['the message', 'Dragon Warrior crashed'], command[-2:])

    def test_linux_tries_each_dialog_program(self):
        run = MagicMock(side_effect=[FileNotFoundError, None])
        self.assertTrue(show_dialog('the message', 'linux', run))
        self.assertEqual(['zenity', 'kdialog'], [call.args[0][0] for call in run.call_args_list])

    def test_none_there(self):
        run = MagicMock(side_effect=FileNotFoundError)
        self.assertFalse(show_dialog('the message', 'linux', run))


class TestACrashingGame(TestCase):

    def test_an_uncaught_exception_exits_1_with_its_traceback_and_a_log(self):
        # What the release smoke test relies on: a crash still fails the process, with the traceback on stderr
        folder = tempfile.mkdtemp()
        script = ("from src.crash_log import install\ninstall()\nprint('about to crash')\n"
                  "raise RuntimeError('boom')\n")
        # The settings folder under folder on every OS (macOS's is ~/Library/Application Support/Dragon Warrior)
        env = {**os.environ, 'HOME': folder, 'XDG_CONFIG_HOME': folder, 'APPDATA': folder, 'SDL_VIDEODRIVER': 'dummy'}
        result = subprocess.run([sys.executable, '-c', script], cwd=project_root(), env=env, capture_output=True,
                                text=True, timeout=30)
        self.assertEqual(1, result.returncode)
        self.assertIn('RuntimeError: boom', result.stderr)
        self.assertIn('A crash log was saved to:', result.stderr)
        self.assertEqual('about to crash\n', result.stdout)
        logs = [os.path.join(root, name) for root, _, names in os.walk(folder) for name in names]
        self.assertEqual(1, len(logs))
        with open(logs[0], encoding='utf-8') as log:
            text = log.read()
        self.assertIn('RuntimeError: boom', text)
        self.assertIn('about to crash', text)
