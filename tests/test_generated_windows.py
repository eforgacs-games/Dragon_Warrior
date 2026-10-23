"""Generated windows (src/window_renderer.py) against the NES screenshots they replace: 0 differing pixels, at every
scale, for every variant. See tests/nes_screen_diff.py."""
import os
import tempfile
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame

from src.color import RED, WHITE
from src.config.test_config import test_config
from src.directories import Directories
from src.cursor import CURSOR_TILE
from src import window_renderer
from src.window_renderer import (TL_TOP1, TL_TOP2, glyph_tile, render_window, window_tiles)
from src.windows import (COMBAT_COMMAND_LAYOUT, DIALOG_LAYOUT, POPUP_LAYOUT, STATUS_LAYOUT, YES_NO_LAYOUT, Window,
                         WindowLayout, WindowText, item_menu_layout)
from tests.nes_screen_diff import compare_with_screenshot, count_differing_pixels, load_screenshot
from tests.helpers import new_game

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


def screenshot_path(name: str) -> str:
    return os.path.join(Directories(test_config).IMAGES_DIR, name)


# The miscellaneous windows: (name, layout, screenshot, render_window's cursor arguments). Each screenshot is one
# pixel per NES pixel, white on black, and stays in data/images as the reference.
MISCELLANEOUS_WINDOWS = (
    ('dialog', DIALOG_LAYOUT, 'dialog_box_background.png', {}),
    ('yes_no_no_cursor', YES_NO_LAYOUT, 'confirmation.png', {}),
    ('yes_no_yes', YES_NO_LAYOUT, 'confirmation_yes.png', {'cursor_index': 0}),
    ('yes_no_no', YES_NO_LAYOUT, 'confirmation_no.png', {'cursor_index': 1}),
    # The "off" half of the blink blanks the cursor's tile: the screenshot without a cursor, wherever it is
    ('yes_no_yes_hidden', YES_NO_LAYOUT, 'confirmation.png', {'cursor_index': 0, 'cursor_visible': False}),
    ('yes_no_no_hidden', YES_NO_LAYOUT, 'confirmation.png', {'cursor_index': 1, 'cursor_visible': False}),
    ('popup', POPUP_LAYOUT, 'hovering_stats_window.png', {}),
    ('status', STATUS_LAYOUT, 'status_window_background.png', {}),
    # The SPELL and ITEM windows' border, at the three heights there are screenshots of
    ('item_1', item_menu_layout('inventory', 1), 'menus/item_menu/item_menu_background_1.png', {}),
    ('item_2', item_menu_layout('inventory', 2), 'menus/item_menu/item_menu_background_2.png', {}),
    ('spell_5', item_menu_layout('spells', 5), 'menus/item_menu/item_menu_background_5.png', {}),
)


class TestMiscellaneousWindows(TestCase):
    """DialogDat, YesNo1Dat, PopupDat, StatusDat and the SpellDat/PlayerInvDat border, against their screenshots."""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_every_window_and_variant(self):
        for name, layout, screenshot, cursor in MISCELLANEOUS_WINDOWS:
            for scale in SCALES:
                for color in (WHITE, RED):
                    with self.subTest(window=name, scale=scale, color=color):
                        generated = render_window(layout, color, scale, **cursor)
                        result = compare_with_screenshot(generated, screenshot_path(screenshot), scale,
                                                         window_color=color, diff_dir=DIFF_DIR,
                                                         name=f'{name}_{scale}_{color}')
                        self.assertEqual(0, result.differing_pixels, str(result))

    def test_yes_no_cursor_tiles(self):
        # YesNo1Dat: cursor home X = 1, Y = 2; one column, double spaced
        self.assertEqual(((1, 2), (1, 4)), YES_NO_LAYOUT.cursor_tiles)

    def test_item_window_is_sized_to_its_entries(self):
        for entries in range(1, 11):
            self.assertEqual(Window(9, 3, 6, entries + 1), item_menu_layout('inventory', entries).window)
            self.assertEqual(Window(9, 2, 6, entries + 1), item_menu_layout('spells', entries).window)


