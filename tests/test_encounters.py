import os
import random
import unittest
from collections import Counter
from unittest.mock import patch

import pygame

from src import encounters
from src.config.test_config import test_config
from src.encounters import (
    DUNGEON_ENEMY_GROUPS, ENEMY_GROUPS, NES_COORDINATE_OFFSETS, OVERWORLD_ZONE_GRID, encounter_group, fight_mask,
    nes_coordinates, overworld_zone, passes_zone_zero_check, pick_enemy, roll_encounter, step_starts_fight,
)
from src.enemy_lookup import enemy_string_lookup
from src.game import Game
from src.maps import map_lookup

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

# The NES data, copied byte for byte from Bank03 of the nmikstas disassembly.

# Defines.asm EN_SLIME ($00) .. EN_DRAGONLORD2 ($27)
NES_ENEMY_NUMBERS = (
    'Slime', 'Red Slime', 'Drakee', 'Ghost', 'Magician', 'Magidrakee', 'Scorpion', 'Druin', 'Poltergeist', 'Droll',
    'Drakeema', 'Skeleton', 'Warlock', 'Metal Scorpion', 'Wolf', 'Wraith', 'Metal Slime', 'Specter', 'Wolflord',
    'Druinlord', 'Drollmagi', 'Wyvern', 'Rogue Scorpion', 'Wraith Knight', 'Golem', 'Goldman', 'Knight', 'Magiwyvern',
    'Demon Knight', 'Werewolf', 'Green Dragon', 'Starwyvern', 'Wizard', 'Axe Knight', 'Blue Dragon', 'Stoneman',
    'Armored Knight', 'Red Dragon', 'Dragonlord', 'Dragonlord 2',
)

# OvrWrldEnGrid ($F522): 4 bytes per zone row, a nibble per zone, the upper nibble for the even zone X.
NES_OVRWRLD_EN_GRID = (
    0x33, 0x22, 0x35, 0x45,
    0x32, 0x12, 0x33, 0x45,
    0x41, 0x00, 0x23, 0x45,
    0x51, 0x1C, 0x66, 0x66,
    0x55, 0x4C, 0x97, 0x77,
    0xA9, 0x8C, 0xCC, 0x87,
    0xAA, 0xBC, 0xDD, 0x98,
    0xBB, 0xCD, 0xDC, 0x99,
)

# CaveEnIndexTbl ($F542), for map numbers $0F (DL castle SL1) to $1B (Garinham cave B4).
NES_CAVE_EN_INDEX_TBL = (0x10, 0x11, 0x11, 0x11, 0x12, 0x12, 0x13, 0x13, 0x0E, 0x0E, 0x07, 0x0F, 0x0F)
# This project's maps for NES map numbers $0F-$1B (SL6 is split into two maps here).
NES_DUNGEON_MAPS = (
    ('CharlockB2',), ('CharlockB3',), ('CharlockB4',), ('CharlockB5',), ('CharlockB6',),
    ('CharlockB7Wide', 'CharlockB7Narrow'), ('SwampCave',), ('MountainCaveB1',), ('MountainCaveB2',),
    ('GarinsGraveB1',), ('GarinsGraveB2',), ('GarinsGraveB3',), ('GarinsGraveB4',),
)

# EnemyGroupsTbl ($F54F), as enemy numbers.
NES_ENEMY_GROUPS_TBL = (
    (0x00, 0x01, 0x00, 0x01, 0x00),
    (0x01, 0x00, 0x01, 0x02, 0x01),
    (0x00, 0x03, 0x02, 0x03, 0x01),
    (0x01, 0x01, 0x02, 0x03, 0x04),
    (0x03, 0x04, 0x05, 0x05, 0x06),
    (0x03, 0x04, 0x05, 0x06, 0x0B),
    (0x05, 0x06, 0x0B, 0x0C, 0x0E),
    (0x0B, 0x0C, 0x0D, 0x0E, 0x0E),
    (0x0D, 0x0F, 0x12, 0x12, 0x19),
    (0x0F, 0x15, 0x12, 0x15, 0x19),
    (0x15, 0x16, 0x17, 0x1A, 0x1C),
    (0x17, 0x1A, 0x1B, 0x1C, 0x10),
    (0x1A, 0x1B, 0x1C, 0x1D, 0x1F),
    (0x1D, 0x1E, 0x1F, 0x1F, 0x20),
    (0x08, 0x09, 0x0A, 0x0B, 0x0C),
    (0x11, 0x12, 0x13, 0x14, 0x17),
    (0x1D, 0x1E, 0x1F, 0x20, 0x21),
    (0x20, 0x21, 0x22, 0x22, 0x23),
    (0x20, 0x23, 0x24, 0x24, 0x25),
    (0x03, 0x04, 0x06, 0x07, 0x07),
)


