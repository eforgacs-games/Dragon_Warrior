"""The widescreen view (#411): VIEW NES (4:3) or WIDE, the options overlay's VIEW row. Not NES.

NES (4:3) is the NES's own picture: 256 x 240 NES pixels, the screen surface the game has always drawn on. Nothing
here is used then: the game's screen is the display surface itself.

WIDE shows more of the map to the left and right, so the picture fills a 16:9 or 16:10 screen: the display surface is
wider (wide_width: as many NES pixels across as the desktop's shape gives 240 rows, 426 for 16:9 and 384 for 16:10),
and the game's screen is the 4:3 area in its middle, a subsurface of it (WideView.screen). Everything the game draws on
its screen (the windows, the dialogs, the battle window and the enemy, the title) is drawn there as before, so it stays
where the NES puts it, centered. Only what covers the whole picture draws on the whole display (full_screen):
- the map, which Drawer.draw_all draws across the whole width (with the border block beyond the map's edges);
- the darkness in a dungeon, centered on the hero as before;
- the fades, cuts to black and screen flashes (src/visual_effects.py), and the options overlay's shade.

The hero stays where the NES draws him, half a block right of the middle (the camera is the NES camera, moved right
by WideView.origin_x).

The view goes with the window: it is set up again whenever the window is made (Game.set_view, for F11 too). The SCALED
window stretches the wider surface the same way, and the zoom keys (src/zoom.py) use whole multiples of its NES size.
"""
from dataclasses import dataclass

from pygame import Surface, display

VIEW_NES = 'NES'
VIEW_WIDE = 'Wide'
VIEWS = (VIEW_NES, VIEW_WIDE)
DEFAULT_VIEW = VIEW_NES

NES_WIDTH, NES_HEIGHT = 256, 240
# The widest view: 16:9. A wider desktop (21:9) shows 16:9 with black at the sides, like the NES view on a 16:9 one
WIDEST_ASPECT = 16 / 9
# A desktop no wider than the NES view's own 16:15 (256 x 240 square pixels), or none known: WIDE is 16:9
DEFAULT_WIDE_ASPECT = 16 / 9


@dataclass(frozen=True)
class WideView:
    """The wide display surface and the game's 4:3 screen in its middle."""
    display: Surface
    screen: Surface
    origin_x: int  # where the 4:3 screen starts on the display, in pixels


_wide_view: WideView | None = None


def view_name(config: dict) -> str:
    view = config.get('VIEW', DEFAULT_VIEW)
    return view if view in VIEWS else DEFAULT_VIEW


def wide_aspect(desktop_sizes: list[tuple[int, int]] | None = None) -> float:
    """The shape of the WIDE view: the first desktop's, at most 16:9 (DEFAULT_WIDE_ASPECT if it's no wider than the
    NES view). A 4:3 desktop gets 320 NES pixels across."""
    if desktop_sizes is None:
        try:
            desktop_sizes = display.get_desktop_sizes() if display.get_init() else []
        except Exception:  # pygame.error with no video system
            desktop_sizes = []
    if not desktop_sizes or not desktop_sizes[0][1]:
        return DEFAULT_WIDE_ASPECT
    width, height = desktop_sizes[0]
    aspect = width / height
    if aspect <= NES_WIDTH / NES_HEIGHT:
        return DEFAULT_WIDE_ASPECT
    return min(aspect, WIDEST_ASPECT)


def wide_width(aspect: float) -> int:
    """The WIDE view's width in NES pixels for a screen of this shape: 240 rows that shape, rounded down to an even
    number (so the extra columns are the same on both sides), and never narrower than the NES's 256."""
    return max(NES_WIDTH, int(NES_HEIGHT * aspect) // 2 * 2)


def view_width(config: dict, aspect: float | None = None) -> int:
    """The view's width in NES pixels: 256 for NES (4:3), wide_width for WIDE."""
    if view_name(config) == VIEW_NES:
        return NES_WIDTH
    return wide_width(wide_aspect() if aspect is None else aspect)


def set_up_view(display_surface: Surface, scale: int) -> Surface:
    """The game's screen on a display surface just made by set_mode: the display surface itself if it is the NES's
    size, else the NES-sized area in its middle. Call it after every set_mode: the subsurface of an older display
    surface doesn't draw on the new one."""
    global _wide_view
    width, height = display_surface.get_size()
    nes_width = NES_WIDTH * scale
    if width <= nes_width:
        _wide_view = None
        return display_surface
    origin_x = (width - nes_width) // 2
    screen = display_surface.subsurface((origin_x, 0, nes_width, height))
    _wide_view = WideView(display_surface, screen, origin_x)
    return screen


def wide_view() -> WideView | None:
    return _wide_view


def full_screen(screen: Surface) -> Surface:
    """What covers the whole picture is drawn on: the wide display surface if screen is the game's screen in the
    WIDE view, else screen itself."""
    view = _wide_view
    if view is not None and screen is view.screen:
        return view.display
    return screen


def screen_origin_x(screen: Surface) -> int:
    """Where screen starts on full_screen(screen), in pixels: 0 but for the game's screen in the WIDE view."""
    view = _wide_view
    if view is not None and screen is view.screen:
        return view.origin_x
    return 0


def reset_view() -> None:
    """Forget the wide view (tests, a closed display)."""
    global _wide_view
    _wide_view = None
