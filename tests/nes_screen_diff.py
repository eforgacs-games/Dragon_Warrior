"""Compare a generated window or screen with the NES screenshot it replaces, pixel for pixel.

The rule for replacing a screenshot with a generated window: 0 differing pixels, at every scale. There is no
tolerance and no threshold. The only thing done to a screenshot before comparing is an explicit colour mapping
(SCREENSHOT_COLOR_MAP): the screenshots' white is (255, 254, 255), not the game's WHITE (255, 255, 255); every
other colour must match exactly, so a colour the map doesn't list (an antialiased edge, a stray grey) is a difference.

Usage:
    result = compare_with_screenshot(generated, screenshot_path, nes_pixel=2, diff_dir=some_dir, name='fight')
    assert result.differing_pixels == 0, result
"""
from array import array
from os import makedirs
from os.path import join
from typing import NamedTuple

from pygame import PixelArray, Rect, Surface, image, transform

from src.color import BLACK, WHITE

# The NES screenshots' colours, mapped to the game's: exact colours, no tolerance
SCREENSHOT_COLOR_MAP = {
    (255, 254, 255): WHITE,
}
# How the diff image shows a pixel that differs
DIFF_HIGHLIGHT = (255, 0, 255)


class DiffResult(NamedTuple):
    differing_pixels: int
    size: tuple[int, int]
    diff_path: str | None  # the saved diff image, if any pixel differs and a diff_dir was given

    def __str__(self):
        return (f"{self.differing_pixels} of {self.size[0] * self.size[1]} pixels differ"
                + (f" (diff image: {self.diff_path})" if self.diff_path else ""))


def load_screenshot(path: str, nes_pixel: int = 1, window_color: tuple = WHITE) -> Surface:
    """
    A screenshot as the game would draw it: its colours mapped with SCREENSHOT_COLOR_MAP, and scaled.
    :param path: The screenshot, one pixel per NES pixel.
    :param nes_pixel: Screen pixels per NES pixel (SCALE). Scaled by whole pixels (nearest neighbour).
    :param window_color: The window color to compare with: white is replaced by it, exactly like the NES palette
    swap (red at low HP), to derive the low HP screenshot from the white one.
    """
    screenshot = image.load(path)
    mapped = Surface(screenshot.get_size())
    mapped.blit(screenshot, (0, 0))
    pixels = PixelArray(mapped)
    # distance=0: only that exact colour is replaced
    for source, target in SCREENSHOT_COLOR_MAP.items():
        pixels.replace(source, target, distance=0)
    if window_color != WHITE:
        pixels.replace(WHITE, window_color, distance=0)
    pixels.close()
    return transform.scale_by(mapped, nes_pixel) if nes_pixel != 1 else mapped


def _pixels(surface: Surface) -> array:
    """The surface's pixels as 32 bit values, one per pixel (alpha ignored: copied onto an opaque surface first)."""
    opaque = Surface(surface.get_size())
    opaque.blit(surface, (0, 0))
    pixels = array('I')
    pixels.frombytes(image.tobytes(opaque, 'RGBX'))
    return pixels


def count_differing_pixels(generated: Surface, reference: Surface) -> int:
    if generated.get_size() != reference.get_size():
        raise ValueError(f"sizes differ: {generated.get_size()} and {reference.get_size()}")
    return sum(1 for a, b in zip(_pixels(generated), _pixels(reference)) if a != b)


def save_diff_image(generated: Surface, reference: Surface, path: str) -> None:
    """Save the screenshot, the generated surface and the differences side by side: in the third panel, matching
    pixels are the screenshot dimmed to a quarter, and differing pixels are DIFF_HIGHLIGHT."""
    width, height = reference.get_size()
    diff = Surface((width * 3, height))
    diff.fill(BLACK)
    diff.blit(reference, (0, 0))
    diff.blit(generated, (width, 0))
    generated_pixels, reference_pixels = _pixels(generated), _pixels(reference)
    for index, (a, b) in enumerate(zip(generated_pixels, reference_pixels)):
        x, y = index % width, index // width
        if a != b:
            diff.set_at((2 * width + x, y), DIFF_HIGHLIGHT)
        else:
            r, g, bl = tuple(reference.get_at((x, y)))[:3]
            diff.set_at((2 * width + x, y), (r // 4, g // 4, bl // 4))
    image.save(diff, path)


def compare_with_screenshot(generated: Surface, screenshot_path: str, nes_pixel: int = 1,
                            window_color: tuple = WHITE, area: Rect | None = None, diff_dir: str | None = None,
                            name: str = 'diff') -> DiffResult:
    """
    Compare a generated window or screen with its screenshot.
    :param generated: What the game draws.
    :param screenshot_path: The NES screenshot (one pixel per NES pixel).
    :param nes_pixel: The scale generated is drawn at (SCALE).
    :param window_color: The window color generated is drawn in (see load_screenshot).
    :param area: The part of generated to compare: the screenshot's position and size on the screen (in screen
    pixels). By default, all of generated.
    :param diff_dir: Where to save a diff image if any pixel differs (created if needed).
    :param name: The diff image's file name, without '.png'.
    """
    reference = load_screenshot(screenshot_path, nes_pixel, window_color)
    if area is not None:
        generated = generated.subsurface(area)
    differing = count_differing_pixels(generated, reference)
    diff_path = None
    if differing and diff_dir is not None:
        makedirs(diff_dir, exist_ok=True)
        diff_path = join(diff_dir, f'{name}.png')
        save_diff_image(generated, reference, diff_path)
    return DiffResult(differing, reference.get_size(), diff_path)
