"""
Chiptune music: the NES soundtrack from the game's NSF and the Super Famicom one from SPC files, played by emulating
the consoles' sound hardware with libgme (Game_Music_Emu, https://github.com/libgme/game-music-emu) instead of from
recordings. src/music_stream.py streams what the emulator renders; src/music_player.py decides when.

A chiptune track is named by a "track reference", a string so it fits wherever the game keeps a music file's path (a
map's music_file_path, Directories): the file's path, then '#' and the track number for a file with several tracks
(an NSF), e.g. '.../dragon_warrior.nsf#14'. A file with one track (an SPC) is named by its path alone. Track numbers
count from 1, as the playlist and the NES's music numbers do; libgme counts from 0.

libgme is a C library loaded with ctypes: a build bundles it next to the game (dragon_warrior.spec), and from source it
is the system's (README: Installing libgme). Without it, chiptune_library() is None and the game says so once; the
track lengths (tagged_length_seconds) are read from the files themselves, so they need no libgme.
"""
import ctypes
import ctypes.util
import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cache
from os.path import dirname, join, splitext

from src.paths import is_frozen, project_root

NSF_EXTENSION = '.nsf'
SPC_EXTENSION = '.spc'
CHIPTUNE_EXTENSIONS = (NSF_EXTENSION, SPC_EXTENSION)
TRACK_SEPARATOR = '#'

# The emulator renders interleaved stereo, signed 16-bit samples
EMULATOR_CHANNELS = 2
BYTES_PER_SAMPLE = 2

# The names libgme goes by on each platform: the shared library a CMake build installs, then the names package
# managers use (Debian's libgme0, Homebrew's game-music-emu, MSYS2's mingw-w64-game-music-emu)
LIBRARY_FILE_NAMES = {
    'linux': ('libgme.so.0', 'libgme.so'),
    'darwin': ('libgme.0.dylib', 'libgme.dylib'),
    'win32': ('gme.dll', 'libgme.dll', 'libgme-0.dll'),
}
# Where a package manager puts libraries that macOS's dlopen doesn't search by itself (Homebrew on Apple silicon, then
# on Intel, then MacPorts)
MACOS_LIBRARY_DIRS = ('/opt/homebrew/lib', '/usr/local/lib', '/opt/local/lib')

# An SPC file's ID666 tag (the SPC file format, at 0x23 and 0x2E): the tag is there when the byte at 0x23 is 26, and
# the song's length is 3 characters of seconds at 0xA9 (the text format) or a 24-bit number of seconds (the binary one)
ID666_PRESENT_OFFSET = 0x23
ID666_PRESENT = 26
ID666_LENGTH_OFFSET = 0xA9
ID666_LENGTH_SIZE = 3

# A playlist line: "file::NSF,track,title,length,loop,fade" (the title may itself hold escaped commas, so the numbers
# are read from the ends of the line)
PLAYLIST_TRACK_FIELD = 1
PLAYLIST_LENGTH_FIELD = -3


@dataclass(frozen=True)
class ChiptuneTrack:
    path: str
    number: int = 1  # counted from 1


def track_ref(path: str, number: int = 1) -> str:
    """The reference to track `number` (from 1) of a chiptune file; an SPC (one track) is named by its path alone."""
    if splitext(path)[1].lower() == SPC_EXTENSION:
        return path
    return f'{path}{TRACK_SEPARATOR}{number}'


def parse_track_ref(ref: str) -> ChiptuneTrack | None:
    """The chiptune track a reference names, or None if it names no chiptune file (an mp3, say)."""
    path, separator, number = ref.rpartition(TRACK_SEPARATOR)
    if not separator or not number.isdigit():
        path, number = ref, '1'
    if splitext(path)[1].lower() not in CHIPTUNE_EXTENSIONS:
        return None
    return ChiptuneTrack(path, int(number))


def is_chiptune(ref: str) -> bool:
    return parse_track_ref(ref) is not None


