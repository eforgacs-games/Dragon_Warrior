"""Every option the options overlay changes (src/options_overlay.py), each declared once. Not NES, apart from the
message speed.

An Option is the config key the game reads, its values (in the order the overlay goes round them), its default, its
NES and MODERN preset values, and where it is kept:

- per adventure log (``save_key``): beside the NES's message speed in the save file (src/save_file.py) and in save
  states, as a field of Options. A new quest starts with the defaults, which are the NES preset's values, so a new
  quest plays as the NES does until the player switches something on.
- global (no save_key): the player's, not the adventure's, kept in the global settings file (src/settings.py) as the
  Settings field of the same name.

Everything else is derived from this table: Options and its save file entries (options_from_save, options_to_save),
reading the options in force from the config (options_from_config) and putting them back (apply_options), the
settings file's entries and their defaults (Settings), the presets (src/options_overlay.py preset_values) and the
overlay's rows. A value that isn't one of an option's values (a save from before the option was kept, a hand-edited
file) loads as its default, so one bad value never loses the others.
"""
from dataclasses import dataclass
from typing import Any, override

from src.display_filters import SCALING_KEY, SCALING_MODES, SCALING_SMOOTH, SCANLINES_KEY
from src.languages import LANGUAGE_NAMES
from src.items import BAG_SIZES, BIG_BAG_SLOTS, INVENTORY_SLOTS
from src.random_streams import RANDOMNESS_NES, RANDOMNESS_SEEDED
from src.quest_journal import JOURNAL_HINTS, JOURNAL_LEARNED, JOURNAL_OFF, JOURNAL_SETTINGS, LEGACY_JOURNAL_GOALS
from src.soundtrack import DEFAULT_SOUNDTRACK, SOUNDTRACK_KEY, SOUNDTRACK_SAVE_KEY, SOUNDTRACKS, Soundtrack, \
    soundtrack, soundtrack_from_save
from src.view import VIEW_NES, VIEW_WIDE
from src.visual_effects import FADE_STYLE_NES, FADE_STYLES
from src.waiting import MENU_SPEED_NORMAL, MENU_SPEEDS

ON_OFF = (False, True)

# MessageSpeed: #$00-fast, #$01-normal, #$02-slow; the window lists them in that order (WndRow = MessageSpeed)
MESSAGE_SPEED_NAMES = ('Fast', 'Normal', 'Slow')
CLASSIC = 'Classic'  # the NES dialog window (src/dialog_box.py), the default
MODERN = 'Modern'  # each message replaces the last one, as this game drew dialog before it matched the NES
DIALOG_STYLES = (CLASSIC, MODERN)
AUTO_GRIND_STOP_VALUES = ('RedHP', 'HalfHP', 'ThreeQuartersHP', 'Danger')
AUTO_HEAL_OFF, AUTO_HEAL_ON, AUTO_HEAL_KEEP_ONE = AUTO_HEAL_SETTINGS = ('Off', 'On', 'KeepOneHeal')
ENCOUNTERS_NES, ENCOUNTERS_HALF, ENCOUNTERS_OFF = ENCOUNTER_SETTINGS = ('NES', 'Half', 'Off')
EXP_GOLD_MULTIPLIERS = (1, 2, 4)
STATUS_WINDOW_NES, STATUS_WINDOW_ALWAYS = STATUS_WINDOW_SETTINGS = ('NES', 'Always')

# AUTOSAVE in a config that doesn't set it: OFF, the NES (it only saves with King Lorik). Every config sets it OFF, so
# the tests and dev runs never write an autosave.
DEFAULT_AUTOSAVE = False


def same_value(value: Any, choice: Any) -> bool:
    """Equal and of the same type: True is not 1."""
    return value == choice and type(value) is type(choice)


