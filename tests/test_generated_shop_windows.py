"""The shop windows generated from their NES window data (src/windows.py shop_inventory_layout and BUY_SELL_LAYOUT,
drawn by src/window_renderer.py), against the NES screenshots they replace: 0 differing pixels, at every scale, in
white and in the low HP red, with the cursor at every item, blinked off, and with no cursor. See
tests/nes_screen_diff.py."""
import os
import tempfile
from os.path import basename, dirname, join
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame
from pygame import KEYDOWN, K_DOWN, K_RETURN

from src.color import RED, WHITE
from src.config.test_config import test_config
from src.directories import Directories
from src.items import armor, shields, tools, weapons
from src.shops import ShopInventories
from src.window_renderer import render_window, window_tiles
from src.windows import (BUY_SELL_LAYOUT, SHOP_INVENTORY_WINDOW, Window, WindowText, name_halves,
                         shop_inventory_layout)
from tests.nes_screen_diff import compare_with_screenshot
from tests.helpers import new_game

SCALES = (1, 2, 3)
COLORS = (WHITE, RED)
DIFF_DIR = os.path.join(tempfile.gettempdir(), 'dragon_warrior_screen_diffs')

# NES ItemCostTbl (Bank00): the item indexes ShopItemsTbl uses
ITEM_COST_TBL = ("Bamboo Pole", "Club", "Copper Sword", "Hand Axe", "Broad Sword", "Flame Sword", "Erdrick's Sword",
                 "Clothes", "Leather Armor", "Chain Mail", "Half Plate", "Full Plate", "Magic Armor",
                 "Erdrick's Armor", "Small Shield", "Large Shield", "Silver Shield", "Herb", "Magic Key", "Torch",
                 "Fairy Water", "Wings", "Dragon's Scale")
# NES ShopItemsTbl (Bank00), every shop in the game, and the ShopInventories attribute for each
SHOP_ITEMS_TBL = {
    'kol_weapons_store_inventory': (0x02, 0x03, 0x0A, 0x0B, 0x0E),
    'brecconary_weapons_store_inventory': (0x00, 0x01, 0x02, 0x07, 0x08, 0x0E),
    'garinham_weapons_store_inventory': (0x01, 0x02, 0x03, 0x08, 0x09, 0x0A, 0x0F),
    'cantlin_weapons_store_north_inventory': (0x00, 0x01, 0x02, 0x08, 0x09, 0x0F),
    'cantlin_weapons_store_south_inventory': (0x03, 0x04, 0x0B, 0x0C),
    'cantlin_weapons_store_3_inventory': (0x05, 0x10),
    'rimuldar_weapons_store_inventory': (0x02, 0x03, 0x04, 0x0A, 0x0B, 0x0C),
    'kol_item_store_inventory': (0x11, 0x13, 0x16, 0x15),
    'brecconary_item_store_inventory': (0x11, 0x13, 0x16),
    'garinham_item_store_inventory': (0x11, 0x13, 0x16),
    'cantlin_item_store_1_inventory': (0x11, 0x13),
    'cantlin_item_store_2_inventory': (0x16, 0x15),
}
DIRECTORIES = Directories(test_config)
# The shops there are NES screenshots of (data/images/shops)
SHOP_SCREENSHOTS = {
    'brecconary_weapons_store_inventory': DIRECTORIES.BRECCONARY_WEAPONS_SHOP_PATH,
    'garinham_weapons_store_inventory': DIRECTORIES.GARINHAM_WEAPONS_SHOP_PATH,
    'kol_weapons_store_inventory': DIRECTORIES.KOL_WEAPONS_SHOP_PATH,
    'rimuldar_weapons_store_inventory': DIRECTORIES.RIMULDAR_WEAPONS_SHOP_PATH,
    'cantlin_weapons_store_north_inventory': DIRECTORIES.CANTLIN_WEAPONS_SHOP_NORTH_PATH,
    'cantlin_weapons_store_south_inventory': DIRECTORIES.CANTLIN_WEAPONS_SHOP_SOUTH_PATH,
}
ALL_ITEMS = {**weapons, **armor, **shields, **tools}


def cursor_screenshot(shop_screenshot: str, item: str) -> str:
    """The screenshot of a shop's window with the cursor at an item: <shop>_<item>.png, next to the shop's."""
    return join(dirname(shop_screenshot), f"{basename(shop_screenshot)[:-4]}_{item.lower().replace(' ', '_')}.png")


def shop_layout(inventory: dict):
    names = tuple(inventory)
    return shop_inventory_layout(names, tuple(inventory[name]['cost'] for name in names))


class ShopWindowTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.shops = ShopInventories(test_config)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def assert_matches(self, layout, screenshot, color, nes_pixel, name, **window):
        generated = render_window(layout, color, nes_pixel, **window)
        result = compare_with_screenshot(generated, screenshot, nes_pixel, window_color=color, diff_dir=DIFF_DIR,
                                         name=name)
        self.assertEqual(0, result.differing_pixels, str(result))


