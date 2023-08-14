import textwrap

from pygame import font, time, display, Surface
from pygame.font import Font

from src.color import WHITE, BLACK
from src.config import dev_config
from src.directories import Directories
from src.sound import Sound


class DialogBoxWrapper(textwrap.TextWrapper):

    def wrap(self, text):
        split_text = text.split('\n')
        lines = [line for para in split_text for line in textwrap.TextWrapper.wrap(self, para)]
        return lines


def draw_text(text: str, x: float, y: float, screen: Surface, config: dict, color: tuple = WHITE, size: int = 16,
              text_wrap_length: int = 21, alignment: str = 'left', letter_by_letter: bool = True,
              disable_sound: bool = False, font_name: str = None) -> str:
    # n = 34
    # 34 is the maximum characters on the screen at a time.
    # 21? appears to be the actual max in the original game
    # chunks = [text[i:i + n] for i in range(0, len(text), n)]
    directories = Directories(config)
    dialog_box_wrapper = DialogBoxWrapper(width=text_wrap_length, break_long_words=False)
    chunks = dialog_box_wrapper.wrap(text)
    item_gained_matches = ("thou hast gained", "Thou hast found")
    if any([x in text for x in item_gained_matches]):
        disable_sound = True
    current_font = set_font_by_ascii_chars(chunks, size, font_name)
    for chunk in chunks:
        if letter_by_letter:
            string = ''
            for i in range(len(chunk)):
                string += chunk[i]
                if not config['NO_BLIT']:
                    display.update(blit_text_to_screen(alignment, color, current_font, screen, string, x, y,
                                                       config["RENDER_TEXT"]))
                if not config['NO_WAIT']:
                    time.wait(16)
                if not disable_sound:
                    if i % 2 == 0:
                        Sound(config).play_sound(directories.text_beep_sfx)
        else:
            if not config['NO_BLIT']:
                current_font = set_font_by_ascii_chars(chunks, size, font_name)
                blit_text_to_screen(alignment, color, current_font, screen, chunk, x, y, config["RENDER_TEXT"])
        y += 17
        if chunk == chunks[len(chunks) - 1]:
            return chunk


# TODO: remove dev_config
directories = Directories(dev_config)


def set_font_by_ascii_chars(chunks, size, font_name):
    if font_name is not None:
        return font.Font(font_name, size)
    else:
        if all(chunk.strip('’(↑ ← ↓ →)▼').isascii() for chunk in chunks):
            current_font = font.Font(directories.DRAGON_QUEST_FONT_PATH, size)
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
