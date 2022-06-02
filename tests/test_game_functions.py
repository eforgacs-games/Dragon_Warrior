import os
from unittest import TestCase

from pygame.image import load_extended
from pygame.transform import scale

from src.camera import Camera
from src.common import Direction, UNARMED_HERO_PATH
from src.config import TILE_SIZE, SCALE
from src.game import Game
from src.game_functions import get_next_coordinates, set_character_position
from src.maps import MapWithoutNPCs
from src.maps_functions import parse_animated_sprite_sheet
from src.player.player import Player

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ['SDL_AUDIODRIVER'] = 'dummy'
layout = [[33, 0, 3],
          [1, 2, 3],
          [3, 3, 3]]


class MockMap(MapWithoutNPCs):
    def __init__(self):
        super().__init__(layout)

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.DOWN.value


class Test(TestCase):

    def setUp(self) -> None:
        self.game = Game()
        self.game.camera_pos = 0, 0
        self.center_pt = 0, 0
        self.game.current_map = MockMap()
        self.initial_hero_location = self.game.current_map.get_initial_character_location('HERO')
        unarmed_hero_sheet = load_extended(UNARMED_HERO_PATH)
        self.hero_images = parse_animated_sprite_sheet(
            scale(unarmed_hero_sheet, (unarmed_hero_sheet.get_width() * SCALE, unarmed_hero_sheet.get_height() * SCALE)))
        self.game.current_map.player = Player(self.center_pt, self.hero_images)
        self.camera = Camera((self.game.current_map.player.rect.y // TILE_SIZE, self.game.current_map.player.rect.x // TILE_SIZE), self.game.current_map,
                             None)

    def test_set_character_position(self):
        self.assertIsNone(self.game.current_map.player.column)
        self.assertIsNone(self.game.current_map.player.row)
        self.assertEqual(-1, self.game.current_map.player.rect.x // TILE_SIZE)
        self.assertEqual(-1, self.game.current_map.player.rect.y // TILE_SIZE)
        set_character_position(self.game.current_map.player)
        self.assertEqual((self.game.current_map.player.column, self.game.current_map.player.row), (self.game.current_map.player.rect.x // TILE_SIZE, self.game.current_map.player.rect.y // TILE_SIZE))
        self.assertEqual((self.game.current_map.player.column, self.game.current_map.player.row), (-1, -1))

    def test_get_next_coordinates(self):
        self.game.player.direction_value = 0
        self.assertEqual((11, 13), get_next_coordinates(self.game.player.rect.x // TILE_SIZE,
                                                        self.game.player.rect.y // TILE_SIZE,
                                                        self.game.player.direction_value))
        self.game.player.direction_value = 1
        self.assertEqual((10, 12), get_next_coordinates(self.game.player.rect.x // TILE_SIZE,
                                                        self.game.player.rect.y // TILE_SIZE,
                                                        self.game.player.direction_value))
        self.game.player.direction_value = 2
        self.assertEqual((9, 13), get_next_coordinates(self.game.player.rect.x // TILE_SIZE,
                                                       self.game.player.rect.y // TILE_SIZE,
                                                       self.game.player.direction_value))
        self.game.player.direction_value = 3
        self.assertEqual((10, 14), get_next_coordinates(self.game.player.rect.x // TILE_SIZE,
                                                        self.game.player.rect.y // TILE_SIZE,
                                                        self.game.player.direction_value))



