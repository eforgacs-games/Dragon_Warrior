from pygame import time

from src.common import convert_to_milliseconds, play_sound, bump_sfx


def bump(character):
    if character.identifier == 'HERO':
        if not character.last_bump_time:
            character.last_bump_time = time.get_ticks()
        if time.get_ticks() - character.last_bump_time >= convert_to_milliseconds(15):
            character.last_bump_time = time.get_ticks()
            if character.current_tile not in ('BRICK_STAIR_UP', 'BRICK_STAIR_DOWN', 'GRASS_STAIR_DOWN'):
                play_sound(bump_sfx)
    character.bumped = True
