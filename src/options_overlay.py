"""The options overlay: this game's own settings, changed during play. Not on the NES.

SELECT (U) or Tab on the map opens it (MapHotkeys.press_select), when START would pause the game: no window open,
and only once the hero and the NPCs have finished their steps (MovementController.resolve_pending_freezes). The map
frame stays on screen, darkened by a translucent black overlay, with one NES-style window over it (src/windows.py,
drawn by src/translated_window.py).

Every convenience this game adds to the NES can be switched on or off on its own, with the NES behaviour as one of its
values (#409). The rows are grouped in pages, one page at a time in the window, titled with the page's name:

    LOOK & SOUND
    MESSAGE SPEED  FAST / NORMAL / SLOW     (TEXT_SPEED, src/dialog_box.py; the NES's own setting)
    DIALOG STYLE   CLASSIC (NES) / MODERN   (DIALOG_STYLE, src/dialog_box.py)
    FADE STYLE     NES / SMOOTH             (FADE_STYLE, src/visual_effects.py screen_fade)
    MUSIC          NES / SFC / ORCHESTRA    (SOUNDTRACK, src/soundtrack.py, src/directories.py music_paths)
    LANGUAGE       ENGLISH / 한국어          (LANGUAGE: a global setting, src/settings.py)
    SCANLINES      OFF / ON                 (SCANLINES: a display filter, src/display_filters.py; global)
    SCALING        SMOOTH / PIXEL PERFECT   (SCALING: pygame's SCALED, or whole multiples of 256x240 only; global)
    VIEW           NES (4:3) / WIDE         (VIEW: more of the map left and right, src/view.py; global)
    STATUS WINDOW  NES / ALWAYS             (STATUS_WINDOW: the pop-up window, Drawer.status_window_always)
    SHOP PREVIEW   OFF (NES) / ON           (SHOP_PREVIEW: the shops' stat preview, src/shop_preview.py)

    GAMEPLAY
    NPCS MAKE WAY  ON / OFF (NES)           (NPCS_MAKE_WAY, MovementController.ask_npc_to_make_way)
    STAIRS         STEP ON / NES            (AUTO_STAIRS, MapManager.handle_warps)
    QUICK ACTION   OFF (NES) / ON           (QUICK_ACTION: Enter takes, opens or talks, MapHotkeys.press_smart_a_key)
    SMART A        OFF (NES) / ON           (SMART_A: A does TALK, TAKE, DOOR or STAIRS, MapHotkeys.smart_command)
    ENCOUNTERS     NES / HALF / OFF         (ENCOUNTERS: the random fights, Game.thin_encounters)
    EXP/GOLD       x1 (NES) / x2 / x4       (EXP_GOLD: what a won fight gives, Battle.enemy_defeated)
    QUEST JOURNAL  OFF (NES) / LEARNED / LEARNED+HINTS  (QUEST_JOURNAL: what Q shows, src/quest_journal.py)
    AUTOSAVE       OFF (NES) / ON           (AUTOSAVE: the autosave slot, src/autosave.py)
    BAG            NES (8) / 16             (BAG_SIZE: the inventory slots, src/items.py bag_slots)
    RUN BUTTON     OFF (NES) / ON           (RUN_BUTTON: hold B to walk twice as fast, src/movement.py)

    CONTROLS
    GAME SPEED     OFF (NES) / ON           (GAME_SPEED_KEYS: keys 1 to 5, src/waiting.py)
    SAVE STATES    OFF (NES) / ON           (SAVE_STATES: F1-F3, Shift+F1-F3)
    REWIND         OFF (NES) / ON           (REWIND: Backspace)
    AUTO-GRIND     OFF (NES) / ON           (AUTO_GRIND: G, src/auto_grind.py)
    GRIND STOP     RED HP / HALF HP / 3/4 HP  (AUTO_GRIND_STOP: when auto-grind stops)
    MENU SPEED     NORMAL / FOLLOW GAME     (MENU_SPEED: the selection windows at 1x, or at the game speed,
                                             src/waiting.py menu_ticks)
    CHEATS         OFF (NES) / ON           (CHEAT_KEYS: F4 auto-battle, F9 invulnerability)
    DUNGEON MAP    OFF (NES) / ON           (DUNGEON_MAP: whether M shows the dungeon map, src/dungeon_map.py; global)
    MESSAGE LOG    OFF (NES) / ON           (MESSAGE_LOG: the L key shows the last messages, src/message_log.py)
    CONTROLS                                (A opens the CONTROLS screen to rebind the keys, src/controls_screen.py)

    OTHER
    CONFIRM NAME   OFF (NES) / ON           (NAME_CONFIRM: a full name waits on END, START ends it; global)

Above every page's rows are two more:

    PRESET         NES / MODERN / CUSTOM
    PAGE           1/3

PRESET sets every row that belongs to a preset at once (OptionRow.presets): NES to the NES behaviour, MODERN to the
recommended conveniences. It reads NES or MODERN while every such row has that preset's value, and CUSTOM as soon as one
differs from both. A new game reads NES: every such row's default (base_config, src/game_options.py) is its NES
value. Choosing it goes round NES, MODERN and, once there has been one, the last CUSTOM set of values, so a custom set
is never lost by trying a preset. The message speed (the NES's own setting, chosen on the title menu too)
isn't part of either.

PAGE (or START, Page Up and Page Down from any row) shows the next or the previous page; the cursor stays where it is,
or goes to the new page's last row if it has fewer.

Up and down move the NES cursor (src/cursor.py) between the rows, stopping at the first and last; left, right or A
change the row's value, with the menu button sound. A change goes into the game config at once, so the next dialog,
fade, bump, step or key press uses it (apply_option does what can't wait for that: the music, the game speed and
the cheats), and is saved with the adventure log the next time the game is saved (options_from_config). LANGUAGE,
SCANLINES, SCALING, VIEW and DUNGEON MAP are the player's, not the adventure's, kept in the global settings file:
apply_option switches the game to the new language at once (Game.set_language), this window included, the display
filters from the next frame on, and DUNGEON MAP from the next M; the VIEW is shown once the overlay closes
(Game.set_view). B, Esc, SELECT or Tab close it, and the map frame is put back exactly as it was. Everything is on the
NES buttons, so a gamepad works it as the keyboard does.

The overlay runs its own loop, so nothing else runs while it's open: the map, the NPCs, the timers and the pop-up
window wait, as they do for a dialog.
"""
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from pygame import K_PAGEDOWN, K_PAGEUP, KEYDOWN, SRCALPHA, Rect, Surface, display

