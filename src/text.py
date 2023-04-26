import textwrap

from pygame import font, time, display

from src.common import BLACK, WHITE, DRAGON_QUEST_FONT_PATH, UNIFONT_PATH, play_sound, text_beep_sfx
from src.config import LANGUAGE


class DialogBoxWrapper(textwrap.TextWrapper):

    def wrap(self, text):
        split_text = text.split('\n')
        lines = [line for para in split_text for line in textwrap.TextWrapper.wrap(self, para)]
        return lines


def draw_text(text, x, y, screen, color=WHITE, size=16, font_name=DRAGON_QUEST_FONT_PATH, text_wrap_length=21,
              alignment='left', letter_by_letter=True):
    # n = 34
    # 34 is the maximum characters on the screen at a time.
    # 21? appears to be the actual max in the original game
    # chunks = [text[i:i + n] for i in range(0, len(text), n)]
    current_font = set_font_by_language(font_name, size, text)
    dialog_box_wrapper = DialogBoxWrapper(width=text_wrap_length, break_long_words=False)
    chunks = dialog_box_wrapper.wrap(text)
    sound_off = False
    item_gained_matches = ["thou hast gained", "Thou hast found"]
    if any([x in text for x in item_gained_matches]):
        sound_off = True
    for chunk in chunks:
        if letter_by_letter:
            string = ''
            for i in range(len(chunk)):
                string += chunk[i]
                blit_text_to_screen(alignment, color, current_font, screen, string, x, y)
                display.update()
                time.wait(16)
                if not sound_off:
                    if i % 2 == 0:
                        play_sound(text_beep_sfx)
        else:
            blit_text_to_screen(alignment, color, current_font, screen, chunk, x, y)
        y += 17
        if chunk == chunks[len(chunks) - 1]:
            return chunk


def blit_text_to_screen(alignment, color, current_font, screen, string, x, y):
    text_surface = current_font.render(string, True, color, BLACK)
    text_rect = set_text_rect_alignment(alignment, text_surface, x, y)
    screen.blit(text_surface, text_rect)


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


def set_font_by_language(font_name, size, text):
    if LANGUAGE == 'Korean':
        if not text.strip('’(↑ ← ↓ →)').isascii():
            current_font = font.Font(UNIFONT_PATH, size + 1)
        else:
            current_font = font.Font(font_name, size)
    else:
        current_font = font.Font(font_name, size)
    return current_font
