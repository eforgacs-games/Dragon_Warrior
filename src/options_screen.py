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
copied the NES: each message on a fresh window, replacing the one before. Above that, an NPCS MAKE WAY window:
ON lets a roaming NPC the hero walks into step aside (Game.ask_npc_to_make_way), OFF (the NES) leaves it in the way.
After the speed is chosen the cursor moves to the dialog style, then to NPCS MAKE WAY; B goes back a window.

The windows read the joypad like every NES selection window (src/cursor.py SelectionButtons, WndProcessInput): one
button per press, up and down in a one-column window, left and right in a one-row window, stopping at the edges.
"""
from dataclasses import dataclass
from typing import Callable, Iterable, List, Sequence, Tuple

from pygame import Rect, Surface, display

from src.color import BLACK, WHITE
from src.command_window import COMMAND_WINDOW_BUTTON_KEYS
from src.common import Graphics, set_gettext_language
from src.directories import Directories
from src.cursor import IN_DOWN, IN_LEFT, IN_RIGHT, IN_UP, draw_cursor_tile
from src.selection import run_selection
from src.sound import Sound
from src.text import draw_text
from src.windows import ADVENTURE_LOG_WINDOW_1, ADVENTURE_LOG_WINDOW_2, ERASE_LOG_WINDOW, ITEM_MENU_BORDER, \
    MESSAGE_SPEED_WINDOW, YES_NO_2_WINDOW, Window, variable_height_window

# The save file keys (CommandMenu.save, Game.load_game): one per adventure log, like the NES MessageSpeed byte
MESSAGE_SPEED_SAVE_KEY = 'MessageSpeed'
DIALOG_STYLE_SAVE_KEY = 'DialogStyle'
NPCS_MAKE_WAY_SAVE_KEY = 'NpcsMakeWay'

# MessageSpeed: #$00-fast, #$01-normal, #$02-slow; the window lists them in that order (WndRow = MessageSpeed)
MESSAGE_SPEED_NAMES = ('Fast', 'Normal', 'Slow')
# NewQuest (LF8D4): a new quest starts at normal speed; a save without the setting loads as normal too
DEFAULT_MESSAGE_SPEED = 'Normal'

CLASSIC = 'Classic'  # the NES dialog window (src/dialog_box.py), the default
MODERN = 'Modern'  # each message replaces the last one, as this game drew dialog before it matched the NES
DIALOG_STYLES = (CLASSIC, MODERN)
DEFAULT_DIALOG_STYLE = CLASSIC

# NPCS_MAKE_WAY (base_config, #297): on by default; a save without the setting loads as ON
DEFAULT_NPCS_MAKE_WAY = True
NPCS_MAKE_WAY_CHOICES = (True, False)  # the window's entries, left to right


@dataclass(frozen=True)
class Options:
    """The settings kept per adventure log."""
    message_speed: str = DEFAULT_MESSAGE_SPEED
    dialog_style: str = DEFAULT_DIALOG_STYLE
    npcs_make_way: bool = DEFAULT_NPCS_MAKE_WAY


# A new quest's settings when none are chosen: NewQuest's MSG_NORMAL, the NES dialog window, and base_config's default
DEFAULT_OPTIONS = Options()

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

# The NPCS MAKE WAY window: not on the NES either. Directly above the dialog style window (block rows 0 to 2), the
# same width; the prompt on row 1 and the two entries side by side on row 3, each with the cursor in the tile before.
NPCS_MAKE_WAY_WINDOW = Window(MESSAGE_SPEED_WINDOW.x, DIALOG_STYLE_WINDOW.y - 3, MESSAGE_SPEED_WINDOW.width, 3)
NPCS_MAKE_WAY_PROMPT = ((2, 1, 'NPCs Make Way'),)
NPCS_MAKE_WAY_LABELS = ('ON', 'OFF (NES)')
NPCS_MAKE_WAY_ROW = 3
NPCS_MAKE_WAY_TEXT_COLUMNS = (3, 8)

# LogList1Dat2 ... LogList123Dat2 (see src/adventure_log.py): " ADVENTURE LOG n:" and the first 4 letters of the
# name; the first line on tile row 2 of the window, one block apart; the cursor in column 1, the text from column 2
LOG_FIRST_ROW = 2
LOG_TEXT_COLUMN = 2
LOG_CURSOR_COLUMN = 1
LOG_NAME_LETTERS = 4

# LogList1Dat1 ... LogList123Dat1 (ShowOpenLogs): " ADVENTURE LOG n", no colon and no name, laid out like the used logs
# window above
OPEN_LOG_FIRST_ROW = 2
OPEN_LOG_TEXT_COLUMN = 2
OPEN_LOG_CURSOR_COLUMN = 1

# EraseLogDat ($B4D4), double spaced, each line after 1 blank tile ($81): the saved hero's full name ($B4), " LEVEL",
# 2 blank tiles ($82) and the saved level in 2 digits ($A1), then " Do You Want To", " Erase This", " Character?"
ERASE_LOG_TEXT_COLUMN = 2
ERASE_LOG_NAME_ROW = 2
ERASE_LOG_LEVEL_ROW = 4
ERASE_LOG_LEVEL_COLUMN = 9  # after "LEVEL" (columns 2-6) and the 2 blank tiles
ERASE_LOG_QUESTION_ROW = 6

# YesNo2Dat ($B50D): a selection window, cursor home Y = 2, X = 1; 1 blank tile ($81) then YES, and NO a row below
YES_NO_FIRST_ROW = 2
YES_NO_TEXT_COLUMN = 2
YES_NO_CURSOR_COLUMN = 1
YES = 0  # WND_YES: the first entry

ENTRY_SPACING = 2  # every window here is single spaced with a blank row between entries: 2 tile rows per entry


def message_speed_from_save(save: dict) -> str:
    """The log's message speed (LoadSavedData, LFBC8); a save from before it was kept loads as NORMAL."""
    speed = save.get(MESSAGE_SPEED_SAVE_KEY)
    return speed if speed in MESSAGE_SPEED_NAMES else DEFAULT_MESSAGE_SPEED


