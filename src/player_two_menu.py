"""Player 2's command window on the map (co-op, src/party.py). Not NES.

Player 2's A (the P2 A action: numpad 0, player 2's controller, or player 2's window in network play, src/netplay.py)
opens the second hero's own command window on the map, once everyone has finished their step, as the map's other
windows open (src/map_hotkeys.py MAP_REQUESTS). It's titled with the second hero's name and has the commands that are
the hero's own:

    +-GWEN----+
    | > ITEM  |
    |   SPELL |
    |   STATUS|
    +---------+

The window and what it opens run on player 2's joypad (src/controls.py player_input) with the second hero as the
player (party.acting): ITEM and SPELL as when player 1 chooses the second hero for them (src/menu.py: the cost is the
second hero's; what acts for the party works where the first hero stands), STATUS the second hero's alone. B closes
it. The commands that are done where the party stands (TALK, SEARCH, DOOR, STAIRS, TAKE) are the first hero's, on
player 1's COMMAND window.
"""
from typing import TYPE_CHECKING

from pygame import display

from src.controls import PLAYER_TWO, player_input
from src.party import acting, companion_of
from src.selection import run_selection, stop_at_edges
from src.translated_window import draw_translated_window
from src.windows import Window, WindowLayout, WindowText, selection_cursor_tiles

if TYPE_CHECKING:
    from src.game import Game  # src.game imports this module (through src.map_hotkeys)

ITEM, SPELL, STATUS = "ITEM", "SPELL", "STATUS"
COMMANDS = (ITEM, SPELL, STATUS)
# Where player 1's COMMAND window opens (src/windows.py COMMAND_WINDOW): never at the same time as this one
MENU_WINDOW = Window(6, 1, 6, len(COMMANDS) + 1)
TEXT_COLUMN = 2


def menu_layout(name: str) -> WindowLayout:
    return WindowLayout(
        window=MENU_WINDOW, title=WindowText(name, 2, 0),
        texts=tuple(WindowText(command, TEXT_COLUMN, 2 + 2 * number) for number, command in enumerate(COMMANDS)),
        cursor_tiles=selection_cursor_tiles(home_column=1, home_row=2, columns=1, column_spacing=0,
                                            rows=len(COMMANDS)))


def open_player_two_menu(game: 'Game') -> None:
    """Player 2's command window (see the module docstring); nothing without a second hero."""
    hero = companion_of(game)
    if hero is None:
        return
    cmd_menu = game.cmd_menu
    config = game.game_state.config
    layout = menu_layout(hero.name)
    with acting(game, hero), player_input(PLAYER_TWO):
        covered = cmd_menu.covered_area(layout.window)
        cmd_menu.play_menu_button_sound()

        def draw(index: int, cursor_visible: bool) -> None:
            rect = draw_translated_window(game.screen, layout, game.color, config, cmd_menu._, cursor_index=index,
                                          cursor_visible=cursor_visible)
            if not config.get('NO_BLIT'):
                display.update(rect)

        answer = run_selection(draw, 0, move=stop_at_edges(len(COMMANDS)), sound=cmd_menu.play_menu_button_sound)
        cmd_menu.remove_window(layout.window, covered)
        if answer.accepted:
            command = COMMANDS[answer.entry]
            if command == ITEM:
                cmd_menu.use_an_item()
            elif command == SPELL:
                cmd_menu.cast_a_spell()
            else:
                cmd_menu.show_status_of([hero])
    game.game_state.unpause_all_movement()
