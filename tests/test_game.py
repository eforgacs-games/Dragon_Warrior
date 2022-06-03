import os
from unittest import TestCase
from unittest.mock import MagicMock

import pygame
from pygame.imageext import load_extended
from pygame.transform import scale

from src.camera import Camera
from src.common import UNARMED_HERO_PATH, get_tile_id_by_coordinates, Direction
from src.config import SCALE, TILE_SIZE
from src.game import Game
from src.maps import MapWithoutNPCs, TantegelThroneRoom
from src.maps_functions import parse_animated_sprite_sheet
from src.player.player import Player
from src.sprites.roaming_character import RoamingCharacter

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ['SDL_AUDIODRIVER'] = 'dummy'


def create_key_mock(pressed_key):
    def helper():
        # increase this number as necessary to accommodate keys used
        tmp = [0] * 200
        tmp[pressed_key] = 1
        return tmp

    return helper


layout = [[33, 0, 3],
          [1, 2, 3],
          [3, 3, 39]]


class MockMap(MapWithoutNPCs):
    __test__ = False

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
        self.game.current_map = MockMap()
        self.initial_hero_location = self.game.current_map.get_initial_character_location('HERO')
        unarmed_hero_sheet = load_extended(UNARMED_HERO_PATH)
        self.hero_images = parse_animated_sprite_sheet(
            scale(unarmed_hero_sheet, (unarmed_hero_sheet.get_width() * SCALE, unarmed_hero_sheet.get_height() * SCALE)))
        self.game.current_map.player = Player(self.center_pt, self.hero_images)
        # self.camera = Camera(self.game.current_map, self.initial_hero_location, speed=2)
        self.camera = Camera((self.game.current_map.player.rect.y // TILE_SIZE, self.game.current_map.player.rect.x // TILE_SIZE), self.game.current_map,
                             None)

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
        test_roaming_character.direction_value = Direction.DOWN.value
        self.game.move_medially(test_roaming_character)
        self.assertEqual(0, test_roaming_character.rect.y)

    def test_move_roaming_character_laterally(self):
        test_roaming_character = setup_roaming_character(row=2, column=2, direction=Direction.LEFT.value)
        test_roaming_character.rect.x = 0
        self.game.move_laterally(test_roaming_character)
        self.assertEqual(-2, test_roaming_character.rect.x)
        test_roaming_character.direction_value = Direction.RIGHT.value
        self.game.move_laterally(test_roaming_character)
        self.assertEqual(0, test_roaming_character.rect.x)

    def test_roaming_character_blocked_by_object(self):
        test_roaming_character = setup_roaming_character(row=2, column=0, direction=Direction.UP.value)
        test_roaming_character.rect.y = 0
        self.game.move_medially(test_roaming_character)
        self.assertEqual(0, test_roaming_character.rect.y)

    # TODO(ELF): Write tests that test the test_roaming_character.row / column update correctly after moving/not moving

    def test_handle_fps_changes(self):
        self.game.current_map.player.row = 1
        self.assertEqual(60, self.game.fps)
        pygame.key.get_pressed = create_key_mock(pygame.K_2)
        self.game.handle_fps_changes(pygame.key.get_pressed())
        self.assertEqual(120, self.game.fps)
        pygame.key.get_pressed = create_key_mock(pygame.K_3)
        self.game.handle_fps_changes(pygame.key.get_pressed())
        self.assertEqual(240, self.game.fps)
        pygame.key.get_pressed = create_key_mock(pygame.K_4)
        self.game.handle_fps_changes(pygame.key.get_pressed())
        self.assertEqual(480, self.game.fps)

    def test_handle_keypresses_start(self):
        self.assertFalse(self.game.paused)
        pygame.key.get_pressed = create_key_mock(pygame.K_i)
        self.game.handle_keypresses(pygame.key.get_pressed())
        self.assertTrue(self.game.paused)
        pygame.key.get_pressed = create_key_mock(pygame.K_i)
        self.game.handle_keypresses(pygame.key.get_pressed())
        self.assertFalse(self.game.paused)

    def test_handle_keypresses_command_menu(self):
        self.assertFalse(self.game.cmd_menu.launch_signaled)
        pygame.key.get_pressed = create_key_mock(pygame.K_k)
        self.game.handle_keypresses(pygame.key.get_pressed())
        self.assertTrue(self.game.cmd_menu.launch_signaled)
        pygame.key.get_pressed = create_key_mock(pygame.K_j)
        self.game.handle_keypresses(pygame.key.get_pressed())
        self.assertFalse(self.game.cmd_menu.launch_signaled)

    def test_replace_characters_with_underlying_tiles(self):
        self.assertEqual(['BRICK'], self.game.replace_characters_with_underlying_tiles([self.game.player.current_tile]))

    def test_convert_numeric_tile_list_to_unique_tile_values(self):
        self.assertEqual(['WALL',
                          'WOOD',
                          'BRICK',
                          'TREASURE_BOX',
                          'DOOR',
                          'BRICK_STAIR_DOWN',
                          'BRICK_STAIR_UP',
                          'BARRIER',
                          'WEAPON_SIGN'], self.game.convert_numeric_tile_list_to_unique_tile_values([1, 2, 3, 4, 5, 6, 7, 8, 9]))

    def test_handle_menu_launch(self):
        self.game.cmd_menu.launch_signaled = True
        self.game.handle_menu_launch(self.game.cmd_menu)
        self.assertTrue(self.game.cmd_menu.launched)

    def test_change_map(self):
        self.game.current_map.staircases = {(10, 13): {'map': 'TantegelThroneRoom', 'destination_coordinates': (14, 18)}}
        self.game.change_map(TantegelThroneRoom())
        self.assertEqual('MockMap', self.game.last_map.identifier)
        self.assertEqual('TantegelThroneRoom', self.game.current_map.identifier)

    def test_king_lorik_initial_dialog(self):
        self.assertEqual((
            "Descendant of Erdrick, listen now to my words.",
            "It is told that in ages past Erdrick fought demons with a Ball of Light.",
            "Then came the Dragonlord who stole the precious globe and hid it in the darkness.",
            "Now, Edward, thou must help us recover the Ball of Light and restore peace to our land.",
            "The Dragonlord must be defeated.",
            "Take now whatever thou may find in these Treasure Chests to aid thee in thy quest.",
            "Then speak with the guards, for they have much knowledge that may aid thee.",
            "May the light shine upon thee, Edward."
        ), self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'])

    def test_king_lorik_post_initial_dialog(self):
        self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['is_initial_dialog'] = False
        self.game.set_to_post_initial_dialog()
        self.assertEqual("When thou art finished preparing for thy departure, please see me.\n"
                         "I shall wait.", self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'])

    def test_wise_man_tantegel_courtyard_dialog(self):
        self.assertEqual("Edward's coming was foretold by legend. May the light shine upon "
                         'this brave warrior.', self.game.cmd_menu.dialog_lookup.lookup_table['TantegelCourtyard']['WISE_MAN']['dialog'])

    # gives an IndexError: list index out of range because the constants for K_UP, etc. are huge
    # def test_move_player_directions(self):
    #     self.assertEqual(Direction.UP.value, self.game.player.direction_value)
    #     pygame.key.get_pressed = create_key_mock(pygame.K_s)
    #     self.game.move_player(pygame.key.get_pressed())
    #     self.assertEqual(Direction.DOWN.value, self.game.player.direction_value)
