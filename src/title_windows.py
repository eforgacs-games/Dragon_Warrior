"""The title menu's windows (Bank03 StartMenu, ShowOpenLogs and ShowUsedLogs), generated from the NES window data
(src/windows.py) instead of from screenshots, and translated like every generated window (src/translated_window.py).

The title menu is one of three windows, by how many adventure logs are used: NewQuestDat (none), FullMenuDat (some)
or ContChngErsDat (all three). BEGIN A NEW QUEST opens the open logs window over it (LogList??Dat1), and CONTINUE A
QUEST the used logs window (LogList??Dat2), with the title menu's arrow held on its entry behind them.
"""
import re
from collections.abc import Sequence

from pygame import Surface

from src.color import WHITE
from src.translated_window import Translate, draw_translated_window
from src.windows import CONTINUE_CHANGE_ERASE_LAYOUT, FULL_MENU_LAYOUT, NEW_QUEST_LAYOUT, WindowLayout, \
    with_autosave_entry

# An adventure log window's line (src/windows.py ADVENTURE_LOG_LINE, USED_ADVENTURE_LOG_LINE): the log's number, the
# ":" of a used log and the hero's name after it
LOG_LINE = re.compile(r'ADVENTURE LOG (\d)(:?)(.*)', re.DOTALL)

# A window on the title screen, with the entry its cursor is on (None for no cursor) and whether the cursor is in the
# "on" half of its blink
TitleWindow = tuple[WindowLayout, int | None, bool]


def title_menu_layout(used_logs: int, autosave: bool = False) -> WindowLayout:
    """The title menu with this many adventure logs used (PreNoSaves, PreUnusedSaves, PreSavesUsed), with CONTINUE
    AUTOSAVE added at the bottom when there's an autosave (not NES, src/autosave.py)."""
    if used_logs == 0:
        layout = NEW_QUEST_LAYOUT
    else:
        layout = CONTINUE_CHANGE_ERASE_LAYOUT if used_logs >= 3 else FULL_MENU_LAYOUT
    return with_autosave_entry(layout) if autosave else layout


def title_translate(_: Translate) -> Translate:
    """``_`` for the title screen's windows: an adventure log line is translated as its catalog line, with the log's
    number and the hero's name (never translated) put back in; anything else is translated as it is."""
    def translate(text: str) -> str:
        match = LOG_LINE.fullmatch(text)
        if match is None:
            return _(text)
        number, colon, name = match.groups()
        line = _("ADVENTURE LOG {}:") if colon else _("ADVENTURE LOG {}")
        return line.format(number) + name
    return translate


def draw_title_windows(screen: Surface, windows: Sequence[TitleWindow], config: dict, translate: Translate) -> None:
    """Draw the windows, bottom to top, in the title screen's white (the NES title screen palette)."""
    for layout, cursor_index, cursor_visible in windows:
        draw_translated_window(screen, layout, WHITE, config, translate, cursor_index=cursor_index,
                               cursor_visible=cursor_visible)
