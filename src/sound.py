from pygame.time import get_ticks

from src.common import convert_to_milliseconds, play_sound, bump_sfx


def bump(character):
    if character.identifier == 'HERO':
        if not character.last_bump_time:
            character.last_bump_time = get_ticks()
        if get_ticks() - character.last_bump_time >= convert_to_milliseconds(15):
            character.last_bump_time = get_ticks()
            play_sound(bump_sfx)
    character.bumped = True
