import os
from unittest import TestCase
from unittest.mock import MagicMock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from pygame import KEYDOWN, K_DOWN, K_ESCAPE, K_RETURN, event

from src.config.test_config import test_config
from src.game import Game
from src.windows import ADVENTURE_LOG_WINDOW_1, ADVENTURE_LOG_WINDOW_2, ALPHABET_WINDOW, BUY_SELL_WINDOW, \
    COMBAT_COMMAND_WINDOW, COMMAND_WINDOW, CONTINUE_CHANGE_ERASE_WINDOW, DIALOG_WINDOW, ERASE_LOG_WINDOW, \
    FULL_MENU_WINDOW, INPUT_NAME_WINDOW, MESSAGE_SPEED_WINDOW, NAME_ENTRY_WINDOW, NEW_QUEST_WINDOW, POPUP_WINDOW, \
    SHOP_INVENTORY_WINDOW, STATUS_WINDOW, YES_NO_2_WINDOW, YES_NO_WINDOW, Window, name_halves, \
    variable_height_window

# NES Bank01 window data: (height in blocks, width in tiles, position byte (Y << 4 | X, in blocks))
NES_WINDOW_DATA = {
    'PopupDat': (POPUP_WINDOW, 0x06, 0x08, 0x21),
    'StatusDat': (STATUS_WINDOW, 0x0B, 0x14, 0x35),
    'DialogDat': (DIALOG_WINDOW, 0x05, 0x18, 0x92),
    'CmdNonCmbtDat': (COMMAND_WINDOW, 0x05, 0x10, 0x16),
    'CmdCmbtDat': (COMBAT_COMMAND_WINDOW, 0x03, 0x10, 0x16),
    'ShopInvDat': (SHOP_INVENTORY_WINDOW, 0x08, 0x12, 0x25),
    'YesNo1Dat': (YES_NO_WINDOW, 0x03, 0x08, 0x25),
    'BuySellDat': (BUY_SELL_WINDOW, 0x03, 0x08, 0x25),
    'AlphabetDat': (ALPHABET_WINDOW, 0x07, 0x18, 0x52),
    'MsgSpeedDat': (MESSAGE_SPEED_WINDOW, 0x07, 0x12, 0x74),
    'InputNameDat': (INPUT_NAME_WINDOW, 0x02, 0x14, 0x73),
    'NameEntryDat': (NAME_ENTRY_WINDOW, 0x03, 0x0C, 0x35),
    'ContChngErsDat': (CONTINUE_CHANGE_ERASE_WINDOW, 0x04, 0x18, 0x42),
    'FullMenuDat': (FULL_MENU_WINDOW, 0x06, 0x18, 0x42),
    'NewQuestDat': (NEW_QUEST_WINDOW, 0x02, 0x18, 0x42),
    'LogList123Dat1': (ADVENTURE_LOG_WINDOW_1, 0x04, 0x14, 0x95),
    'LogList123Dat2': (ADVENTURE_LOG_WINDOW_2, 0x04, 0x18, 0x63),
    'EraseLogDat': (ERASE_LOG_WINDOW, 0x06, 0x14, 0x73),
    'YesNo2Dat': (YES_NO_2_WINDOW, 0x03, 0x08, 0x3A),
}


