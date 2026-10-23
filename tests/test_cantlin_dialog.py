import os
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from src.config.test_config import test_config
from src.direction import Direction
from src.game import Game
from src.maps import Cantlin
from tests.test_shop_dialog import npc_identifiers

# NES CantMobTbl and CantStatTbl (Bank00): (graphic, X, Y, dialog byte, mobile). Cantlin is offset so that the NES
# NPC at X,Y is at (Y + 8, X + 1) on this map.
CANTLIN_NPCS = (
    ('MAN', 20, 15, 0x4B, True),
    ('GUARD', 5, 6, 0x60, True),
    ('MERCHANT', 25, 17, 0x4C, True),
    ('WOMAN', 4, 14, 0x49, True),
    ('MERCHANT', 22, 5, 0x03, True),
    ('WOMAN', 9, 16, 0x4A, True),
    ('WISE_MAN', 14, 28, 0x6B, True),
    ('GUARD', 15, 6, 0x48, True),
    ('MERCHANT', 3, 26, 0x4E, True),
    ('GUARD', 22, 9, 0x4D, True),
    ('MERCHANT', 8, 3, 0x14, False),
    ('WISE_MAN', 27, 6, 0x0C, False),
    ('MAN', 2, 7, 0x0A, False),
    ('MERCHANT', 2, 12, 0x45, False),
    ('MERCHANT', 7, 12, 0x0B, False),
    ('GUARD', 24, 12, 0x05, False),
    ('WOMAN', 22, 13, 0x10, False),
    ('WISE_MAN', 15, 16, 0x46, False),
    ('WISE_MAN', 22, 22, 0x47, False),
    ('MERCHANT', 27, 26, 0x04, False),
)

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


def nes_to_map(x, y):
    return y + 8, x + 1


class TestCantlinDialog(TestCase):
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
        self.cantlin = Cantlin(test_config)
        self.identifiers = npc_identifiers(self.cantlin)
        self.lines = []
        self.prompts = []
        self.answers = []
        self.dialog_lookup.command_menu.show_line_in_dialog_box = lambda line, **kwargs: self.lines.append(line)
        confirmation_patch = patch('data.text.dialog_lookup_table.confirmation_prompt', side_effect=self.answer)
        confirmation_patch.start()
        self.addCleanup(confirmation_patch.stop)

    def answer(self, command_menu, prompt, yes_path_function, no_path_function, **kwargs):
        self.prompts.append(prompt)
        (yes_path_function if self.answers.pop(0) else no_path_function)()

    def dialog_at(self, x, y):
        identifier = self.identifiers[nes_to_map(x, y)]
        return self.dialog_lookup.lookup_table['Cantlin'][identifier]['dialog']

    def test_every_nes_npc_is_on_the_map(self):
        expected = {nes_to_map(x, y): graphic for graphic, x, y, _, _ in CANTLIN_NPCS}
        self.assertEqual(self.cantlin.npc_coordinates, expected)

    def test_every_npc_has_dialog(self):
        self.assertEqual(set(self.identifiers.values()), set(self.dialog_lookup.lookup_table['Cantlin']))

    def test_mobile_npcs_roam(self):
        roaming = {self.identifiers[nes_to_map(x, y)] for _, x, y, _, mobile in CANTLIN_NPCS if mobile}
        self.assertEqual(set(self.cantlin.roaming_character_list), roaming)

    def test_static_npc_directions(self):
        # The DD bits of the CantStatTbl entries that don't face down
        self.cantlin.load_map(self.game.player, None, test_config['TILE_SIZE'])
        facing = {(2, 7): Direction.RIGHT, (2, 12): Direction.RIGHT, (7, 12): Direction.LEFT,
                  (24, 12): Direction.RIGHT, (22, 13): Direction.LEFT, (27, 26): Direction.LEFT}
        for _, x, y, _, mobile in CANTLIN_NPCS:
            identifier = self.identifiers[nes_to_map(x, y)]
            expected = facing.get((x, y), Direction.DOWN)
            self.assertEqual(self.cantlin.characters[identifier]['character'].direction_value, expected.value,
                             identifier)

    def test_text_dialog_matches_nes(self):
        for _, x, y, dialog_byte, _ in CANTLIN_NPCS:
            if dialog_byte in CANTLIN_TEXT:
                self.assertEqual(self.dialog_at(x, y), CANTLIN_TEXT[dialog_byte], f'NES {x},{y} ${dialog_byte:02X}')

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
