"""Window zoom: Ctrl + and Ctrl - (or Ctrl and the mouse wheel) make the window bigger or smaller, Ctrl 0 puts it back to
the size it opened at. A modern convenience, not NES behavior.

Only the window changes size. The game still draws on the same screen surface (NES_RES * SCALE, with TILE_SIZE = 16 *
SCALE): the window is opened with pygame's SCALED flag, so SDL stretches that surface to whatever size the window is,
with nearest-neighbour sampling. The zoom levels are whole multiples of the NES's 256x240 (wider in the WIDE view,
src/view.py: nes_width), so every NES pixel becomes the same number of window pixels and the pixel art stays crisp
(at SCALE 2, zoom 3 turns each 2x2 block of the screen into a 3x3 block). Nothing the game draws, caches or decides
changes, so it works the same on every screen: the map, battles, menus, dialogs and the title.

The smallest zoom is the screen surface's own size (SCALE: pygame doesn't let a SCALED window get smaller than the
surface), and the biggest is what fits on the desktop, or the size the window opened at if that is bigger.

In fullscreen (F11) the keys do nothing: the screen fills the monitor there. Leaving fullscreen puts the window back
at the size it had before (remember_windowed_size, restore_windowed_size). The zoom is kept with the global settings
(src/settings.py): set_zoom tells the zoom listener (set_zoom_listener), and the game opens the window at the saved zoom
the next time. So is a size the window is given by dragging its edge (or maximizing it): SCALED stretches the screen
to it as it is, and the nearest whole zoom is saved (note_window_resized), which the window opens at the next time.

This module imports nothing from ``src`` but src/display_window.py (which imports nothing from ``src``), so
src/waiting.py can use it without an import cycle.
"""
from collections.abc import Callable

from pygame import FULLSCREEN, K_0, K_EQUALS, K_KP0, K_KP_MINUS, K_KP_PLUS, K_MINUS, K_PLUS, KEYDOWN, KMOD_CTRL, \
    MOUSEWHEEL, VIDEORESIZE, WINDOWSIZECHANGED, display, event, key

from src.display_window import display_window

NES_WIDTH, NES_HEIGHT = 256, 240
# Room left on the desktop for the window's title bar and the taskbar when working out the biggest zoom that fits
DESKTOP_MARGIN = 64

ZOOM_IN_KEYS = (K_EQUALS, K_PLUS, K_KP_PLUS)  # Ctrl = is Ctrl + without Shift on most keyboards
ZOOM_OUT_KEYS = (K_MINUS, K_KP_MINUS)
ZOOM_RESET_KEYS = (K_0, K_KP0)

# The zoom the window opened at (remember_default_zoom), which Ctrl 0 goes back to
_default_zoom: int | None = None
# The window's size before it went fullscreen (remember_windowed_size), in window pixels per NES pixel across and
# down, so it is the same zoom in whichever view (src/view.py) the window comes back in
_windowed_scale: tuple[float, float] | None = None
# Told the new zoom each time set_zoom changes the window's size: the game saves it with the global settings
_zoom_listener: Callable[[int], None] | None = None


def set_zoom_listener(listener: Callable[[int], None] | None) -> None:
    """Call ``listener`` with the zoom after every change set_zoom makes (None: no one is told)."""
    global _zoom_listener
    _zoom_listener = listener


def is_fullscreen() -> bool:
    surface = display.get_surface()
    return surface is not None and bool(surface.get_flags() & FULLSCREEN)


def nes_width() -> int:
    """The picture's width in NES pixels: 256, or more in the WIDE view (src/view.py), whose window is wider. The
    screen surface is always 240 NES pixels high, so its width at that height is the NES width."""
    surface = display.get_surface()
    if surface is None or not surface.get_height():
        return NES_WIDTH
    width, height = surface.get_size()
    return max(NES_WIDTH, round(width * NES_HEIGHT / height))


def window_zoom() -> float:
    """How many window pixels each NES pixel takes right now (not a whole number after the window is resized by
    dragging its edge)."""
    width, height = display.get_window_size()
    return min(width / nes_width(), height / NES_HEIGHT)


