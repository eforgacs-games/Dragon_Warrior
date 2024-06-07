import array
import os
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame
from pygame import K_UP, RESIZABLE, SCALED
from pygame.imageext import load_extended
from pygame.sprite import LayeredDirty
from pygame.transform import scale

from data.text.dialog_lookup_table import DialogLookup
from data.text.intro_lookup_table import ControlInfo
from src.calculation import get_tile_id_by_coordinates
from src.camera import Camera
from src.config.test_config import test_config
from src.direction import Direction
from src.drawer import replace_characters_with_underlying_tiles, convert_numeric_tile_list_to_unique_tile_values, \
    set_to_save_prompt
from src.game import Game
from src.game_functions import get_next_coordinates
from src.maps import TantegelThroneRoom, TantegelCourtyard, Alefgard
from src.maps_functions import parse_animated_sprite_sheet
from src.menu import CommandMenu
from src.menu_functions import convert_list_to_newline_separated_string
from src.music_player import MusicPlayer
from src.player.player import Player
from src.sprites.roaming_character import RoamingCharacter
from tests.mock_map import MockMap

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


def create_get_pressed_mock_array(max_key):
    return array.array('i', (0,)) * (max_key + 1)


def create_move_player_key_mock(pressed_key):
    def helper():
        tmp = create_get_pressed_mock_array(K_UP)
        tmp[pressed_key] = 1
        return tmp

    return helper


def setup_roaming_character(row, column, direction):
    test_roaming_character = RoamingCharacter(None, direction, None, 'ROAMING_GUARD')
    test_roaming_character.rect = MagicMock()
    test_roaming_character.row = row
    test_roaming_character.column = column
    return test_roaming_character