def dialog_style_from_save(save: dict) -> str:
    """The log's dialog style; a save from before it was kept loads as CLASSIC (the NES)."""
    style = save.get(DIALOG_STYLE_SAVE_KEY)
    return style if style in DIALOG_STYLES else DEFAULT_DIALOG_STYLE


def npcs_make_way_from_save(save: dict) -> bool:
    """The log's NPCS MAKE WAY; a save from before it was kept loads as ON (the default)."""
    make_way = save.get(NPCS_MAKE_WAY_SAVE_KEY)
    return make_way if isinstance(make_way, bool) else DEFAULT_NPCS_MAKE_WAY


def options_from_save(save: dict) -> Options:
    return Options(message_speed_from_save(save), dialog_style_from_save(save), npcs_make_way_from_save(save))


def options_to_save(options: Options) -> dict:
    """The save file entries for these settings (CommandMenu.save, TitleMenu.change_message_speed)."""
    return {MESSAGE_SPEED_SAVE_KEY: options.message_speed, DIALOG_STYLE_SAVE_KEY: options.dialog_style,
            NPCS_MAKE_WAY_SAVE_KEY: options.npcs_make_way}


def options_from_config(config: dict) -> Options:
    """The settings the running game uses."""
    return Options(config.get('TEXT_SPEED', DEFAULT_MESSAGE_SPEED), config.get('DIALOG_STYLE', DEFAULT_DIALOG_STYLE),
                   bool(config.get('NPCS_MAKE_WAY', DEFAULT_NPCS_MAKE_WAY)))


def apply_options(config: dict, options: Options) -> None:
    """Use these settings from now on: the dialog code reads TEXT_SPEED and DIALOG_STYLE for every message, and
    Game.ask_npc_to_make_way reads NPCS_MAKE_WAY for every bump."""
    config['TEXT_SPEED'] = options.message_speed
    config['DIALOG_STYLE'] = options.dialog_style
    config['NPCS_MAKE_WAY'] = options.npcs_make_way


