from unittest import TestCase
from unittest.mock import patch

import pygame

from src.color import LOW_HP_RED, WHITE
from src.config.test_config import test_config
from src.maps import LOW_HP_PALETTE_TILES, map_lookup
from src.maps_functions import PAL0_COLOR1_LOW_HP, PAL0_COLOR1_NORMAL, low_hp_tile_image
from src.visual_effects import NES_PALETTE
from tests.helpers import new_game


def pixels(surface):
    return [[tuple(surface.get_at((x, y)))[:3] for y in range(surface.get_height())]
            for x in range(surface.get_width())]


class LowHPMapTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        self.game = new_game()
        self.player = self.game.player
        self.player.name = "Edward"
        self.player.max_hp = 15
        self.player.current_hp = 15
        self.game.load_window_palette()
        pygame.event.clear()

    def go_to(self, map_name, coordinates=None):
        next_map = map_lookup[map_name](self.game.config)
        self.game.change_map(next_map, destination_coordinates=coordinates or next_map.initial_coordinates)
        self.game.loop_count = 2  # the map has been drawn once

    @property
    def current_map(self):
        return self.game.current_map

    def map_images(self):
        """The image of every palette 0 tile on the current map."""
        return {tile_name: {tile.image for tile in self.current_map.floor_tile_key[tile_name]['group']}
                for tile_name in LOW_HP_PALETTE_TILES if self.current_map.floor_tile_key[tile_name].get('group')}

    def assert_map_red(self, red):
        self.assertEqual(self.current_map.low_hp_palette, red)
        images = self.map_images()
        self.assertTrue(images)
        for tile_name, tile_images in images.items():
            tile_value = self.current_map.floor_tile_key[tile_name]['val']
            normal = self.current_map.normal_tile_image(tile_value)
            with self.subTest(tile=tile_name):
                self.assertEqual(len(tile_images), 1)
                image = tile_images.pop()
                if red:
                    self.assertIsNot(image, normal)
                    self.assertEqual(pixels(image), pixels(low_hp_tile_image(normal)))
                else:
                    self.assertIs(image, normal)


class TestLowHPTileImages(LowHPMapTestCase):
    """GFXTilesTbl (Bank03): only Town, Castle, Bridge and the water blocks use background palette 0."""

    def test_palette_0_tiles_are_the_ones_with_white(self):
        # palette 0 is $30, $10, $11 and no other background palette has $30, so in tileset.png the tiles with
        # white pixels are exactly the palette 0 blocks
        tiles_with_white = set()
        for tile_name, tile_dict in self.current_map.floor_tile_key.items():
            image = self.current_map.normal_tile_image(tile_dict['val'])
            if any(PAL0_COLOR1_NORMAL in column for column in pixels(image)):
                tiles_with_white.add(tile_name)
        self.assertEqual(tiles_with_white, LOW_HP_PALETTE_TILES)
        self.assertEqual(LOW_HP_PALETTE_TILES, {
            'CASTLE', 'TOWN', 'BRIDGE', 'WATER', 'BOTTOM_COAST', 'BOTTOM_LEFT_COAST', 'LEFT_COAST', 'TOP_LEFT_COAST',
            'TOP_COAST', 'TOP_RIGHT_COAST', 'RIGHT_COAST', 'BOTTOM_RIGHT_COAST', 'BOTTOM_TOP_LEFT_COAST',
            'BOTTOM_TOP_RIGHT_COAST'})

    def test_only_color_1_pixels_turn_red(self):
        self.assertEqual(PAL0_COLOR1_NORMAL, NES_PALETTE[0x30])
        self.assertEqual(PAL0_COLOR1_LOW_HP, NES_PALETTE[0x26])
        self.current_map.low_hp_palette = True
        for tile_name in LOW_HP_PALETTE_TILES:
            tile_value = self.current_map.floor_tile_key[tile_name]['val']
            normal = pixels(self.current_map.normal_tile_image(tile_value))
            red = pixels(self.current_map.floor_tile_image(tile_value))
            with self.subTest(tile=tile_name):
                changed = 0
                for normal_column, red_column in zip(normal, red):
                    for normal_pixel, red_pixel in zip(normal_column, red_column):
                        if normal_pixel == PAL0_COLOR1_NORMAL:
                            self.assertEqual(red_pixel, PAL0_COLOR1_LOW_HP)
                            changed += 1
                        else:
                            self.assertEqual(red_pixel, normal_pixel)
                self.assertGreater(changed, 0)

    def test_other_tiles_keep_their_image(self):
        self.current_map.low_hp_palette = True
        for tile_name, tile_dict in self.current_map.floor_tile_key.items():
            if tile_name not in LOW_HP_PALETTE_TILES:
                with self.subTest(tile=tile_name):
                    self.assertIs(self.current_map.floor_tile_image(tile_dict['val']),
                                  self.current_map.normal_tile_image(tile_dict['val']))

    def test_red_tiles_are_made_once(self):
        self.current_map.low_hp_palette = True
        water = self.current_map.floor_tile_key['WATER']['val']
        self.assertIs(self.current_map.floor_tile_image(water), self.current_map.floor_tile_image(water))