def nes_overworld_group(x, y):
    """DoRandomFight's lookup of OvrWrldEnGrid for the NES position (x, y)."""
    zone_x, zone_y = x // 15, y // 15
    byte = NES_OVRWRLD_EN_GRID[zone_y * 4 + zone_x // 2]
    return (byte if zone_x % 2 else byte >> 4) & 0x0F


class TestEncounterTables(unittest.TestCase):

    def test_enemy_groups_match_enemy_groups_tbl(self):
        self.assertEqual(len(ENEMY_GROUPS), len(NES_ENEMY_GROUPS_TBL))
        for row, nes_row in enumerate(NES_ENEMY_GROUPS_TBL):
            with self.subTest(row=hex(row)):
                self.assertEqual(ENEMY_GROUPS[row], tuple(NES_ENEMY_NUMBERS[number] for number in nes_row))

    def test_enemy_groups_only_name_known_enemies(self):
        for group in ENEMY_GROUPS:
            for name in group:
                self.assertIn(name, enemy_string_lookup)

    def test_overworld_zone_grid_matches_ovrwrld_en_grid(self):
        for zone_y in range(8):
            for zone_x in range(8):
                with self.subTest(zone=(zone_x, zone_y)):
                    self.assertEqual(OVERWORLD_ZONE_GRID[zone_y][zone_x],
                                     nes_overworld_group(zone_x * 15, zone_y * 15))

    def test_every_overworld_position_uses_the_nes_zone(self):
        column_offset, row_offset = NES_COORDINATE_OFFSETS['Alefgard']
        for y in range(120):
            for x in range(120):
                self.assertEqual(encounter_group('Alefgard', x + column_offset, y + row_offset),
                                 nes_overworld_group(x, y), (x, y))

    def test_zones_are_15_blocks(self):
        # Tantegel Castle is at NES (43, 43): zone (2, 2), one of the two zone-0 squares.
        self.assertEqual(overworld_zone(43 + 8, 43 + 7), (2, 2))
        self.assertEqual(encounter_group('Alefgard', 43 + 8, 43 + 7), 0)
        self.assertEqual(overworld_zone(119 + 8, 119 + 7), (7, 7))
        self.assertEqual(overworld_zone(8 + 15, 7 + 14), (1, 0))

    def test_dungeon_maps_match_cave_en_index_tbl(self):
        for maps, group in zip(NES_DUNGEON_MAPS, NES_CAVE_EN_INDEX_TBL):
            for map_identifier in maps:
                with self.subTest(map=map_identifier):
                    self.assertEqual(DUNGEON_ENEMY_GROUPS[map_identifier], group)

    def test_fixed_rows_for_charlock_and_hauksness(self):
        # DoRandomFight: ChkDungeonFights, ChkHauksnessFight, ChkDLCastleFight
        self.assertEqual(encounter_group('CharlockB1', 0, 0), 0x10)
        self.assertEqual(encounter_group('Hauksness', 0, 0), 0x0D)
        self.assertEqual(encounter_group('CharlockB8', 0, 0), 0x12)

    def test_maps_without_random_fights(self):
        # ChkErdrickFight (maps $1C and up), and maps that aren't MAP_DUNGEON: towns, castles and shrines.
        for map_identifier in ('ErdricksCaveB1', 'ErdricksCaveB2', 'TantegelThroneRoom', 'TantegelCourtyard',
                               'TantegelCellar', 'Brecconary', 'Garinham', 'Kol', 'Rimuldar', 'Cantlin',
                               'StaffOfRainCave', 'MagicTemple'):
            with self.subTest(map=map_identifier):
                self.assertIsNone(encounter_group(map_identifier, 5, 5))
        self.assertEqual(len(DUNGEON_ENEMY_GROUPS), 3 + 14)


class TestCoordinateOffsets(unittest.TestCase):
    # (map, NES (x, y) from MapEntryTbl/MapTargetTbl, this project's (column, row) of the same block)
    CASES = (
        ('Alefgard', (43, 43), (51, 50)),  # Tantegel
        ('Alefgard', (104, 10), (112, 17)),  # Kol
        ('CharlockB1', (10, 19), (17, 25)),
        ('Hauksness', (0, 10), (9, 18)),
        ('CharlockB8', (10, 29), (16, 33)),
        ('CharlockB2', (9, 0), (12, 3)),
        ('CharlockB3', (0, 0), (3, 3)),
        ('CharlockB4', (7, 0), (10, 3)),
        ('CharlockB5', (0, 9), (3, 12)),
        ('CharlockB6', (4, 0), (7, 3)),
        ('CharlockB7Narrow', (0, 0), (3, 3)),
        ('CharlockB7Wide', (0, 6), (3, 5)),
        ('SwampCave', (0, 29), (4, 35)),
        ('MountainCaveB1', (0, 7), (1, 8)),
        ('MountainCaveB2', (6, 5), (7, 6)),
        ('GarinsGraveB1', (6, 11), (7, 12)),
        ('GarinsGraveB2', (11, 2), (12, 3)),
        ('GarinsGraveB3', (18, 1), (19, 2)),
        ('GarinsGraveB4', (0, 4), (1, 5)),
    )

    def test_nes_coordinates(self):
        for map_identifier, nes, (column, row) in self.CASES:
            with self.subTest(map=map_identifier):
                self.assertEqual(nes_coordinates(map_identifier, column, row), nes)


class TestFightChance(unittest.TestCase):
    """CheckBlockDmg: a fight starts when RandNumUB AND mask == 0."""

    def chance(self, tile, x, y):
        mask = fight_mask(tile, x, y)
        return None if mask is None else 1 / (mask + 1)

    def test_chance_per_block(self):
        for tile, expected in (('SAND', 1 / 8), ('HILLS', 1 / 8), ('MARSH', 1 / 16), ('TREES', 1 / 16),
                               ('BRICK', 1 / 16), ('BARRIER', 1 / 16)):
            for x, y in ((0, 0), (0, 1), (1, 0), (1, 1)):
                with self.subTest(tile=tile, position=(x, y)):
                    self.assertEqual(self.chance(tile, x, y), expected)

    def test_grass_and_other_blocks_depend_on_position_parity(self):
        # ChkFight6: HighFightChance (mask $1F) for even X/even Y and odd X/odd Y, NormFightChance ($0F) otherwise
        for tile in ('GRASS', 'BRIDGE', 'BRICK_STAIR_UP', 'BRICK_STAIR_DOWN', 'TREASURE_BOX', 'WOOD', 'DOOR'):
            with self.subTest(tile=tile):
                self.assertEqual(self.chance(tile, 0, 0), 1 / 32)
                self.assertEqual(self.chance(tile, 1, 1), 1 / 32)
                self.assertEqual(self.chance(tile, 0, 1), 1 / 16)
                self.assertEqual(self.chance(tile, 1, 0), 1 / 16)

    def test_map_changing_blocks_never_start_fights(self):
        for tile in ('TOWN', 'CASTLE', 'CAVE', 'GRASS_STAIR_DOWN'):
            with self.subTest(tile=tile):
                self.assertIsNone(fight_mask(tile, 0, 0))
                self.assertFalse(any(step_starts_fight('Alefgard', tile, 20, 20) for _ in range(200)))

    def test_parity_uses_nes_coordinates(self):
        # Alefgard's layout is offset by (8, 7), an odd sum, so layout (column + row) even is NES (x + y) odd.
        with patch('src.encounters.random.randint', return_value=1) as randint:
            step_starts_fight('Alefgard', 'GRASS', 20, 20)
            self.assertEqual(randint.call_args.args, (0, 0x0F))
            step_starts_fight('Alefgard', 'GRASS', 20, 21)
            self.assertEqual(randint.call_args.args, (0, 0x1F))
            # Garin's Grave is offset by (1, 1)
            step_starts_fight('GarinsGraveB1', 'TREASURE_BOX', 20, 20)
            self.assertEqual(randint.call_args.args, (0, 0x1F))

    def test_seeded_fight_rate_per_block(self):
        random.seed(230)
        trials = 64000
        # (map, tile, column, row, expected chance)
        for map_identifier, tile, column, row, expected in (
                ('Alefgard', 'SAND', 20, 20, 1 / 8),
                ('Alefgard', 'HILLS', 20, 20, 1 / 8),
                ('Alefgard', 'MARSH', 20, 20, 1 / 16),
                ('Alefgard', 'TREES', 20, 20, 1 / 16),
                ('Alefgard', 'GRASS', 20, 20, 1 / 16),
                ('Alefgard', 'GRASS', 20, 21, 1 / 32),
                ('Alefgard', 'BRIDGE', 21, 20, 1 / 32),
                ('SwampCave', 'BRICK', 10, 10, 1 / 16),
                ('CharlockB1', 'BARRIER', 10, 10, 1 / 16),
        ):
            with self.subTest(map=map_identifier, tile=tile, position=(column, row)):
                fights = sum(step_starts_fight(map_identifier, tile, column, row) for _ in range(trials))
                self.assertAlmostEqual(fights / trials, expected, delta=expected * 0.15)


class TestZoneZero(unittest.TestCase):

    def test_zone_zero_check(self):
        # HighFightModifier (hills: RandNumUB AND 3) and NormFightModifier (RandNumUB AND 1)
        with patch('src.encounters.random.randint', return_value=0) as randint:
            self.assertTrue(passes_zone_zero_check('HILLS'))
            self.assertEqual(randint.call_args.args, (0, 3))
            self.assertTrue(passes_zone_zero_check('GRASS'))
            self.assertEqual(randint.call_args.args, (0, 1))
        with patch('src.encounters.random.randint', return_value=1):
            self.assertFalse(passes_zone_zero_check('HILLS'))
            self.assertFalse(passes_zone_zero_check('GRASS'))

    def test_zone_zero_rate_near_tantegel(self):
        # Two zone-0 squares: NES zones (2, 2) and (3, 2). Grass at even/odd parity: 1/16 * 1/2 = 1/32.
        random.seed(43)
        trials = 64000
        column, row = 40 + 8, 35 + 7  # NES (40, 35): zone (2, 2), x + y odd
        self.assertEqual(encounter_group('Alefgard', column, row), 0)
        fights = sum(roll_encounter('Alefgard', 'GRASS', column, row) is not None for _ in range(trials))
        self.assertAlmostEqual(fights / trials, 1 / 32, delta=1 / 32 * 0.15)
        fights = sum(roll_encounter('Alefgard', 'HILLS', column, row) is not None for _ in range(trials))
        self.assertAlmostEqual(fights / trials, 1 / 32, delta=1 / 32 * 0.15)

    def test_other_zones_skip_the_check(self):
        column, row = 60 + 8, 35 + 7  # NES (60, 35): zone (4, 2), row $02
        with patch('src.encounters.random.randint', return_value=0) as randint, \
                patch.object(encounters, 'passes_zone_zero_check') as zone_zero:
            self.assertEqual(roll_encounter('Alefgard', 'GRASS', column, row), ENEMY_GROUPS[2])
        zone_zero.assert_not_called()
        randint.assert_called_once()

    def test_no_fight_when_the_step_roll_fails(self):
        with patch('src.encounters.random.randint', return_value=1):
            self.assertIsNone(roll_encounter('GarinsGraveB2', 'BRICK', 5, 5))
        with patch('src.encounters.random.randint', return_value=0):
            self.assertEqual(roll_encounter('GarinsGraveB2', 'BRICK', 5, 5), ENEMY_GROUPS[7])
            self.assertIsNone(roll_encounter('ErdricksCaveB1', 'BRICK', 5, 5))


class TestPickEnemy(unittest.TestCase):

    def test_rerolls_slots_five_to_seven(self):
        # GetEnemyInRow: RandNumUB AND 7, again while >= 5
        group = ENEMY_GROUPS[0x13]
        with patch('src.encounters.random.randint', side_effect=[7, 5, 6, 3]) as randint:
            self.assertEqual(pick_enemy(group), group[3])
        self.assertEqual(randint.call_count, 4)
        self.assertEqual(randint.call_args.args, (0, 7))

    def test_each_slot_equally_likely(self):
        random.seed(5)
        trials = 50000
        counts = Counter(pick_enemy(ENEMY_GROUPS[0x13]) for _ in range(trials))
        # Ghost, Magician, Scorpion: 1 slot each; Druin: 2 slots
        self.assertAlmostEqual(counts['Druin'] / trials, 2 / 5, delta=0.02)
        for name in ('Ghost', 'Magician', 'Scorpion'):
            self.assertAlmostEqual(counts[name] / trials, 1 / 5, delta=0.02)



class TestHandleBattles(unittest.TestCase):
    """Game.handle_battles checks the block the player has just stepped onto, once per step."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.addCleanup(patch.stopall)
        self.config = patch.dict(self.game.game_state.config, FORCE_BATTLE=False, NO_BATTLES=False)
        self.config.start()

    def step_onto(self, map_name, row, column):
        """Arrive on (row, column), with player.column/row and current_tile still on the block before it."""
        self.game.change_map(map_lookup[map_name](self.game.config), destination_coordinates=(row, column))
        self.game.player.column, self.game.player.row = column - 1, row
        self.game.player.current_tile = 'CASTLE'
        self.game.tiles_moved_since_spawn += 1

    def fight_roll(self):
        with patch('src.encounters.random.randint', return_value=0) as randint, \
                patch.object(self.game.battle_ctrl, 'run_battle') as run_battle:
            self.game.handle_battles()
        return randint, run_battle

    def test_overworld_fight_uses_the_new_block(self):
        # Layout (row 37, column 62) is NES (54, 30), zone (3, 2): row $00. Hills there.
        row, column = 37, 62
        self.step_onto('Alefgard', row, column)
        self.assertEqual(self.game.current_map.get_tile_by_value(self.game.current_map.layout[row][column]),
                         'HILLS')
        randint, run_battle = self.fight_roll()
        run_battle.assert_called_once_with(ENEMY_GROUPS[0])
        # the step roll (1 in 8 on hills), then zone 0's extra roll (1 in 4 on hills)
        self.assertEqual([c.args for c in randint.call_args_list], [(0, 7), (0, 3)])

    def test_one_check_per_step(self):
        self.step_onto('GarinsGraveB2', 3, 12)
        _, run_battle = self.fight_roll()
        run_battle.assert_called_once_with(ENEMY_GROUPS[7])
        _, run_battle = self.fight_roll()
        run_battle.assert_not_called()

    def test_charlock_ground_floor_has_fights(self):
        self.step_onto('CharlockB1', 25, 17)
        _, run_battle = self.fight_roll()
        run_battle.assert_called_once_with(ENEMY_GROUPS[0x10])

    def test_no_fights_in_erdricks_cave_or_towns(self):
        for map_name, row, column in (('ErdricksCaveB1', 3, 3), ('Brecconary', 23, 10)):
            with self.subTest(map=map_name):
                self.step_onto(map_name, row, column)
                _, run_battle = self.fight_roll()
                run_battle.assert_not_called()


if __name__ == '__main__':
    unittest.main()
