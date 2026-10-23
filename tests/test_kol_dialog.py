from unittest import TestCase

from src.items import hidden_items
from src.maps import Kol
from tests.town_dialog import TownDialogMixin

# Bank02 text for the dialog bytes between $16 and $5D (TextBlock entry = byte + $2F)
KOL_TEXT = {
    0x2E: "Please,save us from the minions of the Dragonlord.",
    0x30: "Art thou the descendant of Erdrick?\nHast thou any proof?",
    0x32: "This bath cures rheumatism.",
    0x33: "East of Hauksness there is a town, ʼtis said, where one may purchase weapons of extraordinary quality.",
    0x34: "Rimuldar is the place to buy keys.",
    0x35: "Hast thou seen Nester?\nI think he may need help.",
    0x36: ("Dreadful is the South Island.",
           "Great strength and skill and wit only will bring thee back from that place."),
    0x37: "Golem is afraid of the music of the flute, so ʼtis said.",
    0x38: "This is the village of Kol.",
    0x39: "In legends it is said that fairies know how to put Golem to sleep.",
}


class TestKolDialog(TownDialogMixin, TestCase):
    map_class = Kol
    text = KOL_TEXT

    def test_shops(self):
        shops = self.dialog_lookup.shop_inventories
        expected = {
            (19, 4): ('check_stay_at_inn', 20),
            (22, 12): ('check_buy_weapons_armor', shops.kol_weapons_store_inventory),
            (14, 21): ('tool_shop', shops.kol_item_store_inventory),
        }
        for (x, y), (function_name, argument) in expected.items():
            entry, = self.dialog_at(x, y)
            self.assertEqual(entry.func.__name__, function_name, f'NES {x},{y}')
            self.assertEqual(entry.args[0], argument, f'NES {x},{y}')

    def test_erdricks_sword_wizard_without_the_sword(self):
        self.assertEqual(self.dialog_at(1, 1), (self.dialog_lookup.kol_erdricks_sword_wizard,))
        self.game.player.weapon = "Copper Sword"
        self.dialog_lookup.kol_erdricks_sword_wizard()
        self.assertEqual(self.lines, [
            f"Though thou art as brave as thy ancestor, {self.game.player.name}, thou cannot defeat the great "
            "Dragonlord with such weapons.",
            "Thou shouldst come here again.",
        ])

    def test_erdricks_sword_wizard_with_the_sword(self):
        self.game.player.weapon = "Erdrick's Sword"
        self.dialog_lookup.kol_erdricks_sword_wizard()
        self.assertEqual(self.lines, [f"Finally thou hast obtained it, {self.game.player.name}."])

    def test_flute_wizard(self):
        self.assertEqual(self.dialog_at(2, 12), (self.dialog_lookup.kol_hast_thou_found_the_flute,))
        for answer, line in ((True, "Go to the town of Cantlin."),
                             (False, "Howard had it, but he went to Rimuldar and never returned.")):
            self.prompts, self.lines, self.answers = [], [], [answer]
            self.dialog_lookup.kol_hast_thou_found_the_flute()
            self.assertEqual(self.prompts, ["Hast thou found the flute?"])
            self.assertEqual(self.lines, [line])

    def test_southern_island_shopkeeper(self):
        self.assertEqual(self.dialog_at(7, 19), (self.dialog_lookup.kol_hast_thou_been_to_the_southern_island,))
        for answer, line in ((True, "I have heard that powerful enemies live there."),
                             (False, "To the south, I believe, there is a town called Rimuldar.")):
            self.prompts, self.lines, self.answers = [], [], [answer]
            self.dialog_lookup.kol_hast_thou_been_to_the_southern_island()
            self.assertEqual(self.prompts, ["Hast thou been to the southern island?"])
            self.assertEqual(self.lines, [line])

    def test_fairy_flute_tile_is_free(self):
        # The Fairy Flute is hidden at NES 9,6; no NPC stands on it
        flute = next(coordinates for coordinates, item in hidden_items['Kol'].items() if item == 'Fairy Flute')
        self.assertEqual(flute, self.nes_to_map(9, 6))
        self.assertNotIn(flute, self.town.npc_coordinates)
