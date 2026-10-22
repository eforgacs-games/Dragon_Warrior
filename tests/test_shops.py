import os
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from src.config.test_config import test_config
from src.items import armor, inventory_list, shields, tools, weapons
from src.shops import INVENTORY_SLOTS, MAX_GOLD, ShopInventories, buyback_price, inventory_is_full, \
    inventory_slots_used, pay_player, sell_price

VALID_ITEM_TYPES = {'weapon', 'armor', 'shield'}
EXPECTED_KEYS = {'cost', 'type', 'menu_image'}


class TestShopInventories(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.shops = ShopInventories(test_config)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def _all_inventories(self):
        return [
            self.shops.brecconary_weapons_store_inventory,
            self.shops.rimuldar_weapons_store_inventory,
            self.shops.garinham_weapons_store_inventory,
            self.shops.kol_weapons_store_inventory,
            self.shops.cantlin_weapons_store_north_inventory,
            self.shops.cantlin_weapons_store_south_inventory,
        ]

    def _item_inventories(self):
        return [
            self.shops.kol_item_store_inventory,
            self.shops.brecconary_item_store_inventory,
            self.shops.garinham_item_store_inventory,
            self.shops.cantlin_item_store_1_inventory,
            self.shops.cantlin_item_store_2_inventory,
        ]

    def test_stock_matches_nes_shop_items_tbl(self):
        # NES ShopItemsTbl (Bank00), in table order
        expected = {
            'kol_weapons_store_inventory': ["Copper Sword", "Hand Axe", "Half Plate", "Full Plate", "Small Shield"],
            'brecconary_weapons_store_inventory': ["Bamboo Pole", "Club", "Copper Sword", "Clothes", "Leather Armor",
                                                   "Small Shield"],
            'garinham_weapons_store_inventory': ["Club", "Copper Sword", "Hand Axe", "Leather Armor", "Chain Mail",
                                                 "Half Plate", "Large Shield"],
            'cantlin_weapons_store_north_inventory': ["Bamboo Pole", "Club", "Copper Sword", "Leather Armor",
                                                      "Chain Mail", "Large Shield"],
            'cantlin_weapons_store_south_inventory': ["Hand Axe", "Broad Sword", "Full Plate", "Magic Armor"],
            'cantlin_weapons_store_3_inventory': ["Flame Sword", "Silver Shield"],
            'rimuldar_weapons_store_inventory': ["Copper Sword", "Hand Axe", "Broad Sword", "Half Plate",
                                                 "Full Plate", "Magic Armor"],
            'kol_item_store_inventory': ["Herb", "Torch", "Dragon's Scale", "Wings"],
            'brecconary_item_store_inventory': ["Herb", "Torch", "Dragon's Scale"],
            'garinham_item_store_inventory': ["Herb", "Torch", "Dragon's Scale"],
            'cantlin_item_store_1_inventory': ["Herb", "Torch"],
            'cantlin_item_store_2_inventory': ["Dragon's Scale", "Wings"],
        }
        for attribute, items in expected.items():
            with self.subTest(shop=attribute):
                self.assertEqual(list(getattr(self.shops, attribute)), items)

    def test_tool_prices_match_nes_item_cost_tbl(self):
        expected = {"Herb": 24, "Torch": 8, "Wings": 70, "Dragon's Scale": 20}
        for inventory in self._item_inventories():
            for item_name, item_data in inventory.items():
                with self.subTest(item=item_name):
                    self.assertEqual(item_data['cost'], expected[item_name])
                    self.assertEqual(item_data['type'], 'tool')
                    self.assertEqual(item_data['cost'], tools[item_name]['cost'])

    def test_cantlin_shop_3_prices(self):
        self.assertEqual(self.shops.cantlin_weapons_store_3_inventory,
                         {"Flame Sword": {'cost': 9800, 'type': 'weapon'},
                          "Silver Shield": {'cost': 14_800, 'type': 'shield'}})

    def test_instantiates_with_config(self):
        shops = ShopInventories(test_config)
        self.assertIsNotNone(shops)

    def test_all_inventories_have_expected_keys(self):
        for inventory in self._all_inventories():
            for item_name, item_data in inventory.items():
                with self.subTest(item=item_name):
                    self.assertEqual(set(item_data.keys()), EXPECTED_KEYS)

    def test_item_types_are_valid(self):
        for inventory in self._all_inventories():
            for item_name, item_data in inventory.items():
                with self.subTest(item=item_name):
                    self.assertIn(item_data['type'], VALID_ITEM_TYPES)

    def test_item_types_and_costs_match_equipment_tables(self):
        tables = {'weapon': weapons, 'armor': armor, 'shield': shields}
        for inventory in self._all_inventories():
            for item_name, item_data in inventory.items():
                with self.subTest(item=item_name):
                    table = tables[item_data['type']]
                    self.assertIn(item_name, table)
                    self.assertEqual(item_data['cost'], table[item_name]['cost'])

    def test_costs_are_positive_integers(self):
        for inventory in self._all_inventories():
            for item_name, item_data in inventory.items():
                with self.subTest(item=item_name):
                    self.assertIsInstance(item_data['cost'], int)
                    self.assertGreater(item_data['cost'], 0)

    def test_menu_image_paths_are_strings(self):
        for inventory in self._all_inventories():
            for item_name, item_data in inventory.items():
                with self.subTest(item=item_name):
                    self.assertIsInstance(item_data['menu_image'], str)

    # --- Specific item assertions ---

    def test_bamboo_pole_cost_and_type(self):
        item = self.shops.brecconary_weapons_store_inventory['Bamboo Pole']
        self.assertEqual(item['cost'], 10)
        self.assertEqual(item['type'], 'weapon')

    def test_club_is_weapon(self):
        item = self.shops.brecconary_weapons_store_inventory['Club']
        self.assertEqual(item['cost'], 60)
        self.assertEqual(item['type'], 'weapon')

    def test_copper_sword_cost(self):
        item = self.shops.brecconary_weapons_store_inventory['Copper Sword']
        self.assertEqual(item['cost'], 180)
        self.assertEqual(item['type'], 'weapon')

    def test_clothes_is_armor(self):
        item = self.shops.brecconary_weapons_store_inventory['Clothes']
        self.assertEqual(item['cost'], 20)
        self.assertEqual(item['type'], 'armor')

    def test_small_shield_is_shield(self):
        item = self.shops.brecconary_weapons_store_inventory['Small Shield']
        self.assertEqual(item['cost'], 90)
        self.assertEqual(item['type'], 'shield')

    def test_broad_sword_in_rimuldar(self):
        item = self.shops.rimuldar_weapons_store_inventory['Broad Sword']
        self.assertEqual(item['cost'], 1500)
        self.assertEqual(item['type'], 'weapon')

    def test_magic_armor_is_armor_type(self):
        # Buying it as a 'shield' used to replace the player's shield instead of their armor
        for inventory in (self.shops.rimuldar_weapons_store_inventory,
                          self.shops.cantlin_weapons_store_south_inventory):
            item = inventory['Magic Armor']
            self.assertEqual(item['cost'], 7700)
            self.assertEqual(item['type'], 'armor')

    def test_large_shield_in_garinham(self):
        item = self.shops.garinham_weapons_store_inventory['Large Shield']
        self.assertEqual(item['cost'], 800)
        self.assertEqual(item['type'], 'shield')

    def test_brecconary_inventory_not_empty(self):
        self.assertGreater(len(self.shops.brecconary_weapons_store_inventory), 0)

    def test_all_inventories_not_empty(self):
        for inventory in self._all_inventories():
            self.assertGreater(len(inventory), 0)



class TestShopRules(unittest.TestCase):

    def test_herbs_and_keys_take_no_inventory_slot(self):
        inventory = ['Herb'] * 6 + ['Magic Key'] * 6 + ['Torch']
        self.assertEqual(inventory_slots_used(inventory), 1)
        self.assertFalse(inventory_is_full(inventory))

    def test_inventory_holds_eight_items(self):
        # NES AddInvItem: 4 bytes of two items each; duplicates each take a slot
        self.assertEqual(INVENTORY_SLOTS, 8)
        self.assertFalse(inventory_is_full(['Torch'] * 7))
        self.assertTrue(inventory_is_full(['Torch'] * 7 + ["Dragon's Scale"]))

    def test_sell_price_is_half_rounded_down(self):
        self.assertEqual(sell_price('Herb'), 12)
        self.assertEqual(sell_price('Magic Key'), 26)
        self.assertEqual(sell_price('Torch'), 4)
        self.assertEqual(sell_price('Fairy Water'), 19)
        self.assertEqual(sell_price('Wings'), 35)
        self.assertEqual(sell_price("Dragon's Scale"), 10)
        self.assertEqual(sell_price("Fighter's Ring"), 15)
        self.assertEqual(sell_price('Cursed Belt'), 180)
        self.assertEqual(sell_price('Death Necklace'), 1200)

    def test_quest_items_cannot_be_sold(self):
        for item in ('Fairy Flute', "Erdrick's Token", "Gwaelin's Love", 'Silver Harp', 'Stones of Sunlight',
                     'Staff of Rain', 'Rainbow Drop'):
            with self.subTest(item=item):
                self.assertEqual(sell_price(item), 0)

    def test_buyback_price(self):
        self.assertEqual(buyback_price('Copper Sword', 'weapon'), 90)
        self.assertEqual(buyback_price('Magic Armor', 'armor'), 3850)
        self.assertEqual(buyback_price('Small Shield', 'shield'), 45)
        # NES ItemCostTbl: Erdrick's equipment costs 2, so it's bought back for 1
        self.assertEqual(buyback_price("Erdrick's Sword", 'weapon'), 1)
        self.assertEqual(buyback_price('', 'weapon'), 0)

    def test_gold_is_capped_when_paid(self):
        self.assertEqual(MAX_GOLD, 65535)
        self.assertEqual(pay_player(65000, 1200), 65535)
        self.assertEqual(pay_player(100, 12), 112)

    def test_inventory_list_puts_herbs_and_keys_first_once(self):
        inventory = ['Torch', 'Herb', 'Magic Key', 'Herb', 'Torch', 'Wings']
        self.assertEqual(inventory_list(inventory), ['Herb', 'Magic Key', 'Torch', 'Torch', 'Wings'])
        self.assertEqual(inventory_list([]), [])


if __name__ == '__main__':
    unittest.main()
