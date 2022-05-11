import os
from abc import ABC
from unittest import TestCase
from unittest.mock import MagicMock

import pygame
from pygame.imageext import load_extended
from pygame.transform import scale

from src.camera import Camera
from src.common import UNARMED_HERO_PATH, get_tile_id_by_coordinates, Direction, GUARD_PATH, get_image
from src.config import SCALE, TILE_SIZE
from src.game import Game
from src.maps import DragonWarriorMap, parse_animated_sprite_sheet
from src.player.player import Player
from src.sprites.roaming_character import RoamingCharacter

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ['SDL_AUDIODRIVER'] = 'dummy'


def create_key_mock(pressed_key):
    def helper():
        tmp = [0] * 300
        tmp[pressed_key] = 1
        return tmp

    return helper


layout = [[33, 0, 3],
          [1, 2, 3],
          [3, 3, 3]]


class TestMockMap(DragonWarriorMap, ABC):
    def __init__(self):
        super().__init__(layout)

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.DOWN.value


def setup_roaming_character(row, column, direction):
    test_roaming_character = RoamingCharacter(None, direction, None, 'ROAMING_GUARD')
    test_roaming_character.rect = MagicMock()
    test_roaming_character.row = row
    test_roaming_character.column = column
    return test_roaming_character


class TestGame(TestCase):

    def setUp(self) -> None:
        self.game = Game()
        self.game.camera_pos = 0, 0
        self.center_pt = 0, 0
        self.game.current_map = TestMockMap()

        self.initial_hero_location = self.game.current_map.get_initial_character_location('HERO')

        unarmed_hero_sheet = load_extended(UNARMED_HERO_PATH)
        unarmed_hero_sheet = scale(unarmed_hero_sheet,
                                   (unarmed_hero_sheet.get_width() * SCALE, unarmed_hero_sheet.get_height() * SCALE))
        self.hero_images = parse_animated_sprite_sheet(unarmed_hero_sheet)
        self.game.current_map.player = Player(center_point=self.center_pt,
                                              images=self.hero_images)
        self.game.hero_row = 0
        self.game.hero_column = 0
        self.hero_layout_column, self.hero_layout_row = self.game.current_map.player.rect.x // TILE_SIZE, self.game.current_map.player.rect.y // TILE_SIZE
        # self.camera = Camera(self.game.current_map, self.initial_hero_location, speed=2)
        self.camera = Camera(hero_position=(self.hero_layout_row, self.hero_layout_column), current_map=self.game.current_map, screen=None)
        pygame.key.get_pressed = create_key_mock(pygame.K_RIGHT)
        pygame.key.get_pressed = create_key_mock(pygame.K_UP)
        pygame.key.get_pressed = create_key_mock(pygame.K_DOWN)
        pygame.key.get_pressed = create_key_mock(pygame.K_LEFT)

    # def test_get_initial_camera_position(self):
    #     initial_hero_location = self.game.current_map.get_initial_character_location('HERO')
    #     self.assertEqual(self.camera.set_camera_position(initial_hero_location), (0, 0))
    #     self.game.current_map.layout = [[1, 0],
    #                                     [34, 2]]
    #     initial_hero_location = self.game.current_map.get_initial_character_location('HERO')
    #     self.assertEqual(self.camera.set_camera_position(initial_hero_location), (-16, 0))
    #     self.game.current_map.layout = [[1, 34],
    #                                     [0, 2]]
    #     initial_hero_location = self.game.current_map.get_initial_character_location('HERO')
    #     self.assertEqual(self.camera.set_camera_position(initial_hero_location), (0, -7))
    #     self.game.current_map.layout = [[1, 0],
    #                                     [2, 34]]
    #     initial_hero_location = self.game.current_map.get_initial_character_location('HERO')
    #     self.assertEqual(self.camera.set_camera_position(initial_hero_location), (-16, -7))

    def test_hero_underlying_tile(self):
        self.assertEqual('BRICK', self.game.current_map.hero_underlying_tile())

    # def test_hero_underlying_tile_not_implemented(self):
    #     self.assertRaises(NotImplementedError, self.game.current_map.hero_underlying_tile)

    # def test_move_player_return_value(self):
    #     key = pygame.key.get_pressed()
    #     self.assertEqual(self.game.move_player(key), None)

    def test_get_tile_by_coordinates(self):
        self.assertEqual('HERO', get_tile_id_by_coordinates(0, 0, self.game.current_map))
        self.assertEqual('ROOF', get_tile_id_by_coordinates(1, 0, self.game.current_map))
        self.assertEqual('WALL', get_tile_id_by_coordinates(0, 1, self.game.current_map))
        self.assertEqual('WOOD', get_tile_id_by_coordinates(1, 1, self.game.current_map))

    # TODO: implement test_handle_roaming_character_map_edge_side_collision.

    # def test_handle_roaming_character_map_edge_side_collision(self):
    #     initial_roaming_guard_position = self.game.current_map.get_initial_character_location('ROAMING_GUARD')
    #     self.game.current_map.layout = [[3, 1, 3],
    #                                     [1, 38, 1],
    #                                     [34, 1, 3]]
    #     self.roaming_guard = AnimatedSprite(self.center_pt, 0,
    #                                         self.roaming_guard_images[0], name='ROAMING_GUARD')
    #     self.game.current_map.roaming_characters.append(self.roaming_guard)
    #     self.game.move_roaming_characters()
    #     self.assertEqual(initial_roaming_guard_position, )  # current roaming guard position)

    def test_move_roaming_character_medially(self):
        test_roaming_character = setup_roaming_character(row=2, column=2, direction=Direction.UP.value)
        test_roaming_character.rect.y = 0
        self.game.move_medially(test_roaming_character)
        self.assertEqual(-2, test_roaming_character.rect.y)
        test_roaming_character.direction = Direction.DOWN.value
        self.game.move_medially(test_roaming_character)
        self.assertEqual(0, test_roaming_character.rect.y)

    def test_move_roaming_character_laterally(self):
        test_roaming_character = setup_roaming_character(row=2, column=2, direction=Direction.LEFT.value)
        test_roaming_character.rect.x = 0
        self.game.move_laterally(test_roaming_character)
        self.assertEqual(-2, test_roaming_character.rect.x)
        test_roaming_character.direction = Direction.RIGHT.value
        self.game.move_laterally(test_roaming_character)
        self.assertEqual(0, test_roaming_character.rect.x)

    def test_roaming_character_blocked_by_object(self):
        test_roaming_character = setup_roaming_character(row=2, column=0, direction=Direction.UP.value)
        test_roaming_character.rect.y = 0
        self.game.move_medially(test_roaming_character)
        self.assertEqual(0, test_roaming_character.rect.y)

    # TODO(ELF): Write tests that test the test_roaming_character.row / column update correctly after moving/not moving
