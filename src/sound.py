from os.path import sep

from pygame import mixer

from src.calculation import Calculation
from src.directories import Directories

# Sound

_sound_library: dict[str, object] = {}


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

    def play_sfx(self, path):
        """Plays a sound effect the way the NES sound engine does: there is one SFX slot (pulse 2 and noise), and a new
        SFX takes it over, so a sound still playing there stops and the new one starts from the beginning (Bank01
        DoSFX resets the SFX data pointer and SFXActive). Here the slot is a reserved mixer channel."""
        if self.config["SOUND_ENABLED"]:
            sound = retrieve_audio_resource(_sound_library, path, _sound_library.get(path))
            sound.set_volume(self.sfx_volume)
            sfx_channel().play(sound)

    def stop_sfx(self):
        """Silences the SFX slot. On the NES, starting an SFX does this right away (DoSFX writes $30, constant volume 0,
        to SQ2Cntrl0 and NoiseCntrl0), and the new sound only starts at the next frame's UpdateSound."""
        if self.config["SOUND_ENABLED"] and mixer.get_init():
            sfx_channel().stop()

    def set_sfx_volume(self, volume):
        """Set the sound effects volume (0.0 to 1.0)"""
        self.sfx_volume = max(0.0, min(1.0, volume))

    def get_sfx_volume(self):
        """Get the current sound effects volume"""
        return self.sfx_volume


SFX_CHANNEL = 0


def sfx_channel() -> mixer.Channel:
    """The mixer channel kept for play_sfx. Reserving it keeps Sound.play() from picking it for other sounds; the
    reservation is renewed on each call because it resets whenever the mixer is initialized again."""
    mixer.set_reserved(SFX_CHANNEL + 1)
    return mixer.Channel(SFX_CHANNEL)


def retrieve_audio_resource(_sound_library, path, sound):
    if sound is None:
        canonicalized_path = path.replace('/', sep).replace('\\', sep)
        sound = mixer.Sound(canonicalized_path)
        _sound_library[path] = sound
    return sound
