"""The title menu's CHANGE MESSAGE SPEED: pick an adventure log, then its message speed (the NES window); and the
settings kept per adventure log.

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

What this game adds (none of it on the NES, so none of it asked here): the dialog style, NPCS MAKE WAY, the fade style
and the stairs. They are changed during play, in the options overlay (src/options_overlay.py: SELECT or Tab on the
map), and kept per adventure log beside the message speed (Options below). A new quest starts with their defaults.

The windows read the joypad like every NES selection window (src/cursor.py SelectionButtons, WndProcessInput): one
button per press, up and down in a one-column window, left and right in a one-row window, stopping at the edges.
"""
from dataclasses import dataclass
from collections.abc import Callable, Iterable, Sequence

from pygame import Rect, Surface, display

from src.color import BLACK, WHITE
from src.command_window import COMMAND_WINDOW_BUTTON_KEYS
from src.common import Graphics, set_gettext_language
from src.directories import Directories
from src.cursor import IN_DOWN, IN_LEFT, IN_RIGHT, IN_UP, draw_cursor_tile
from src.selection import run_selection
from src.sound import Sound
from src.text import draw_text
from src.visual_effects import FADE_STYLE_NES, FADE_STYLES, fade_style
from src.waiting import MENU_SPEED_NORMAL, MENU_SPEEDS
from src.windows import ADVENTURE_LOG_WINDOW_1, ADVENTURE_LOG_WINDOW_2, ERASE_LOG_WINDOW, ITEM_MENU_BORDER, \
    MESSAGE_SPEED_WINDOW, YES_NO_2_WINDOW, Window, variable_height_window

# The save file keys (CommandMenu.save, Game.load_game): one per adventure log, like the NES MessageSpeed byte
MESSAGE_SPEED_SAVE_KEY = 'MessageSpeed'
DIALOG_STYLE_SAVE_KEY = 'DialogStyle'
NPCS_MAKE_WAY_SAVE_KEY = 'NpcsMakeWay'
FADE_STYLE_SAVE_KEY = 'FadeStyle'
AUTO_STAIRS_SAVE_KEY = 'AutoStairs'
AUTO_GRIND_STOP_SAVE_KEY = 'AutoGrindStop'
MENU_SPEED_SAVE_KEY = 'MenuSpeed'

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

# FADE_STYLE (base_config, #319): the NES palette fade by default; a save without the setting loads as NES
DEFAULT_FADE_STYLE = FADE_STYLE_NES

# AUTO_STAIRS (base_config): STEP ON by default, stairs are taken by stepping onto them; off is the NES, where only the
# STAIRS command takes them (Bank03 CheckStairs). A save without the setting loads as STEP ON.
DEFAULT_AUTO_STAIRS = True

# AUTO_GRIND_STOP (base_config): when auto-grind stops (src/auto_grind.py); a save without the setting loads as RED HP
AUTO_GRIND_STOP_VALUES = ('RedHP', 'HalfHP', 'ThreeQuartersHP')
DEFAULT_AUTO_GRIND_STOP = 'RedHP'

# MENU_SPEED (base_config, #440): NORMAL by default, the selection windows at 1x whatever the game speed
# (src/waiting.py menu_ticks); a save without the setting loads as NORMAL
DEFAULT_MENU_SPEED = MENU_SPEED_NORMAL


@dataclass(frozen=True, slots=True)
class Options:
    """The settings kept per adventure log."""
    message_speed: str = DEFAULT_MESSAGE_SPEED
    dialog_style: str = DEFAULT_DIALOG_STYLE
    npcs_make_way: bool = DEFAULT_NPCS_MAKE_WAY
    fade_style: str = DEFAULT_FADE_STYLE
    auto_stairs: bool = DEFAULT_AUTO_STAIRS
    auto_grind_stop: str = DEFAULT_AUTO_GRIND_STOP
    menu_speed: str = DEFAULT_MENU_SPEED