from src.color import BLACK
from src.common import A_BUTTON_KEYS, B_BUTTON_KEYS, DOWN_KEYS, LEFT_KEYS, RIGHT_KEYS, SELECT_BUTTON_KEYS, \
    START_BUTTON_KEYS, UP_KEYS, set_gettext_language
from src.controls import KeySet
from src.controls_screen import ControlsScreen
from src.cursor import BlinkingCursor
from src.directories import music_name
from src.display_filters import PRESENTER, SCALING_KEY, SCANLINES_KEY
from src.game_options import AUTO_GRIND, AUTO_GRIND_STOP, AUTO_STAIRS, AUTOSAVE, BAG_SIZE, CHEAT_KEYS, DIALOG_STYLE, \
    DUNGEON_MAP, ENCOUNTERS, EXP_GOLD, FADE_STYLE, GAME_SPEED_KEYS, LANGUAGE, MENU_SPEED, MESSAGE_LOG, MESSAGE_SPEED, \
    MUSIC, NAME_CONFIRM, NPCS_MAKE_WAY, OPTIONS_BY_CONFIG_KEY, QUEST_JOURNAL, QUICK_ACTION, REWIND, RUN_BUTTON, \
    SAVE_STATES, SCALING, SCANLINES, SHOP_PREVIEW, SMART_A, STATUS_WINDOW, VIEW, Option, Options, apply_options
from src.options_screen import MESSAGE_SPEED_LABELS
from src.selection import frame_events, next_frame
from src.translated_window import draw_translated_window
from src.view import full_screen
from src.soundtrack import SOUNDTRACK_KEY
from src.waiting import set_game_speed, set_speed_keys_enabled
from src.windows import Window, WindowLayout, WindowText

# The keys that open the overlay on the map, and close it again
OPTIONS_KEYS = SELECT_BUTTON_KEYS + KeySet('OPTIONS')  # U and Tab, as bound (src/controls.py)
CLOSE_KEYS = B_BUTTON_KEYS + OPTIONS_KEYS
# The keys that turn the page from any row
NEXT_PAGE_KEYS = START_BUTTON_KEYS + (K_PAGEDOWN,)
PREVIOUS_PAGE_KEYS = (K_PAGEUP,)

