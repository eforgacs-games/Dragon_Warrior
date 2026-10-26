"""src/chiptune.py: track references, the tagged lengths, loading libgme (from source, from a build, or not at all)
and the emulator itself, on the game's own NSF and SPC files."""
import array
import contextlib
import io
import os
import sys
import tempfile
from os.path import join
from unittest import TestCase
from unittest.mock import MagicMock, patch

from src import chiptune
from src.chiptune import (ChiptuneError, ChiptuneTrack, Emulator, chiptune_library, is_chiptune, library_candidates,
                          load_library, parse_duration, parse_track_ref, playlist_lengths, playlist_path,
                          spc_tagged_length, tagged_length_seconds, track_ref)
from src.chiptune_soundtracks import (MSC_DUNGEON1, MSC_END, MSC_INN, MSC_OUTDOOR, MSC_VICTORY, nes_nsf_path,
                                      nes_track, sfc_track)
from tests.helpers import requires_libgme

SAMPLE_RATE = 44100
STEREO = 2


def render_seconds(ref: str, seconds: float) -> array.array:
    """The first seconds of a track, from the real libgme."""
    library = chiptune_library()
    assert library is not None
    track = parse_track_ref(ref)
    assert track is not None
    emulator = Emulator(library, track, SAMPLE_RATE)
    try:
        return array.array('h', emulator.render(round(seconds * SAMPLE_RATE)))
    finally:
        emulator.close()


def loudest(samples: array.array, from_seconds: float, to_seconds: float) -> int:
    window = samples[round(from_seconds * SAMPLE_RATE) * STEREO:round(to_seconds * SAMPLE_RATE) * STEREO]
    return max(map(abs, window), default=0)


class TestTrackReferences(TestCase):

    def test_an_nsf_track_is_its_file_and_number(self):
        ref = track_ref('music/dragon_warrior.nsf', 14)
        self.assertEqual('music/dragon_warrior.nsf#14', ref)
        self.assertEqual(ChiptuneTrack('music/dragon_warrior.nsf', 14), parse_track_ref(ref))

    def test_an_spc_is_its_path(self):
        self.assertEqual('music/victory.spc', track_ref('music/victory.spc'))
        self.assertEqual(ChiptuneTrack('music/victory.spc', 1), parse_track_ref('music/victory.spc'))

    def test_a_recording_is_no_chiptune_track(self):
        for path in ('music/05 Fight.mp3', 'music/odd#name.mp3', 'sfx/text_beep.wav'):
            with self.subTest(path=path):
                self.assertIsNone(parse_track_ref(path))
                self.assertFalse(is_chiptune(path))
        self.assertTrue(is_chiptune(nes_track(MSC_OUTDOOR)))


class TestTaggedLengths(TestCase):

    def test_playlist_durations(self):
        self.assertEqual(74.185, parse_duration('0:01:14.185'))
        self.assertEqual(2.45, parse_duration('0:00:02.45'))
        self.assertEqual(62.5, parse_duration('1:02.5'))
        self.assertEqual(3, parse_duration('3'))

    def test_the_nsf_playlist(self):
        lengths = playlist_lengths(playlist_path(nes_nsf_path()))
        self.assertEqual(2.0, lengths[MSC_VICTORY])  # "Battle Victory,0:00:02"
        self.assertEqual(121.355, lengths[MSC_END])
        # the inn's jingle isn't in the original playlist: the game's own line, measured
        self.assertEqual(2.95, lengths[MSC_INN])
        # a title with a comma in it ("Town,\ Game Selection") still gives the right numbers
        self.assertEqual(50.65, lengths[4])

    def test_tagged_length_of_a_track(self):
        self.assertEqual(2.0, tagged_length_seconds(nes_track(MSC_VICTORY)))
        self.assertEqual(2.0, tagged_length_seconds(sfc_track('victory.spc')))  # its ID666 tag
        self.assertEqual(7.0, tagged_length_seconds(sfc_track('thou_hast_died.spc')))
        self.assertIsNone(tagged_length_seconds('music/05 Fight.mp3'))
        self.assertIsNone(tagged_length_seconds(track_ref('no/such/file.nsf', 1)))

    def test_id666_text_and_binary_lengths(self):
        def spc_with_length_field(field: bytes) -> bytes:
            data = bytearray(0x200)
            data[chiptune.ID666_PRESENT_OFFSET] = chiptune.ID666_PRESENT
            data[chiptune.ID666_LENGTH_OFFSET:chiptune.ID666_LENGTH_OFFSET + 3] = field
            return bytes(data)
        self.assertEqual(289.0, spc_tagged_length(spc_with_length_field(b'289')))
        self.assertEqual(7.0, spc_tagged_length(spc_with_length_field(b'7\0\0')))
        self.assertEqual(300.0, spc_tagged_length(spc_with_length_field((300).to_bytes(3, 'little'))))
        self.assertIsNone(spc_tagged_length(spc_with_length_field(b'\0\0\0')))
        untagged = bytearray(spc_with_length_field(b'289'))
        untagged[chiptune.ID666_PRESENT_OFFSET] = 27
        self.assertIsNone(spc_tagged_length(bytes(untagged)))
        self.assertIsNone(spc_tagged_length(b'too short'))


