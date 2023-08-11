from pygame import display, KEYDOWN, K_DOWN, K_UP, K_w, K_s, event, Rect, time, USEREVENT, Surface
from pygame.event import get
from pygame.time import get_ticks

from src.common import WHITE, BLACK, CONFIRMATION_YES_BACKGROUND_PATH, CONFIRMATION_BACKGROUND_PATH, \
    CONFIRMATION_NO_BACKGROUND_PATH, play_sound, confirmation_sfx, menu_button_sfx, create_window, \
    convert_to_frames_since_start_time
from src.text import draw_text


def blink_arrow(x: float, y: float, direction: str, screen: Surface, config: dict, color: tuple = WHITE):
    # TODO(ELF): There is a lingering lag/input issue in this method that needs to be fixed.
    #  Make the arrow show or not based on the arrow_fade event/show_arrow boolean
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
    draw_text(arrow_character, x, y, screen, config, BLACK, letter_by_letter=False)
    display.update(arrow_screen_portion)
    while convert_to_frames_since_start_time(down_arrow_start) <= 16:
        pass
    while 16 < convert_to_frames_since_start_time(down_arrow_start) <= 32:
        draw_text(arrow_character, x, y, screen, config, color, letter_by_letter=False)
        display.update(arrow_screen_portion)


def confirmation_prompt(command_menu, prompt_line, yes_path_function, no_path_function, config, show_arrow,
                        finally_function=None, skip_text=False, color=WHITE):
    command_menu.show_line_in_dialog_box(prompt_line, skip_text=True, hide_arrow=True, letter_by_letter=True)
    command_menu.window_drop_down_effect(5, 2, 4, 3)
    window_surface = create_window(5, 2, 4, 3, CONFIRMATION_BACKGROUND_PATH, command_menu.screen, color)
    display.update(window_surface.get_rect())
    # for some reason it needs this wait() call to actually play the sound
    if not config['NO_WAIT']:
        time.wait(300)
    play_sound(confirmation_sfx)
    blinking = True
    blinking_yes = True
    arrow_fade = USEREVENT + 1
    time.set_timer(arrow_fade, 530)
    while blinking:
        tile_size = config["TILE_SIZE"]
        if blinking_yes and not config['NO_WAIT']:
            blink_switch(command_menu.screen, CONFIRMATION_YES_BACKGROUND_PATH, CONFIRMATION_BACKGROUND_PATH,
                         x=5, y=2, width=4, height=3, tile_size=tile_size, show_arrow=show_arrow)
        else:
            blink_switch(command_menu.screen, CONFIRMATION_NO_BACKGROUND_PATH, CONFIRMATION_BACKGROUND_PATH,
                         x=5, y=2,
                         width=4, height=3, tile_size=tile_size, color=color, show_arrow=show_arrow)
        if skip_text:
            play_sound(menu_button_sfx)
            yes_path_function()
            blinking = False
        for current_event in get():
            if current_event.type == KEYDOWN:
                if current_event.key in (K_DOWN, K_UP, K_w, K_s):
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
            elif current_event.type == arrow_fade:
                show_arrow = not show_arrow
        event.pump()

    if finally_function is not None:
        finally_function()


def blink_switch(screen: Surface, image_1: str, image_2: str, x: int, y: int, width: int, height: int, tile_size: int,
                 show_arrow: bool, color: tuple = WHITE) -> Rect:
    """Switches between two images, creating a blinking effect.
    :param screen: the screen to draw on
    :param image_1: the path of the first image to draw (usually the selection image)
    :param image_2: the path of the second image to draw (usually a blank image)
    :param x: the x coordinate of the window
    :param y: the y coordinate of the window
    :param width: the width of the window
    :param height: the height of the window
    :param tile_size: the size of the tiles
    :param show_arrow: whether to show the arrow
    :param color: the color of the window
    :return: the rect of the window
    """
    window_rect = Rect(x * tile_size, y * tile_size, width * tile_size, height * tile_size)
    if show_arrow:
        create_window(x, y, width, height, image_1, screen, color)
    else:
        create_window(x, y, width, height, image_2, screen, color)
    display.update(window_rect)
    return window_rect
