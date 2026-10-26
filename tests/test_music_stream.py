"""src/music_stream.py: the chiptune music streamed to its mixer channel. A fake emulator and a fake channel show what
is rendered and queued, chunk by chunk; the last tests stream the real NSF through libgme to the dummy audio device."""
import array
import subprocess
import sys
import textwrap
import time
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame
from pygame import mixer

from src.chiptune import ChiptuneError, chiptune_library
from src.chiptune_soundtracks import MSC_OUTDOOR, nes_track
from src.music_stream import CHUNK_SECONDS, MusicStream, Segment, close_all_streams, convert_channels
from src.paths import project_root
from src.sound import music_channel
from src.waiting import quit_pygame
from tests.helpers import requires_libgme

SAMPLE_RATE = 44100
FRAMES_PER_CHUNK = round(CHUNK_SECONDS * SAMPLE_RATE)
BYTES_PER_FRAME = 4  # stereo, 16-bit
LOOP = 'music/dragon_warrior.nsf#5'
JINGLE = 'music/dragon_warrior.nsf#25'


class FakeEmulator:
    """Renders frames whose samples are the track's number, so each chunk shows which track it came from."""

    instances: list['FakeEmulator'] = []

    def __init__(self, _library, track, _sample_rate):
        self.number = track.number
        self.closed = False
        FakeEmulator.instances.append(self)

    def render(self, frame_count: int) -> bytes:
        return array.array('h', [self.number] * frame_count * 2).tobytes()

    def close(self) -> None:
        self.closed = True


class FakeChannel:
    """A mixer channel: one sound playing, one queued. finish_sound() plays the playing sound to its end."""

    def __init__(self):
        self.playing: list[int] | None = None  # the samples of the sound playing
        self.queued: list[int] | None = None
        self.heard: list[int] = []
        self.volume = 1.0
        self.paused = False
        self.stops = 0

    def queue(self, sound) -> None:
        samples = list(array.array('h', sound.get_raw()))
        if self.playing is None:
            self.playing = samples
        else:
            self.queued = samples

    def get_queue(self):
        return self.queued

    def get_busy(self) -> bool:
        return self.playing is not None

    def finish_sound(self) -> None:
        if self.playing is not None:
            self.heard.extend(self.playing)
        self.playing, self.queued = self.queued, None

    def stop(self) -> None:
        self.stops += 1
        self.playing = self.queued = None

    def pause(self) -> None:
        self.paused = True

    def unpause(self) -> None:
        self.paused = False

    def set_volume(self, volume: float) -> None:
        self.volume = volume


class StreamTestCase(TestCase):

    def setUp(self):
        mixer.quit()
        mixer.init(SAMPLE_RATE, -16, 2)
        self.addCleanup(mixer.quit)
        FakeEmulator.instances = []
        patch('src.music_stream.Emulator', FakeEmulator).start()
        self.addCleanup(patch.stopall)
        self.channel = FakeChannel()
        self.stream = MusicStream(MagicMock(), lambda: self.channel)
        # The tests pump the stream themselves, one step at a time, instead of its thread
        patch.object(self.stream, '_ensure_thread').start()
        self.addCleanup(self.stream.close)

    def play_out(self, chunks: int) -> None:
        """Let the channel play `chunks` sounds, the stream refilling its queue after each."""
        for _ in range(chunks):
            self.channel.finish_sound()
            self.stream.pump()
            self.stream.pump()


