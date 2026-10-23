"""
Decode the NES map data (tests/nes_map_data.py) into this game's tile names, placed where this game's layouts have them.

NES references (nmikstas disassembly, Bank00):
- MapDatTbl: each map's data, size, and boundary block (shown outside the map).
- GetBlockID: town maps (below MAP_TANTCSTL_SL) use all 4 bits of a block's nibble. The Tantegel sublevel, the Staff of
  Rain cave, the Rainbow Drop cave and every dungeon use only the low 3 bits; the high bit is covered-area data for the
  towns. The three caves use the town part of GenBlkConvTbl. The dungeons (MAP_DLCSTL_SL1 and up, MapType MAP_DUNGEON)
  use the dungeon part.
- WrldMapPtrTbl, Row000-Row119 and WrldBlkConvTbl: the overworld, run-length encoded (FindMapBlkLoop).
- NPCMobPtrTbl and NPCStatPtrTbl: each town's and castle's mobile and static NPC tables (GetNPCDataPointer).

Regenerate tests/nes_map_data.py with reference/reference_utility_scripts/extract_nes_map_data.py.
"""
from tests.nes_map_data import BOUNDARY_BLOCKS, MAPS, NPC_TABLES, OVERWORLD_ROWS

MAP_OVERWORLD = 0x01
MAP_TANTCSTL_SL = 0x0C
MAP_DLCSTL_SL1 = 0x0F
OVERWORLD_SIZE = 120

# GenBlkConvTbl, town block conversions, as this game's tiles. NES stone is WALL here, and large tiles (counters) are
# WOOD.
TOWN_BLOCKS = ('GRASS', 'SAND', 'WATER', 'TREASURE_BOX', 'WALL', 'BRICK_STAIR_UP', 'BRICK', 'BRICK_STAIR_DOWN',
               'TREES', 'MARSH', 'BARRIER', 'DOOR', 'WEAPON_SIGN', 'INN_SIGN', 'BRIDGE', 'WOOD')
# GenBlkConvTbl, dungeon block conversions. Only the Swamp Cave uses Gwaelin's block, and no map uses Blank.
DUNGEON_BLOCKS = ('WALL', 'BRICK_STAIR_UP', 'BRICK', 'BRICK_STAIR_DOWN', 'TREASURE_BOX', 'DOOR', 'PRINCESS_GWAELIN',
                  'BLANK')
# WrldBlkConvTbl
OVERWORLD_BLOCKS = ('GRASS', 'SAND', 'HILLS', 'MOUNTAINS', 'WATER', 'WALL', 'TREES', 'MARSH', 'TOWN', 'CAVE', 'CASTLE',
                    'BRIDGE', 'GRASS_STAIR_DOWN')
# The block IDs used as MapDatTbl boundary blocks (BLK_GRASS, BLK_SAND, BLK_BRICK, BLK_SWAMP, BLK_TREES, BLK_WATER,
# BLK_STONE and BLK_SML_TILES, the small tiles that cover roofs, which is ROOF here)
BOUNDARY_TILES = {0x00: 'GRASS', 0x01: 'SAND', 0x04: 'BRICK', 0x06: 'MARSH', 0x0B: 'TREES', 0x0F: 'WATER', 0x10: 'WALL',
                  0x15: 'ROOF'}

