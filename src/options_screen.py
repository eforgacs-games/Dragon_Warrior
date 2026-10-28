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
  NORMAL on the NES (LF8D4: LDA #MSG_NORMAL); here it starts on FAST, the game's default speed (DEFAULT_MESSAGE_SPEED),
  and InitNewGame saves the choice with the new log.

What this game adds (none of it on the NES, so none of it asked here): the dialog style, NPCS MAKE WAY, the fade style,
the stairs, the grind stop, the soundtrack and the switches for this game's other conveniences (SWITCHES: the game speed
keys, save states, rewind, auto-grind, the cheat keys, the shop preview, the quest journal and the bag size) and
AUTOSAVE. They are changed during play, in the options overlay (src/options_overlay.py: SELECT or Tab on the map), and
kept per adventure log beside the message speed (Options below). A new quest starts with their defaults, which are the
NES preset's values, so a new quest plays as the NES does until the player switches something on.

The windows read the joypad like every NES selection window (src/cursor.py SelectionButtons, WndProcessInput): one
button per press, up and down in a one-column window, left and right in a one-row window, stopping at the edges.
"""
from dataclasses import dataclass
from collections.abc import Callable, Iterable, Sequence
from typing import Any

from pygame import Rect, Surface, display

from src.color import BLACK, WHITE
from src.command_window import COMMAND_WINDOW_BUTTON_KEYS
from src.common import Graphics, set_gettext_language
from src.directories import Directories
from src.quest_journal import JOURNAL_LEARNED, JOURNAL_OFF, JOURNAL_SETTINGS, LEGACY_JOURNAL_GOALS
from src.items import BAG_SIZES, INVENTORY_SLOTS
from src.cursor import IN_DOWN, IN_LEFT, IN_RIGHT, IN_UP, draw_cursor_tile
from src.selection import run_selection
from src.sound import Sound
from src.soundtrack import DEFAULT_SOUNDTRACK, SOUNDTRACK_KEY, SOUNDTRACK_SAVE_KEY, Soundtrack, \
    soundtrack, soundtrack_from_save
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
AUTOSAVE_SAVE_KEY = 'Autosave'
BAG_SIZE_SAVE_KEY = 'BagSize'

# BAG_SIZE (base_config, src/items.py bag_slots): the NES's 8 slots by default; a save without the setting loads as 8
DEFAULT_BAG_SIZE = INVENTORY_SLOTS

# MessageSpeed: #$00-fast, #$01-normal, #$02-slow; the window lists them in that order (WndRow = MessageSpeed)
MESSAGE_SPEED_NAMES = ('Fast', 'Normal', 'Slow')
# The default speed: a new quest's window starts on it, and a save without the setting loads with it. The NES starts a
# new quest on NORMAL (NewQuest, LF8D4: LDA #MSG_NORMAL); this game defaults to FAST, and NORMAL is a choice away.
DEFAULT_MESSAGE_SPEED = 'Fast'

CLASSIC = 'Classic'  # the NES dialog window (src/dialog_box.py), the default
MODERN = 'Modern'  # each message replaces the last one, as this game drew dialog before it matched the NES
DIALOG_STYLES = (CLASSIC, MODERN)
DEFAULT_DIALOG_STYLE = CLASSIC

# NPCS_MAKE_WAY (base_config, #297): off by default, the NES; a save without the setting loads as OFF
DEFAULT_NPCS_MAKE_WAY = False

# FADE_STYLE (base_config, #319): the NES palette fade by default; a save without the setting loads as NES
DEFAULT_FADE_STYLE = FADE_STYLE_NES

# AUTO_STAIRS (base_config): off by default, the NES, where only the STAIRS command takes stairs (Bank03 CheckStairs);
# STEP ON takes them by stepping onto them. A save without the setting loads as off (NES).
DEFAULT_AUTO_STAIRS = False

# AUTO_GRIND_STOP (base_config): when auto-grind stops (src/auto_grind.py); a save without the setting loads as RED HP
AUTO_GRIND_STOP_VALUES = ('RedHP', 'HalfHP', 'ThreeQuartersHP')
DEFAULT_AUTO_GRIND_STOP = 'RedHP'

# MENU_SPEED (base_config, #440): NORMAL by default, the selection windows at 1x whatever the game speed
# (src/waiting.py menu_ticks); a save without the setting loads as NORMAL
DEFAULT_MENU_SPEED = MENU_SPEED_NORMAL
# SMART_A (base_config): off by default, the NES, where A on the map always opens COMMAND; on, A does TALK, TAKE, DOOR
# or STAIRS when one applies (Game.smart_command). A save without the setting loads as OFF.
DEFAULT_SMART_A = False

# MESSAGE_LOG (base_config): off by default, the NES, which has none; on, the MESSAGE LOG key opens the log of the last
# messages (src/message_log.py). A save without the setting loads as OFF.
DEFAULT_MESSAGE_LOG = False


# ENCOUNTERS, EXP/GOLD and STATUS WINDOW's values
ENCOUNTERS_NES, ENCOUNTERS_HALF, ENCOUNTERS_OFF = ENCOUNTER_SETTINGS = ('NES', 'Half', 'Off')
EXP_GOLD_MULTIPLIERS = (1, 2, 4)
STATUS_WINDOW_NES, STATUS_WINDOW_ALWAYS = STATUS_WINDOW_SETTINGS = ('NES', 'Always')


@dataclass(frozen=True, slots=True)
class Switch:
    """One of this game's conveniences, switched in the options overlay (#409, #437): the Options field, the config
    key the game reads, the save file key, its values and its default (also what a save without it loads as). Every
    default is the NES's value, as the NES preset (src/options_overlay.py) sets it, so a new quest plays as the NES
    does. ``renamed`` maps a value an older build saved to the value it is now."""
    field_name: str
    config_key: str
    save_key: str
    values: tuple[Any, ...]
    default: Any
    renamed: tuple[tuple[Any, Any], ...] = ()

    def valid(self, value: Any) -> Any:
        """value if it's one of the values (a bool for an on/off switch, not 0 or 1), what it was renamed to if an
        older build saved it under another name, the default otherwise."""
        value = next((new for old, new in self.renamed if same_value(value, old)), value)
        if any(same_value(value, choice) for choice in self.values):
            return value
        return self.default


def same_value(value: Any, choice: Any) -> bool:
    """Equal and of the same type: True is not 1."""
    return value == choice and type(value) is type(choice)


SWITCHES = (
    # GAME SPEED: keys 1 to 5 set the game speed (src/waiting.py); off, the default, they do nothing (the NES has one
    # speed)
    Switch('game_speed_keys', 'GAME_SPEED_KEYS', 'GameSpeedKeys', (False, True), False),
    # SAVE STATES: F1-F3 load and Shift+F1-F3 save a state; off, the keys do nothing
    Switch('save_states', 'SAVE_STATES', 'SaveStates', (False, True), False),
    # REWIND: Backspace rewinds; off, it does nothing
    Switch('rewind', 'REWIND', 'Rewind', (False, True), False),
    # AUTO-GRIND: G starts auto-grind (src/auto_grind.py); off, G does nothing
    Switch('auto_grind', 'AUTO_GRIND', 'AutoGrind', (False, True), False),
    # CHEATS: F4 auto-battle and F9 invulnerability; off, the keys do nothing and both are off
    Switch('cheat_keys', 'CHEAT_KEYS', 'CheatKeys', (False, True), False),
    # QUICK ACTION: Enter on the map takes a chest, opens a door or talks without the COMMAND window; off, Enter is
    # the A button there too, as everywhere else
    Switch('quick_action', 'QUICK_ACTION', 'QuickAction', (False, True), False),
    # ENCOUNTERS: the NES's random fights, half as many (every other one that would start is skipped, so the NES's
    # rolls and enemy choice are untouched) or none (Game.roll_for_fight); scripted fights always happen
    Switch('encounters', 'ENCOUNTERS', 'Encounters', ENCOUNTER_SETTINGS, ENCOUNTERS_NES),
    # EXP/GOLD: the experience and gold a won fight gives, times 1 (the NES), 2 or 4 (Battle.enemy_defeated)
    Switch('exp_gold', 'EXP_GOLD', 'ExpGold', EXP_GOLD_MULTIPLIERS, 1),
    # RUN BUTTON: B held while walking on the map walks twice as fast (MovementController.run_button_held)
    Switch('run_button', 'RUN_BUTTON', 'RunButton', (False, True), False),
    # STATUS WINDOW: the NES pop-up after standing still, or always on the map (Drawer.status_window_always)
    Switch('status_window', 'STATUS_WINDOW', 'StatusWindow', STATUS_WINDOW_SETTINGS, STATUS_WINDOW_NES),
    # SHOP PREVIEW (#401): a weapon and armor shop's list shows the attack or defense power the highlighted item would
    # give (src/shop_preview.py); off, the default, is the NES
    Switch('shop_preview', 'SHOP_PREVIEW', 'ShopPreview', (False, True), False),
    # QUEST JOURNAL (#410): what Q shows on the map (src/quest_journal.py): nothing (the NES, the default), the goals
    # the hero has learned of, or those with what was said about them. Older builds' GOALS showed every open goal; it
    # loads as LEARNED.
    Switch('quest_journal', 'QUEST_JOURNAL', 'QuestJournal', JOURNAL_SETTINGS, JOURNAL_OFF,
           renamed=((LEGACY_JOURNAL_GOALS, JOURNAL_LEARNED),)),
    # BAG (#413): the inventory's slots for everything but Herbs and Magic Keys (src/items.py bag_slots): the NES's 8,
    # the default, or 16
    Switch('bag_size', 'BAG_SIZE', BAG_SIZE_SAVE_KEY, BAG_SIZES, DEFAULT_BAG_SIZE),
    # SMART A (#404): A on the map does TALK, TAKE, DOOR or STAIRS when one applies, instead of opening COMMAND
    # (Game.smart_command); off, the NES and the default, A always opens COMMAND
    Switch('smart_a', 'SMART_A', 'SmartA', (False, True), DEFAULT_SMART_A),
    # MESSAGE LOG (#405): the MESSAGE LOG key (L) shows the last messages on the map (src/message_log.py); off, the
    # default, is the NES
    Switch('message_log', 'MESSAGE_LOG', 'MessageLog', (False, True), DEFAULT_MESSAGE_LOG),
)

# AUTOSAVE (base_config, src/autosave.py): OFF by default, which is the NES (it only saves with King Lorik); the MODERN
# preset turns it on. A new quest, or a save without the setting, keeps the config's (OFF in every config, so the tests
# and dev runs never write an autosave)
DEFAULT_AUTOSAVE = False


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
    # MUSIC (src/soundtrack.py): a save from before there were three soundtracks loads its OrchestraMusic switch
    soundtrack: Soundtrack = DEFAULT_SOUNDTRACK
    # SWITCHES, each defaulting to its Switch.default
    game_speed_keys: bool = False
    save_states: bool = False
    rewind: bool = False
    auto_grind: bool = False
    cheat_keys: bool = False
    quick_action: bool = False
    encounters: str = ENCOUNTERS_NES
    exp_gold: int = 1
    run_button: bool = False
    status_window: str = STATUS_WINDOW_NES
    shop_preview: bool = False
    quest_journal: str = JOURNAL_OFF
    bag_size: int = DEFAULT_BAG_SIZE
    smart_a: bool = DEFAULT_SMART_A
    message_log: bool = DEFAULT_MESSAGE_LOG
    autosave: bool | None = None  # None: the config's AUTOSAVE is kept


# A new quest's settings when none are chosen: the default message speed and the NES preset's values, as base_config
# has them
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
    """The log's message speed (LoadSavedData, LFBC8); a save from before it was kept loads at the default speed
    (DEFAULT_MESSAGE_SPEED: FAST)."""
    speed = save.get(MESSAGE_SPEED_SAVE_KEY)
    return speed if speed in MESSAGE_SPEED_NAMES else DEFAULT_MESSAGE_SPEED


def dialog_style_from_save(save: dict) -> str:
    """The log's dialog style; a save from before it was kept loads as CLASSIC (the NES)."""
    style = save.get(DIALOG_STYLE_SAVE_KEY)
    return style if style in DIALOG_STYLES else DEFAULT_DIALOG_STYLE


