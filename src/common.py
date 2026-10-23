# Constants
import gettext
import ntpath
import os
from os.path import sep, exists

from pygame import Surface, image, transform, K_RETURN, K_i, K_k, K_ESCAPE, K_j, K_u, K_UP, K_DOWN, K_LEFT, K_RIGHT, \
    K_w, K_a, K_s, K_d

from src.color import WHITE, BLACK
from src.direction import Direction
from src.directories import Directories
from src.korean_particles import KoreanText
from src.paths import data_path


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
        :param color: The window color: white, or another color for its white pixels (the low HP red, $26).
        :param border: If given, the size of the image's corners in NES pixels: the image is stretched without
        distorting its border (see nine_slice), so one image serves windows of any size. Otherwise the whole image is
        scaled to the window.
        """
        black_box.fill(BLACK)
        background_image = image.load(background_path)
        if color != WHITE:
            transform.threshold(background_image, background_image, WHITE, (1, 1, 1), color, 1, None, True)
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

# The NES joypad on the keyboard. Enter is an extra A (it also picks menu items and is the TAKE/DOOR/TALK shortcut) and
# Escape an extra B (it closes the command window), like accept_keys and reject_keys.
A_BUTTON_KEYS = (K_k, K_RETURN)
B_BUTTON_KEYS = (K_j, K_ESCAPE)
START_BUTTON_KEYS = (K_i,)
SELECT_BUTTON_KEYS = (K_u,)
UP_KEYS = (K_UP, K_w)
DOWN_KEYS = (K_DOWN, K_s)
LEFT_KEYS = (K_LEFT, K_a)
RIGHT_KEYS = (K_RIGHT, K_d)
D_PAD_KEYS = UP_KEYS + DOWN_KEYS + LEFT_KEYS + RIGHT_KEYS
# Bank01 TxtCheckInput (DoWait, the dialog's blinking down arrow): JoypadBtns AND #IN_A_OR_B
A_OR_B_KEYS = A_BUTTON_KEYS + B_BUTTON_KEYS
# Bank03 WaitForBtnPress (after WaitForBtnRelease, ending a conversation): any joypad button, D-pad, START and SELECT too
ANY_BUTTON_KEYS = A_BUTTON_KEYS + B_BUTTON_KEYS + START_BUTTON_KEYS + SELECT_BUTTON_KEYS + D_PAD_KEYS
# Bank03 DeathText (after "Thou art dead."): JoypadBtns AND #$09, IN_A or IN_START
A_OR_START_KEYS = A_BUTTON_KEYS + START_BUTTON_KEYS


def singular_or_plural(count: int, singular: str, plural: str) -> str:
    """The NES text's PLRL, PNTS and AMTP (Bank01 DoPLRL, DoPNTS, DoAMTP): "Point" or "Hit" when the amount is exactly 1,
    "Points" or "Hits" for anything else, 0 included. Both forms are separate catalog entries."""
    return singular if count == 1 else plural


def set_gettext_language(language):
    localedir = data_path('text', 'locales')
    if language == 'Korean':
        ko = gettext.translation('base', localedir=localedir, languages=['ko'])
        ko.install()

        def _(message):
            # KoreanText: .format() makes a particle after a placeholder agree with the value (src/korean_particles.py)
            return KoreanText(ko.gettext(message))
    else:
        _ = gettext.gettext
    return _
