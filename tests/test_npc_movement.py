"""Where roaming NPCs may walk, per NES UpdateNPCs1 (Bank00, $B76F). See src/npc_movement.py for the rules."""
import os
import random
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from src.config.test_config import test_config
from src.direction import Direction
from src.game import Game
from src.maps import map_lookup
from src.npc_movement import npc_may_step_onto, step
from src.npc_schedule import FRAMES_PER_TURN, TURNS_PER_CYCLE

# NES block IDs (Dragon_Warrior_Defines.asm BLK_*, converted from map data by GenBlkConvTbl in Bank00) of this game's
# floor tiles. GetBlockID's result must be below BLK_FFIELD for an NPC to step there. ROOF isn't an NES block.
NES_BLOCK_IDS = {
    'GRASS': 0x00, 'SAND': 0x01, 'HILLS': 0x02, 'BRICK_STAIR_UP': 0x03, 'BRICK': 0x04, 'BRICK_STAIR_DOWN': 0x05,
    'GRASS_STAIR_DOWN': 0x05, 'MARSH': 0x06, 'TOWN': 0x07, 'CAVE': 0x08, 'CASTLE': 0x09, 'BRIDGE': 0x0A,
    'TREES': 0x0B, 'TREASURE_BOX': 0x0C, 'BARRIER': 0x0D, 'WOOD': 0x0E, 'WATER': 0x0F, 'WALL': 0x10, 'DOOR': 0x11,
    'MOUNTAINS': 0x12, 'WEAPON_SIGN': 0x13, 'INN_SIGN': 0x14,
    **{coast: 0x18 for coast in ('BOTTOM_COAST', 'BOTTOM_LEFT_COAST', 'LEFT_COAST', 'TOP_LEFT_COAST', 'TOP_COAST',
                                 'TOP_RIGHT_COAST', 'RIGHT_COAST', 'BOTTOM_RIGHT_COAST', 'BOTTOM_TOP_LEFT_COAST',
                                 'BOTTOM_TOP_RIGHT_COAST')},
}
BLK_FFIELD = 0x0D

# Every town or castle with NPCs, with the NES map size (MapDatTbl, Bank00: MapWidth + 1, MapHeight + 1) and where
# NES (0, 0) is in the layout. These match the offsets in tests/test_map_connectivity.py and in src/maps.py.
NES_TOWNS = {
    'TantegelThroneRoom': ((6, 10), (10, 10)),
    'TantegelCourtyard': ((7, 7), (30, 30)),
    'Brecconary': ((8, 10), (30, 30)),
    'Garinham': ((1, 9), (20, 20)),
    'Kol': ((8, 10), (24, 24)),
    'Cantlin': ((8, 1), (30, 30)),
    'Rimuldar': ((8, 8), (30, 30)),
}
ROUNDS = 1000


def nes_walkable(tile: str) -> bool:
    return NES_BLOCK_IDS.get(tile, BLK_FFIELD) < BLK_FFIELD


