from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import KEYDOWN, K_DOWN, K_RETURN, K_ESCAPE

from src.config.test_config import test_config
from src.maps import Brecconary, Cantlin, Garinham, Kol, Rimuldar
from src.shops import KEY_COSTS
from src.windows import BUY_SELL_WINDOW
from tests.helpers import new_game


def npc_identifiers(game_map):
    """The identifiers load_map gives each NPC: the second MERCHANT is MERCHANT_2, and so on."""
    counts = {}
    identifiers = {}
    for coordinates, name in game_map.npc_coordinates.items():
        counts[name] = counts.get(name, 0) + 1
        identifiers[coordinates] = name if counts[name] == 1 else f'{name}_{counts[name]}'
    return identifiers


class ShopDialogTestCase(TestCase):
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
        self.dialog_lookup = self.game.cmd_menu.dialog_lookup
        self.player = self.dialog_lookup.player
        self.player.gold = 1000
        self.player.inventory = []
        self.lines = []
        self.prompts = []
        self.answers = []
        self.dialog_lookup.command_menu.show_line_in_dialog_box = lambda line, **kwargs: self.lines.append(line)
        self.dialog_lookup.command_menu.window_drop_down_effect = lambda *args: None
        confirmation_patch = patch('data.text.dialog_lookup_table.confirmation_prompt', side_effect=self.answer)
        confirmation_patch.start()
        self.addCleanup(confirmation_patch.stop)

    def answer(self, command_menu, prompt, yes_path_function, no_path_function, **kwargs):
        self.prompts.append(prompt)
        (yes_path_function if self.answers.pop(0) else no_path_function)()

    def run_shop(self, function, answers, menu_choices):
        """Run a shop dialog, answering the yes/no windows with answers and the list windows with menu_choices."""
        self.answers = list(answers)
        with patch.object(self.dialog_lookup, 'select_in_window', side_effect=list(menu_choices)):
            function()
        self.assertEqual(self.answers, [], 'not every scripted answer was used')

    def store(self, name):
        return getattr(self.dialog_lookup.shop_inventories, name)


class TestToolShop(ShopDialogTestCase):

    def test_buy_herb(self):
        shop = self.store('brecconary_item_store_inventory')
        # BUY, then Herb; no to "anything else?"
        self.run_shop(lambda: self.dialog_lookup.tool_shop(shop), [False], [0, 0])
        self.assertEqual(self.player.inventory, ['Herb'])
        self.assertEqual(self.player.gold, 1000 - 24)
        self.assertIn("The Herb?\nThank you very much.", self.lines)
        self.assertEqual(self.prompts, ["Dost thou want anything else?"])
        self.assertEqual(self.lines[-1], "I will be waiting for thy next visit.")

    def test_cannot_hold_more_than_six_herbs(self):
        self.player.inventory = ['Herb'] * 6
        shop = self.store('brecconary_item_store_inventory')
        self.run_shop(lambda: self.dialog_lookup.tool_shop(shop), [False], [0, 0])
        self.assertEqual(self.player.inventory.count('Herb'), 6)
        self.assertEqual(self.player.gold, 1000)
        self.assertIn("Thou cannot hold more Herbs.", self.lines)

    def test_herbs_can_be_bought_with_a_full_inventory(self):
        self.player.inventory = ['Torch'] * 8
        shop = self.store('brecconary_item_store_inventory')
        self.run_shop(lambda: self.dialog_lookup.tool_shop(shop), [False], [0, 0])
        self.assertEqual(self.player.inventory.count('Herb'), 1)

    def test_cannot_carry_more_than_eight_items(self):
        self.player.inventory = ['Torch'] * 8 + ['Herb', 'Magic Key']
        shop = self.store('kol_item_store_inventory')
        self.run_shop(lambda: self.dialog_lookup.tool_shop(shop), [False], [0, 3])
        self.assertNotIn('Wings', self.player.inventory)
        self.assertEqual(self.player.gold, 1000)
        self.assertIn("Thou cannot carry anymore.", self.lines)

    def test_a_second_dragons_scale_can_be_bought(self):
        self.player.inventory = ["Dragon's Scale"]
        self.player.wearing_dragon_scale = True
        shop = self.store('garinham_item_store_inventory')
        self.run_shop(lambda: self.dialog_lookup.tool_shop(shop), [False], [0, 2])
        self.assertEqual(self.player.inventory.count("Dragon's Scale"), 2)
        self.assertEqual(self.player.gold, 1000 - 20)

    def test_not_enough_money(self):
        self.player.gold = 69
        shop = self.store('kol_item_store_inventory')
        self.run_shop(lambda: self.dialog_lookup.tool_shop(shop), [False], [0, 3])
        self.assertEqual(self.player.inventory, [])
        self.assertEqual(self.player.gold, 69)
        self.assertIn("Thou hast not enough money.", self.lines)

    def test_buy_several_in_a_row(self):
        shop = self.store('cantlin_item_store_1_inventory')
        self.run_shop(lambda: self.dialog_lookup.tool_shop(shop), [True, False], [0, 1, 1])
        self.assertEqual(self.player.inventory, ['Torch', 'Torch'])
        self.assertEqual(self.player.gold, 1000 - 16)

    def test_cancel_buy_sell_window(self):
        shop = self.store('cantlin_item_store_2_inventory')
        self.run_shop(lambda: self.dialog_lookup.tool_shop(shop), [], [None])
        self.assertEqual(self.lines[-1], "I will be waiting for thy next visit.")


