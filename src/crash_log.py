"""The crash log (#435). Not NES.

When the game stops on an exception nothing caught, ``install``'s ``sys.excepthook`` prints the traceback as Python
always does, then writes a crash log and says where it is. The log holds the traceback, the game's version, the OS
and Python, and the last lines the game printed. It goes in the settings folder (src/paths.py user_config_dir), as
crash-<date>-<time>.log, and only the newest MAX_CRASH_LOGS are kept. A packaged build has no console to show the
traceback in (the Windows build hides its console, the macOS app has none), so the game also shows a small window that
says where the log is and how to report the crash: the system's own message box, after the game's window has closed.

There is no message box when the game runs headless (SDL_VIDEODRIVER=dummy, as in CI) or for --smoke-test, which must
fail without waiting for anyone: the exception still ends the game with exit status 1 and its traceback on stderr.
"""
import contextlib
import os
import platform
import subprocess
import sys
import tempfile
import threading
import tomllib
import traceback
from collections import deque
from collections.abc import Callable
from datetime import datetime
from types import TracebackType
from typing import Any, TextIO

from src.paths import APP_NAME, is_frozen, project_root, user_config_dir

ISSUES_URL = 'https://github.com/eforgacs-games/Dragon_Warrior/issues'
RECENT_LINES = 200  # the last lines of output a crash log keeps
MAX_CRASH_LOGS = 10
CRASH_LOG_PREFIX = 'crash-'
CRASH_LOG_SUFFIX = '.log'


class RecentOutput:
    """The last lines written to stdout and stderr, for the crash log. A stream that keeps what is written to it, line
    by line, and passes it on to the stream it replaced (none, in a build with no console)."""

    def __init__(self, lines: deque[str], stream: TextIO | None) -> None:
        self.lines = lines
        self.stream = stream
        self._partial = ''
        self._lock = threading.Lock()

    def write(self, text: str) -> int:
        with self._lock:
            *complete, self._partial = (self._partial + text).split('\n')
            self.lines.extend(complete)
        if self.stream is not None:
            with contextlib.suppress(Exception):  # a closed or broken console never stops the game
                self.stream.write(text)
        return len(text)

    def flush(self) -> None:
        if self.stream is not None:
            with contextlib.suppress(Exception):
                self.stream.flush()

    def pending(self) -> str:
        """What was written after the last newline."""
        return self._partial

    def __getattr__(self, name: str) -> Any:  # encoding, isatty, fileno...: the real stream's
        if self.stream is None:
            raise AttributeError(name)
        return getattr(self.stream, name)


_recent_lines: deque[str] = deque(maxlen=RECENT_LINES)
_outputs: list[RecentOutput] = []


def recent_lines() -> list[str]:
    """The last lines the game printed (stdout and stderr together, in order), once ``install`` has run."""
    pending = [output.pending() for output in _outputs if output.pending()]
    return list(_recent_lines) + pending


def game_version() -> str:
    """The game's version (pyproject.toml's, which the builds bundle), and whether this is a build or the source."""
    version = 'unknown'
    try:
        with open(os.path.join(project_root(), 'pyproject.toml'), 'rb') as pyproject:
            version = str(tomllib.load(pyproject)['project']['version'])
    except (OSError, KeyError, ValueError):
        pass
    return f"{version} ({'build' if is_frozen() else 'source'})"


def crash_report(exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None,
                 lines: list[str] | None = None, now: datetime | None = None) -> str:
    """The crash log's text."""
    now = datetime.now() if now is None else now
    lines = recent_lines() if lines is None else lines
    pygame = sys.modules.get('pygame')  # not imported here: the crash may have come before it was
    pygame_version = getattr(getattr(pygame, 'version', None), 'ver', 'not loaded')
    return '\n'.join([
        f"{APP_NAME} crash log",
        f"Time: {now.isoformat(timespec='seconds')}",
        f"Version: {game_version()}",
        f"OS: {platform.platform()}",
        f"Python: {platform.python_version()} ({platform.machine()}), pygame {pygame_version}",
        f"Command line: {' '.join(sys.argv)}",
        '',
        'Traceback:',
        ''.join(traceback.format_exception(exc_type, exc, tb)).rstrip('\n'),
        '',
        f"Last {len(lines)} lines of output:" if lines else 'No output before the crash.',
        *lines,
        '',
    ])


def crash_log_dir() -> str:
    return user_config_dir()


