import os
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from src.config.test_config import test_config
from src.shops import ShopInventories

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

    def test_magic_armor_is_shield_type(self):
        # Despite its name, Magic Armor is categorised as 'shield' in the data
        item = self.shops.rimuldar_weapons_store_inventory['Magic Armor']
        self.assertEqual(item['cost'], 7700)
        self.assertEqual(item['type'], 'shield')

    def test_large_shield_in_garinham(self):
        item = self.shops.garinham_weapons_store_inventory['Large Shield']
        self.assertEqual(item['cost'], 800)
        self.assertEqual(item['type'], 'shield')

    def test_brecconary_inventory_not_empty(self):
        self.assertGreater(len(self.shops.brecconary_weapons_store_inventory), 0)

    def test_all_inventories_not_empty(self):
        for inventory in self._all_inventories():
            self.assertGreater(len(inventory), 0)


if __name__ == '__main__':
    unittest.main()
