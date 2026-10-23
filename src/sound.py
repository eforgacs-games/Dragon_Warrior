from os.path import sep

from pygame import mixer

from src.calculation import Calculation
from src.directories import Directories
from src.waiting import NES_FPS, game_ticks, wait

# Sound

_sound_library: dict[str, object] = {}

# NES SpellSFX (Bank01, $848E): 7 notes of 6 counts each, 42 frames (the recording's audible part is 0.72 s)
SPELL_SFX_FRAMES = 42


class Sound:

    def __init__(self, config):
        self.config = config
        self.calculation = Calculation(config)
        self.directories = Directories(config)
        self.sfx_volume = 0.5
        self._sfx_started_ticks: int | None = None  # game time the sound effect in the SFX slot started at

    def play_sound(self, path='data/sound/sfx'):
        """Plays a sound effect. Every sound effect goes to the one SFX slot (play_sfx), as on the NES: InitMusicSFX
        sends every SFX_ number to DoSFX, which points the one SFX data pointer at it, so a new sound effect cuts off the
        one still playing and none is ever skipped.

        They used to play with Sound.play() on any free mixer channel. Every SFX file is padded to about 3 seconds, so
        at a high game speed seven quick ones left no free channel, and the next one was silently dropped (#317)."""
        self._play_in_sfx_slot(path)

    def play_sfx(self, path):
        """Plays a sound effect the way the NES sound engine does: there is one SFX slot (pulse 2 and noise), and a new
        SFX takes it over, so a sound still playing there stops and the new one starts from the beginning (Bank01
        DoSFX resets the SFX data pointer and SFXActive). Here the slot is a reserved mixer channel."""
        self._play_in_sfx_slot(path)

    def wait_for_sfx_end(self, length_frames: float, config: dict) -> None:
        """Wait until the sound effect that last started, which is length_frames NES frames long, has finished: the
        NES WaitForMusicEnd (Bank01, $815E) after a sound effect, as in PlyrCastSpell (LDBAC). Only the rest of it is
        waited out, in game frames (shorter at a higher game speed), so whatever ran since it started counts. The
        recordings are padded with silence, so their length can't be read off the file. NO_WAIT skips it."""
        if self._sfx_started_ticks is None:
            return
        end_ticks = self._sfx_started_ticks + length_frames * 1000 / NES_FPS
        wait(max(0.0, end_ticks - game_ticks()), config)

    def _play_in_sfx_slot(self, path):
        self._sfx_started_ticks = game_ticks()
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
    """The NES SFX slot: the one mixer channel every sound effect plays on. Reserving it keeps a Sound.play()
    elsewhere from picking it; the reservation is renewed on each call because it resets whenever the mixer is
    initialized again, so it holds from the first sound effect after any mixer start."""
    mixer.set_reserved(SFX_CHANNEL + 1)
    return mixer.Channel(SFX_CHANNEL)


def retrieve_audio_resource(_sound_library, path, sound):
    if sound is None:
        canonicalized_path = path.replace('/', sep).replace('\\', sep)
        sound = mixer.Sound(canonicalized_path)
        _sound_library[path] = sound
    return sound
