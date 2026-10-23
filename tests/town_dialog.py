"""
The NPC checks every town and castle dialog test runs (test_kol_dialog.py and so on), against the NES NPC tables in
tests/nes_map_data.py (generated from the disassembly), not against the maps' own NPC tables.
"""
import os
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from src.config.test_config import test_config
from src.direction import Direction
from src.game import Game
from tests.nes_maps import layout_location, nes_npcs
from tests.test_shop_dialog import npc_identifiers


class TownDialogMixin:
    """The setup, helpers and NPC table tests of a map's dialog tests. Mix in before TestCase, and set:

    map_class: the map (Kol, Brecconary, ...).
    text: the Bank02 text of the map's dialog bytes between $16 and $5D (TextBlock entry = byte + $2F), by byte. "{}"
        is the hero's name.
    not_on_the_map: the dialog bytes of NES table NPCs that aren't on the map when it's loaded (Gwaelin in the throne
        room until she's been returned).
    """
    map_class: type
    text: dict = {}
    not_on_the_map: frozenset = frozenset()

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
        self.town = self.map_class(test_config)
        self.identifiers = npc_identifiers(self.town)
        self.lines = []
        self.prompts = []
        self.answers = []
        self.dialog_lookup.command_menu.show_line_in_dialog_box = self.record
        confirmation_patch = patch('data.text.dialog_lookup_table.confirmation_prompt', side_effect=self.answer)
        confirmation_patch.start()
        self.addCleanup(confirmation_patch.stop)

    def record(self, line, **kwargs):
        self.lines.append(line)

    def answer(self, command_menu, prompt, yes_path_function, no_path_function, **kwargs):
        self.prompts.append(prompt)
        (yes_path_function if self.answers.pop(0) else no_path_function)()

    @property
    def map_name(self) -> str:
        return self.map_class.__name__

    def nes_to_map(self, x, y):
        """The layout (row, column) of NES (x, y), from tests/nes_maps.py."""
        return layout_location(self.map_name, x, y)

    def nes_npcs_on_the_map(self):
        """The map's NES NPCs, (sprite, x, y, dialog byte, mobile, facing), less the ones not_on_the_map."""
        return [npc for npc in nes_npcs(self.map_name) if npc[3] not in self.not_on_the_map]

    def dialog_at(self, x, y):
        identifier = self.identifiers[self.nes_to_map(x, y)]
        return self.dialog_lookup.lookup_table[self.map_name][identifier]['dialog']

    def test_every_nes_npc_is_on_the_map(self):
        expected = {self.nes_to_map(x, y): sprite for sprite, x, y, *_ in self.nes_npcs_on_the_map()}
        self.assertEqual(expected, self.town.npc_coordinates)

    def test_every_npc_has_dialog(self):
        self.assertEqual({npc.name for npc in self.town.npc_table},
                         set(self.dialog_lookup.lookup_table[self.map_name]))

    def test_mobile_npcs_roam(self):
        self.assertEqual([self.identifiers[self.nes_to_map(x, y)] for _, x, y, _, mobile, _ in self.nes_npcs_on_the_map()
                          if mobile], self.town.roaming_character_list)

    def test_npc_directions(self):
        # The DD bits of each table entry
        self.town.load_map(self.game.player, None, test_config['TILE_SIZE'])
        for _, x, y, _, _, facing in self.nes_npcs_on_the_map():
            identifier = self.identifiers[self.nes_to_map(x, y)]
            with self.subTest(identifier):
                self.assertEqual(Direction[facing].value, self.town.characters[identifier]['character'].direction_value)

    def test_text_dialog_matches_nes(self):
        for _, x, y, dialog_byte, _, _ in self.nes_npcs_on_the_map():
            if dialog_byte in self.text:
                text = self.text[dialog_byte]
                if isinstance(text, tuple):
                    text = tuple(line.format(self.game.player.name) for line in text)
                else:
                    text = text.format(self.game.player.name)
                self.assertEqual(text, self.dialog_at(x, y), f'NES {x},{y} ${dialog_byte:02X}')
