import os
import sys
from os.path import join

from pygame import image, display, QUIT, quit, KEYUP
from pygame.event import get
from pygame.time import get_ticks
from pygame.transform import scale

from src.common import convert_to_frames, INTRO_BANNER_WITH_DRAGON_PATH, ORANGE, DRAGON_QUEST_FONT_PATH, PINK, \
    SMB_FONT_PATH, convert_to_milliseconds, BLACK, \
    INTRO_BANNER_PATH
from src.config import IMAGES_DIR, FPS
from src.text import draw_text
from src.visual_effects import fade


def convert_to_frames_since_start_time(start_time):
    return convert_to_frames(get_ticks() - start_time)


def show_intro_banner(intro_banner_path, screen):
    intro_banner = image.load(intro_banner_path)
    intro_banner = scale(intro_banner, (screen.get_width(), intro_banner.get_height() * 2))
    intro_banner_rect = intro_banner.get_rect()
    intro_banner_rect.midtop = (screen.get_width() / 2, screen.get_height() * 1 / 6)
    screen.blit(intro_banner, intro_banner_rect)


def banner_sparkle(short, screen):
    # first (long) sparkle starts 654 frames in, ends at 678 frames in, lasts (678 - 654 = 24 frames)
    # first (short) sparkle starts 782 frames in, ends at 794 frames in, lasts (794 - 782 = 12 frames)
    for banner in os.listdir(join(IMAGES_DIR, 'intro_banner', 'sparkle')):
        before_frame = convert_to_frames(get_ticks())
        if short:
            frames_per_slide = 1.5
        else:
            frames_per_slide = 3
        while convert_to_frames(get_ticks()) < before_frame + frames_per_slide:
            show_intro_banner(join(IMAGES_DIR, 'intro_banner', 'sparkle', banner), screen)
            display.flip()


def draw_banner_text(screen):
    draw_text("- PUSH ANY KEY -", 15, ORANGE, screen.get_width() / 2, screen.get_height() * 10 / 16, DRAGON_QUEST_FONT_PATH, screen)
    pink_banner_text = ("K key: A Button", "J key: B Button", "I key: Start", "WASD / Arrow Keys: Move")
    for i in range(11, 15):
        draw_text(pink_banner_text[i - 11], 15, PINK, screen.get_width() / 2, screen.get_height() * i / 16, DRAGON_QUEST_FONT_PATH, screen, text_wrap_length=23)
    draw_text("(↑ ← ↓ →)", 15, PINK, screen.get_width() / 2, screen.get_height() * 15 / 16, SMB_FONT_PATH, screen)


def repeated_sparkle(screen, clock_check, short):
    if get_ticks() - clock_check >= convert_to_milliseconds(256):
        clock_check = get_ticks()
        banner_sparkle(short, screen)
    return clock_check


def handle_sparkles(screen, done, clock_check, short):
    if not done:
        # print(f'{frames_since_program_launch} sparkle')
        banner_sparkle(short, screen)
        # return sparkle_done, last_sparkle_clock_check
        return True, get_ticks()
    else:
        return True, repeated_sparkle(screen, clock_check, short)


class Intro:
    def __init__(self):
        self.last_long_sparkle_clock_check = None
        self.last_first_short_sparkle_clock_check = None
        self.last_second_short_sparkle_clock_check = None

        self.first_long_sparkle_done = False
        self.first_short_sparkle_done = False
        self.second_short_sparkle_done = False

    def show_start_screen(self, screen, start_time, clock, background):
        screen.fill(BLACK)
        show_intro_banner(INTRO_BANNER_PATH, screen)
        display.flip()
        waiting = True
        while waiting:
            clock.tick(FPS)
            for current_event in get():
                if current_event.type == QUIT:
                    quit()
                    sys.exit()
                elif current_event.type == KEYUP:
                    waiting = False
            if convert_to_frames_since_start_time(start_time) >= 620:  # intro banner with text displays 620 frames in
                waiting = False
            display.flip()
        self.show_intro_dragon_banner_with_text(screen, clock, background)

    def show_intro_dragon_banner_with_text(self, screen, clock, background):
        show_intro_banner(INTRO_BANNER_WITH_DRAGON_PATH, screen)
        draw_banner_text(screen)
        # TODO: Might be good to add these control keys to an F1 help screen.
        display.flip()
        intro_banner_with_text_enabled = True
        intro_banner_with_text_enabled_start_time = get_ticks()

        while intro_banner_with_text_enabled:
            self.handle_all_sparkles(intro_banner_with_text_enabled_start_time, screen)
            clock.tick(FPS)
            for current_event in get():
                if current_event.type == QUIT:
                    quit()
                    sys.exit()
                elif current_event.type == KEYUP:
                    intro_banner_with_text_enabled = False
            display.flip()
        fade(fade_out=True, screen=screen)

    def handle_all_sparkles(self, start_time, screen):
        frames_since_banner_launch = convert_to_frames_since_start_time(start_time)
        if frames_since_banner_launch >= 32:
            self.first_long_sparkle_done, self.last_long_sparkle_clock_check = handle_sparkles(screen, self.first_long_sparkle_done,
                                                                                               self.last_long_sparkle_clock_check,
                                                                                               short=False)
            if frames_since_banner_launch >= 32 + 128:  # 160
                self.first_short_sparkle_done, self.last_first_short_sparkle_clock_check = handle_sparkles(screen, self.first_short_sparkle_done,
                                                                                                           self.last_first_short_sparkle_clock_check,
                                                                                                           short=True)
                if frames_since_banner_launch >= 32 + 128 + 32:  # 192
                    self.second_short_sparkle_done, self.last_second_short_sparkle_clock_check = handle_sparkles(screen, self.second_short_sparkle_done,
                                                                                                                 self.last_second_short_sparkle_clock_check,
                                                                                                                 short=True)


def wait_for_key(clock):
    waiting = True
    while waiting:
        clock.tick(FPS)
        for current_event in get():
            if current_event.type == QUIT:
                quit()
                sys.exit()
            elif current_event.type == KEYUP:
                waiting = False