class TestWindowData(TestCase):

    def test_windows_match_the_nes_window_data(self):
        for label, (window, height, width_in_tiles, position) in NES_WINDOW_DATA.items():
            with self.subTest(label):
                self.assertEqual(Window(position & 0x0F, position >> 4, width_in_tiles // 2, height), window)

    def test_windows_fit_on_the_screen(self):
        nes_width, nes_height = test_config['NES_RES']
        for label, (window, *_) in NES_WINDOW_DATA.items():
            with self.subTest(label):
                self.assertLessEqual((window.x + window.width) * 16, nes_width)
                self.assertLessEqual((window.y + window.height) * 16, nes_height)

    def test_variable_height_window(self):
        for items in range(1, 8):
            self.assertEqual(Window(5, 2, 9, items + 1), variable_height_window(SHOP_INVENTORY_WINDOW, items))

    def test_name_halves(self):
        self.assertEqual(("Copper", "Sword"), name_halves("Copper Sword"))
        self.assertEqual(("Club", ""), name_halves("Club"))
        self.assertEqual(("Magic", "Key"), name_halves("Magic Key"))
        self.assertEqual(("Stones of", "Sunlight"), name_halves("Stones of Sunlight"))


class WindowTestCase(TestCase):
    no_blit = True

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.saved_config = {key: test_config[key] for key in ('NO_WAIT', 'RENDER_TEXT', 'NO_BLIT')}
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = not self.no_blit
        test_config['NO_BLIT'] = self.no_blit
        self.addCleanup(test_config.update, self.saved_config)
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.cmd_menu = self.game.cmd_menu
        self.dialog_lookup = self.cmd_menu.dialog_lookup
        self.player = self.game.player
        self.nes_tile = test_config['TILE_SIZE'] / 2

    def tile(self, x, y):
        """Screen pixels to NES tiles."""
        return x / self.nes_tile, y / self.nes_tile


class TestCommandWindow(WindowTestCase):
    no_blit = False

    def white_columns(self, top, bottom, left, right):
        """The screen columns between left and right with a white pixel between rows top and bottom."""
        screen = self.game.screen
        return [x for x in range(left, right) if any(sum(screen.get_at((x, y))[:3]) > 600 for y in range(top, bottom))]

    def test_command_window_is_drawn_at_cmd_non_cmbt_dat(self):
        tile_size = test_config['TILE_SIZE']
        self.game.screen.fill((0, 0, 0))
        self.cmd_menu.launch_signaled = True
        with patch.object(self.cmd_menu, 'window_drop_down_effect') as drop_down:
            self.game.drawer.handle_menu_launch(self.game.screen, self.cmd_menu, self.cmd_menu)
        drop_down.assert_called_once_with(6, 1, 8, 5)
        self.game.drawer.handle_menu_launch(self.game.screen, self.cmd_menu, self.cmd_menu)
        # The border: nothing drawn left of block 6 or right of block 14, the border inside the first and last tiles
        border_columns = self.white_columns(tile_size, 6 * tile_size, 0, self.game.screen.get_width())
        self.assertGreaterEqual(min(border_columns), 6 * tile_size)
        self.assertLess(min(border_columns), 6 * tile_size + self.nes_tile)
        self.assertLess(max(border_columns), 14 * tile_size)
        self.assertGreaterEqual(max(border_columns), 14 * tile_size - self.nes_tile)
        # Tile row 2 holds the cursor in tile column 1, TALK from column 2 and SPELL from column 10. The cursor is
        # the NES arrow tile (TL_RIGHT_ARROW), whose point is 2 NES pixels in from the tile's left edge.
        row_top = int((2 + 2) * self.nes_tile)
        columns = self.white_columns(row_top, row_top + int(self.nes_tile), int(6 * tile_size + self.nes_tile),
                                     int(14 * tile_size - self.nes_tile))
        window_left = 12 * self.nes_tile
        self.assertEqual(window_left + 1 * self.nes_tile + 2 * test_config['SCALE'], min(columns))
        self.assertIn(window_left + 2 * self.nes_tile, columns)
        self.assertNotIn(window_left + 2 * self.nes_tile - 1, columns)
        self.assertIn(window_left + 10 * self.nes_tile, columns)
        self.assertNotIn(window_left + 10 * self.nes_tile - 1, columns)

    def test_command_window_surface_is_the_window_size(self):
        tile_size = test_config['TILE_SIZE']
        self.assertEqual((8 * tile_size, 5 * tile_size), self.cmd_menu.command_menu_surface.get_size())
        self.assertEqual((8 * tile_size, 5 * tile_size), self.cmd_menu.command_window_frame.get_size())


class TestStatusWindow(WindowTestCase):

    def test_status_window_position_and_layout(self):
        self.player.name = 'ERDRICK'
        self.player.weapon, self.player.armor, self.player.shield = 'Copper Sword', 'Clothes', 'Small Shield'
        with patch('src.menu.draw_text') as draw_text, \
                patch.object(self.cmd_menu.graphics, 'create_window') as create_window:
            self.cmd_menu.draw_status_window()
        self.assertEqual((5, 3, 10, 11), create_window.call_args.args[:4])
        drawn = [(call.args[0], call.kwargs['alignment'], *self.tile(*call.args[1:3]))
                 for call in draw_text.call_args_list]
        # The window is at tile (10, 6). The name follows "NAME:" at tile column 11 of row 1.
        self.assertEqual(('ERDRICK', 'left', 10 + 11, 6 + 1.5), drawn[0])
        # The numbers end at tile column 18 (draw_text's right edge is the left edge of column 19), every other row
        values = [self.player.strength, self.player.agility, self.player.max_hp, self.player.max_mp,
                  self.player.attack_power, self.player.defense_power]
        rows = (3, 5, 7, 9, 11, 13)
        self.assertEqual([(str(value), 'right', 10 + 19, 6 + row + 0.5) for value, row in zip(values, rows)],
                         drawn[1:7])
        # The equipment in two halves: column 10, then column 11 on the next row
        self.assertEqual([('Copper', 'left', 10 + 10, 6 + 15.5), ('Sword', 'left', 10 + 11, 6 + 16.5),
                          ('Clothes', 'left', 10 + 10, 6 + 17.5),
                          ('Small', 'left', 10 + 10, 6 + 19.5), ('Shield', 'left', 10 + 11, 6 + 20.5)], drawn[7:])

    def test_status_drops_down_at_status_dat(self):
        escape = MagicMock(type=KEYDOWN, key=K_ESCAPE)
        with patch.object(event, 'get', return_value=[escape]), \
                patch.object(self.cmd_menu, 'window_drop_down_effect') as drop_down, \
                patch.object(self.cmd_menu, 'window_drop_up_effect') as drop_up, \
                patch.object(self.game, 'unlaunch_menu'):
            self.cmd_menu.status()
        drop_down.assert_called_once_with(5, 3, 10, 11)
        drop_up.assert_called_once_with(5, 3, 10, 11)


class TestItemWindowOrder(WindowTestCase):

    def open_item_menu(self, menu_name, keys):
        events = [[MagicMock(type=KEYDOWN, key=key)] for key in keys]
        with patch.object(event, 'get', side_effect=events), \
                patch('src.menu.draw_text') as draw_text, \
                patch.object(self.cmd_menu.graphics, 'create_window') as create_window, \
                patch.object(self.cmd_menu, 'draw_window_cursor'):
            chosen = self.cmd_menu.display_item_menu(menu_name)
        return chosen, draw_text, create_window

    def test_items_are_listed_herbs_then_keys_then_slots(self):
        self.player.inventory = ['Torch', 'Herb', 'Wings', 'Magic Key', 'Herb', 'Torch']
        _, draw_text, create_window = self.open_item_menu('inventory', [K_ESCAPE])
        first_halves = [call.args[0] for call in draw_text.call_args_list
                        if call.args[1] == 20 * self.nes_tile]
        self.assertEqual(['Herb', 'Magic', 'Torch', 'Wings', 'Torch'], first_halves)
        # Each Torch has its own slot and its own entry
        self.assertEqual((9, 3, 6, 6), create_window.call_args.args[:4])

    def test_the_chosen_item_is_the_one_shown(self):
        self.player.inventory = ['Torch', 'Wings', 'Herb']
        # Herb, Torch, Wings: the second entry is the Torch, though it is first in the inventory list
        chosen, _, _ = self.open_item_menu('discard', [K_DOWN, K_RETURN])
        self.assertEqual('Torch', chosen)
        self.player.inventory = ['Torch', 'Wings', 'Magic Key']
        chosen, _, _ = self.open_item_menu('discard', [K_DOWN, K_DOWN, K_RETURN])
        self.assertEqual('Wings', chosen)

    def test_battle_item_window_uses_the_same_order(self):
        self.player.inventory = ['Wings', 'Herb']
        self.cmd_menu.current_battle = MagicMock()
        with patch.object(self.cmd_menu, 'use_item_in_battle') as use_item:
            self.open_item_menu('inventory', [K_RETURN])
        use_item.assert_called_once_with('Herb')


class TestShopWindows(WindowTestCase):

    def run_window(self, function, *keys):
        # One key press per pass of the window's loop, so the cursor is drawn after each move
        events = [[MagicMock(type=KEYDOWN, key=key)] for key in keys]
        with patch('data.text.dialog_lookup_table.get', side_effect=events), \
                patch('data.text.dialog_lookup_table.draw_text') as draw_text, \
                patch('src.menu.draw_text') as item_draw_text, \
                patch('src.common.Graphics.create_window') as create_window, \
                patch.object(self.cmd_menu, 'window_drop_down_effect') as drop_down, \
                patch.object(self.cmd_menu, 'draw_window_cursor') as self.draw_cursor:
            result = function()
        return result, draw_text, item_draw_text, create_window, drop_down

    def positions(self, draw_text):
        return [(call.args[0], *self.tile(*call.args[1:3])) for call in draw_text.call_args_list]

    def test_buy_sell_window(self):
        result, draw_text, _, create_window, drop_down = self.run_window(
            lambda: self.dialog_lookup.select_from_text_menu(['BUY', 'SELL'], BUY_SELL_WINDOW), K_DOWN, K_RETURN)
        self.assertEqual(1, result)
        drop_down.assert_called_once_with(5, 2, 4, 3)
        self.assertEqual((5, 2, 4, 3), create_window.call_args.args[:4])
        # Window at tile (10, 4): BUY on tile row 2 and SELL on row 4, at column 2; the cursor in column 1
        positions = self.positions(draw_text)
        self.assertIn(('BUY', 12, 6.5), positions)
        self.assertIn(('SELL', 12, 8.5), positions)
        # The cursor ends on SELL, in column 1 of row 4, held on after the choice (WndAPressed)
        self.assertEqual((5, 2, 1, 4, True), self.draw_cursor.call_args.args)

    def test_shop_inventory_window(self):
        shop = self.dialog_lookup.shop_inventories.kol_item_store_inventory
        result, draw_text, _, create_window, drop_down = self.run_window(
            lambda: self.dialog_lookup.open_store_inventory(shop), K_DOWN, K_DOWN, K_RETURN)
        self.assertEqual("Dragon's Scale", result)
        drop_down.assert_called_once_with(5, 2, 9, len(shop) + 1)
        self.assertEqual((5, 2, 9, len(shop) + 1), create_window.call_args.args[:4])
        # Window at tile (10, 4). Each item is one block: the first half of its name at column 2, the cost ending at
        # column 16 (draw_text's right edge at column 17), the second half on the next row at column 3.
        positions = self.positions(draw_text)
        self.assertIn(('Herb', 12, 5.5), positions)
        self.assertIn(('24', 27, 5.5), positions)
        self.assertIn(('Torch', 12, 7.5), positions)
        self.assertIn(("Dragon's", 12, 9.5), positions)
        self.assertIn(('20', 27, 9.5), positions)
        self.assertIn(('Scale', 13, 10.5), positions)
        right_aligned = [call.args[0] for call in draw_text.call_args_list if call.kwargs.get('alignment') == 'right']
        self.assertEqual(['24', '8', '20', '70'], right_aligned[:4])
        # The cursor is on the third item, at column 1, held on after the choice (WndAPressed)
        self.assertEqual((5, 2, 1, 5, True), self.draw_cursor.call_args.args)

    def test_weapon_shop_window_position(self):
        shop = self.dialog_lookup.shop_inventories.brecconary_weapons_store_inventory
        result, _, _, create_window, drop_down = self.run_window(
            lambda: self.dialog_lookup.open_store_inventory(shop, self.dialog_lookup.directories.
                                                            BRECCONARY_WEAPONS_SHOP_PATH), K_RETURN)
        self.assertEqual('Bamboo Pole', result)
        drop_down.assert_called_once_with(5, 2, 9, len(shop) + 1)
        self.assertEqual((5, 2, 9, len(shop) + 1), create_window.call_args.args[:4])

    def test_sell_window_is_the_item_window_in_nes_order(self):
        self.player.inventory = ['Wings', 'Torch', 'Herb']
        self.player.gold = 0
        say = patch.object(self.dialog_lookup, 'say')
        say.start()
        self.addCleanup(say.stop)
        with patch('data.text.dialog_lookup_table.confirmation_prompt',
                   side_effect=lambda command_menu, prompt, yes_path_function, no_path_function, **kwargs:
                   yes_path_function() if 'buy' in prompt else no_path_function()) as confirm, \
                patch.object(self.dialog_lookup, 'tool_shop_goodbye'):
            # Herb, Wings, Torch: the third entry is the Torch
            _, _, item_draw_text, create_window, drop_down = self.run_window(
                lambda: self.dialog_lookup.sell_tool(self.dialog_lookup.shop_inventories.kol_item_store_inventory),
                K_DOWN, K_DOWN, K_RETURN)
        self.assertIn('Torch', confirm.call_args_list[0].args[1])
        self.assertEqual(['Wings', 'Herb'], self.player.inventory)
        # NES DoToolSell shows WND_INVTRY1 (PlayerInvDat), as the ITEM command does
        drop_down.assert_called_once_with(9, 3, 6, 4)
        self.assertEqual((9, 3, 6, 4), create_window.call_args_list[0].args[:4])
        self.assertEqual(['Herb', '1', 'Wings', 'Torch'], [call.args[0] for call in item_draw_text.call_args_list[:4]])