class OptionWindow:
    """One selection window: its place, fixed text, entries and where its cursor goes."""

    def __init__(self, window: Window, prompt: Iterable[Tuple[int, int, str]], labels: Sequence[str], first_row: int,
                 text_column: int, cursor_column: int, text_columns: Sequence[int] = ()):
        """``text_columns``, if given, puts the entries side by side on first_row, starting at these columns (a one-row
        window, moved through with left and right); otherwise they go down from first_row at text_column."""
        self.window = window
        self.prompt = tuple(prompt)
        self.labels = tuple(labels)
        self.first_row = first_row
        self.text_column = text_column
        self.cursor_column = cursor_column
        self.text_columns = tuple(text_columns)

    @property
    def horizontal(self) -> bool:
        return bool(self.text_columns)

    def entry_row(self, index: int) -> int:
        return self.first_row if self.horizontal else self.first_row + ENTRY_SPACING * index

    def entry_text_column(self, index: int) -> int:
        return self.text_columns[index] if self.horizontal else self.text_column

    def entry_cursor_column(self, index: int) -> int:
        return self.text_columns[index] - 1 if self.horizontal else self.cursor_column

    def move(self, index: int, button: int) -> int:
        """WndUpPressed, WndDownPressed, WndDoLeftPressed, WndRightPressed: the entry the cursor moves to, which
        stops at the window's edges (and doesn't move across a one-column window, or up and down a one-row one)."""
        back, forward = (IN_LEFT, IN_RIGHT) if self.horizontal else (IN_UP, IN_DOWN)
        if button == back:
            return max(0, index - 1)
        if button == forward:
            return min(len(self.labels) - 1, index + 1)
        return index


MESSAGE_SPEED_OPTIONS = OptionWindow(MESSAGE_SPEED_WINDOW, MESSAGE_SPEED_PROMPT, MESSAGE_SPEED_LABELS,
                                     MESSAGE_SPEED_FIRST_ROW, MESSAGE_SPEED_TEXT_COLUMN, MESSAGE_SPEED_CURSOR_COLUMN)
DIALOG_STYLE_OPTIONS = OptionWindow(DIALOG_STYLE_WINDOW, DIALOG_STYLE_PROMPT, DIALOG_STYLE_LABELS,
                                    DIALOG_STYLE_FIRST_ROW, DIALOG_STYLE_TEXT_COLUMN, DIALOG_STYLE_CURSOR_COLUMN)
NPCS_MAKE_WAY_OPTIONS = OptionWindow(NPCS_MAKE_WAY_WINDOW, NPCS_MAKE_WAY_PROMPT, NPCS_MAKE_WAY_LABELS,
                                     NPCS_MAKE_WAY_ROW, NPCS_MAKE_WAY_TEXT_COLUMNS[0], NPCS_MAKE_WAY_TEXT_COLUMNS[0] - 1,
                                     text_columns=NPCS_MAKE_WAY_TEXT_COLUMNS)


def adventure_log_options(logs: Sequence[Tuple[int, str]], _: Callable[[str], str] = str) -> OptionWindow:
    """The used logs window (LogList*Dat2): one line per log, " ADVENTURE LOG n:" and 4 letters of the hero's name.
    ``_`` translates the line (set_gettext_language); the hero's name is never translated."""
    window = variable_height_window(ADVENTURE_LOG_WINDOW_2, len(logs))
    labels = [_("ADVENTURE LOG {}:").format(slot) + name[:LOG_NAME_LETTERS] for slot, name in logs]
    return OptionWindow(window, (), labels, LOG_FIRST_ROW, LOG_TEXT_COLUMN, LOG_CURSOR_COLUMN)


