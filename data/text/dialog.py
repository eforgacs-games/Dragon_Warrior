from pygame import display, image, transform, KEYDOWN, K_DOWN, K_UP, K_w, K_s, event
from pygame.event import get

from src.common import WHITE, BLACK, CONFIRMATION_YES_BACKGROUND_PATH, CONFIRMATION_BACKGROUND_PATH, \
    CONFIRMATION_NO_BACKGROUND_PATH, play_sound, confirmation_sfx, menu_button_sfx
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
        command_menu.create_window(x, y, width, height, image_1)
        display.flip()
    for i in range(time):
        command_menu.create_window(x, y, width, height, image_2)
        display.flip()


def confirmation_prompt(command_menu, prompt_line, yes_path_function, no_path_function, finally_function=None, skip_text=False):
    command_menu.show_line_in_dialog_box(prompt_line, skip_text=True)
    command_menu.window_drop_down_effect(4, 3, 5, 2)
    command_menu.create_window(5, 2, 4, 3, CONFIRMATION_BACKGROUND_PATH)
    display.flip()
    play_sound(confirmation_sfx)
    blinking = True
    blinking_yes = True
    while blinking:
        if blinking_yes:
            blink_yes_confirmation(command_menu)
        else:
            blink_no_confirmation(command_menu)
        if skip_text:
            play_sound(menu_button_sfx)
            yes_path_function()
            blinking = False
        for current_event in get():
            if current_event.type == KEYDOWN:
                if current_event.key in (K_DOWN, K_UP, K_w, K_s):
                    if blinking_yes:
                        command_menu.create_window(5, 2, 4, 3, CONFIRMATION_NO_BACKGROUND_PATH)
                        blinking_yes = False
                    else:
                        command_menu.create_window(5, 2, 4, 3, CONFIRMATION_YES_BACKGROUND_PATH)
                        blinking_yes = True
                elif (blinking_yes and current_event.unicode in ('\r', 'k')) or current_event.unicode == 'y':
                    command_menu.create_window(5, 2, 4, 3, CONFIRMATION_YES_BACKGROUND_PATH)
                    play_sound(menu_button_sfx)
                    event.pump()
                    yes_path_function()
                    blinking = False
                elif (not blinking_yes and current_event.unicode in ('\r', 'k')) or current_event.unicode in ('n', 'j'):
                    command_menu.create_window(5, 2, 4, 3, CONFIRMATION_NO_BACKGROUND_PATH)
                    play_sound(menu_button_sfx)
                    event.pump()
                    no_path_function()
                    blinking = False
        event.pump()

    if finally_function is not None:
        finally_function()


def get_inn_intro(inn_cost):
    return "Welcome to the traveler's Inn.\n" \
           f"Room and board is {inn_cost} GOLD per night.\n" \
           "Dost thou want a room?"