class TestSegments(StreamTestCase):

    def test_the_first_chunk_plays_at_once_and_the_next_waits_queued(self):
        self.stream.play([Segment(LOOP)])
        self.assertEqual([5] * FRAMES_PER_CHUNK * 2, self.channel.playing)
        self.assertIsNone(self.channel.queued)
        self.stream.pump()
        self.assertIsNotNone(self.channel.queued)
        self.stream.pump()  # a chunk already waiting: nothing more is rendered
        self.assertEqual(2 * FRAMES_PER_CHUNK, self.rendered_frames())

    def rendered_frames(self) -> int:
        playing, queued = self.channel.playing or [], self.channel.queued or []
        return (len(self.channel.heard) + len(playing) + len(queued)) // 2

    def test_music_that_loops_never_ends(self):
        self.stream.play([Segment(LOOP)])
        self.play_out(100)  # 10 s
        self.assertTrue(self.stream.get_busy())
        self.assertEqual({5}, set(self.channel.heard))

    def test_a_jingle_plays_exactly_its_length_then_the_music_ends(self):
        self.stream.play([Segment(JINGLE, 0.25)])
        self.play_out(5)
        self.assertEqual(round(0.25 * SAMPLE_RATE) * 2, len(self.channel.heard))
        self.assertFalse(self.stream.get_busy())
        self.assertTrue(FakeEmulator.instances[0].closed)

    def test_a_jingle_runs_straight_into_the_music_after_it(self):
        self.stream.play([Segment(JINGLE, 0.25), Segment(LOOP)])
        self.play_out(10)
        jingle_samples = round(0.25 * SAMPLE_RATE) * 2
        self.assertEqual([25] * jingle_samples, self.channel.heard[:jingle_samples])
        self.assertEqual({5}, set(self.channel.heard[jingle_samples:]))
        # the 0.25 s ends inside the third chunk, which carries on with the music: every chunk is full
        self.assertEqual(0, len(self.channel.heard) % (FRAMES_PER_CHUNK * 2))
        self.assertTrue(self.stream.get_busy())

    def test_playing_again_starts_over(self):
        self.stream.play([Segment(LOOP)])
        self.play_out(3)
        self.stream.play([Segment(JINGLE, 1)])
        self.assertEqual(1, self.channel.stops)
        self.assertTrue(FakeEmulator.instances[0].closed)
        self.assertEqual({25}, set(self.channel.playing or []))

    def test_without_the_mixer_nothing_plays(self):
        mixer.quit()
        self.stream.play([Segment(LOOP)])
        self.assertFalse(self.stream.get_busy())
        self.assertEqual([], FakeEmulator.instances)

    def test_a_track_that_will_not_play_ends_the_music(self):
        with patch('src.music_stream.Emulator', side_effect=ChiptuneError('bad file')), \
                patch('builtins.print') as printed:
            self.stream.play([Segment(LOOP)])
        self.assertFalse(self.stream.get_busy())
        self.assertIn('bad file', printed.call_args.args[0])

    def test_not_a_chiptune_track(self):
        with patch('builtins.print'):
            self.stream.play([Segment('music/05 Fight.mp3')])
        self.assertFalse(self.stream.get_busy())


class TestControls(StreamTestCase):

    def test_stop(self):
        self.stream.play([Segment(LOOP)])
        self.stream.pump()
        self.stream.stop()
        self.assertIsNone(self.channel.playing)
        self.assertIsNone(self.channel.queued)
        self.assertFalse(self.stream.get_busy())
        self.assertTrue(FakeEmulator.instances[0].closed)
        self.stream.pump()
        self.assertIsNone(self.channel.playing)  # nothing more is rendered

    def test_pause_and_unpause(self):
        self.stream.play([Segment(LOOP)])
        self.stream.pause()
        self.assertTrue(self.channel.paused)
        self.assertTrue(self.stream.get_busy())  # paused music still counts as playing, as pygame's does
        self.stream.unpause()
        self.assertFalse(self.channel.paused)

    def test_pause_without_music_does_nothing(self):
        self.stream.pause()
        self.assertFalse(self.channel.paused)

    def test_volume(self):
        self.stream.set_volume(0.3)
        self.stream.play([Segment(LOOP)])
        self.assertAlmostEqual(0.3, self.channel.volume)
        self.stream.set_volume(2)
        self.assertEqual(1.0, self.channel.volume)
        self.stream.set_volume(-1)
        self.assertEqual(0.0, self.channel.volume)

    def test_fadeout(self):
        self.stream.set_volume(0.8)
        clock = [100.0]
        with patch('src.music_stream.time.monotonic', side_effect=lambda: clock[0]):
            self.stream.play([Segment(LOOP)])
            self.stream.fadeout(1000)
            clock[0] += 0.25
            self.stream.pump()
            self.assertAlmostEqual(0.6, self.channel.volume)
            clock[0] += 0.5
            self.stream.pump()
            self.assertAlmostEqual(0.2, self.channel.volume)
            clock[0] += 0.25
            self.stream.pump()
        self.assertFalse(self.stream.get_busy())
        self.assertIsNone(self.channel.playing)

    def test_fadeout_of_nothing_or_at_once(self):
        self.stream.fadeout(500)
        self.assertFalse(self.stream.get_busy())
        self.stream.play([Segment(LOOP)])
        self.stream.fadeout(0)
        self.assertFalse(self.stream.get_busy())

    def test_the_mixer_closing_under_it_ends_the_music(self):
        self.stream.play([Segment(LOOP)])
        mixer.quit()
        self.assertFalse(self.stream.get_busy())