class TestShopInventoryScreenshots(ShopWindowTestCase):
    """ShopInvDat, against every shop screenshot in data/images/shops."""

    def test_every_shop_screenshot_has_its_cursor_screenshots(self):
        for shop, screenshot in SHOP_SCREENSHOTS.items():
            for item in getattr(self.shops, shop):
                with self.subTest(shop=shop, item=item):
                    self.assertTrue(os.path.exists(cursor_screenshot(screenshot, item)))

    def test_every_cursor_position(self):
        for shop, screenshot in SHOP_SCREENSHOTS.items():
            inventory = getattr(self.shops, shop)
            layout = shop_layout(inventory)
            for scale in SCALES:
                for color in COLORS:
                    for index, item in enumerate(inventory):
                        with self.subTest(shop=shop, item=item, scale=scale, color=color):
                            self.assert_matches(layout, cursor_screenshot(screenshot, item), color, scale,
                                                f'{shop}_{index}_{scale}_{color}', cursor_index=index)

    def test_cursor_hidden(self):
        # The "off" half of the blink blanks the cursor's tile: the screenshot without a cursor, wherever it is
        for shop, screenshot in SHOP_SCREENSHOTS.items():
            inventory = getattr(self.shops, shop)
            layout = shop_layout(inventory)
            for scale in SCALES:
                for color in COLORS:
                    for index in range(len(inventory)):
                        with self.subTest(shop=shop, entry=index, scale=scale, color=color):
                            self.assert_matches(layout, screenshot, color, scale,
                                                f'{shop}_hidden_{index}_{scale}_{color}', cursor_index=index,
                                                cursor_visible=False)

    def test_no_cursor(self):
        for shop, screenshot in SHOP_SCREENSHOTS.items():
            for scale in SCALES:
                for color in COLORS:
                    with self.subTest(shop=shop, scale=scale, color=color):
                        self.assert_matches(shop_layout(getattr(self.shops, shop)), screenshot, color, scale,
                                            f'{shop}_no_cursor_{scale}_{color}')


class TestEveryShop(ShopWindowTestCase):
    """Every shop in the game, with or without a screenshot: its stock is ShopItemsTbl's, and its window is built
    the way ShopInvDat builds it."""

    def test_every_shop_is_listed(self):
        shops = {name for name in vars(self.shops) if name.endswith('_inventory')}
        self.assertEqual(set(SHOP_ITEMS_TBL), shops)

    def test_stock_is_shop_items_tbl(self):
        for shop, indexes in SHOP_ITEMS_TBL.items():
            with self.subTest(shop=shop):
                inventory = getattr(self.shops, shop)
                self.assertEqual([ITEM_COST_TBL[index] for index in indexes], list(inventory))
                self.assertEqual([ALL_ITEMS[name]['cost'] for name in inventory],
                                 [item['cost'] for item in inventory.values()])

    def test_window_fits_the_stock(self):
        for shop in SHOP_ITEMS_TBL:
            inventory = getattr(self.shops, shop)
            layout = shop_layout(inventory)
            with self.subTest(shop=shop):
                # WndVariableHeight: one block per item, one for the borders
                self.assertEqual(SHOP_INVENTORY_WINDOW._replace(height=len(inventory) + 1), layout.window)
                self.assertEqual(tuple((1, 1 + 2 * index) for index in range(len(inventory))), layout.cursor_tiles)
                # Every text is inside the window (window_tiles raises otherwise), and every scale draws
                window_tiles(layout)
                for scale in SCALES:
                    for color in COLORS:
                        surface = render_window(layout, color, scale, cursor_index=len(inventory) - 1)
                        self.assertEqual((18 * 8 * scale, (len(inventory) + 1) * 16 * scale), surface.get_size())

    def test_entries(self):
        for shop in SHOP_ITEMS_TBL:
            inventory = getattr(self.shops, shop)
            texts = shop_layout(inventory).texts
            for index, (name, item) in enumerate(inventory.items()):
                with self.subTest(shop=shop, item=name):
                    first_half, second_half = name_halves(name)
                    cost = str(item['cost'])
                    row = 1 + 2 * index
                    self.assertIn(WindowText(first_half, 2, row), texts)
                    # WndItemCost: 5 tiles, right-aligned, the last one in column 16 (the right border is 17)
                    self.assertIn(WindowText(cost, 17 - len(cost), row), texts)
                    if second_half:
                        self.assertIn(WindowText(second_half, 3, row + 1), texts)

    def test_five_digit_cost(self):
        # Cantlin's guard sells the Silver Shield for 14800: all 5 of WndItemCost's tiles
        layout = shop_layout(self.shops.cantlin_weapons_store_3_inventory)
        self.assertEqual((WindowText("Flame", 2, 1), WindowText("9800", 13, 1), WindowText("Sword", 3, 2),
                          WindowText("Silver", 2, 3), WindowText("14800", 12, 3), WindowText("Shield", 3, 4)),
                         layout.texts)

    def test_cost_too_long(self):
        with self.assertRaises(ValueError):
            shop_inventory_layout(("Herb",), (100000,))


