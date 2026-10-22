import os
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from src.config.test_config import test_config
from src.direction import Direction
from src.game import Game
from src.maps import Brecconary
from tests.test_shop_dialog import npc_identifiers

# NES BrecMobTbl and BrecStatTbl (Bank00): (graphic, X, Y, dialog byte, mobile). Brecconary is offset so that the NES
# NPC at X,Y is at (Y + 8, X + 10) on this map. NES fighters are SOLDIERs here.
BRECCONARY_NPCS = (
    ('WISE_MAN', 9, 4, 0x2B, True),
    ('SOLDIER', 12, 19, 0x5D, True),
    ('MERCHANT', 15, 9, 0x2E, True),
    ('MAN', 25, 22, 0x31, True),
    ('MAN', 10, 14, 0x2C, True),
    ('WOMAN', 24, 4, 0x0F, True),
    ('GUARD', 26, 15, 0x2F, True),
    ('WOMAN', 15, 24, 0x2D, True),
    ('SOLDIER', 19, 18, 0x30, True),
    ('SOLDIER', 3, 26, 0x27, True),
    ('MERCHANT', 5, 4, 0x01, False),
    ('SOLDIER', 28, 1, 0x25, False),
    ('WOMAN', 4, 7, 0x29, False),
    ('MAN', 20, 10, 0x26, False),
    ('WISE_MAN', 24, 10, 0x67, False),
    ('MAN', 1, 13, 0x2A, False),
    ('MERCHANT', 10, 21, 0x12, False),
    ('MAN', 20, 23, 0x28, False),
    ('MERCHANT', 25, 25, 0x08, False),
    ('GUARD', 10, 26, 0x64, False),
)

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


def nes_to_map(x, y):
    return y + 8, x + 10


class TestBrecconaryDialog(TestCase):
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
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.dialog_lookup = self.game.cmd_menu.dialog_lookup
        self.brecconary = Brecconary(test_config)
        self.identifiers = npc_identifiers(self.brecconary)
        self.lines = []
        self.dialog_lookup.command_menu.show_line_in_dialog_box = self.record

    def record(self, line, **kwargs):
        if callable(line):
            line()
        else:
            self.lines.append(line)

    def dialog_at(self, x, y):
        identifier = self.identifiers[nes_to_map(x, y)]
        return self.dialog_lookup.lookup_table['Brecconary'][identifier]['dialog']

    def test_every_nes_npc_is_on_the_map(self):
        expected = {nes_to_map(x, y): graphic for graphic, x, y, _, _ in BRECCONARY_NPCS}
        self.assertEqual(self.brecconary.npc_coordinates, expected)

    def test_every_npc_has_dialog(self):
        self.assertEqual(set(self.identifiers.values()), set(self.dialog_lookup.lookup_table['Brecconary']))

    def test_story_npcs_keep_their_identifiers(self):
        # The ending, curse and Gwaelin code look these NPCs up by identifier
        self.assertEqual(self.identifiers[nes_to_map(10, 26)], 'GUARD')
        self.assertEqual(self.identifiers[nes_to_map(24, 10)], 'WISE_MAN')
        self.assertEqual(self.identifiers[nes_to_map(5, 4)], 'MERCHANT')
        self.assertEqual(self.identifiers[nes_to_map(10, 21)], 'MERCHANT_2')
        self.assertEqual(self.identifiers[nes_to_map(24, 4)], 'WOMAN')

    def test_mobile_npcs_roam(self):
        roaming = {self.identifiers[nes_to_map(x, y)] for _, x, y, _, mobile in BRECCONARY_NPCS if mobile}
        self.assertEqual(set(self.brecconary.roaming_character_list), roaming)

    def test_npc_directions(self):
        # The DD bits of the BrecStatTbl entries that don't face down; every BrecMobTbl entry faces down
        self.brecconary.load_map(self.game.player, None, test_config['TILE_SIZE'])
        facing = {(10, 21): Direction.LEFT, (20, 23): Direction.UP, (25, 25): Direction.LEFT,
                  (10, 26): Direction.UP}
        for _, x, y, _, _ in BRECCONARY_NPCS:
            identifier = self.identifiers[nes_to_map(x, y)]
            expected = facing.get((x, y), Direction.DOWN)
            self.assertEqual(self.brecconary.characters[identifier]['character'].direction_value, expected.value,
                             identifier)

    def test_npcs_stand_on_the_map_floor(self):
        # Each NPC's underlying tile is the floor tile under it, so a roaming NPC doesn't leave a patch behind
        floor_names = {value['val']: name for name, value in self.brecconary.floor_tile_key.items()}
        for _, x, y, _, mobile in BRECCONARY_NPCS:
            if mobile:
                row, column = nes_to_map(x, y)
                identifier = self.identifiers[(row, column)]
                underlying = self.brecconary.custom_underlying_tiles.get(identifier, 'BRICK')
                self.assertEqual(underlying, floor_names[self.brecconary.layout[row][column]], identifier)

    def test_text_dialog_matches_nes(self):
        for _, x, y, dialog_byte, _ in BRECCONARY_NPCS:
            if dialog_byte in BRECCONARY_TEXT:
                text = BRECCONARY_TEXT[dialog_byte]
                if isinstance(text, tuple):
                    text = tuple(line.format(self.game.player.name) for line in text)
                self.assertEqual(self.dialog_at(x, y), text, f'NES {x},{y} ${dialog_byte:02X}')

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