def open_log_options(logs: Sequence[int]) -> OptionWindow:
    """The open logs window (ShowOpenLogs, LogList*Dat1): one line per open log, " ADVENTURE LOG n"."""
    window = variable_height_window(ADVENTURE_LOG_WINDOW_1, len(logs))
    labels = [f'ADVENTURE LOG {slot}' for slot in logs]
    return OptionWindow(window, (), labels, OPEN_LOG_FIRST_ROW, OPEN_LOG_TEXT_COLUMN, OPEN_LOG_CURSOR_COLUMN)


def erase_log_window(name: str, level: int, _: Callable[[str], str]) -> OptionWindow:
    """EraseLogDat: the log's hero and level, and the question. Nothing to choose in it; YesNo2Dat opens over it."""
    question = _("Do You Want To\nErase This\nCharacter?").split('\n')
    prompt = [(ERASE_LOG_TEXT_COLUMN, ERASE_LOG_NAME_ROW, name),
              (ERASE_LOG_TEXT_COLUMN, ERASE_LOG_LEVEL_ROW, _("LEVEL")),
              (ERASE_LOG_LEVEL_COLUMN, ERASE_LOG_LEVEL_ROW, f'{level:>2}')]
    prompt += [(ERASE_LOG_TEXT_COLUMN, ERASE_LOG_QUESTION_ROW + ENTRY_SPACING * line, text)
               for line, text in enumerate(question)]
    return OptionWindow(ERASE_LOG_WINDOW, prompt, (), 0, 0, 0)


def yes_no_options(_: Callable[[str], str]) -> OptionWindow:
    """YesNo2Dat: YES and NO."""
    return OptionWindow(YES_NO_2_WINDOW, (), (_("YES"), _("NO")), YES_NO_FIRST_ROW, YES_NO_TEXT_COLUMN,
                        YES_NO_CURSOR_COLUMN)


