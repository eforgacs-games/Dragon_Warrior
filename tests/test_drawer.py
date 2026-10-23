import unittest
from unittest.mock import MagicMock, patch


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


# ---------------------------------------------------------------------------
# Drawer enemy effects
# ---------------------------------------------------------------------------

class TestDrawerEnemyEffects(unittest.TestCase):

    def setUp(self):
        self.drawer = _make_drawer()
        self.image = MagicMock()
        patch.object(self.drawer, 'get_enemy_image', return_value=(self.image, (256, 224))).start()
        self.addCleanup(patch.stopall)

    @patch('src.drawer.wait')
    @patch('src.drawer.enemy_fade_in')
    def test_regular_enemy_fades_in_twice(self, mock_fade, mock_wait):
        screen = MagicMock()
        self.drawer.fade_in_enemy(screen, 'Slime')
        mock_fade.assert_called_once_with(screen, self.image, (256, 224), self.drawer.game_state.config)
        mock_wait.assert_not_called()

    @patch('src.drawer.cut_to_black')
    @patch('src.drawer.screen_fade')
    @patch('src.drawer.wait')
    @patch('src.drawer.enemy_fade_in')
    def test_final_form_fades_in_four_times_then_waits_41_frames(self, mock_fade, mock_wait, _screen_fade, _black):
        # Bank00 LoadEndBossGFX: PalFadeIn x4, then WaitForNMI + 40 more frames
        self.drawer.game_state.config['NO_WAIT'] = False
        self.drawer.fade_in_enemy(MagicMock(), 'Dragonlord 2')
        self.assertEqual(mock_fade.call_args.kwargs['repeats'], 4)
        mock_wait.assert_called_once_with(682, self.drawer.game_state.config)  # 41 frames

    @patch('src.drawer.wait')
    def test_final_form_fades_the_screen_out_first(self, _wait):
        # Bank00 LoadEndBossGFX: PalFadeOut over the whole screen, the nametable blanked, then the PalFadeIns
        order = []
        screen = MagicMock()
        with patch('src.drawer.screen_fade', side_effect=lambda **kwargs: order.append(('fade', kwargs['fade_out']))), \
                patch('src.drawer.cut_to_black', side_effect=lambda *_: order.append('black')), \
                patch('src.drawer.enemy_fade_in', side_effect=lambda *_, **__: order.append('enemy')):
            self.drawer.fade_in_enemy(screen, 'Dragonlord 2')
        self.assertEqual(order, [('fade', True), 'black', 'enemy'])

    @patch('src.drawer.wait')
    def test_final_form_plays_the_fire_sound_before_fading_in(self, _wait):
        # Bank00 LoadEndBossGFX (LBB86): SFX_FIRE once the screen is blank, before the PalFadeIns
        order = []
        sound = MagicMock()
        sound.play_sound.side_effect = order.append
        with patch.object(self.drawer, 'sound', sound), patch('src.drawer.screen_fade'), \
                patch('src.drawer.cut_to_black', side_effect=lambda *_: order.append('black')), \
                patch('src.drawer.enemy_fade_in', side_effect=lambda *_, **__: order.append('enemy')):
            self.drawer.fade_in_enemy(MagicMock(), 'Dragonlord 2')
        self.assertEqual(order, ['black', self.drawer.directories.breathe_fire_sfx, 'enemy'])

    @patch('src.drawer.enemy_fade_in')
    def test_other_enemies_play_no_sound_as_they_fade_in(self, _enemy_fade_in):
        sound = MagicMock()
        with patch.object(self.drawer, 'sound', sound):
            self.drawer.fade_in_enemy(MagicMock(), 'Dragonlord')
        sound.play_sound.assert_not_called()

    @patch('src.drawer.screen_fade')
    @patch('src.drawer.enemy_fade_in')
    def test_other_enemies_do_not_fade_the_screen_out(self, _enemy_fade_in, mock_screen_fade):
        self.drawer.fade_in_enemy(MagicMock(), 'Dragonlord')
        mock_screen_fade.assert_not_called()

    @patch('src.drawer.enemy_hit_flash')
    def test_flash_enemy(self, mock_flash):
        screen = MagicMock()
        self.drawer.flash_enemy(screen, 'Slime')
        mock_flash.assert_called_once_with(screen, self.image, (256, 224), self.drawer.game_state.config,
                                           keep_black=False)

    @patch('src.drawer.enemy_spell_flash')
    def test_flash_enemy_spell(self, mock_flash):
        screen = MagicMock()
        self.drawer.flash_enemy_spell(screen, 'Slime')
        mock_flash.assert_called_once_with(screen, self.image, (256, 224), self.drawer.game_state.config)

    @patch('src.drawer.enemy_hit_flash')
    def test_final_form_flash_keeps_black(self, mock_flash):
        # PaletteFlash loads FinalRedBGPal for the end boss, which leaves the universal black alone
        self.drawer.flash_enemy(MagicMock(), 'Dragonlord 2')
        self.assertTrue(mock_flash.call_args.kwargs['keep_black'])


