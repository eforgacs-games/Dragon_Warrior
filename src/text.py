import textwrap
from collections import OrderedDict
from os.path import realpath
from typing import override

from pygame import font, display, Surface
from pygame.font import Font

from src.color import WHITE, BLACK
from src.paths import data_path
from src.sound import Sound
from src.waiting import wait
from src.window_renderer import DRAGON_QUEST_FONT_PATH, ELISION_APOSTROPHE, NES_GLYPHS, NES_TILE, font_characters

WRAP_LENGTH = 21
# How many rendered lines draw_text keeps (rendered_line): every window line on the screen at once, many times over
RENDERED_LINES_KEPT = 256


class TextPaths:
    """The files draw_text uses, the same as Directories' (src/directories.py), without making a Directories (which
    loads two fonts and builds every other path of the game) for every line of text drawn."""
    DRAGON_QUEST_FONT_PATH = DRAGON_QUEST_FONT_PATH
    UNIFONT_PATH = data_path('fonts', 'unifont.otf')
    text_beep_sfx = data_path('sound', 'sfx', 'text_beep.wav')


class DialogBoxWrapper(textwrap.TextWrapper):

    @override
    def wrap(self, text):
        split_text = text.split('\n')
        lines = [line for para in split_text for line in textwrap.TextWrapper.wrap(self, para)]
        return lines


def draw_text(text: str, x: float, y: float, screen: Surface, config: dict, color: tuple = WHITE, size: int = 16,
              text_wrap_length: int = WRAP_LENGTH, alignment: str = 'left', letter_by_letter: bool = True,
              disable_sound: bool = False, font_name: str | None = None, text_font: Font | None = None) -> str | None:
    """:param text_font: The font to draw in, instead of the one the text's characters pick (a translated window keeps
        one font for all its lines)."""
    # 34 is the maximum characters on the screen at a time.
    # 21? appears to be the actual max in the original game
    # chunks = [text[i:i + n] for i in range(0, len(text), n)]
    directories = TextPaths
    dialog_box_wrapper = DialogBoxWrapper(width=text_wrap_length, break_long_words=False)
    chunks = dialog_box_wrapper.wrap(text)
    item_gained_matches = ("thou hast gained", "Thou hast found")
    if any([x in text for x in item_gained_matches]):
        disable_sound = True
    if not letter_by_letter and text_font is None:
        # A whole line at once, in the font its characters pick: the same line in the same font and color is the same
        # picture every time, so it is rendered once and kept (rendered_line). The pop-up window draws five of them
        # every frame the hero stands still.
        font_key = (font_name, size, font_name is None and all(in_nes_font(chunk) for chunk in chunks))
        for chunk in chunks:
            if not config['NO_BLIT'] and config["RENDER_TEXT"]:
                text_surface = rendered_line(font_key, chunks, chunk, color)
                screen.blit(text_surface, set_text_rect_alignment(alignment, text_surface, x, y))
            y += 17
            if chunk == chunks[len(chunks) - 1]:
                return chunk
        return None
    current_font = text_font or set_font_by_ascii_chars(chunks, size, font_name, directories)
    for chunk in chunks:
        if letter_by_letter:
            string = ''
            for i in range(len(chunk)):
                string += chunk[i]
                if not config['NO_BLIT']:
                    display.update(blit_text_to_screen(alignment, color, current_font, screen, string, x, y,
                                                       config["RENDER_TEXT"]))
                wait(16, config)
                if not disable_sound:
                    if i % 3 == 0:
                        Sound(config).play_sound(directories.text_beep_sfx)
        else:
            if not config['NO_BLIT']:
                blit_text_to_screen(alignment, color, current_font, screen, chunk, x, y, config["RENDER_TEXT"])
        y += 17
        if chunk == chunks[len(chunks) - 1]:
            return chunk
    return None


_rendered_lines: OrderedDict[tuple, Surface] = OrderedDict()