class TestClosing(StreamTestCase):

    def test_close_stops_the_music_and_the_pump_does_nothing_after(self):
        self.stream.play([Segment(LOOP)])
        self.stream.close()
        self.assertFalse(self.stream.get_busy())
        self.channel.finish_sound()
        self.stream.pump()
        self.assertIsNone(self.channel.playing)

    def test_close_all_streams_before_pygame_quits(self):
        self.stream.play([Segment(LOOP)])
        with patch('src.waiting.pygame_quit') as pygame_quit:
            quit_pygame()
        pygame_quit.assert_called_once()
        self.assertFalse(self.stream.get_busy())

    def test_a_closed_stream_plays_again_with_the_mixer_back(self):
        self.stream.play([Segment(LOOP)])
        close_all_streams()
        self.stream.play([Segment(JINGLE, 1)])
        self.assertTrue(self.stream.get_busy())


# Run in a process of its own, so a crash fails the test rather than killing pytest: the game's music streaming while
# the window is closed (quit_game), several times over
QUIT_WHILE_STREAMING = textwrap.dedent("""
    import os, sys, time
    os.environ['SDL_VIDEODRIVER'] = os.environ['SDL_AUDIODRIVER'] = 'dummy'
    sys.path.insert(0, sys.argv[1])
    import pygame
    from src.chiptune_soundtracks import MSC_OUTDOOR, nes_track
    from src.music_player import MusicPlayer
    from src.waiting import quit_game, quit_pygame
    for _ in range(5):
        pygame.init()
        player = MusicPlayer({'MUSIC_ENABLED': True, 'SOUND_ENABLED': False})
        player.load_and_play_music(nes_track(MSC_OUTDOOR))
        time.sleep(0.2)
        assert player.music_busy()
        quit_pygame()
        time.sleep(0.05)
    pygame.init()
    MusicPlayer({'MUSIC_ENABLED': True, 'SOUND_ENABLED': False}).load_and_play_music(nes_track(MSC_OUTDOOR))
    time.sleep(0.2)
    quit_game()
""")


@requires_libgme
class TestQuitWhileStreaming(TestCase):

    def test_the_game_closes_cleanly_while_the_music_streams(self):
        result = subprocess.run([sys.executable, '-c', QUIT_WHILE_STREAMING, project_root()], capture_output=True,
                                text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)


class TestChannels(TestCase):

    def test_stereo_stays_stereo(self):
        stereo = array.array('h', [1, 2, 3, 4]).tobytes()
        self.assertEqual(stereo, convert_channels(stereo, 2))

    def test_mono_takes_the_left_channel(self):
        stereo = array.array('h', [1, 2, 3, 4]).tobytes()
        self.assertEqual([1, 3], list(array.array('h', convert_channels(stereo, 1))))

    def test_more_channels_get_left_and_right_and_silence(self):
        stereo = array.array('h', [1, 2, 3, 4]).tobytes()
        self.assertEqual([1, 2, 0, 0, 3, 4, 0, 0], list(array.array('h', convert_channels(stereo, 4))))


@requires_libgme
class TestRealStream(TestCase):
    """The NSF through libgme, streamed by the thread to the music channel of the dummy audio device."""

    def setUp(self):
        pygame.mixer.quit()
        pygame.mixer.init(SAMPLE_RATE, -16, 2, 1024)
        self.addCleanup(pygame.mixer.quit)
        library = chiptune_library()
        assert library is not None
        self.stream = MusicStream(library, music_channel)
        self.addCleanup(self.stream.close)

    def test_streams_on_the_music_channel_while_the_game_goes_on(self):
        self.stream.play([Segment(nes_track(MSC_OUTDOOR))])
        time.sleep(0.5)
        self.assertTrue(self.stream.get_busy())
        self.assertTrue(music_channel().get_busy())
        self.stream.stop()
        self.assertFalse(music_channel().get_busy())

    def test_a_jingle_ends_on_its_own(self):
        self.stream.play([Segment(nes_track(MSC_OUTDOOR), 0.3)])
        started = time.monotonic()
        while self.stream.get_busy() and time.monotonic() - started < 5:
            time.sleep(0.01)
        self.assertFalse(self.stream.get_busy())
        self.assertLess(time.monotonic() - started, 2)
