from unittest import TestCase, mock
from unittest.mock import MagicMock, patch

from pygame import KEYDOWN, K_RETURN, event, K_s, K_w
from pygame.image import load_extended
from pygame.time import get_ticks
from pygame.transform import scale

from src import drawer
from src.camera import Camera
from src.config.test_config import test_config
from src.drawer import Drawer
from src.game_functions import set_character_position
from src.windows import ADVENTURE_LOG_123_LAYOUT, NEW_QUEST_LAYOUT
from src.maps_functions import parse_animated_sprite_sheet
from src.npc_movement import step
from src.player.player import Player
from tests.mock_map import MockMap
from tests.helpers import new_game

layout = [[33, 0, 3],
          [1, 2, 3],
          [3, 3, 3]]


class TestGameFunctions(TestCase):

    def setUp(self) -> None:
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        self.game = new_game()
        self.game.camera_pos = 0, 0
        self.center_pt = 0, 0
        self.game.current_map = MockMap(self.game.config)
        self.initial_hero_location = self.game.current_map.initial_coordinates
        unarmed_hero_sheet = load_extended(self.game.directories.UNARMED_HERO_PATH)
        self.hero_images = parse_animated_sprite_sheet(scale(unarmed_hero_sheet, (
            unarmed_hero_sheet.get_width() * test_config['SCALE'], unarmed_hero_sheet.get_height() * test_config['SCALE'])),
                                                       self.game.game_state.config)
        self.game.current_map.player = Player(self.center_pt, self.hero_images, self.game.current_map,
                                              god_mode=test_config['GOD_MODE'])
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

    def test_step(self):
        # TODO(ELF): this test fails if the initial current map is not set to TantegelThroneRoom...might need work.
        self.game.player.direction_value = 0
        self.assertEqual((11, 13),
                         step(self.game.player.rect.y // self.game.game_state.config['TILE_SIZE'],
                              self.game.player.rect.x // self.game.game_state.config['TILE_SIZE'],
                              self.game.player.direction_value))
        self.game.player.direction_value = 1
        self.assertEqual((10, 12),
                         step(self.game.player.rect.y // self.game.game_state.config['TILE_SIZE'],
                              self.game.player.rect.x // self.game.game_state.config['TILE_SIZE'],
                              self.game.player.direction_value))
        self.game.player.direction_value = 2
        self.assertEqual((9, 13),
                         step(self.game.player.rect.y // self.game.game_state.config['TILE_SIZE'],
                              self.game.player.rect.x // self.game.game_state.config['TILE_SIZE'],
                              self.game.player.direction_value))
        self.game.player.direction_value = 3
        self.assertEqual((10, 14),
                         step(self.game.player.rect.y // self.game.game_state.config['TILE_SIZE'],
                              self.game.player.rect.x // self.game.game_state.config['TILE_SIZE'],
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
            self.game.drawer.draw_stats_strings_with_alignments("12345", 1, self.game.screen, self.game.color)
            mocked_draw_text.assert_called_once_with("12345", 102.4, 32, self.game.screen, self.game.game_state.config,
                                                     color=(255, 255, 255), alignment='center', letter_by_letter=False)
            self.game.drawer.draw_stats_strings_with_alignments("1234", 1, self.game.screen, self.game.color)
            mocked_draw_text.assert_called_with("1234", 110.08, 32, self.game.screen, self.game.game_state.config,
                                                color=(255, 255, 255), alignment='center', letter_by_letter=False)
            self.game.drawer.draw_stats_strings_with_alignments("123", 1, self.game.screen, self.game.color)
            mocked_draw_text.assert_called_with("123", 117.44, 32, self.game.screen, self.game.game_state.config,
                                                color=(255, 255, 255), alignment='center', letter_by_letter=False)
            self.game.drawer.draw_stats_strings_with_alignments("12", 1, self.game.screen, self.game.color)
            mocked_draw_text.assert_called_with("12", 127.68, 32, self.game.screen, self.game.game_state.config,
                                                color=(255, 255, 255), alignment='center', letter_by_letter=False)
            self.game.drawer.draw_stats_strings_with_alignments("1", 1, self.game.screen, self.game.color)
            mocked_draw_text.assert_called_with("1", 134.4, 32, self.game.screen, self.game.game_state.config,
                                                color=(255, 255, 255), alignment='center', letter_by_letter=False)

    # "1", 134.4, 32, self.game.screen

    def test_main_menu_selection_draws_the_generated_windows(self):
        # The window chosen from, with its blinking arrow, over the windows below it with their arrows held on
        drawn = []
        with patch.dict(self.game.game_functions.config, NO_BLIT=False), \
                patch('src.game_functions.draw_title_windows', side_effect=lambda screen, windows, *args:
                      drawn.append(windows)), patch('src.game_functions.display'), \
                patch.object(event, 'get', return_value=[self.key(K_RETURN)]):
            self.assertEqual(0, self.game.game_functions.main_menu_selection(
                get_ticks(), self.game.screen, ADVENTURE_LOG_123_LAYOUT, below=[(NEW_QUEST_LAYOUT, 0)]))
        self.assertEqual([(NEW_QUEST_LAYOUT, 0, True), (ADVENTURE_LOG_123_LAYOUT, 0, True)], drawn[-1])

    @staticmethod
    def key(key):
        pressed = MagicMock()
        pressed.type = KEYDOWN
        pressed.key = key
        return pressed

    def select(self, keys, layout=ADVENTURE_LOG_123_LAYOUT, blink_start=None):
        with patch.object(event, 'get', return_value=[self.key(key) for key in keys]):
            return self.game.game_functions.main_menu_selection(
                get_ticks() if blink_start is None else blink_start, self.game.screen, layout)

    def test_select_from_vertical_menu(self):
        self.assertEqual(0, self.select([K_RETURN]))
        self.assertEqual(0, self.select([K_w, K_RETURN]))
        self.assertEqual(1, self.select([K_s, K_RETURN]))
        self.assertEqual(2, self.select([K_s, K_s, K_RETURN]))
        self.assertEqual(1, self.select([K_s, K_s, K_w, K_RETURN]))
        # a window of one entry
        start_time = get_ticks()
        while get_ticks() - start_time <= 64:
            # just to hit the blink_start reset line
            self.assertEqual(0, self.select([K_s, K_s, K_w, K_RETURN], NEW_QUEST_LAYOUT, start_time))
        self.assertEqual(0, self.select([K_s, K_s, K_w, K_RETURN], NEW_QUEST_LAYOUT, start_time))