# How dark the map gets behind the window (0 is clear, 255 black)
OVERLAY_ALPHA = 160

# The presets (PRESET row)
PRESET_NES = 'NES'
PRESET_MODERN = 'Modern'
PRESET_CUSTOM = 'Custom'
PRESET_LABELS = {PRESET_NES: "NES", PRESET_MODERN: "MODERN", PRESET_CUSTOM: "CUSTOM"}

ON_OFF_LABELS = ("OFF (NES)", "ON")


@dataclass(frozen=True, slots=True)
class OptionRow:
    """One row: its label, the option it sets (src/game_options.py: its config key, its values in the order they're
    cycled and its presets), and its values' labels."""
    label: str
    option: Option
    value_labels: tuple[str, ...]

    @property
    def config_key(self) -> str:
        return self.option.config_key

    @property
    def values(self) -> tuple[Any, ...]:
        return self.option.values

    @property
    def presets(self) -> tuple[Any, Any] | None:
        """Its (NES, MODERN) values, or None for a row the presets leave alone."""
        return self.option.presets

    def index(self, config: dict) -> int:
        """The current value's place in values (the first value if the config holds something else)."""
        value = config.get(self.config_key)
        return self.values.index(value) if value in self.values else 0

    def value_label(self, config: dict) -> str:
        return self.value_labels[self.index(config)]

    def change(self, config: dict, step: int) -> None:
        """Set the next (step 1) or the previous (step -1) value, going round."""
        config[self.config_key] = self.values[(self.index(config) + step) % len(self.values)]


def switch_row(label: str, option: Option) -> OptionRow:
    """An OFF (NES) / ON row for a convenience."""
    return OptionRow(label, option, ON_OFF_LABELS)


@dataclass(frozen=True, slots=True)
class ScreenRow:
    """A row with no value that opens a screen of its own with A (CONTROLS)."""
    label: str
    value_labels: tuple[str, ...] = ()

    def value_label(self, config: dict) -> str:
        return ''


CONTROLS_ROW = ScreenRow("CONTROLS")


@dataclass(frozen=True, slots=True)
class OptionPage:
    title: str
    rows: tuple[OptionRow | ScreenRow, ...]


# What each option does, its values and its presets are in src/game_options.py
OPTION_PAGES = (
    OptionPage("LOOK & SOUND", (
        OptionRow("MESSAGE SPEED", MESSAGE_SPEED, MESSAGE_SPEED_LABELS),
        OptionRow("DIALOG STYLE", DIALOG_STYLE, ("CLASSIC (NES)", "MODERN")),
        OptionRow("FADE STYLE", FADE_STYLE, ("NES", "SMOOTH")),
        OptionRow("MUSIC", MUSIC, ("NES", "SFC", "ORCHESTRA")),
        # Each language's name is in that language, so it can be found whichever is on
        OptionRow("LANGUAGE", LANGUAGE, ("ENGLISH", "한국어")),
        OptionRow("SCANLINES", SCANLINES, ("OFF", "ON")),
        OptionRow("SCALING", SCALING, ("SMOOTH", "PIXEL PERFECT")),
        OptionRow("VIEW", VIEW, ("NES (4:3)", "WIDE")),
        OptionRow("STATUS WINDOW", STATUS_WINDOW, ("NES", "ALWAYS")),
        switch_row("SHOP PREVIEW", SHOP_PREVIEW),
    )),
    OptionPage("GAMEPLAY", (
        OptionRow("NPCS MAKE WAY", NPCS_MAKE_WAY, ("ON", "OFF (NES)")),
        OptionRow("STAIRS", AUTO_STAIRS, ("STEP ON", "NES")),
        switch_row("QUICK ACTION", QUICK_ACTION),
        switch_row("SMART A", SMART_A),
        OptionRow("ENCOUNTERS", ENCOUNTERS, ("NES", "HALF", "OFF")),
        OptionRow("EXP/GOLD", EXP_GOLD, ("x1 (NES)", "x2", "x4")),
        OptionRow("QUEST JOURNAL", QUEST_JOURNAL, ("OFF (NES)", "LEARNED", "LEARNED+HINTS")),
        switch_row("AUTOSAVE", AUTOSAVE),
        OptionRow("BAG", BAG_SIZE, ("NES (8)", "16")),
        # Walking: on this page, as CONTROLS is full
        switch_row("RUN BUTTON", RUN_BUTTON),
    )),
    OptionPage("CONTROLS", (
        switch_row("GAME SPEED", GAME_SPEED_KEYS),
        switch_row("SAVE STATES", SAVE_STATES),
        switch_row("REWIND", REWIND),
        switch_row("AUTO-GRIND", AUTO_GRIND),
        OptionRow("GRIND STOP", AUTO_GRIND_STOP, ("RED HP", "HALF HP", "3/4 HP")),
        OptionRow("MENU SPEED", MENU_SPEED, ("NORMAL", "FOLLOW GAME")),
        switch_row("CHEATS", CHEAT_KEYS),
        switch_row("DUNGEON MAP", DUNGEON_MAP),
        switch_row("MESSAGE LOG", MESSAGE_LOG),
        # A opens the CONTROLS screen to rebind the keys (src/controls_screen.py)
        CONTROLS_ROW,
    )),
    # The other pages are full (each fits 10 rows): settings that don't belong to the map
    OptionPage("OTHER", (
        switch_row("CONFIRM NAME", NAME_CONFIRM),
    )),
)
# The rows with a setting (every row but CONTROLS)
OPTION_ROWS = tuple(row for page in OPTION_PAGES for row in page.rows if isinstance(row, OptionRow))
PRESET_ROWS = tuple(row for row in OPTION_ROWS if row.presets is not None)