def npcs_make_way_from_save(save: dict) -> bool:
    """The log's NPCS MAKE WAY; a save from before it was kept loads as OFF (the default)."""
    make_way = save.get(NPCS_MAKE_WAY_SAVE_KEY)
    return make_way if isinstance(make_way, bool) else DEFAULT_NPCS_MAKE_WAY


def fade_style_from_save(save: dict) -> str:
    """The log's fade style; a save from before it was kept loads as NES (the default)."""
    style = save.get(FADE_STYLE_SAVE_KEY)
    return style if style in FADE_STYLES else DEFAULT_FADE_STYLE


def auto_stairs_from_save(save: dict) -> bool:
    """The log's STAIRS setting; a save from before it was kept loads as NES (the default)."""
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


def autosave_from_save(save: dict) -> bool | None:
    """The log's AUTOSAVE setting (src/autosave.py); None for a save from before it was kept, which leaves the
    config's as it is."""
    autosave = save.get(AUTOSAVE_SAVE_KEY)
    return autosave if isinstance(autosave, bool) else None


def options_from_save(save: dict) -> Options:
    """The log's settings; each one a save from before it was kept doesn't have loads as its default."""
    return Options(message_speed_from_save(save), dialog_style_from_save(save), npcs_make_way_from_save(save),
                   fade_style_from_save(save), auto_stairs_from_save(save), auto_grind_stop_from_save(save),
                   menu_speed_from_save(save), soundtrack_from_save(save), autosave=autosave_from_save(save),
                   **{switch.field_name: switch.valid(save.get(switch.save_key)) for switch in SWITCHES})


