import sys

from pygame import mixer

from src.chiptune import chiptune_library, is_chiptune, tagged_length_seconds
from src.chiptune_soundtracks import is_clip
from src.music_stream import MusicStream, Segment
from src.sound import music_channel
from src.waiting import POLL_INTERVAL_MS, game_ticks, wait


class MusicPlayer:
    """The one place that plays music, and the one place that decides whether music plays (config["MUSIC_ENABLED"]).
    Everything else asks it to play, stop or wait for music. With the music off, every method leaves the mixer alone,
    so the game is silent; play_clip and wait_for_music_end still keep the clip's timing (see play_clip). Sound effects
    are separate (src/sound.py).

    Music comes two ways, chosen by what it is asked to play:
    - a chiptune track (the NES and SFC soundtracks, src/chiptune.py), emulated and streamed to a mixer channel
      (src/music_stream.py). A map or fight track loops for ever, as the console's music engine loops it; a clip
      plays for its tagged length.
    - an mp3 (the orchestral soundtrack), streamed from the file by pygame.mixer.music.
    Starting either stops the other. Without libgme, a chiptune clip is silent but keeps its timing, as with the music
    off (the map music falls back to the orchestral soundtrack: src/directories.py)."""

    def __init__(self, config):
        self.music_enabled = config["MUSIC_ENABLED"]
        self.sound_enabled = config["SOUND_ENABLED"]
        self.music_volume = 0.5
        self._clip_end_ticks: float | None = None  # when a clip that isn't heard would end (game time)
        self._stream: MusicStream | None = None

    @property
    def stream(self) -> MusicStream | None:
        """The chiptune music stream, made the first time it's needed; None without libgme."""
        if self._stream is None:
            library = chiptune_library()
            if library is not None:
                self._stream = MusicStream(library, music_channel)
                self._stream.set_volume(self.music_volume)
        return self._stream

    def load_and_play_music(self, path, loop=-1, then_loop: str | None = None):
        """NES InitMusicSFX with a music number: whatever was playing stops and the new music starts from the beginning
        (even when it's the same music). With then_loop, path plays once and then_loop follows it and loops, the way
        the NES's fight music runs into its loop (MSC_ENTR_FGHT falls through into SQ1Fight). loop=0 plays it once.

        A chiptune track loops by itself, as on the console: the NES's MSC_ENTR_FGHT track already runs into the fight
        loop, so only a clip (src/chiptune_soundtracks.py), which ends, is followed by then_loop."""
        if not self.music_enabled:
            return
        self.stop_music()  # also drops anything queued
        if is_chiptune(path):
            self._play_chiptune(self._chiptune_segments(path, loop, then_loop))
            return
        mixer.music.load(path)
        mixer.music.set_volume(self.music_volume)
        if then_loop is None or then_loop == path:
            mixer.music.play(loop)
        else:
            mixer.music.play()
            mixer.music.queue(then_loop, loops=-1)

    @staticmethod
    def _chiptune_segments(path: str, loop: int, then_loop: str | None) -> list[Segment]:
        if loop == 0:
            return [Segment(path, played_once_seconds(path))]
        if then_loop is None or then_loop == path or not is_clip(path):
            return [Segment(path)]
        return [Segment(path, played_once_seconds(path)), Segment(then_loop)]

    def _play_chiptune(self, segments: list[Segment]) -> bool:
        """Plays chiptune segments; False if they can't be heard (no libgme)."""
        stream = self.stream
        if stream is None:
            return False
        stream.play(segments)
        return True

    def play_clip(self, path: str) -> None:
        """NES InitMusicSFX with a music clip (the victory and level-up fanfares, the harp, the flute, the curse,
        Gwaelin's love, the inn): the clip takes the music's place, whatever was playing stops, and it plays once. It
        returns at once, so the game carries on (the battle's experience and gold lines print over the victory music);
        wait_for_music_end waits for the clip to finish.

        The NES music engine has one music track, so a clip can only be cut off by the next InitMusicSFX with music
        (the next clip, the map music, the next fight's music). Playing it as the music, not as a Sound on a
        mixer channel of its own, gives it that one slot: no sound effect can take its place or leave it without a free
        channel. With the music off (or a chiptune clip without libgme), nothing plays, but wait_for_music_end still
        waits as long as the clip lasts."""
        self.stop_music()
        self._clip_end_ticks = None
        if self.music_enabled:
            if not is_chiptune(path):
                mixer.music.load(path)
                mixer.music.set_volume(self.music_volume)
                mixer.music.play()
                return
            if self._play_chiptune([Segment(path, played_once_seconds(path))]):
                return
        self._clip_end_ticks = game_ticks() + clip_length_ms(path)

    def wait_for_music_end(self, config: dict) -> None:
        """NES WaitForMusicEnd (Bank01): wait until the clip play_clip started has finished. With the music on, that
        is when the music stops, whatever the game speed (keys 1 to 5 only make the polling faster), since the clip
        plays at its normal length. With the music off, it waits out the rest of the clip's length, in game time like
        any other wait (shorter at a higher game speed). Closing the window quits during either wait
        (src/waiting.py); NO_WAIT skips them."""
        clip_end_ticks, self._clip_end_ticks = self._clip_end_ticks, None
        if config.get('NO_WAIT'):
            return
        if clip_end_ticks is not None:
            wait(max(0, clip_end_ticks - game_ticks()), config)
        elif self.music_enabled:
            while self.music_busy():
                wait(POLL_INTERVAL_MS)

    def music_busy(self) -> bool:
        """Whether any music is playing (the chiptune stream or pygame's music)."""
        stream = self._stream
        return bool(mixer.music.get_busy() or (stream is not None and stream.get_busy()))

    def play_until_end(self, path: str, config: dict) -> None:
        """NES InitMusicSFX with a music clip, then WaitForMusicEnd: the clip replaces the music, plays once, and the
        game waits until it has finished (play_clip, then wait_for_music_end)."""
        self.play_clip(path)
        self.wait_for_music_end(config)

    def stop_music(self):
        if self.music_enabled:
            mixer.music.stop()
            if self._stream is not None:
                self._stream.stop()

    def pause_music(self):
        if self.music_enabled:
            mixer.music.pause()
            if self._stream is not None:
                self._stream.pause()

    def unpause_music(self):
        if self.music_enabled:
            mixer.music.unpause()
            if self._stream is not None:
                self._stream.unpause()

    def fadeout_music(self, fadeout_time):
        if self.music_enabled:
            mixer.music.fadeout(fadeout_time)
            if self._stream is not None:
                self._stream.fadeout(fadeout_time)

    def set_music_volume(self, volume):
        self.music_volume = volume
        if self.music_enabled:
            mixer.music.set_volume(self.music_volume)
            if self._stream is not None:
                self._stream.set_volume(self.music_volume)

    def get_music_volume(self):
        return self.music_volume


# How long a chiptune track played once lasts when its length isn't tagged (a playlist that can't be read, an SPC with
# no ID666 length): about as long as the longer jingles, so the game never waits for ever on one (the smoke test checks
# every clip has its length)
UNTAGGED_CLIP_SECONDS = 6.0


def played_once_seconds(path: str) -> float:
    """How long a chiptune track plays when it plays once: its tagged length, or UNTAGGED_CLIP_SECONDS (said on
    stderr) when it has none."""
    seconds = tagged_length_seconds(path)
    if seconds is None:
        print(f"No length is tagged for {path}: it plays for {UNTAGGED_CLIP_SECONDS} s", file=sys.stderr)
        return UNTAGGED_CLIP_SECONDS
    return seconds


def clip_length_ms(path: str) -> float:
    """How long a clip plays, in milliseconds: a chiptune track's tagged length (src/chiptune.py), or how long an audio
    file plays (0 if the mixer isn't running)."""
    if is_chiptune(path):
        return played_once_seconds(path) * 1000
    if not mixer.get_init():
        return 0
    return mixer.Sound(path).get_length() * 1000
