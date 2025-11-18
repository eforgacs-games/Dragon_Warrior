from os.path import sep

from pygame import mixer

from src.calculation import Calculation
from src.directories import Directories

# Sound

_sound_library = {}


class Sound:

    def __init__(self, config):
        self.config = config
        self.calculation = Calculation(config)
        self.directories = Directories(config)
        self.sfx_volume = 0.5

    def play_sound(self, path='data/sound/sfx'):
        if self.config["SOUND_ENABLED"]:
            sound = _sound_library.get(path)
            sound = retrieve_audio_resource(_sound_library, path, sound)
            sound.set_volume(self.sfx_volume)
            sound.play()

    def set_sfx_volume(self, volume):
        """Set the sound effects volume (0.0 to 1.0)"""
        self.sfx_volume = max(0.0, min(1.0, volume))

    def get_sfx_volume(self):
        """Get the current sound effects volume"""
        return self.sfx_volume


def retrieve_audio_resource(_sound_library, path, sound):
    if sound is None:
        canonicalized_path = path.replace('/', sep).replace('\\', sep)
        sound = mixer.Sound(canonicalized_path)
        _sound_library[path] = sound
    return sound
