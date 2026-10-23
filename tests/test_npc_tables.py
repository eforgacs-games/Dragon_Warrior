"""The maps' NPC tables (DragonWarriorMap.npc_table, src/npcs.py) against the NES NPC tables in tests/nes_map_data.py,
which are generated from the disassembly: same NPCs, in the same order, at the same places, with the same sprites,
dialog bytes, facings and mobile flags."""
import os
from unittest import TestCase

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from src.config.test_config import test_config
from src.maps import map_lookup
from src.npcs import GWAELIN_RESCUE
from tests.nes_maps import NPC_TABLE_PREFIXES, decode_map, layout_location, nes_npcs

MAP_SWAMPCAVE = 0x15


class TestNPCTables(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_npc_tables_match_the_nes_tables(self):
        for key in NPC_TABLE_PREFIXES:
            map_name = key.removesuffix('_DL')
            game_map = map_lookup[map_name](test_config)
            table = game_map.npc_table_after_dragonlord if key.endswith('_DL') else game_map.npc_table
            with self.subTest(key):
                self.assertEqual(
                    [(sprite, layout_location(map_name, x, y), dialog, mobile, facing)
                     for sprite, x, y, dialog, mobile, facing in nes_npcs(key)],
                    [(npc.sprite, game_map.npc_position(npc), npc.dialog, npc.mobile, npc.facing.name)
                     for npc in table])

    def test_only_maps_with_nes_npc_tables_have_npcs(self):
        # The NES only loads NPCs for maps MAP_TANTCSTL_GF to MAP_RAINBOW (ChkMapDungeon) and the Dragonlord's room.
        # Gwaelin in the Swamp Cave is a map block there (test_swamp_cave_gwaelin_is_the_princess_block).
        with_npcs = {name for name, map_class in map_lookup.items() if map_class.npc_table}
        self.assertEqual({key.removesuffix('_DL') for key in NPC_TABLE_PREFIXES} | {'SwampCave'}, with_npcs)

    def test_swamp_cave_gwaelin_is_the_princess_block(self):
        nes_map = decode_map(MAP_SWAMPCAVE)
        blocks = [(x, y) for y, row in enumerate(nes_map) for x, tile in enumerate(row) if tile == 'PRINCESS_GWAELIN']
        (x, y), = blocks
        swamp_cave = map_lookup['SwampCave'](test_config)
        gwaelin, = swamp_cave.npc_table
        self.assertEqual(('PRINCESS_GWAELIN', GWAELIN_RESCUE), (gwaelin.sprite, gwaelin.dialog))
        self.assertEqual(layout_location('SwampCave', x, y), swamp_cave.npc_position(gwaelin))

    def test_npc_names_are_unique_on_each_map(self):
        for name, map_class in map_lookup.items():
            for table in (map_class.npc_table, getattr(map_class, 'npc_table_after_dragonlord', ())):
                names = [npc.name for npc in table]
                with self.subTest(name):
                    self.assertEqual(len(names), len(set(names)))