# --------------------------------------------------------------------------------------------------------------------
# Track lengths
# --------------------------------------------------------------------------------------------------------------------

def parse_duration(text: str) -> float:
    """Seconds from a playlist duration: '0:01:00.897', '1:14.185' or '2.5'."""
    seconds = 0.0
    for part in text.strip().split(':'):
        seconds = seconds * 60 + float(part)
    return seconds


def playlist_path(nsf_path: str) -> str:
    """An NSF's playlist (.m3u), next to it with the same name."""
    return splitext(nsf_path)[0] + '.m3u'


@cache
def playlist_lengths(path: str) -> dict[int, float]:
    """The length of each track (by number, from 1) an NSF playlist tags; comment lines (#) and blank ones skipped."""
    lengths = {}
    with open(path, encoding='utf-8') as playlist:
        for line in playlist:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            fields = line.split(',')
            lengths[int(fields[PLAYLIST_TRACK_FIELD])] = parse_duration(fields[PLAYLIST_LENGTH_FIELD])
    return lengths


def spc_tagged_length(data: bytes) -> float | None:
    """The song length an SPC file's ID666 tag gives, in seconds; None if it has no tag or no length."""
    if len(data) <= ID666_LENGTH_OFFSET + ID666_LENGTH_SIZE or data[ID666_PRESENT_OFFSET] != ID666_PRESENT:
        return None
    field = data[ID666_LENGTH_OFFSET:ID666_LENGTH_OFFSET + ID666_LENGTH_SIZE]
    text = field.split(b'\0')[0]
    if text.isdigit():
        seconds = int(text)
    elif all(byte in b'\0 ' or chr(byte).isdigit() for byte in field):
        return None  # a text tag with no length
    else:
        seconds = int.from_bytes(field, 'little')
    return float(seconds) or None


@cache
def tagged_length_seconds(ref: str) -> float | None:
    """How long a track plays when it plays once (a jingle, the ending): the NSF playlist's length for an NSF track,
    the ID666 tag's for an SPC; None if neither tags one."""
    track = parse_track_ref(ref)
    if track is None:
        return None
    if splitext(track.path)[1].lower() == NSF_EXTENSION:
        try:
            return playlist_lengths(playlist_path(track.path)).get(track.number)
        except OSError:
            return None
    try:
        return spc_tagged_length(read_file(track.path))
    except OSError:
        return None


@cache
def read_file(path: str) -> bytes:
    with open(path, 'rb') as chiptune_file:
        return chiptune_file.read()


# --------------------------------------------------------------------------------------------------------------------
# The libgme library
# --------------------------------------------------------------------------------------------------------------------

def platform_key(platform: str | None = None) -> str:
    platform = sys.platform if platform is None else platform
    if platform.startswith('win'):
        return 'win32'
    if platform == 'darwin':
        return 'darwin'
    return 'linux'


def bundled_library_dirs() -> list[str]:
    """Where a PyInstaller build keeps libgme: next to the game's code (sys._MEIPASS) and next to its executable."""
    if not is_frozen():
        return []
    return list(dict.fromkeys([project_root(), dirname(os.path.realpath(sys.executable))]))


def library_candidates(platform: str | None = None) -> Iterator[str]:
    """What to try to load libgme as, in order: a bundled copy (a build), then the system's by name, then what
    ctypes.util.find_library finds."""
    key = platform_key(platform)
    names = LIBRARY_FILE_NAMES[key]
    for directory in bundled_library_dirs():
        for name in names:
            yield join(directory, name)
    yield from names
    if key == 'darwin':
        for directory in MACOS_LIBRARY_DIRS:
            for name in names:
                yield join(directory, name)
    found = ctypes.util.find_library('gme')
    if found:
        yield found


_ERROR = ctypes.c_char_p  # libgme returns NULL on success, or an error message
_EMULATOR = ctypes.c_void_p  # Music_Emu*