@dataclass(frozen=True, slots=True)
class Option:
    """One option (see the module docstring). ``name`` is its Options field (per log) or its Settings field (global);
    ``presets`` is its (NES, MODERN) values, or None for an option the presets leave alone; ``renamed`` maps a value
    an older build saved to the value it is now. While any of the config keys in ``locked_by`` is set (not None or
    False), the option is ``locked_value`` whatever it says (``in_force``), and the overlay grays its row out."""
    name: str
    config_key: str
    values: tuple[Any, ...]
    default: Any
    presets: tuple[Any, Any] | None = None
    save_key: str | None = None
    renamed: tuple[tuple[Any, Any], ...] = ()
    locked_by: tuple[str, ...] = ()
    locked_value: Any = None

    @property
    def per_log(self) -> bool:
        return self.save_key is not None

    def valid(self, value: Any) -> Any:
        """value if it's one of the values (a bool for an on/off option, not 0 or 1), what it was renamed to if an
        older build saved it under another name, the default otherwise."""
        value = next((new for old, new in self.renamed if same_value(value, old)), value)
        if any(same_value(value, choice) for choice in self.values):
            return value
        return self.default

    def locked(self, config: dict) -> bool:
        return any(config.get(key) is not None and config.get(key) is not False for key in self.locked_by)  # SEED 0 too

    def in_force(self, config: dict) -> Any:
        """What the game goes by: the config's value, or ``locked_value`` while the option is locked. The config's
        value is kept as it is (and saved with the adventure log), in force again once nothing locks it."""
        return self.locked_value if self.locked(config) else self.from_config(config)

    def from_save(self, save: dict) -> Any:
        """The value a save file (or a save state's options) holds."""
        assert self.save_key is not None
        return self.valid(save.get(self.save_key))

    def to_save(self, value: Any) -> Any:
        """The value as the save file holds it."""
        return value

    def from_config(self, config: dict) -> Any:
        """The value in force in the game."""
        return self.valid(config.get(self.config_key))


class SoundtrackOption(Option):
    """MUSIC (src/soundtrack.py): saved by its name; a save from before there were three soundtracks loads its
    OrchestraMusic switch, and a config its old ORCHESTRA_MUSIC_ENABLED switch."""
    __slots__ = ()

    @override
    def from_save(self, save: dict) -> Any:
        return soundtrack_from_save(save)

    @override
    def to_save(self, value: Any) -> Any:
        return value.value

    @override
    def from_config(self, config: dict) -> Any:
        return soundtrack(config)


class AutosaveOption(Option):
    """AUTOSAVE (src/autosave.py): a save from before it was kept loads as None, which leaves the config's as it is (and
    isn't written back); a config without it is OFF (DEFAULT_AUTOSAVE)."""
    __slots__ = ()

    @override
    def from_config(self, config: dict) -> Any:
        return bool(config.get(self.config_key, DEFAULT_AUTOSAVE))


# Per adventure log, in the order of Options' fields and of the save file's entries

# The NES's own setting (LoadSavedData, LFBC8). The NES starts a new quest on NORMAL (NewQuest, LF8D4: LDA
# #MSG_NORMAL); this game defaults to FAST, and NORMAL is a choice away. No preset changes it.
MESSAGE_SPEED = Option('message_speed', 'TEXT_SPEED', MESSAGE_SPEED_NAMES, 'Fast', save_key='MessageSpeed')
# The MODERN dialog style is how this game drew dialog before it matched the NES, not a convenience
DIALOG_STYLE = Option('dialog_style', 'DIALOG_STYLE', DIALOG_STYLES, CLASSIC, (CLASSIC, CLASSIC), 'DialogStyle')
# MovementController.ask_npc_to_make_way (#297)
NPCS_MAKE_WAY = Option('npcs_make_way', 'NPCS_MAKE_WAY', (True, False), False, (False, True), 'NpcsMakeWay')
# src/visual_effects.py screen_fade (#319)
FADE_STYLE = Option('fade_style', 'FADE_STYLE', FADE_STYLES, FADE_STYLE_NES, (FADE_STYLE_NES, FADE_STYLE_NES),
                    'FadeStyle')