def options_to_save(options: Options) -> dict:
    """The save file entries for these settings (CommandMenu.save, TitleMenu.change_message_speed)."""
    entries = {MESSAGE_SPEED_SAVE_KEY: options.message_speed, DIALOG_STYLE_SAVE_KEY: options.dialog_style,
               NPCS_MAKE_WAY_SAVE_KEY: options.npcs_make_way, FADE_STYLE_SAVE_KEY: options.fade_style,
               AUTO_STAIRS_SAVE_KEY: options.auto_stairs, AUTO_GRIND_STOP_SAVE_KEY: options.auto_grind_stop,
               MENU_SPEED_SAVE_KEY: options.menu_speed, SOUNDTRACK_SAVE_KEY: options.soundtrack.value,
               **{switch.save_key: getattr(options, switch.field_name) for switch in SWITCHES}}
    if options.autosave is not None:
        entries[AUTOSAVE_SAVE_KEY] = options.autosave
    return entries


def options_from_config(config: dict) -> Options:
    """The settings the running game uses."""
    return Options(config.get('TEXT_SPEED', DEFAULT_MESSAGE_SPEED), config.get('DIALOG_STYLE', DEFAULT_DIALOG_STYLE),
                   bool(config.get('NPCS_MAKE_WAY', DEFAULT_NPCS_MAKE_WAY)),
                   fade_style(config), bool(config.get('AUTO_STAIRS', DEFAULT_AUTO_STAIRS)),
                   auto_grind_stop_from_save({AUTO_GRIND_STOP_SAVE_KEY: config.get('AUTO_GRIND_STOP')}),
                   menu_speed_from_save({MENU_SPEED_SAVE_KEY: config.get('MENU_SPEED')}), soundtrack(config),
                   autosave=bool(config.get('AUTOSAVE', DEFAULT_AUTOSAVE)),
                   **{switch.field_name: switch.valid(config.get(switch.config_key)) for switch in SWITCHES})