class TestLibraryLoading(TestCase):

    def setUp(self):
        chiptune_library.cache_clear()
        self.addCleanup(chiptune_library.cache_clear)

    def freeze(self, meipass: str) -> None:
        for frozen_patch in (patch.object(sys, 'frozen', True, create=True),
                             patch.object(sys, '_MEIPASS', meipass, create=True),
                             patch.object(sys, 'executable', join(meipass, 'DragonWarrior'))):
            frozen_patch.start()
            self.addCleanup(frozen_patch.stop)

    def test_from_source_the_systems_library_by_name(self):
        with patch('ctypes.util.find_library', return_value=None):
            self.assertEqual(['libgme.so.0', 'libgme.so'], list(library_candidates('linux')))
            self.assertEqual(['gme.dll', 'libgme.dll', 'libgme-0.dll'], list(library_candidates('win32')))
            macos = list(library_candidates('darwin'))
        self.assertEqual(['libgme.0.dylib', 'libgme.dylib'], macos[:2])
        self.assertIn('/opt/homebrew/lib/libgme.0.dylib', macos)

    def test_what_find_library_finds_comes_last(self):
        with patch('ctypes.util.find_library', side_effect=lambda name: f'/found/{name}.dll'):
            self.assertEqual(['/found/gme.dll', '/found/libgme.dll'], list(library_candidates('win32'))[-2:])

    def test_a_build_loads_its_bundled_copy_first(self):
        with tempfile.TemporaryDirectory() as meipass:
            self.freeze(meipass)
            candidates = list(library_candidates('linux'))
            self.assertEqual(join(meipass, 'libgme.so.0'), candidates[0])
            bundled = join(meipass, 'libgme.so.0')
            open(bundled, 'wb').close()
            with patch('src.chiptune.ctypes.CDLL', return_value=MagicMock()) as cdll:
                library = load_library(iter(candidates))
        assert library is not None
        self.assertEqual(bundled, library.path)
        cdll.assert_called_once_with(bundled)

    def test_a_missing_bundled_file_is_skipped(self):
        with tempfile.TemporaryDirectory() as meipass, \
                patch('src.chiptune.ctypes.CDLL', return_value=MagicMock()) as cdll:
            library = load_library(iter([join(meipass, 'libgme.so.0'), 'libgme.so.0']))
        assert library is not None
        self.assertEqual('libgme.so.0', library.path)
        cdll.assert_called_once_with('libgme.so.0')

    def test_a_library_that_is_not_libgme_is_skipped(self):
        not_libgme = MagicMock(spec=[])  # has none of libgme's functions
        with patch('src.chiptune.ctypes.CDLL', side_effect=[OSError('not found'), not_libgme, MagicMock()]):
            library = load_library(iter(['missing', 'other', 'libgme']))
        assert library is not None
        self.assertEqual('libgme', library.path)

    def test_without_libgme_the_game_says_so_once(self):
        stderr = io.StringIO()
        with patch('src.chiptune.load_library', return_value=None), contextlib.redirect_stderr(stderr):
            self.assertIsNone(chiptune_library())
            self.assertIsNone(chiptune_library())
            self.assertFalse(chiptune.chiptune_available())
        self.assertEqual(1, stderr.getvalue().count("wasn't found"))
        self.assertIn('orchestral', stderr.getvalue())


@requires_libgme
class TestEmulator(TestCase):

    def test_renders_the_nsf(self):
        samples = render_seconds(nes_track(MSC_OUTDOOR), 1)
        self.assertEqual(SAMPLE_RATE * STEREO, len(samples))
        self.assertGreater(loudest(samples, 0, 1), 1000)

    def test_music_loops_on_past_its_tagged_length(self):
        # The console's music engine loops a map's music: the playlist's 27 s for the first dungeon floor is one time
        # through, and the emulator goes on playing it
        tagged = tagged_length_seconds(nes_track(MSC_DUNGEON1))
        assert tagged is not None
        samples = render_seconds(nes_track(MSC_DUNGEON1), tagged + 8)
        self.assertGreater(loudest(samples, tagged + 3, tagged + 8), 1000)

    def test_an_spc_loops_on_past_its_tagged_length(self):
        floor = sfc_track('dark_dungeon_floor_1.spc')
        tagged = tagged_length_seconds(floor)
        assert tagged is not None
        samples = render_seconds(floor, tagged + 8)
        self.assertGreater(loudest(samples, tagged + 3, tagged + 8), 500)

    def test_a_jingle_is_over_by_its_tagged_length(self):
        # The NES victory fanfare's last note is over before the playlist's 2 s, and the engine plays nothing after it
        samples = render_seconds(nes_track(MSC_VICTORY), 4)
        self.assertGreater(loudest(samples, 0, 1), 1000)
        self.assertLess(loudest(samples, 2, 4), 50)

    def test_each_play_starts_the_track_from_its_beginning(self):
        # Each play is its own emulator, from the track's start: the same samples every time
        self.assertEqual(render_seconds(nes_track(MSC_OUTDOOR), 0.5), render_seconds(nes_track(MSC_OUTDOOR), 0.5))

    def test_a_file_that_is_not_music(self):
        with tempfile.NamedTemporaryFile(suffix='.spc', delete=False) as not_music:
            not_music.write(b'not an spc file at all')
        self.addCleanup(os.remove, not_music.name)
        library = chiptune_library()
        assert library is not None
        with self.assertRaises(ChiptuneError):
            Emulator(library, ChiptuneTrack(not_music.name), SAMPLE_RATE)

    def test_a_track_the_file_does_not_have(self):
        library = chiptune_library()
        assert library is not None
        with self.assertRaises(ChiptuneError):
            Emulator(library, ChiptuneTrack(nes_nsf_path(), 99), SAMPLE_RATE)
