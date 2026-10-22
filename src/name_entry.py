"""The name entry screen, as the NES runs and draws it (Bank03 DoNewQuest, Bank01 WndEnterName and the routines after
it), generated from the window data instead of from screenshots.

The screen: the title menu's NewQuestDat and the open log list LogList123Dat1 stay on the screen, and InitNameWindow
draws NameEntryDat and then AlphabetDat over them (src/windows.py has their layouts). The name is 8 tiles in
NameEntryDat: each starts as the placeholder tile $41 and is replaced by the character entered there
(WndNameCharYPos), and the underscore, a TL_TOP1 tile, is under the next one (WndShowUnderscore).

The input: the alphabet window is a selection window with 11 columns of 6 rows (WndDoSelect), whose last row has
BACK and END; A enters the selected character (WndProcessChar), B and BACK move back one character (WndDoBackspace)
and END ends the name. The 8th character ends it too (WndMaxNameLength).
"""
from functools import lru_cache

from pygame import Surface

from src.color import BLACK
from src.cursor import draw_cursor_tile
from src.window_renderer import NES_TILE, TL_NAME_PLACEHOLDER, TL_TOP1, glyph_tile, render_window, tile_surface
from src.windows import (ADVENTURE_LOG_123_LAYOUT, ALPHABET_BACK, ALPHABET_COLUMNS, ALPHABET_END, ALPHABET_LAYOUT,
                         ALPHABET_ROWS, NAME_ENTRY_LAYOUT, NAME_FIRST_TILE_COLUMN, NAME_LENGTH, NAME_TILE_ROW,
                         NAME_UNDERSCORE_TILE_ROW, NEW_QUEST_LAYOUT, Window)

# The NES screen, in NES pixels (config NES_RES)
NES_SCREEN_SIZE = (256, 240)
# The windows on the name entry screen, in the order the NES draws them: each one is drawn over the ones before
NAME_ENTRY_SCREEN_LAYOUTS = (NEW_QUEST_LAYOUT, ADVENTURE_LOG_123_LAYOUT, NAME_ENTRY_LAYOUT, ALPHABET_LAYOUT)
BACK = 'BACK'
END = 'END'


class NameEntry:
    """What WndEnterName keeps track of: the 8 characters of the name (TempBuffer), where the next one goes
    (WndNameIndex), and the alphabet window's cursor (WndRow and WndCol)."""

    def __init__(self) -> None:
        # None is a character never entered, still showing its placeholder; InitNameWindow fills TempBuffer with
        # blank tiles, so it is a blank in the name
        self.characters: list[str | None] = [None] * NAME_LENGTH
        self.index = 0
        self.row = 0
        self.column = 0

    @property
    def name(self) -> str:
        """The name the NES stores (WndStorePlyrName: all 8 characters of TempBuffer), without its trailing blanks."""
        return ''.join(character or ' ' for character in self.characters).rstrip()

    @property
    def finished(self) -> bool:
        """WndMaxNameLength: the name is done once the index reaches 8, after END or the 8th character."""
        return self.index >= NAME_LENGTH

    @property
    def cursor_index(self) -> int:
        """The selection result of the entry under the cursor (WndCalcAlphaResult: row * 11 + column), which is also
        its index in ALPHABET_LAYOUT.cursor_tiles."""
        return self.row * ALPHABET_COLUMNS + self.column

    @property
    def selection(self) -> str:
        """The entry under the cursor: a character, BACK or END."""
        if (self.row, self.column) == ALPHABET_BACK:
            return BACK
        if (self.row, self.column) == ALPHABET_END:
            return END
        return ALPHABET_ROWS[self.row][self.column]

    # The cursor (WndUpPressed, WndDownPressed, WndDoLeftPressed, WndRightPressed); each returns whether it moved

    def move_up(self) -> bool:
        # WndMoveCursorUp keeps the column, so BACK goes up to r and END to u
        if self.row == 0:
            return False
        self.row -= 1
        return True

    def move_down(self) -> bool:
        if self.row == len(ALPHABET_ROWS) - 1:
            return False
        # WndSpclMoveCrsr: from the row above the last one, column 7 goes down to BACK and columns 8 to 10 to END
        if self.row == ALPHABET_BACK[0] - 1:
            if self.column == ALPHABET_BACK[1] + 1:
                self.column = ALPHABET_BACK[1]
            elif self.column > ALPHABET_BACK[1] + 1:
                self.column = ALPHABET_END[1]
        self.row += 1
        return True

    def move_left(self) -> bool:
        if self.column == 0:
            return False
        # From END, left goes to BACK
        self.column = ALPHABET_BACK[1] if (self.row, self.column) == ALPHABET_END else self.column - 1
        return True

    def move_right(self) -> bool:
        if self.row == ALPHABET_BACK[0] and self.column >= ALPHABET_BACK[1]:
            # From BACK, right goes to END; END is the last entry
            if self.column != ALPHABET_BACK[1]:
                return False
            self.column = ALPHABET_END[1]
            return True
        if self.column == ALPHABET_COLUMNS - 1:
            return False
        self.column += 1
        return True

    def move_to(self, character: str) -> bool:
        """Put the cursor on a character of the alphabet (typing it on the keyboard); False if it isn't in it."""
        for row, characters in enumerate(ALPHABET_ROWS):
            if character and character in characters:
                self.row, self.column = row, characters.index(character)
                return True
        return False

    def move_to_end(self) -> None:
        self.row, self.column = ALPHABET_END

    # The name (WndProcessChar)

    def select(self) -> None:
        """A: enter the character under the cursor, or BACK, or END."""
        selection = self.selection
        if selection == BACK:
            self.back()
        elif selection == END:
            self.end()
        else:
            self.enter(selection)

    def enter(self, character: str) -> None:
        """WndUpdateName: the character replaces the one at the index, which moves on to the next one."""
        if not self.finished:
            self.characters[self.index] = character
            self.index += 1

    def back(self) -> None:
        """WndDoBackspace (B or BACK): only the index moves back. The character stays in the name and on the screen
        until another one replaces it, so END keeps it."""
        if self.index:
            self.index -= 1

    def erase(self) -> None:
        """The keyboard's Backspace (not an NES button): back, and the character is removed, showing its placeholder
        again."""
        if self.index:
            self.index -= 1
            self.characters[self.index] = None

    def end(self) -> None:
        """END: LAE6B sets the index to 8."""
        self.index = NAME_LENGTH