class TestSelling(ShopDialogTestCase):

    def sell(self, answers, menu_choices):
        shop = self.store('brecconary_item_store_inventory')
        # menu_choices[0] = 1 picks SELL in the BUY/SELL window
        self.run_shop(lambda: self.dialog_lookup.tool_shop(shop), answers, [1] + list(menu_choices))

    def test_sell_for_half_price(self):
        self.player.inventory = ['Wings', 'Torch']
        self.sell([True, False], [0])
        self.assertEqual(self.player.inventory, ['Torch'])
        self.assertEqual(self.player.gold, 1000 + 35)
        self.assertEqual(self.prompts[0], "Thou said the Wings.\nI will buy thy Wings for 35 GOLD.\nIs that all right?")
        self.assertEqual(self.prompts[1], "Wilt thou sell anything else?")

    def test_herbs_and_keys_are_listed_first(self):
        self.player.inventory = ['Torch', 'Magic Key', 'Herb', 'Herb']
        # the sell list is Herb, Magic Key, Torch
        self.sell([True, False], [1])
        self.assertEqual(self.player.inventory, ['Torch', 'Herb', 'Herb'])
        self.assertEqual(self.player.gold, 1000 + 26)

    def test_selling_one_herb_keeps_the_rest(self):
        self.player.inventory = ['Herb', 'Herb', 'Herb']
        self.sell([True, False], [0])
        self.assertEqual(self.player.inventory, ['Herb', 'Herb'])
        self.assertEqual(self.player.gold, 1000 + 12)

    def test_declining_the_offer_keeps_the_item(self):
        self.player.inventory = ['Torch']
        self.sell([False, False], [0])
        self.assertEqual(self.player.inventory, ['Torch'])
        self.assertEqual(self.player.gold, 1000)

    def test_quest_items_cannot_be_sold(self):
        self.player.inventory = ['Silver Harp']
        self.sell([False], [0])
        self.assertEqual(self.player.inventory, ['Silver Harp'])
        self.assertIn("I cannot buy it.", self.lines)

    def test_worn_cursed_belt_cannot_be_sold(self):
        self.player.inventory = ['Cursed Belt']
        # stands in for Player.is_wearing_cursed_item from PR #199
        self.player.is_wearing_cursed_item = lambda item: item == 'Cursed Belt'
        self.sell([True, False], [0])
        self.assertEqual(self.player.inventory, ['Cursed Belt'])
        self.assertEqual(self.player.gold, 1000)
        self.assertIn("A curse is upon thy body.", self.lines)

    def test_unworn_death_necklace_can_be_sold(self):
        self.player.inventory = ['Death Necklace']
        self.sell([True, False], [0])
        self.assertEqual(self.player.inventory, [])
        self.assertEqual(self.player.gold, 1000 + 1200)

    def test_sale_caps_gold(self):
        self.player.gold = 65000
        self.player.inventory = ['Death Necklace']
        self.sell([True, False], [0])
        self.assertEqual(self.player.gold, 65535)

    def test_no_possessions(self):
        self.sell([], [])
        self.assertEqual(self.lines[-2:], ["Thou hast no possessions.", "I will be waiting for thy next visit."])

    def test_sell_more_loops_back(self):
        self.player.inventory = ['Torch', 'Wings']
        self.sell([True, True, True, False], [0, 0])
        self.assertEqual(self.player.inventory, [])
        self.assertEqual(self.player.gold, 1000 + 4 + 35)


