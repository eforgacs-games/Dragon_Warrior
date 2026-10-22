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
            # NES CheckCollision (DirectionBlocked) plays SFX_WALL_BUMP on every blocked step. Game.move_player only
            # tries a step every 16 frames while the hero is held against something, so that's how often it plays.
            if character.current_tile not in ('BRICK_STAIR_UP', 'BRICK_STAIR_DOWN', 'GRASS_STAIR_DOWN'):
                self.sound.play_sound(self.directories.bump_sfx)
        character.bumped = True
