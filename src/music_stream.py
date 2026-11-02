"""
Streams chiptune music (src/chiptune.py) to the speakers: a background thread renders the emulated track a short
chunk at a time and queues each chunk on the music's mixer channel (src/sound.py music_channel), so the channel always
has the next chunk waiting and the music plays without gaps, looping for as long as the track loops, while the game's
own loop never waits for the emulator.

What plays is a list of segments: each a track, played for some seconds (a jingle, the ending) or for ever (map and
fight music, which the console's music engine loops). When a segment's time is up the next one starts in the same
chunk, so a track played once runs straight into the one that loops after it.

The game's thread starts, stops, pauses and fades the stream; the streaming thread only renders and queues. A lock
keeps them from changing the stream at the same time.

Every stream is closed, and its thread finished, before pygame or its mixer is closed (close_all_streams), however
that is done. pygame frees its mixer channels on quit, and a thread still queueing on one crashes the game: pygame's
mixer quit frees the channels' data and then closes the audio device with the GIL released, and in that time the
streaming thread, which saw the mixer running, calls Channel.get_queue, which reads the freed data without checking
(pygame 2.6 src_c/mixer.c mixer_quit and chan_get_queue). No check from this side can close that gap, so the streams
are closed before the mixer starts to quit:
- pygame.quit() closes the streams first through pygame's own hook for that, pygame.register_quit, which runs before
  pygame closes any of its modules. pygame forgets the hooks once it has run them, so a stream registers it again when
  it next plays (_close_streams_when_pygame_quits).
- pygame.mixer.quit() has no such hook, so this module replaces it, once, when it is imported, with one that closes
  the streams first (_close_streams_before_mixer_quit). Everything that calls it as pygame.mixer.quit or mixer.quit
  looks the function up when it calls it, so it gets the replacement. (pygame.quit() looks it up too, in pygame 2.6,
  but that is pygame's own business, so pygame.quit() keeps its hook as well; closing the streams twice is harmless.)
- src/waiting.py quit_pygame, the game's way out, also closes them (on_quit), and so does Python's exit (atexit).
"""
import array
import atexit
import threading
import time
import weakref
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps

from pygame import error as pygame_error, mixer, register_quit

from src.chiptune import (BYTES_PER_SAMPLE, EMULATOR_CHANNELS, ChiptuneError, Emulator, GmeLibrary, parse_track_ref)
from src.waiting import on_quit

# How much music each queued chunk holds. The channel plays one chunk while the next waits in its queue, so this is
# also how far ahead of the speakers the emulator runs, and how long a volume change can take to be heard.
CHUNK_SECONDS = 0.1
# How often the streaming thread checks whether the channel wants the next chunk: well under a chunk's length
PUMP_INTERVAL_SECONDS = 0.01
# The mixer's format the chunks are made in: signed 16-bit samples (pygame's default)
SIGNED_16_BIT = -16
# How long closing a stream waits for its thread to finish the step it is on (a step takes well under a millisecond)
THREAD_JOIN_TIMEOUT_SECONDS = 1.0

_open_streams: 'weakref.WeakSet[MusicStream]' = weakref.WeakSet()


def close_all_streams() -> None:
    """Stops every stream and finishes its thread: before pygame quits, so no thread touches a freed mixer channel."""
    for stream in list(_open_streams):
        stream.close()


on_quit(close_all_streams)
atexit.register(close_all_streams)

_pygame_quit_hook_registered = False


def _close_streams_as_pygame_quits() -> None:
    global _pygame_quit_hook_registered
    _pygame_quit_hook_registered = False  # pygame runs each hook once, then forgets it
    close_all_streams()


def _close_streams_when_pygame_quits() -> None:
    """Has the next pygame.quit() close the streams before it frees the mixer (once per quit, however often the music
    starts)."""
    global _pygame_quit_hook_registered
    if not _pygame_quit_hook_registered:
        register_quit(_close_streams_as_pygame_quits)
        _pygame_quit_hook_registered = True


