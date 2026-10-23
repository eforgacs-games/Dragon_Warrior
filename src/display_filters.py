"""Optional display filters: scanlines and pixel-perfect scaling. Not NES behavior; both are off by default, set in the
options overlay (SCANLINES and SCALING, src/options_overlay.py) and kept with the global settings (src/settings.py).

How the game is shown without them: the window is opened with pygame's SCALED flag, so the game draws on a screen
surface of NES_RES * SCALE (512x480) and pygame's ``display.flip`` (``display.update`` is the same thing on a SCALED
display) copies it to a texture and has SDL's renderer stretch it over the window: in a window by whole multiples of
the 512x480 surface (pygame turns on SDL's integer scaling there), in fullscreen to fit the screen, keeping its shape,
with black borders. That is the SCALING option's SMOOTH, and with both filters off this module changes nothing at all:
``display.flip`` and ``display.update`` are pygame's own.

With either filter on, the Presenter takes over those two functions on the ``pygame.display`` module (the way
src/frame_recorder.py does: the game always presents through them) and shows the screen surface itself, on the same
SDL renderer (``pygame._sdl2.video.Renderer.from_window``), with no logical size set so it can say where every window
pixel goes:
- PIXEL PERFECT scales by whole multiples of the NES's 256x240 only (presentation_rect), centred, black around it,
  in a window and in fullscreen, so every NES pixel is the same square of window pixels. (SMOOTH at SCALE 2 can't show
  a 3x window, 768x720: pygame's integer scaling only knows multiples of 512x480, so it shows 2x with a border.)
- SCANLINES darkens the lower half of each of the NES's 240 lines, in window pixels (scanline_rects), at present
  time: translucent black rectangles drawn by the renderer over the picture. The game's own surfaces are never drawn
  on, so what the game reads back (screen copies, the frame recorder, the tests that compare screen bytes) is the same
  with the filter on or off.

Each present is one texture upload and one copy, as pygame's own flip is, and with SCANLINES 240 filled rectangles
(cheaper than blending a stretched texture of lines with SDL's software renderer, and the same on a GPU). Measured
with tools/benchmark.py --display: on a GPU (X11) neither filter costs a measurable part of a frame; with SDL's software
renderer (the dummy driver) SCANLINES costs about 0.5 ms a frame and PIXEL PERFECT about 0.15 ms. Without a renderer
(a window opened without SCALED, as some tests and tools do), the filters do nothing and pygame presents as always.

This module imports nothing from ``src``.
"""
from collections.abc import Callable
from functools import cache
from typing import Any

from pygame import FULLSCREEN, Rect, Surface, display, error as pygame_error
from pygame._sdl2.video import Renderer, Texture, Window

SCANLINES_KEY = 'SCANLINES'
SCALING_KEY = 'SCALING'
SCALING_SMOOTH = 'Smooth'
SCALING_PIXEL_PERFECT = 'PixelPerfect'
SCALING_MODES = (SCALING_SMOOTH, SCALING_PIXEL_PERFECT)

NES_WIDTH, NES_HEIGHT = 256, 240
SCANLINE_ALPHA = 96  # how dark a scanline is: 0 clear, 255 black
SDL_BLENDMODE_BLEND = 1
BLACK = (0, 0, 0, 255)


