from unittest import TestCase

from src.maps import Garinham
from tests.town_dialog import TownDialogMixin

# Bank02 text for the dialog bytes between $16 and $5D (TextBlock entry = byte + $2F)
GARINHAM_TEXT = {
    0x3A: "The harp attracts enemies.\nStay away from the grave in Garinham.",
    0x3B: "I'm too busy.\nAsk the other guard.",
    0x3C: "I suggest making a map if thy path leads into the darkness.",
    0x3D: "Once there was a town called Hauksness far to the south,but I do not know if it still exists.",
    0x3E: "I hate people!\nGo! Leave me!",
    0x3F: "They say that Erdrick's armor was hidden long ago.",
    0x40: "Many believe that Princess Gwaelin is hidden away in a cave.",
    0x41: "I have heard of one named Nester.\nDost thou know such a one?",
    0x42: "Garin, a wandering minstrel of legendary fame, is said to have built this town.",
    0x43: "Welcome to Garinham.\nMay thy stay be a peaceful one.",
    0x44: "It is said that the Princess was kidnapped and taken eastward.",
}


class TestGarinhamDialog(TownDialogMixin, TestCase):
    map_class = Garinham
    text = GARINHAM_TEXT

    def test_shops(self):
        shops = self.dialog_lookup.shop_inventories
        expected = {
            (17, 15): ('check_stay_at_inn', 25),
            (10, 18): ('check_buy_weapons_armor', shops.garinham_weapons_store_inventory),
            (5, 11): ('tool_shop', shops.garinham_item_store_inventory),
        }
        for (x, y), (function_name, argument) in expected.items():
            entry, = self.dialog_at(x, y)
            self.assertEqual(entry.func.__name__, function_name, f'NES {x},{y}')
            self.assertEqual(entry.args[0], argument, f'NES {x},{y}')

    def test_garins_grave_stairs(self):
        # NES 19,0 is the staircase down into Garin's Grave
        self.assertEqual(self.town.staircases[self.nes_to_map(19, 0)]['map'], 'GarinsGraveB1')