def min_zoom() -> int:
    """The smallest zoom: the screen surface's own size (NES_RES * SCALE), which a SCALED window can't go below."""
    surface = display.get_surface()
    if surface is None:
        return 1
    width, height = surface.get_size()
    return max(1, -(-width // nes_width()), -(-height // NES_HEIGHT))


def max_zoom() -> int:
    """The biggest zoom whose window fits on the biggest monitor, but never less than the zoom the window opened at or
    the smallest zoom."""
    fits = [min(width // nes_width(), (height - DESKTOP_MARGIN) // NES_HEIGHT)
            for width, height in display.get_desktop_sizes()]
    return max([min_zoom(), default_zoom()] + fits)


def remember_default_zoom() -> None:
    """Note the window's zoom as the one Ctrl 0 goes back to: call it once the game's window has been opened."""
    global _default_zoom
    if display_window() is not None and not is_fullscreen():
        _default_zoom = max(min_zoom(), round(window_zoom()))


def default_zoom() -> int:
    """The zoom the window opened at, which Ctrl 0 goes back to."""
    return _default_zoom if _default_zoom is not None else min_zoom()


def set_zoom(zoom: int) -> bool:
    """Make the window ``zoom`` times the NES's 256x240 (kept between min_zoom and max_zoom), keeping its center where
    it was. Returns whether the window changed size. Does nothing in fullscreen."""
    window = display_window()
    if window is None or is_fullscreen():
        return False
    zoom = max(min_zoom(), min(zoom, max_zoom()))
    old_width, old_height = window.size
    new_size = (nes_width() * zoom, NES_HEIGHT * zoom)
    if new_size == (old_width, old_height):
        return False
    old_position = window.position  # typed as int too (WINDOWPOS_CENTERED when setting it), but read as (x, y)
    window.size = new_size
    if isinstance(old_position, tuple):
        old_x, old_y = old_position
        window.position = (max(0, old_x + (old_width - new_size[0]) // 2),
                           max(0, old_y + (old_height - new_size[1]) // 2))
    # Show the screen at the new size now: a window waiting for a key doesn't draw again until something changes
    display.flip()
    if _zoom_listener is not None:
        _zoom_listener(zoom)
    return True


def zoom_in() -> bool:
    """One step bigger: the next whole zoom above the window's size (a window dragged to 3.5x goes to 4x). A window
    already at max_zoom (or dragged past it) stays as it is."""
    if display_window() is None:
        return False
    target = int(window_zoom()) + 1
    return target <= max_zoom() and set_zoom(target)


def zoom_out() -> bool:
    """One step smaller: the next whole zoom below the window's size (a window dragged to 3.5x goes to 3x)."""
    if display_window() is None:
        return False
    current = window_zoom()
    target = int(current) - 1 if current == int(current) else int(current)
    return target >= min_zoom() and set_zoom(target)


def reset_zoom() -> bool:
    """Back to the size the window opened at."""
    return set_zoom(default_zoom())


def remember_windowed_size() -> None:
    """Note the window's size before it goes fullscreen (F11), for restore_windowed_size."""
    global _windowed_scale
    if display_window() is not None and not is_fullscreen():
        width, height = display.get_window_size()
        _windowed_scale = (width / nes_width(), height / NES_HEIGHT)


def set_windowed_zoom(zoom: int) -> None:
    """The window size to go back to on leaving fullscreen: ``zoom`` times the NES picture (256x240, wider in the WIDE
    view). For a game that opens in fullscreen with a saved zoom, whose window has never had a size of its own."""
    global _windowed_scale
    _windowed_scale = (zoom, zoom)


def restore_windowed_size() -> None:
    """Back from fullscreen: give the window the size it had before (set_mode alone opens it at its first size), as
    many window pixels per NES pixel as it had, in the view it is in now: the VIEW option may have changed meanwhile
    (src/view.py), and a WIDE window is wider at the same zoom."""
    window = display_window()
    if window is not None and not is_fullscreen() and _windowed_scale is not None:
        scale_x, scale_y = _windowed_scale
        window.size = (round(nes_width() * scale_x), round(NES_HEIGHT * scale_y))
        display.flip()


def note_window_resized() -> None:
    """The window has a new size, perhaps one the player dragged its edge to: tell the zoom listener the nearest whole
    zoom (between min_zoom and max_zoom), so the next launch opens at it. The window itself is left at the size it
    was given (SCALED stretches the screen to fit it), and a fullscreen window's size isn't a zoom."""
    if _zoom_listener is None or display_window() is None or is_fullscreen():
        return
    _zoom_listener(max(min_zoom(), min(round(window_zoom()), max_zoom())))


def handle_zoom_event(current_event: event.Event) -> bool:
    """If ``current_event`` is Ctrl +, Ctrl -, Ctrl 0 or the mouse wheel turned with Ctrl held, zoom the window and
    return True (the event is used up, so no window reads it as a key). A window resize is noted (note_window_resized)
    and left for the loop to read. Any other event: False."""
    if current_event.type in (VIDEORESIZE, WINDOWSIZECHANGED):
        note_window_resized()
        return False
    if current_event.type == KEYDOWN:
        if not getattr(current_event, 'mod', 0) & KMOD_CTRL:
            return False
        pressed = getattr(current_event, 'key', None)
        if pressed in ZOOM_IN_KEYS:
            zoom_in()
        elif pressed in ZOOM_OUT_KEYS:
            zoom_out()
        elif pressed in ZOOM_RESET_KEYS:
            reset_zoom()
        else:
            return False
        return True
    if current_event.type == MOUSEWHEEL and key.get_mods() & KMOD_CTRL:
        wheel = getattr(current_event, 'y', 0)
        if wheel > 0:
            zoom_in()
        elif wheel < 0:
            zoom_out()
        return True
    return False