class TestMiscellaneousWindowsDrawnByTheGame(TestCase):
    """What the game draws on its screen, at its own scale and window positions, with the dynamic text (the name,
    the values, the dialog text, the SPELL title) off (RENDER_TEXT): the screenshots are of the windows without it."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        config = dict(test_config, NO_WAIT=True, RENDER_TEXT=False, NO_BLIT=True)
        self.game = new_game(config)
        self.config = self.game.game_state.config
        self.cmd_menu = self.game.cmd_menu
        self.tile_size = self.config['TILE_SIZE']

    def assert_drawn(self, draw, window, screenshot, name):
        area = pygame.Rect(window.x * self.tile_size, window.y * self.tile_size, window.width * self.tile_size,
                           window.height * self.tile_size)
        for color in (WHITE, RED):
            self.game.color = color
            with self.subTest(window=name, color=color), patch.dict(self.config, NO_BLIT=False), \
                    patch('src.menu.display'):
                self.game.screen.fill((0, 0, 255))  # anything the window doesn't cover would show
                draw()
                result = compare_with_screenshot(self.game.screen, screenshot_path(screenshot), self.config['SCALE'],
                                                 window_color=color, area=area, diff_dir=DIFF_DIR,
                                                 name=f'game_{name}_{color}')
                self.assertEqual(0, result.differing_pixels, str(result))

    def test_dialog_window(self):
        self.assert_drawn(self.cmd_menu.draw_dialog_window, DIALOG_LAYOUT.window, 'dialog_box_background.png',
                          'dialog')

    def test_yes_no_window(self):
        for yes_selected, screenshot in ((True, 'confirmation_yes.png'), (False, 'confirmation_no.png')):
            self.assert_drawn(lambda: self.cmd_menu.draw_yes_no_window(yes_selected, True), YES_NO_LAYOUT.window,
                              screenshot, f'yes_no_{yes_selected}')
            self.assert_drawn(lambda: self.cmd_menu.draw_yes_no_window(yes_selected, False), YES_NO_LAYOUT.window,
                              'confirmation.png', f'yes_no_{yes_selected}_hidden')

    def test_popup_window(self):
        self.assert_drawn(lambda: self.game.drawer.draw_hovering_stats_window(self.game.screen, self.game.player,
                                                                              self.game.color),
                          POPUP_LAYOUT.window, 'hovering_stats_window.png', 'popup')

    def test_status_window(self):
        self.assert_drawn(self.cmd_menu.draw_status_window, STATUS_LAYOUT.window, 'status_window_background.png',
                          'status')

    def test_item_window(self):
        for entries, screenshot in ((["Herb"], 'item_menu_background_1.png'),
                                    (["Herb", "Torch"], 'item_menu_background_2.png'),
                                    (["Herb", "Torch", "Wings", "Magic Key", "Fairy Water"],
                                     'item_menu_background_5.png')):
            self.assert_drawn(lambda: self.cmd_menu.draw_item_menu('inventory', entries),
                              item_menu_layout('inventory', len(entries)).window,
                              f'menus/item_menu/{screenshot}', f'item_{len(entries)}')

    def test_confirmation_prompt_opens_without_a_cursor(self):
        # data/text/dialog.py draws YesNo1Dat without its cursor first, as confirmation.png shows it
        from data.text.dialog import confirmation_prompt
        with patch.object(self.cmd_menu, 'show_line_in_dialog_box'), \
                patch.object(self.cmd_menu, 'window_drop_down_effect'), \
                patch.object(self.cmd_menu, 'draw_yes_no_window'), patch('data.text.dialog.display'), \
                patch.object(self.cmd_menu, 'remove_window'):  # the answered window is taken off afterwards (#283)
            self.assert_drawn(lambda: confirmation_prompt(self.cmd_menu, "", MagicMock(), MagicMock(), self.config,
                                                          self.game.color, skip_text=True),
                              YES_NO_LAYOUT.window, 'confirmation.png', 'confirmation_prompt')


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