# (NES map number, NES map name, this game's map, (row, column) here of NES (0, 0), the NES rows this game's map holds).
# An NES (x, y) is at (y + row offset, x + column offset) here. The Dragonlord's castle sublevel 6 is two maps here: the
# corridor at y = 0 and the one at y = 6 (rows 1 to 3 are solid stone).
NES_MAPS = (
    (0x01, 'OVERWORLD', 'Alefgard', (7, 8), None),
    (0x02, 'DLCSTL_GF', 'CharlockB1', (6, 7), None),
    (0x03, 'HAUKSNESS', 'Hauksness', (8, 9), None),
    (0x04, 'TANTCSTL_GF', 'TantegelCourtyard', (7, 7), None),
    (0x05, 'THRONEROOM', 'TantegelThroneRoom', (6, 10), None),
    (0x06, 'DLCSTL_BF', 'CharlockB8', (4, 6), None),
    (0x07, 'KOL', 'Kol', (8, 10), None),
    (0x08, 'BRECCONARY', 'Brecconary', (8, 10), None),
    (0x09, 'GARINHAM', 'Garinham', (1, 9), None),
    (0x0A, 'CANTLIN', 'Cantlin', (8, 1), None),
    (0x0B, 'RIMULDAR', 'Rimuldar', (8, 8), None),
    (0x0C, 'TANTCSTL_SL', 'TantegelCellar', (1, 1), None),
    (0x0D, 'RAIN', 'StaffOfRainCave', (2, 2), None),
    (0x0E, 'RAINBOW', 'MagicTemple', (2, 2), None),
    (0x0F, 'DLCSTL_SL1', 'CharlockB2', (3, 3), None),
    (0x10, 'DLCSTL_SL2', 'CharlockB3', (3, 3), None),
    (0x11, 'DLCSTL_SL3', 'CharlockB4', (3, 3), None),
    (0x12, 'DLCSTL_SL4', 'CharlockB5', (3, 3), None),
    (0x13, 'DLCSTL_SL5', 'CharlockB6', (3, 3), None),
    (0x14, 'DLCSTL_SL6', 'CharlockB7Narrow', (3, 3), range(0, 4)),
    (0x14, 'DLCSTL_SL6', 'CharlockB7Wide', (-1, 3), range(4, 10)),
    (0x15, 'SWAMPCAVE', 'SwampCave', (6, 4), None),
    (0x16, 'RCKMTN_B1', 'MountainCaveB1', (1, 1), None),
    (0x17, 'RCKMTN_B2', 'MountainCaveB2', (1, 1), None),
    (0x18, 'CVGAR_B1', 'GarinsGraveB1', (1, 1), None),
    (0x19, 'CVGAR_B2', 'GarinsGraveB2', (1, 1), None),
    (0x1A, 'CVGAR_B3', 'GarinsGraveB3', (1, 1), None),
    (0x1B, 'CVGAR_B4', 'GarinsGraveB4', (1, 1), None),
    (0x1C, 'ERDRCK_B1', 'ErdricksCaveB1', (3, 3), None),
    (0x1D, 'ERDRCK_B2', 'ErdricksCaveB2', (1, 1), None),
)


def decode_overworld() -> list[list[str]]:
    """The overworld as rows of tile names, indexed [y][x] (FindMapBlkLoop, WrldBlkConvTbl)."""
    rows = []
    for row_hex in OVERWORLD_ROWS:
        tiles: list[str] = []
        for i in range(0, len(row_hex), 2):
            value = int(row_hex[i:i + 2], 16)
            tiles += [OVERWORLD_BLOCKS[value >> 4]] * ((value & 0x0F) + 1)
        rows.append(tiles[:OVERWORLD_SIZE])  # Row011's last run is 2 blocks too long
    return rows


def decode_map(map_number: int) -> list[list[str]]:
    """An NES map as rows of tile names, indexed [y][x] (GetBlockID, GenBlkConvTbl)."""
    if map_number == MAP_OVERWORLD:
        return decode_overworld()
    _label, _columns, _rows, rows = MAPS[map_number]
    if map_number >= MAP_DLCSTL_SL1:
        return [[DUNGEON_BLOCKS[int(nibble, 16) & 0x07] for nibble in row] for row in rows]
    mask = 0x07 if map_number >= MAP_TANTCSTL_SL else 0x0F
    return [[TOWN_BLOCKS[int(nibble, 16) & mask] for nibble in row] for row in rows]


# GenBlkConvTbl, overworld water block conversions (BLK_WATER, BLK_WTR_T .. BLK_WTR_TLRB), as this game's tiles, indexed
# by the shores: top 1, left 2, right 4, bottom 8. The left, right and bottom and the all-sides shores are never used.
SHORE_BLOCKS = ('WATER', 'TOP_COAST', 'LEFT_COAST', 'TOP_LEFT_COAST', 'RIGHT_COAST', 'TOP_RIGHT_COAST', 'LEFT_RIGHT_COAST',
                'TOP_LEFT_RIGHT_COAST', 'BOTTOM_COAST', 'BOTTOM_TOP_COAST', 'BOTTOM_LEFT_COAST', 'BOTTOM_TOP_LEFT_COAST',
                'BOTTOM_RIGHT_COAST', 'BOTTOM_TOP_RIGHT_COAST', None, None)
SHORE_TOP, SHORE_LEFT, SHORE_RIGHT, SHORE_BOTTOM = 1, 2, 4, 8


