from typing import Tuple, List

from pygame import surface
from pygame.transform import scale


def parse_map_tiles(map_path: str, tile_size: int, graphics, configured_scale):
    map_sheet = graphics.get_image(map_path).convert()
    map_tile_sheet = scale(map_sheet,
                           (map_sheet.get_width() * configured_scale, map_sheet.get_height() * configured_scale))
    width, height = map_tile_sheet.get_size()
    return [[map_tile_sheet.subsurface((x * tile_size, y * tile_size, tile_size, tile_size)) for y in
             range(0, height // tile_size)]
            for x in range(0, width // tile_size)]


def warp_line(lower_bound, upper_bound) -> List[tuple]:
    assert lower_bound[0] == upper_bound[0] or lower_bound[1] == upper_bound[1]
    if lower_bound[0] != upper_bound[0]:
        return [(min(n, upper_bound[0]), upper_bound[1]) for n in range(lower_bound[0], upper_bound[0] + 1)]
    else:
        return [(upper_bound[0], min(n, upper_bound[1])) for n in range(lower_bound[1], upper_bound[1] + 1)]


def parse_animated_sprite_sheet(sheet: surface.Surface, config: dict) -> Tuple[list, list, list, list]:
    """
    Parses sprite sheets and creates image lists. If is_roaming is True
    the sprite will have four lists of images, one for each direction. If
    is_roaming is False then there will be one list of 2 images.
    """
    sheet.set_colorkey(config['COLOR_KEY'])
    sheet.convert_alpha()

    facing_down, facing_left, facing_up, facing_right = [], [], [], []

    for i in range(0, 2):

        tile_size = config['TILE_SIZE']
        rect = (i * tile_size, 0, tile_size, tile_size)
        facing_down.append(sheet.subsurface(rect))

        is_four_sided = sheet.get_size()[0] % 128 == 0
        if is_four_sided:
            # is_four_sided
            rect = ((i + 2) * tile_size, 0, tile_size, tile_size)
            facing_left.append(sheet.subsurface(rect))

            rect = ((i + 4) * tile_size, 0, tile_size, tile_size)
            facing_up.append(sheet.subsurface(rect))

            rect = ((i + 6) * tile_size, 0, tile_size, tile_size)
            facing_right.append(sheet.subsurface(rect))

    return facing_down, facing_left, facing_up, facing_right


def get_center_point(x, y, tile_size):
    offset = tile_size // 2
    return (x * tile_size) + offset, (y * tile_size) + offset
