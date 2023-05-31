from pygame import display, KEYDOWN, K_DOWN, K_UP, K_w, K_s, event, Rect, time
from pygame.event import get
from pygame.time import get_ticks

from src.common import WHITE, BLACK, CONFIRMATION_YES_BACKGROUND_PATH, CONFIRMATION_BACKGROUND_PATH, \
    CONFIRMATION_NO_BACKGROUND_PATH, play_sound, confirmation_sfx, menu_button_sfx, create_window, \
    convert_to_frames_since_start_time
from src.text import draw_text


def blink_arrow(x, y, direction, screen, config: dict, color=WHITE):
    if direction == 'up':
        arrow_character = '^'
    elif direction == "down":
        arrow_character = "▼"
    elif direction == "left":
        arrow_character = "<"
    elif direction == "right":
        arrow_character = ">"
    else:
        arrow_character = ""
    down_arrow_start = get_ticks()
    if convert_to_frames_since_start_time(down_arrow_start) > 32:
        down_arrow_start = get_ticks()
    arrow_screen_portion = Rect(x, y, config["TILE_SIZE"], config["TILE_SIZE"])
    while convert_to_frames_since_start_time(down_arrow_start) <= 16:
        draw_text(arrow_character, x, y, screen, config, color, letter_by_letter=False)
        display.update(arrow_screen_portion)
    while 16 < convert_to_frames_since_start_time(down_arrow_start) <= 32:
        draw_text(arrow_character, x, y, screen, config, BLACK, letter_by_letter=False)
        display.update(arrow_screen_portion)


def blink_switch(screen, image_1, image_2, x, y, width, height, start, config, color=WHITE):
    blink_start = start
    image_rect = Rect(x * config["TILE_SIZE"], y * config["TILE_SIZE"], width * config["TILE_SIZE"],
                      height * config["TILE_SIZE"])
    if convert_to_frames_since_start_time(blink_start) > 32:
        blink_start = get_ticks()
    while convert_to_frames_since_start_time(blink_start) <= 16:
        create_window(x, y, width, height, image_1, screen, color)
        display.update(image_rect)
    while 16 < convert_to_frames_since_start_time(blink_start) <= 32:
        create_window(x, y, width, height, image_2, screen, color)
        display.update(image_rect)


def confirmation_prompt(command_menu, prompt_line, yes_path_function, no_path_function, config, finally_function=None,
                        skip_text=False, color=WHITE):
    command_menu.show_line_in_dialog_box(prompt_line, skip_text=True, last_line=True, letter_by_letter=True)
    command_menu.window_drop_down_effect(5, 2, 4, 3)
    window_surface = create_window(5, 2, 4, 3, CONFIRMATION_BACKGROUND_PATH, command_menu.screen, color)
    display.update(window_surface.get_rect())
    # for some reason it needs this wait() call to actually play the sound
    if not config['NO_WAIT']:
        time.wait(300)
    play_sound(confirmation_sfx)
    blinking = True
    blinking_yes = True
    blink_start = get_ticks()
    while blinking:
        if blinking_yes and not config['NO_WAIT']:
            blink_switch(command_menu.screen, CONFIRMATION_YES_BACKGROUND_PATH, CONFIRMATION_BACKGROUND_PATH, x=5, y=2,
                         width=4, height=3, start=blink_start, config=config, color=color)
        else:
            blink_switch(command_menu.screen, CONFIRMATION_NO_BACKGROUND_PATH, CONFIRMATION_BACKGROUND_PATH, x=5, y=2,
                         width=4, height=3, start=blink_start, config=config, color=color)
        if skip_text:
            play_sound(menu_button_sfx)
            yes_path_function()
            blinking = False
        for current_event in get():
            if current_event.type == KEYDOWN:
                if current_event.key in (K_DOWN, K_UP, K_w, K_s):
                    blink_start = get_ticks()
                    if blinking_yes:
                        create_window(5, 2, 4, 3, CONFIRMATION_NO_BACKGROUND_PATH, command_menu.screen, color)
                        blinking_yes = False
                    else:
                        create_window(5, 2, 4, 3, CONFIRMATION_YES_BACKGROUND_PATH, command_menu.screen, color)
                        blinking_yes = True
                elif (blinking_yes and current_event.unicode in ('\r', 'k')) or current_event.unicode == 'y':
                    create_window(5, 2, 4, 3, CONFIRMATION_YES_BACKGROUND_PATH, command_menu.screen, color)
                    play_sound(menu_button_sfx)
                    event.pump()
                    yes_path_function()
                    blinking = False
                elif (not blinking_yes and current_event.unicode in ('\r', 'k')) or current_event.unicode in ('n', 'j'):
                    create_window(5, 2, 4, 3, CONFIRMATION_NO_BACKGROUND_PATH, command_menu.screen, color)
                    play_sound(menu_button_sfx)
                    event.pump()
                    no_path_function()
                    blinking = False
        event.pump()

    if finally_function is not None:
        finally_function()
