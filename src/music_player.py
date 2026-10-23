from pygame import mixer

from src.waiting import POLL_INTERVAL_MS, game_ticks, wait


class MusicPlayer:
    """The one place that talks to pygame.mixer.music, and the one place that decides whether music plays
    (config["MUSIC_ENABLED"]). Everything else asks it to play, stop or wait for music. With the music off, every
    method leaves pygame's music alone, so the game is silent; play_clip and wait_for_music_end still keep the clip's
    timing (see play_clip). Sound effects are separate (src/sound.py)."""

    def __init__(self, config):
        self.music_enabled = config["MUSIC_ENABLED"]
        self.sound_enabled = config["SOUND_ENABLED"]
        self.orchestra_music_enabled = config["ORCHESTRA_MUSIC_ENABLED"]
        self.music_volume = 0.5
        self._clip_end_ticks: float | None = None  # when a clip started with the music off would end (game time)

    def load_and_play_music(self, path, loop=-1):
        if not self.music_enabled:
            return
        self.stop_music()
        mixer.music.load(path)
        mixer.music.set_volume(self.music_volume)
        mixer.music.play(loop)

    def play_clip(self, path: str) -> None:
        """NES InitMusicSFX with a music clip (the victory and level-up fanfares, the harp, the flute, the curse,
        Gwaelin's love, the inn): the clip takes the music's place, whatever was playing stops, and it plays once. It
        returns at once, so the game carries on (the battle's experience and gold lines print over the victory music);
        wait_for_music_end waits for the clip to finish.

        The NES music engine has one music track, so a clip can only be cut off by the next InitMusicSFX with music
        (the next clip, the map music, the next fight's music). Playing it as pygame's music, not as a Sound on a
        mixer channel, gives it that one slot: no sound effect can take its place or leave it without a free
        channel. With the music off, nothing plays, but wait_for_music_end still waits as long as the clip lasts."""
        self.stop_music()
        if self.music_enabled:
            mixer.music.load(path)
            mixer.music.set_volume(self.music_volume)
            mixer.music.play()
            self._clip_end_ticks = None
        else:
            self._clip_end_ticks = game_ticks() + clip_length_ms(path)

    def wait_for_music_end(self, config: dict) -> None:
        """NES WaitForMusicEnd (Bank01): wait until the clip play_clip started has finished. With the music on, that
        is when pygame's music stops, whatever the game speed (keys 1 to 4 only make the polling faster), since the
        clip plays at its normal length. With the music off, it waits out the rest of the clip's length, in game time
        like any other wait (shorter at a higher game speed). Closing the window quits during either wait
        (src/waiting.py); NO_WAIT skips them."""
        clip_end_ticks, self._clip_end_ticks = self._clip_end_ticks, None
        if config.get('NO_WAIT'):
            return
        if self.music_enabled:
            while mixer.music.get_busy():
                wait(POLL_INTERVAL_MS)
        elif clip_end_ticks is not None:
            wait(max(0, clip_end_ticks - game_ticks()), config)

    def play_until_end(self, path: str, config: dict) -> None:
        """NES InitMusicSFX with a music clip, then WaitForMusicEnd: the clip replaces the music, plays once, and the
        game waits until it has finished (play_clip, then wait_for_music_end)."""
        self.play_clip(path)
        self.wait_for_music_end(config)

    def stop_music(self):
        if self.music_enabled:
            mixer.music.stop()

    def pause_music(self):
        if self.music_enabled:
            mixer.music.pause()

    def unpause_music(self):
        if self.music_enabled:
            mixer.music.unpause()

    def fadeout_music(self, fadeout_time):
        if self.music_enabled:
            mixer.music.fadeout(fadeout_time)

    def set_music_volume(self, volume):
        self.music_volume = volume
        if self.music_enabled:
            mixer.music.set_volume(self.music_volume)

    def get_music_volume(self):
        return self.music_volume



def clip_length_ms(path: str) -> float:
    """How long an audio file plays, in milliseconds (0 if the mixer isn't running)."""
    if not mixer.get_init():
        return 0
    return mixer.Sound(path).get_length() * 1000