class TestRoamingNPCMovement(TestCase):

    @classmethod
    def setUpClass(cls):
        # pygame isn't quit afterwards: later test modules (e.g. test_player) rely on the display staying up
        pygame.init()
        pygame.display.set_mode((800, 600))

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.tile_size = self.game.tile_size

    def load(self, map_name: str, dragonlord_defeated: bool = False):
        self.game.story_flags.dragonlord_defeated = dragonlord_defeated
        next_map = map_lookup[map_name](self.game.config)
        self.game.change_map(next_map, destination_coordinates=next_map.initial_coordinates)
        return self.game.current_map

    def place(self, character, row: int, column: int, direction: Direction | None = None) -> None:
        character.row, character.column = row, column
        character.rect.x, character.rect.y = column * self.tile_size, row * self.tile_size
        if direction is not None:
            character.direction_value = direction.value

    def nes(self, current_map, x: int, y: int) -> tuple[int, int]:
        """The layout (row, column) of NES (x, y)."""
        return y + current_map.nes_origin[0], x + current_map.nes_origin[1]

    def roaming(self, current_map, identifier: str):
        return next(npc for npc in current_map.roaming_characters if npc.identifier == identifier)

    def tile(self, current_map, row: int, column: int) -> str:
        return current_map.get_tile_by_value(current_map.layout[row][column])

    def may_step(self, npc, direction: Direction) -> bool:
        """Whether the game starts a step for a roaming NPC facing this way (then undoes it)."""
        npc.direction_value = direction.value
        npc.step_origin = npc.step_destination = None
        x, y = npc.rect.x, npc.rect.y
        if direction in (Direction.UP, Direction.DOWN):
            self.game.movement.move_medially(npc)
        else:
            self.game.movement.move_laterally(npc)
        moved = (npc.rect.x, npc.rect.y) != (x, y)
        npc.rect.x, npc.rect.y = x, y
        npc.step_origin = npc.step_destination = None
        return moved

    # The NES map area

    def test_nes_map_areas(self):
        for map_name, (origin, size) in NES_TOWNS.items():
            current_map = map_lookup[map_name](self.game.config)
            with self.subTest(map_name):
                self.assertEqual((origin, size), (current_map.nes_origin, current_map.nes_size))
                self.assertTrue(all(current_map.in_nes_map(row, column)
                                    for row, column in current_map.npc_coordinates))

    def test_npcs_cannot_step_out_of_the_nes_map(self):
        # NES ChkNPCMapLimit. The layouts pad the NES maps (Cantlin has eight rows of open brick above it), so a step
        # off the NES map's edge is often onto a tile an NPC could otherwise walk on.
        for map_name in NES_TOWNS:
            current_map = self.load(map_name)
            npc = current_map.roaming_characters[0] if current_map.roaming_characters else None
            self.place(self.game.player, 0, 0)
            current_map.fixed_characters, current_map.roaming_characters = [], [npc] if npc else []
            (origin_row, origin_column), (columns, rows) = current_map.nes_origin, current_map.nes_size
            edges = [((origin_row, origin_column + x), Direction.UP) for x in range(columns)]
            edges += [((origin_row + rows - 1, origin_column + x), Direction.DOWN) for x in range(columns)]
            edges += [((origin_row + y, origin_column), Direction.LEFT) for y in range(rows)]
            edges += [((origin_row + y, origin_column + columns - 1), Direction.RIGHT) for y in range(rows)]
            for (row, column), direction in edges:
                with self.subTest(map_name, row=row, column=column, direction=direction.name):
                    self.assertFalse(npc_may_step_onto(current_map, step(row, column, direction.value)))
                    if npc is not None:
                        self.place(npc, row, column)
                        self.assertFalse(self.may_step(npc, direction))

    def test_cantlin_guard_cannot_leave_through_the_padding(self):
        cantlin = self.load('Cantlin')
        guard = self.roaming(cantlin, 'GUARD')  # the mobile guard at NES 5,6 (CantMobTbl)
        self.place(guard, *self.nes(cantlin, 5, 0))
        self.assertEqual('BRICK', self.tile(cantlin, *step(guard.row, guard.column, Direction.UP.value)))
        self.assertFalse(self.may_step(guard, Direction.UP))
        self.assertTrue(self.may_step(guard, Direction.DOWN))

    # Tiles

    def test_tiles_npcs_may_step_on(self):
        # NES GetBlockID: block IDs below BLK_FFIELD. Stairs, chests, trees and swamp are fine; force fields, counters
        # (large tiles), water, stone, doors, mountains and shop signs aren't.
        cantlin = self.load('Cantlin')
        npc = self.roaming(cantlin, 'GUARD')
        start = self.nes(cantlin, 5, 9)
        target = step(*start, Direction.RIGHT.value)
        self.place(npc, *start, Direction.RIGHT)
        cantlin.layout = [list(row) for row in cantlin.layout]
        for tile, tile_dict in cantlin.floor_tile_key.items():
            cantlin.layout[target[0]][target[1]] = tile_dict['val']
            with self.subTest(tile):
                self.assertEqual(nes_walkable(tile), npc_may_step_onto(cantlin, target))

    def test_opened_doors_and_taken_chests_are_brick(self):
        # NES GetBlockID returns BLK_BRICK for a door in DoorXPos or a chest in TrsrXPos; here the layout changes
        cantlin = self.load('Cantlin')
        npc = self.roaming(cantlin, 'GUARD')
        start = self.nes(cantlin, 5, 9)
        target = step(*start, Direction.RIGHT.value)
        self.place(npc, *start, Direction.RIGHT)
        cantlin.layout = [list(row) for row in cantlin.layout]
        cantlin.layout[target[0]][target[1]] = cantlin.floor_tile_key['DOOR']['val']
        self.assertFalse(npc_may_step_onto(cantlin, target))
        cantlin.layout[target[0]][target[1]] = cantlin.floor_tile_key['BRICK']['val']
        self.assertTrue(npc_may_step_onto(cantlin, target))

    # The player and other NPCs

    def test_npcs_cannot_step_onto_the_player(self):
        # NES: not onto CharXPos/CharYPos, nor onto _CharXPos/_CharYPos, where the player is moving
        cantlin = self.load('Cantlin')
        guard = self.roaming(cantlin, 'GUARD')
        self.place(guard, *self.nes(cantlin, 5, 9))
        self.place(self.game.player, *self.nes(cantlin, 6, 9))
        self.assertFalse(self.may_step(guard, Direction.RIGHT))
        self.place(self.game.player, *self.nes(cantlin, 7, 9), Direction.LEFT)
        self.assertTrue(self.may_step(guard, Direction.RIGHT))
        self.game.player.step_destination = self.nes(cantlin, 6, 9)
        self.assertFalse(self.may_step(guard, Direction.RIGHT))
        self.game.player.step_destination = None

    def test_npcs_cannot_step_onto_other_npcs(self):
        # NES NPCCollideLoop checks all 20 NPCs, static or mobile
        cantlin = self.load('Cantlin')
        guard, guard_2 = self.roaming(cantlin, 'GUARD'), self.roaming(cantlin, 'GUARD_2')
        static_guard = cantlin.characters['GUARD_4']['character']  # the static guard at NES 24,12
        self.assertNotIn(static_guard, cantlin.roaming_characters)
        self.place(guard, *step(static_guard.row, static_guard.column, Direction.LEFT.value))
        self.assertFalse(self.may_step(guard, Direction.RIGHT))
        self.place(guard, *self.nes(cantlin, 5, 9))
        self.place(guard_2, *self.nes(cantlin, 6, 9))
        self.assertFalse(self.may_step(guard, Direction.RIGHT))
        # Nor onto the tile another NPC is walking onto
        self.place(guard_2, *self.nes(cantlin, 6, 10), Direction.UP)
        guard_2.step_destination = self.nes(cantlin, 6, 9)
        self.assertFalse(self.may_step(guard, Direction.RIGHT))
        guard_2.step_destination = None
        self.assertTrue(self.may_step(guard, Direction.RIGHT))

    # No leash

    def test_npcs_are_not_kept_near_where_they_started(self):
        cantlin = self.load('Cantlin')
        guard = self.roaming(cantlin, 'GUARD')  # starts at NES 5,6
        self.place(guard, *self.nes(cantlin, 20, 9))
        self.assertTrue(self.may_step(guard, Direction.UP))

    # Simulation

    def simulate(self, current_map, seed: int) -> int:
        """Run the game's own NPC movement for ROUNDS cycles of the NPC schedule, a turn at a time, checking every step
        against the NES rules. Returns the number of steps taken."""
        rng = random.Random(seed)
        npcs = current_map.roaming_characters
        player = self.game.player
        # The game loop keeps the player's row and column up to date; the player stands still here
        self.place(player, player.rect.y // self.tile_size, player.rect.x // self.tile_size)
        player_tile = (player.row, player.column)
        steps = 0
        with patch('src.movement.random', rng):
            for _ in range(ROUNDS * TURNS_PER_CYCLE):
                before = {npc: (npc.row, npc.column) for npc in npcs}
                taken = set(before.values()) | {(npc.row, npc.column) for npc in current_map.fixed_characters}
                # One turn of the NPC schedule (#289): one pair steps at once, and ends the turn back on a tile.
                # ROUNDS cycles of turns give each NPC ROUNDS chances to step.
                for _ in range(FRAMES_PER_TURN):
                    self.game.movement.do_sprites()
                for npc in npcs:
                    position = (npc.row, npc.column)
                    self.assertFalse(npc.is_moving, npc.identifier)
                    self.assertEqual(position, (npc.rect.y // self.tile_size, npc.rect.x // self.tile_size))
                    self.assertTrue(current_map.in_nes_map(*position), (npc.identifier, position))
                    if position == before[npc]:
                        continue
                    steps += 1
                    self.assertEqual(1, abs(position[0] - before[npc][0]) + abs(position[1] - before[npc][1]))
                    self.assertTrue(nes_walkable(self.tile(current_map, *position)), (npc.identifier, position))
                    self.assertNotIn(position, taken - {before[npc]}, npc.identifier)
                    self.assertNotEqual(player_tile, position, npc.identifier)
                positions = [(npc.row, npc.column) for npc in npcs]
                self.assertEqual(len(positions), len(set(positions)))
        return steps

    def test_simulated_npcs_stay_where_the_nes_lets_them(self):
        towns = [(name, False) for name in NES_TOWNS] + [('TantegelCourtyard', True)]
        for seed, (map_name, dragonlord_defeated) in enumerate(towns):
            current_map = self.load(map_name, dragonlord_defeated)
            if not current_map.roaming_characters:
                continue
            with self.subTest(map_name, dragonlord_defeated=dragonlord_defeated):
                steps = self.simulate(current_map, seed)
                # NPCs that could never move would pass trivially
                self.assertGreater(steps, ROUNDS * len(current_map.roaming_characters) // 10)
