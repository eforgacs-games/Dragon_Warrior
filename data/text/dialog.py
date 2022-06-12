from pygame import display, image, transform

from src.common import WHITE, BLACK, CONFIRMATION_YES_BACKGROUND_PATH, CONFIRMATION_BACKGROUND_PATH, \
    CONFIRMATION_NO_BACKGROUND_PATH
from src.text import draw_text


def set_window_background(black_box, background_path):
    black_box.fill(BLACK)
    background_image = image.load(background_path)
    background_image = transform.scale(background_image, black_box.get_size())
    black_box.blit(background_image, black_box.get_rect())


def blink_down_arrow(screen):
    for i in range(256):
        draw_text("▼", WHITE, screen.get_width() / 2, (screen.get_height() * 13 / 16) + 32, screen)
        # TODO(ELF): Change display.flip() to display.update() and pass in a rect.
        display.flip()
    for i in range(256):
        draw_text("▼", BLACK, screen.get_width() / 2, (screen.get_height() * 13 / 16) + 32, screen)
        display.flip()


def blink_yes_confirmation(command_menu):
    blink_switch(command_menu, image_1=CONFIRMATION_YES_BACKGROUND_PATH, image_2=CONFIRMATION_BACKGROUND_PATH, width=4, height=3, x=5, y=2)


def blink_no_confirmation(command_menu):
    blink_switch(command_menu, image_1=CONFIRMATION_NO_BACKGROUND_PATH, image_2=CONFIRMATION_BACKGROUND_PATH, width=4, height=3, x=5, y=2)


def blink_switch(command_menu, image_1=CONFIRMATION_YES_BACKGROUND_PATH, image_2=CONFIRMATION_BACKGROUND_PATH, time=512, width=4, height=3, x=5, y=2):
    # not as accurate as the implementation in open_store_inventory,
    # since that one uses the actual 16 frames of screen time for the arrow
    for i in range(time):
        command_menu.create_window(width, height, x, y, image_1)
        display.flip()
    for i in range(time):
        command_menu.create_window(width, height, x, y, image_2)
        display.flip()
