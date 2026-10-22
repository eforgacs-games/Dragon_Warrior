"""Generated windows (src/window_renderer.py) against the NES screenshots they replace: 0 differing pixels, at every
scale, for every variant. See tests/nes_screen_diff.py."""
import os
import tempfile
from unittest import TestCase
from unittest.mock import MagicMock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame  # noqa: E402

from src.color import RED, WHITE  # noqa: E402
from src.config.test_config import test_config  # noqa: E402
from src.directories import Directories  # noqa: E402
from src.cursor import CURSOR_TILE  # noqa: E402
from src import window_renderer  # noqa: E402
from src.window_renderer import (TL_TOP1, TL_TOP2, glyph_tile, render_window, window_tiles)  # noqa: E402
from src.windows import COMBAT_COMMAND_LAYOUT, Window, WindowLayout, WindowText  # noqa: E402
from tests.nes_screen_diff import compare_with_screenshot, count_differing_pixels, load_screenshot  # noqa: E402

SCALES = (1, 2, 3)
DIFF_DIR = os.path.join(tempfile.gettempdir(), 'dragon_warrior_screen_diffs')


class TestBattleCommandWindow(TestCase):
    """CmdCmbtDat, against data/images/menus/battle_menu."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        directories = Directories(test_config)
        # The screenshot of each cursor position, in cursor_tiles order: FIGHT, SPELL, RUN, ITEM
        cls.cursor_screenshots = (directories.BATTLE_MENU_FIGHT_PATH, directories.BATTLE_MENU_SPELL_PATH,
                                  directories.BATTLE_MENU_RUN_PATH, directories.BATTLE_MENU_ITEM_PATH)
        cls.no_cursor_screenshot = directories.BATTLE_MENU_STATIC_PATH

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def assert_matches(self, screenshot, color, nes_pixel, name, **window):
        generated = render_window(COMBAT_COMMAND_LAYOUT, color, nes_pixel, **window)
        result = compare_with_screenshot(generated, screenshot, nes_pixel, window_color=color, diff_dir=DIFF_DIR,
                                         name=name)
        self.assertEqual(0, result.differing_pixels, str(result))

    def test_every_cursor_position(self):
        for scale in SCALES:
            for color in (WHITE, RED):
                for index, screenshot in enumerate(self.cursor_screenshots):
                    with self.subTest(scale=scale, color=color, entry=COMBAT_COMMAND_LAYOUT.texts[index].text):
                        self.assert_matches(screenshot, color, scale, f'battle_{index}_{scale}_{color}',
                                            cursor_index=index)

    def test_cursor_hidden(self):
        # The "off" half of the blink blanks the cursor's tile: the screenshot without a cursor, wherever it is
        for scale in SCALES:
            for color in (WHITE, RED):
                for index in range(4):
                    with self.subTest(scale=scale, color=color, entry=index):
                        self.assert_matches(self.no_cursor_screenshot, color, scale,
                                            f'battle_hidden_{index}_{scale}_{color}', cursor_index=index,
                                            cursor_visible=False)

    def test_no_cursor(self):
        for scale in SCALES:
            with self.subTest(scale=scale):
                self.assert_matches(self.no_cursor_screenshot, WHITE, scale, f'battle_no_cursor_{scale}')

    def test_drawn_by_the_battle_controller(self):
        # What the game actually draws on its screen, at its own scale, where the screenshot was drawn
        from src.battle_controller import BattleController
        config = dict(test_config, NO_BLIT=False)
        tile_size = config['TILE_SIZE']
        game = MagicMock()
        game.game_state.config = config
        game.screen = pygame.Surface((16 * tile_size, 15 * tile_size))
        controller = BattleController(game)
        area = pygame.Rect(6 * tile_size, 1 * tile_size, 8 * tile_size, 3 * tile_size)
        for color in (WHITE, RED):
            game.color = color
            for index, screenshot in enumerate(self.cursor_screenshots):
                controller.battle_menu_row, controller.battle_menu_column = divmod(index, 2)
                with self.subTest(color=color, entry=index), patch('src.battle_controller.display'):
                    controller.draw_command_window(True)
                    result = compare_with_screenshot(game.screen, screenshot, config['SCALE'], window_color=color,
                                                     area=area, diff_dir=DIFF_DIR, name=f'battle_game_{index}')
                    self.assertEqual(0, result.differing_pixels, str(result))


class TestWindowTiles(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_border_before_a_title_stops_short(self):
        # BuildWndLine: the TL_TOP1 before a character becomes TL_TOP2; the border after the title is TL_TOP1
        layout = WindowLayout(Window(0, 0, 4, 2), title=WindowText("AB", 3, 0))
        top = window_tiles(layout)[0]
        self.assertEqual([TL_TOP1, TL_TOP2], top[1:3])
        self.assertEqual([glyph_tile("A"), glyph_tile("B")], top[3:5])
        self.assertEqual([TL_TOP1, TL_TOP1], top[5:7])

    def test_text_must_be_inside_the_window(self):
        window = Window(0, 0, 4, 2)
        for text in (WindowText("ABCDEFG", 1, 1), WindowText("A", 0, 1), WindowText("A", 1, 3)):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    window_tiles(WindowLayout(window, texts=(text,)))

    def test_glyphs_are_one_tile(self):
        self.assertEqual(("........",) * 8, glyph_tile(" "))
        self.assertEqual(8, len(glyph_tile("W")))
        self.assertTrue(all(len(row) == 8 for row in glyph_tile("W")))


# One screenshot of each window or screen family in data/images (the others only move the cursor)
TILE_VOCABULARY_SCREENSHOTS = (
    'menus/battle_menu/battle_menu_fight.png',
    'command_menu_static.png', 'confirmation_yes.png', 'dialog_box_background.png', 'hovering_stats_window.png',
    'status_window_background.png', 'menus/item_menu/item_menu_background_5.png',
    'menus/main_menu/empty_log/0_begin_quest.png', 'menus/main_menu/empty_log/adventure_log/1_adventure_log_2.png',
    'menus/main_menu/partially_full_log/3_copy_quest.png', 'menus/main_menu/full_log/2_erase_quest.png',
    'menus/main_menu/partially_full_log/one_adventure_log/0_adventure_log_1.png',
    'menus/name_selection/0_upper_A.png', 'menus/name_selection/67_static_image_len_4.png',
    'shops/brecconary/weapons/brecconary_shop.png', 'shops/garinham/weapons/garinham_shop.png',
    'shops/kol/weapons/kol_shop.png', 'shops/rimuldar/weapons/rimuldar_shop.png',
    'shops/cantlin/weapons/north/cantlin_shop_north.png', 'shops/cantlin/weapons/south/cantlin_shop_south.png',
)


class TestTileVocabulary(TestCase):
    """Every 8x8 tile of the window screenshots is one the renderer can draw: a border tile, the cursor, the name
    placeholder or a font tile. This is what makes the screenshots reproducible from window data alone."""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_every_screenshot_tile_is_known(self):
        import string
        known = {getattr(window_renderer, name) for name in dir(window_renderer) if name.startswith('TL_')}
        known |= {CURSOR_TILE} | {glyph_tile(character) for character in string.printable.strip()}
        images_dir = Directories(test_config).IMAGES_DIR
        for screenshot in TILE_VOCABULARY_SCREENSHOTS:
            with self.subTest(screenshot=screenshot):
                surface = pygame.image.load(os.path.join(images_dir, screenshot))
                width, height = surface.get_size()
                self.assertEqual((0, 0), (width % 8, height % 8))
                pixels = pygame.image.tobytes(surface, 'RGB')
                unknown = []
                for row in range(height // 8):
                    for column in range(width // 8):
                        tile = tuple(''.join('#' if pixels[((row * 8 + y) * width + column * 8 + x) * 3] else '.'
                                             for x in range(8)) for y in range(8))
                        if tile not in known:
                            unknown.append((column, row))
                self.assertEqual([], unknown)


class TestScreenDiff(TestCase):
    """The harness itself: exact colours, a diff image when anything differs."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screenshot = Directories(test_config).BATTLE_MENU_STATIC_PATH

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_screenshot_white_is_mapped_exactly(self):
        reference = load_screenshot(self.screenshot)
        colors = {tuple(reference.get_at((x, y)))[:3] for x in range(reference.get_width())
                  for y in range(reference.get_height())}
        self.assertEqual({(0, 0, 0), WHITE}, colors)

    def test_one_pixel_off_is_counted_and_saved(self):
        generated = load_screenshot(self.screenshot, 2).copy()
        generated.set_at((10, 10), (254, 255, 255))  # nearly white, but not white
        with tempfile.TemporaryDirectory() as diff_dir:
            result = compare_with_screenshot(generated, self.screenshot, 2, diff_dir=diff_dir, name='one_off')
            self.assertEqual(1, result.differing_pixels)
            self.assertTrue(os.path.exists(result.diff_path))
            self.assertEqual((generated.get_width() * 3, generated.get_height()),
                             pygame.image.load(result.diff_path).get_size())

    def test_identical_is_zero_and_saves_nothing(self):
        with tempfile.TemporaryDirectory() as diff_dir:
            result = compare_with_screenshot(load_screenshot(self.screenshot), self.screenshot, diff_dir=diff_dir)
            self.assertEqual(0, result.differing_pixels)
            self.assertIsNone(result.diff_path)
            self.assertEqual([], os.listdir(diff_dir))

    def test_sizes_must_match(self):
        with self.assertRaises(ValueError):
            count_differing_pixels(pygame.Surface((2, 2)), pygame.Surface((2, 3)))
