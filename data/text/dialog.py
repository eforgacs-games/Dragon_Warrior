from pygame import display, K_y, K_n, event

from src.cursor import IN_A, IN_B
from src.selection import NO, YES, Answer, run_selection, toggle
from src.translated_window import draw_translated_window
from src.windows import YES_NO_LAYOUT, YES_NO_WINDOW

# Matched by key, not by the typed character, so Caps Lock doesn't matter: Y answers YES and N answers NO, wherever
# the cursor is
YES_NO_HOTKEYS = {K_y: Answer(IN_A, YES), K_n: Answer(IN_B, NO)}


def confirmation_prompt(command_menu, prompt_line, yes_path_function, no_path_function, config, color,
                        show_arrow=True, finally_function=None, skip_text=False):
    """A line of dialog, then the YES/NO window (YesNo1Dat), with the NES cursor (src/cursor.py).

    show_arrow is no longer used: the cursor's blink is timed by the window itself (BlinkingCursor), as the NES
    times it off the frame counter. It is still accepted so callers that pass it keep working."""
    def display_prompt():
        command_menu.show_line_in_dialog_box(prompt_line, skip_text=True, hide_arrow=True, letter_by_letter=True)
        # NES ShowWindow (Bank01, $A194) runs DoWindowPrep before WindowSequence builds the window, and for the YES/NO
        # window (WND_YES_NO1, LAF02) DoWindowPrep plays SFX_CONFIRM (DoConfirmSFX, LAF19): the sound starts as the
        # window starts to drop down
        sound.play_sound(directories.confirmation_sfx)
        command_menu.window_drop_down_effect(*YES_NO_WINDOW)
        # The window without its cursor, until the selection starts below (generated: src/window_renderer.py)
        display.update(draw_translated_window(command_menu.screen, YES_NO_LAYOUT, color, config, command_menu._))

    # Initialization
    directories = command_menu.directories
    sound = command_menu.sound

    display_prompt()

    if skip_text:
        sound.play_sound(directories.menu_button_sfx)
        command_menu.remove_window(YES_NO_WINDOW)
        yes_path_function()
    else:
        # Up and down both switch entries. A answers with the entry under the cursor; B, Escape included, is NO
        # (WndBPressed), as in CommandMenu.prompt_yes_no. The answer's arrow is drawn once more and stays on, and
        # once a choice is made the rest of the keys pressed are dropped, so extra presses don't choose again (#97).
        answer = run_selection(lambda index, visible: command_menu.draw_yes_no_window(index == YES, visible), YES,
                               move=toggle, hotkeys=YES_NO_HOTKEYS, b_index=NO,
                               sound=lambda: sound.play_sound(directories.menu_button_sfx))
        event.pump()
        # NES WindowSequence (Bank01): the answered YES/NO window is removed (RemoveWindow) before the answer is acted on
        command_menu.remove_window(YES_NO_WINDOW)
        if answer.accepted and answer.entry == YES:
            yes_path_function()
        else:
            no_path_function()

    if finally_function is not None:
        finally_function()
