"""The bad ending's palette, NES BadEndBGPal (Bank00, $9AA3): ChooseDrgnLrd (Bank03) loads it into the background
palettes, so background palette 0's color 1 is red ($16) and every other background color is black. The sprites'
palettes don't change (#313)."""
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import Rect

from src.color import BLACK
from src.config.test_config import test_config
from src.direction import Direction
from src.maps import LOW_HP_PALETTE_TILES, CharlockB8
from src.maps_functions import PAL0_COLOR1_NORMAL, bad_ending_tile_image
from src.visual_effects import NES_RED
from src.windows import COMMAND_WINDOW, DIALOG_WINDOW, POPUP_WINDOW
from tests.helpers import new_game


def colors(surface) -> set:
    return {tuple(surface.get_at((x, y)))[:3] for x in range(surface.get_width()) for y in range(surface.get_height())}


class TestBadEndingTileImage(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))
        cls.charlock = CharlockB8(test_config)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def tile(self, name):
        return self.charlock.normal_tile_image(self.charlock.floor_tile_key[name]['val'])

    def test_a_palette_0_block_keeps_only_its_color_1_pixels_in_red(self):
        water = self.tile('WATER')
        self.assertIn('WATER', LOW_HP_PALETTE_TILES)
        self.assertIn(PAL0_COLOR1_NORMAL, colors(water))
        image = bad_ending_tile_image(water, True, NES_RED)
        self.assertEqual({BLACK, NES_RED}, colors(image))
        for x in range(water.get_width()):
            for y in range(water.get_height()):
                was_white = tuple(water.get_at((x, y)))[:3] == PAL0_COLOR1_NORMAL
                self.assertEqual(NES_RED if was_white else BLACK, tuple(image.get_at((x, y)))[:3])

    def test_any_other_block_goes_black(self):
        brick = self.tile('BRICK')
        self.assertNotIn('BRICK', LOW_HP_PALETTE_TILES)
        self.assertEqual({BLACK}, colors(bad_ending_tile_image(brick, False, NES_RED)))


class TestBadEndingScreen(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['NO_BLIT'] = False
        self.addCleanup(test_config.__setitem__, 'NO_BLIT', True)
        self.game = game = new_game()
        # Below the Dragonlord, on his throne at NES (16, 24)
        game.change_map(CharlockB8(game.config), destination_coordinates=(29, 22), direction=Direction.UP.value)
        # TALK: the pop-up and COMMAND windows are open
        game.drawer.display_hovering_stats = True
        game.cmd_menu.launch_signaled = True
        for _ in range(3):
            game.drawer.draw_all(game.screen, game.loop_count, game.big_map, game.current_map, game.player,
                                 game.cmd_menu, game.foreground_rects, game.sprites_animate, game.camera,
                                 game.initial_dialog_enabled, [], game.skip_text, game.story_flags.left_throne_room,
                                 game.game_state, game.color)
            game.loop_count += 1
        self.tile_size = game.tile_size
        with patch.object(game.cmd_menu, 'show_line_in_dialog_box'):
            game.cmd_menu.dialog_lookup.show_bad_ending_palette()
        self.assertTrue(game.cmd_menu.menu.is_enabled())

    def screen_rect(self, row, column) -> Rect:
        camera_x, camera_y = self.game.camera.pos
        return Rect(column * self.tile_size + camera_x, row * self.tile_size + camera_y, self.tile_size,
                    self.tile_size)

    def window_rects(self):
        size = self.tile_size
        return [Rect(x * size, y * size, width * size, height * size)
                for x, y, width, height in (POPUP_WINDOW, COMMAND_WINDOW, DIALOG_WINDOW)]

    def test_the_hero_and_the_dragonlord_keep_their_colors(self):
        for row, column in ((29, 22), (28, 22)):
            with self.subTest(row=row, column=column):
                block_colors = colors(self.game.screen.subsurface(self.screen_rect(row, column)))
                self.assertTrue(block_colors - {BLACK, NES_RED}, block_colors)

    def test_the_map_is_black_but_palette_0_color_1(self):
        current_map = self.game.current_map
        screen_rect = self.game.screen.get_rect()
        checked = set()
        for row in range(len(current_map.layout)):
            for column in range(len(current_map.layout[row])):
                rect = self.screen_rect(row, column)
                if (row, column) in ((29, 22), (28, 22)) or not screen_rect.contains(rect) or \
                        rect.collidelist(self.window_rects()) != -1:
                    continue
                tile_name = current_map.get_tile_by_value(current_map.layout[row][column])
                block_colors = colors(self.game.screen.subsurface(rect))
                expected = {BLACK, NES_RED} if tile_name in LOW_HP_PALETTE_TILES else {BLACK}
                self.assertLessEqual(block_colors, expected, (row, column, tile_name))
                checked.add(tile_name)
        self.assertIn('BRICK', checked)

    def test_the_windows_are_red(self):
        for rect in self.window_rects():
            with self.subTest(rect=rect):
                self.assertIn(NES_RED, colors(self.game.screen.subsurface(rect)))
