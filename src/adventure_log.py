"""The hero's name on the "ADVENTURE LOG n:" line of the start menus, drawn over the NES screenshot.

The start menus are full-screen NES screenshots (see Game.show_main_menu_screen), so the name, which the screenshot
can't know, is drawn on top of it here at the NES tile position.

On the NES (Bank03 ShowUsedLogs) "continue a quest", "change message speed", "copy a quest" (the log to copy from)
and "erase a quest" all list the used logs in windows $19-$1F (Bank01 LogList1Dat2 ... LogList123Dat2). Each line
there is " ADVENTURE LOG n:" followed by control byte $B5/$B6/$B7, which WndShowName sends to WndLwr4Saved: the
first 4 letters of that log's name (WndPrepGetLwr reads DispName0-3). There is no level on these lines. Names are
up to 8 letters (WndMaxNameLength); WndEnterName fills the unused letters with blank tiles (TL_BLANK_TILE2), so a
shorter name is padded with blanks. A log with no saved game isn't listed at all: "begin a new quest" and the copy
target list the open logs instead (ShowOpenLogs, LogList1Dat1 ... LogList123Dat1), which show " ADVENTURE LOG n"
with no colon and no name. The level only appears in the erase confirmation window (EraseLogDat: the full 8-letter
name, then "LEVEL" and the level), which this game doesn't have a screenshot for.

The window data puts the first line at:
- window position $63 (X = 3 blocks, Y = 6 blocks; src.windows.ADVENTURE_LOG_WINDOW_2): top-left corner at NES tile
  column 6, row 12;
- the top border ($88) on row 12, a blank row, then the first line on row 14 (each line is a block, 2 tiles, tall);
- in the line, the left border on column 6, a blank (the cursor) on 7, "ADVENTURE LOG n" on columns 8-22, ":" on 23
  and the 4 name letters on 24-27, then a blank on 28 and the right border on 29 (24 tiles wide, $18).
"""
import json
import os
import re
from dataclasses import dataclass
from typing import List

from pygame import Surface
from pygame.font import Font

from src.color import WHITE
from src.directories import Directories
from src.text import blit_text_to_screen, set_font_by_ascii_chars
from src.windows import ADVENTURE_LOG_WINDOW_2

# WndLwr4Saved: 4 letters of the saved name.
LOG_NAME_LENGTH = 4
# NES tile row of the first line in LogList*Dat2 (ADVENTURE_LOG_WINDOW_2's top border, then a blank row); each further
# log is one block (2 tiles) lower.
FIRST_LOG_ROW = ADVENTURE_LOG_WINDOW_2.y * 2 + 2
LOG_ROW_SPACING = 2
# NES tile columns of the log's number (after the border, the cursor blank and "ADVENTURE LOG ") and of its name
# (after the ":"); see the module docstring.
LOG_NUMBER_COLUMN = ADVENTURE_LOG_WINDOW_2.x * 2 + 16
LOG_NAME_COLUMN = LOG_NUMBER_COLUMN + 2

SAVE_SLOT_PATTERN = re.compile(r'save_slot_(\d+)\.json$')
# The NES has three adventure logs (reference/sram-doc.txt), numbered 1 to 3 on screen
ADVENTURE_LOGS = (1, 2, 3)


def first_open_log(save_dir: str) -> int | None:
    """ShowOpenLogs: the lowest adventure log with no save in save_dir, or None if all three are used."""
    for log in ADVENTURE_LOGS:
        if not os.path.exists(os.path.join(save_dir, f'save_slot_{log}.json')):
            return log
    return None


def logs_named(save_dir: str, name: str) -> List[int]:
    """The adventure logs in save_dir whose hero is called name (the save's 'Name', as Game.load_game reads it). A
    save that can't be read matches no name."""
    return [log for log in ADVENTURE_LOGS if read_save_name(os.path.join(save_dir, f'save_slot_{log}.json')) == name]


def log_name_tiles(name: str) -> str:
    """The 4 letters WndLwr4Saved shows: the start of the name, padded with blank tiles if it's shorter."""
    return name[:LOG_NAME_LENGTH].ljust(LOG_NAME_LENGTH)


def read_save_name(save_path: str) -> str | None:
    """The hero's name in a save file, or None if there is no readable save there."""
    try:
        with open(save_path) as save_file:
            name = json.load(save_file).get('Name')
    except (OSError, ValueError, AttributeError):
        return None
    return name if isinstance(name, str) else None


def save_slot_number(save_path: str) -> int | None:
    """The adventure log number of a save_slot_<n>.json file, or None for any other file."""
    match = SAVE_SLOT_PATTERN.search(os.path.basename(save_path))
    return int(match.group(1)) if match else None


@dataclass(frozen=True)
class OverlayText:
    """Text to draw starting at an NES tile (column, row) of the 32x30 tile screen."""
    text: str
    column: int
    row: int


def adventure_log_overlay_texts(save_path: str, line: int = 0, screenshot_log_number: int = 1) -> List[OverlayText]:
    """What to draw over a used-logs screenshot for the save at save_path, shown on the given line (0 = first).

    The screenshot already says "ADVENTURE LOG <screenshot_log_number>:"; if the save is a different log, its
    number is drawn over the screenshot's. Nothing is drawn if the save can't be read."""
    name = read_save_name(save_path)
    if name is None:
        return []
    row = FIRST_LOG_ROW + line * LOG_ROW_SPACING
    texts = []
    slot = save_slot_number(save_path)
    if slot is not None and slot != screenshot_log_number:
        texts.append(OverlayText(str(slot), LOG_NUMBER_COLUMN, row))
    texts.append(OverlayText(log_name_tiles(name), LOG_NAME_COLUMN, row))
    return texts


class AdventureLogOverlay:
    """Draws OverlayTexts onto the screen in the game's NES font, one NES tile per letter.

    The font is loaded once, since the menu blink loop redraws the screen every pass."""

    def __init__(self, texts: List[OverlayText], config: dict):
        self.texts = texts
        self.config = config
        # an NES 8x8 tile is half a 16x16 map tile
        self.tile_px = config['TILE_SIZE'] // 2
        self._font: Font | None = None

    def tile_position(self, column: int, row: int) -> tuple[float, float]:
        """Where blit_text_to_screen's 'left' alignment (midleft) has to be for the text to fill that tile: the
        tile's left edge, vertically centred on the tile. This lines the letters up pixel for pixel with the
        screenshot's own text."""
        return column * self.tile_px, (row + 0.5) * self.tile_px

    def __call__(self, screen: Surface) -> None:
        if not self.texts:
            return
        if self._font is None:
            self._font = set_font_by_ascii_chars([text.text for text in self.texts], self.tile_px, None,
                                                 Directories(self.config))
        for text in self.texts:
            x, y = self.tile_position(text.column, text.row)
            blit_text_to_screen('left', WHITE, self._font, screen, text.text, x, y,
                                self.config['RENDER_TEXT'])