if __name__ == '__main__':
    unittest.main()


# ---------------------------------------------------------------------------
# handle_darkness
# ---------------------------------------------------------------------------

class TestHandleDarkness(unittest.TestCase):
    """The dungeon light (NES LightDiameter, ChkLightDiameterX/ChkLightDiameterY in Bank00)."""

    def setUp(self):
        from src.game_state import GameState
        config = dict(test_config)
        config['NO_BLIT'] = False
        self.game_state = GameState(config)
        with patch('src.drawer.Graphics'), patch('src.drawer.Directories'), patch('src.drawer.Sound'), \
                patch('src.drawer.Calculation'):
            self.drawer = Drawer(self.game_state)
        self.tile_size = config['TILE_SIZE']
        self.player = MagicMock(is_moving=False, bumped=False)

    def lit_area(self, frames=1):
        """Draw some frames of darkness over a white screen and return the size, in tiles, of the part left lit."""
        from pygame import Surface
        screen = Surface((self.tile_size * 16, self.tile_size * 15))
        for _ in range(frames):
            screen.fill((255, 255, 255))
            self.drawer.handle_darkness(screen, self.player)
        screen.set_colorkey((0, 0, 0))  # so that the bounding rect leaves out the darkness
        lit = screen.get_bounding_rect()
        center = (screen.get_width() // 2 + self.tile_size // 2, screen.get_height() // 2)
        self.assertTrue(lit.collidepoint(center), 'the light is centered on the hero')
        return lit.width / self.tile_size, lit.height / self.tile_size

    def test_without_a_light_only_the_hero_is_lit(self):
        self.assertEqual(self.lit_area(), (1, 1))

    def test_radiant_expands_the_light_one_block_at_a_time(self):
        from src.game_state import LIGHT_REDRAW_FRAMES
        self.game_state.cast_radiant()
        self.assertEqual(self.lit_area(LIGHT_REDRAW_FRAMES - 1), (1, 1))
        self.assertEqual(self.lit_area(1), (3, 3))
        self.assertEqual(self.lit_area(LIGHT_REDRAW_FRAMES), (5, 5))
        self.assertEqual(self.lit_area(LIGHT_REDRAW_FRAMES), (7, 7))
        self.assertEqual(self.lit_area(LIGHT_REDRAW_FRAMES), (7, 7))
        self.assertEqual(self.drawer.sound.play_sound.call_count, 3)

    def test_torch_lights_3_blocks(self):
        from src.game_state import LIGHT_REDRAW_FRAMES
        self.game_state.use_torch()
        self.assertEqual(self.lit_area(LIGHT_REDRAW_FRAMES), (3, 3))
        self.assertEqual(self.drawer.sound.play_sound.call_count, 1)

    def test_shrinking_light_is_shown_once_the_hero_steps(self):
        from src.game_state import LIGHT_REDRAW_FRAMES
        self.game_state.cast_radiant()
        self.lit_area(LIGHT_REDRAW_FRAMES * 3)
        for _ in range(80):
            self.game_state.tick_radiant_timer()
        self.assertEqual(self.lit_area(), (7, 7))
        self.player.is_moving = True
        self.assertEqual(self.lit_area(), (5, 5))

    def test_bumping_into_a_wall_does_not_redraw_the_light(self):
        self.game_state.light_diameter = 5
        self.game_state.lit_diameter = 7
        self.player.is_moving, self.player.bumped = True, True
        self.assertEqual(self.lit_area(), (7, 7))
