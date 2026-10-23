"""The drawing shortcuts of #241 draw exactly what the long way did.

- draw_text keeps the lines it renders (src/text.py rendered_line) instead of making a font and rendering each line
  every frame: the pop-up window drew five of them every frame the hero stood still;
- draw_all finds the tiles under the characters through an index (src/drawer.py TileIndex) instead of going through
  every tile of their types: 14,400 on Alefgard;
- the darkness is made once for each light diameter (Drawer.draw_darkness);
- a map's first frame draws on the black surface MapManager.set_big_map made, not on copies of it.
Each test compares the picture with the one drawn the old way, byte for byte.
"""
import hashlib
import random
from collections import defaultdict
from contextlib import ExitStack
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import K_LEFT, K_RIGHT, Rect, Surface
from pygame.sprite import Group

from src.color import BLACK, LOW_HP_RED, WHITE
from src.config.test_config import test_config
from src.drawer import Drawer, TileIndex, first_frame_background, map_surface
from src.sprites.base_sprite import BaseSprite
from src.text import TextPaths, blit_text_to_screen, draw_text, set_font_by_ascii_chars
from src.directories import Directories
from tests.test_character_redraw import draw_frame, frame_view, make_game


def screen_bytes(surface: Surface) -> bytes:
    return pygame.image.tobytes(surface, 'RGB')


class DisplayTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((512, 480))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()


class TestRenderedLines(DisplayTestCase):
    config = {**test_config, 'NO_BLIT': False, 'RENDER_TEXT': True, 'NO_WAIT': True}

    def old_draw_text(self, text, x, y, color, alignment, font_name=None):
        """What draw_text drew for a line at once before it kept the lines it renders."""
        font = set_font_by_ascii_chars([text], 16, font_name, Directories(self.config))
        blit_text_to_screen(alignment, color, font, self.screen, text, x, y)

    def test_a_line_is_drawn_as_before_rendered_or_kept(self):
        directories = Directories(self.config)
        lines = ['ED', '120', '∞', "Thou'rt dead", 'Tis a hard path', '설정', 'HP 절반']
        for text in lines:
            for color in (WHITE, LOW_HP_RED):
                for alignment in ('left', 'center', 'right'):
                    for font_name in (None, directories.DRAGON_QUEST_FONT_PATH, directories.SMB_FONT_PATH):
                        with self.subTest(text=text, color=color, alignment=alignment, font_name=font_name):
                            self.screen.fill(BLACK)
                            self.old_draw_text(text, 200, 100, color, alignment, font_name)
                            expected = screen_bytes(self.screen)
                            for _ in ('rendered', 'kept'):
                                self.screen.fill(BLACK)
                                draw_text(text, 200, 100, self.screen, self.config, color=color, alignment=alignment,
                                          letter_by_letter=False, font_name=font_name)
                                self.assertEqual(expected, screen_bytes(self.screen))

    def test_a_kept_line_makes_no_font(self):
        draw_text('LV', 50, 50, self.screen, self.config, letter_by_letter=False)
        with patch('src.text.NESFont') as nes_font, patch('src.text.font.Font') as font:
            draw_text('LV', 50, 50, self.screen, self.config, letter_by_letter=False)
        nes_font.assert_not_called()
        font.assert_not_called()

    def test_the_paths_are_the_directories_ones(self):
        directories = Directories(self.config)
        self.assertEqual(directories.DRAGON_QUEST_FONT_PATH, TextPaths.DRAGON_QUEST_FONT_PATH)
        self.assertEqual(directories.UNIFONT_PATH, TextPaths.UNIFONT_PATH)
        self.assertEqual(directories.text_beep_sfx, TextPaths.text_beep_sfx)


def linear_tiles_at(group: Group, corners: set) -> list:
    """The tiles draw_all used to find, by going through the whole group."""
    return [tile for tile in group if tile.rect.topleft in corners]


class TestTileIndex(DisplayTestCase):

    def test_finds_the_tiles_a_scan_of_the_group_finds_in_its_order(self):
        game = make_game('Alefgard')
        current_map, tile_size = game.current_map, game.tile_size
        index = TileIndex()
        rng = random.Random(241)
        groups = [tile_dict['group'] for tile_dict in current_map.floor_tile_key.values() if tile_dict.get('group')]
        self.assertGreater(sum(len(group) for group in groups), 10000)
        for _ in range(50):
            column, row = rng.randrange(118), rng.randrange(118)
            corners = {((column + dx) * tile_size, (row + dy) * tile_size) for dx in range(-1, 3) for dy in range(-1, 3)}
            for group in groups:
                self.assertEqual(linear_tiles_at(group, corners), index.tiles_at(group, corners))

    def test_indexes_a_group_again_when_tiles_are_added_or_it_is_replaced(self):
        image = Surface((16, 16))
        group = Group(BaseSprite((8, 8), image))
        index = TileIndex()
        corners = {(0, 0), (16, 0)}
        self.assertEqual(linear_tiles_at(group, corners), index.tiles_at(group, corners))
        group.add(BaseSprite((24, 8), image))
        self.assertEqual(2, len(index.tiles_at(group, corners)))
        replacement = Group(BaseSprite((24, 8), image))
        self.assertEqual(linear_tiles_at(replacement, corners), index.tiles_at(replacement, corners))

    def test_frames_are_drawn_as_with_a_scan(self):
        # The hero walks out of Brecconary's west gate and back while the NPCs roam: every frame, the screen is what
        # the old scan drew
        self.assertEqual(walk_frames(scan=True), walk_frames(scan=False))