def _close_streams_before_mixer_quit() -> None:
    """Makes pygame.mixer.quit() close the streams before it frees the channels (it has no hook of its own)."""
    unguarded_quit = mixer.quit
    if hasattr(unguarded_quit, '__wrapped__'):  # wrapped already (the module was imported again)
        return

    @wraps(unguarded_quit)
    def quit_after_closing_streams() -> None:
        close_all_streams()
        unguarded_quit()

    mixer.quit = quit_after_closing_streams


_close_streams_before_mixer_quit()


@dataclass(frozen=True)
class Segment:
    ref: str  # a chiptune track reference (src/chiptune.py track_ref)
    seconds: float | None = None  # None: for ever (the track loops)


class _SegmentPlayer:
    """One segment being rendered: its emulator and how many frames it has left (None: no end)."""

    def __init__(self, library: GmeLibrary, segment: Segment, sample_rate: int):
        track = parse_track_ref(segment.ref)
        if track is None:
            raise ChiptuneError(f'not a chiptune track: {segment.ref}')
        self.emulator = Emulator(library, track, sample_rate)
        self.frames_left = None if segment.seconds is None else round(segment.seconds * sample_rate)

    def render(self, frame_count: int) -> bytes:
        if self.frames_left is not None:
            frame_count = min(frame_count, self.frames_left)
            self.frames_left -= frame_count
        return self.emulator.render(frame_count) if frame_count else b''

    @property
    def finished(self) -> bool:
        return self.frames_left == 0


def convert_channels(stereo: bytes, channels: int) -> bytes:
    """Interleaved stereo samples for a mixer with `channels` channels: the left channel alone for mono, and for more
    than two, left and right on the first two with the rest silent."""
    if channels == EMULATOR_CHANNELS:
        return stereo
    samples = array.array('h', stereo)
    left, right = samples[0::2], samples[1::2]
    if channels == 1:
        return left.tobytes()
    out = array.array('h', bytes(len(left) * channels * BYTES_PER_SAMPLE))
    out[0::channels] = left
    out[1::channels] = right
    return out.tobytes()


