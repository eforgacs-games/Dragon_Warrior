"""Generated NES windows (src/window_renderer.py) whose text may be translated.

The NES font has no Korean, so a window can only be generated tile by tile while all of its text is untranslated
(English). Once any of it is translated, the border is generated without text and every title and line is drawn over
it as text (src/text.py draw_text, which picks Unifont for Korean) at the tile the NES puts it in, the same way the
COMMAND window (CommandMenu.draw_command_window) and the shop windows (DialogLookup.is_nes_text) do it.
"""
from typing import Callable

from pygame import Rect, Surface

from src.color import BLACK
from src.directories import Directories
from src.text import draw_text, set_font_by_ascii_chars
from src.window_renderer import draw_window, window_tiles
from src.windows import WindowLayout, WindowText

Translate = Callable[[str], str]


def layout_texts(layout: WindowLayout) -> tuple[WindowText, ...]:
    """The window's title (if it has one), then its text."""
    return ((layout.title,) if layout.title else ()) + layout.texts


def layout_in_nes_font(layout: WindowLayout, translate: Translate) -> bool:
    """Whether none of the window's text is translated and every character of it is an NES font tile, so all of it
    can be generated in the NES font. (A hero's name in an adventure log window comes from the save file.)"""
    if not all(translate(text.text) == text.text for text in layout_texts(layout)):
        return False
    try:
        window_tiles(layout)
    except ValueError:
        return False
    return True


def draw_translated_window(screen: Surface, layout: WindowLayout, color: tuple, config: dict, translate: Translate,
                           cursor_index: int | None = None, cursor_visible: bool = True,
                           right_aligned: bool = False) -> Rect:
    """
    Draw a window with its text translated (see draw_window for the other parameters).
    :param translate: The gettext function of the game's language (set_gettext_language).
    :param right_aligned: Translated text ends where the English text ends (the status window's labels, which line up
    on their right edge), instead of starting where it starts.
    :return: The window's rect on the screen, for display.update.
    """
    if layout_in_nes_font(layout, translate):
        return draw_window(screen, layout, color, config, cursor_index=cursor_index, cursor_visible=cursor_visible)
    rect = draw_window(screen, layout._replace(title=None, texts=()), color, config, cursor_index=cursor_index,
                       cursor_visible=cursor_visible)
    if config.get('NO_BLIT'):
        return rect
    nes_tile = config['TILE_SIZE'] / 2
    window_column, window_row = layout.window.x * 2, layout.window.y * 2
    for text in layout_texts(layout):
        translated = translate(text.text)
        column, alignment = (text.column + len(text.text), 'right') if right_aligned else (text.column, 'left')
        x, y = (window_column + column) * nes_tile, (window_row + text.row + 0.5) * nes_tile
        if text.row == 0:
            # A title: the top border stops one pixel short of it on each side (TL_TOP2)
            scale = config['TILE_SIZE'] // 16  # screen pixels per NES pixel
            width = set_font_by_ascii_chars([translated], 16, None, Directories(config)).size(translated)[0]
            left = x - width if alignment == 'right' else x
            screen.fill(BLACK, (left - scale, window_row * nes_tile, width + 2 * scale, nes_tile))
        draw_text(translated, x, y, screen, config, color=color, alignment=alignment, letter_by_letter=False)
    return rect
