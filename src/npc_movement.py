"""Where a roaming NPC may step, per the NES's NPC movement code.

NES UpdateNPCs1 (Bank00, $B76F) picks a random direction for each mobile NPC (SetNPCDir: RandNumUB AND #$60, so each
direction is equally likely) and turns the NPC to face it. The NPC then takes the step only if every check below
passes; otherwise HaltNPCMoveCalcs stops it, and it stays where it is, facing the new direction, until its next turn:

1. ChkNPCMapLimit: the target is inside the NES map (0 <= x <= MapWidth, 0 <= y <= MapHeight; a step left or up from 0
   wraps to $FF, past the limit). Our layouts pad the NES maps, so this is the NES area, not the layout.
2. The target isn't the player's position (CharXPos, CharYPos) or the player's next position (_CharXPos, _CharYPos).
3. NPCCollideLoop: the target isn't the position of any of the 20 NPCs, mobile or static.
   (MovementController.character_in_path checks 2 and 3, for the player and NPCs alike.)
4. GetBlockID: the target's block ID is below BLK_FFIELD ($0D). GetBlockID returns opened doors and taken chests as
   BLK_BRICK; here those are already BRICK in the layout.
5. HasCoverData/CoveredStsNext: the target is covered (under a roof) exactly when the NPC's current tile is
   (CheckCoveredArea), so NPCs never walk in or out of a covered area. Covered areas aren't modelled here yet.

There is no limit on how far an NPC may wander from where it started. (ChkNPCWndwBlock also stops NPCs that are under
an open window; that's about when NPCs move, not where.)
"""
from src.coordinates import Cell
from src.direction import Direction

# Tiles whose NES block ID is below BLK_FFIELD ($0D): BLK_GRASS, BLK_SAND, BLK_HILL, BLK_STAIR_UP, BLK_BRICK,
# BLK_STAIR_DN, BLK_SWAMP, BLK_TOWN, BLK_CAVE, BLK_CASTLE, BLK_BRIDGE, BLK_TREES and BLK_CHEST. Everything else
# (BLK_FFIELD, BLK_LRG_TILE, water, BLK_STONE, BLK_DOOR, BLK_MOUNTAIN, the shop and inn signs, and so on) blocks NPCs,
# as do this game's own tiles that the NES doesn't have (ROOF).
NPC_WALKABLE_TILES = frozenset({
    'GRASS', 'SAND', 'HILLS', 'BRICK_STAIR_UP', 'GRASS_STAIR_DOWN', 'BRICK', 'BRICK_STAIR_DOWN', 'MARSH', 'TOWN',
    'CAVE', 'CASTLE', 'BRIDGE', 'TREES', 'TREASURE_BOX',
})


def step(row: int, column: int, direction: int, offset: int = 1) -> Cell:
    """The (row, column) `offset` tiles from (row, column) in the given direction."""
    if direction == Direction.UP.value:
        return row - offset, column
    if direction == Direction.DOWN.value:
        return row + offset, column
    if direction == Direction.LEFT.value:
        return row, column - offset
    return row, column + offset


def npc_may_step_onto(current_map, target: Cell) -> bool:
    """Whether an NPC may step onto `target`, a (row, column) in the layout, as far as the map goes (NES UpdateNPCs1
    checks 1 and 4 above)."""
    row, column = target
    if not current_map.in_nes_map(row, column):  # ChkNPCMapLimit
        return False
    return current_map.get_tile_by_value(current_map.layout[row][column]) in NPC_WALKABLE_TILES  # GetBlockID