# A new quest's settings when none are chosen: NewQuest's MSG_NORMAL, the NES dialog window, and base_config's
# defaults
DEFAULT_OPTIONS = Options()

# MsgSpeedDat ($B194): single spaced, 18 tiles wide. " Which Message", " Speed Do You" and " Want To Use?" on tile rows
# 1, 3 and 5 (a blank tile, then the text from column 2); FAST, NORMAL and SLOW on rows 8, 10 and 12 after 6 blank
# tiles (column 7); cursor home Y = 8, X = 6 ($86), and the cursor moves 2 rows per entry.
MESSAGE_SPEED_PROMPT = ((2, 1, 'Which Message'), (2, 3, 'Speed Do You'), (2, 5, 'Want To Use?'))
MESSAGE_SPEED_LABELS = ('FAST', 'NORMAL', 'SLOW')
MESSAGE_SPEED_FIRST_ROW = 8
MESSAGE_SPEED_TEXT_COLUMN = 7
MESSAGE_SPEED_CURSOR_COLUMN = 6

# LogList1Dat2 ... LogList123Dat2 (see used_logs_layout in src/windows.py): " ADVENTURE LOG n:" and the first 4 letters of the
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


def fade_style_from_save(save: dict) -> str:
    """The log's fade style; a save from before it was kept loads as NES (the default)."""
    style = save.get(FADE_STYLE_SAVE_KEY)
    return style if style in FADE_STYLES else DEFAULT_FADE_STYLE


def auto_stairs_from_save(save: dict) -> bool:
    """The log's STAIRS setting; a save from before it was kept loads as STEP ON (the default)."""
    auto_stairs = save.get(AUTO_STAIRS_SAVE_KEY)
    return auto_stairs if isinstance(auto_stairs, bool) else DEFAULT_AUTO_STAIRS


def auto_grind_stop_from_save(save: dict) -> str:
    """The log's GRIND STOP setting; a save from before it was kept loads as RED HP (the default)."""
    setting = save.get(AUTO_GRIND_STOP_SAVE_KEY)
    return setting if setting in AUTO_GRIND_STOP_VALUES else DEFAULT_AUTO_GRIND_STOP


def menu_speed_from_save(save: dict) -> str:
    """The log's MENU SPEED setting; a save from before it was kept loads as NORMAL (the default)."""
    setting = save.get(MENU_SPEED_SAVE_KEY)
    return setting if setting in MENU_SPEEDS else DEFAULT_MENU_SPEED


def options_from_save(save: dict) -> Options:
    return Options(message_speed_from_save(save), dialog_style_from_save(save), npcs_make_way_from_save(save),
                   fade_style_from_save(save), auto_stairs_from_save(save), auto_grind_stop_from_save(save),
                   menu_speed_from_save(save))


def options_to_save(options: Options) -> dict:
    """The save file entries for these settings (CommandMenu.save, TitleMenu.change_message_speed)."""
    return {MESSAGE_SPEED_SAVE_KEY: options.message_speed, DIALOG_STYLE_SAVE_KEY: options.dialog_style,
            NPCS_MAKE_WAY_SAVE_KEY: options.npcs_make_way, FADE_STYLE_SAVE_KEY: options.fade_style,
            AUTO_STAIRS_SAVE_KEY: options.auto_stairs, AUTO_GRIND_STOP_SAVE_KEY: options.auto_grind_stop,
            MENU_SPEED_SAVE_KEY: options.menu_speed}


def options_from_config(config: dict) -> Options:
    """The settings the running game uses."""
    return Options(config.get('TEXT_SPEED', DEFAULT_MESSAGE_SPEED), config.get('DIALOG_STYLE', DEFAULT_DIALOG_STYLE),
                   bool(config.get('NPCS_MAKE_WAY', DEFAULT_NPCS_MAKE_WAY)),
                   fade_style(config), bool(config.get('AUTO_STAIRS', DEFAULT_AUTO_STAIRS)),
                   auto_grind_stop_from_save({AUTO_GRIND_STOP_SAVE_KEY: config.get('AUTO_GRIND_STOP')}),
                   menu_speed_from_save({MENU_SPEED_SAVE_KEY: config.get('MENU_SPEED')}))


