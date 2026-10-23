"""The options overlay: this game's own settings, changed during play. Not on the NES.

SELECT (U) or Tab on the map opens it (Game.handle_select_button), when START would pause the game: no window open,
and only once the hero and the NPCs have finished their steps (MovementController.resolve_pending_freezes). The map
frame stays on screen, darkened by a translucent black overlay, with one NES-style window over it (src/windows.py,
drawn by src/translated_window.py), titled OPTIONS, with one row per setting and its current value:

    MESSAGE SPEED  FAST / NORMAL / SLOW     (TEXT_SPEED, src/dialog_box.py; the NES's own setting)
    DIALOG STYLE   CLASSIC (NES) / MODERN   (DIALOG_STYLE, src/dialog_box.py)
    NPCS MAKE WAY  ON / OFF (NES)           (NPCS_MAKE_WAY, MovementController.ask_npc_to_make_way)
    FADE STYLE     NES / SMOOTH             (FADE_STYLE, src/visual_effects.py screen_fade)
    STAIRS         STEP ON / NES            (AUTO_STAIRS, MapManager.handle_warps)
    GRIND STOP     RED HP / HALF HP / 3/4 HP  (AUTO_GRIND_STOP: when auto-grind stops, src/auto_grind.py)

Up and down move the NES cursor (src/cursor.py) between the rows; left, right or A change the row's value, with the
menu button sound. A change goes into the game config at once, so the next dialog, fade, bump or step uses it, and
is saved with the adventure log the next time the game is saved (options_from_config). B, Esc, SELECT or Tab close
it, and the map frame is put back exactly as it was.

The overlay runs its own loop, so nothing else runs while it's open: the map, the NPCs, the timers and the pop-up
window wait, as they do for a dialog. The message speed is the NES's own setting, chosen on the title menu as well
(src/options_screen.py): it is here too, so it can be changed without going back there.
"""
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from pygame import K_TAB, KEYDOWN, SRCALPHA, Rect, Surface, display

from src.color import BLACK
from src.common import A_BUTTON_KEYS, B_BUTTON_KEYS, DOWN_KEYS, LEFT_KEYS, RIGHT_KEYS, SELECT_BUTTON_KEYS, UP_KEYS, \
    set_gettext_language
from src.cursor import BlinkingCursor
from src.options_screen import AUTO_GRIND_STOP_VALUES, CLASSIC, MESSAGE_SPEED_LABELS, MESSAGE_SPEED_NAMES, MODERN
from src.selection import frame_events, next_frame
from src.translated_window import draw_translated_window
from src.visual_effects import FADE_STYLE_NES, FADE_STYLE_SMOOTH
from src.windows import Window, WindowLayout, WindowText

# The keys that open the overlay on the map, and close it again
OPTIONS_KEYS = SELECT_BUTTON_KEYS + (K_TAB,)
CLOSE_KEYS = B_BUTTON_KEYS + OPTIONS_KEYS

# How dark the map gets behind the window (0 is clear, 255 black)
OVERLAY_ALPHA = 160


@dataclass(frozen=True, slots=True)
class OptionRow:
    """One row: its label, the config key it sets, and its values with their labels, in the order they're cycled."""
    label: str
    config_key: str
    values: tuple[Any, ...]
    value_labels: tuple[str, ...]

    def index(self, config: dict) -> int:
        """The current value's place in values (the first value if the config holds something else)."""
        value = config.get(self.config_key)
        return self.values.index(value) if value in self.values else 0

    def value_label(self, config: dict) -> str:
        return self.value_labels[self.index(config)]

    def change(self, config: dict, step: int) -> None:
        """Set the next (step 1) or the previous (step -1) value, going round."""
        config[self.config_key] = self.values[(self.index(config) + step) % len(self.values)]


OPTION_ROWS = (
    OptionRow("MESSAGE SPEED", 'TEXT_SPEED', MESSAGE_SPEED_NAMES, MESSAGE_SPEED_LABELS),
    OptionRow("DIALOG STYLE", 'DIALOG_STYLE', (CLASSIC, MODERN), ("CLASSIC (NES)", "MODERN")),
    OptionRow("NPCS MAKE WAY", 'NPCS_MAKE_WAY', (True, False), ("ON", "OFF (NES)")),
    OptionRow("FADE STYLE", 'FADE_STYLE', (FADE_STYLE_NES, FADE_STYLE_SMOOTH), ("NES", "SMOOTH")),
    OptionRow("STAIRS", 'AUTO_STAIRS', (True, False), ("STEP ON", "NES")),
    OptionRow("GRIND STOP", 'AUTO_GRIND_STOP', AUTO_GRIND_STOP_VALUES, ("RED HP", "HALF HP", "3/4 HP")),
)