def presentation_rect(output_size: tuple[int, int], surface_size: tuple[int, int], scaling: str,
                      fullscreen: bool) -> Rect:
    """Where in the window (``output_size``, in pixels) the screen surface (``surface_size``) is shown.
    - PIXEL PERFECT: the biggest whole multiple of the NES's 256x240 that fits (at least 1x), centred.
    - SMOOTH, as pygame's SCALED shows it: in a window the biggest whole multiple of the surface that fits, in fullscreen
      (or a window smaller than the surface) stretched to fit, keeping its shape; centred."""
    width, height = output_size
    surface_width, surface_height = surface_size
    if scaling == SCALING_PIXEL_PERFECT:
        factor = max(1, min(width // NES_WIDTH, height // NES_HEIGHT))
        size = (NES_WIDTH * factor, NES_HEIGHT * factor)
    else:
        scale = min(width / surface_width, height / surface_height)
        if not fullscreen and scale >= 1:
            scale = int(scale)
        size = (int(surface_width * scale), int(surface_height * scale))
    rect = Rect((0, 0), size)
    rect.center = (width // 2, height // 2)
    return rect


@cache
def scanline_rects(left: int, top: int, width: int, height: int) -> tuple[tuple[int, int, int, int], ...]:
    """The window rows darkened in a picture shown at (left, top, width, height): the lower half of each NES line (of
    3 window rows, the last one; of 4, the last 2)."""
    rects = []
    for line in range(NES_HEIGHT):
        middle = top + -(-(2 * line + 1) * height // (2 * NES_HEIGHT))
        bottom = top + (line + 1) * height // NES_HEIGHT
        if bottom > middle:
            rects.append((left, middle, width, bottom - middle))
    return tuple(rects)


class _RendererState:
    """The renderer of the window that shows ``surface``, and the textures made on it."""

    def __init__(self, surface: Surface):
        self.surface = surface
        self.renderer = Renderer.from_window(Window.from_display_module())
        self.pygame_logical_size = tuple(self.renderer.logical_size)
        self.renderer.logical_size = (0, 0)  # window pixels: presentation_rect says where the picture goes
        self.texture = Texture(self.renderer, surface.get_size(), streaming=True)

    def present(self, scanlines: bool, scaling: str) -> None:
        renderer = self.renderer
        output = renderer.get_viewport().size
        destination = presentation_rect(output, self.surface.get_size(), scaling,
                                        bool(self.surface.get_flags() & FULLSCREEN))
        self.texture.update(self.surface)
        renderer.draw_blend_mode = 0
        renderer.draw_color = BLACK
        renderer.clear()
        renderer.blit(self.texture, destination)
        if scanlines:
            renderer.draw_blend_mode = SDL_BLENDMODE_BLEND
            renderer.draw_color = (0, 0, 0, SCANLINE_ALPHA)
            fill_rect = renderer.fill_rect
            for rect in scanline_rects(*destination):
                fill_rect(rect)
            renderer.draw_blend_mode = 0
        renderer.present()

    def give_back(self) -> None:
        """Hand the renderer back to pygame's own flip, which stretches over the logical size it set."""
        self.renderer.logical_size = self.pygame_logical_size


class Presenter:
    """Shows each frame with the filters (see the module docstring). There is one, PRESENTER: the display is one."""

    def __init__(self) -> None:
        self.scanlines = False
        self.scaling = SCALING_SMOOTH
        self._state: _RendererState | None = None
        self._unavailable_for: Surface | None = None  # a screen surface whose window has no renderer
        self._previous_flip: Callable[[], Any] | None = None
        self._previous_update: Callable[..., Any] | None = None
        # The functions put on pygame.display, made once: each read of self.flip makes a new bound method, and these
        # are compared by identity to see whether they're still there
        self._flip: Callable[[], None] = self.flip
        self._update: Callable[..., None] = self.update
        # Whether ours are in the chain of display.flip and update: on top, or under something that wrapped them since
        self._installed = False

    @property
    def active(self) -> bool:
        return self.scanlines or self.scaling == SCALING_PIXEL_PERFECT

    def configure(self, scanlines: bool, scaling: str) -> None:
        """Use these filters from the next frame on (and show the screen with them now)."""
        self.scanlines = bool(scanlines)
        self.scaling = scaling if scaling in SCALING_MODES else SCALING_SMOOTH
        if self.active:
            self._install()
        else:
            self.release()
            self._uninstall()

    def configure_from(self, config: dict) -> None:
        self.configure(bool(config.get(SCANLINES_KEY)), config.get(SCALING_KEY, SCALING_SMOOTH))

    def release(self) -> None:
        """Let go of the renderer and its textures, giving it back to pygame. Call it before the window is made again
        (``set_mode``) or closed: SDL destroys the renderer's textures with it."""
        if self._state is not None:
            try:
                self._state.give_back()
            except pygame_error:
                pass
            self._state = None
        self._unavailable_for = None

    def _install(self) -> None:
        if not self._installed:
            self._previous_flip, self._previous_update = display.flip, display.update
            display.flip, display.update = self._flip, self._update  # type: ignore[assignment]
            self._installed = True

    def _uninstall(self) -> None:
        # Something that wrapped these after us (a frame recorder) puts us back when it stops; while it's there we
        # stay underneath it, passing straight through to pygame
        if self._installed and display.flip is self._flip and display.update is self._update:
            display.flip, display.update = self._previous_flip, self._previous_update  # type: ignore[assignment]
            self._installed = False

    def flip(self) -> None:
        if not self.present():
            self._pass_through_flip()

    def update(self, *args: Any, **kwargs: Any) -> None:
        """On a SCALED display pygame shows the whole surface for any update, so this is a flip too."""
        if not self.present():
            if self._previous_update is not None:
                self._previous_update(*args, **kwargs)

    def _pass_through_flip(self) -> None:
        if self._previous_flip is not None:
            self._previous_flip()

    def present(self) -> bool:
        """Show the screen with the filters. False if they're off or the window has no renderer: pygame shows it."""
        if not self.active:
            return False
        state = self._state_for(display.get_surface())
        if state is None:
            return False
        state.present(self.scanlines, self.scaling)
        return True

    def _state_for(self, surface: Surface | None) -> _RendererState | None:
        if surface is None or surface is self._unavailable_for:
            return None
        if self._state is not None and self._state.surface is surface:
            return self._state
        if self._state is not None:
            # The window was made again without release(): its renderer, and the textures on it, may be gone already,
            # so they're neither handed back nor destroyed (freeing a texture of a destroyed renderer can crash)
            _orphans.append(self._state)
            self._state = None
        try:
            self._state = _RendererState(surface)
        except pygame_error:
            # No renderer: a window opened without SCALED
            self._unavailable_for = surface
            return None
        return self._state


_orphans: list[_RendererState] = []

PRESENTER = Presenter()
