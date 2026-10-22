"""The cursor of the NES selection windows (Bank01 WndDoSelect and the routines after it).

Every selection window (the COMMAND windows, SPELL, ITEM, the shops, BUY/SELL, YES/NO, the title menus and the
alphabet) shows the same cursor: the right pointing arrow tile, TL_RIGHT_ARROW ($42), in the tile before the selected
entry (the window data's cursor home X). It is a background tile like the window's text, so it is drawn in the
window color, color 1 of background palette 0, which turns red at low HP (AddPalByte, ChkLowHPPal).

It blinks off the frame counter (UpdateCursorGFX, called every frame by WndGetButtons): the arrow is shown while
FrameCounter AND #$1F is below #$10 and replaced by TL_BLANK_TILE1 while it isn't, so 16 frames on and 16 off.
WndInitSelect sets FrameCounter to 5 when the window opens, and WndUpdateCrsrPos sets it to 5 again whenever the
cursor moves, so a new window or a moved cursor always starts visible, for the 11 frames left of the "on" half.

When A or B is pressed (WndAPressed, WndBPressed), WndUpdateCrsrPos draws the arrow one last time and the selection
loop ends, so nothing redraws that tile any more: the chosen entry's arrow stays on, without blinking, while the
window stays on the screen (behind the windows the selection opens, for example).
"""
from pygame import Rect, Surface

from src.color import BLACK
from src.waiting import NES_FPS, game_ticks as get_ticks  # game time: runs N times as fast at speed N

# TL_RIGHT_ARROW ($42), as the NES draws it: 8x8 pixels, its point 2 pixels in from the tile's left edge and one row
# lower than the letters (which use rows 0 to 6), so it lines up with the middle of the entry's text.
CURSOR_TILE = (
    "........",
    "..#.....",
    "..##....",
    "..###...",
    "..####..",
    "..###...",
    "..##....",
    "..#.....",
)
# UpdateCursorGFX: AND #$1F, CMP #$10
CURSOR_BLINK_MASK = 0x1F
CURSOR_HIDDEN_FROM = 0x10
# WndInitSelect and WndUpdateCrsrPos: LDA #$05, STA FrameCounter
CURSOR_RESET_FRAME = 0x05


def cursor_visible_on_frame(frame_counter: int) -> bool:
    """UpdateCursorGFX: whether the arrow (rather than a blank tile) is drawn on this value of FrameCounter."""
    return frame_counter & CURSOR_BLINK_MASK < CURSOR_HIDDEN_FROM


class BlinkingCursor:
    """A selection window's cursor blink, timed like the NES frame counter (see the module docstring).

    restart() is WndInitSelect/WndUpdateCrsrPos (the window opened, or the cursor moved); hold() is the last
    WndUpdateCrsrPos of WndAPressed/WndBPressed, after which the arrow stays on."""

    def __init__(self, ticks: int | None = None):
        self.start_ticks = 0
        self.held = False
        self.restart(ticks)

    def restart(self, ticks: int | None = None) -> None:
        """FrameCounter = 5: the arrow is on, and stays on for the rest of the 16 frame "on" half (11 frames)."""
        self.start_ticks = get_ticks() if ticks is None else ticks
        self.held = False

    def hold(self) -> None:
        """A or B was pressed: the arrow is drawn and stays on until the window is opened again (restart)."""
        self.held = True

    def frame_counter(self, ticks: int | None = None) -> int:
        """The NES FrameCounter: 5 when the cursor was restarted, plus one per NES frame since (it is one byte)."""
        now = get_ticks() if ticks is None else ticks
        frames = max(0, now - self.start_ticks) * NES_FPS // 1000
        return (CURSOR_RESET_FRAME + int(frames)) & 0xFF

    def visible(self, ticks: int | None = None) -> bool:
        return self.held or cursor_visible_on_frame(self.frame_counter(ticks))


def draw_cursor_tile(screen: Surface, x: float, y: float, nes_pixel: int, color: tuple, visible: bool = True) -> Rect:
    """Draw the cursor's tile, the arrow or (not visible) a blank tile, the way UpdateCursorGFX writes either
    TL_RIGHT_ARROW or TL_BLANK_TILE1 into the window.
    :param screen: Where to draw.
    :param x: The tile's left edge, in screen pixels.
    :param y: The tile's top edge, in screen pixels.
    :param nes_pixel: The size of one NES pixel in screen pixels (SCALE).
    :param color: The window color.
    :param visible: Whether to draw the arrow, or only blank the tile.
    :return: The tile's rect, for display.update.
    """
    tile_rect = Rect(int(x), int(y), 8 * nes_pixel, 8 * nes_pixel)
    screen.fill(BLACK, tile_rect)
    if visible:
        for row, line in enumerate(CURSOR_TILE):
            for column, pixel in enumerate(line):
                if pixel == '#':
                    screen.fill(color, (tile_rect.x + column * nes_pixel, tile_rect.y + row * nes_pixel,
                                        nes_pixel, nes_pixel))
    return tile_rect
