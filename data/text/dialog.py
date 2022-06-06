from pygame import display, image, transform

from src.common import WHITE, DRAGON_QUEST_FONT_PATH, BLACK
from src.text import draw_text


def set_window_background(black_box, background_path):
    black_box.fill(BLACK)
    dialog_box_background = image.load(background_path)
    dialog_box_background = transform.scale(dialog_box_background, black_box.get_size())
    black_box.blit(dialog_box_background, black_box.get_rect())


def blink_down_arrow(screen):
    for i in range(256):
        draw_text("▼", 15, WHITE, screen.get_width() / 2, (screen.get_height() * 13 / 16) + 32, DRAGON_QUEST_FONT_PATH, screen)
        # TODO(ELF): Change display.flip() to display.update() and pass in a rect.
        display.flip()
    for i in range(256):
        draw_text("▼", 15, BLACK, screen.get_width() / 2, (screen.get_height() * 13 / 16) + 32, DRAGON_QUEST_FONT_PATH, screen)
        display.flip()