class TestLowHPMapSwitching(LowHPMapTestCase):
    """The map's palette 0 tiles change at the same moments as the windows (Game.set_window_color)."""

    def setUp(self):
        super().setUp()
        self.go_to('Alefgard', (44, 43))

    def set_hp(self, hp):
        self.player.current_hp = hp
        self.game.load_window_palette()

    def test_normal_hp_is_white(self):
        self.assertEqual(self.game.color, WHITE)
        self.assert_map_red(False)

    def test_palette_load_at_low_hp_turns_map_red_and_back(self):
        self.set_hp(4)
        self.assertEqual(self.game.color, LOW_HP_RED)
        self.assert_map_red(True)
        self.set_hp(15)
        self.assert_map_red(False)

    def test_redrawn_only_when_it_changes(self):
        with patch.object(self.game.drawer, 'draw_all_tiles_in_current_map') as redraw:
            self.set_hp(3)
            self.set_hp(2)
        redraw.assert_called_once_with(self.current_map, self.game.drawer.background)
        with patch.object(self.game.drawer, 'draw_all_tiles_in_current_map') as redraw:
            self.set_hp(15)
            self.set_hp(14)
        redraw.assert_called_once()

    def test_redrawn_tiles_are_red(self):
        self.game.drawer.background = pygame.Surface((self.current_map.width, self.current_map.height))
        self.set_hp(2)
        water = next(iter(self.current_map.floor_tile_key['WATER']['group']))
        drawn = self.game.drawer.background.subsurface(water.rect)
        self.assertEqual(pixels(drawn), pixels(water.image))
        self.assertTrue(any(PAL0_COLOR1_LOW_HP in column for column in pixels(drawn)))

    def test_damage(self):
        with patch.object(self.game.cmd_menu, 'show_line_in_dialog_box'), \
                patch.object(self.game.battle_ctrl, 'player_hit_effect'):
            self.game.receive_damage(10)
            self.assert_map_red(False)  # 5 of 15 isn't low
            self.game.receive_damage(1)
        self.assert_map_red(True)

    def test_swamp_damage(self):
        self.player.current_hp = 6
        with patch('src.game.flash_transparent_color'), patch.object(self.game.drawer, 'draw_all'):
            self.game.damage_step(damage_amount=2)
        self.assert_map_red(True)

    def test_healing(self):
        for heal in ('heal', 'herb', 'healmore'):
            with self.subTest(heal=heal):
                self.set_hp(1)
                self.assert_map_red(True)
                self.player.inventory = ['Herb']
                with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box'), \
                        patch.object(self.game.cmd_menu, 'show_line_in_dialog_box'):
                    getattr(self.game.cmd_menu, heal)()
                self.assert_map_red(False)

    def test_step_only_clears_red(self):
        # NES ChkLowHP: a step turns $3F01 white if HP isn't low, but never red
        self.player.current_hp = 2
        self.game.count_step()
        self.assert_map_red(False)
        self.set_hp(2)
        self.player.current_hp = 10
        self.game.count_step()
        self.assert_map_red(False)

    def test_new_map_at_low_hp_is_red(self):
        # NES PalFadeIn: the new map fades in with the low HP palette
        self.player.current_hp = 2
        self.go_to('Rimuldar')
        self.assertEqual(self.game.color, LOW_HP_RED)
        self.assert_map_red(True)

    def test_tile_added_at_low_hp_is_red(self):
        # e.g. the Rainbow Drop's bridge, added while the palette is red
        self.set_hp(2)
        self.current_map.add_tile(self.current_map.floor_tile_key['BRIDGE'], (8, 8))
        self.assert_map_red(True)

    def test_inn(self):
        self.go_to('Rimuldar')
        self.set_hp(2)
        self.player.gold = 100
        cmd_menu = self.game.cmd_menu
        reds = []

        def record(*_args, **_kwargs):
            reds.append((self.game.color, self.current_map.low_hp_palette))

        with patch.object(cmd_menu, 'show_line_in_dialog_box', side_effect=record), \
                patch.object(cmd_menu, 'show_text_in_dialog_box', side_effect=record), \
                patch('data.text.dialog_lookup_table.screen_fade'):
            cmd_menu.dialog_lookup.inn_sleep(6)
        # "Good night." comes before the fade out, at the old HP; the map wakes up white with the windows
        self.assertEqual(reds, [(LOW_HP_RED, True), (WHITE, False)])
        self.assert_map_red(False)
