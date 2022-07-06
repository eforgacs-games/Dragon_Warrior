import os
from unittest import TestCase, mock
from unittest.mock import MagicMock, patch

from pygame import KEYDOWN, K_RETURN, event, K_s, K_w
from pygame.image import load_extended
from pygame.time import get_ticks
from pygame.transform import scale

from src import game_functions, text
from src.camera import Camera
from src.common import Direction, UNARMED_HERO_PATH, NAME_SELECTION_UPPER_A, NAME_SELECTION_STATIC_IMAGE_LEN_0, ADVENTURE_LOG_PATH, ADVENTURE_LOG_1_PATH, \
    ADVENTURE_LOG_2_PATH, ADVENTURE_LOG_3_PATH, BEGIN_QUEST_PATH, BEGIN_QUEST_SELECTED_PATH
from src.config import TILE_SIZE, SCALE
from src.game import Game
from src.game_functions import get_next_coordinates, set_character_position, draw_hovering_stats_window, draw_stats_strings_with_alignments, alternate_blink, \
    select_from_vertical_menu
from src.maps import MapWithoutNPCs
from src.maps_functions import parse_animated_sprite_sheet
from src.player.player import Player

os.environ['SDL_VIDEODRIVER'] = 'dummy'
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


class TestGameFunctions(TestCase):

    def setUp(self) -> None:
        with patch('src.game.SCALED'):
            self.game = Game()
        self.game.camera_pos = 0, 0
        self.center_pt = 0, 0
        self.game.current_map = MockMap()
        self.initial_hero_location = self.game.current_map.get_initial_character_location('HERO')
        unarmed_hero_sheet = load_extended(UNARMED_HERO_PATH)
        self.hero_images = parse_animated_sprite_sheet(
            scale(unarmed_hero_sheet, (unarmed_hero_sheet.get_width() * SCALE, unarmed_hero_sheet.get_height() * SCALE)))
        self.game.current_map.player = Player(self.center_pt, self.hero_images, self.game.current_map)
        self.camera = Camera((self.game.current_map.player.rect.y // TILE_SIZE, self.game.current_map.player.rect.x // TILE_SIZE), self.game.current_map,
                             None)

    def test_set_character_position(self):
        # TODO(ELF): this test fails if the initial current map is not set to TantegelThroneRoom...might need work.
        self.game.player.column = 13
        self.game.player.row = 10
        self.assertEqual(13, self.game.player.column)
        self.assertEqual(10, self.game.player.row)
        self.assertEqual(13, self.game.player.rect.x // TILE_SIZE)
        self.assertEqual(10, self.game.player.rect.y // TILE_SIZE)
        set_character_position(self.game.player)
        self.assertEqual((self.game.player.column, self.game.player.row), (self.game.player.rect.x // TILE_SIZE, self.game.player.rect.y // TILE_SIZE))
        self.assertEqual((self.game.player.column, self.game.player.row), (13, 10))

    def test_get_next_coordinates(self):
        # TODO(ELF): this test fails if the initial current map is not set to TantegelThroneRoom...might need work.
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

    @mock.patch.object(game_functions, "draw_stats_strings_with_alignments")
    def test_draw_hovering_stats_window(self, mock_draw_stats_strings_with_alignments):
        self.game.player.level = 7
        self.game.player.current_hp = 50
        self.game.player.current_mp = 25
        self.game.player.gold = 8
        self.game.player.total_experience = 1984
        draw_hovering_stats_window(self.game.screen, self.game.player)
        mock_draw_stats_strings_with_alignments.assert_any_call("7", 2.99, self.game.screen)
        mock_draw_stats_strings_with_alignments.assert_any_call("50", 3.99, self.game.screen)
        mock_draw_stats_strings_with_alignments.assert_any_call("25", 4.99, self.game.screen)
        mock_draw_stats_strings_with_alignments.assert_any_call("8", 5.99, self.game.screen)
        mock_draw_stats_strings_with_alignments.assert_called_with("1984", 6.99, self.game.screen)

    @mock.patch.object(text, "draw_text")
    def test_draw_stats_strings_with_alignments(self, mock_draw_text):
        self.assertIsNone(draw_stats_strings_with_alignments("12345", 1, self.game.screen))
        self.assertIsNone(draw_stats_strings_with_alignments("1234", 1, self.game.screen))
        self.assertIsNone(draw_stats_strings_with_alignments("123", 1, self.game.screen))
        self.assertIsNone(draw_stats_strings_with_alignments("12", 1, self.game.screen))
        self.assertIsNone(draw_stats_strings_with_alignments("1", 1, self.game.screen))
        # TODO(ELF): Assert that draw_text calls are made.
        # mock_draw_text.assert_any_call("12345", 3.2, self.game.cmd_menu.dialog_lookup.screen)
        # mock_draw_text.assert_any_call("12345", TILE_SIZE * 3.2, TILE_SIZE, self.game.screen)

    # "1", 134.4, 32, self.game.screen

    def test_alternate_blink(self):
        # TODO(ELF): Actually test something with test_alternate_blink().
        selected_image = NAME_SELECTION_UPPER_A
        unselected_image = NAME_SELECTION_STATIC_IMAGE_LEN_0
        alternate_blink(selected_image, unselected_image, get_ticks(), self.game.screen)

    def test_select_from_vertical_menu(self):
        mocked_return = MagicMock()
        mocked_return.type = KEYDOWN
        mocked_return.key = K_RETURN
        with patch.object(event, 'get', return_value=[mocked_return]) as mock_method:
            self.assertEqual(0, select_from_vertical_menu(get_ticks(), self.game.screen, ADVENTURE_LOG_PATH,
                                                          ADVENTURE_LOG_1_PATH,
                                                          [ADVENTURE_LOG_2_PATH, ADVENTURE_LOG_3_PATH]))
        mocked_up = MagicMock()
        mocked_up.type = KEYDOWN
        mocked_up.key = K_w
        with patch.object(event, 'get', return_value=[mocked_up, mocked_return]) as mock_method:
            self.assertEqual(0, select_from_vertical_menu(get_ticks(), self.game.screen, ADVENTURE_LOG_PATH,
                                                          ADVENTURE_LOG_1_PATH,
                                                          [ADVENTURE_LOG_2_PATH, ADVENTURE_LOG_3_PATH]))

        mocked_down = MagicMock()
        mocked_down.type = KEYDOWN
        mocked_down.key = K_s
        with patch.object(event, 'get', return_value=[mocked_down, mocked_return]) as mock_method:
            self.assertEqual(1, select_from_vertical_menu(get_ticks(), self.game.screen, ADVENTURE_LOG_PATH,
                                                          ADVENTURE_LOG_1_PATH,
                                                          [ADVENTURE_LOG_2_PATH, ADVENTURE_LOG_3_PATH]))

        with patch.object(event, 'get', return_value=[mocked_down, mocked_down, mocked_return]) as mock_method:
            self.assertEqual(2, select_from_vertical_menu(get_ticks(), self.game.screen, ADVENTURE_LOG_PATH,
                                                          ADVENTURE_LOG_1_PATH,
                                                          [ADVENTURE_LOG_2_PATH, ADVENTURE_LOG_3_PATH]))

        with patch.object(event, 'get', return_value=[mocked_down, mocked_down, mocked_up, mocked_return]) as mock_method:
            self.assertEqual(1, select_from_vertical_menu(get_ticks(), self.game.screen, ADVENTURE_LOG_PATH,
                                                          ADVENTURE_LOG_1_PATH,
                                                          [ADVENTURE_LOG_2_PATH, ADVENTURE_LOG_3_PATH]))
        # test without other_selected_images
        with patch.object(event, 'get', return_value=[mocked_down, mocked_down, mocked_up, mocked_return]) as mock_method:
            start_time = get_ticks()
            while get_ticks() - start_time <= 64:
                # just to hit the blink_start reset line
                self.assertEqual(0, select_from_vertical_menu(start_time, self.game.screen, BEGIN_QUEST_PATH, BEGIN_QUEST_SELECTED_PATH, []))
            self.assertEqual(0, select_from_vertical_menu(start_time, self.game.screen, BEGIN_QUEST_PATH, BEGIN_QUEST_SELECTED_PATH, []))
