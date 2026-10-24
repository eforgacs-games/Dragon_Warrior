"""The options overlay: this game's own settings, changed during play. Not on the NES.

SELECT (U) or Tab on the map opens it (Game.handle_select_button), when START would pause the game: no window open,
and only once the hero and the NPCs have finished their steps (MovementController.resolve_pending_freezes). The map
frame stays on screen, darkened by a translucent black overlay, with one NES-style window over it (src/windows.py,
drawn by src/translated_window.py).

Every convenience this game adds to the NES can be switched on or off on its own, with the NES behaviour as one of its
values (#409). The rows are grouped in pages, one page at a time in the window, titled with the page's name:

    LOOK & SOUND
    MESSAGE SPEED  FAST / NORMAL / SLOW     (TEXT_SPEED, src/dialog_box.py; the NES's own setting)
    DIALOG STYLE   CLASSIC (NES) / MODERN   (DIALOG_STYLE, src/dialog_box.py)
    FADE STYLE     NES / SMOOTH             (FADE_STYLE, src/visual_effects.py screen_fade)
    MUSIC          ORCHESTRA / NES          (ORCHESTRA_MUSIC_ENABLED, src/directories.py music_paths)
    LANGUAGE       ENGLISH / 한국어          (LANGUAGE: a global setting, src/settings.py)
    SCANLINES      OFF / ON                 (SCANLINES: a display filter, src/display_filters.py; global)
    SCALING        SMOOTH / PIXEL PERFECT   (SCALING: pygame's SCALED, or whole multiples of 256x240 only; global)
    STATUS WINDOW  NES / ALWAYS             (STATUS_WINDOW: the pop-up window, Drawer.status_window_always)
    SHOP PREVIEW   OFF (NES) / ON           (SHOP_PREVIEW: the shops' stat preview, src/shop_preview.py)

    GAMEPLAY
    NPCS MAKE WAY  ON / OFF (NES)           (NPCS_MAKE_WAY, MovementController.ask_npc_to_make_way)
    STAIRS         STEP ON / NES            (AUTO_STAIRS, MapManager.handle_warps)
    QUICK ACTION   OFF (NES) / ON           (QUICK_ACTION: Enter takes, opens or talks, Game.handle_enter_key)
    ENCOUNTERS     NES / HALF / OFF         (ENCOUNTERS: the random fights, Game.thin_encounters)
    EXP/GOLD       x1 (NES) / x2 / x4       (EXP_GOLD: what a won fight gives, Battle.enemy_defeated)

    CONTROLS
    GAME SPEED     OFF (NES) / ON           (GAME_SPEED_KEYS: keys 1 to 5, src/waiting.py)
    SAVE STATES    OFF (NES) / ON           (SAVE_STATES: F1-F3, Shift+F1-F3)
    REWIND         OFF (NES) / ON           (REWIND: Backspace)
    AUTO-GRIND     OFF (NES) / ON           (AUTO_GRIND: G, src/auto_grind.py)
    GRIND STOP     RED HP / HALF HP / 3/4 HP  (AUTO_GRIND_STOP: when auto-grind stops)
    MENU SPEED     NORMAL / FOLLOW GAME     (MENU_SPEED: the selection windows at 1x, or at the game speed,
                                             src/waiting.py menu_ticks)
    CHEATS         OFF (NES) / ON           (CHEAT_KEYS: F4 auto-battle, F9 invulnerability)
    RUN BUTTON     OFF (NES) / ON           (RUN_BUTTON: hold B to walk twice as fast, src/movement.py)

Above every page's rows are two more:

    PRESET         NES / MODERN / CUSTOM
    PAGE           1/3

PRESET sets every row that belongs to a preset at once (OptionRow.presets): NES to the NES behaviour, MODERN to the
recommended conveniences. It reads NES or MODERN while every such row has that preset's value, and CUSTOM as soon as one
differs from both. Choosing it goes round NES, MODERN and, once there has been one, the last CUSTOM set of values, so a
custom set is never lost by trying a preset. The message speed (the NES's own setting, chosen on the title menu too)
isn't part of either.

PAGE (or START, Page Up and Page Down from any row) shows the next or the previous page; the cursor stays where it is,
or goes to the new page's last row if it has fewer.

Up and down move the NES cursor (src/cursor.py) between the rows, stopping at the first and last; left, right or A
change the row's value, with the menu button sound. A change goes into the game config at once, so the next dialog,
fade, bump, step or key press uses it (Game.apply_option does what can't wait for that: the music, the game speed and
the cheats), and is saved with the adventure log the next time the game is saved (options_from_config). LANGUAGE,
SCANLINES and SCALING are the player's, not the adventure's, kept in the global settings file: Game.apply_option
switches the game to the new language at once (Game.set_language), this window included, and the display filters from
the next frame on. B, Esc, SELECT or Tab close it, and the map frame is put back
exactly as it was. Everything is on the NES buttons, so a gamepad works it as the keyboard does.

The overlay runs its own loop, so nothing else runs while it's open: the map, the NPCs, the timers and the pop-up
window wait, as they do for a dialog.
"""
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from pygame import K_PAGEDOWN, K_PAGEUP, K_TAB, KEYDOWN, SRCALPHA, Rect, Surface, display