PRESET_LABEL = "PRESET"
PAGE_LABEL = "PAGE"
PRESET_ROW, PAGE_ROW = 0, 1  # the two rows above every page's own
FIXED_ROWS = 2


def preset_values(preset: str) -> dict[str, Any]:
    """The config values NES or MODERN sets."""
    which = 0 if preset == PRESET_NES else 1
    return {row.config_key: row.presets[which] for row in PRESET_ROWS if row.presets is not None}


def current_preset(config: dict) -> str:
    """NES or MODERN if every preset row has that preset's value, CUSTOM otherwise."""
    for preset in (PRESET_NES, PRESET_MODERN):
        if all(config.get(key) == value for key, value in preset_values(preset).items()):
            return preset
    return PRESET_CUSTOM


def preset_settings(config: dict) -> dict[str, Any]:
    """The preset rows' current values, to go back to with CUSTOM."""
    return {row.config_key: config.get(row.config_key) for row in PRESET_ROWS}


# The switches that act on the game at once, beyond the config (apply_option), when an adventure log's or a save state's
# options are put in force (apply_log_options)
IMMEDIATE_SWITCHES = ('GAME_SPEED_KEYS', 'CHEAT_KEYS')


def apply_option(game: Any, config_key: str) -> None:
    """An option has just been changed (in the overlay, or by loading options). Most are read from the config when
    they're next needed; these are made to follow at once:

    - The global settings (src/game_options.py GLOBAL_OPTIONS) are saved with the global settings at once. LANGUAGE
      is switched to at once (Game.set_language); the display filters (SCANLINES and SCALING) change from the next
      frame on; VIEW is shown once the overlay closes (Game.set_view); M reads DUNGEON MAP each time it's pressed, and
      the next name entry reads CONFIRM NAME.
    - MUSIC (SOUNDTRACK): every Directories reads the music from the config (src/directories.py), so
      the next music played is from the new set; the map's music is started again from the new set now.
    - GAME SPEED (GAME_SPEED_KEYS): keys 1 to 5 are switched on or off; off goes back to normal speed, and on to
      the speed kept in the global settings.
    - CHEATS (CHEAT_KEYS): switched off, auto-battle and invulnerability are switched off too.
    - REWIND: switched off, the snapshots kept so far are dropped (src/rewind.py takes none while it's off)."""
    config = game.game_state.config
    option = OPTIONS_BY_CONFIG_KEY.get(config_key)
    if option is not None and not option.per_log:
        game.settings.update(**{option.name: option.from_config(config)})  # kept with the global settings
    if config_key == 'LANGUAGE':
        game.set_language(config['LANGUAGE'])
    elif config_key in (SCANLINES_KEY, SCALING_KEY):
        PRESENTER.configure_from(config)
    elif config_key == SOUNDTRACK_KEY:
        name = music_name(game.current_map.music_file_path)
        if name is not None:
            game.current_map.music_file_path = getattr(game.directories, name)
            game.music_player.load_and_play_music(game.current_map.music_file_path)
    elif config_key == 'GAME_SPEED_KEYS':
        set_speed_keys_enabled(bool(config.get('GAME_SPEED_KEYS')))
        if config.get('GAME_SPEED_KEYS'):
            set_game_speed(game.settings.settings.game_speed)
    elif config_key == 'CHEAT_KEYS' and not config.get('CHEAT_KEYS'):
        game.auto_battle = False
        game.invulnerable = False
    elif config_key == 'REWIND' and not config.get('REWIND'):
        game.rewind.snapshots.clear()