class GmeLibrary:
    """The few libgme functions the game uses, with their C signatures (gme.h)."""

    def __init__(self, library: ctypes.CDLL, path: str):
        self.library = library
        self.path = path  # what it was loaded as: a bundled copy's full path, or the system's by name
        self._declare('gme_open_data', _ERROR, ctypes.c_void_p, ctypes.c_long, ctypes.POINTER(_EMULATOR), ctypes.c_int)
        self._declare('gme_track_count', ctypes.c_int, _EMULATOR)
        self._declare('gme_start_track', _ERROR, _EMULATOR, ctypes.c_int)
        self._declare('gme_play', _ERROR, _EMULATOR, ctypes.c_int, ctypes.POINTER(ctypes.c_short))
        self._declare('gme_tell', ctypes.c_int, _EMULATOR)
        self._declare('gme_track_ended', ctypes.c_int, _EMULATOR)
        self._declare('gme_ignore_silence', None, _EMULATOR, ctypes.c_int)
        self._declare('gme_delete', None, _EMULATOR)
        # libgme 0.6.2 and later: without it, a track with a tagged length fades out and ends at that length
        self.has_playback_limit = hasattr(library, 'gme_set_autoload_playback_limit')
        if self.has_playback_limit:
            self._declare('gme_set_autoload_playback_limit', None, _EMULATOR, ctypes.c_int)

    def _declare(self, name: str, restype, *argtypes) -> None:
        function = getattr(self.library, name)
        function.restype = restype
        function.argtypes = argtypes

    def __getattr__(self, name: str):
        return getattr(self.library, name)


def load_library(candidates: Iterator[str]) -> GmeLibrary | None:
    """The first candidate that loads as libgme, or None."""
    for candidate in candidates:
        try:
            return GmeLibrary(ctypes.CDLL(candidate), candidate)
        except (OSError, AttributeError):  # not there, or not libgme
            continue
    return None


@cache
def chiptune_library() -> GmeLibrary | None:
    """libgme, loaded once; None, said once on stderr, if it can't be found."""
    library = load_library(library_candidates())
    if library is None:
        print("libgme (Game_Music_Emu) wasn't found, so the NES and SFC soundtracks can't play: the orchestral "
              "music plays instead. See the README's 'Installing libgme' to install it.", file=sys.stderr)
    return library


def chiptune_available() -> bool:
    return chiptune_library() is not None


class ChiptuneError(Exception):
    pass


class Emulator:
    """One chiptune track being played: the console's sound hardware, emulated, rendering it from the start."""

    def __init__(self, library: GmeLibrary, track: ChiptuneTrack, sample_rate: int):
        self.library = library
        # libgme may keep reading the file's bytes after loading them (an SPC's), so they live as long as it does
        self._data = read_file(track.path)
        handle = _EMULATOR()
        self._check(library.gme_open_data(self._data, len(self._data), ctypes.byref(handle), sample_rate))
        self.handle = handle
        # The game decides when a track ends: it loops on (the console's music engine repeats it) unless played once,
        # and then stops after its tagged length (tagged_length_seconds). So no fading out at the tagged length, and
        # no ending a track after a long silence.
        if library.has_playback_limit:
            library.gme_set_autoload_playback_limit(handle, 0)
        library.gme_ignore_silence(handle, 1)
        self._check(library.gme_start_track(handle, track.number - 1))

    def _check(self, error: bytes | None) -> None:
        if error:
            raise ChiptuneError(error.decode(errors='replace'))

    def render(self, frame_count: int) -> bytes:
        """The next frame_count stereo frames of the track, as interleaved signed 16-bit samples."""
        sample_count = frame_count * EMULATOR_CHANNELS
        buffer = (ctypes.c_short * sample_count)()
        self._check(self.library.gme_play(self.handle, sample_count, buffer))
        return bytes(buffer)

    def close(self) -> None:
        if self.handle:
            self.library.gme_delete(self.handle)
            self.handle = _EMULATOR()