# The window: the screen's full 16 blocks wide (the longest labels and value, MESSAGE SPEED, NPCS MAKE WAY and
# CLASSIC (NES), are 13 tiles each), one block high per row plus a block of border at the top and bottom, from block
# row 2. Laid out like the NES selection windows: the title in the top border after the corner and 3 border tiles (as
# COMMAND), the rows double spaced from tile row 2, the cursor in tile column 1 and the label after it; the value
# starts in tile column 17.
OPTIONS_WINDOW = Window(0, 2, 16, len(OPTION_ROWS) + 2)
OPTIONS_TITLE = WindowText("OPTIONS", 4, 0)
FIRST_ROW = 2
CURSOR_COLUMN = 1
LABEL_COLUMN = 2
VALUE_COLUMN = 17


def options_layout(config: dict) -> WindowLayout:
    """The window with each row's label and current value."""
    texts: list[WindowText] = []
    for number, row in enumerate(OPTION_ROWS):
        tile_row = FIRST_ROW + 2 * number
        texts += [WindowText(row.label, LABEL_COLUMN, tile_row), WindowText(row.value_label(config), VALUE_COLUMN,
                                                                            tile_row)]
    return WindowLayout(window=OPTIONS_WINDOW, title=OPTIONS_TITLE, texts=tuple(texts),
                        cursor_tiles=tuple((CURSOR_COLUMN, FIRST_ROW + 2 * number) for number in range(len(OPTION_ROWS))))


def overlay_texts() -> list[str]:
    """Every text the window can show, for the translation catalog (catalog_tools.dynamic_messages)."""
    return [OPTIONS_TITLE.text] + [text for row in OPTION_ROWS for text in (row.label, *row.value_labels)]


def darken(screen: Surface) -> None:
    """Lay the translucent black overlay over the whole screen."""
    shade = Surface(screen.get_size(), SRCALPHA)
    shade.fill((*BLACK, OVERLAY_ALPHA))
    screen.blit(shade, (0, 0))


class OptionsOverlay:
    """The overlay over the map, run until it's closed (see the module docstring)."""

    def __init__(self, game, rows: Sequence[OptionRow] = OPTION_ROWS):
        self.game = game
        self.rows = tuple(rows)
        self.config: dict = game.game_state.config
        self._: Callable[[str], str] = set_gettext_language(self.config.get('LANGUAGE'))

    def run(self) -> None:
        """Show the overlay, read the buttons once a frame until it's closed, then put the map frame back."""
        screen = self.game.screen
        background = screen.copy()
        cursor = BlinkingCursor()
        index = 0
        drawn: tuple | None = None
        while True:
            visible = cursor.visible()
            shown = (index, visible, tuple(row.index(self.config) for row in self.rows))
            if shown != drawn:
                self.draw(background, index, visible)
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
                    moved_to = max(0, min(len(self.rows) - 1, index + (-1 if key in UP_KEYS else 1)))
                    if moved_to != index:
                        index = moved_to
                        cursor.restart()  # WndUpdateCrsrPos: the arrow shows at once on its new row
                elif key in LEFT_KEYS or key in RIGHT_KEYS or key in A_BUTTON_KEYS:
                    self.rows[index].change(self.config, -1 if key in LEFT_KEYS else 1)
                    self.game.sound.play_sound(self.game.directories.menu_button_sfx)

    def draw(self, background: Surface, index: int, cursor_visible: bool) -> None:
        """The map frame the overlay opened over, darkened, then the window."""
        if self.config.get('NO_BLIT'):
            return
        screen = self.game.screen
        screen.blit(background, (0, 0))
        darken(screen)
        draw_translated_window(screen, options_layout(self.config), self.game.color, self.config, self._,
                               cursor_index=index, cursor_visible=cursor_visible)
        display.update(Rect(0, 0, screen.get_width(), screen.get_height()))

    def close(self, background: Surface) -> None:
        """Put the map frame back as it was when the overlay opened."""
        if self.config.get('NO_BLIT'):
            return
        screen = self.game.screen
        screen.blit(background, (0, 0))
        display.update(Rect(0, 0, screen.get_width(), screen.get_height()))
