from pygame import mixer

from src.waiting import POLL_INTERVAL_MS, wait


class MusicPlayer:
    def __init__(self, config):
        self.music_enabled = config["MUSIC_ENABLED"]
        self.sound_enabled = config["SOUND_ENABLED"]
        self.orchestra_music_enabled = config["ORCHESTRA_MUSIC_ENABLED"]
        self.music_volume = 0.5

    def load_and_play_music(self, path, loop=-1):
        self.stop_music()
        mixer.music.load(path)
        if self.music_enabled:
            mixer.music.set_volume(self.music_volume)
            mixer.music.play(loop)

    def play_until_end(self, path: str, config: dict) -> None:
        """NES InitMusicSFX with a music clip, then WaitForMusicEnd (Bank01): the clip replaces the music, plays once,
        and the game waits until it has finished. That wait ends with the music, whatever the game speed (keys 1 to 4
        only make the polling faster), since the clip plays at its normal length. With the music off there is nothing
        to wait for, so it waits as long as the clip lasts, in game time like any other wait (shorter at a higher game
        speed). Closing the window quits during either wait (src/waiting.py); NO_WAIT skips them."""
        if self.music_enabled:
            self.stop_music()
            mixer.music.load(path)
            mixer.music.set_volume(self.music_volume)
            mixer.music.play()
            if config.get('NO_WAIT'):
                return
            while mixer.music.get_busy():
                wait(POLL_INTERVAL_MS)
        else:
            wait(clip_length_ms(path), config)

    @staticmethod
    def stop_music():
        mixer.music.stop()

    @staticmethod
    def pause_music():
        mixer.music.pause()

    @staticmethod
    def unpause_music():
        mixer.music.unpause()

    @staticmethod
    def fadeout_music(fadeout_time):
        mixer.music.fadeout(fadeout_time)

    def set_music_volume(self, volume):
        self.music_volume = volume
        mixer.music.set_volume(self.music_volume)

    def get_music_volume(self):
        return self.music_volume



def clip_length_ms(path: str) -> float:
    """How long an audio file plays, in milliseconds (0 if the mixer isn't running)."""
    if not mixer.get_init():
        return 0
    return mixer.Sound(path).get_length() * 1000