# STAIRS (MapManager.handle_warps): STEP ON takes stairs by stepping onto them; the NES only with the STAIRS command
# (Bank03 CheckStairs)
AUTO_STAIRS = Option('auto_stairs', 'AUTO_STAIRS', (True, False), False, (False, True), 'AutoStairs')
# GRIND STOP: when auto-grind stops (src/auto_grind.py)
AUTO_GRIND_STOP = Option('auto_grind_stop', 'AUTO_GRIND_STOP', AUTO_GRIND_STOP_VALUES, AUTO_GRIND_STOP_VALUES[0],
                         (AUTO_GRIND_STOP_VALUES[0], AUTO_GRIND_STOP_VALUES[0]), 'AutoGrindStop')
# MENU SPEED (#440): the selection windows at 1x whatever the game speed (src/waiting.py menu_ticks), or at the game
# speed. On the NES there is only 1x, so NORMAL is as faithful as FOLLOW GAME; both presets keep NORMAL.
MENU_SPEED = Option('menu_speed', 'MENU_SPEED', MENU_SPEEDS, MENU_SPEED_NORMAL, (MENU_SPEED_NORMAL, MENU_SPEED_NORMAL),
                    'MenuSpeed')
# MUSIC: the NES preset plays the NES's soundtrack, MODERN the orchestral one
MUSIC = SoundtrackOption('soundtrack', SOUNDTRACK_KEY, SOUNDTRACKS, DEFAULT_SOUNDTRACK,
                         (Soundtrack.NES, Soundtrack.ORCHESTRA), SOUNDTRACK_SAVE_KEY)
# GAME SPEED: keys 1 to 5 set the game speed (src/waiting.py); off, they do nothing (the NES has one speed)
GAME_SPEED_KEYS = Option('game_speed_keys', 'GAME_SPEED_KEYS', ON_OFF, False, (False, True), 'GameSpeedKeys')
# SAVE STATES: F1-F3 load and Shift+F1-F3 save a state; off, the keys do nothing
SAVE_STATES = Option('save_states', 'SAVE_STATES', ON_OFF, False, (False, True), 'SaveStates')
# REWIND: Backspace rewinds; off, it does nothing
REWIND = Option('rewind', 'REWIND', ON_OFF, False, (False, True), 'Rewind')
# AUTO-GRIND: G starts auto-grind (src/auto_grind.py); off, G does nothing
AUTO_GRIND = Option('auto_grind', 'AUTO_GRIND', ON_OFF, False, (False, True), 'AutoGrind')
# CHEATS: F4 auto-battle and F9 invulnerability; off, the keys do nothing and both are off. Cheats, not
# conveniences: off in both presets.
CHEAT_KEYS = Option('cheat_keys', 'CHEAT_KEYS', ON_OFF, False, (False, False), 'CheatKeys')
# QUICK ACTION: Enter on the map takes a chest, opens a door or talks without the COMMAND window; off, Enter is the A
# button there too, as everywhere else
QUICK_ACTION = Option('quick_action', 'QUICK_ACTION', ON_OFF, False, (False, True), 'QuickAction')
# ENCOUNTERS: the NES's random fights, half as many (every other one that would start is skipped, so the NES's rolls
# and enemy choice are untouched) or none (FieldEncounters.thin_encounters); scripted fights always happen. How many
# fights, and what they give, are the game's balance, not conveniences: NES in both presets.
ENCOUNTERS = Option('encounters', 'ENCOUNTERS', ENCOUNTER_SETTINGS, ENCOUNTERS_NES, (ENCOUNTERS_NES, ENCOUNTERS_NES),
                    'Encounters')