def apply_log_options(game: Any, options: Options) -> None:
    """Put an adventure log's (or a save state's) options in force (apply_options), with the switches that act at
    once (IMMEDIATE_SWITCHES). The music isn't restarted: what loads them starts the map's music."""
    apply_options(game.game_state.config, options)
    for config_key in IMMEDIATE_SWITCHES:
        apply_option(game, config_key)


# The window: the screen's full 16 blocks wide (the longest labels and values, MESSAGE SPEED, NPCS MAKE WAY and
# CLASSIC (NES), are 13 tiles each), one block high per row of the longest page plus a block of border at the top and
# bottom, from block row 1, the same size on every page. Laid out like the NES selection windows: the page's title in
# the top border after the corner and 3 border tiles (as COMMAND), the rows double spaced from tile row 2, the cursor in
# tile column 1 and the label after it; the value starts in tile column 17.
MOST_ROWS = FIXED_ROWS + max(len(page.rows) for page in OPTION_PAGES)
OPTIONS_WINDOW = Window(0, 1, 16, MOST_ROWS + 2)
TITLE_COLUMN = 4
FIRST_ROW = 2
CURSOR_COLUMN = 1
LABEL_COLUMN = 2
VALUE_COLUMN = 17


def page_number_label(page: int) -> str:
    return f"{page + 1}/{len(OPTION_PAGES)}"


def options_layout(config: dict, page: int = 0) -> WindowLayout:
    """The window with the page's title, PRESET, PAGE, and each of the page's rows with its current value."""
    shown = OPTION_PAGES[page]
    lines = [(PRESET_LABEL, PRESET_LABELS[current_preset(config)]), (PAGE_LABEL, page_number_label(page))]
    lines += [(row.label, row.value_label(config)) for row in shown.rows]
    texts: list[WindowText] = []
    for number, (label, value) in enumerate(lines):
        tile_row = FIRST_ROW + 2 * number
        texts.append(WindowText(label, LABEL_COLUMN, tile_row))
        if value:  # a screen row (CONTROLS) has no value
            texts.append(WindowText(value, VALUE_COLUMN, tile_row))
    return WindowLayout(window=OPTIONS_WINDOW, title=WindowText(shown.title, TITLE_COLUMN, 0), texts=tuple(texts),
                        cursor_tiles=tuple((CURSOR_COLUMN, FIRST_ROW + 2 * number) for number in range(len(lines))))


def overlay_texts() -> list[str]:
    """Every text the window can show, for the translation catalog (catalog_tools.dynamic_messages)."""
    return ([page.title for page in OPTION_PAGES] + [PRESET_LABEL, *PRESET_LABELS.values(), PAGE_LABEL] +
            [text for page in OPTION_PAGES for row in page.rows for text in (row.label, *row.value_labels)])


def darken(screen: Surface) -> None:
    """Lay the translucent black overlay over the whole screen."""
    shade = Surface(screen.get_size(), SRCALPHA)
    shade.fill((*BLACK, OVERLAY_ALPHA))
    screen.blit(shade, (0, 0))


