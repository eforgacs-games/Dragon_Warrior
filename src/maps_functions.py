from collections.abc import Iterable

from pygame import PixelArray, mask, surface
from pygame.transform import scale

from src.color import BLACK, LOW_HP_RED
from src.coordinates import Cell, Pixel
from src.visual_effects import NES_PALETTE

# NES AddPalByte/ChkLowHPPal (Bank03, $C661): while HP is low, background palette 0's color 1 ($3F01) is loaded as $26
# instead of the $30 that OverworldPal, TownPal and DungeonPal (Bank00) all give it.
PAL0_COLOR1_NORMAL = NES_PALETTE[0x30]
PAL0_COLOR1_LOW_HP = LOW_HP_RED  # $26, the windows' low HP color too


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


def tile_from_quarters(top_left: surface.Surface, top_right: surface.Surface, bottom_left: surface.Surface,
                       bottom_right: surface.Surface) -> surface.Surface:
    """A tile made of the matching quarter of each of four tiles (the NES draws a block as four 8x8 tiles)."""
    width, height = top_left.get_size()
    half_width, half_height = width // 2, height // 2
    tile = surface.Surface((width, height), top_left.get_flags(), top_left)
    for source, (x, y) in ((top_left, (0, 0)), (top_right, (half_width, 0)), (bottom_left, (0, half_height)),
                           (bottom_right, (half_width, half_height))):
        tile.blit(source, (x, y), (x, y, half_width, half_height))
    return tile


def bad_ending_tile_image(tile: surface.Surface, palette_0_tile: bool, window_color) -> surface.Surface:
    """A tile under NES BadEndBGPal (Bank00, $9AA3: $16 then eleven $0E), the background palettes ChooseDrgnLrd loads
    for the bad ending: background palette 0's color 1 is the window color (red, or the low HP red) and every other
    background color is black. So a palette 0 block (LOW_HP_PALETTE_TILES in maps.py) keeps only its color 1 pixels
    ($30 white, see low_hp_tile_image), in the window color, and every other block goes black."""
    image = surface.Surface(tile.get_size())
    image.fill(BLACK)
    if palette_0_tile:
        color_1_pixels = mask.from_threshold(tile, PAL0_COLOR1_NORMAL, (1, 1, 1, 255))
        color_1_pixels.to_surface(image, setcolor=window_color, unsetcolor=None)
    return image


def warp_line(lower_bound, upper_bound) -> list[tuple]:
    assert lower_bound[0] == upper_bound[0] or lower_bound[1] == upper_bound[1]
    if lower_bound[0] != upper_bound[0]:
        return [(min(n, upper_bound[0]), upper_bound[1]) for n in range(lower_bound[0], upper_bound[0] + 1)]
    else:
        return [(upper_bound[0], min(n, upper_bound[1])) for n in range(lower_bound[1], upper_bound[1] + 1)]


def parse_animated_sprite_sheet(sheet: surface.Surface, config: dict) -> tuple[list, list, list, list]:
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


def get_center_point(x: int, y: int, tile_size: int) -> Pixel:
    """The pixel center of the block in column x, row y."""
    offset = tile_size // 2
    return (x * tile_size) + offset, (y * tile_size) + offset


def covered_cells(nes_rows: dict[int, Iterable[int]], row_offset: int, column_offset: int) -> frozenset[Cell]:
    """
    Converts a town's NES covered-area data into the (row, column) cells of this project's layout.
    :param nes_rows: NES map Y -> the NES map X positions whose covered-area nibble has bit 3 set.
    :param row_offset: Layout row of NES map Y 0.
    :param column_offset: Layout column of NES map X 0.
    """
    return frozenset((y + row_offset, x + column_offset) for y, xs in nes_rows.items() for x in xs)
