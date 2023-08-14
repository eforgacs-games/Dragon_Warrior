# Constants
import gettext
import ntpath
import os
from os.path import sep, exists

from pygame import Surface, image, transform, K_RETURN, K_i, K_k, K_ESCAPE, K_j, Rect, display

from src.color import WHITE, BLACK, RED
from src.direction import Direction
from src.directories import Directories
from src.text import draw_text


def find_file(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)


# Images

_image_library = {}


# Characters


def is_facing_down(character):
    return character.direction_value == Direction.DOWN.value


def is_facing_up(character):
    return character.direction_value == Direction.UP.value


def is_facing_right(character):
    return character.direction_value == Direction.RIGHT.value


def is_facing_left(character):
    return character.direction_value == Direction.LEFT.value


def is_facing_medially(character):
    return is_facing_up(character) or is_facing_down(character)


def is_facing_laterally(character):
    return is_facing_left(character) or is_facing_right(character)


# Maps


class Graphics:
    def __init__(self, config):
        self.config = config
        self.directories = Directories(config)

    def set_window_background(self, black_box, background_path, color):
        black_box.fill(BLACK)
        background_image = image.load(background_path)
        if color == RED:
            transform.threshold(background_image, background_image, WHITE, (1, 1, 1), RED, 1, None, True)
            # image_pixel_array = PixelArray(background_image)
            # image_pixel_array.replace(WHITE, RED)
        background_image = transform.scale(background_image, black_box.get_size())
        black_box.blit(background_image, black_box.get_rect()) if not self.config['NO_BLIT'] else None

    def create_window(self, x, y, width, height, window_background, screen, color) -> Surface:
        tile_size = self.config["TILE_SIZE"]
        window_box = Surface((tile_size * width, tile_size * height))  # lgtm [py/call/wrong-arguments]
        self.set_window_background(window_box, window_background, color=color)
        screen.blit(window_box, (tile_size * x, tile_size * y)) if not self.config['NO_BLIT'] else None
        return window_box

    def get_image(self, path):
        global _image_library
        image_to_load = _image_library.get(path)
        if image_to_load is None:
            canonicalized_path = path.replace('/', sep).replace('\\', sep)
            if exists(canonicalized_path):
                image_to_load = image.load(canonicalized_path).convert_alpha()
                _image_library[path] = image_to_load
            else:
                image_to_load = image.load(
                    find_file(ntpath.basename(canonicalized_path), self.directories.root_project_path)).convert_alpha()
                _image_library[path] = image_to_load
        return image_to_load

    def blink_switch(self, screen: Surface, image_1: str, image_2: str, x: int, y: int, width: int, height: int,
                     tile_size: int,
                     show_arrow: bool, color: tuple = WHITE) -> Rect:
        """Switches between two images, creating a blinking effect.
        :param screen: the screen to draw on
        :param image_1: the path of the first image to draw (usually the selection image)
        :param image_2: the path of the second image to draw (usually a blank image)
        :param x: the x coordinate of the window
        :param y: the y coordinate of the window
        :param width: the width of the window
        :param height: the height of the window
        :param tile_size: the size of the tiles
        :param show_arrow: whether to show the arrow
        :param color: the color of the window
        :return: the rect of the window
        """
        window_rect = Rect(x * tile_size, y * tile_size, width * tile_size, height * tile_size)
        if show_arrow:
            self.create_window(x, y, width, height, image_1, screen, color)
        else:
            self.create_window(x, y, width, height, image_2, screen, color)
        display.update(window_rect)
        return window_rect

    def blink_arrow(self, screen: Surface, x: float, y: float, direction: str, show_arrow, color: tuple = WHITE):
        if direction == 'up':
            arrow_character = '^'
        elif direction == "down":
            arrow_character = "▼"
        elif direction == "left":
            arrow_character = "<"
        elif direction == "right":
            arrow_character = ">"
        else:
            arrow_character = ""
        arrow_screen_portion = Rect(x, y, self.config["TILE_SIZE"], self.config["TILE_SIZE"])
        if show_arrow:
            draw_text(arrow_character, x, y, screen, self.config, color, letter_by_letter=False)
        else:
            draw_text(arrow_character, x, y, screen, self.config, BLACK, letter_by_letter=False)
        display.update(arrow_screen_portion)


accept_keys = (K_RETURN, K_i, K_k)
reject_keys = (K_ESCAPE, K_j)


def set_gettext_language(language):
    if language == 'Korean':
        ko = gettext.translation('base', localedir=os.path.join('../data/text/locales'), languages=['ko'])
        ko.install()
        _ = ko.gettext
    else:
        _ = gettext.gettext
    return _
