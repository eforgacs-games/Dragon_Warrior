"""BAG (src/items.py bag_slots): the NES's 8 inventory slots, or 16. Not NES."""
from contextlib import ExitStack
from unittest import TestCase
from unittest.mock import MagicMock, patch

from pygame import KEYDOWN, K_DOWN, K_ESCAPE, K_RETURN, K_UP, event

from src.config.base_config import base_config
from src.config.test_config import test_config
from src.items import BIG_BAG_SLOTS, INVENTORY_SLOTS, bag_slots
from src.options_screen import BAG_SIZE_SAVE_KEY, options_from_save
from src.shops import inventory_is_full
from src.windows import ITEM_MENU_MAX_ENTRIES, first_shown_entry, item_menu_window
from tests.test_windows import WindowTestCase

SIXTEEN = ['Torch', 'Fairy Water', 'Wings', "Dragon's Scale"] * 4


class TestBagSlots(TestCase):

    def test_nes_by_default(self):
        self.assertEqual(8, base_config['BAG_SIZE'])
        self.assertEqual(8, bag_slots({}))
        self.assertEqual(8, bag_slots({'BAG_SIZE': 12}))
        self.assertEqual(16, bag_slots({'BAG_SIZE': 16}))

    def test_full(self):
        self.assertFalse(inventory_is_full(['Torch'] * 15, BIG_BAG_SLOTS))
        self.assertTrue(inventory_is_full(['Torch'] * 16, BIG_BAG_SLOTS))
        # Herbs and Magic Keys never use a slot
        self.assertFalse(inventory_is_full(['Torch'] * 15 + ['Herb'] * 6 + ['Magic Key'] * 6, BIG_BAG_SLOTS))
        # back at 8 with more than 8: full, until it's down to 7
        self.assertTrue(inventory_is_full(['Torch'] * 12, INVENTORY_SLOTS))
        self.assertFalse(inventory_is_full(['Torch'] * 7, INVENTORY_SLOTS))

    def test_kept_per_adventure_log(self):
        self.assertEqual(16, options_from_save({BAG_SIZE_SAVE_KEY: 16}).bag_size)
        self.assertEqual(8, options_from_save({}).bag_size)
        self.assertEqual(8, options_from_save({BAG_SIZE_SAVE_KEY: True}).bag_size)


class TestFirstShownEntry(TestCase):

    def test_scrolls_only_past_the_edges(self):
        self.assertEqual(0, first_shown_entry(9, 0, 18))
        self.assertEqual(1, first_shown_entry(10, 0, 18))
        self.assertEqual(8, first_shown_entry(17, 7, 18))
        self.assertEqual(8, first_shown_entry(8, 8, 18))
        self.assertEqual(7, first_shown_entry(7, 8, 18))
        self.assertEqual(0, first_shown_entry(3, 0, 5))

    def test_the_window_is_never_taller_than_the_nes_one(self):
        self.assertEqual((9, 3, 6, 11), item_menu_window('inventory', 10))
        self.assertEqual((9, 3, 6, 11), item_menu_window('inventory', 18))
        self.assertEqual((9, 3, 6, 4), item_menu_window('inventory', 3))


class BagTestCase(WindowTestCase):

    def setUp(self):
        super().setUp()
        saved = test_config['BAG_SIZE']
        self.addCleanup(test_config.__setitem__, 'BAG_SIZE', saved)  # new_game uses test_config itself
        self.config = self.game.game_state.config
        self.config['BAG_SIZE'] = BIG_BAG_SLOTS


