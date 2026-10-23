from typing import Callable, List

from pygame import Rect, image, display
from pygame.transform import scale

from src.calculation import Calculation
from src.common import BLACK, Graphics
from src.cursor import IN_A, IN_B, BlinkingCursor
from src.directories import Directories
from src.selection import run_selection, stop_at_edges
from src.sound import Sound


def blit_scaled_image(image_path: str, screen, graphics=None, overlay: Callable | None = None):
    """Blit a scaled image to the screen. Uses cache if graphics object provided.

    overlay, if given, draws on top of the image (e.g. the hero's name on an adventure log screenshot) before the
    display is updated."""
    if graphics:
        # Use cached scaled image
        scaled_image = graphics.get_scaled_image(image_path, (screen.get_width(), screen.get_height()))
    else:
        # Fallback to direct loading (not cached)
        scaled_image = scale(image.load(image_path), (screen.get_width(), screen.get_height()))
    screen.blit(scaled_image, (0, 0))
    if overlay is not None:
        overlay(screen)
    display.update(scaled_image.get_rect())


# What main_menu_selection returns for B when B goes back (WND_ABORT)
MENU_BACK = -1


class GameFunctions:
    def __init__(self, config):
        self.config = config
        self.calculation = Calculation(config)
        self.sound = Sound(config)
        self.directories = Directories(config)
        self.graphics = Graphics(config)  # Add graphics for caching

    def main_menu_selection(self, blink_start: int, screen, unselected_image: str, selected_image: str,
                            other_selected_images: List[str] | None = None, no_blit: bool = False,
                            overlay: Callable | None = None, b_goes_back: bool = False) -> int:
        """A title screen menu (ContChngErsDat, the adventure log lists...), drawn from screenshots: each selected
        image is the window with the NES arrow at that entry, unselected_image the window without one. The arrow
        blinks like every NES window cursor (src/cursor.py), starting visible at blink_start and again whenever it
        moves, and stays on once an entry is chosen.

        B does nothing in the title menu itself (the NES loops on it). With b_goes_back (a log window, where B is
        WND_ABORT), B returns MENU_BACK instead."""
        all_selected_images = [selected_image] + (other_selected_images or [])

        def draw(index: int, cursor_visible: bool) -> None:
            screen.fill(BLACK)
            self.draw_menu_frame(all_selected_images[index], unselected_image, cursor_visible, screen, no_blit,
                                 overlay)

        # The cursor stops at the first and last entries. A chooses: its arrow is drawn once more and stays on
        # (WndAPressed). B makes the menu sound either way, and only ends the selection with b_goes_back.
        answer = run_selection(draw, 0, move=stop_at_edges(len(all_selected_images)),
                               answers=(IN_A, IN_B) if b_goes_back else (IN_A,), hold=(IN_A,),
                               sound=lambda: self.sound.play_sound(self.directories.menu_button_sfx),
                               cursor=BlinkingCursor(blink_start))  # WndInitSelect
        return answer.entry if answer.accepted else MENU_BACK

    def draw_menu_frame(self, selected_image: str, unselected_image: str, cursor_visible: bool, screen,
                        no_blit: bool, overlay: Callable | None = None) -> None:
        """One frame of a screenshot menu: the image with the arrow while the cursor is visible, the one without it
        while it isn't (UpdateCursorGFX)."""
        if no_blit:
            return
        blit_scaled_image(selected_image if cursor_visible else unselected_image, screen, self.graphics, overlay)


def set_character_position(character, tile_size: int):
    character.column, character.row = character.rect.x // tile_size, character.rect.y // tile_size


def get_surrounding_rect(character, tile_size: int) -> Rect:
    """The character's rect, grown by a block on every side. While a character steps, this covers where its sprite
    was drawn on the frame before. (It used to be 2.04 blocks square from a block up and left, which, as Rect drops
    the fraction, didn't reach below or right of the sprite at SCALE 1: the hero walking up or left left the bottom
    or right edge of his last frame behind.)"""
    return character.rect.inflate(tile_size * 2, tile_size * 2)
