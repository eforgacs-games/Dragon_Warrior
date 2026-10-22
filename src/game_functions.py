from typing import Callable, Tuple, List

from pygame import K_DOWN, K_s, K_UP, K_w, KEYDOWN, event, Rect, image, display
from pygame.time import get_ticks
from pygame.transform import scale

from src.calculation import Calculation
from src.common import BLACK, accept_keys, reject_keys, Graphics
from src.direction import Direction
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


class GameFunctions:
    def __init__(self, config):
        self.config = config
        self.calculation = Calculation(config)
        self.sound = Sound(config)
        self.directories = Directories(config)
        self.graphics = Graphics(config)  # Add graphics for caching

    def main_menu_selection(self, blink_start: int, screen, unselected_image: str, selected_image: str,
                            other_selected_images: List[str] | None = None, no_blit: bool = False,
                            overlay: Callable | None = None) -> int:
        # TODO: Merge with open_store_inventory() if possible
        current_item_index = 0
        all_selected_images = [selected_image] + (other_selected_images or [])
        while True:
            screen.fill(BLACK)
            if self.calculation.convert_to_frames_since_start_time(blink_start) > 32:
                blink_start = get_ticks()
            self.alternate_blink(all_selected_images[current_item_index], unselected_image, blink_start, screen,
                                 no_blit, overlay)
            for current_event in event.get():
                quit_if_requested(current_event)
                if current_event.type == KEYDOWN:
                    if current_event.key in accept_keys:
                        self.sound.play_sound(self.directories.menu_button_sfx)
                        return current_item_index
                    elif current_event.key in reject_keys:
                        self.sound.play_sound(self.directories.menu_button_sfx)
                    elif current_event.key in (K_DOWN, K_s) and current_item_index < len(all_selected_images) - 1:
                        current_item_index += 1
                        blink_start = get_ticks()
                    elif current_event.key in (K_UP, K_w) and current_item_index > 0:
                        current_item_index -= 1
                        blink_start = get_ticks()

    def alternate_blink(self, image_1: str, image_2: str, right_arrow_start: int, screen, no_blit: bool,
                        overlay: Callable | None = None):
        if no_blit:
            return
        while self.calculation.convert_to_frames_since_start_time(right_arrow_start) <= 16:
            blit_scaled_image(image_1, screen, self.graphics, overlay)
        while 16 < self.calculation.convert_to_frames_since_start_time(right_arrow_start) <= 32:
            blit_scaled_image(image_2, screen, self.graphics, overlay)


def set_character_position(character, tile_size: int):
    character.column, character.row = character.rect.x // tile_size, character.rect.y // tile_size


def get_next_coordinates(character_column: int, character_row: int, direction: int,
                         offset_from_character: int = 1) -> Tuple[int, int] | None:
    match direction:
        case Direction.UP.value:
            return character_row - offset_from_character, character_column
        case Direction.DOWN.value:
            return character_row + offset_from_character, character_column
        case Direction.LEFT.value:
            return character_row, character_column - offset_from_character
        case Direction.RIGHT.value:
            return character_row, character_column + offset_from_character
    return None


def get_surrounding_rect(character, tile_size: int) -> Rect:
    """The character's rect, grown by a block on every side. While a character steps, this covers where its sprite
    was drawn on the frame before. (It used to be 2.04 blocks square from a block up and left, which, as Rect drops
    the fraction, didn't reach below or right of the sprite at SCALE 1: the hero walking up or left left the bottom
    or right edge of his last frame behind.)"""
    return character.rect.inflate(tile_size * 2, tile_size * 2)
