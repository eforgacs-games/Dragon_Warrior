from collections.abc import Sequence

from pygame import Rect, display

from src.calculation import Calculation
from src.common import BLACK, Graphics, set_gettext_language
from src.cursor import IN_A, IN_B, BlinkingCursor
from src.directories import Directories
from src.selection import run_selection, stop_at_edges
from src.sound import Sound
from src.title_windows import draw_title_windows, title_translate
from src.windows import WindowLayout

# What main_menu_selection returns for B when B goes back (WND_ABORT)
MENU_BACK = -1


class GameFunctions:
    def __init__(self, config):
        self.config = config
        self.calculation = Calculation(config)
        self.sound = Sound(config)
        self.directories = Directories(config)
        self.graphics = Graphics(config)  # Add graphics for caching

    def main_menu_selection(self, blink_start: int, screen, layout: WindowLayout,
                            below: Sequence[tuple[WindowLayout, int]] = (), b_goes_back: bool = False) -> int:
        """A title screen selection window (NewQuestDat, FullMenuDat, ContChngErsDat, an adventure log window), drawn
        from its window data (src/title_windows.py) over the windows below it, each with its arrow held on the entry
        chosen in it. The arrow blinks like every NES window cursor (src/cursor.py), starting visible at blink_start
        and again whenever it moves, and stays on once an entry is chosen.

        B does nothing in the title menu itself (the NES loops on it). With b_goes_back (a log window, where B is
        WND_ABORT), B returns MENU_BACK instead."""
        translate = title_translate(set_gettext_language(self.config.get('LANGUAGE')))

        def draw(index: int, cursor_visible: bool) -> None:
            if self.config.get('NO_BLIT'):
                return
            screen.fill(BLACK)
            draw_title_windows(screen, [(window, entry, True) for window, entry in below]
                               + [(layout, index, cursor_visible)], self.config, translate)
            display.update(Rect(0, 0, screen.get_width(), screen.get_height()))

        # The cursor stops at the first and last entries. A chooses: its arrow is drawn once more and stays on
        # (WndAPressed). B makes the menu sound either way, and only ends the selection with b_goes_back.
        answer = run_selection(draw, 0, move=stop_at_edges(len(layout.cursor_tiles)),
                               answers=(IN_A, IN_B) if b_goes_back else (IN_A,), hold=(IN_A,),
                               sound=lambda: self.sound.play_sound(self.directories.menu_button_sfx),
                               cursor=BlinkingCursor(blink_start))  # WndInitSelect
        return answer.entry if answer.accepted else MENU_BACK


def set_character_position(character, tile_size: int):
    character.column, character.row = character.rect.x // tile_size, character.rect.y // tile_size


def get_surrounding_rect(character, tile_size: int) -> Rect:
    """The character's rect, grown by a block on every side. While a character steps, this covers where its sprite
    was drawn on the frame before. (It used to be 2.04 blocks square from a block up and left, which, as Rect drops
    the fraction, didn't reach below or right of the sprite at SCALE 1: the hero walking up or left left the bottom
    or right edge of his last frame behind.)"""
    return character.rect.inflate(tile_size * 2, tile_size * 2)