from src.color import BLACK
from src.common import A_BUTTON_KEYS, B_BUTTON_KEYS, DOWN_KEYS, LEFT_KEYS, RIGHT_KEYS, SELECT_BUTTON_KEYS, \
    START_BUTTON_KEYS, UP_KEYS, set_gettext_language
from src.cursor import BlinkingCursor
from src.display_filters import SCALING_KEY, SCALING_MODES, SCANLINES_KEY
from src.options_screen import AUTO_GRIND_STOP_VALUES, CLASSIC, ENCOUNTER_SETTINGS, ENCOUNTERS_NES, \
    EXP_GOLD_MULTIPLIERS, MESSAGE_SPEED_LABELS, MESSAGE_SPEED_NAMES, MODERN, STATUS_WINDOW_ALWAYS, \
    STATUS_WINDOW_NES, STATUS_WINDOW_SETTINGS
from src.selection import frame_events, next_frame
from src.settings import LANGUAGES
from src.translated_window import draw_translated_window
from src.visual_effects import FADE_STYLE_NES, FADE_STYLE_SMOOTH
from src.waiting import MENU_SPEED_FOLLOW, MENU_SPEED_NORMAL
from src.windows import Window, WindowLayout, WindowText

# The keys that open the overlay on the map, and close it again
OPTIONS_KEYS = SELECT_BUTTON_KEYS + (K_TAB,)
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

ON_OFF = (False, True)
ON_OFF_LABELS = ("OFF (NES)", "ON")


@dataclass(frozen=True, slots=True)
class OptionRow:
    """One row: its label, the config key it sets, and its values with their labels, in the order they're cycled.
    ``presets`` is its (NES, MODERN) values, or None for a row the presets leave alone."""
    label: str
    config_key: str
    values: tuple[Any, ...]
    value_labels: tuple[str, ...]
    presets: tuple[Any, Any] | None = None

    def index(self, config: dict) -> int:
        """The current value's place in values (the first value if the config holds something else)."""
        value = config.get(self.config_key)
        return self.values.index(value) if value in self.values else 0

    def value_label(self, config: dict) -> str:
        return self.value_labels[self.index(config)]

    def change(self, config: dict, step: int) -> None:
        """Set the next (step 1) or the previous (step -1) value, going round."""
        config[self.config_key] = self.values[(self.index(config) + step) % len(self.values)]


def switch_row(label: str, config_key: str, modern: bool = True) -> OptionRow:
    """An OFF (NES) / ON row for a convenience, off in the NES preset."""
    return OptionRow(label, config_key, ON_OFF, ON_OFF_LABELS, (False, modern))


@dataclass(frozen=True, slots=True)
class OptionPage:
    title: str
    rows: tuple[OptionRow, ...]