def apply_options(config: dict, options: Options) -> None:
    """Use these settings from now on: the dialog code reads TEXT_SPEED and DIALOG_STYLE for every message, and
    MovementController.ask_npc_to_make_way reads NPCS_MAKE_WAY for every bump, screen_fade reads FADE_STYLE for every
    fade, MapManager.handle_warps reads AUTO_STAIRS for every step, auto-grind reads AUTO_GRIND_STOP for every check
    and the menu clock reads MENU_SPEED (src/waiting.py menu_speed); the music is read from SOUNDTRACK each time
    one starts (src/directories.py). Each of the SWITCHES goes into its config key,
    which the game reads at each key press (Game.apply_option makes the music and the game speed follow at once); the
    shops read SHOP_PREVIEW whenever their list opens, Q reads QUEST_JOURNAL each time it's pressed, Game.map_frame
    reads AUTOSAVE every frame, the inventory checks read BAG_SIZE for every item added, and Game.handle_a_button and
    Game.handle_message_log_key read SMART_A and MESSAGE_LOG for every press."""
    config['TEXT_SPEED'] = options.message_speed
    config['DIALOG_STYLE'] = options.dialog_style
    config['NPCS_MAKE_WAY'] = options.npcs_make_way
    config['FADE_STYLE'] = options.fade_style
    config['AUTO_STAIRS'] = options.auto_stairs
    config['AUTO_GRIND_STOP'] = options.auto_grind_stop
    config['MENU_SPEED'] = options.menu_speed
    config[SOUNDTRACK_KEY] = options.soundtrack
    for switch in SWITCHES:
        config[switch.config_key] = getattr(options, switch.field_name)
    if options.autosave is not None:
        config['AUTOSAVE'] = options.autosave


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
