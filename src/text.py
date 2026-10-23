import textwrap
from os.path import realpath
from typing import override

from pygame import font, display, Surface
from pygame.font import Font

from src.color import WHITE, BLACK
from src.directories import Directories
from src.sound import Sound
from src.waiting import wait
from src.window_renderer import DRAGON_QUEST_FONT_PATH, ELISION_APOSTROPHE, NES_GLYPHS, NES_TILE, font_characters

WRAP_LENGTH = 21


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
    directories = Directories(config)
    dialog_box_wrapper = DialogBoxWrapper(width=text_wrap_length, break_long_words=False)
    chunks = dialog_box_wrapper.wrap(text)
    item_gained_matches = ("thou hast gained", "Thou hast found")
    if any([x in text for x in item_gained_matches]):
        disable_sound = True
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
                current_font = text_font or set_font_by_ascii_chars(chunks, size, font_name, directories)
                blit_text_to_screen(alignment, color, current_font, screen, chunk, x, y, config["RENDER_TEXT"])
        y += 17
        if chunk == chunks[len(chunks) - 1]:
            return chunk
    return None


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