def overworld_water_block(overworld: list[list[str]], x: int, y: int) -> str:
    """The water block the NES draws at overworld (x, y), with its shores: a shore on each side with land next to it.

    DoWtrConv (Bank00, $AB24) for a water block in the map: water and bridges aren't land (ChkWtrOrBrdg), and the
    map's edges count as water. TrgtOutOfBounds ($AB77) outside it: the boundary block is water, and the blocks just
    past an edge, beside the map, get a shore on the side that faces land."""
    def is_land(land_x: int, land_y: int) -> bool:
        inside = 0 <= land_x < OVERWORLD_SIZE and 0 <= land_y < OVERWORLD_SIZE
        return inside and overworld[land_y][land_x] not in ('WATER', 'BRIDGE')

    inside = 0 <= x < OVERWORLD_SIZE and 0 <= y < OVERWORLD_SIZE
    beside_the_map = 0 <= x < OVERWORLD_SIZE or 0 <= y < OVERWORLD_SIZE
    shores = 0
    if inside or beside_the_map:
        for side, (dx, dy) in ((SHORE_TOP, (0, -1)), (SHORE_LEFT, (-1, 0)), (SHORE_RIGHT, (1, 0)),
                               (SHORE_BOTTOM, (0, 1))):
            if is_land(x + dx, y + dy):
                shores |= side
    return SHORE_BLOCKS[shores]


def boundary_tile(map_number: int) -> str:
    return BOUNDARY_TILES[BOUNDARY_BLOCKS[map_number]]


def nes_tiles(map_number: int, offset: tuple, nes_rows=None) -> dict:
    """{(row, column) here: NES tile name} for an NES map, or for the rows of it that one of this game's maps holds."""
    row_offset, column_offset = offset
    tiles = {}
    for y, row in enumerate(decode_map(map_number)):
        if nes_rows is None or y in nes_rows:
            for x, tile in enumerate(row):
                tiles[(y + row_offset, x + column_offset)] = tile
    return tiles


def layout_location(map_name: str, x: int, y: int) -> tuple:
    """Where NES (x, y) is in one of this game's maps, as (row, column)."""
    for _number, _nes_name, name, (row_offset, column_offset), nes_rows in NES_MAPS:
        if name == map_name and (nes_rows is None or y in nes_rows):
            return y + row_offset, x + column_offset
    raise KeyError((map_name, x, y))


# The NES NPC tables of this game's maps: map name (with _DL for after the Dragonlord's defeat, when GetNPCDataPointer
# loads TaDLMobTbl and TaDLStatTbl on the ground floor) -> the tables' name prefix (ThRmMobTbl, ThRmStatTbl, ...)
NPC_TABLE_PREFIXES = {
    'TantegelThroneRoom': 'ThRm',
    'TantegelCourtyard': 'Tant',
    'TantegelCourtyard_DL': 'TaDL',
    'TantegelCellar': 'TaSL',
    'CharlockB8': 'DLBF',
    'StaffOfRainCave': 'Rain',
    'MagicTemple': 'Rnbw',
    'Brecconary': 'Brec',
    'Garinham': 'Gar',
    'Kol': 'Kol',
    'Rimuldar': 'Rim',
    'Cantlin': 'Cant',
}
# The NNN bits of an NPC table entry, as this game's sprites (NES fighters are SOLDIER here, and stationary guards and
# guards with trumpets are GUARD)
NPC_GRAPHICS = ('MAN', 'SOLDIER', 'GUARD', 'MERCHANT', 'KING_LORIK', 'WISE_MAN', 'WOMAN', 'GUARD')
# The DD bits
NPC_DIRECTIONS = ('UP', 'RIGHT', 'DOWN', 'LEFT')


def npc_sprite(table: str, graphic: int, dialog: int) -> str:
    """This game's sprite for an NPC table entry. Graphic 5 with dialog byte $70 is the Dragonlord and graphic 6 with
    $6F is Gwaelin, not a wizard and a female villager. After the Dragonlord's defeat the ground floor's wizards and
    trumpet guards are all guards (NES GetGuardType; there's no trumpet sprite here)."""
    if graphic == 5 and dialog == 0x70:
        return 'DRAGONLORD'
    if graphic == 6 and dialog == 0x6F:
        return 'PRINCESS_GWAELIN'
    if table == 'TaDLStatTbl' and graphic in (5, 7):
        return 'GUARD'
    return NPC_GRAPHICS[graphic]


def nes_npcs(map_name: str) -> list[tuple[str, int, int, int, bool, str]]:
    """A map's NES NPCs in table order (the mobile table, then the static one), as (sprite, x, y, dialog byte, mobile,
    facing). map_name is a key of NPC_TABLE_PREFIXES."""
    prefix = NPC_TABLE_PREFIXES[map_name]
    return [(npc_sprite(table, graphic, dialog), x, y, dialog, mobile, NPC_DIRECTIONS[direction])
            for table, mobile in ((f'{prefix}MobTbl', True), (f'{prefix}StatTbl', False))
            for graphic, x, y, direction, dialog in NPC_TABLES[table]]
