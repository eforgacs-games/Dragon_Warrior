from unittest import TestCase

from src.items import treasure
from src.maps import Rimuldar
from tests.town_dialog import TownDialogMixin

# Bank02 text for the dialog bytes between $16 and $5D (TextBlock entry = byte + $2F)
RIMULDAR_TEXT = {
    0x30: "Art thou the descendant of Erdrick?\nHast thou any proof?",
    0x4F: "Welcome!",
    0x50: "Who art thou?\nLeave at once or I will call my friends.",
    0x51: "I am Orwick, and I am waiting for my girl friend.",
    0x52: "The scales of the Dragonlord are as hard as steel.",
    0x53: ("Over the western part of this island Erdrick created a rainbow.",
           "ʼTis also said that he entered the darkness from a hidden entrance in the room of the Dragonlord."),
    0x54: "Thou shalt find the Stones of Sunlight in Tantegel Castle,\nif thou has not found them yet.",
    0x55: "Welcome to the town of Rimuldar.",
    0x56: "No, I have no tomatoes.\nI have no tomatoes today.",
    0x58: "Good day,I am Howard. Four steps south of the bath in Kol thou shalt find a magic item.",
    0x59: "Before long the enemy will arrive.",
    0x5A: "Heed my warning! Travel not to the south for there the monsters are fierce and terrible.",
    0x5B: "In this world is there any sword that can pierce the scales of the Dragonlord?",
    0x5C: "Orwick is late again. I'm starving.",
}


class TestRimuldarDialog(TownDialogMixin, TestCase):
    map_class = Rimuldar
    text = RIMULDAR_TEXT

    def test_hero_name_fighter(self):
        # $57, TextBlock9 entry 6 has the hero's name in it
        self.assertEqual(self.dialog_at(24, 19),
                         f"You are {self.game.player.name}?\nIt has been long since last we met.")

    def test_shops(self):
        shops = self.dialog_lookup.shop_inventories
        expected = {
            (16, 18): ('check_stay_at_inn', 55),
            (23, 7): ('check_buy_weapons_armor', shops.rimuldar_weapons_store_inventory),
            (4, 7): ('check_buy_magic_keys', 53),
        }
        for (x, y), (function_name, argument) in expected.items():
            entry, = self.dialog_at(x, y)
            self.assertEqual(entry.func.__name__, function_name, f'NES {x},{y}')
            self.assertEqual(entry.args[0], argument, f'NES {x},{y}')

    def test_weapons_shop_matches_shop_items_tbl(self):
        # NES ShopItemsTbl, Rimuldar row: $02, $03, $04, $0A, $0B, $0C (ItemCostTbl)
        inventory = self.dialog_lookup.shop_inventories.rimuldar_weapons_store_inventory
        self.assertEqual({name: item['cost'] for name, item in inventory.items()},
                         {'Copper Sword': 180, 'Hand Axe': 560, 'Broad Sword': 1500, 'Half Plate': 1000,
                          'Full Plate': 3000, 'Magic Armor': 7700})

    def test_wings_chest(self):
        # The Wings chest at NES 24,23 is untouched, and no NPC stands on it
        self.assertEqual(treasure['Rimuldar'], {self.nes_to_map(24, 23): {'item': 'Wings'}})
        self.assertNotIn(self.nes_to_map(24, 23), self.town.npc_coordinates)

    def test_magic_temple_wizard(self):
        first_line, prompt = self.dialog_at(3, 23)
        self.assertEqual(first_line, "This is a magic place.")
        self.assertEqual(prompt, self.dialog_lookup.rimuldar_hast_thou_found_a_magic_temple)

    def test_magic_temple_wizard_yes(self):
        self.answers = [True]
        self.dialog_lookup.rimuldar_hast_thou_found_a_magic_temple()
        self.assertEqual(self.prompts, ["Hast thou found a magic temple?"])
        self.assertEqual(self.lines, ["In this temple do the sun and rain meet."])

    def test_magic_temple_wizard_no(self):
        self.answers = [False]
        self.dialog_lookup.rimuldar_hast_thou_found_a_magic_temple()
        self.assertEqual(self.prompts, ["Hast thou found a magic temple?"])
        self.assertEqual(self.lines, ["Go to the south."])

    def test_fighters_ring_fighter_without_ring(self):
        self.assertEqual(self.dialog_at(16, 26), (self.dialog_lookup.rimuldar_fighters_ring_dialog,))
        self.dialog_lookup.rimuldar_fighters_ring_dialog()
        self.assertEqual(self.lines, ["All true warriors wear a ring."])

    def test_fighters_ring_fighter_ring_carried_but_not_worn(self):
        self.game.player.inventory.append("Fighter's Ring")
        self.dialog_lookup.rimuldar_fighters_ring_dialog()
        self.assertEqual(self.lines, ["All true warriors wear a ring."])

    def test_fighters_ring_fighter_wearing_ring(self):
        self.game.player.inventory.append("Fighter's Ring")
        self.game.player.wearing_fighters_ring = True
        self.dialog_lookup.rimuldar_fighters_ring_dialog()
        self.assertEqual(self.lines, ["Is that a wedding ring?’\n`Thou seems too young to be married."])
        self.assertTrue(self.game.player.wearing_fighters_ring)

    def test_fighters_ring_flag_cleared_when_ring_gone(self):
        # NES ChkRingDialog clears the worn flag when the ring is no longer in the inventory
        self.game.player.wearing_fighters_ring = True
        self.dialog_lookup.rimuldar_fighters_ring_dialog()
        self.assertEqual(self.lines, ["All true warriors wear a ring."])
        self.assertFalse(self.game.player.wearing_fighters_ring)
