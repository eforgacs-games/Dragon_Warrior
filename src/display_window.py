"""The game's window as a ``pygame._sdl2.video.Window``, for the window zoom (src/zoom.py) and the display filters'
renderer (src/display_filters.py).

``Window.from_display_module()`` makes a new Window object each time and points the SDL window's "pg_window" data at
it, without keeping a reference to it. pygame reads that pointer for every window, key and mouse event (their
``window`` attribute), so once the object is garbage collected those events point at freed memory, and the next
``event.get()`` can crash or hand back garbage. ``display_window`` keeps the last Window it made alive, in one place for
every module that needs the window, so whichever of them asked last, the pointer SDL holds is always to a live object.

This module imports nothing from ``src``.
"""
from pygame import display, error as pygame_error
from pygame._sdl2.video import Window

# The last Window made for the display's window, kept alive (see the module docstring)
_window: Window | None = None


def display_window() -> Window | None:
    """The game's window, or None if there isn't one (a test that never opened the display)."""
    global _window
    if not display.get_init() or display.get_surface() is None:
        return None
    try:
        _window = Window.from_display_module()
    except pygame_error:
        return None
    return _window
