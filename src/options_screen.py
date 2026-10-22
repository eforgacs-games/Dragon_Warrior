"""The title menu's CHANGE MESSAGE SPEED: pick an adventure log, then its message speed (the NES window) and its dialog
style (a modern option this game adds below the NES behaviour, which stays the default).

NES flow (Bank03):

- DoChngMsgSpeed lists the used adventure logs (ShowUsedLogs: windows LogList1Dat2 ... LogList123Dat2). B goes back
  to the title menu (WndBackToMain).
- ShowChngMsgSpeed loads the chosen log (Copy100Times -> LoadSavedData, which reads its MessageSpeed byte) and shows
  WND_MSG_SPEED (Bank01 MsgSpeedDat). The window opens with the cursor on the log's current speed (Bank01 LA937: "Use
  current message speed to set the cursor in the window", WndRow = MessageSpeed). B goes back to the title menu without
  saving.
- ChngMsgSpeed stores the choice in MessageSpeed, saves the log (SaveCurrentGame -> SaveData, LFA7D: game slot offset
  $16, "Message Speed" in reference/sram-doc.txt: 0 fast, 1 normal, 2 slow) and goes back to the title menu.
- A new quest (DoNewQuest -> NewQuest) shows the same window right after the name is entered, with the cursor on
  NORMAL (LF8D4: LDA #MSG_NORMAL), and InitNewGame saves the choice with the new log.

What this game adds: a DIALOG STYLE window above the speed window, drawn the same way. CLASSIC is the NES dialog
window, whose text scrolls up a row at a time (src/dialog_box.py); MODERN is how this game drew dialog before it
copied the NES: each message on a fresh window, replacing the one before. After the speed is chosen the cursor moves
to it; B there goes back to the speed.
"""
from typing import Callable, Iterable, List, Sequence, Tuple

from pygame import K_DOWN, K_UP, K_s, K_w, KEYDOWN, Rect, Surface, display, event

from src.color import BLACK, WHITE
from src.common import Graphics, accept_keys, reject_keys
from src.directories import Directories
from src.cursor import BlinkingCursor, draw_cursor_tile
from src.sound import Sound
from src.text import draw_text
from src.waiting import quit_if_requested
from src.windows import ADVENTURE_LOG_WINDOW_2, ITEM_MENU_BORDER, MESSAGE_SPEED_WINDOW, Window, variable_height_window

# The save file keys (CommandMenu.save, Game.load_game): one per adventure log, like the NES MessageSpeed byte
MESSAGE_SPEED_SAVE_KEY = 'MessageSpeed'
DIALOG_STYLE_SAVE_KEY = 'DialogStyle'

# MessageSpeed: #$00-fast, #$01-normal, #$02-slow; the window lists them in that order (WndRow = MessageSpeed)
MESSAGE_SPEED_NAMES = ('Fast', 'Normal', 'Slow')
# NewQuest (LF8D4): a new quest starts at normal speed; a save without the setting loads as normal too
DEFAULT_MESSAGE_SPEED = 'Normal'

CLASSIC = 'Classic'  # the NES dialog window (src/dialog_box.py), the default
MODERN = 'Modern'  # each message replaces the last one, as this game drew dialog before it matched the NES
DIALOG_STYLES = (CLASSIC, MODERN)
DEFAULT_DIALOG_STYLE = CLASSIC

# MsgSpeedDat ($B194): single spaced, 18 tiles wide. " Which Message", " Speed Do You" and " Want To Use?" on tile rows
# 1, 3 and 5 (a blank tile, then the text from column 2); FAST, NORMAL and SLOW on rows 8, 10 and 12 after 6 blank
# tiles (column 7); cursor home Y = 8, X = 6 ($86), and the cursor moves 2 rows per entry.
MESSAGE_SPEED_PROMPT = ((2, 1, 'Which Message'), (2, 3, 'Speed Do You'), (2, 5, 'Want To Use?'))
MESSAGE_SPEED_LABELS = ('FAST', 'NORMAL', 'SLOW')
MESSAGE_SPEED_FIRST_ROW = 8
MESSAGE_SPEED_TEXT_COLUMN = 7
MESSAGE_SPEED_CURSOR_COLUMN = 6

