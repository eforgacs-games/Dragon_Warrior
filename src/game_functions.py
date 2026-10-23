from typing import Callable, List

from pygame import K_DOWN, K_s, K_UP, K_w, KEYDOWN, event, Rect, image, display
from pygame.transform import scale

from src.calculation import Calculation
from src.common import BLACK, accept_keys, reject_keys, Graphics
from src.cursor import BlinkingCursor
from src.directories import Directories
from src.sound import Sound
from src.waiting import quit_if_requested


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
        # TODO: Merge with open_store_inventory() if possible
        current_item_index = 0
        all_selected_images = [selected_image] + (other_selected_images or [])
        cursor = BlinkingCursor(blink_start)  # WndInitSelect
        while True:
            screen.fill(BLACK)
            self.draw_menu_frame(all_selected_images[current_item_index], unselected_image, cursor.visible(), screen,
                                 no_blit, overlay)
            for current_event in event.get():
                quit_if_requested(current_event)
                if current_event.type == KEYDOWN:
                    if current_event.key in accept_keys:
                        # WndAPressed: the chosen entry's arrow is drawn once more and stays on
                        self.draw_menu_frame(all_selected_images[current_item_index], unselected_image, True,
                                             screen, no_blit, overlay)
                        self.sound.play_sound(self.directories.menu_button_sfx)
                        return current_item_index
                    elif current_event.key in reject_keys:
                        self.sound.play_sound(self.directories.menu_button_sfx)
                        if b_goes_back:
                            return MENU_BACK
                    elif current_event.key in (K_DOWN, K_s) and current_item_index < len(all_selected_images) - 1:
                        current_item_index += 1
                        cursor.restart()  # WndUpdateCrsrPos
                    elif current_event.key in (K_UP, K_w) and current_item_index > 0:
                        current_item_index -= 1
                        cursor.restart()

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