class TestBigBag(BagTestCase):

    def open_chest(self):
        """TAKE the Rimuldar chest (Wings). Returns the text shown."""
        cmd_menu = self.cmd_menu
        cmd_menu.map_name = 'Rimuldar'
        self.player.row, self.player.column = (31, 32)
        self.player.current_tile = 'TREASURE_BOX'
        with ExitStack() as stack:
            stack.enter_context(patch.object(cmd_menu, 'set_tile_by_coordinates'))
            show_text = stack.enter_context(patch.object(cmd_menu, 'show_text_in_dialog_box'))
            cmd_menu.take()
        return [call.args[0] for call in show_text.call_args_list]

    def test_a_chest_fills_the_ninth_slot(self):
        self.player.inventory = ['Torch'] * 8
        self.open_chest()
        self.assertEqual(['Torch'] * 8 + ['Wings'], self.player.inventory)

    def test_sixteen_full_asks_to_discard_as_on_the_nes(self):
        self.player.inventory = list(SIXTEEN)
        with patch.object(self.cmd_menu, 'prompt_yes_no', return_value=True), \
                patch.object(self.cmd_menu, 'display_item_menu', return_value='Torch'):
            messages = self.open_chest()
        self.assertEqual(('Thou hast dropped thy Torch.', 'And obtained the Wings.'), messages[-1])
        self.assertEqual(16, len(self.player.inventory))
        self.assertEqual('Wings', self.player.inventory[0])  # the dropped Torch's slot

    def test_back_to_8_keeps_every_item(self):
        self.player.inventory = ['Torch'] * 12
        self.config['BAG_SIZE'] = INVENTORY_SLOTS
        with patch.object(self.cmd_menu, 'prompt_yes_no', return_value=False):
            messages = self.open_chest()
        self.assertEqual('Thou hast given up thy Wings.', messages[-1])
        self.assertEqual(['Torch'] * 12, self.player.inventory)

    def test_shops_sell_up_to_16(self):
        self.player.inventory = ['Torch'] * 15
        self.player.gold = 1000
        say = patch.object(self.dialog_lookup, 'say').start()
        self.addCleanup(patch.stopall)
        patch.object(self.dialog_lookup, 'open_store_inventory', return_value='Wings').start()
        patch.object(self.dialog_lookup, 'confirm').start()
        patch.object(self.cmd_menu, 'show_popup_window').start()
        store = self.dialog_lookup.shop_inventories.kol_item_store_inventory
        self.dialog_lookup.buy_tool(store)
        self.assertEqual(16, len(self.player.inventory))
        self.dialog_lookup.buy_tool(store)
        self.assertEqual(16, len(self.player.inventory))
        self.assertEqual("Thou cannot carry anymore.", say.call_args_list[-1].args[0])

    def test_saved_and_loaded(self):
        import json
        import os
        import tempfile
        self.player.inventory = list(SIXTEEN)
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.cmd_menu.directories.save_dir = tmp_dir
            self.player.adventure_log = 1
            self.cmd_menu.save()
            with open(os.path.join(tmp_dir, 'save_slot_1.json')) as save_file:
                save = json.load(save_file)
        self.assertEqual(16, save[BAG_SIZE_SAVE_KEY])
        self.config['BAG_SIZE'] = INVENTORY_SLOTS
        with patch.object(self.game.map_mgr, 'change_map'):
            self.game.load_game(save)
        self.assertEqual(SIXTEEN, list(self.player.inventory))
        self.assertEqual(16, self.config['BAG_SIZE'])


class TestScrollingItemWindow(BagTestCase):

    def open_item_menu(self, menu_name, keys):
        events = [[MagicMock(type=KEYDOWN, key=key)] for key in keys]
        with patch.object(event, 'get', side_effect=events), \
                patch('src.menu.draw_text') as draw_text, \
                patch('src.menu.draw_window') as draw_window, \
                patch.object(self.cmd_menu, 'draw_window_cursor') as cursor:
            chosen = self.cmd_menu.display_item_menu(menu_name)
        return chosen, draw_text, draw_window, cursor

    def shown(self, draw_text):
        """The first halves of the names drawn the last time the window was drawn (each draw starts at row 1)."""
        rows = [(call.args[0], call.args[2]) for call in draw_text.call_args_list
                if call.args[1] == 20 * self.nes_tile]
        last_start = max(index for index, (_, y) in enumerate(rows) if y == rows[0][1])
        return [text for text, _ in rows[last_start:]]

    def test_up_to_18_entries_scroll(self):
        self.player.inventory = ['Herb', 'Magic Key'] + list(SIXTEEN)
        chosen, draw_text, draw_window, cursor = self.open_item_menu('discard', [K_DOWN] * 17 + [K_RETURN])
        self.assertEqual("Dragon's Scale", chosen)
        self.assertEqual((9, 3, 6, ITEM_MENU_MAX_ENTRIES + 1), draw_window.call_args.args[1].window)
        # the last ten entries shown, the cursor on the last row
        self.assertEqual(ITEM_MENU_MAX_ENTRIES, len(self.shown(draw_text)))
        self.assertEqual(1 + 2 * (ITEM_MENU_MAX_ENTRIES - 1), cursor.call_args.args[3])

    def test_scrolls_back_up(self):
        self.player.inventory = list(SIXTEEN)
        chosen, draw_text, _, cursor = self.open_item_menu('discard', [K_DOWN] * 15 + [K_UP] * 15 + [K_RETURN])
        self.assertEqual('Torch', chosen)
        self.assertEqual(['Torch', 'Fairy', 'Wings', "Dragon's"] * 2 + ['Torch', 'Fairy'], self.shown(draw_text))
        self.assertEqual(1, cursor.call_args.args[3])

    def test_the_nes_window_never_scrolls(self):
        self.player.inventory = ['Herb', 'Magic Key'] + ['Torch'] * 8
        chosen, _, draw_window, _ = self.open_item_menu('discard', [K_DOWN] * 9 + [K_ESCAPE])
        self.assertIsNone(chosen)
        self.assertEqual((9, 3, 6, 11), draw_window.call_args.args[1].window)

    def test_the_sell_window_scrolls_too(self):
        self.player.inventory = list(SIXTEEN)
        events = [[MagicMock(type=KEYDOWN, key=key)] for key in [K_DOWN] * 12 + [K_RETURN]]
        with patch('src.selection.event.get', side_effect=events), patch('src.menu.draw_text'), \
                patch('src.menu.draw_window'), patch.object(self.cmd_menu, 'window_drop_down_effect'), \
                patch.object(self.cmd_menu, 'draw_window_cursor') as cursor:
            index = self.dialog_lookup.select_from_inventory(list(SIXTEEN))
        self.assertEqual(12, index)
        self.assertEqual(1 + 2 * (ITEM_MENU_MAX_ENTRIES - 1), cursor.call_args.args[3])
