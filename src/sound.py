from os.path import sep

from pygame import time, mixer

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
            global _sound_library
            sound = _sound_library.get(path)
            sound = retrieve_audio_resource(_sound_library, path, sound)
            sound.play()

    def bump(self, character):
        if character.identifier == 'HERO':
            if not character.last_bump_time:
                character.last_bump_time = time.get_ticks()
            if time.get_ticks() - character.last_bump_time >= self.calculation.convert_to_milliseconds(15):
                character.last_bump_time = time.get_ticks()
                if character.current_tile not in ('BRICK_STAIR_UP', 'BRICK_STAIR_DOWN', 'GRASS_STAIR_DOWN'):
                    self.play_sound(self.directories.bump_sfx)
        character.bumped = True


def retrieve_audio_resource(_sound_library, path, sound):
    if sound is None:
        canonicalized_path = path.replace('/', sep).replace('\\', sep)
        sound = mixer.Sound(canonicalized_path)
        _sound_library[path] = sound
    return sound