class TestBuySellWindow(ShopWindowTestCase):
    """BuySellDat. There is no screenshot of it, but it is YesNo1Dat's window with BUY and SELL instead of YES and
    NO: the same size, position, spacing and cursor home. So with YES and NO, it must be the YES/NO screenshots."""

    def test_window_data(self):
        self.assertEqual(Window(5, 2, 4, 3), BUY_SELL_LAYOUT.window)
        self.assertEqual((WindowText("BUY", 2, 2), WindowText("SELL", 2, 4)), BUY_SELL_LAYOUT.texts)
        self.assertEqual(((1, 2), (1, 4)), BUY_SELL_LAYOUT.cursor_tiles)

    def test_yes_no_screenshots(self):
        yes_no = BUY_SELL_LAYOUT._replace(texts=(WindowText("YES", 2, 2), WindowText("NO", 2, 4)))
        for scale in SCALES:
            for color in COLORS:
                with self.subTest(scale=scale, color=color):
                    self.assert_matches(yes_no, DIRECTORIES.CONFIRMATION_BACKGROUND_PATH, color, scale,
                                        f'yes_no_{scale}_{color}', cursor_index=0, cursor_visible=False)
                    self.assert_matches(yes_no, DIRECTORIES.CONFIRMATION_YES_BACKGROUND_PATH, color, scale,
                                        f'yes_{scale}_{color}', cursor_index=0)


class TestDrawnByTheShop(TestCase):
    """What the game actually draws on its screen when a shop opens its window, at its own scale, where the
    screenshot is: through DialogLookup.open_store_inventory, the cursor moved with the keys."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        saved = {key: test_config[key] for key in ('NO_WAIT', 'NO_BLIT')}
        test_config['NO_WAIT'] = True
        test_config['NO_BLIT'] = False
        self.addCleanup(test_config.update, saved)
        self.game = new_game()
        self.dialog_lookup = self.game.cmd_menu.dialog_lookup

    def choose(self, inventory, index):
        """Open the shop's window, move the cursor to the item at index and choose it."""
        keys = [K_DOWN] * index + [K_RETURN]
        events = [[MagicMock(type=KEYDOWN, key=key)] for key in keys]
        with patch('src.selection.event.get', side_effect=events), \
                patch('data.text.dialog_lookup_table.display'), \
                patch.object(self.game.cmd_menu, 'window_drop_down_effect'), \
                patch.object(self.game.cmd_menu, 'remove_window'):  # the answered window is taken off afterwards (#283)
            return self.dialog_lookup.open_store_inventory(inventory)

    def test_every_cursor_position(self):
        tile_size = test_config['TILE_SIZE']
        for shop, screenshot in SHOP_SCREENSHOTS.items():
            inventory = getattr(self.dialog_lookup.shop_inventories, shop)
            window = SHOP_INVENTORY_WINDOW._replace(height=len(inventory) + 1)
            area = pygame.Rect(window.x * tile_size, window.y * tile_size, window.width * tile_size,
                               window.height * tile_size)
            for color in COLORS:
                # Game.load_window_palette: red at low HP
                self.game.color = color
                for index, item in enumerate(inventory):
                    with self.subTest(shop=shop, item=item, color=color):
                        self.assertEqual(item, self.choose(inventory, index))
                        result = compare_with_screenshot(self.game.screen, cursor_screenshot(screenshot, item),
                                                         test_config['SCALE'], window_color=color, area=area,
                                                         diff_dir=DIFF_DIR, name=f'{shop}_game_{index}')
                        self.assertEqual(0, result.differing_pixels, str(result))

    def test_buy_sell_window(self):
        # The window the item shops open, with the cursor on SELL: YesNo1Dat's border and cursor, with BUY and SELL
        tile_size = test_config['TILE_SIZE']
        events = [[MagicMock(type=KEYDOWN, key=K_DOWN)], [MagicMock(type=KEYDOWN, key=K_RETURN)]]
        with patch('src.selection.event.get', side_effect=events), \
                patch('data.text.dialog_lookup_table.display'), \
                patch.object(self.game.cmd_menu, 'window_drop_down_effect'), \
                patch.object(self.game.cmd_menu, 'remove_window'):  # the answered window is taken off afterwards (#283)
            self.assertEqual(1, self.dialog_lookup.select_in_generated_window(BUY_SELL_LAYOUT))
        nes_pixel = test_config['SCALE']
        expected = render_window(BUY_SELL_LAYOUT, self.dialog_lookup.color, nes_pixel, cursor_index=1)
        drawn = self.game.screen.subsurface(pygame.Rect(5 * tile_size, 2 * tile_size, 4 * tile_size, 3 * tile_size))
        self.assertEqual(pygame.image.tobytes(expected, 'RGB'), pygame.image.tobytes(drawn, 'RGB'))