class MusicStream:
    """The chiptune music being played on the music channel (see the module docstring)."""

    def __init__(self, library: GmeLibrary, channel: Callable[[], mixer.Channel]):
        self.library = library
        self.channel = channel
        self.volume = 1.0
        self._lock = threading.RLock()
        self._wake = threading.Event()
        self._segments: list[Segment] = []
        self._player: _SegmentPlayer | None = None
        self._sample_rate = 0
        self._mixer_channels = EMULATOR_CHANNELS
        self._rendering = False  # segments are still being rendered
        self._playing = False  # rendering, or the last chunks are still being heard
        self._paused = False
        self._fade: tuple[float, float] | None = None  # (start, seconds) of a fade out in progress
        self._thread: threading.Thread | None = None
        self._closed = False
        _open_streams.add(self)

    # The game's side

    def play(self, segments: list[Segment]) -> None:
        """Stops whatever was playing and starts the segments, the first chunk at once."""
        with self._lock:
            self._stop_locked()
            mixer_format = mixer.get_init()
            if not mixer_format or not segments:
                return
            self._closed = False  # a stream closed with pygame plays again once the mixer is back
            _close_streams_when_pygame_quits()
            sample_rate, sample_format, channels = mixer_format
            if sample_format != SIGNED_16_BIT:
                return
            self._sample_rate, self._mixer_channels = sample_rate, channels
            self._segments = list(segments)
            self._rendering = self._playing = True
            self._paused = False
            self._apply_volume()
            self._pump_locked()  # the first chunk now, so the music starts with no wait for the thread
        self._ensure_thread()
        self._wake.set()

    def stop(self) -> None:
        with self._lock:
            self._stop_locked()

    def pause(self) -> None:
        with self._lock:
            if self._playing and not self._paused:
                self._paused = True
                self.channel().pause()

    def unpause(self) -> None:
        with self._lock:
            if self._paused:
                self._paused = False
                self.channel().unpause()

    def fadeout(self, milliseconds: int) -> None:
        """Fades the music out over the given time, then stops it (pygame.mixer.music.fadeout)."""
        with self._lock:
            if not self._playing:
                return
            if milliseconds <= 0:
                self._stop_locked()
                return
            self._fade = (time.monotonic(), milliseconds / 1000)
            self._apply_volume()

    def set_volume(self, volume: float) -> None:
        with self._lock:
            self.volume = max(0.0, min(1.0, volume))
            if self._playing:
                self._apply_volume()

    def get_busy(self) -> bool:
        """Whether music is playing: rendering, or its last chunks still being heard (paused counts as playing, as for
        pygame.mixer.music)."""
        with self._lock:
            self._update_locked()
            return self._playing

    def pump(self) -> None:
        """One step of the streaming thread: ends the music if it's over, and gives the channel its next chunk if it
        has none waiting."""
        with self._lock:
            self._pump_locked()

    def close(self) -> None:
        """Stops the music and the streaming thread, and waits for the thread to finish: before the mixer goes away.
        Playing again (with the mixer running) starts a new thread."""
        with self._lock:
            self._closed = True
            self._stop_locked()
        self._wake.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(THREAD_JOIN_TIMEOUT_SECONDS)

    # Both sides, under the lock

    def _stop_locked(self) -> None:
        if self._playing and mixer.get_init():
            self.channel().stop()  # a stopped channel drops its queued chunk too
        self._close_player()
        self._segments = []
        self._rendering = self._playing = self._paused = False
        self._fade = None

    def _close_player(self) -> None:
        if self._player is not None:
            self._player.emulator.close()
            self._player = None

    def _fade_factor(self) -> float:
        if self._fade is None:
            return 1.0
        start, seconds = self._fade
        return max(0.0, 1.0 - (time.monotonic() - start) / seconds)

    def _apply_volume(self) -> None:
        self.channel().set_volume(self.volume * self._fade_factor())

    def _update_locked(self) -> None:
        """Ends the music once a fade out is over, or once the last chunk has been heard."""
        if not self._playing:
            return
        if not mixer.get_init():  # the mixer was closed under it
            self._stop_locked()
            return
        if self._fade is not None:
            if self._fade_factor() <= 0:
                self._stop_locked()
                return
            self._apply_volume()
        if not self._rendering and not self.channel().get_busy():
            self._playing = False

    def _render_chunk(self) -> bytes:
        """The next chunk of the segments, moving on to the next segment where one ends; b'' once they all have."""
        frames_wanted = round(CHUNK_SECONDS * self._sample_rate)
        chunk = b''
        while frames_wanted > 0 and (self._player is not None or self._segments):
            if self._player is None:
                self._player = _SegmentPlayer(self.library, self._segments.pop(0), self._sample_rate)
            rendered = self._player.render(frames_wanted)
            chunk += rendered
            frames_wanted -= len(rendered) // (EMULATOR_CHANNELS * BYTES_PER_SAMPLE)
            if self._player.finished:
                self._close_player()
        return chunk

    def _pump_locked(self) -> None:
        """Gives the channel its next chunk if it has none waiting."""
        self._update_locked()
        if not self._rendering:
            return
        channel = self.channel()
        if channel.get_queue() is not None:
            return
        try:
            chunk = self._render_chunk()
        except ChiptuneError as error:
            print(f"Can't play the music: {error}")
            chunk = b''
            self._segments = []
            self._close_player()
        if not chunk:
            self._rendering = False
            return
        channel.queue(mixer.Sound(buffer=convert_channels(chunk, self._mixer_channels)))
        self._apply_volume()

    # The streaming thread

    def _ensure_thread(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run, name='chiptune music', daemon=True)
            self._thread.start()

    def _run(self) -> None:
        while True:
            with self._lock:
                if self._closed:  # checked under the lock: close() may have run since the last step
                    return
                try:
                    self._pump_locked()
                except pygame_error:  # the mixer went away (the game is closing)
                    self._stop_locked()
                active = self._playing
            if active:
                time.sleep(PUMP_INTERVAL_SECONDS)
            else:
                self._wake.wait()
                self._wake.clear()