class OptionsScreen:
    """Draws the title menu's windows over a background (the title menu window, or black) and runs their cursors.

    Each window keeps its cursor: the one being chosen from blinks like every NES window cursor (src/cursor.py), the
    others hold theirs on their choice, as the NES leaves a chosen entry's arrow on behind the windows it opens."""

    def __init__(self, screen: Surface, config: dict, background: Callable[[Surface], None] | None = None):
        """``background`` draws what the windows open over (the title menu, TitleMenu.title_menu_background); without
        it they open on black."""
        self.screen = screen
        self.config = config
        self.background = background
        self.graphics = Graphics(config)
        self.directories = Directories(config)
        self.sound = Sound(config)
        # The prompts and entries are translated (the NES font has no Korean: draw_text draws it in Unifont)
        self._ = set_gettext_language(config.get('LANGUAGE'))
        # windows on screen, bottom to top, each with the entry its cursor is on
        self.windows: List[Tuple[OptionWindow, int]] = []

    def choose_log(self, logs: Sequence[Tuple[int, str]]) -> int | None:
        """DoChngMsgSpeed -> ShowUsedLogs: the chosen log's number, or None for B."""
        log_window = adventure_log_options(logs, self._)
        self.windows = [(log_window, 0)]
        index = self.select(0)
        return None if index is None else logs[index][0]

    def choose_open_log(self, logs: Sequence[int]) -> int | None:
        """ShowOpenLogs, opened over the windows already on screen (DoCopyGame's used logs window): the chosen open
        log's number, or None for B."""
        self.windows = self.windows + [(open_log_options(logs), 0)]
        index = self.select(len(self.windows) - 1)
        return None if index is None else logs[index]

    def confirm(self) -> bool:
        """YesNo2Dat over the windows on screen: True for YES, False for NO or B (anything but WND_YES)."""
        self.windows = self.windows + [(yes_no_options(self._), YES)]
        return self.select(len(self.windows) - 1) == YES

    def confirm_erase(self, name: str, level: int) -> bool:
        """DoEraseGame's VerifyErase: EraseLogDat with the log's hero and level, then YesNo2Dat over it."""
        self.windows = self.windows + [(erase_log_window(name, level, self._), 0)]
        return self.confirm()

    def choose_options(self, current: Options) -> Options | None:
        """WND_MSG_SPEED, then the dialog style, then NPCS MAKE WAY: the chosen settings, or None if B was pressed in
        the speed window (WndBackToMain). B in a later window goes back to the one before. The cursors start on the
        current settings (LA93E: WndRow = MessageSpeed)."""
        choices = [MESSAGE_SPEED_NAMES.index(current.message_speed), DIALOG_STYLES.index(current.dialog_style),
                   NPCS_MAKE_WAY_CHOICES.index(current.npcs_make_way)]
        # chosen in this order; drawn bottom to top in the reverse order, so the speed window is on top
        steps = (MESSAGE_SPEED_OPTIONS, DIALOG_STYLE_OPTIONS, NPCS_MAKE_WAY_OPTIONS)
        base = list(self.windows)
        step = 0
        while step < len(steps):
            self.windows = base + [(steps[i], choices[i]) for i in reversed(range(len(steps)))]
            chosen = self.select(len(self.windows) - 1 - step)
            if chosen is None:
                if step == 0:
                    self.windows = base
                    return None
                step -= 1
                continue
            choices[step] = chosen
            step += 1
        return Options(MESSAGE_SPEED_NAMES[choices[0]], DIALOG_STYLES[choices[1]], NPCS_MAKE_WAY_CHOICES[choices[2]])

    def select(self, active: int) -> int | None:
        """WndDoSelect for self.windows[active]: once a frame, read the joypad (SelectionButtons) and handle the
        first button pressed (WndProcessInput) until A (the entry's index) or B (None). A and B draw the arrow once
        more, held on, and make the menu sound (src/selection.py)."""
        options, index = self.windows[active]

        def draw(entry: int, cursor_visible: bool) -> None:
            self.windows[active] = (options, entry)
            self.draw(active, cursor_visible)

        answer = run_selection(draw, index, move=options.move, keys=COMMAND_WINDOW_BUTTON_KEYS, joypad=True,
                               sound=lambda: self.sound.play_sound(self.directories.menu_button_sfx))
        return answer.entry if answer.accepted else None

    def draw(self, active: int, cursor_visible: bool) -> None:
        """The background, then each window with its text and cursor; only the active window's cursor blinks."""
        if self.config['NO_BLIT']:
            return
        self.screen.fill(BLACK)
        if self.background is not None:
            self.background(self.screen)
        for window_index, (options, index) in enumerate(self.windows):
            self.draw_window(options, index, show_cursor=window_index != active or cursor_visible)
        display.update(Rect(0, 0, self.screen.get_width(), self.screen.get_height()))

    def draw_window(self, options: OptionWindow, index: int, show_cursor: bool) -> None:
        x, y, width, height = options.window
        self.graphics.create_window(x, y, width, height, self.directories.ITEM_MENU_BACKGROUND_PATH, self.screen, WHITE,
                                    border=ITEM_MENU_BORDER)
        draw = self.text_drawer(options.window)
        for column, row, text in options.prompt:
            draw(self._(text), column, row)
        for entry, label in enumerate(options.labels):
            draw(self._(label), options.entry_text_column(entry), options.entry_row(entry))
        if show_cursor and options.labels:
            nes_tile = self.config['TILE_SIZE'] // 2
            draw_cursor_tile(self.screen, (x * 2 + options.entry_cursor_column(index)) * nes_tile,
                             (y * 2 + options.entry_row(index)) * nes_tile, self.config['TILE_SIZE'] // 16, WHITE)

    def text_drawer(self, window: Window) -> Callable[[str, int, int], None]:
        """Draws text from a tile (column, row) of the window, counted from its top left corner."""
        nes_tile = self.config['TILE_SIZE'] / 2

        def draw(text: str, column: int, row: int) -> None:
            draw_text(text, (window.x * 2 + column) * nes_tile, (window.y * 2 + row + 0.5) * nes_tile, self.screen,
                      self.config, color=WHITE, letter_by_letter=False)
        return draw
