"""Draw an NES window tile by tile, the way the NES builds it from its window data (Bank01 WndwDataPtrTbl and the
window routines after it), instead of from a screenshot.

A window is a grid of 8x8 NES tiles, 2 per block each way (src/windows.py): its border tiles, its text (one font
tile per character) and the cursor tile (src/cursor.py), all background tiles in palette 0, so everything that isn't
black is drawn in the window color, which turns red at low HP (src/color.py window_color).

The border tiles' patterns are in the CHR ROM, which the disassembly doesn't include; they are copied here from the
NES screenshots in data/images (as CURSOR_TILE is), pixel for pixel. The letters are the NES font tiles, from
data/fonts/dragon-quest.ttf: rendered at 8 pixels without antialiasing, every character is exactly the NES tile (8
pixels wide, its 8 rows from the second row of the rendered line), so a tile is that render scaled up, never the
font rendered at a bigger size. Except for four letters: the font's j, k, p and t are not the NES ones, so their NES
tiles are in NES_GLYPHS, copied from the screenshots (the name entry alphabet, and the shop windows' "Copper" and
"Plate", agree pixel for pixel); and the NES apostrophe is the font's ’, not its ' (which is the apostrophe of 'tis,
ELISION_APOSTROPHE). src/text.py's NESFont draws them
the same way in all other text (dialog, draw_text).
"""
from functools import cache, lru_cache

from pygame import Rect, Surface, font

from src.color import BLACK
from src.cursor import draw_cursor_tile
from src.paths import data_path
from src.windows import WindowLayout

NES_TILE = 8
# A tile's 8 rows of 8 pixels: '#' is drawn in the window color, '.' is black
Pattern = tuple[str, ...]
DRAGON_QUEST_FONT_PATH = data_path('fonts', 'dragon-quest.ttf')

# The apostrophe of 'tis (TB7E2, TB7E6, TB8E6, TB9E2, TB9E15) is its own NES font tile, $54, not the apostrophe of
# "Erdrick's" ($53, like TXT_APOS $40) nor the comma ($48); the disassembly's text comments write it as a comma
# (",Tis said ..."). It is the comma shape raised to the top of the tile, like the apostrophe, but at the tile's right
# edge, against the letter after it, where the apostrophe ($53, the font's ’) is at the left edge, against the letter
# before it. The font's ' is that tile, so the game's text writes this apostrophe as ʼ (U+02BC, MODIFIER LETTER
# APOSTROPHE) and it is drawn with the font's '.
ELISION_APOSTROPHE = 'ʼ'


def font_characters(text: str) -> str:
    """text in the characters dragon-quest.ttf draws its NES tiles with: the apostrophe is the font's ’ (the font's '
    is the 'tis apostrophe, ELISION_APOSTROPHE)."""
    return text.replace("'", '’').replace(ELISION_APOSTROPHE, "'")

# The window border tiles (Defines TL_LEFT $61 to TL_BOT_RIGHT $69): '#' is drawn in the window color.
TL_UPPER_LEFT: Pattern = (
    "........",
    "..######",
    ".#######",
    ".###....",
    ".##.....",
    ".##.....",
    ".##.....",
    ".##.....",
)
TL_TOP1: Pattern = (
    "........",
    "########",
    "########",
    "........",
    "........",
    "........",
    "........",
    "........",
)
# The top border tile just before text in the top border (a title): it stops one pixel short, so the border doesn't
# touch the text (BuildWndLine replaces a TL_TOP1 followed by a character with TL_TOP2).
TL_TOP2: Pattern = (
    "........",
    "#######.",
    "#######.",
    "........",
    "........",
    "........",
    "........",
    "........",
)
TL_UPPER_RIGHT: Pattern = (
    "........",
    "######..",
    "#######.",
    "....###.",
    ".....##.",
    ".....##.",
    ".....##.",
    ".....##.",
)
TL_LEFT: Pattern = (".##.....",) * NES_TILE
TL_RIGHT: Pattern = (".....##.",) * NES_TILE
TL_BOT_LEFT: Pattern = (
    ".##.....",
    ".##.....",
    ".##.....",
    ".##.....",
    ".###....",
    ".#######",
    "..######",
    "........",
)
TL_BOTTOM: Pattern = (
    "........",
    "........",
    "........",
    "........",
    "........",
    "########",
    "########",
    "........",
)
TL_BOT_RIGHT: Pattern = (
    ".....##.",
    ".....##.",
    ".....##.",
    ".....##.",
    "....###.",
    "#######.",
    "######..",
    "........",
)
# TL_BLANK_TILE1 ($5F)
TL_BLANK: Pattern = ("........",) * NES_TILE

# Tile $41, the 8 placeholders of an empty name (NameEntryDat)
TL_NAME_PLACEHOLDER: Pattern = (
    "........",
    "...#....",
    "#..#..#.",
    ".#.#.#..",
    "..###...",
    ".#.#.#..",
    "#..#..#.",
    "...#....",
)