# The dialog style window: not on the NES. The same width and column as MsgSpeedDat, directly above it (block rows 3
# to 6), laid out the same way: a prompt on row 1, the entries 2 rows apart from row 3, the cursor in the tile before.
DIALOG_STYLE_WINDOW = Window(MESSAGE_SPEED_WINDOW.x, MESSAGE_SPEED_WINDOW.y - 4, MESSAGE_SPEED_WINDOW.width, 4)
DIALOG_STYLE_PROMPT = ((2, 1, 'Dialog Style'),)
DIALOG_STYLE_LABELS = ('CLASSIC (NES)', 'MODERN')
DIALOG_STYLE_FIRST_ROW = 3
DIALOG_STYLE_TEXT_COLUMN = 3
DIALOG_STYLE_CURSOR_COLUMN = 2

# LogList1Dat2 ... LogList123Dat2 (see src/adventure_log.py): " ADVENTURE LOG n:" and the first 4 letters of the
# name; the first line on tile row 2 of the window, one block apart; the cursor in column 1, the text from column 2
LOG_FIRST_ROW = 2
LOG_TEXT_COLUMN = 2
LOG_CURSOR_COLUMN = 1
LOG_NAME_LETTERS = 4

ENTRY_SPACING = 2  # every window here is single spaced with a blank row between entries: 2 tile rows per entry


def message_speed_from_save(save: dict) -> str:
    """The log's message speed (LoadSavedData, LFBC8); a save from before it was kept loads as NORMAL."""
    speed = save.get(MESSAGE_SPEED_SAVE_KEY)
    return speed if speed in MESSAGE_SPEED_NAMES else DEFAULT_MESSAGE_SPEED


def dialog_style_from_save(save: dict) -> str:
    """The log's dialog style; a save from before it was kept loads as CLASSIC (the NES)."""
    style = save.get(DIALOG_STYLE_SAVE_KEY)
    return style if style in DIALOG_STYLES else DEFAULT_DIALOG_STYLE


def apply_options(config: dict, message_speed: str, dialog_style: str) -> None:
    """Use these settings from now on: the dialog code reads TEXT_SPEED and DIALOG_STYLE for every message."""
    config['TEXT_SPEED'] = message_speed
    config['DIALOG_STYLE'] = dialog_style


class OptionWindow:
    """One selection window: its place, fixed text, entries and where its cursor goes."""

    def __init__(self, window: Window, prompt: Iterable[Tuple[int, int, str]], labels: Sequence[str], first_row: int,
                 text_column: int, cursor_column: int):
        self.window = window
        self.prompt = tuple(prompt)
        self.labels = tuple(labels)
        self.first_row = first_row
        self.text_column = text_column
        self.cursor_column = cursor_column

    def entry_row(self, index: int) -> int:
        return self.first_row + ENTRY_SPACING * index


MESSAGE_SPEED_OPTIONS = OptionWindow(MESSAGE_SPEED_WINDOW, MESSAGE_SPEED_PROMPT, MESSAGE_SPEED_LABELS,
                                     MESSAGE_SPEED_FIRST_ROW, MESSAGE_SPEED_TEXT_COLUMN, MESSAGE_SPEED_CURSOR_COLUMN)
DIALOG_STYLE_OPTIONS = OptionWindow(DIALOG_STYLE_WINDOW, DIALOG_STYLE_PROMPT, DIALOG_STYLE_LABELS,
                                    DIALOG_STYLE_FIRST_ROW, DIALOG_STYLE_TEXT_COLUMN, DIALOG_STYLE_CURSOR_COLUMN)


def adventure_log_options(logs: Sequence[Tuple[int, str]]) -> OptionWindow:
    """The used logs window (LogList*Dat2): one line per log, " ADVENTURE LOG n:" and 4 letters of the hero's name."""
    window = variable_height_window(ADVENTURE_LOG_WINDOW_2, len(logs))
    labels = [f'ADVENTURE LOG {slot}:{name[:LOG_NAME_LETTERS]}' for slot, name in logs]
    return OptionWindow(window, (), labels, LOG_FIRST_ROW, LOG_TEXT_COLUMN, LOG_CURSOR_COLUMN)


