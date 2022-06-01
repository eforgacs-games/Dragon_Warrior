import textwrap

from pygame import font, draw

from src.common import BLACK, WHITE


class DialogBoxWrapper(textwrap.TextWrapper):

    def wrap(self, text):
        split_text = text.split('\n')
        lines = [line for para in split_text for line in textwrap.TextWrapper.wrap(self, para)]
        return lines


def draw_text(text, size, color, x, y, font_name, screen, center_align=True, text_wrap_length=21):
    # n = 34
    # 34 is the maximum characters on the screen at a time.
    # 21? appears to be the actual max in the original game
    # chunks = [text[i:i + n] for i in range(0, len(text), n)]
    y_position = y
    dialog_box_wrapper = DialogBoxWrapper(width=text_wrap_length, break_long_words=False)
    chunks = dialog_box_wrapper.wrap(text)
    for chunk in chunks:
        text_surface = font.Font(font_name, size).render(chunk, True, color, BLACK)
        text_rect = text_surface.get_rect()
        if center_align:
            text_rect.midtop = (x, y_position)
        else:
            text_rect.midleft = (x, y_position)
        screen.blit(text_surface, text_rect)
        y_position += 16
        if chunk == chunks[len(chunks) - 1]:
            return chunk


def draw_text_with_rectangle(text, size, color, x, y, font_name, screen):
    text_surface = font.Font(font_name, size).render(text, True, color, BLACK)
    text_rect = text_surface.get_rect()
    draw.rect(text_surface, WHITE, text_rect, width=1)
    text_rect.midtop = (x, y)
    screen.blit(text_surface, text_rect)
