import textwrap

from pygame import font

from src.common import BLACK, WHITE, DRAGON_QUEST_FONT_PATH, UNIFONT_PATH
from src.config import LANGUAGE


class DialogBoxWrapper(textwrap.TextWrapper):

    def wrap(self, text):
        split_text = text.split('\n')
        lines = [line for para in split_text for line in textwrap.TextWrapper.wrap(self, para)]
        return lines


def draw_text(text, x, y, screen, color=WHITE, size=16, font_name=DRAGON_QUEST_FONT_PATH, text_wrap_length=21, alignment='left', letter_by_letter=False):
    # n = 34
    # 34 is the maximum characters on the screen at a time.
    # 21? appears to be the actual max in the original game
    # chunks = [text[i:i + n] for i in range(0, len(text), n)]
    dialog_box_wrapper = DialogBoxWrapper(width=text_wrap_length, break_long_words=False)
    chunks = dialog_box_wrapper.wrap(text)
    for chunk in chunks:
        # TODO(ELF): Add letter by letter text scrolling.
        # if letter_by_letter:
        #     for letter in chunk:
        #         text_surface = font.Font(font_name, size).render(letter, True, color, BLACK)
        #         text_rect = text_surface.get_rect()
        #         if center_align:
        #             text_rect.midtop = (x, y_position)
        #         else:
        #             text_rect.midleft = (x, y_position)
        #         screen.blit(text_surface, text_rect)
        # else:
        if LANGUAGE == 'ko':
            if not text.strip('’(↑ ← ↓ →)').isascii():
                current_font = font.Font(UNIFONT_PATH, size + 1)
            else:
                current_font = font.Font(font_name, size)
        else:
            current_font = font.Font(font_name, size)
        text_surface = current_font.render(chunk, True, color, BLACK)
        text_rect = text_surface.get_rect()
        match alignment:
            case 'left':
                text_rect.midleft = (x, y)
            case 'center':
                text_rect.midtop = (x, y)
            case 'right':
                text_rect.midright = (x, y)
        screen.blit(text_surface, text_rect)
        y += 17
        if chunk == chunks[len(chunks) - 1]:
            return chunk