def window_origin(window: Window) -> tuple[int, int]:
    """A window's top left tile on the screen (a block is 2 tiles)."""
    return window.x * 2, window.y * 2


@lru_cache(maxsize=8)
def name_entry_background(color: tuple, nes_pixel: int) -> Surface:
    """The screen's windows, without the name and the cursor. Cached: copy it, don't draw on it."""
    screen = Surface((NES_SCREEN_SIZE[0] * nes_pixel, NES_SCREEN_SIZE[1] * nes_pixel))
    screen.fill(BLACK)
    tile = NES_TILE * nes_pixel
    for layout in NAME_ENTRY_SCREEN_LAYOUTS:
        column, row = window_origin(layout.window)
        screen.blit(render_window(layout, color, nes_pixel), (column * tile, row * tile))
    return screen


def render_name_entry_screen(entry: NameEntry, color: tuple, nes_pixel: int, cursor_visible: bool | None = True
                             ) -> Surface:
    """
    The whole name entry screen.
    :param entry: The name so far and the cursor.
    :param color: The window color.
    :param nes_pixel: Screen pixels per NES pixel (SCALE; TILE_SIZE // 16).
    :param cursor_visible: Whether the alphabet window's cursor is in the "on" half of its blink (src/cursor.py), or
    None for no cursor at all (before WndDoSelect).
    :return: A new surface, NES_SCREEN_SIZE NES pixels, scaled.
    """
    screen = name_entry_background(color, nes_pixel).copy()
    tile = NES_TILE * nes_pixel
    name_column, name_row = window_origin(NAME_ENTRY_LAYOUT.window)
    for slot, character in enumerate(entry.characters):
        pattern = TL_NAME_PLACEHOLDER if character is None else glyph_tile(character)
        screen.blit(tile_surface(pattern, color, nes_pixel),
                    ((name_column + NAME_FIRST_TILE_COLUMN + slot) * tile, (name_row + NAME_TILE_ROW) * tile))
    if not entry.finished:
        screen.blit(tile_surface(TL_TOP1, color, nes_pixel), ((name_column + NAME_FIRST_TILE_COLUMN + entry.index) * tile,
                                                              (name_row + NAME_UNDERSCORE_TILE_ROW) * tile))
    if cursor_visible is not None:
        alphabet_column, alphabet_row = window_origin(ALPHABET_LAYOUT.window)
        column, row = ALPHABET_LAYOUT.cursor_tiles[entry.cursor_index]
        draw_cursor_tile(screen, (alphabet_column + column) * tile, (alphabet_row + row) * tile, nes_pixel, color,
                         cursor_visible)
    return screen
