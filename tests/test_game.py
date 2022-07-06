import os
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame
from pygame import K_F1, K_z, K_UP, RESIZABLE, SCALED
from pygame.imageext import load_extended
from pygame.sprite import LayeredDirty
from pygame.transform import scale

from data.text.dialog_lookup_table import DialogLookup
from src.camera import Camera
from src.common import UNARMED_HERO_PATH, get_tile_id_by_coordinates, Direction, get_next_tile_identifier, village_music
from src.config import SCALE, TILE_SIZE
from src.game import Game
from src.game_functions import get_next_coordinates, replace_characters_with_underlying_tiles
from src.intro import controls
from src.maps import MapWithoutNPCs, TantegelThroneRoom, Alefgard, TantegelCourtyard
from src.maps_functions import parse_animated_sprite_sheet
from src.menu import CommandMenu
from src.menu_functions import convert_list_to_newline_separated_string
from src.player.player import Player
from src.sprites.roaming_character import RoamingCharacter

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


def create_get_pressed_mock_array(max_key=K_z):
    return [0] * (max_key + 1)


def create_f1_key_mock(pressed_key):
    def helper():
        tmp = create_get_pressed_mock_array(K_F1)
        tmp[pressed_key] = 1
        return tmp

    return helper


def create_move_player_key_mock(pressed_key):
    def helper():
        tmp = create_get_pressed_mock_array(K_UP)
        tmp[pressed_key] = 1
        return tmp

    return helper


