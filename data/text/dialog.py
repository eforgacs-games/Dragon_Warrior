from pygame import display, Surface, KEYDOWN
from pygame.event import get

from src.common import print_with_beep_sfx, WHITE, DRAGON_QUEST_FONT_PATH, BLACK
from src.config import TILE_SIZE
from src.text import draw_text


class Dialog:
    def __init__(self, player, dialog_character, screen):
        self.screen = screen
        self.player = player
        self.dialog_character = dialog_character
        self.dialog_text = []

    def say_dialog(self):
        if self.dialog_text:
            # for line in self.dialog_text:
            #     draw_text(line, 15, WHITE, self.screen.get_width() / 2, self.screen.get_height() / 2,
            #               DRAGON_QUEST_FONT_PATH,
            #               self.screen)
            #     display.update()
            for line in self.dialog_text:
                self.show_text_in_dialog_box(line)
        else:
            print("Character has no dialog.")

    def show_text_in_dialog_box(self, line):
        display_current_line = True
        while display_current_line:
            black_box = Surface((TILE_SIZE * 12, TILE_SIZE * 5))
            black_box.fill(BLACK)
            self.screen.blit(black_box, (TILE_SIZE * 2, TILE_SIZE * 9))
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
            draw_text(line, 15, WHITE, TILE_SIZE * 3, TILE_SIZE * 9.5,
                      DRAGON_QUEST_FONT_PATH,
                      self.screen, center_align=False)
            display.flip()
            for i in range(256):
                draw_text("▼", 15, WHITE, self.screen.get_width() / 2, (self.screen.get_height() * 3 / 4) + 30,
                          DRAGON_QUEST_FONT_PATH,
                          self.screen)
                display.flip()
            for i in range(256):
                draw_text("▼", 15, BLACK, self.screen.get_width() / 2, (self.screen.get_height() * 3 / 4) + 30,
                          DRAGON_QUEST_FONT_PATH,
                          self.screen)
                display.flip()
            for current_event in get():
                if current_event.type == KEYDOWN:
                    # if current_key[K_KP_ENTER] or current_key[K_k]:
                    display_current_line = False

    def dialog_box_drop_down_effect(self):
        """Intro effect for dialog box."""
        # TODO(ELF): Make dialog_box_drop_up_effect.
        for i in range(6):
            for j in range(32):
                black_box = Surface((TILE_SIZE * 12, TILE_SIZE * i))
                black_box.fill(BLACK)
                self.screen.blit(black_box, (TILE_SIZE * 2, TILE_SIZE * 9))
                display.update()