# EXP/GOLD: the experience and gold a won fight gives, times 1 (the NES), 2 or 4 (Battle.enemy_defeated)
EXP_GOLD = Option('exp_gold', 'EXP_GOLD', EXP_GOLD_MULTIPLIERS, 1, (1, 1), 'ExpGold')
# RUN BUTTON: B held while walking on the map walks twice as fast (MovementController.run_button_held)
RUN_BUTTON = Option('run_button', 'RUN_BUTTON', ON_OFF, False, (False, True), 'RunButton')
# STATUS WINDOW: the NES pop-up after standing still, or always on the map (Drawer.status_window_always)
STATUS_WINDOW = Option('status_window', 'STATUS_WINDOW', STATUS_WINDOW_SETTINGS, STATUS_WINDOW_NES,
                       (STATUS_WINDOW_NES, STATUS_WINDOW_ALWAYS), 'StatusWindow')
# SHOP PREVIEW (#401): a weapon and armor shop's list shows the attack or defense power the highlighted item would give
# (src/shop_preview.py). Information only: on in MODERN.
SHOP_PREVIEW = Option('shop_preview', 'SHOP_PREVIEW', ON_OFF, False, (False, True), 'ShopPreview')
# QUEST JOURNAL (#410): what Q shows on the map (src/quest_journal.py): nothing (the NES), the goals the hero has
# learned of, or those with what was said about them. MODERN shows the hints, since they're only what the hero was told.
# Older builds' GOALS showed every open goal; it loads as LEARNED.
QUEST_JOURNAL = Option('quest_journal', 'QUEST_JOURNAL', JOURNAL_SETTINGS, JOURNAL_OFF, (JOURNAL_OFF, JOURNAL_HINTS),
                       'QuestJournal', renamed=((LEGACY_JOURNAL_GOALS, JOURNAL_LEARNED),))
# BAG (#413): the inventory's slots for everything but Herbs and Magic Keys (src/items.py bag_slots): the NES's 8, or 16
BAG_SIZE = Option('bag_size', 'BAG_SIZE', BAG_SIZES, INVENTORY_SLOTS, (INVENTORY_SLOTS, BIG_BAG_SLOTS), 'BagSize')
# SMART A (#404): A on the map does TALK, TAKE, DOOR or STAIRS when one applies, instead of opening COMMAND
# (MapHotkeys.smart_command)
SMART_A = Option('smart_a', 'SMART_A', ON_OFF, False, (False, True), 'SmartA')
# MESSAGE LOG (#405): the MESSAGE LOG key (L) shows the last messages on the map (src/message_log.py). Off in MODERN
# too: the quest journal (Q) keeps what matters (the hints with who said them, and the records: src/records.py)
MESSAGE_LOG = Option('message_log', 'MESSAGE_LOG', ON_OFF, False, (False, False), 'MessageLog')
# STATS PAGE (#414): the STATS key (P) shows the adventure's play statistics on the map (src/stats_screen.py). They're
# counted whatever it says (src/play_stats.py). Information only: on in MODERN.
STATS_PAGE = Option('stats_page', 'STATS_PAGE', ON_OFF, False, (False, True), 'StatsPage')
# ACHIEVEMENTS (#425): achievements are unlocked, shown in a banner and on the TROPHIES key's page (T,
# src/achievements.py). Off, nothing is unlocked.
ACHIEVEMENTS = Option('achievements', 'ACHIEVEMENTS', ON_OFF, False, (False, True), 'Achievements')
# FALLEN HEROES (co-op, src/party.py): a party's hero brought to 0 HP in a fight stays down until an inn (INN, the
# stricter rule and the default, as in the later Dragon Quests) or gets back up with 1 HP once the fight is won or fled
# (GET UP). The NES has one hero, so no preset changes it.
FALLEN_INN, FALLEN_GET_UP = 'Inn', 'GetUp'
FALLEN = Option('fallen', 'FALLEN', (FALLEN_INN, FALLEN_GET_UP), FALLEN_INN, None, 'FallenHeroes')
# AUTOSAVE: the autosave slot (src/autosave.py); the NES only saves with King Lorik
AUTOSAVE = AutosaveOption('autosave', 'AUTOSAVE', ON_OFF, None, (False, True), 'Autosave')
# AUTO-HEAL: when auto-grind's HP is low (GRIND STOP), it casts HEAL or HEALMORE instead of stopping, until HP is out
# of danger, with all the MP or keeping enough for one HEAL (src/auto_grind.py). Off, it stops.
AUTO_HEAL = Option('auto_heal', 'AUTO_HEAL', AUTO_HEAL_SETTINGS, AUTO_HEAL_OFF, (AUTO_HEAL_OFF, AUTO_HEAL_KEEP_ONE),
                   'AutoHeal')
