import os
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from src.config.test_config import test_config
from src.direction import Direction
from src.game import Game
from src.items import hidden_items
from src.maps import Kol
from tests.test_shop_dialog import npc_identifiers

# NES KolMobTbl and KolStatTbl (Bank00): (graphic, X, Y, dialog byte, mobile). Kol is offset so that the NES NPC at
# X,Y is at (Y + 8, X + 10) on this map. The fighters are SOLDIER here.
KOL_NPCS = (
    ('MAN', 14, 13, 0x36, True),
    ('MAN', 5, 12, 0x30, True),
    ('GUARD', 12, 10, 0x37, True),
    ('WISE_MAN', 2, 12, 0x5E, True),
    ('WISE_MAN', 20, 19, 0x38, True),
    ('SOLDIER', 6, 7, 0x35, True),
    ('WOMAN', 11, 14, 0x2E, True),
    ('MERCHANT', 7, 19, 0x5F, True),
    ('WISE_MAN', 20, 8, 0x39, True),
    ('WISE_MAN', 1, 1, 0x68, False),
    ('WOMAN', 12, 1, 0x32, False),
    ('MERCHANT', 19, 4, 0x11, False),
    ('MERCHANT', 22, 12, 0x00, False),
    ('SOLDIER', 20, 13, 0x33, False),
    ('MERCHANT', 14, 21, 0x07, False),
    ('GUARD', 1, 23, 0x34, False),
)

# Bank02 text for the dialog bytes between $16 and $5D (TextBlock entry = byte + $2F)
KOL_TEXT = {
    0x2E: "Please,save us from the minions of the Dragonlord.",
    0x30: "Art thou the descendant of Erdrick?\nHast thou any proof?",
    0x32: "This bath cures rheumatism.",
    0x33: "East of Hauksness there is a town, 'tis said, where one may purchase weapons of extraordinary quality.",
    0x34: "Rimuldar is the place to buy keys.",
    0x35: "Hast thou seen Nester?\nI think he may need help.",
    0x36: ("Dreadful is the South Island.",
           "Great strength and skill and wit only will bring thee back from that place."),
    0x37: "Golem is afraid of the music of the flute, so 'tis said.",
    0x38: "This is the village of Kol.",
    0x39: "In legends it is said that fairies know how to put Golem to sleep.",
}


def nes_to_map(x, y):
    return y + 8, x + 10


class TestKolDialog(TestCase):
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
        self.kol = Kol(test_config)
        self.identifiers = npc_identifiers(self.kol)
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
        return self.dialog_lookup.lookup_table['Kol'][identifier]['dialog']

    def test_every_nes_npc_is_on_the_map(self):
        expected = {nes_to_map(x, y): graphic for graphic, x, y, _, _ in KOL_NPCS}
        self.assertEqual(self.kol.npc_coordinates, expected)

    def test_every_npc_has_dialog(self):
        self.assertEqual(set(self.identifiers.values()), set(self.dialog_lookup.lookup_table['Kol']))

    def test_mobile_npcs_roam(self):
        roaming = {self.identifiers[nes_to_map(x, y)] for _, x, y, _, mobile in KOL_NPCS if mobile}
        self.assertEqual(set(self.kol.roaming_character_list), roaming)

    def test_npc_directions(self):
        # The DD bits of the KolStatTbl entries that don't face down (every KolMobTbl entry faces down)
        self.kol.load_map(self.game.player, None, test_config['TILE_SIZE'])
        facing = {(19, 4): Direction.UP, (22, 12): Direction.LEFT, (14, 21): Direction.LEFT}
        for _, x, y, _, _ in KOL_NPCS:
            identifier = self.identifiers[nes_to_map(x, y)]
            expected = facing.get((x, y), Direction.DOWN)
            self.assertEqual(self.kol.characters[identifier]['character'].direction_value, expected.value,
                             identifier)

    def test_text_dialog_matches_nes(self):
        for _, x, y, dialog_byte, _ in KOL_NPCS:
            if dialog_byte in KOL_TEXT:
                self.assertEqual(self.dialog_at(x, y), KOL_TEXT[dialog_byte], f'NES {x},{y} ${dialog_byte:02X}')

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
        self.assertEqual(flute, nes_to_map(9, 6))
        self.assertNotIn(flute, self.kol.npc_coordinates)