def rendered_line(font_key: tuple, chunks: list[str], chunk: str, color: tuple) -> Surface:
    """chunk rendered as blit_text_to_screen renders it, in the font set_font_by_ascii_chars picks for chunks
    (font_key says which: the font name, the size and whether the NES font is picked). The last RENDERED_LINES_KEPT
    are kept, so a line drawn again is blitted without making a font or rendering it again. Nothing draws on the
    surfaces returned: they are only blitted."""
    key = (font_key, chunk, tuple(color))
    surface = _rendered_lines.get(key)
    if surface is None:
        surface = set_font_by_ascii_chars(chunks, font_key[1], font_key[0], TextPaths).render(chunk, True, color,
                                                                                            BLACK)
        _rendered_lines[key] = surface
        if len(_rendered_lines) > RENDERED_LINES_KEPT:
            _rendered_lines.popitem(last=False)
    else:
        _rendered_lines.move_to_end(key)
    return surface


class NESFont(Font):
    """dragon-quest.ttf, drawing every character as its NES font tile.

    Rendered at a multiple of 8 pixels, the font is the NES tile scaled up for every character but j, k, p, t and the
    apostrophe (src/window_renderer.py). render draws those with the NES tiles instead: the letters from NES_GLYPHS,
    and the apostrophe as the font's ’ (its ' is a straight one), in the text color and at the font's scale (size / 8
    screen pixels per NES pixel), so text everywhere matches the NES windows."""

    def __init__(self, path: str, size: int):
        super().__init__(path, size)
        self.font_size = size

    @override
    def render(self, text, antialias, color, bgcolor=None) -> Surface:  # type: ignore[override]
        if not isinstance(text, str):
            return super().render(text, antialias, color, bgcolor)
        text = font_characters(text)
        # Render the NES_GLYPHS letters as spaces (the font is monospaced), then draw their NES tiles in those cells
        surface = super().render(''.join(' ' if character in NES_GLYPHS else character for character in text),
                                 antialias, color, bgcolor)
        # The font's line: size / 8 blank rows, the tile's 8 rows (size pixels), size / 8 blank rows
        nes_pixel = self.font_size / NES_TILE
        top = nes_pixel
        for index, character in enumerate(text):
            if character not in NES_GLYPHS:
                continue
            left = self.size(text[:index])[0]
            cell_pixel = (self.size(text[:index + 1])[0] - left) / NES_TILE
            for row, line in enumerate(NES_GLYPHS[character]):
                y = round(top + row * nes_pixel)
                height = round(top + (row + 1) * nes_pixel) - y
                for column, pixel in enumerate(line):
                    if pixel == '#':
                        x = left + round(column * cell_pixel)
                        surface.fill(color, (x, y, left + round((column + 1) * cell_pixel) - x, height))
        return surface


def nes_font(path: str, size: int) -> Font:
    """The font at path; dragon-quest.ttf as an NESFont."""
    if realpath(path) == realpath(DRAGON_QUEST_FONT_PATH):
        return NESFont(path, size)
    return font.Font(path, size)


def in_nes_font(text: str) -> bool:
    """Whether text is drawn in the NES font (dragon-quest.ttf): English text, with the NES symbols it uses. Anything
    else (Korean) is drawn in Unifont."""
    return text.replace(ELISION_APOSTROPHE, "'").strip('’(↑ ← ↓ →)▼').isascii()


def set_font_by_ascii_chars(chunks, size, font_name, directories):
    if font_name is not None:
        return nes_font(font_name, size)
    else:
        if all(in_nes_font(chunk) for chunk in chunks):
            current_font = NESFont(directories.DRAGON_QUEST_FONT_PATH, size)
        else:
            current_font = font.Font(directories.UNIFONT_PATH, size)
            current_font.bold = True
        return current_font


def blit_text_to_screen(alignment: str, color: tuple, current_font: Font, screen: Surface, string: str, x: float,
                        y: float, render_text=True):
    if render_text:
        text_surface = current_font.render(string, True, color, BLACK)
        text_rect = set_text_rect_alignment(alignment, text_surface, x, y)
        return screen.blit(text_surface, text_rect)


def set_text_rect_alignment(alignment, text_surface, x, y):
    text_rect = text_surface.get_rect()
    match alignment:
        case 'left':
            text_rect.midleft = (x, y)
        case 'center':
            text_rect.midtop = (x, y)
        case 'right':
            text_rect.midright = (x, y)
    return text_rect
