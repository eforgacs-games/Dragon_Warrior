import time

from pygame import display, Surface, KEYDOWN, SRCALPHA
from pygame.event import get

from src.common import WHITE, DRAGON_QUEST_FONT_PATH, BLACK, play_sound, menu_button_sfx, text_beep_sfx
from src.config import TILE_SIZE
from src.text import draw_text


def show_text_in_dialog_box(line, screen):
    display_current_line = True
    finished_printing = False
    line = f"`{line}’"
    while display_current_line:
        black_box = Surface((TILE_SIZE * 12, TILE_SIZE * 5), flags=SRCALPHA)
        black_box.fill(BLACK)
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
        draw_text(line, 15, WHITE, TILE_SIZE * 3, TILE_SIZE * 9.75,
                  DRAGON_QUEST_FONT_PATH,
                  screen, center_align=False)
        display.flip()
        for i in range(256):
            draw_text("▼", 15, WHITE, screen.get_width() / 2, (screen.get_height() * 3 / 4) + 30,
                      DRAGON_QUEST_FONT_PATH,
                      screen)
            display.flip()
        for i in range(256):
            draw_text("▼", 15, BLACK, screen.get_width() / 2, (screen.get_height() * 3 / 4) + 30,
                      DRAGON_QUEST_FONT_PATH,
                      screen)
            display.flip()
        for current_event in get():
            if current_event.type == KEYDOWN:
                # if current_key[K_KP_ENTER] or current_key[K_k]:
                play_sound(menu_button_sfx)
                display_current_line = False


class Dialog:
    def __init__(self, player, dialog_character, screen):
        self.screen = screen
        self.player = player
        self.dialog_character = dialog_character
        self.dialog_text = []

    def say_dialog(self, current_map, background, camera_position):
        if self.dialog_text:
            # for line in self.dialog_text:
            #     draw_text(line, 15, WHITE, self.screen.get_width() / 2, self.screen.get_height() / 2,
            #               DRAGON_QUEST_FONT_PATH,
            #               self.screen)
            #     display.update()
            self.dialog_box_drop_down_effect()
            for line in self.dialog_text:
                show_text_in_dialog_box(line, self.screen)
            self.dialog_box_drop_up_effect(current_map, background, camera_position)
        else:
            print(f"Character has no dialog: {self.dialog_character}")

    def dialog_box_drop_down_effect(self):
        """Intro effect for dialog box."""
        for i in range(6):
            for j in range(32):
                black_box = Surface((TILE_SIZE * 12, TILE_SIZE * i))
                black_box.fill(BLACK)
                self.screen.blit(black_box, (TILE_SIZE * 2, TILE_SIZE * 9))
                display.update()

    def dialog_box_drop_up_effect(self, current_map, background, camera_position):
        """Outro effect for dialog box."""
        self.screen.blit(background, camera_position)
        for i in range(4, -1, -1):
            for j in range(32):
                for tile_dict in current_map.floor_tile_key.values():
                    if tile_dict.get('group'):
                        tile_dict['group'].draw(background)
                self.screen.blit(background, camera_position)
                black_box = Surface((TILE_SIZE * 12, TILE_SIZE * i))
                black_box.fill(BLACK)
                self.screen.blit(black_box, (TILE_SIZE * 2, TILE_SIZE * 9))
                display.flip()
