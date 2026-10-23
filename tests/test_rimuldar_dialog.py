import os
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from src.config.test_config import test_config
from src.direction import Direction
from src.game import Game
from src.items import treasure
from src.maps import Rimuldar
from tests.test_shop_dialog import npc_identifiers

# NES RimMobTbl and RimStatTbl (Bank00): (graphic, X, Y, dialog byte, mobile). Rimuldar is offset so that the NES
# NPC at X,Y is at (Y + 8, X + 8) on this map.
RIMULDAR_NPCS = (
    ('WOMAN', 6, 21, 0x59, True),
    ('MAN', 11, 8, 0x30, True),
    ('MAN', 6, 23, 0x5A, True),
    ('WOMAN', 22, 14, 0x56, True),
    ('SOLDIER', 5, 25, 0x5B, True),
    ('SOLDIER', 23, 11, 0x52, True),
    ('MAN', 14, 11, 0x55, True),
    ('SOLDIER', 16, 26, 0x69, True),
    ('GUARD', 8, 16, 0x54, True),
    ('SOLDIER', 24, 19, 0x57, True),
    ('MAN', 27, 0, 0x51, False),
    ('MERCHANT', 2, 4, 0x4F, False),
    ('WISE_MAN', 4, 7, 0x0D, False),
    ('MERCHANT', 23, 7, 0x06, False),
    ('WOMAN', 15, 8, 0x50, False),
    ('WISE_MAN', 6, 13, 0x53, False),
    ('MERCHANT', 16, 18, 0x15, False),
    ('WISE_MAN', 3, 23, 0x61, False),
    ('WISE_MAN', 20, 23, 0x58, False),
    ('WOMAN', 0, 26, 0x5C, False),
)

# Bank02 text for the dialog bytes between $16 and $5D (TextBlock entry = byte + $2F)
RIMULDAR_TEXT = {
    0x30: "Art thou the descendant of Erdrick?\nHast thou any proof?",
    0x4F: "Welcome!",
    0x50: "Who art thou?\nLeave at once or I will call my friends.",
    0x51: "I am Orwick, and I am waiting for my girl friend.",
    0x52: "The scales of the Dragonlord are as hard as steel.",
    0x53: ("Over the western part of this island Erdrick created a rainbow.",
           "'Tis also said that he entered the darkness from a hidden entrance in the room of the Dragonlord."),
    0x54: "Thou shalt find the Stones of Sunlight in Tantegel Castle,\nif thou has not found them yet.",
    0x55: "Welcome to the town of Rimuldar.",
    0x56: "No, I have no tomatoes.\nI have no tomatoes today.",
    0x58: "Good day,I am Howard. Four steps south of the bath in Kol thou shalt find a magic item.",
    0x59: "Before long the enemy will arrive.",
    0x5A: "Heed my warning! Travel not to the south for there the monsters are fierce and terrible.",
    0x5B: "In this world is there any sword that can pierce the scales of the Dragonlord?",
    0x5C: "Orwick is late again. I'm starving.",
}


def nes_to_map(x, y):
    return y + 8, x + 8


class TestRimuldarDialog(TestCase):
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
        self.rimuldar = Rimuldar(test_config)
        self.identifiers = npc_identifiers(self.rimuldar)
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
        return self.dialog_lookup.lookup_table['Rimuldar'][identifier]['dialog']

    def test_every_nes_npc_is_on_the_map(self):
        expected = {nes_to_map(x, y): graphic for graphic, x, y, _, _ in RIMULDAR_NPCS}
        self.assertEqual(self.rimuldar.npc_coordinates, expected)

    def test_every_npc_has_dialog(self):
        self.assertEqual(set(self.identifiers.values()), set(self.dialog_lookup.lookup_table['Rimuldar']))

    def test_mobile_npcs_roam(self):
        roaming = {self.identifiers[nes_to_map(x, y)] for _, x, y, _, mobile in RIMULDAR_NPCS if mobile}
        self.assertEqual(set(self.rimuldar.roaming_character_list), roaming)

    def test_npc_directions(self):
        # The DD bits of the RimStatTbl entries that don't face down; every RimMobTbl entry faces down
        self.rimuldar.load_map(self.game.player, None, test_config['TILE_SIZE'])
        facing = {(2, 4): Direction.UP, (4, 7): Direction.UP, (15, 8): Direction.UP, (6, 13): Direction.LEFT,
                  (16, 18): Direction.RIGHT, (3, 23): Direction.RIGHT}
        for _, x, y, _, _ in RIMULDAR_NPCS:
            identifier = self.identifiers[nes_to_map(x, y)]
            expected = facing.get((x, y), Direction.DOWN)
            self.assertEqual(self.rimuldar.characters[identifier]['character'].direction_value, expected.value,
                             identifier)

    def test_text_dialog_matches_nes(self):
        for _, x, y, dialog_byte, _ in RIMULDAR_NPCS:
            if dialog_byte in RIMULDAR_TEXT:
                self.assertEqual(self.dialog_at(x, y), RIMULDAR_TEXT[dialog_byte], f'NES {x},{y} ${dialog_byte:02X}')

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
        self.assertEqual(treasure['Rimuldar'], {nes_to_map(24, 23): {'item': 'Wings'}})
        self.assertNotIn(nes_to_map(24, 23), self.rimuldar.npc_coordinates)

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