class TestWeaponShop(ShopDialogTestCase):

    def buy(self, store_name, item, answers):
        shop = self.store(store_name)
        self.answers = list(answers)
        with patch.object(self.dialog_lookup, 'open_store_inventory', side_effect=[item]):
            self.dialog_lookup.check_buy_weapons_armor(shop)
        self.assertEqual(self.answers, [])

    def test_buyback_of_equipped_weapon(self):
        self.player.weapon = 'Club'
        self.player.gold = 200
        # yes to "buy anything today?", yes to "Is that Okay.?", no to "anything more?"
        self.buy('brecconary_weapons_store_inventory', 'Copper Sword', [True, True, False])
        self.assertEqual(self.player.weapon, 'Copper Sword')
        self.assertEqual(self.player.gold, 200 - 180 + 30)
        self.assertIn("Then I will buy thy Club for 30 GOLD.", self.lines)

    def test_no_buyback_without_equipment(self):
        self.player.shield = ''
        self.buy('kol_weapons_store_inventory', 'Small Shield', [True, True, False])
        self.assertEqual(self.player.shield, 'Small Shield')
        self.assertEqual(self.player.gold, 1000 - 90)
        self.assertFalse(any(line.startswith("Then I will buy") for line in self.lines))

    def test_buyback_does_not_count_toward_the_price(self):
        # NES CheckBuyWeapon compares only the new item's price with the player's gold
        self.player.armor = 'Full Plate'
        self.player.gold = 7699
        self.buy('rimuldar_weapons_store_inventory', 'Magic Armor', [True, False])
        self.assertEqual(self.player.armor, 'Full Plate')
        self.assertIn("Sorry.\nThou hast not enough money.", self.lines)

    def test_declining_keeps_old_equipment(self):
        self.player.weapon = 'Club'
        self.player.gold = 10_000
        self.buy('cantlin_weapons_store_3_inventory', 'Flame Sword', [True, False, False])
        self.assertEqual(self.player.weapon, 'Club')
        self.assertEqual(self.player.gold, 10_000)
        self.assertIn("Oh, yes? That's too bad.", self.lines)

    def test_flame_sword_shop(self):
        self.player.gold = 10_000
        self.buy('cantlin_weapons_store_3_inventory', 'Flame Sword', [True, True, False])
        self.assertEqual(self.player.weapon, 'Flame Sword')
        self.assertEqual(self.player.gold, 200)


class TestKeyAndFairyWaterShops(ShopDialogTestCase):

    def test_buy_keys_until_six(self):
        self.player.inventory = ['Magic Key'] * 5
        self.answers = [True, True]
        self.dialog_lookup.check_buy_magic_keys(53)
        self.assertEqual(self.player.inventory.count('Magic Key'), 6)
        self.assertEqual(self.player.gold, 1000 - 53)
        self.assertEqual(self.lines[-2:], ["I am sorry, but I cannot sell thee anymore.", "I will see thee later."])
        self.assertEqual(self.prompts[1], "Here, take this key.\nDost thou wish to purchase more?")

    def test_key_not_enough_money(self):
        self.player.gold = 97
        self.answers = [True]
        self.dialog_lookup.check_buy_magic_keys(98)
        self.assertEqual(self.player.inventory, [])
        self.assertEqual(self.lines[-2:], ["Thou hast not enough money.", "I will see thee later."])

    def test_keys_ignore_the_inventory_limit(self):
        self.player.inventory = ['Torch'] * 8
        self.answers = [True, False]
        self.dialog_lookup.check_buy_magic_keys(85)
        self.assertEqual(self.player.inventory.count('Magic Key'), 1)

    def test_buy_fairy_water(self):
        self.answers = [True, True, False]
        self.dialog_lookup.fairy_water_shop()
        self.assertEqual(self.player.inventory, ['Fairy Water', 'Fairy Water'])
        self.assertEqual(self.player.gold, 1000 - 76)
        self.assertEqual(self.prompts[0], "Will thou buy some Fairy Water for 38 GOLD to keep the Dragonlord's "
                                          "minions away?")
        self.assertEqual(self.lines[-1], "All the best to thee.")

    def test_fairy_water_full_inventory(self):
        self.player.inventory = ['Torch'] * 8
        self.answers = [True]
        self.dialog_lookup.fairy_water_shop()
        self.assertEqual(self.player.gold, 1000)
        self.assertEqual(self.lines[-2:], ["Thou cannot carry anymore.", "All the best to thee."])