def create_key_mock(pressed_key):
    def helper():
        # increase this number as necessary to accommodate keys used
        tmp = create_get_pressed_mock_array()
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
        with patch('src.game.SCALED'):
            self.game = Game()
        self.game.player.name = "Edward"
        self.game.cmd_menu.dialog_lookup = DialogLookup(self.game.cmd_menu)
        self.game.current_map = MockMap()
        unarmed_hero_sheet = load_extended(UNARMED_HERO_PATH)
        self.game.player = Player((0, 0), parse_animated_sprite_sheet(
            scale(unarmed_hero_sheet, (unarmed_hero_sheet.get_width() * SCALE, unarmed_hero_sheet.get_height() * SCALE))), self.game.current_map)
        # self.camera = Camera(self.game.current_map, self.initial_hero_location, speed=2)
        self.camera = Camera((self.game.player.rect.y // TILE_SIZE, self.game.player.rect.x // TILE_SIZE), self.game.current_map,
                             self.game.screen)

    def test_get_initial_camera_position(self):
        self.assertEqual((288.0, 256.0), self.camera.get_pos())
        self.game.current_map.staircases = {(10, 13): {'map': 'TantegelThroneRoom', 'destination_coordinates': (14, 18)}}
        # self.game.change_map(TantegelThroneRoom())
        # self.assertEqual((-160.0, -96.0), self.camera.get_pos())
        # self.game.change_map(TantegelCourtyard())
        # self.assertEqual((-192.0, -224.0), self.camera.get_pos())

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

    def test_handle_start_button(self):
        self.assertFalse(self.game.paused)
        pygame.key.get_pressed = create_key_mock(pygame.K_i)
        self.game.handle_start_button(pygame.key.get_pressed())
        self.assertTrue(self.game.paused)
        pygame.key.get_pressed = create_key_mock(pygame.K_i)
        self.game.handle_start_button(pygame.key.get_pressed())
        self.assertFalse(self.game.paused)

    def test_handle_a_button_and_b_button(self):
        self.assertFalse(self.game.cmd_menu.launch_signaled)
        pygame.key.get_pressed = create_key_mock(pygame.K_k)
        self.game.handle_a_button(pygame.key.get_pressed())
        self.assertTrue(self.game.cmd_menu.launch_signaled)
        pygame.key.get_pressed = create_key_mock(pygame.K_j)
        self.game.handle_b_button(pygame.key.get_pressed())
        self.assertFalse(self.game.cmd_menu.launch_signaled)

    def test_replace_characters_with_underlying_tiles(self):
        self.game.current_map.character_key['HERO']['underlying_tile'] = 'BRICK'
        self.assertEqual(['BRICK'], replace_characters_with_underlying_tiles(['HERO'], self.game.current_map.character_key))

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
        self.assertTrue(self.game.cmd_menu.menu.is_enabled())
        self.game.handle_menu_launch(self.game.cmd_menu)

    def test_change_map(self):
        self.game.player.row = 10
        self.game.player.column = 13
        self.game.current_map.staircases = {(10, 13): {'map': 'TantegelThroneRoom', 'destination_coordinates': (14, 18)}}
        self.game.change_map(TantegelThroneRoom())
        self.assertEqual('MockMap', self.game.last_map.identifier)
        self.assertEqual('TantegelThroneRoom', self.game.current_map.identifier)
        self.game.player.row = 14
        self.game.player.column = 18
        self.game.change_map(TantegelCourtyard())
        self.assertTrue(self.game.allow_save_prompt)
        self.game.music_enabled = False
        self.game.player.row = 14
        self.game.player.column = 14
        self.game.change_map(TantegelThroneRoom())

    def test_change_map_maintain_inventory_and_gold(self):
        self.game.player.row = 10
        self.game.player.column = 13
        self.game.player.gold = 120
        self.game.player.inventory = ['Torch']
        self.game.current_map.staircases = {(10, 13): {'map': 'TantegelThroneRoom', 'destination_coordinates': (14, 18)}}
        self.game.change_map(TantegelThroneRoom())
        self.assertEqual(120, self.game.player.gold)
        self.assertEqual(['Torch'], self.game.player.inventory)

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
                         'this brave warrior.', self.game.cmd_menu.dialog_lookup.lookup_table['TantegelCourtyard']['WISE_MAN']['dialog'][0])

    # gives an IndexError: list index out of range because the constants for K_UP, etc. are huge
    # def test_move_player_directions(self):
    #     self.assertEqual(Direction.UP.value, self.game.player.direction_value)
    #     pygame.key.get_pressed = create_key_mock(pygame.K_s)
    #     self.game.move_player(pygame.key.get_pressed())
    #     self.assertEqual(Direction.DOWN.value, self.game.player.direction_value)

    def test_run_automatic_initial_dialog(self):
        self.assertTrue(self.game.is_initial_dialog)
        # pygame.key.get_pressed = create_key_mock(pygame.K_j)
        self.game.run_automatic_initial_dialog()
        self.assertFalse(self.game.enable_movement)
        # TODO(ELF): Need to enable the following checks:
        # self.assertFalse(self.game.is_initial_dialog)
        # self.assertTrue(self.game.automatic_initial_dialog_run)

    def test_set_to_save_prompt(self):
        self.game.player.name = "Edward"
        self.assertEqual((
            "Descendant of Erdrick, listen now to my words.",
            "It is told that in ages past Erdrick fought demons with a Ball of Light.",
            "Then came the Dragonlord who stole the precious globe and hid it in the darkness.",
            f"Now, {self.game.player.name}, thou must help us recover the Ball of Light and restore peace to our land.",
            "The Dragonlord must be defeated.",
            "Take now whatever thou may find in these Treasure Chests to aid thee in thy quest.",
            "Then speak with the guards, for they have much knowledge that may aid thee.",
            f"May the light shine upon thee, {self.game.player.name}."
        ), self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'])
        self.game.set_to_save_prompt()
        self.assertEqual((
            f"I am greatly pleased that thou hast returned, {self.game.player.name}.",
            f"Before reaching thy next level of experience thou must gain {self.game.player.points_to_next_level} Points.",
            "Will thou tell me now of thy deeds so they won't be forgotten?",
            # if yes:
            "Thy deeds have been recorded on the Imperial Scrolls of Honor.",
            "Dost thou wish to continue thy quest?",
            # if yes:
            f"Goodbye now, {self.game.player.name}.\n'Take care and tempt not the Fates.",
            # if no:
            # "Rest then for awhile."
        ), self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'])

    def test_travelers_inn(self):
        self.game.current_map = Alefgard()
        self.game.player.row, self.game.player.column = 48, 56
        # organically switch maps to Brecconary, as though entering from Alefgard
        for staircase_location, staircase_dict in self.game.current_map.staircases.items():
            self.game.process_staircase_warps(staircase_location, staircase_dict)
        self.assertEqual('Brecconary', self.game.current_map.identifier)
        self.game.player.current_hp = 1
        self.game.player.current_mp = 1
        self.game.player.direction_value = Direction.RIGHT.value
        self.game.cmd_menu.skip_text = True
        self.game.player.gold = 10
        self.game.player.row, self.game.player.column = 29, 18
        self.game.player.next_next_coordinates = get_next_coordinates(18, 29, self.game.player.direction_value, offset_from_character=2)
        self.game.player.next_tile_id = get_next_tile_identifier(self.game.player.column,
                                                                 self.game.player.row,
                                                                 self.game.player.direction_value,
                                                                 self.game.current_map)
        self.game.cmd_menu.talk()
        self.assertEqual(self.game.player.max_hp, self.game.player.current_hp)
        self.assertEqual(self.game.player.max_mp, self.game.player.current_mp)
        self.assertEqual(4, self.game.player.gold)
        self.game.player.current_hp = 2
        self.game.player.current_mp = 3
        self.game.cmd_menu.talk()
        self.assertEqual(2, self.game.player.current_hp)
        self.assertEqual(3, self.game.player.current_mp)
        self.assertEqual(4, self.game.player.gold)

    def test_load_and_play_music(self):
        with patch.object(Game, 'load_and_play_music', return_value=None) as mock_load_and_play_music:
            thing = Game()
            thing.load_and_play_music(village_music)
        mock_load_and_play_music.assert_called_with(village_music)

    def test_unlaunch_menu(self):
        self.game.cmd_menu.menu.enable()
        with patch.object(CommandMenu, 'window_drop_up_effect', return_value=None) as mock_window_drop_up_effect:
            self.assertFalse(self.game.cmd_menu.launch_signaled)
            self.game.unlaunch_menu(self.game.cmd_menu)
            self.assertTrue(self.game.enable_animate)
            self.assertTrue(self.game.enable_roaming)
            self.assertTrue(self.game.enable_movement)
            self.assertFalse(self.game.cmd_menu.menu.is_enabled())
        mock_window_drop_up_effect.assert_called_with(x=6, y=1, width=8, height=5)

    def test_handle_initial_dialog(self):
        self.game.skip_text = True
        self.game.initial_dialog_enabled = True
        self.game.is_initial_dialog = True
        self.game.current_map.identifier = 'TantegelThroneRoom'
        self.assertEqual(('Descendant of Erdrick, listen now to my words.',
                          'It is told that in ages past Erdrick fought demons with a Ball of Light.',
                          'Then came the Dragonlord who stole the precious globe and hid it in the '
                          'darkness.',
                          'Now, Edward, thou must help us recover the Ball of Light and restore peace '
                          'to our land.',
                          'The Dragonlord must be defeated.',
                          'Take now whatever thou may find in these Treasure Chests to aid thee in thy '
                          'quest.',
                          'Then speak with the guards, for they have much knowledge that may aid thee.',
                          'May the light shine upon thee, Edward.'),
                         self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'])
        self.game.handle_initial_dialog()
        self.assertFalse(self.game.display_hovering_stats)
        self.assertFalse(self.game.cmd_menu.launch_signaled)
        self.assertFalse(self.game.enable_movement)
        self.assertFalse(self.game.is_initial_dialog)
        self.assertTrue(self.game.automatic_initial_dialog_run)
        self.assertEqual('When thou art finished preparing for thy departure, please see me.\nI shall wait.',
                         self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'])
        self.game.allow_save_prompt = True
        self.game.handle_initial_dialog()
        self.assertEqual(('I am greatly pleased that thou hast returned, Edward.',
                          'Before reaching thy next level of experience thou must gain 7 Points.',
                          "Will thou tell me now of thy deeds so they won't be forgotten?",
                          'Thy deeds have been recorded on the Imperial Scrolls of Honor.',
                          'Dost thou wish to continue thy quest?',
                          "Goodbye now, Edward.\n'Take care and tempt not the Fates."),
                         self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'])
        # self.game.handle_initial_dialog()
        # self.assertFalse(self.game.is_initial_dialog)

    def test_drop_down_hovering_stats_window(self):
        with patch.object(CommandMenu, 'window_drop_down_effect', return_value=None) as mock_window_drop_down_effect:
            self.game.cmd_menu.window_drop_down_effect(1, 2, 4, 6)
            self.game.hovering_stats_displayed = True
            self.assertTrue(self.game.hovering_stats_displayed)
        mock_window_drop_down_effect.assert_called_with(1, 2, 4, 6)

    def test_handle_select_button(self):
        pygame.key.get_pressed = create_key_mock(pygame.K_u)
        self.game.handle_select_button(pygame.key.get_pressed())

    def test_handle_help_button(self):
        with patch.object(CommandMenu, 'show_text_in_dialog_box', return_value=None) as mock_show_text_in_dialog_box:
            pygame.key.get_pressed = create_f1_key_mock(pygame.K_F1)
            self.game.handle_help_button(pygame.key.get_pressed())
        mock_show_text_in_dialog_box.assert_called_with(f"Controls:\n{convert_list_to_newline_separated_string(controls)}")

    def test_handle_keypresses(self):
        pygame.key.get_pressed = create_f1_key_mock(pygame.K_k)
        self.game.handle_keypresses(pygame.key.get_pressed())
        pygame.key.get_pressed = create_f1_key_mock(pygame.K_j)
        self.game.handle_keypresses(pygame.key.get_pressed())

    def test_get_events(self):
        self.game.get_events()
        # this is a weird value for the player current tile
        self.assertEqual('ROAMING_GUARD', self.game.player.current_tile)
        self.assertEqual((0, -1), self.game.player.next_coordinates)
        self.assertEqual((1, -1), self.game.player.next_next_coordinates)
        self.game.enable_roaming = True
        self.game.player.row = 10
        self.game.player.column = 13
        self.game.current_map.staircases = {(10, 13): {'map': 'TantegelThroneRoom', 'destination_coordinates': (14, 18)}}
        self.game.change_map(TantegelThroneRoom())
        self.game.get_events()

    def test_draw_all(self):
        self.game.draw_all()
        self.assertTrue(self.game.not_moving_time_start)

    # def test_handle_sprite_drawing_and_animation(self):
    #     self.game.handle_sprite_drawing_and_animation()

    def test_move_roaming_characters(self):
        # test with no roaming characters
        self.game.move_roaming_characters()
        self.game.player.row = 10
        self.game.player.column = 13
        self.game.current_map.staircases = {(10, 13): {'map': 'TantegelThroneRoom', 'destination_coordinates': (14, 18)}}
        self.game.change_map(TantegelThroneRoom())
        self.game.current_map.load_map(self.game.player, (14, 18))
        # test with moving characters before they're moving
        for roaming_character in self.game.current_map.roaming_characters:
            self.assertFalse(roaming_character.is_moving)
        self.game.move_roaming_characters()
        for roaming_character in self.game.current_map.roaming_characters:
            self.assertTrue(roaming_character.is_moving)
        # test with moving characters once they're moving
        self.game.move_roaming_characters()

    def test_move_and_handle_sides_collision(self):
        self.game.player.rect.x = -1
        self.game.move_and_handle_sides_collision(-1, 1)
        self.assertEqual(0, self.game.player.rect.x)
        self.game.player.rect.y = -1
        self.game.move_and_handle_sides_collision(1, -1)
        self.assertEqual(0, self.game.player.rect.y)
        self.game.player.rect.x = 65
        self.game.move_and_handle_sides_collision(65, 1)
        self.assertEqual(64, self.game.player.rect.x)
        self.game.player.rect.y = 65
        self.game.move_and_handle_sides_collision(1, 65)
        self.assertEqual(64, self.game.player.rect.y)

    def test_move_player_up(self):
        pygame.key.get_pressed = create_move_player_key_mock(pygame.K_w)
        self.game.current_map.player_sprites = LayeredDirty(self.game.player)
        self.game.move_player(pygame.key.get_pressed())
        self.assertEqual(Direction.UP.value, self.game.player.direction_value)

    def test_move_player_left(self):
        pygame.key.get_pressed = create_move_player_key_mock(pygame.K_a)
        self.game.current_map.player_sprites = LayeredDirty(self.game.player)
        self.game.move_player(pygame.key.get_pressed())
        self.assertEqual(Direction.LEFT.value, self.game.player.direction_value)

    def test_move_player_down(self):
        pygame.key.get_pressed = create_move_player_key_mock(pygame.K_s)
        self.game.current_map.player_sprites = LayeredDirty(self.game.player)
        self.game.move_player(pygame.key.get_pressed())
        self.assertEqual(Direction.DOWN.value, self.game.player.direction_value)

    def test_move_player_right(self):
        pygame.key.get_pressed = create_move_player_key_mock(pygame.K_d)
        self.game.current_map.player_sprites = LayeredDirty(self.game.player)
        self.game.move_player(pygame.key.get_pressed())
        self.assertEqual(Direction.RIGHT.value, self.game.player.direction_value)

    def test_flags(self):
        self.game.fullscreen_enabled = False
        self.game.__init__()
        self.assertEqual(RESIZABLE | SCALED, self.game.flags)
        # self.game.fullscreen_enabled = True
        # self.game.__init__()
        # self.assertEqual(FULLSCREEN, self.game.flags)

    # this test fails in GitHub Actions

    # def test_show_main_menu_screen(self):
    #     mocked_return = MagicMock()
    #     mocked_return.type = KEYDOWN
    #     mocked_return.key = K_RETURN
    #     with patch.object(event, 'get', return_value=[mocked_return]) as mock_method:
    #         self.game.show_main_menu_screen(self.game.screen)

    # this test fails in GitHub Actions

    # @mock.patch.object(menu_functions, "select_name", return_value="ed")
    # def test_show_main_menu_screen(self, mock_select_name):
    #     mocked_return = MagicMock()
    #     mocked_return.type = KEYDOWN
    #     mocked_return.key = K_RETURN
    #     with patch.object(event, 'get', return_value=[mocked_return]) as mock_method:
    #         self.game.show_main_menu_screen(self.game.screen)
    #     self.assertEqual(1, self.game.player.adventure_log)
    #     self.assertEqual('ed', self.game.player.name)
    #
    #     self.assertEqual(1, self.game.player.level)

    # self.assertEqual(1, self.game.player.strength)
    # self.assertEqual(1, self.game.player.agility)
    # self.assertEqual(15, self.game.player.max_hp)
    # self.assertEqual(0, self.game.player.max_mp)