# AUTO-INN: when auto-grind can't go on (HP low with no heal, or no MP left for one), it walks to the nearest inn it can
# pay for, stays the night and walks back (src/inn_trip.py). Off, it stops.
AUTO_INN = Option('auto_inn', 'AUTO_INN', ON_OFF, False, (False, True), 'AutoInn')

# RANDOMNESS (src/random_streams.py): every roll from the NES's own random number (UpdateRandNum, stepped every frame and
# every roll), or SEEDED, from the hero's and the world's streams, which a seed and multiplayer need: --seed (SEED) and
# a multiplayer game (MULTIPLAYER) lock it on SEEDED. The NES's in both presets: SEEDED changes how the dice are
# thrown, not what they give.
RANDOMNESS = Option('randomness', 'RANDOMNESS', (RANDOMNESS_NES, RANDOMNESS_SEEDED), RANDOMNESS_NES,
                    (RANDOMNESS_NES, RANDOMNESS_NES), 'Randomness', locked_by=('SEED', 'MULTIPLAYER'),
                    locked_value=RANDOMNESS_SEEDED)

PER_LOG_OPTIONS = (MESSAGE_SPEED, DIALOG_STYLE, NPCS_MAKE_WAY, FADE_STYLE, AUTO_STAIRS, AUTO_GRIND_STOP, MENU_SPEED,
                   MUSIC, GAME_SPEED_KEYS, SAVE_STATES, REWIND, AUTO_GRIND, CHEAT_KEYS, QUICK_ACTION, ENCOUNTERS,
                   EXP_GOLD, RUN_BUTTON, STATUS_WINDOW, SHOP_PREVIEW, QUEST_JOURNAL, BAG_SIZE, SMART_A, MESSAGE_LOG,
                   STATS_PAGE, AUTOSAVE, AUTO_HEAL, AUTO_INN, RANDOMNESS, ACHIEVEMENTS, FALLEN)

# Global, in the order of Settings' fields

# None: from the system locale (base_config language_from_locale). No preset changes it.
LANGUAGE = Option('language', 'LANGUAGE', LANGUAGE_NAMES, None)
# The display filters (src/display_filters.py). Neither is on the NES or off it (the NES drew to a TV), so no preset
# changes them.
SCANLINES = Option('scanlines', SCANLINES_KEY, ON_OFF, False)
SCALING = Option('scaling', SCALING_KEY, SCALING_MODES, SCALING_SMOOTH)
# VIEW (src/view.py): WIDE is a display preference, not a convenience: both presets keep NES (4:3)
VIEW = Option('view', 'VIEW', (VIEW_NES, VIEW_WIDE), VIEW_NES, (VIEW_NES, VIEW_NES))
# DUNGEON MAP: M shows the dark floor's map (src/dungeon_map.py)
DUNGEON_MAP = Option('dungeon_map', 'DUNGEON_MAP', ON_OFF, False, (False, True))
# CONFIRM NAME: a full name waits on END, START ends the name (src/name_entry.py)
NAME_CONFIRM = Option('name_confirm', 'NAME_CONFIRM', ON_OFF, False, (False, True))

