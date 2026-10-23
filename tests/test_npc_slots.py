"""The roaming NPCs' mobile slots, which decide which two NPCs move together on the NES's schedule
(src/npc_schedule.py).

NES GetNPCDataPointer (Bank00) copies a map's mobile NPC table into the mobile slots in the table's order, so the pairs
that take turns are the table's first and second NPCs, its third and fourth, and so on. Removing an NPC (zeroing its
position) leaves its slot empty: the others keep theirs until the map is loaded again.
"""
from unittest import TestCase
from unittest.mock import patch

import pygame

from src.config.test_config import test_config
from src.game import Game
from src.maps import map_lookup
from src.npc_schedule import FRAMES_PER_TURN, NPCS_PER_TURN

# The NES mobile NPC tables (Bank00.asm of the nmikstas Dragon Warrior disassembly, TantMobTbl to GarMobTbl), as each
# entry's NES (x, y), in table order
NES_MOBILE_NPC_TABLES = {
    'ThRmMobTbl': [(7, 5)],
    'TantMobTbl': [(8, 13), (19, 2), (11, 11), (17, 11), (4, 21), (25, 11), (18, 18), (2, 12), (6, 25), (24, 21)],
    'TaDLMobTbl': [(19, 2), (14, 23), (25, 11), (18, 18), (2, 12), (6, 25), (24, 21)],
    'CantMobTbl': [(20, 15), (5, 6), (25, 17), (4, 14), (22, 5), (9, 16), (14, 28), (15, 6), (3, 26), (22, 9)],
    'RimMobTbl': [(6, 21), (11, 8), (6, 23), (22, 14), (5, 25), (23, 11), (14, 11), (16, 26), (8, 16), (24, 19)],
    'BrecMobTbl': [(9, 4), (12, 19), (15, 9), (25, 22), (10, 14), (24, 4), (26, 15), (15, 24), (19, 18), (3, 26)],
    'KolMobTbl': [(14, 13), (5, 12), (12, 10), (2, 12), (20, 19), (6, 7), (11, 14), (7, 19), (20, 8)],
    'GarMobTbl': [(12, 4), (12, 12), (12, 8), (2, 10), (11, 7), (18, 12), (7, 17)],
}
# map name, whether the Dragonlord is defeated, the map's mobile NPC table then
MAP_TABLES = [
    ('TantegelThroneRoom', False, 'ThRmMobTbl'),
    ('TantegelCourtyard', False, 'TantMobTbl'),
    ('TantegelCourtyard', True, 'TaDLMobTbl'),
    ('Brecconary', False, 'BrecMobTbl'),
    ('Garinham', False, 'GarMobTbl'),
    ('Kol', False, 'KolMobTbl'),
    ('Rimuldar', False, 'RimMobTbl'),
    ('Cantlin', False, 'CantMobTbl'),
]


class TestMobileNPCSlots(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    def setUp(self):
        with patch('src.game.SCALED', 0):
            self.game = Game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True})
        self.game.game_state.is_initial_dialog = False

    def load(self, map_name: str, dragonlord_defeated: bool = False):
        self.game.story_flags.dragonlord_defeated = dragonlord_defeated
        next_map = map_lookup[map_name](self.game.config)
        self.game.change_map(next_map, destination_coordinates=next_map.initial_coordinates)
        return self.game.current_map

    def test_slots_are_in_the_order_of_the_nes_mobile_npc_table(self):
        for map_name, dragonlord_defeated, table in MAP_TABLES:
            with self.subTest(map_name, table=table):
                current_map = self.load(map_name, dragonlord_defeated)
                origin_row, origin_column = current_map.nes_origin
                expected = [(y + origin_row, x + origin_column) for x, y in NES_MOBILE_NPC_TABLES[table]]
                roaming_characters = current_map.roaming_characters
                self.assertEqual(expected, [(npc.row, npc.column) for npc in roaming_characters])
                self.assertEqual(list(range(len(expected))), [npc.slot for npc in roaming_characters])
                self.assertEqual(current_map.roaming_character_list, [npc.identifier for npc in roaming_characters])

    def deciders_by_turn(self) -> list[list[str]]:
        """Run one 5-pair cycle from the start of a pair 0 turn. Returns, by turn, the NPCs that decided a step."""
        self.game.movement.npc_schedule.give_turn_to(0)
        turns: list[list[str]] = []
        with patch.object(self.game.movement, 'start_npc_step', lambda npc: turns[-1].append(npc.identifier)):
            for frame in range(5 * FRAMES_PER_TURN):
                if frame % FRAMES_PER_TURN == 0:
                    turns.append([])
                self.game.movement.do_sprites()
        return turns

    def test_removing_a_roaming_npc_keeps_the_others_slots(self):
        current_map = self.load('Cantlin')
        dialog_lookup = self.game.cmd_menu.dialog_lookup
        dialog_lookup.current_map = current_map
        slots = {npc.identifier: npc.slot for npc in current_map.roaming_characters}
        before = self.deciders_by_turn()
        self.assertEqual([[npc.identifier for npc in current_map.roaming_characters[first:first + NPCS_PER_TURN]]
                          for first in range(0, len(slots), NPCS_PER_TURN)], before)

        removed = current_map.roaming_characters[2].identifier  # the first NPC of the second pair
        dialog_lookup.remove_npc(removed)
        self.assertNotIn(removed, [npc.identifier for npc in current_map.roaming_characters])
        del slots[removed]
        self.assertEqual(slots, {npc.identifier: npc.slot for npc in current_map.roaming_characters})
        # Its pair partner now moves alone on the pair's turn; every other pair is unchanged
        expected = [[identifier for identifier in turn if identifier != removed] for turn in before]
        self.assertEqual(expected, self.deciders_by_turn())
