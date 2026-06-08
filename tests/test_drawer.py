import os
import unittest
from unittest.mock import MagicMock, patch, call

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from src.config.test_config import test_config
from src.drawer import (
    replace_characters_with_underlying_tiles,
    get_surrounding_tile_values,
    convert_numeric_tile_list_to_unique_tile_values,
    get_fixed_character_underlying_tiles,
    Drawer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_LAYOUT = [
    [33, 0, 3],
    [1, 2, 3],
    [3, 3, 39],
]


def _make_drawer():
    """Build a Drawer with a fully-mocked game_state, bypassing all real init."""
    game_state = MagicMock()
    game_state.config = dict(test_config)  # real dict so key access works
    with patch('src.drawer.Graphics'), \
         patch('src.drawer.Directories'), \
         patch('src.drawer.Sound'), \
         patch('src.drawer.Calculation'):
        drawer = Drawer(game_state)
    return drawer


# ---------------------------------------------------------------------------
# replace_characters_with_underlying_tiles
# ---------------------------------------------------------------------------

class TestReplaceCharactersWithUnderlyingTiles(unittest.TestCase):

    def test_no_characters_returns_unchanged(self):
        tiles = ['GRASS', 'WATER', 'STONE']
        character_key = {}
        result = replace_characters_with_underlying_tiles(tiles, character_key)
        self.assertEqual(result, ['GRASS', 'WATER', 'STONE'])

    def test_replaces_single_character_tile(self):
        tiles = ['HERO', 'GRASS']
        character_key = {'HERO': {'underlying_tile': 'BRICK'}}
        result = replace_characters_with_underlying_tiles(tiles, character_key)
        self.assertNotIn('HERO', result)
        self.assertIn('BRICK', result)

    def test_replaces_multiple_character_tiles(self):
        tiles = ['HERO', 'GUARD', 'WATER']
        character_key = {
            'HERO': {'underlying_tile': 'GRASS'},
            'GUARD': {'underlying_tile': 'STONE'},
        }
        result = replace_characters_with_underlying_tiles(tiles, character_key)
        self.assertNotIn('HERO', result)
        self.assertNotIn('GUARD', result)
        self.assertIn('GRASS', result)
        self.assertIn('STONE', result)
        self.assertIn('WATER', result)

    def test_returns_list(self):
        result = replace_characters_with_underlying_tiles([], {})
        self.assertIsInstance(result, list)

    def test_no_match_leaves_list_unchanged(self):
        tiles = ['TREE', 'WALL']
        character_key = {'HERO': {'underlying_tile': 'GRASS'}}
        result = replace_characters_with_underlying_tiles(tiles, character_key)
        self.assertEqual(result, ['TREE', 'WALL'])


# ---------------------------------------------------------------------------
# get_surrounding_tile_values
# ---------------------------------------------------------------------------

class TestGetSurroundingTileValues(unittest.TestCase):

    def test_center_tile_returns_all_neighbors(self):
        result = get_surrounding_tile_values((1, 1), SAMPLE_LAYOUT)
        self.assertEqual(result, {0, 1, 2, 3})

    def test_top_left_corner(self):
        result = get_surrounding_tile_values((0, 0), SAMPLE_LAYOUT)
        self.assertEqual(result, {0, 1, 33})

    def test_top_right_corner(self):
        result = get_surrounding_tile_values((0, 2), SAMPLE_LAYOUT)
        self.assertEqual(result, {0, 3})

    def test_bottom_right_corner(self):
        result = get_surrounding_tile_values((2, 2), SAMPLE_LAYOUT)
        self.assertEqual(result, {3, 39})

    def test_bottom_left_corner(self):
        result = get_surrounding_tile_values((2, 0), SAMPLE_LAYOUT)
        self.assertEqual(result, {1, 3})

    def test_negative_x_treated_as_no_left_neighbor(self):
        # x < 0 guard prevents negative indexing on the left side
        result = get_surrounding_tile_values((-1, 2), SAMPLE_LAYOUT)
        # should not crash; returns some subset
        self.assertIsInstance(result, set)

    def test_out_of_bounds_row_returns_set(self):
        result = get_surrounding_tile_values((3, 2), SAMPLE_LAYOUT)
        self.assertIsInstance(result, set)

    def test_returns_set(self):
        result = get_surrounding_tile_values((1, 1), SAMPLE_LAYOUT)
        self.assertIsInstance(result, set)


# ---------------------------------------------------------------------------
# convert_numeric_tile_list_to_unique_tile_values
# ---------------------------------------------------------------------------

class TestConvertNumericTileList(unittest.TestCase):

    def test_converts_values_via_get_tile_by_value(self):
        current_map = MagicMock()
        current_map.get_tile_by_value.side_effect = lambda v: f'TILE_{v}'
        result = convert_numeric_tile_list_to_unique_tile_values(current_map, [1, 2, 3])
        self.assertIn('TILE_1', result)
        self.assertIn('TILE_2', result)
        self.assertIn('TILE_3', result)

    def test_deduplicates_values(self):
        current_map = MagicMock()
        current_map.get_tile_by_value.side_effect = lambda v: f'TILE_{v}'
        result = convert_numeric_tile_list_to_unique_tile_values(current_map, [5, 5, 5])
        # get_tile_by_value should be called once for the deduplicated value
        self.assertEqual(current_map.get_tile_by_value.call_count, 1)
        self.assertEqual(result, ['TILE_5'])

    def test_empty_list_returns_empty(self):
        current_map = MagicMock()
        result = convert_numeric_tile_list_to_unique_tile_values(current_map, [])
        self.assertEqual(result, [])

    def test_returns_list(self):
        current_map = MagicMock()
        current_map.get_tile_by_value.return_value = 'GRASS'
        result = convert_numeric_tile_list_to_unique_tile_values(current_map, [0])
        self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# get_fixed_character_underlying_tiles
# ---------------------------------------------------------------------------

class TestGetFixedCharacterUnderlyingTiles(unittest.TestCase):

    def test_returns_tile_name_for_each_fixed_character(self):
        current_map = MagicMock()
        char1 = MagicMock()
        char1.identifier = 'KING'
        current_map.fixed_characters = [char1]
        current_map.characters = {
            'KING': {'coordinates': (1, 2)}
        }
        current_map.layout = [[0, 1, 5], [10, 20, 30]]
        current_map.get_tile_by_value.return_value = 'THRONE'

        result = get_fixed_character_underlying_tiles(current_map)
        self.assertEqual(result, ['THRONE'])
        current_map.get_tile_by_value.assert_called_once_with(30)

    def test_empty_fixed_characters_returns_empty_list(self):
        current_map = MagicMock()
        current_map.fixed_characters = []
        result = get_fixed_character_underlying_tiles(current_map)
        self.assertEqual(result, [])

    def test_multiple_fixed_characters(self):
        current_map = MagicMock()
        char1 = MagicMock()
        char1.identifier = 'GUARD1'
        char2 = MagicMock()
        char2.identifier = 'GUARD2'
        current_map.fixed_characters = [char1, char2]
        current_map.characters = {
            'GUARD1': {'coordinates': (0, 0)},
            'GUARD2': {'coordinates': (0, 1)},
        }
        current_map.layout = [[7, 8]]
        current_map.get_tile_by_value.side_effect = lambda v: f'TILE_{v}'
        result = get_fixed_character_underlying_tiles(current_map)
        self.assertEqual(len(result), 2)


# ---------------------------------------------------------------------------
# Drawer.draw_stats_strings_with_alignments
# ---------------------------------------------------------------------------

class TestDrawerDrawStatsStrings(unittest.TestCase):

    def setUp(self):
        self.drawer = _make_drawer()

    @patch('src.drawer.draw_text')
    def test_one_digit_string(self, mock_draw_text):
        screen = MagicMock()
        self.drawer.draw_stats_strings_with_alignments('5', 3.0, screen, color=(255, 255, 255))
        mock_draw_text.assert_called_once()

    @patch('src.drawer.draw_text')
    def test_two_digit_string(self, mock_draw_text):
        screen = MagicMock()
        self.drawer.draw_stats_strings_with_alignments('42', 3.0, screen, color=(255, 255, 255))
        mock_draw_text.assert_called_once()

    @patch('src.drawer.draw_text')
    def test_three_digit_string(self, mock_draw_text):
        screen = MagicMock()
        self.drawer.draw_stats_strings_with_alignments('999', 3.0, screen, color=(255, 255, 255))
        mock_draw_text.assert_called_once()

    @patch('src.drawer.draw_text')
    def test_four_digit_string(self, mock_draw_text):
        screen = MagicMock()
        self.drawer.draw_stats_strings_with_alignments('1234', 3.0, screen, color=(255, 255, 255))
        mock_draw_text.assert_called_once()

    @patch('src.drawer.draw_text')
    def test_five_digit_string(self, mock_draw_text):
        screen = MagicMock()
        self.drawer.draw_stats_strings_with_alignments('12345', 3.0, screen, color=(255, 255, 255))
        mock_draw_text.assert_called_once()

    @patch('src.drawer.draw_text')
    def test_x_position_decreases_as_string_grows(self, mock_draw_text):
        """Longer strings are positioned further left (smaller x multiplier)."""
        screen = MagicMock()
        tile_size = test_config['TILE_SIZE']

        self.drawer.draw_stats_strings_with_alignments('1', 3.0, screen, color=(255, 255, 255))
        x_1digit = mock_draw_text.call_args[0][1]

        mock_draw_text.reset_mock()
        self.drawer.draw_stats_strings_with_alignments('12', 3.0, screen, color=(255, 255, 255))
        x_2digit = mock_draw_text.call_args[0][1]

        mock_draw_text.reset_mock()
        self.drawer.draw_stats_strings_with_alignments('123', 3.0, screen, color=(255, 255, 255))
        x_3digit = mock_draw_text.call_args[0][1]

        # Longer strings should use a smaller x-multiplier (positioned left of shorter ones)
        self.assertGreater(x_1digit, x_2digit)
        self.assertGreater(x_2digit, x_3digit)


# ---------------------------------------------------------------------------
# Drawer.handle_sprite_animation (static method)
# ---------------------------------------------------------------------------

class TestHandleSpriteAnimation(unittest.TestCase):

    def test_animate_called_when_enabled(self):
        character = MagicMock()
        character_dict = {'character': character}
        Drawer.handle_sprite_animation(True, character_dict)
        character.animate.assert_called_once()
        character.pause.assert_not_called()

    def test_pause_called_when_disabled(self):
        character = MagicMock()
        character_dict = {'character': character}
        Drawer.handle_sprite_animation(False, character_dict)
        character.pause.assert_called_once()
        character.animate.assert_not_called()

    def test_animate_not_called_when_disabled(self):
        character = MagicMock()
        character_dict = {'character': character}
        Drawer.handle_sprite_animation(False, character_dict)
        character.animate.assert_not_called()

    def test_pause_not_called_when_enabled(self):
        character = MagicMock()
        character_dict = {'character': character}
        Drawer.handle_sprite_animation(True, character_dict)
        character.pause.assert_not_called()


if __name__ == '__main__':
    unittest.main()