class TestShopkeeperPlacement(ShopDialogTestCase):
    """Every NES shopkeeper (Bank00 *StatTbl/*MobTbl dialog bytes) runs the right shop."""

    def dialog_entry(self, town, identifier):
        return self.dialog_lookup.lookup_table[town][identifier]['dialog'][0]

    def assert_shop(self, game_map_class, town, coordinates, function_name, argument=None):
        identifier = npc_identifiers(game_map_class(test_config))[coordinates]
        entry = self.dialog_entry(town, identifier)
        self.assertEqual(getattr(entry, 'func', entry).__name__, function_name, f'{town} {identifier}')
        if argument is not None:
            self.assertIs(entry.args[0], argument, f'{town} {identifier}')

    def test_item_shops(self):
        shops = self.dialog_lookup.shop_inventories
        self.assert_shop(Kol, 'Kol', (29, 24), 'tool_shop', shops.kol_item_store_inventory)
        self.assert_shop(Brecconary, 'Brecconary', (33, 35), 'tool_shop', shops.brecconary_item_store_inventory)
        self.assert_shop(Garinham, 'Garinham', (12, 14), 'tool_shop', shops.garinham_item_store_inventory)
        self.assert_shop(Cantlin, 'Cantlin', (15, 3), 'tool_shop', shops.cantlin_item_store_1_inventory)
        self.assert_shop(Cantlin, 'Cantlin', (20, 8), 'tool_shop', shops.cantlin_item_store_2_inventory)

    def test_weapon_shops(self):
        shops = self.dialog_lookup.shop_inventories
        self.assert_shop(Kol, 'Kol', (20, 32), 'check_buy_weapons_armor', shops.kol_weapons_store_inventory)
        self.assert_shop(Rimuldar, 'Rimuldar', (15, 31), 'check_buy_weapons_armor',
                         shops.rimuldar_weapons_store_inventory)
        self.assert_shop(Cantlin, 'Cantlin', (13, 23), 'check_buy_weapons_armor',
                         shops.cantlin_weapons_store_north_inventory)
        self.assert_shop(Cantlin, 'Cantlin', (34, 28), 'check_buy_weapons_armor',
                         shops.cantlin_weapons_store_south_inventory)
        self.assert_shop(Cantlin, 'Cantlin', (20, 25), 'check_buy_weapons_armor',
                         shops.cantlin_weapons_store_3_inventory)

    def test_key_shops(self):
        self.assertEqual(KEY_COSTS, {'Cantlin': 98, 'Rimuldar': 53, 'TantegelCourtyard': 85})
        self.assert_shop(Rimuldar, 'Rimuldar', (15, 12), 'check_buy_magic_keys', 53)
        self.assert_shop(Cantlin, 'Cantlin', (14, 28), 'check_buy_magic_keys', 98)

    def test_fairy_water_shops(self):
        self.assert_shop(Brecconary, 'Brecconary', (12, 34), 'fairy_water_shop')
        self.assert_shop(Cantlin, 'Cantlin', (21, 23), 'fairy_water_shop')


class TestTextMenu(ShopDialogTestCase):

    def test_select_with_keys(self):
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(KEYDOWN, key=K_DOWN, unicode=''))
        pygame.event.post(pygame.event.Event(KEYDOWN, key=K_RETURN, unicode='\r'))
        self.assertEqual(self.dialog_lookup.select_from_text_menu(['BUY', 'SELL'], BUY_SELL_WINDOW), 1)

    def test_cancel(self):
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(KEYDOWN, key=K_ESCAPE, unicode=''))
        self.assertIsNone(self.dialog_lookup.select_shop_item(['Herb', 'Torch'], [24, 8]))

    def test_text_store_returns_item_name(self):
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(KEYDOWN, key=K_DOWN, unicode=''))
        pygame.event.post(pygame.event.Event(KEYDOWN, key=K_RETURN, unicode='\r'))
        shop = self.store('kol_item_store_inventory')
        self.assertEqual(self.dialog_lookup.open_store_inventory(shop), 'Torch')