# HEROES (co-op, #438): how many heroes a new quest starts with, the NES's one or a party of two (src/party.py). It
# only changes the next BEGIN A NEW QUEST: a log keeps the party it was started with. Co-op isn't a convenience: no
# preset changes it.
PARTY = Option('party', 'PARTY', (1, 2), 1)

GLOBAL_OPTIONS = (LANGUAGE, SCANLINES, SCALING, VIEW, DUNGEON_MAP, NAME_CONFIRM, PARTY)

ALL_OPTIONS = PER_LOG_OPTIONS + GLOBAL_OPTIONS
OPTIONS_BY_CONFIG_KEY = {option.config_key: option for option in ALL_OPTIONS}


@dataclass(frozen=True, slots=True)
class Options:
    """The settings kept per adventure log: one field per PER_LOG_OPTIONS option, in its order, defaulting to its
    default."""
    message_speed: str = MESSAGE_SPEED.default
    dialog_style: str = DIALOG_STYLE.default
    npcs_make_way: bool = NPCS_MAKE_WAY.default
    fade_style: str = FADE_STYLE.default
    auto_stairs: bool = AUTO_STAIRS.default
    auto_grind_stop: str = AUTO_GRIND_STOP.default
    menu_speed: str = MENU_SPEED.default
    soundtrack: Soundtrack = MUSIC.default
    game_speed_keys: bool = GAME_SPEED_KEYS.default
    save_states: bool = SAVE_STATES.default
    rewind: bool = REWIND.default
    auto_grind: bool = AUTO_GRIND.default
    cheat_keys: bool = CHEAT_KEYS.default
    quick_action: bool = QUICK_ACTION.default
    encounters: str = ENCOUNTERS.default
    exp_gold: int = EXP_GOLD.default
    run_button: bool = RUN_BUTTON.default
    status_window: str = STATUS_WINDOW.default
    shop_preview: bool = SHOP_PREVIEW.default
    quest_journal: str = QUEST_JOURNAL.default
    bag_size: int = BAG_SIZE.default
    smart_a: bool = SMART_A.default
    message_log: bool = MESSAGE_LOG.default
    stats_page: bool = STATS_PAGE.default
    autosave: bool | None = AUTOSAVE.default  # None: the config's AUTOSAVE is kept
    auto_heal: str = AUTO_HEAL.default
    auto_inn: bool = AUTO_INN.default
    randomness: str = RANDOMNESS.default
    achievements: bool = ACHIEVEMENTS.default
    fallen: str = FALLEN.default


# A new quest's settings when none are chosen: the default message speed and the NES preset's values, as base_config
# has them
DEFAULT_OPTIONS = Options()


def options_from_save(save: dict) -> Options:
    """The log's settings; each one a save from before it was kept doesn't have loads as its default."""
    return Options(**{option.name: option.from_save(save) for option in PER_LOG_OPTIONS})


def options_to_save(options: Options) -> dict:
    """The save file entries for these settings (CommandMenu.save, TitleMenu.change_message_speed); an AUTOSAVE of
    None isn't written."""
    entries = {}
    for option in PER_LOG_OPTIONS:
        assert option.save_key is not None
        value = getattr(options, option.name)
        if value is not None:
            entries[option.save_key] = option.to_save(value)
    return entries


def options_from_config(config: dict) -> Options:
    """The settings the running game uses."""
    return Options(**{option.name: option.from_config(config) for option in PER_LOG_OPTIONS})


def apply_options(config: dict, options: Options) -> None:
    """Use these settings from now on: each goes into its config key, which the game reads whenever it next needs it
    (the dialog code for every message, MovementController.ask_npc_to_make_way for every bump, screen_fade for every
    fade, MapManager.handle_warps for every step, the music each time one starts, the map's keys for every press, and
    so on; src/options_overlay.py apply_option makes the music and the game speed follow at once). An AUTOSAVE of None
    leaves the config's as it is."""
    for option in PER_LOG_OPTIONS:
        value = getattr(options, option.name)
        if value is not None:
            config[option.config_key] = value