OPTION_PAGES = (
    OptionPage("LOOK & SOUND", (
        OptionRow("MESSAGE SPEED", 'TEXT_SPEED', MESSAGE_SPEED_NAMES, MESSAGE_SPEED_LABELS),
        # The MODERN dialog style is how this game drew dialog before it matched the NES, not a convenience
        OptionRow("DIALOG STYLE", 'DIALOG_STYLE', (CLASSIC, MODERN), ("CLASSIC (NES)", "MODERN"), (CLASSIC, CLASSIC)),
        OptionRow("FADE STYLE", 'FADE_STYLE', (FADE_STYLE_NES, FADE_STYLE_SMOOTH), ("NES", "SMOOTH"),
                  (FADE_STYLE_NES, FADE_STYLE_NES)),
        OptionRow("MUSIC", 'ORCHESTRA_MUSIC_ENABLED', (True, False), ("ORCHESTRA", "NES"), (False, True)),
        # The player's, not the adventure's: kept in the global settings (src/settings.py), and no preset's. Each
        # language's name is in that language, so it can be found whichever is on.
        OptionRow("LANGUAGE", 'LANGUAGE', LANGUAGES, ("ENGLISH", "한국어")),
        # The display filters (src/display_filters.py): the player's screen, kept in the global settings too. Neither
        # is on the NES or off it (the NES drew to a TV), so no preset changes them.
        OptionRow("SCANLINES", SCANLINES_KEY, (False, True), ("OFF", "ON")),
        OptionRow("SCALING", SCALING_KEY, SCALING_MODES, ("SMOOTH", "PIXEL PERFECT")),
        OptionRow("STATUS WINDOW", 'STATUS_WINDOW', STATUS_WINDOW_SETTINGS, ("NES", "ALWAYS"),
                  (STATUS_WINDOW_NES, STATUS_WINDOW_ALWAYS)),
        # Information only (src/shop_preview.py): on by default, off in the NES preset
        switch_row("SHOP PREVIEW", 'SHOP_PREVIEW'),
    )),
    OptionPage("GAMEPLAY", (
        OptionRow("NPCS MAKE WAY", 'NPCS_MAKE_WAY', (True, False), ("ON", "OFF (NES)"), (False, True)),
        OptionRow("STAIRS", 'AUTO_STAIRS', (True, False), ("STEP ON", "NES"), (False, True)),
        switch_row("QUICK ACTION", 'QUICK_ACTION'),
        # How many fights, and what they give, are the game's balance, not conveniences: NES in both presets
        OptionRow("ENCOUNTERS", 'ENCOUNTERS', ENCOUNTER_SETTINGS, ("NES", "HALF", "OFF"), (ENCOUNTERS_NES, ENCOUNTERS_NES)),
        OptionRow("EXP/GOLD", 'EXP_GOLD', EXP_GOLD_MULTIPLIERS, ("x1 (NES)", "x2", "x4"), (1, 1)),
    )),
    OptionPage("CONTROLS", (
        switch_row("GAME SPEED", 'GAME_SPEED_KEYS'),
        switch_row("SAVE STATES", 'SAVE_STATES'),
        switch_row("REWIND", 'REWIND'),
        switch_row("AUTO-GRIND", 'AUTO_GRIND'),
        OptionRow("GRIND STOP", 'AUTO_GRIND_STOP', AUTO_GRIND_STOP_VALUES, ("RED HP", "HALF HP", "3/4 HP"),
                  (AUTO_GRIND_STOP_VALUES[0], AUTO_GRIND_STOP_VALUES[0])),
        # On the NES there is only 1x, so NORMAL is as faithful as FOLLOW GAME; both presets keep the menus at NORMAL
        OptionRow("MENU SPEED", 'MENU_SPEED', (MENU_SPEED_NORMAL, MENU_SPEED_FOLLOW), ("NORMAL", "FOLLOW GAME"),
                  (MENU_SPEED_NORMAL, MENU_SPEED_NORMAL)),
        # F4 and F9 are cheats, not conveniences: off in both presets
        switch_row("CHEATS", 'CHEAT_KEYS', modern=False),
        switch_row("RUN BUTTON", 'RUN_BUTTON'),
    )),
)
OPTION_ROWS = tuple(row for page in OPTION_PAGES for row in page.rows)
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
        texts += [WindowText(label, LABEL_COLUMN, tile_row), WindowText(value, VALUE_COLUMN, tile_row)]
    return WindowLayout(window=OPTIONS_WINDOW, title=WindowText(shown.title, TITLE_COLUMN, 0), texts=tuple(texts),
                        cursor_tiles=tuple((CURSOR_COLUMN, FIRST_ROW + 2 * number) for number in range(len(lines))))


def overlay_texts() -> list[str]:
    """Every text the window can show, for the translation catalog (catalog_tools.dynamic_messages)."""
    return ([page.title for page in OPTION_PAGES] + [PRESET_LABEL, *PRESET_LABELS.values(), PAGE_LABEL] +
            [text for row in OPTION_ROWS for text in (row.label, *row.value_labels)])


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
    def rows(self) -> tuple[OptionRow, ...]:
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
        screen = self.game.screen
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
                elif key in LEFT_KEYS or key in RIGHT_KEYS or key in A_BUTTON_KEYS:
                    self.change(-1 if key in LEFT_KEYS else 1)
                    self.play_sound()

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
            row.change(self.config, step)
            self.game.apply_option(row.config_key)
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
                self.game.apply_option(key)

    def draw(self, background: Surface, index: int, cursor_visible: bool) -> None:
        """The map frame the overlay opened over, darkened, then the window."""
        if self.config.get('NO_BLIT'):
            return
        screen = self.game.screen
        screen.blit(background, (0, 0))
        darken(screen)
        draw_translated_window(screen, options_layout(self.config, self.page), self.game.color, self.config, self._,
                               cursor_index=index, cursor_visible=cursor_visible)
        display.update(Rect(0, 0, screen.get_width(), screen.get_height()))

    def close(self, background: Surface) -> None:
        """Put the map frame back as it was when the overlay opened."""
        if self.config.get('NO_BLIT'):
            return
        screen = self.game.screen
        screen.blit(background, (0, 0))
        display.update(Rect(0, 0, screen.get_width(), screen.get_height()))