def walk_frames(scan: bool) -> list[bytes]:
    """The screens of 120 frames of Brecconary, the hero walking left and right, the NPCs roaming."""
    random.seed(241)
    game = make_game('Brecconary')
    if scan:
        game.drawer.tile_index = SimpleNamespace(tiles_at=linear_tiles_at)
    held_keys: defaultdict = defaultdict(int)
    screens = []
    with patch('src.game.get_ticks', return_value=0), patch('src.movement.key.get_pressed', return_value=held_keys):
        for frame in range(120):
            held_keys.clear()
            held_keys[K_LEFT if frame < 60 else K_RIGHT] = 1
            game.movement.handle_player_movement()
            game.movement.sprites_frame()
            draw_frame(game)
            screens.append(hashlib.sha256(screen_bytes(game.screen) + screen_bytes(game.drawer.background)).digest())
    return screens


class TestDarkness(DisplayTestCase):

    @staticmethod
    def old_darkness(screen: Surface, tile_size: int, lit_diameter: int) -> None:
        radius = (lit_diameter - 1) // 2
        darkness = Surface((screen.get_width(), screen.get_height()))
        darkness.subsurface((screen.get_width() / 2) - tile_size * radius,
                            (screen.get_height() / 2) - tile_size * (radius + 0.5),
                            tile_size * lit_diameter, tile_size * lit_diameter).fill(WHITE)
        darkness.set_colorkey(WHITE)
        screen.blit(darkness, (0, 0))

    def test_the_darkness_is_drawn_as_before_for_every_light_diameter(self):
        game_state = SimpleNamespace(config={**test_config, 'NO_BLIT': False}, lit_diameter=1)
        drawer = Drawer.__new__(Drawer)
        drawer.game_state, drawer._darkness = game_state, {}
        picture = Surface(self.screen.get_size())
        for y in range(0, picture.get_height(), 8):
            picture.fill((y % 256, 255 - y % 256, 77), Rect(0, y, picture.get_width(), 8))
        for lit_diameter in (1, 3, 5, 7, 3, 1):
            game_state.lit_diameter = lit_diameter
            with self.subTest(lit_diameter=lit_diameter):
                self.screen.blit(picture, (0, 0))
                self.old_darkness(self.screen, test_config['TILE_SIZE'], lit_diameter)
                expected = screen_bytes(self.screen)
                for _ in ('made', 'kept'):
                    self.screen.blit(picture, (0, 0))
                    drawer.draw_darkness(self.screen)
                    self.assertEqual(expected, screen_bytes(self.screen))


class TestFirstFrameBackground(DisplayTestCase):

    def test_map_surface_is_a_converted_black_surface(self):
        converted = Surface((96, 64)).convert()
        surface = map_surface(96, 64)
        self.assertEqual((converted.get_bitsize(), converted.get_masks(), converted.get_flags()),
                         (surface.get_bitsize(), surface.get_masks(), surface.get_flags()))
        self.assertEqual(screen_bytes(converted), screen_bytes(surface))

    def test_the_first_frame_draws_on_big_map_black_again(self):
        big_map = map_surface(64, 32)
        big_map.fill(WHITE, Rect(3, 3, 10, 10))
        background = first_frame_background(big_map, 64, 32)
        self.assertIs(big_map, background)
        self.assertEqual(screen_bytes(map_surface(64, 32)), screen_bytes(background))

    def test_a_big_map_of_another_size_is_copied(self):
        big_map = map_surface(64, 64)
        background = first_frame_background(big_map, 32, 32)
        self.assertIsNot(big_map, background)
        self.assertEqual((32, 32), background.get_size())

    def test_map_change_frames_are_drawn_as_on_copies(self):
        # The frame a map change fades in from and the main loop's first frame after it (both loop_count 1) are what
        # they were when each was drawn on a new copy of big_map, after a frame of the old map had been drawn
        self.assertEqual(map_change_frames(copies=True), map_change_frames(copies=False))


def map_change_frames(copies: bool) -> list[bytes]:
    random.seed(241)
    game = make_game('Brecconary')
    with ExitStack() as stack:
        if copies:
            stack.enter_context(patch('src.drawer.first_frame_background',
                                      lambda big_map, width, height: big_map.subsurface(0, 0, width, height).convert()))
        for _ in range(20):
            game.movement.sprites_frame()
            draw_frame(game)
        game.map_mgr.set_big_map()
        game.loop_count = 1
        frames = []
        for _ in range(2):
            game.drawer.draw_all(frame_view(game), False)
            frames.append(screen_bytes(game.drawer.background) + screen_bytes(game.screen))
        return frames