class OptionsOverlay:
    """The overlay over the map, run until it's closed (see the module docstring)."""

    def __init__(self, game, pages: Sequence[OptionPage] = OPTION_PAGES):
        self.game = game
        self.pages = tuple(pages)
        self.config: dict = game.game_state.config
        self._: Callable[[str], str] = set_gettext_language(self.config.get('LANGUAGE'))
        self.page = 0
        self.index = 0
        # The last CUSTOM set of values, which PRESET goes back to (None until there has been one)
        self.custom: dict[str, Any] | None = None
        self.remember_custom()

    @property
    def rows(self) -> tuple[OptionRow | ScreenRow, ...]:
        """The rows of the page shown."""
        return self.pages[self.page].rows

    @property
    def row_count(self) -> int:
        return FIXED_ROWS + len(self.rows)

    def remember_custom(self) -> None:
        if current_preset(self.config) == PRESET_CUSTOM:
            self.custom = preset_settings(self.config)

    def run(self) -> None:
        """Show the overlay, read the buttons once a frame until it's closed, then put the map frame back."""
        screen = full_screen(self.game.screen)  # the whole picture in the WIDE view (src/view.py)
        background = screen.copy()
        cursor = BlinkingCursor()
        drawn: tuple | None = None
        while True:
            visible = cursor.visible()
            shown = (self.page, self.index, visible, tuple(self.config.get(row.config_key) for row in OPTION_ROWS))
            if shown != drawn:
                self.draw(background, self.index, visible)
                drawn = shown
            next_frame()
            for current_event in frame_events():
                if current_event.type != KEYDOWN:
                    continue
                key = current_event.key
                if key in CLOSE_KEYS:
                    self.close(background)
                    return
                if key in UP_KEYS or key in DOWN_KEYS:
                    moved_to = max(0, min(self.row_count - 1, self.index + (-1 if key in UP_KEYS else 1)))
                    if moved_to != self.index:
                        self.index = moved_to
                        cursor.restart()  # WndUpdateCrsrPos: the arrow shows at once on its new row
                elif key in NEXT_PAGE_KEYS or key in PREVIOUS_PAGE_KEYS:
                    self.turn_page(-1 if key in PREVIOUS_PAGE_KEYS else 1)
                    self.play_sound()
                elif isinstance(row := self.shown_row(), ScreenRow):
                    if key in A_BUTTON_KEYS:
                        self.play_sound()
                        self.open_screen(row)
                        drawn = None  # the screen covered the window: draw it again
                elif key in LEFT_KEYS or key in RIGHT_KEYS or key in A_BUTTON_KEYS:
                    self.change(-1 if key in LEFT_KEYS else 1)
                    self.play_sound()

    def shown_row(self) -> OptionRow | ScreenRow | None:
        """The page's own row the cursor is on (None on PRESET and PAGE)."""
        return self.rows[self.index - FIXED_ROWS] if self.index >= FIXED_ROWS else None

    def play_sound(self) -> None:
        self.game.sound.play_sound(self.game.directories.menu_button_sfx)

    def turn_page(self, step: int) -> None:
        self.page = (self.page + step) % len(self.pages)
        self.index = min(self.index, self.row_count - 1)

    def change(self, step: int) -> None:
        """Left, right or A on the cursor's row."""
        if self.index == PRESET_ROW:
            self.change_preset(step)
        elif self.index == PAGE_ROW:
            self.turn_page(step)
        else:
            row = self.rows[self.index - FIXED_ROWS]
            assert isinstance(row, OptionRow)
            row.change(self.config, step)
            apply_option(self.game, row.config_key)
            # The window's own text in the language just chosen
            self._ = set_gettext_language(self.config.get('LANGUAGE'))
            self.remember_custom()

    def change_preset(self, step: int) -> None:
        """The next or previous of NES, MODERN and the last CUSTOM values, setting every preset row at once."""
        choices = [PRESET_NES, PRESET_MODERN] + ([PRESET_CUSTOM] if self.custom is not None else [])
        current = current_preset(self.config)
        place = choices.index(current) if current in choices else len(choices) - 1
        chosen = choices[(place + step) % len(choices)]
        values = self.custom if chosen == PRESET_CUSTOM and self.custom is not None else preset_values(chosen)
        for key, value in values.items():
            if self.config.get(key) != value:
                self.config[key] = value
                apply_option(self.game, key)

    def open_screen(self, row: ScreenRow) -> None:
        """Run the screen the row opens (CONTROLS: src/controls_screen.py) until it's closed."""
        ControlsScreen(self.game).run()

    def draw(self, background: Surface, index: int, cursor_visible: bool) -> None:
        """The map frame the overlay opened over, darkened, then the window."""
        if self.config.get('NO_BLIT'):
            return
        screen = self.game.screen
        whole = full_screen(screen)
        whole.blit(background, (0, 0))
        darken(whole)
        draw_translated_window(screen, options_layout(self.config, self.page), self.game.color, self.config, self._,
                               cursor_index=index, cursor_visible=cursor_visible)
        display.update(Rect(0, 0, whole.get_width(), whole.get_height()))

    def close(self, background: Surface) -> None:
        """Put the map frame back as it was when the overlay opened."""
        if self.config.get('NO_BLIT'):
            return
        screen = full_screen(self.game.screen)
        screen.blit(background, (0, 0))
        display.update(Rect(0, 0, screen.get_width(), screen.get_height()))
