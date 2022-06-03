from pygame import display, image, transform

from src.common import WHITE, DRAGON_QUEST_FONT_PATH, BLACK
from src.text import draw_text


def set_window_background(black_box, background_path):
    black_box.fill(BLACK)
    dialog_box_background = image.load(background_path)
    dialog_box_background = transform.scale(dialog_box_background, black_box.get_size())
    black_box.blit(dialog_box_background, black_box.get_rect())


def blink_down_arrow(screen):
    for i in range(256):
        draw_text("▼", 15, WHITE, screen.get_width() / 2, (screen.get_height() * 13 / 16) + 32, DRAGON_QUEST_FONT_PATH, screen)
        # TODO(ELF): Change display.flip() to display.update() and pass in a rect.
        display.flip()
    for i in range(256):
        draw_text("▼", 15, BLACK, screen.get_width() / 2, (screen.get_height() * 13 / 16) + 32, DRAGON_QUEST_FONT_PATH, screen)
        display.flip()


def get_dialog_box_underlying_tiles(current_map, current_box_height):
    # TODO(ELF): Can be improved further by narrowing the columns to just where the box is, not only the rows.
    box_start_row = 2
    box_end_row = current_box_height + box_start_row
    row_tile_sets = [set(row) for row in
                     current_map.layout[current_map.player.row + box_start_row:current_map.player.row + box_end_row]]
    return set([item for sublist in row_tile_sets for item in sublist])
