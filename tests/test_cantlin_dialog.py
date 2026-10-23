from unittest import TestCase

from src.maps import Cantlin
from tests.town_dialog import TownDialogMixin

# Bank02 text for the dialog bytes between $16 and $5D (TextBlock entry = byte + $2F)
CANTLIN_TEXT = {
    0x45: "Come buy my radishes! They are fresh and cheap.\nBuy thy radishes today!",
    0x46: "To learn how proof may be obtained that thy ancestor was the great Erdrick, see a man in this very town.",
    0x47: "'Tis said that Erdrick's sword could cleave steel.",
    0x48: "Welcome to Cantlin, the castle town.",
    0x49: "What shall I get for thy dinner?",
    0x4A: "I know nothing.",
    0x4B: "I'm Nester.\nHey, where am I? No, don't tell me!",
    0x4C: "Grandfather used to say that his friend, Wynn, had buried something of great value at the foot of a tree "
          "behind his shop.",
    0x4D: ("It is said that many have held Erdrick's armor.", "The last to have it was a fellow named Wynn."),
    0x4E: "My Grandfather Wynn once had a shop on the east side of Hauksness.",
}


class TestCantlinDialog(TownDialogMixin, TestCase):
    map_class = Cantlin
    text = CANTLIN_TEXT

    def test_shops(self):
        shops = self.dialog_lookup.shop_inventories
        expected = {
            (8, 3): ('check_stay_at_inn', 100),
            (22, 5): ('check_buy_weapons_armor', shops.cantlin_weapons_store_north_inventory),
            (27, 26): ('check_buy_weapons_armor', shops.cantlin_weapons_store_south_inventory),
            (24, 12): ('check_buy_weapons_armor', shops.cantlin_weapons_store_3_inventory),
            (2, 7): ('tool_shop', shops.cantlin_item_store_1_inventory),
            (7, 12): ('tool_shop', shops.cantlin_item_store_2_inventory),
            (27, 6): ('check_buy_magic_keys', 98),
        }
        for (x, y), (function_name, argument) in expected.items():
            entry, = self.dialog_at(x, y)
            self.assertEqual(entry.func.__name__, function_name, f'NES {x},{y}')
            self.assertEqual(entry.args[0], argument, f'NES {x},{y}')
        self.assertEqual(self.dialog_at(22, 13), (self.dialog_lookup.fairy_water_shop,))

    def test_erdricks_token_hint(self):
        # NES ErdTknDialog ($6B): TextBlock5 entry 12, then TextBlock11 entries 14 and 15
        self.assertEqual(self.dialog_at(14, 28), (
            "Let us wish the warrior well!",
            "May the light be thy strength!",
            "Thou may go and search.",
            "From Tantegel Castle travel 70 leagues to the south and 40 to the east.",
        ))

    def test_dragonlord_claws_guard(self):
        first_line, prompt = self.dialog_at(5, 6)
        self.assertEqual(first_line, "'Tis said that the Dragonlord hath claws that can cleave iron and fiery breath "
                                     "that can melt stone.")
        self.assertEqual(prompt, self.dialog_lookup.cantlin_still_wish_to_go_on)

    def test_dragonlord_claws_guard_yes(self):
        self.answers = [True]
        self.dialog_lookup.cantlin_still_wish_to_go_on()
        self.assertEqual(self.prompts, ["Dost thou still wish to go on?"])
        self.assertEqual(self.lines, ["Thou art truly brave."])

    def test_dragonlord_claws_guard_no(self):
        self.answers = [False]
        self.dialog_lookup.cantlin_still_wish_to_go_on()
        self.assertEqual(self.prompts, ["Dost thou still wish to go on?"])
        self.assertEqual(self.lines, ["That is good.’\n`No one will say thou art afraid."])