def apply_options(config: dict, options: Options) -> None:
    """Use these settings from now on: the dialog code reads TEXT_SPEED and DIALOG_STYLE for every message, and
    MovementController.ask_npc_to_make_way reads NPCS_MAKE_WAY for every bump, screen_fade reads FADE_STYLE for every
    fade, MapManager.handle_warps reads AUTO_STAIRS for every step, auto-grind reads AUTO_GRIND_STOP for every check
    and the menu clock reads MENU_SPEED (src/waiting.py menu_speed)."""
    config['TEXT_SPEED'] = options.message_speed
    config['DIALOG_STYLE'] = options.dialog_style
    config['NPCS_MAKE_WAY'] = options.npcs_make_way
    config['FADE_STYLE'] = options.fade_style
    config['AUTO_STAIRS'] = options.auto_stairs
    config['AUTO_GRIND_STOP'] = options.auto_grind_stop
    config['MENU_SPEED'] = options.menu_speed


class OptionWindow:
    """One selection window: its place, fixed text, entries and where its cursor goes."""

    def __init__(self, window: Window, prompt: Iterable[tuple[int, int, str]], labels: Sequence[str], first_row: int,
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

def adventure_log_options(logs: Sequence[tuple[int, str]], _: Callable[[str], str] = str) -> OptionWindow:
    """The used logs window (LogList*Dat2): one line per log, " ADVENTURE LOG n:" and 4 letters of the hero's name.
    ``_`` translates the line (set_gettext_language); the hero's name is never translated."""
    window = variable_height_window(ADVENTURE_LOG_WINDOW_2, len(logs))
    labels = [_("ADVENTURE LOG {}:").format(slot) + name[:LOG_NAME_LETTERS] for slot, name in logs]
    return OptionWindow(window, (), labels, LOG_FIRST_ROW, LOG_TEXT_COLUMN, LOG_CURSOR_COLUMN)


def open_log_options(logs: Sequence[int], _: Callable[[str], str] = str) -> OptionWindow:
    """The open logs window (ShowOpenLogs, LogList*Dat1): one line per open log, " ADVENTURE LOG n". ``_`` translates
    the line."""
    window = variable_height_window(ADVENTURE_LOG_WINDOW_1, len(logs))
    labels = [_("ADVENTURE LOG {}").format(slot) for slot in logs]
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
        self.windows: list[tuple[OptionWindow, int]] = []

    def choose_log(self, logs: Sequence[tuple[int, str]]) -> int | None:
        """DoChngMsgSpeed -> ShowUsedLogs: the chosen log's number, or None for B."""
        log_window = adventure_log_options(logs, self._)
        self.windows = [(log_window, 0)]
        index = self.select(0)
        return None if index is None else logs[index][0]

    def choose_open_log(self, logs: Sequence[int]) -> int | None:
        """ShowOpenLogs, opened over the windows already on screen (DoCopyGame's used logs window): the chosen open
        log's number, or None for B."""
        self.windows = self.windows + [(open_log_options(logs, self._), 0)]
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

    def choose_message_speed(self, current: str) -> str | None:
        """WND_MSG_SPEED over the windows on screen: the chosen speed, or None for B (WndBackToMain). The cursor starts
        on the current speed (LA93E: WndRow = MessageSpeed)."""
        base = list(self.windows)
        self.windows = base + [(MESSAGE_SPEED_OPTIONS, MESSAGE_SPEED_NAMES.index(current))]
        chosen = self.select(len(self.windows) - 1)
        if chosen is None:
            self.windows = base
            return None
        return MESSAGE_SPEED_NAMES[chosen]

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
