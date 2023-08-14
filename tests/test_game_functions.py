import os
from unittest import TestCase, mock
from unittest.mock import MagicMock, patch

from pygame import KEYDOWN, K_RETURN, event, K_s, K_w, image
from pygame.image import load_extended
from pygame.time import get_ticks
from pygame.transform import scale

from src import drawer
from src.camera import Camera
from src.config import SCALE, prod_config
from src.direction import Direction
from src.drawer import Drawer
from src.game import Game
from src.game_functions import get_next_coordinates, set_character_position, select_from_vertical_menu, alternate_blink
from src.maps import MapWithoutNPCs
from src.maps_functions import parse_animated_sprite_sheet
from src.player.player import Player

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
layout = [[33, 0, 3],
          [1, 2, 3],
          [3, 3, 3]]


class MockMap(MapWithoutNPCs):
    def __init__(self, config):
        super().__init__(layout, config)

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.DOWN.value


class TestGameFunctions(TestCase):

    def setUp(self) -> None:
        prod_config['NO_WAIT'] = True
        prod_config['RENDER_TEXT'] = False
        prod_config['NO_BLIT'] = True
        with patch('src.game.SCALED'):
            self.game = Game(prod_config)
        self.game.camera_pos = 0, 0
        self.center_pt = 0, 0
        self.game.current_map = MockMap(self.game.config)
        self.initial_hero_location = self.game.current_map.get_initial_character_location('HERO')
        unarmed_hero_sheet = load_extended(self.game.directories.UNARMED_HERO_PATH)
        self.hero_images = parse_animated_sprite_sheet(scale(unarmed_hero_sheet, (
            unarmed_hero_sheet.get_width() * SCALE, unarmed_hero_sheet.get_height() * SCALE)),
                                                       self.game.game_state.config)
        self.game.current_map.player = Player(self.center_pt, self.hero_images, self.game.current_map,
                                              god_mode=prod_config['GOD_MODE'])
        tile_size = self.game.game_state.config['TILE_SIZE']
        self.camera = Camera(
            (self.game.current_map.player.rect.y // tile_size, self.game.current_map.player.rect.x // tile_size),
            self.game.current_map,
            None, tile_size)

    def test_set_character_position(self):
        # TODO(ELF): this test fails if the initial current map is not set to TantegelThroneRoom...might need work.
        self.game.player.column = 13
        self.game.player.row = 10
        self.assertEqual(13, self.game.player.column)
        self.assertEqual(10, self.game.player.row)
        tile_size = self.game.game_state.config['TILE_SIZE']
        self.assertEqual(13, self.game.player.rect.x // tile_size)
        self.assertEqual(10, self.game.player.rect.y // tile_size)
        set_character_position(self.game.player, tile_size)
        self.assertEqual((self.game.player.column, self.game.player.row),
                         (self.game.player.rect.x // tile_size, self.game.player.rect.y // tile_size))
        self.assertEqual((self.game.player.column, self.game.player.row), (13, 10))

    def test_get_next_coordinates(self):
        # TODO(ELF): this test fails if the initial current map is not set to TantegelThroneRoom...might need work.
        self.game.player.direction_value = 0
        self.assertEqual((11, 13),
                         get_next_coordinates(self.game.player.rect.x // self.game.game_state.config['TILE_SIZE'],
                                              self.game.player.rect.y // self.game.game_state.config['TILE_SIZE'],
                                              self.game.player.direction_value))
        self.game.player.direction_value = 1
        self.assertEqual((10, 12),
                         get_next_coordinates(self.game.player.rect.x // self.game.game_state.config['TILE_SIZE'],
                                              self.game.player.rect.y // self.game.game_state.config['TILE_SIZE'],
                                              self.game.player.direction_value))
        self.game.player.direction_value = 2
        self.assertEqual((9, 13),
                         get_next_coordinates(self.game.player.rect.x // self.game.game_state.config['TILE_SIZE'],
                                              self.game.player.rect.y // self.game.game_state.config['TILE_SIZE'],
                                              self.game.player.direction_value))
        self.game.player.direction_value = 3
        self.assertEqual((10, 14),
                         get_next_coordinates(self.game.player.rect.x // self.game.game_state.config['TILE_SIZE'],
                                              self.game.player.rect.y // self.game.game_state.config['TILE_SIZE'],
                                              self.game.player.direction_value))

    @mock.patch.object(Drawer, "draw_stats_strings_with_alignments")
    def test_draw_hovering_stats_window(self, mock_draw_stats_strings_with_alignments):
        self.game.player.level = 7
        self.game.player.current_hp = 50
        self.game.player.current_mp = 25
        self.game.player.gold = 8
        self.game.player.total_experience = 1984
        self.game.drawer.draw_hovering_stats_window(self.game.screen, self.game.player, self.game.color)
        mock_draw_stats_strings_with_alignments.assert_any_call("7", 2.99, self.game.screen, color=self.game.color)
        mock_draw_stats_strings_with_alignments.assert_any_call("50", 3.99, self.game.screen, color=self.game.color)
        mock_draw_stats_strings_with_alignments.assert_any_call("25", 4.99, self.game.screen, color=self.game.color)
        mock_draw_stats_strings_with_alignments.assert_any_call("8", 5.99, self.game.screen, color=self.game.color)
        mock_draw_stats_strings_with_alignments.assert_called_with("1984", 6.99, self.game.screen,
                                                                   color=self.game.color)

    def test_draw_stats_strings_with_alignments(self):
        with patch.object(drawer, 'draw_text') as mocked_draw_text:
            self.game.drawer.draw_stats_strings_with_alignments("12345", 1, self.game.screen)
            mocked_draw_text.assert_called_once_with("12345", 102.4, 32, self.game.screen, self.game.game_state.config,
                                                     color=(255, 255, 255), alignment='center', letter_by_letter=False)
            self.game.drawer.draw_stats_strings_with_alignments("1234", 1, self.game.screen)
            mocked_draw_text.assert_called_with("1234", 110.08, 32, self.game.screen, self.game.game_state.config,
                                                color=(255, 255, 255), alignment='center', letter_by_letter=False)
            self.game.drawer.draw_stats_strings_with_alignments("123", 1, self.game.screen)
            mocked_draw_text.assert_called_with("123", 117.44, 32, self.game.screen, self.game.game_state.config,
                                                color=(255, 255, 255), alignment='center', letter_by_letter=False)
            self.game.drawer.draw_stats_strings_with_alignments("12", 1, self.game.screen)
            mocked_draw_text.assert_called_with("12", 127.68, 32, self.game.screen, self.game.game_state.config,
                                                color=(255, 255, 255), alignment='center', letter_by_letter=False)
            self.game.drawer.draw_stats_strings_with_alignments("1", 1, self.game.screen)
            mocked_draw_text.assert_called_with("1", 134.4, 32, self.game.screen, self.game.game_state.config,
                                                color=(255, 255, 255), alignment='center', letter_by_letter=False)

    # "1", 134.4, 32, self.game.screen

    def test_alternate_blink(self):
        selected_image_path = self.game.directories.NAME_SELECTION_UPPER_A
        unselected_image_path = self.game.directories.NAME_SELECTION_STATIC_IMAGE_LEN_0
        selected_image = scale(image.load(selected_image_path),
                               (self.game.screen.get_width(), self.game.screen.get_height())).get_rect()
        unselected_image = scale(image.load(unselected_image_path),
                                 (self.game.screen.get_width(), self.game.screen.get_height())).get_rect()
        with patch('pygame.display.update') as mock_update:
            alternate_blink(selected_image_path, unselected_image_path, get_ticks(), self.game.screen, False)
            mock_update.assert_called_with(selected_image)
            mock_update.assert_called_with(unselected_image)

    def test_select_from_vertical_menu(self):
        mocked_return = MagicMock()
        mocked_return.type = KEYDOWN
        mocked_return.key = K_RETURN
        with patch.object(event, 'get', return_value=[mocked_return]) as mock_method:
            self.assertEqual(0, select_from_vertical_menu(get_ticks(), self.game.screen,
                                                          self.game.directories.ADVENTURE_LOG_PATH,
                                                          self.game.directories.ADVENTURE_LOG_1_PATH,
                                                          [self.game.directories.ADVENTURE_LOG_2_PATH,
                                                           self.game.directories.ADVENTURE_LOG_3_PATH], no_blit=True))
        mocked_up = MagicMock()
        mocked_up.type = KEYDOWN
        mocked_up.key = K_w
        with patch.object(event, 'get', return_value=[mocked_up, mocked_return]) as mock_method:
            self.assertEqual(0, select_from_vertical_menu(get_ticks(), self.game.screen,
                                                          self.game.directories.ADVENTURE_LOG_PATH,
                                                          self.game.directories.ADVENTURE_LOG_1_PATH,
                                                          [self.game.directories.ADVENTURE_LOG_2_PATH,
                                                           self.game.directories.ADVENTURE_LOG_3_PATH], no_blit=True))

        mocked_down = MagicMock()
        mocked_down.type = KEYDOWN
        mocked_down.key = K_s
        with patch.object(event, 'get', return_value=[mocked_down, mocked_return]) as mock_method:
            self.assertEqual(1, select_from_vertical_menu(get_ticks(), self.game.screen,
                                                          self.game.directories.ADVENTURE_LOG_PATH,
                                                          self.game.directories.ADVENTURE_LOG_1_PATH,
                                                          [self.game.directories.ADVENTURE_LOG_2_PATH,
                                                           self.game.directories.ADVENTURE_LOG_3_PATH], no_blit=True))

        with patch.object(event, 'get', return_value=[mocked_down, mocked_down, mocked_return]) as mock_method:
            self.assertEqual(2, select_from_vertical_menu(get_ticks(), self.game.screen,
                                                          self.game.directories.ADVENTURE_LOG_PATH,
                                                          self.game.directories.ADVENTURE_LOG_1_PATH,
                                                          [self.game.directories.ADVENTURE_LOG_2_PATH,
                                                           self.game.directories.ADVENTURE_LOG_3_PATH], no_blit=True))

        with patch.object(event, 'get',
                          return_value=[mocked_down, mocked_down, mocked_up, mocked_return]) as mock_method:
            self.assertEqual(1, select_from_vertical_menu(get_ticks(), self.game.screen,
                                                          self.game.directories.ADVENTURE_LOG_PATH,
                                                          self.game.directories.ADVENTURE_LOG_1_PATH,
                                                          [self.game.directories.ADVENTURE_LOG_2_PATH,
                                                           self.game.directories.ADVENTURE_LOG_3_PATH], no_blit=True))
        # test without other_selected_images
        with patch.object(event, 'get',
                          return_value=[mocked_down, mocked_down, mocked_up, mocked_return]) as mock_method:
            start_time = get_ticks()
            while get_ticks() - start_time <= 64:
                # just to hit the blink_start reset line
                self.assertEqual(0, select_from_vertical_menu(start_time, self.game.screen,
                                                              self.game.directories.BEGIN_QUEST_PATH,
                                                              self.game.directories.BEGIN_QUEST_SELECTED_PATH, [],
                                                              no_blit=True))
            self.assertEqual(0, select_from_vertical_menu(start_time, self.game.screen,
                                                          self.game.directories.BEGIN_QUEST_PATH,
                                                          self.game.directories.BEGIN_QUEST_SELECTED_PATH, [],
                                                          no_blit=True))