# The NES letters that dragon-quest.ttf draws differently (see the module docstring)
NES_GLYPHS: dict[str, Pattern] = {
    'j': (
        "....###.",
        "....###.",
        "........",
        "....###.",
        "##..###.",
        "##..###.",
        ".#####..",
        "........",
    ),
    'k': (
        ".##.....",
        ".##..##.",
        ".##.##..",
        ".####...",
        ".#####..",
        ".##..##.",
        ".##..##.",
        "........",
    ),
    'p': (
        "........",
        ".#####..",
        ".##..##.",
        ".##..##.",
        ".##..##.",
        ".#####..",
        ".##.....",
        ".##.....",
    ),
    't': (
        ".##.....",
        ".##.....",
        "######..",
        ".##.....",
        ".##..##.",
        ".##..##.",
        "..####..",
        "........",
    ),
}


@cache
def glyph_tile(character: str) -> Pattern:
    """A character's NES font tile, as a pattern like the border tiles."""
    if character in NES_GLYPHS:
        return NES_GLYPHS[character]
    character = font_characters(character)
    if not font.get_init():
        font.init()
    rendered = font.Font(DRAGON_QUEST_FONT_PATH, NES_TILE).render(character, False, (255, 255, 255), BLACK)
    if rendered.get_width() != NES_TILE:
        raise ValueError(f"{character!r} is not one NES font tile")
    # The font's line is 10 pixels high: a blank row, the 8 rows of the tile, a blank row
    return tuple(''.join('#' if rendered.get_at((x, y + 1))[0] else '.' for x in range(NES_TILE))
                 for y in range(NES_TILE))


def window_tiles(layout: WindowLayout) -> list[list[Pattern]]:
    """The window's tiles, row by row: its border, its title in the top border and its text, the way the NES window
    routines fill a window (top border TL_TOP1, TL_TOP2 before a title; blank tiles TL_BLANK_TILE1 inside)."""
    columns, rows = layout.window.width * 2, layout.window.height * 2
    grid: list[list[Pattern]] = [[TL_LEFT] + [TL_BLANK] * (columns - 2) + [TL_RIGHT] for _ in range(rows)]
    grid[0] = [TL_UPPER_LEFT] + [TL_TOP1] * (columns - 2) + [TL_UPPER_RIGHT]
    grid[-1] = [TL_BOT_LEFT] + [TL_BOTTOM] * (columns - 2) + [TL_BOT_RIGHT]
    texts = ((layout.title,) if layout.title else ()) + layout.texts
    for text in texts:
        # Text can be in the top border (a title), but not in the bottom border or the left and right borders
        if not (0 <= text.row < rows - 1 and 1 <= text.column and text.column + len(text.text) <= columns - 1):
            raise ValueError(f"{text} is not inside the window")
        for offset, character in enumerate(text.text):
            column = text.column + offset
            # BuildWndLine: a character after a TL_TOP1 tile (not the first column) turns that tile into TL_TOP2
            if text.row == 0 and grid[0][column - 1] is TL_TOP1:
                grid[0][column - 1] = TL_TOP2
            grid[text.row][column] = glyph_tile(character)
    return grid


@cache
def tile_surface(pattern: Pattern, color: tuple, nes_pixel: int) -> Surface:
    """A tile drawn in color on black, nes_pixel screen pixels per NES pixel."""
    surface = Surface((NES_TILE * nes_pixel, NES_TILE * nes_pixel))
    surface.fill(BLACK)
    for y, line in enumerate(pattern):
        for x, pixel in enumerate(line):
            if pixel == '#':
                surface.fill(color, (x * nes_pixel, y * nes_pixel, nes_pixel, nes_pixel))
    return surface


@lru_cache(maxsize=256)
def render_window(layout: WindowLayout, color: tuple, nes_pixel: int, cursor_index: int | None = None,
                  cursor_visible: bool = True) -> Surface:
    """
    The window as the NES draws it. The surface is cached: blit it, don't draw on it.
    :param layout: The window's data (src/windows.py).
    :param color: The window color (Game.color).
    :param nes_pixel: Screen pixels per NES pixel (SCALE; TILE_SIZE // 16).
    :param cursor_index: The selected entry (an index into layout.cursor_tiles), or None for no cursor at all.
    :param cursor_visible: Whether the cursor is in the "on" half of its blink (src/cursor.py); if not, its tile is
    blank.
    :return: The window, (width * 16, height * 16) NES pixels, scaled.
    """
    tile = NES_TILE * nes_pixel
    grid = window_tiles(layout)
    surface = Surface((len(grid[0]) * tile, len(grid) * tile))
    for row, tiles in enumerate(grid):
        for column, pattern in enumerate(tiles):
            surface.blit(tile_surface(pattern, color, nes_pixel), (column * tile, row * tile))
    if cursor_index is not None:
        column, row = layout.cursor_tiles[cursor_index]
        draw_cursor_tile(surface, column * tile, row * tile, nes_pixel, color, cursor_visible)
    return surface


def draw_window(screen: Surface, layout: WindowLayout, color: tuple, config: dict, cursor_index: int | None = None,
                cursor_visible: bool = True) -> Rect:
    """
    Draw a window at its NES position (see render_window for the parameters).
    :param config: The game config: TILE_SIZE, and NO_BLIT (nothing is drawn).
    :return: The window's rect on the screen, for display.update.
    """
    tile_size = config['TILE_SIZE']
    x, y, width, height = layout.window
    rect = Rect(x * tile_size, y * tile_size, width * tile_size, height * tile_size)
    if not config.get('NO_BLIT'):
        screen.blit(render_window(layout, color, tile_size // 16, cursor_index, cursor_visible), rect)
    return rect
