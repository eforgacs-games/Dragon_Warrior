import time
from typing import Tuple, List

from pygame import display, Surface, KEYDOWN, image, transform
from pygame.event import get
from pygame.time import get_ticks

from src.common import WHITE, DRAGON_QUEST_FONT_PATH, BLACK, play_sound, menu_button_sfx, text_beep_sfx, DIALOG_BOX_BACKGROUND_PATH
from src.config import TILE_SIZE
from src.text import draw_text


def show_line_in_dialog_box(line, screen, add_quotes=True, temp_text_start=None):
    """Shows a single line in a dialog box."""
    display_current_line = True
    finished_printing = False
    if add_quotes:
        line = f"`{line}’"
    while display_current_line:
        if temp_text_start:
            current_time = get_ticks()
        black_box = Surface((TILE_SIZE * 12, TILE_SIZE * 5))  # lgtm [py/call/wrong-arguments]
        set_window_background(black_box, DIALOG_BOX_BACKGROUND_PATH)
        screen.blit(black_box, (TILE_SIZE * 2, TILE_SIZE * 9))
        if not finished_printing:
            for i in range(len(line)):
                time.sleep(0.01)
                if i % 2 == 0:
                    play_sound(text_beep_sfx)
                if i == len(line) - 1:
                    finished_printing = True
        # if print_by_character:
        #     for i in range(len(line)):
        #         for j in range(16):
        #             white_line = line[:i]
        #             black_line = line[i:]
        #             draw_text(white_line, 15, WHITE, self.screen.get_width() / 2, (self.screen.get_height() * 5 / 8),
        #                       DRAGON_QUEST_FONT_PATH,
        #                       self.screen)
        #             draw_text(black_line, 15, BLACK, self.screen.get_width() / 2, (self.screen.get_height() * 5 / 8),
        #                       DRAGON_QUEST_FONT_PATH,
        #                       self.screen)
        # else:
        draw_text(line, 15, WHITE, TILE_SIZE * 3, TILE_SIZE * 9.75, DRAGON_QUEST_FONT_PATH, screen, center_align=False)
        display.flip()
        blink_down_arrow(screen)
        for current_event in get():
            if current_event.type == KEYDOWN:
                # if current_key[K_KP_ENTER] or current_key[K_k]:
                play_sound(menu_button_sfx)
                display_current_line = False
        if temp_text_start:
            if current_time - temp_text_start >= 200:
                play_sound(menu_button_sfx)
                display_current_line = False


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


def dialog_box_drop_up_effect(current_map, background, camera_position, screen):
    """Outro effect for dialog box."""
    # TODO(ELF): Needs work - doesn't always drop up smoothly. One observation is that it appears to work better closer
    #  to the origin (0, 0) of the map.
    # draw all the tiles initially once
    for tile, tile_dict in current_map.floor_tile_key.items():
        if tile in current_map.tile_types_in_current_map:
            tile_dict['group'].draw(background)
    for i in range(4, -1, -1):
        dialog_box_underlying_tiles = get_dialog_box_underlying_tiles(current_map, i)
        black_box = Surface((TILE_SIZE * 12, TILE_SIZE * i))  # lgtm [py/call/wrong-arguments]
        black_box.fill(BLACK)
        for j in range(64):
            for tile, tile_dict in current_map.floor_tile_key.items():
                if tile in dialog_box_underlying_tiles:
                    tile_dict['group'].draw(background)
            screen.blit(background, camera_position)
            screen.blit(black_box, (TILE_SIZE * 2, TILE_SIZE * 9))
            display.update()


def get_dialog_box_underlying_tiles(current_map, current_box_height):
    # TODO(ELF): Can be improved further by narrowing the columns to just where the box is, not only the rows.
    box_start_row = 2
    box_end_row = current_box_height + box_start_row
    row_tile_sets = [set(row) for row in
                     current_map.layout[current_map.player.row + box_start_row:current_map.player.row + box_end_row]]
    return set([item for sublist in row_tile_sets for item in sublist])


def dialog_box_drop_down_effect(screen):
    """Intro effect for dialog box."""
    for i in range(6):
        black_box = Surface((TILE_SIZE * 12, TILE_SIZE * i))  # lgtm [py/call/wrong-arguments]
        black_box.fill(BLACK)
        for j in range(64):
            screen.blit(black_box, (TILE_SIZE * 2, TILE_SIZE * 9))
            display.update()


def show_text_in_dialog_box(text: Tuple[str] | List[str], background, camera_position, current_map, screen, add_quotes=True,
                            temp_text_start=None):
    """Shows a passage of text in a dialog box."""
    dialog_box_drop_down_effect(screen)
    for line in text:
        show_line_in_dialog_box(line, screen, add_quotes, temp_text_start)
    dialog_box_drop_up_effect(current_map, background, camera_position, screen)


class Dialog:
    def __init__(self, player, screen):
        self.screen = screen
        self.player = player
        self.dialog_character = ''
