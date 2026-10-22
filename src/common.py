# Constants
import gettext
import ntpath
import os
from os.path import sep, exists

from pygame import Surface, image, transform, K_RETURN, K_i, K_k, K_ESCAPE, K_j

from src.color import WHITE, BLACK, RED
from src.direction import Direction
from src.directories import Directories


def find_file(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)


# Images

_image_library: dict[str, object] = {}
_scaled_image_library: dict[tuple, object] = {}  # Cache for scaled images


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


# Windows


def nine_slice(source: Surface, size: tuple[int, int], border: int) -> Surface:
    """Stretch a window background to any size without distorting its border.
    The corners (border x border pixels) are copied as they are; the edges and the middle are stretched. This is how
    the NES builds a window of any size out of fixed corner, edge and blank tiles (Bank01 WndUpdateWrkTile).
    :param source: The window background image.
    :param size: The (width, height) of the window to make.
    :param border: The size of a corner, in pixels of the source image.
    :return: The stretched window background.
    """
    source_width, source_height = source.get_size()
    width, height = size
    result = Surface(size)
    # (source start, source length, destination start, destination length) for the 3 columns and the 3 rows
    columns = ((0, border, 0, border),
               (border, source_width - 2 * border, border, width - 2 * border),
               (source_width - border, border, width - border, border))
    rows = ((0, border, 0, border),
            (border, source_height - 2 * border, border, height - 2 * border),
            (source_height - border, border, height - border, border))
    for source_x, source_w, x, w in columns:
        for source_y, source_h, y, h in rows:
            piece = source.subsurface((source_x, source_y, source_w, source_h))
            result.blit(transform.scale(piece, (w, h)), (x, y))
    return result


# Maps


class Graphics:
    def __init__(self, config):
        self.config = config
        self.directories = Directories(config)

    def set_window_background(self, black_box, background_path, color, border: int | None = None):
        """Draw a window background image onto a window.
        :param black_box: The window surface.
        :param background_path: The window background image, in NES pixels.
        :param color: The window color (red when the hero is nearly dead).
        :param border: If given, the size of the image's corners in NES pixels: the image is stretched without
        distorting its border (see nine_slice), so one image serves windows of any size. Otherwise the whole image is
        scaled to the window.
        """
        black_box.fill(BLACK)
        background_image = image.load(background_path)
        if color == RED:
            transform.threshold(background_image, background_image, WHITE, (1, 1, 1), RED, 1, None, True)
            # image_pixel_array = PixelArray(background_image)
            # image_pixel_array.replace(WHITE, RED)
        if border is None:
            background_image = transform.scale(background_image, black_box.get_size())
        else:
            scale = self.config['SCALE']
            background_image = transform.scale_by(background_image, scale)
            background_image = nine_slice(background_image, black_box.get_size(), border * scale)
        black_box.blit(background_image, black_box.get_rect()) if not self.config['NO_BLIT'] else None

    def create_window(self, x, y, width, height, window_background, screen, color,
                      border: int | None = None) -> Surface:
        """Draw a window on the screen. Position and size are in blocks (16 NES pixels; TILE_SIZE screen pixels).
        :param border: See set_window_background.
        """
        tile_size = self.config["TILE_SIZE"]
        window_box = Surface((tile_size * width, tile_size * height))  # lgtm [py/call/wrong-arguments]
        self.set_window_background(window_box, window_background, color=color, border=border)
        screen.blit(window_box, (tile_size * x, tile_size * y)) if not self.config['NO_BLIT'] else None
        return window_box

    def get_image(self, path):
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

    def get_scaled_image(self, path, size):
        """Get a cached scaled image.

        Args:
            path: Path to the image file
            size: Tuple of (width, height) for the scaled size

        Returns:
            Scaled pygame Surface
        """
        cache_key = (path, size)
        scaled_img = _scaled_image_library.get(cache_key)
        if scaled_img is None:
            # Load the base image (cached)
            base_image = self.get_image(path)
            # Scale it and cache the result
            from pygame.transform import scale
            scaled_img = scale(base_image, size)
            _scaled_image_library[cache_key] = scaled_img
        return scaled_img


accept_keys = (K_RETURN, K_i, K_k)
reject_keys = (K_ESCAPE, K_j)


def set_gettext_language(language):
    localedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'text', 'locales'))
    if language == 'Korean':
        ko = gettext.translation('base', localedir=localedir, languages=['ko'])
        ko.install()
        _ = ko.gettext
    else:
        _ = gettext.gettext
    return _
