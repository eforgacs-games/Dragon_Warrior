import os
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from src.config.test_config import test_config
from src.direction import Direction
from src.game import Game
from src.map_layouts import MapLayouts
from src.maps import Garinham
from tests.test_shop_dialog import npc_identifiers

# NES GarMobTbl and GarStatTbl (Bank00): (graphic, X, Y, dialog byte, mobile). Garinham is offset so that the NES
# NPC at X,Y is at (Y + 1, X + 9) on this map. The NES fighter is this game's SOLDIER.
GARINHAM_NPCS = (
    ('WOMAN', 12, 4, 0x3E, True),
    ('WOMAN', 12, 12, 0x43, True),
    ('WISE_MAN', 12, 8, 0x3F, True),
    ('WISE_MAN', 2, 10, 0x42, True),
    ('MAN', 11, 7, 0x3D, True),
    ('MAN', 18, 12, 0x44, True),
    ('SOLDIER', 7, 17, 0x41, True),
    ('WISE_MAN', 14, 1, 0x3A, False),
    ('GUARD', 3, 5, 0x3B, False),
    ('GUARD', 5, 5, 0x3B, False),
    ('MERCHANT', 9, 6, 0x3C, False),
    ('MERCHANT', 5, 11, 0x09, False),
    ('MERCHANT', 17, 15, 0x13, False),
    ('WISE_MAN', 2, 17, 0x40, False),
    ('MERCHANT', 10, 18, 0x02, False),
)

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


def nes_to_map(x, y):
    return y + 1, x + 9


class TestGarinhamDialog(TestCase):
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
        self.garinham = Garinham(test_config)
        self.identifiers = npc_identifiers(self.garinham)

    def dialog_at(self, x, y):
        identifier = self.identifiers[nes_to_map(x, y)]
        return self.dialog_lookup.lookup_table['Garinham'][identifier]['dialog']

    def test_every_nes_npc_is_on_the_map(self):
        expected = {nes_to_map(x, y): graphic for graphic, x, y, _, _ in GARINHAM_NPCS}
        self.assertEqual(self.garinham.npc_coordinates, expected)

    def test_every_npc_has_dialog(self):
        self.assertEqual(set(self.identifiers.values()), set(self.dialog_lookup.lookup_table['Garinham']))

    def test_mobile_npcs_roam(self):
        roaming = {self.identifiers[nes_to_map(x, y)] for _, x, y, _, mobile in GARINHAM_NPCS if mobile}
        self.assertEqual(set(self.garinham.roaming_character_list), roaming)

    def test_npc_directions(self):
        # The DD bits of the GarStatTbl entries that don't face down (every GarMobTbl entry faces down)
        self.garinham.load_map(self.game.player, None, test_config['TILE_SIZE'])
        facing = {(3, 5): Direction.RIGHT, (5, 5): Direction.LEFT, (5, 11): Direction.LEFT,
                  (17, 15): Direction.LEFT, (2, 17): Direction.RIGHT, (10, 18): Direction.UP}
        for _, x, y, _, _ in GARINHAM_NPCS:
            identifier = self.identifiers[nes_to_map(x, y)]
            expected = facing.get((x, y), Direction.DOWN)
            self.assertEqual(self.garinham.characters[identifier]['character'].direction_value, expected.value,
                             identifier)

    def test_text_dialog_matches_nes(self):
        for _, x, y, dialog_byte, _ in GARINHAM_NPCS:
            if dialog_byte in GARINHAM_TEXT:
                self.assertEqual(self.dialog_at(x, y), GARINHAM_TEXT[dialog_byte], f'NES {x},{y} ${dialog_byte:02X}')

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

    def test_npc_underlying_tiles(self):
        # Each NPC is drawn over the tile it stands on: the fighter at 7,17 is on sand, the rest on brick
        layout = MapLayouts().garinham
        for _, x, y, _, _ in GARINHAM_NPCS:
            row, column = nes_to_map(x, y)
            identifier = self.identifiers[(row, column)]
            underlying = self.garinham.custom_underlying_tiles.get(identifier, 'BRICK')
            self.assertEqual(layout[row][column], self.garinham.floor_tile_key[underlying]['val'], identifier)

    def test_garins_grave_stairs(self):
        # NES 19,0 is the staircase down into Garin's Grave
        self.assertEqual(self.garinham.staircases[nes_to_map(19, 0)]['map'], 'GarinsGraveB1')