def write_crash_log(report: str, directory: str | None = None, now: datetime | None = None) -> str:
    """Write the report to a new crash log in the settings folder (or in the system's temporary folder, if the
    settings folder can't be written) and remove all but the newest MAX_CRASH_LOGS. Returns the log's path."""
    now = datetime.now() if now is None else now
    name = f"{CRASH_LOG_PREFIX}{now.strftime('%Y%m%d-%H%M%S')}{CRASH_LOG_SUFFIX}"
    for folder in (crash_log_dir() if directory is None else directory, tempfile.gettempdir()):
        path = os.path.join(folder, name)
        try:
            os.makedirs(folder, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as log:
                log.write(report)
        except OSError:
            continue
        remove_old_crash_logs(folder)
        return path
    raise OSError("no folder to write the crash log to")


def remove_old_crash_logs(folder: str, keep: int = MAX_CRASH_LOGS) -> None:
    with contextlib.suppress(OSError):
        logs = sorted(name for name in os.listdir(folder)
                      if name.startswith(CRASH_LOG_PREFIX) and name.endswith(CRASH_LOG_SUFFIX))
        for name in logs[:-keep]:
            with contextlib.suppress(OSError):
                os.remove(os.path.join(folder, name))


def crash_message(log_path: str) -> str:
    return (f"{APP_NAME} has crashed. Sorry!\n\n"
            f"A crash log was saved to:\n{log_path}\n\n"
            f"To report it, open an issue at {ISSUES_URL} and attach that file.")


def can_show_dialog(environ: Any = None, argv: list[str] | None = None) -> bool:
    """No message box when the game runs headless (CI, the release smoke test): nobody is there to close it."""
    environ = os.environ if environ is None else environ
    argv = sys.argv if argv is None else argv
    return environ.get('SDL_VIDEODRIVER') != 'dummy' and '--smoke-test' not in argv


def show_dialog(message: str, platform_name: str | None = None, run: Callable[..., Any] = subprocess.run) -> bool:
    """Show message in the system's own message box; returns whether one could be shown. The game's window is closed
    first, so a full-screen game doesn't hide the box."""
    pygame = sys.modules.get('pygame')
    if pygame is not None:
        with contextlib.suppress(Exception):
            pygame.quit()
    platform_name = sys.platform if platform_name is None else platform_name
    title = f"{APP_NAME} crashed"
    try:
        if platform_name.startswith('win'):
            import ctypes
            windll = getattr(ctypes, 'windll')  # noqa: B009 - only on Windows, where mypy on Linux can't see it
            windll.user32.MessageBoxW(None, message, title, 0x10)  # MB_ICONERROR
            return True
        if platform_name == 'darwin':
            script = ('on run argv\ndisplay dialog (item 1 of argv) with title (item 2 of argv) buttons {"OK"} '
                      'default button "OK" with icon stop\nend run')
            run(['osascript', '-e', script, message, title], check=False, timeout=600)
            return True
        for command in (['zenity', '--error', f'--title={title}', f'--text={message}', '--no-markup'],
                        ['kdialog', '--title', title, '--error', message],
                        ['xmessage', '-center', f'{title}\n\n{message}']):
            try:
                run(command, check=False, timeout=600)
                return True
            except FileNotFoundError:
                continue
    except Exception:  # noqa: BLE001 - the crash is already reported on stderr and in the log
        return False
    return False


def handle_crash(exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None) -> str | None:
    """Write the crash log and say where it is (on stderr, and in a message box unless the game is headless).
    Returns the log's path, or None if no log could be written."""
    try:
        path = write_crash_log(crash_report(exc_type, exc, tb))
    except Exception as error:  # noqa: BLE001 - never hide the original crash behind one of the crash log's
        print(f"Couldn't write a crash log: {error}", file=sys.__stderr__)
        return None
    message = crash_message(path)
    print(f"\n{message}", file=sys.stderr)
    if can_show_dialog():
        show_dialog(message)
    return path


def excepthook(exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None) -> None:
    """``sys.excepthook``: the traceback as Python prints it, then the crash log. Closing the game (SystemExit) and
    Ctrl+C aren't crashes."""
    sys.__excepthook__(exc_type, exc, tb)
    if not issubclass(exc_type, KeyboardInterrupt):
        handle_crash(exc_type, exc, tb)


def install() -> None:
    """Keep the game's recent output for the crash log, and write one if the game stops on an exception (once, at
    startup: Game's run)."""
    if _outputs:
        return
    for name in ('stdout', 'stderr'):
        output = RecentOutput(_recent_lines, getattr(sys, name))
        _outputs.append(output)
        setattr(sys, name, output)
    sys.excepthook = excepthook
