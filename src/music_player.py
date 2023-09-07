from pygame import mixer


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