class OptionsScreen:
    """Draws the title menu's windows over a background (the title menu screenshot, or black) and runs their cursors.

    Each window keeps its cursor: the one being chosen from blinks like every NES window cursor (src/cursor.py), the
    others hold theirs on their choice, as the NES leaves a chosen entry's arrow on behind the windows it opens."""

    def __init__(self, screen: Surface, config: dict, background: str | None = None):
        self.screen = screen
        self.config = config
        self.background = background
        self.graphics = Graphics(config)
        self.directories = Directories(config)
        self.sound = Sound(config)
        # windows on screen, bottom to top, each with the entry its cursor is on
        self.windows: List[Tuple[OptionWindow, int]] = []

    def choose_log(self, logs: Sequence[Tuple[int, str]]) -> int | None:
        """DoChngMsgSpeed -> ShowUsedLogs: the chosen log's number, or None for B."""
        log_window = adventure_log_options(logs)
        self.windows = [(log_window, 0)]
        index = self.select(0)
        return None if index is None else logs[index][0]

    def choose_options(self, message_speed: str, dialog_style: str) -> Tuple[str, str] | None:
        """WND_MSG_SPEED, then the dialog style: the chosen (message speed, dialog style), or None if B was pressed in
        the speed window (WndBackToMain). The cursors start on the current settings (LA93E: WndRow = MessageSpeed)."""
        speed_index = MESSAGE_SPEED_NAMES.index(message_speed)
        style_index = DIALOG_STYLES.index(dialog_style)
        base = list(self.windows)
        while True:
            self.windows = base + [(DIALOG_STYLE_OPTIONS, style_index), (MESSAGE_SPEED_OPTIONS, speed_index)]
            chosen_speed = self.select(len(self.windows) - 1)
            if chosen_speed is None:
                self.windows = base
                return None
            speed_index = chosen_speed
            chosen_style = self.select(len(self.windows) - 2)
            if chosen_style is not None:
                return MESSAGE_SPEED_NAMES[speed_index], DIALOG_STYLES[chosen_style]

    def select(self, active: int) -> int | None:
        """Moves the cursor of self.windows[active] until A (the entry's index) or B (None), like the NES selection
        windows (WndDoSelect): up and down stop at the first and last entry."""
        options, index = self.windows[active]
        cursor = BlinkingCursor()  # WndInitSelect
        drawn = None
        while True:
            visible = cursor.visible()
            if drawn != (index, visible):
                self.windows[active] = (options, index)
                self.draw(active, visible)
                drawn = (index, visible)
            for current_event in event.get():
                quit_if_requested(current_event)
                if current_event.type != KEYDOWN:
                    continue
                if current_event.key in accept_keys:
                    # WndAPressed: the chosen entry's arrow is drawn once more and stays on
                    cursor.hold()
                    self.draw(active, True)
                    self.sound.play_sound(self.directories.menu_button_sfx)
                    return index
                if current_event.key in reject_keys:
                    self.sound.play_sound(self.directories.menu_button_sfx)
                    return None
                if current_event.key in (K_UP, K_w) and index > 0:
                    index -= 1
                    cursor.restart()  # WndUpdateCrsrPos
                elif current_event.key in (K_DOWN, K_s) and index < len(options.labels) - 1:
                    index += 1
                    cursor.restart()

    def draw(self, active: int, cursor_visible: bool) -> None:
        """The background, then each window with its text and cursor; only the active window's cursor blinks."""
        if self.config['NO_BLIT']:
            return
        if self.background is None:
            self.screen.fill(BLACK)
        else:
            size = (self.screen.get_width(), self.screen.get_height())
            self.screen.blit(self.graphics.get_scaled_image(self.background, size), (0, 0))
        for window_index, (options, index) in enumerate(self.windows):
            self.draw_window(options, index, show_cursor=window_index != active or cursor_visible)
        display.update(Rect(0, 0, self.screen.get_width(), self.screen.get_height()))

    def draw_window(self, options: OptionWindow, index: int, show_cursor: bool) -> None:
        x, y, width, height = options.window
        self.graphics.create_window(x, y, width, height, self.directories.ITEM_MENU_BACKGROUND_PATH, self.screen, WHITE,
                                    border=ITEM_MENU_BORDER)
        draw = self.text_drawer(options.window)
        for column, row, text in options.prompt:
            draw(text, column, row)
        for entry, label in enumerate(options.labels):
            draw(label, options.text_column, options.entry_row(entry))
        if show_cursor:
            nes_tile = self.config['TILE_SIZE'] // 2
            draw_cursor_tile(self.screen, (x * 2 + options.cursor_column) * nes_tile,
                             (y * 2 + options.entry_row(index)) * nes_tile, self.config['TILE_SIZE'] // 16, WHITE)

    def text_drawer(self, window: Window) -> Callable[[str, int, int], None]:
        """Draws text from a tile (column, row) of the window, counted from its top left corner."""
        nes_tile = self.config['TILE_SIZE'] / 2

        def draw(text: str, column: int, row: int) -> None:
            draw_text(text, (window.x * 2 + column) * nes_tile, (window.y * 2 + row + 0.5) * nes_tile, self.screen,
                      self.config, color=WHITE, letter_by_letter=False)
        return draw