class TestGame(TestCase):

    def setUp(self) -> None:
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.game.player.name = "Edward"
        self.game.cmd_menu.dialog_lookup = DialogLookup(self.game.cmd_menu, self.game.game_state.config)
        self.game.current_map = MockMap(self.game.config)
        unarmed_hero_sheet = load_extended(self.game.directories.UNARMED_HERO_PATH)
        self.game.player = Player((0, 0), parse_animated_sprite_sheet(scale(unarmed_hero_sheet,
                                                                            (unarmed_hero_sheet.get_width() * self.game.config['SCALE'],
                                                                             unarmed_hero_sheet.get_height() * self.game.config['SCALE'])),
                                                                      self.game.game_state.config),
                                  self.game.current_map, god_mode=self.game.game_state.config['GOD_MODE'])
        # self.camera = Camera(self.game.current_map, self.initial_hero_location, speed=2)
        tile_size = self.game.game_state.config['TILE_SIZE']
        self.camera = Camera((self.game.player.rect.y // tile_size,
                              self.game.player.rect.x // tile_size),
                             self.game.current_map,
                             self.game.screen, tile_size)

    def test_get_initial_camera_position(self):
        self.assertEqual((288.0, 256.0), self.camera.pos)
        self.game.current_map.staircases = {
            (10, 13): {'map': 'TantegelThroneRoom', 'destination_coordinates': (14, 18)}}
        # self.game.change_map(TantegelThroneRoom())
        # self.assertEqual((-160.0, -96.0), self.camera.pos)
        # self.game.change_map(TantegelCourtyard())
        # self.assertEqual((-192.0, -224.0), self.camera.pos)

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
    #     self.assertEqual(initial_roaming_guard_position, )  # current roaming guard position

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

    @patch('src.menu.CommandMenu.show_text_in_dialog_box')
    def test_handle_fps_change_60(self, mock_show_text_in_dialog_box):
        keydown_event = pygame.event.Event(pygame.KEYDOWN, unicode="1", key=pygame.K_1, mod=pygame.KMOD_NONE)
        self.game.handle_fps_changes(keydown_event)
        self.assertEqual(60, self.game.fps)

    @patch('src.menu.CommandMenu.show_text_in_dialog_box')
    def test_handle_fps_change_120(self, mock_show_text_in_dialog_box):
        keydown_event = pygame.event.Event(pygame.KEYDOWN, unicode="2", key=pygame.K_2, mod=pygame.KMOD_NONE)
        self.game.handle_fps_changes(keydown_event)
        self.assertEqual(120, self.game.fps)

    @patch('src.menu.CommandMenu.show_text_in_dialog_box')
    def test_handle_fps_change_240(self, mock_show_text_in_dialog_box):
        keydown_event = pygame.event.Event(pygame.KEYDOWN, unicode="3", key=pygame.K_3, mod=pygame.KMOD_NONE)
        self.game.handle_fps_changes(keydown_event)
        self.assertEqual(240, self.game.fps)

    @patch('src.menu.CommandMenu.show_text_in_dialog_box')
    def test_handle_fps_change_480(self, mock_show_text_in_dialog_box):
        keydown_event = pygame.event.Event(pygame.KEYDOWN, unicode="4", key=pygame.K_4, mod=pygame.KMOD_NONE)
        self.game.handle_fps_changes(keydown_event)
        self.assertEqual(480, self.game.fps)

    def test_handle_start_button(self):
        self.assertFalse(self.game.paused)
        keydown_event = pygame.event.Event(pygame.KEYDOWN, unicode="i", key=pygame.K_i, mod=pygame.KMOD_NONE)
        self.game.handle_start_button(keydown_event)
        self.assertTrue(self.game.paused)
        keydown_event = pygame.event.Event(pygame.KEYDOWN, unicode="i", key=pygame.K_i, mod=pygame.KMOD_NONE)
        self.game.handle_start_button(keydown_event)
        self.assertFalse(self.game.paused)

    def test_handle_a_button_and_b_button(self):
        self.assertFalse(self.game.cmd_menu.launch_signaled)
        keydown_event = pygame.event.Event(pygame.KEYDOWN, unicode="k", key=pygame.K_k, mod=pygame.KMOD_NONE)
        # pygame.event.post(keydown_event)
        self.game.handle_a_button(keydown_event)
        self.assertTrue(self.game.cmd_menu.launch_signaled)
        keydown_event = pygame.event.Event(pygame.KEYDOWN, unicode="j", key=pygame.K_j, mod=pygame.KMOD_NONE)
        self.game.handle_b_button(keydown_event)
        self.assertFalse(self.game.cmd_menu.launch_signaled)

    def test_replace_characters_with_underlying_tiles(self):
        self.game.current_map.character_key['HERO']['underlying_tile'] = 'BRICK'
        self.assertEqual(['BRICK'],
                         replace_characters_with_underlying_tiles(['HERO'], self.game.current_map.character_key))

    def test_convert_numeric_tile_list_to_unique_tile_values(self):
        self.assertEqual(['WALL',
                          'WOOD',
                          'BRICK',
                          'TREASURE_BOX',
                          'DOOR',
                          'BRICK_STAIR_DOWN',
                          'BRICK_STAIR_UP',
                          'BARRIER',
                          'WEAPON_SIGN'],
                         convert_numeric_tile_list_to_unique_tile_values(self.game.current_map,
                                                                         [1, 2, 3, 4, 5, 6, 7, 8, 9]))

    def test_handle_menu_launch(self):
        self.game.cmd_menu.launch_signaled = True
        self.game.drawer.handle_menu_launch(self.game.screen, self.game.cmd_menu, self.game.cmd_menu)
        self.assertTrue(self.game.cmd_menu.menu.is_enabled())
        self.game.drawer.handle_menu_launch(self.game.screen, self.game.cmd_menu, self.game.cmd_menu)

    def test_change_map(self):
        self.game.player.row = 10
        self.game.player.column = 13
        self.game.current_map.staircases = {
            (10, 13): {'map': 'TantegelThroneRoom', 'destination_coordinates': (14, 18)}}
        self.game.change_map(TantegelThroneRoom(self.game.config))
        self.assertEqual('MockMap', self.game.last_map.identifier)
        self.assertEqual('TantegelThroneRoom', self.game.current_map.identifier)
        self.game.player.row = 14
        self.game.player.column = 18
        self.game.last_map = TantegelThroneRoom(self.game.config)
        self.game.change_map(TantegelCourtyard(self.game.config))
        self.assertTrue(self.game.allow_save_prompt)
        self.game.music_enabled = False
        self.game.player.row = 14
        self.game.player.column = 14
        self.game.change_map(TantegelThroneRoom(self.game.config))

    def test_change_map_maintain_inventory_and_gold(self):
        self.game.player.row = 10
        self.game.player.column = 13
        self.game.player.gold = 120
        self.game.player.inventory = ['Torch']
        self.game.current_map.staircases = {
            (10, 13): {'map': 'TantegelThroneRoom', 'destination_coordinates': (14, 18)}}
        self.game.change_map(TantegelThroneRoom(self.game.config))
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
        self.game.drawer.set_to_post_initial_dialog(self.game.cmd_menu)
        self.assertEqual("When thou art finished preparing for thy departure, please see me.\nI shall wait.",
                         self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'])

    def test_wise_man_tantegel_courtyard_dialog(self):
        self.assertEqual("Edward's coming was foretold by legend. May the light shine upon "
                         'this brave warrior.',
                         self.game.cmd_menu.dialog_lookup.lookup_table['TantegelCourtyard']['WISE_MAN']['dialog'][0])

    # gives an IndexError: list index out of range because the constants for K_UP, etc. are huge
    # def test_move_player_directions(self):
    #     self.assertEqual(Direction.UP.value, self.game.player.direction_value)
    #     pygame.key.get_pressed = create_key_mock(pygame.K_s)
    #     self.game.move_player(pygame.key.get_pressed())
    #     self.assertEqual(Direction.DOWN.value, self.game.player.direction_value)

    def test_run_automatic_initial_dialog(self):
        self.assertTrue(self.game.game_state.is_initial_dialog)
        self.game.drawer.run_automatic_initial_dialog(self.game.events, self.game.skip_text, self.game.cmd_menu)
        self.assertFalse(self.game.game_state.enable_movement)
        # TODO(ELF): Need to enable the following checks:
        # self.assertFalse(self.game.is_initial_dialog)
        # self.assertTrue(self.game.game_state.automatic_initial_dialog_run)

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
        set_to_save_prompt(self.game.cmd_menu)
        self.assertEqual((
            f"I am greatly pleased that thou hast returned, {self.game.player.name}.",
            f"Before reaching thy next level of experience thou must gain {self.game.player.points_to_next_level} Points.",
            # "Will thou tell me now of thy deeds so they won't be forgotten?",
            # if yes:
            # "Thy deeds have been recorded on the Imperial Scrolls of Honor.",
            # "Dost thou wish to continue thy quest?",
            # if yes:
            # f"Goodbye now, {self.game.player.name}.\n'Take care and tempt not the Fates.",
            # if no:
            # "Rest then for awhile."
        ), (self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][0],
            self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][1],
            # self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][2],
            # self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][3],
            # self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][4],
            ))

    @patch('src.menu.CommandMenu.show_text_line_in_dialog_box')
    @patch('src.menu.CommandMenu.window_drop_up_effect')
    @patch('src.menu.CommandMenu.window_drop_down_effect')
    @patch('src.visual_effects.fade')
    def test_travelers_inn(self, mock_show_text_line_in_dialog_box, mock_window_drop_up_effect,
                           mock_window_drop_down_effect, mock_fade):
        self.game.current_map = Alefgard(self.game.config)
        self.game.player.row, self.game.player.column = 48, 56
        # organically switch maps to Brecconary, as though entering from Alefgard
        for staircase_location, staircase_dict in self.game.current_map.staircases.items():
            self.game.process_staircase_warps(staircase_location, staircase_dict)
        self.game.player.current_hp = 1
        self.game.player.current_mp = 1
        self.game.player.direction_value = Direction.RIGHT.value
        self.game.current_map.load_map(self.game.player, (23, 10), self.game.tile_size)
        self.assertEqual('Brecconary', self.game.current_map.identifier)
        self.assertTrue('MERCHANT_2' in self.game.current_map.characters)
        self.assertTrue(self.game.current_map.characters['MERCHANT_2']['coordinates'] == (29, 20))
        self.assertEqual((23, 10), self.game.current_map.destination_coordinates)
        self.assertEqual((23, 10), self.game.current_map.initial_coordinates)
        self.game.cmd_menu.skip_text = True
        self.game.player.gold = 10
        self.game.player.row, self.game.player.column = 29, 18
        self.game.player.next_next_coordinates = get_next_coordinates(18, 29, self.game.player.direction_value,
                                                                      offset_from_character=2)
        self.assertEqual((29, 20), self.game.player.next_next_coordinates)
        self.assertEqual('BRICK', get_tile_id_by_coordinates(self.game.player.next_next_coordinates[1],
                                                             self.game.player.next_next_coordinates[0],
                                                             self.game.current_map))
        self.game.player.next_tile_id = self.game.calculation.get_next_tile_identifier(self.game.player.column,
                                                                                       self.game.player.row,
                                                                                       self.game.player.direction_value,
                                                                                       self.game.current_map)
        self.assertEqual('WOOD', self.game.player.next_tile_id)
        self.game.player.next_coordinates = get_next_coordinates(self.game.player.column, self.game.player.row,
                                                                 direction=self.game.player.direction_value)
        self.assertEqual((29, 19), self.game.player.next_coordinates)
        self.game.cmd_menu.talk()
        self.assertEqual(self.game.player.max_hp, self.game.player.current_hp)
        self.assertEqual(self.game.player.max_mp, self.game.player.current_mp)
        # checking that it won't work if you don't have enough gold
        self.assertEqual(4, self.game.player.gold)
        self.game.player.current_hp = 2
        self.game.player.current_mp = 3
        self.game.cmd_menu.talk()
        self.assertEqual(2, self.game.player.current_hp)
        self.assertEqual(3, self.game.player.current_mp)
        self.assertEqual(4, self.game.player.gold)

    def test_unlaunch_menu(self):
        self.game.cmd_menu.menu.enable()
        with patch.object(CommandMenu, 'window_drop_up_effect', return_value=None) as mock_window_drop_up_effect:
            self.assertFalse(self.game.cmd_menu.launch_signaled)
            self.game.unlaunch_menu(self.game.cmd_menu)
            self.assertTrue(self.game.enable_animate)
            self.assertTrue(self.game.enable_roaming)
            self.assertTrue(self.game.game_state.enable_movement)
            self.assertFalse(self.game.cmd_menu.menu.is_enabled())
        mock_window_drop_up_effect.assert_called_with(6, 1, 8, 5)

    @patch('src.menu.CommandMenu.show_text_in_dialog_box')
    def test_handle_initial_dialog(self, mock_show_text_in_dialog_box):
        self.game.initial_dialog_enabled = True
        self.game.skip_text = True
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
        self.game.drawer.handle_initial_dialog(self.game.initial_dialog_enabled, self.game.cmd_menu, self.game.events,
                                               self.game.skip_text, self.game.allow_save_prompt)
        self.assertFalse(self.game.drawer.display_hovering_stats)
        self.assertFalse(self.game.cmd_menu.launch_signaled)
        self.assertTrue(self.game.game_state.automatic_initial_dialog_run)
        self.assertEqual('When thou art finished preparing for thy departure, please see me.\nI shall wait.',
                         self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'])
        self.game.allow_save_prompt = True
        self.game.drawer.handle_initial_dialog(self.game.initial_dialog_enabled, self.game.cmd_menu, self.game.events,
                                               self.game.skip_text, self.game.allow_save_prompt)
        self.assertFalse(self.game.game_state.is_initial_dialog)
        self.assertEqual(('I am greatly pleased that thou hast returned, Edward.',
                          'Before reaching thy next level of experience thou must gain 7 Points.',
                          # "Will thou tell me now of thy deeds so they won't be forgotten?",
                          # 'Thy deeds have been recorded on the Imperial Scrolls of Honor.',
                          # 'Dost thou wish to continue thy quest?',
                          # "Goodbye now, Edward.\n'Take care and tempt not the Fates."),
                          ),
                         (
                         self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][0],
                         self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][1],
                         # self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][2],
                         # self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][3],
                         # self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][4],
                         # self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][5]
                         ))
        self.assertFalse(self.game.game_state.is_initial_dialog)

    def test_drop_down_hovering_stats_window(self):
        with patch.object(CommandMenu, 'window_drop_down_effect', return_value=None) as mock_window_drop_down_effect:
            self.game.cmd_menu.window_drop_down_effect(1, 2, 4, 6)
            self.game.hovering_stats_displayed = True
            self.assertTrue(self.game.hovering_stats_displayed)
        mock_window_drop_down_effect.assert_called_with(1, 2, 4, 6)

    # select button doesn't do anything (for now). Commenting it out to keep the unit tests fast.

    # def test_handle_select_button(self):
    #     pygame.key.get_pressed = create_key_mock_u(pygame.K_u)
    #     self.game.handle_select_button(pygame.key.get_pressed())

    def test_handle_help_button(self):
        with patch.object(CommandMenu, 'show_text_in_dialog_box', return_value=None) as mock_show_text_in_dialog_box:
            keydown_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1, mod=pygame.KMOD_NONE)
            self.game.handle_help_button(keydown_event)
        control_info = ControlInfo(test_config)
        mock_show_text_in_dialog_box.assert_called_with(
            f"Controls:\n{convert_list_to_newline_separated_string(control_info.controls)}")

    # def test_handle_keypresses(self):
    #     pygame.key.get_pressed = create_f1_key_mock(pygame.K_k)
    #     self.game.handle_keypresses(pygame.key.get_pressed())
    #     pygame.key.get_pressed = create_f1_key_mock(pygame.K_j)
    #     self.game.handle_keypresses(pygame.key.get_pressed())

    def test_get_events(self):
        self.game.get_events()
        # this is a weird value for the player current tile
        self.assertEqual('SOLDIER', self.game.player.current_tile)
        self.assertEqual((0, -1), self.game.player.next_coordinates)
        self.assertEqual((1, -1), self.game.player.next_next_coordinates)
        self.game.enable_roaming = True
        self.game.player.row = 10
        self.game.player.column = 13
        self.game.current_map.staircases = {
            (10, 13): {'map': 'TantegelThroneRoom', 'destination_coordinates': (14, 18)}}
        self.game.change_map(TantegelThroneRoom(self.game.config))
        self.game.get_events()

    def test_draw_all(self):
        self.game.drawer.draw_all(self.game.screen, self.game.loop_count, self.game.big_map, self.game.current_map,
                                  self.game.player, self.game.cmd_menu, self.game.foreground_rects,
                                  self.game.enable_animate, self.game.camera, self.game.initial_dialog_enabled,
                                  self.game.events, self.game.skip_text, self.game.allow_save_prompt,
                                  self.game.game_state, self.game.torch_active, self.game.color)
        self.assertTrue(self.game.drawer.not_moving_time_start)

    # def test_handle_sprite_drawing_and_animation(self):
    #     self.game.handle_sprite_drawing_and_animation()

    def test_move_roaming_characters(self):
        # test with no roaming characters
        self.game.move_roaming_characters()
        self.game.player.row = 10
        self.game.player.column = 13
        self.game.current_map.staircases = {
            (10, 13): {'map': 'TantegelThroneRoom', 'destination_coordinates': (14, 18)}}
        self.game.change_map(TantegelThroneRoom(self.game.config))
        self.game.current_map.load_map(self.game.player, (14, 18), self.game.game_state.config["TILE_SIZE"])
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
        self.assertEqual(self.game.player.rect.y, -16)
        self.game.move_player(pygame.key.get_pressed())
        self.assertEqual(self.game.player.rect.y, -18)
        self.assertEqual(Direction.UP.value, self.game.player.direction_value)

    def test_move_player_left(self):
        pygame.key.get_pressed = create_move_player_key_mock(pygame.K_a)
        self.game.current_map.player_sprites = LayeredDirty(self.game.player)
        self.assertEqual(self.game.player.rect.x, -16)
        self.game.move_player(pygame.key.get_pressed())
        self.assertEqual(self.game.player.rect.x, 0)
        self.assertEqual(Direction.LEFT.value, self.game.player.direction_value)

    def test_move_player_down(self):
        pygame.key.get_pressed = create_move_player_key_mock(pygame.K_s)
        self.game.current_map.player_sprites = LayeredDirty(self.game.player)
        self.assertEqual(self.game.player.rect.y, -16)
        self.game.move_player(pygame.key.get_pressed())
        # impassable object in way of player
        self.assertEqual(self.game.player.rect.y, -16)
        self.assertEqual(Direction.DOWN.value, self.game.player.direction_value)

    def test_move_player_right(self):
        pygame.key.get_pressed = create_move_player_key_mock(pygame.K_d)
        self.game.current_map.player_sprites = LayeredDirty(self.game.player)
        self.assertEqual(self.game.player.rect.x, -16)
        self.game.move_player(pygame.key.get_pressed())
        self.assertEqual(self.game.player.rect.x, 0)
        self.assertEqual(Direction.RIGHT.value, self.game.player.direction_value)

    @patch('src.game.Game.set_screen')
    def test_flags_fullscreen_disabled(self, mock_set_screen):
        self.game.fullscreen_enabled = False
        self.game.__init__(test_config)
        self.assertEqual(RESIZABLE | SCALED, self.game.flags)

    @patch('src.game.Game.set_screen')
    def test_flags_fullscreen_enabled(self, mock_set_screen):
        self.game.fullscreen_enabled = True
        self.game.__init__(test_config)
        # seems like an integer overflow happens if we try:
        # self.assertEqual(FULLSCREEN | SCALED, self.game.flags)
        self.assertEqual(528, self.game.flags)

    @patch('src.game.Game.set_screen')
    @patch.object(MusicPlayer, "load_and_play_music")
    def test_splash_screen_enabled_load_and_play_music(self, mock_load_and_play_music, mock_set_screen):
        self.game.__init__(test_config)
        mock_load_and_play_music.assert_called_once_with(self.game.directories.intro_overture)

    # @patch('src.config')
    # def test_splash_screen_disabled_load_and_play_music(self, mocked_config):
    #     # self.game.splash_screen_enabled = False
    #     with patch.object(Game, 'load_and_play_music') as mock_method:
    #         self.game.__init__()
    #     mock_method.assert_called_once_with(self.game.current_map.music_file_path)

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
