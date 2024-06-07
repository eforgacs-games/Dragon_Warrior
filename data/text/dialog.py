from pygame import display, KEYDOWN, K_DOWN, K_UP, K_w, K_s, event, time, USEREVENT
from pygame.event import get


def confirmation_prompt(command_menu, prompt_line, yes_path_function, no_path_function, config, show_arrow, color,
                        finally_function=None, skip_text=False):
    def display_prompt():
        command_menu.show_line_in_dialog_box(prompt_line, skip_text=True, hide_arrow=True, letter_by_letter=True)
        command_menu.window_drop_down_effect(5, 2, 4, 3)
        window_surface = graphics.create_window(5, 2, 4, 3, directories.CONFIRMATION_BACKGROUND_PATH,
                                                command_menu.screen, color)
        display.update(window_surface.get_rect())
        # for some reason it needs this wait() call to actually play the sound
        if not config['NO_WAIT']:
            time.wait(300)
        sound.play_sound(directories.confirmation_sfx)

    def update_blinking_graphics(blinking_yes, show_arrow):
        background_path = directories.CONFIRMATION_YES_BACKGROUND_PATH if blinking_yes else directories.CONFIRMATION_NO_BACKGROUND_PATH
        graphics.blink_switch(command_menu.screen, background_path, directories.CONFIRMATION_BACKGROUND_PATH,
                              x=5, y=2, width=4, height=3, tile_size=tile_size, color=color, show_arrow=show_arrow)

    def handle_keydown_event(current_event, blinking_yes):
        nonlocal blinking
        if current_event.key in (K_DOWN, K_UP, K_w, K_s):
            return not blinking_yes
        elif (blinking_yes and current_event.unicode in ('\r', 'k')) or current_event.unicode == 'y':
            finalize_choice(directories.CONFIRMATION_YES_BACKGROUND_PATH, yes_path_function)
            blinking = False
        elif (not blinking_yes and current_event.unicode in ('\r', 'k')) or current_event.unicode in ('n', 'j'):
            finalize_choice(directories.CONFIRMATION_NO_BACKGROUND_PATH, no_path_function)
            blinking = False
        return blinking_yes

    def finalize_choice(background_path, path_function):
        graphics.create_window(5, 2, 4, 3, background_path, command_menu.screen, color)
        sound.play_sound(directories.menu_button_sfx)
        event.pump()
        path_function()

    def handle_events(blinking_yes):
        nonlocal show_arrow
        for current_event in get():
            if current_event.type == KEYDOWN:
                blinking_yes = handle_keydown_event(current_event, blinking_yes)
            elif current_event.type == arrow_fade:
                show_arrow = not show_arrow
        event.pump()
        return blinking_yes

    # Initialization
    graphics = command_menu.graphics
    directories = command_menu.directories
    sound = command_menu.sound
    tile_size = config["TILE_SIZE"]

    display_prompt()

    blinking = True
    blinking_yes = True
    arrow_fade = USEREVENT + 1
    time.set_timer(arrow_fade, 530)

    while blinking:
        if skip_text:
            sound.play_sound(directories.menu_button_sfx)
            yes_path_function()
            blinking = False
        else:
            update_blinking_graphics(blinking_yes, show_arrow)
            blinking_yes = handle_events(blinking_yes)

    if finally_function is not None:
        finally_function()
