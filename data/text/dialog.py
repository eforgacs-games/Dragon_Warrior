from pygame import display, KEYDOWN, K_DOWN, K_UP, K_w, K_s, event
from pygame.event import get

from src.cursor import BlinkingCursor
from src.waiting import quit_if_requested, wait
from src.windows import YES_NO_WINDOW


def confirmation_prompt(command_menu, prompt_line, yes_path_function, no_path_function, config, color,
                        show_arrow=True, finally_function=None, skip_text=False):
    """A line of dialog, then the YES/NO window (YesNo1Dat), with the NES cursor (src/cursor.py).

    show_arrow is no longer used: the cursor's blink is timed by the window itself (BlinkingCursor), as the NES
    times it off the frame counter. It is still accepted so callers that pass it keep working."""
    def display_prompt():
        command_menu.show_line_in_dialog_box(prompt_line, skip_text=True, hide_arrow=True, letter_by_letter=True)
        command_menu.window_drop_down_effect(5, 2, 4, 3)
        window_surface = graphics.create_window(5, 2, 4, 3, directories.CONFIRMATION_BACKGROUND_PATH,
                                                command_menu.screen, color)
        display.update(window_surface.get_rect())
        # for some reason it needs this wait() call to actually play the sound
        wait(300, config)
        sound.play_sound(directories.confirmation_sfx)

    def handle_keydown_event(current_event, blinking_yes):
        nonlocal blinking
        if current_event.key in (K_DOWN, K_UP, K_w, K_s):
            cursor.restart()  # WndUpdateCrsrPos
            return not blinking_yes
        elif (blinking_yes and current_event.unicode in ('\r', 'k')) or current_event.unicode == 'y':
            finalize_choice(True, yes_path_function)
            blinking = False
        elif (not blinking_yes and current_event.unicode in ('\r', 'k')) or current_event.unicode in ('n', 'j'):
            finalize_choice(False, no_path_function)
            blinking = False
        return blinking_yes

    def finalize_choice(yes_chosen, path_function):
        # WndAPressed: the chosen entry's arrow is drawn once more and stays on
        command_menu.draw_yes_no_window(yes_chosen, True)
        sound.play_sound(directories.menu_button_sfx)
        event.pump()
        # NES WindowSequence (Bank01): the answered YES/NO window is removed (RemoveWindow) before the answer is acted on
        command_menu.remove_window(YES_NO_WINDOW)
        path_function()

    def handle_events(blinking_yes):
        for current_event in get():
            quit_if_requested(current_event)
            if current_event.type == KEYDOWN:
                blinking_yes = handle_keydown_event(current_event, blinking_yes)
                if not blinking:
                    # A choice was made: drop the rest of this batch so extra presses don't choose again (#97)
                    break
        event.pump()
        return blinking_yes

    # Initialization
    graphics = command_menu.graphics
    directories = command_menu.directories
    sound = command_menu.sound

    display_prompt()

    blinking = True
    blinking_yes = True
    cursor = BlinkingCursor()  # WndInitSelect

    while blinking:
        if skip_text:
            sound.play_sound(directories.menu_button_sfx)
            command_menu.remove_window(YES_NO_WINDOW)
            yes_path_function()
            blinking = False
        else:
            command_menu.draw_yes_no_window(blinking_yes, cursor.visible())
            blinking_yes = handle_events(blinking_yes)

    if finally_function is not None:
        finally_function()
