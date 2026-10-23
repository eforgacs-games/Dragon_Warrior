from unittest import TestCase

from src.maps import Brecconary
from tests.town_dialog import TownDialogMixin

# Bank02 text for the dialog bytes between $16 and $5D (TextBlock entry = byte + $2F)
BRECCONARY_TEXT = {
    0x25: ("Beware the bridges!", "Danger grows when thou crosses."),
    0x26: "There is a town where magic keys can be purchased.",
    0x27: "Some say that Garin's grave is home to a Silver Harp.",
    0x28: "Enter where thou can.",
    # The space before the line break isn't in the NES text; the translations are keyed on it
    0x29: "Welcome! \nEnter the shop and speak to its keeper across the desk.",
    0x2A: "Thou art most welcome in Brecconary.",
    0x2B: "Watch thy Hit Points when in the Poisonous Marsh.",
    0x2C: "Go north to the seashore, then follow the coastline west until thou hath reached Garinham.",
    0x2D: "No,I am not Princess Gwaelin.",
    0x2E: "Please,save us from the minions of the Dragonlord.",
    0x2F: "See King Lorik when thy experience levels are raised.",
    0x30: "Art thou the descendant of Erdrick?\nHast thou any proof?",
    0x31: ("Within sight of Tantegel Castle to the south is Charlock,", "The fortress of the Dragonlord."),
    0x5D: ("Many have been the warriors who have perished on this quest.", "But for thee I wish success, {}."),
}


class TestBrecconaryDialog(TownDialogMixin, TestCase):
    map_class = Brecconary
    text = BRECCONARY_TEXT

    def record(self, line, **kwargs):
        if callable(line):
            line()
        else:
            self.lines.append(line)

    def test_story_npcs_keep_their_identifiers(self):
        # The ending, curse and Gwaelin code look these NPCs up by identifier
        self.assertEqual(self.identifiers[self.nes_to_map(10, 26)], 'GUARD')
        self.assertEqual(self.identifiers[self.nes_to_map(24, 10)], 'WISE_MAN')
        self.assertEqual(self.identifiers[self.nes_to_map(5, 4)], 'MERCHANT')
        self.assertEqual(self.identifiers[self.nes_to_map(10, 21)], 'MERCHANT_2')
        self.assertEqual(self.identifiers[self.nes_to_map(24, 4)], 'WOMAN')

    def test_shops(self):
        shops = self.dialog_lookup.shop_inventories
        # ShopItemsTbl rows 1 ($01) and 8 ($08), InnCostTbl entry 1 ($12 - $11)
        expected = {
            (5, 4): ('check_buy_weapons_armor', shops.brecconary_weapons_store_inventory),
            (25, 25): ('tool_shop', shops.brecconary_item_store_inventory),
            (10, 21): ('check_stay_at_inn', 6),
        }
        for (x, y), (function_name, argument) in expected.items():
            entry, = self.dialog_at(x, y)
            self.assertEqual(entry.func.__name__, function_name, f'NES {x},{y}')
            self.assertEqual(entry.args[0], argument, f'NES {x},{y}')
        self.assertEqual(self.dialog_at(24, 4), (self.dialog_lookup.fairy_water_shop,))

    def test_curse_remover(self):
        # NES ChkCursedDialog ($67): TextBlock11 entry 6, or entries 7 and 8 after lifting the curse
        self.assertEqual(self.dialog_at(24, 10), (self.dialog_lookup.remove_curse,))
        self.dialog_lookup.remove_curse()
        self.assertEqual(self.lines, ["If thou art cursed, come again."])
        self.lines.clear()
        self.game.player.wearing_cursed_belt = True
        self.dialog_lookup.remove_curse()
        self.assertEqual(self.lines, ["I will free thee from thy curse.", "Now, go."])
        self.assertFalse(self.game.player.is_cursed)

    def test_guard_searching_for_gwaelin(self):
        # NES ChkPrncsDialog3 ($64): TextBlock10 entry 14, or entry 15 once F_DONE_GWAELIN is set
        entry, = self.dialog_at(10, 26)
        self.assertEqual(entry.func, self.dialog_lookup.dialog_once_gwaelin_rescued)
        self.assertEqual(entry.args, (("Tell King Lorik that the search for his daughter hath failed.",
                                       "I am almost gone...."),
                                      "Who touches me?’\n`I see nothing, nor can I hear."))
