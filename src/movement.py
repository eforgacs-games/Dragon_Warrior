from pygame import time

from src.calculation import Calculation
from src.directories import Directories
from src.sound import Sound


class Movement:
    def __init__(self, config):
        self.config = config
        self.sound = Sound(config)
        self.calculation = Calculation(config)
        self.directories = Directories(config)

    def bump_and_reset(self, character, pre_bump_next_tile, pre_bump_next_next_tile):
        if character.next_tile_id != pre_bump_next_tile:
            character.next_tile_id = pre_bump_next_tile
        if character.next_next_tile_id != pre_bump_next_next_tile:
            character.next_next_tile_id = pre_bump_next_next_tile
        self.bump(character)

    def bump(self, character):
        if character.identifier == 'HERO':
            if not character.last_bump_time:
                character.last_bump_time = time.get_ticks()
            if time.get_ticks() - character.last_bump_time >= self.calculation.convert_to_milliseconds(15):
                character.last_bump_time = time.get_ticks()
                if character.current_tile not in ('BRICK_STAIR_UP', 'BRICK_STAIR_DOWN', 'GRASS_STAIR_DOWN'):
                    self.sound.play_sound(self.directories.bump_sfx)
        character.bumped = True
