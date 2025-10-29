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

    # TODO: allow for adjustment of volume for music/sfx

    def play_sound(self, path='data/sound/sfx'):
        if self.config["SOUND_ENABLED"]:
            sound = _sound_library.get(path)
            sound = retrieve_audio_resource(_sound_library, path, sound)
            sound.play()


def retrieve_audio_resource(_sound_library, path, sound):
    if sound is None:
        canonicalized_path = path.replace('/', sep).replace('\\', sep)
        sound = mixer.Sound(canonicalized_path)
        _sound_library[path] = sound
    return sound
