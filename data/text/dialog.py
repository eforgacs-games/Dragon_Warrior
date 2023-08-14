from pygame import display, KEYDOWN, K_DOWN, K_UP, K_w, K_s, event, time, USEREVENT
from pygame.event import get

from src.common import WHITE


def confirmation_prompt(command_menu, prompt_line, yes_path_function, no_path_function, config, show_arrow,
                        finally_function=None, skip_text=False, color=WHITE):
    command_menu.show_line_in_dialog_box(prompt_line, skip_text=True, hide_arrow=True, letter_by_letter=True)
    command_menu.window_drop_down_effect(5, 2, 4, 3)
    graphics = command_menu.graphics
    directories = command_menu.directories
    sound = command_menu.sound
    window_surface = graphics.create_window(5, 2, 4, 3, directories.CONFIRMATION_BACKGROUND_PATH, command_menu.screen,
                                            color)
    display.update(window_surface.get_rect())
    # for some reason it needs this wait() call to actually play the sound
    if not config['NO_WAIT']:
        time.wait(300)

    sound.play_sound(directories.confirmation_sfx)
    blinking = True
    blinking_yes = True
    arrow_fade = USEREVENT + 1
    time.set_timer(arrow_fade, 530)
    while blinking:
        tile_size = config["TILE_SIZE"]
        if blinking_yes and not config['NO_WAIT']:
            graphics.blink_switch(command_menu.screen, directories.CONFIRMATION_YES_BACKGROUND_PATH,
                                  directories.CONFIRMATION_BACKGROUND_PATH,
                                  x=5, y=2, width=4, height=3, tile_size=tile_size, show_arrow=show_arrow)
        else:
            graphics.blink_switch(command_menu.screen, directories.CONFIRMATION_NO_BACKGROUND_PATH,
                                  directories.CONFIRMATION_BACKGROUND_PATH,
                                  x=5, y=2,
                                  width=4, height=3, tile_size=tile_size, color=color, show_arrow=show_arrow)
        if skip_text:
            sound.play_sound(directories.menu_button_sfx)
            yes_path_function()
            blinking = False
        for current_event in get():
            if current_event.type == KEYDOWN:
                if current_event.key in (K_DOWN, K_UP, K_w, K_s):
                    if blinking_yes:
                        graphics.create_window(5, 2, 4, 3, directories.CONFIRMATION_NO_BACKGROUND_PATH,
                                               command_menu.screen, color)
                        blinking_yes = False
                    else:
                        graphics.create_window(5, 2, 4, 3, directories.CONFIRMATION_YES_BACKGROUND_PATH,
                                               command_menu.screen, color)
                        blinking_yes = True
                elif (blinking_yes and current_event.unicode in ('\r', 'k')) or current_event.unicode == 'y':
                    graphics.create_window(5, 2, 4, 3, directories.CONFIRMATION_YES_BACKGROUND_PATH,
                                           command_menu.screen, color)
                    sound.play_sound(directories.menu_button_sfx)
                    event.pump()
                    yes_path_function()
                    blinking = False
                elif (not blinking_yes and current_event.unicode in ('\r', 'k')) or current_event.unicode in ('n', 'j'):
                    graphics.create_window(5, 2, 4, 3, directories.CONFIRMATION_NO_BACKGROUND_PATH, command_menu.screen,
                                           color)
                    sound.play_sound(directories.menu_button_sfx)
                    event.pump()
                    no_path_function()
                    blinking = False
            elif current_event.type == arrow_fade:
                show_arrow = not show_arrow
        event.pump()

    if finally_function is not None:
        finally_function()
