from typing import Dict, FrozenSet, Iterable, List, Tuple

from pygame import PixelArray, surface
from pygame.transform import scale

from src.visual_effects import NES_PALETTE

# NES AddPalByte/ChkLowHPPal (Bank03, $C661): while HP is low, background palette 0's color 1 ($3F01) is loaded as $26
# instead of the $30 that OverworldPal, TownPal and DungeonPal (Bank00) all give it.
PAL0_COLOR1_NORMAL = NES_PALETTE[0x30]
PAL0_COLOR1_LOW_HP = NES_PALETTE[0x26]


def parse_map_tiles(map_path: str, tile_size: int, graphics, configured_scale):
    map_sheet = graphics.get_image(map_path).convert()
    map_tile_sheet = scale(map_sheet,
                           (map_sheet.get_width() * configured_scale, map_sheet.get_height() * configured_scale))
    width, height = map_tile_sheet.get_size()
    return [[map_tile_sheet.subsurface((x * tile_size, y * tile_size, tile_size, tile_size)) for y in
             range(0, height // tile_size)]
            for x in range(0, width // tile_size)]


def low_hp_tile_image(tile: surface.Surface) -> surface.Surface:
    """A copy of a background palette 0 tile with its color 1 pixels ($30 white) turned the low HP red ($26).

    Only call this for palette 0 blocks (LOW_HP_PALETTE_TILES in maps.py). In those blocks white can only be color 1:
    palette 0 is $30, $10, $11 (grey and blue are colors 2 and 3), and no other background palette in OverworldPal,
    TownPal or DungeonPal contains $30, so every white pixel in tileset.png is a palette 0 color 1 pixel."""
    red = tile.copy()
    with PixelArray(red) as pixels:
        pixels.replace(PAL0_COLOR1_NORMAL, PAL0_COLOR1_LOW_HP)
    return red


def warp_line(lower_bound, upper_bound) -> List[tuple]:
    assert lower_bound[0] == upper_bound[0] or lower_bound[1] == upper_bound[1]
    if lower_bound[0] != upper_bound[0]:
        return [(min(n, upper_bound[0]), upper_bound[1]) for n in range(lower_bound[0], upper_bound[0] + 1)]
    else:
        return [(upper_bound[0], min(n, upper_bound[1])) for n in range(lower_bound[1], upper_bound[1] + 1)]


def parse_animated_sprite_sheet(sheet: surface.Surface, config: dict) -> Tuple[list, list, list, list]:
    """
    Parses sprite sheets and creates image lists. If is_roaming is True
    the sprite will have four lists of images, one for each direction. If
    is_roaming is False then there will be one list of 2 images.
    """
    sheet.set_colorkey(config['COLOR_KEY'])
    sheet.convert_alpha()

    facing_down, facing_left, facing_up, facing_right = [], [], [], []

    for i in range(0, 2):

        tile_size = config['TILE_SIZE']
        rect = (i * tile_size, 0, tile_size, tile_size)
        facing_down.append(sheet.subsurface(rect))

        is_four_sided = sheet.get_size()[0] % 128 == 0
        if is_four_sided:
            # is_four_sided
            rect = ((i + 2) * tile_size, 0, tile_size, tile_size)
            facing_left.append(sheet.subsurface(rect))

            rect = ((i + 4) * tile_size, 0, tile_size, tile_size)
            facing_up.append(sheet.subsurface(rect))

            rect = ((i + 6) * tile_size, 0, tile_size, tile_size)
            facing_right.append(sheet.subsurface(rect))

    return facing_down, facing_left, facing_up, facing_right


def get_center_point(x, y, tile_size):
    offset = tile_size // 2
    return (x * tile_size) + offset, (y * tile_size) + offset


def covered_cells(nes_rows: Dict[int, Iterable[int]], row_offset: int, column_offset: int) -> FrozenSet[Tuple[int, int]]:
    """
    Converts a town's NES covered-area data into the (row, column) cells of this project's layout.
    :param nes_rows: NES map Y -> the NES map X positions whose covered-area nibble has bit 3 set.
    :param row_offset: Layout row of NES map Y 0.
    :param column_offset: Layout column of NES map X 0.
    """
    return frozenset((y + row_offset, x + column_offset) for y, xs in nes_rows.items() for x in xs)
