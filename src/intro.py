import os
import sys
from os.path import join

from pygame import image, font, display, QUIT, quit, KEYUP
from pygame.event import get
from pygame.time import get_ticks
from pygame.transform import scale

from src.common import convert_to_frames, INTRO_BANNER_WITH_DRAGON_PATH, ORANGE, DRAGON_QUEST_FONT_PATH, PINK, SMB_FONT_PATH, convert_to_milliseconds, BLACK, \
    INTRO_BANNER_PATH
from src.config import IMAGES_DIR, FPS
from src.visual_effects import fade


def convert_to_frames_since_start_time(start_time):
    return convert_to_frames(get_ticks() - start_time)


def show_intro_banner(intro_banner_path, screen):
    intro_banner = image.load(intro_banner_path)
    intro_banner = scale(intro_banner, (screen.get_width(), intro_banner.get_height() * 2))
    intro_banner_rect = intro_banner.get_rect()
    intro_banner_rect.midtop = (screen.get_width() / 2, screen.get_height() * 1 / 6)
    screen.blit(intro_banner, intro_banner_rect)


def draw_text(text, size, color, x, y, font_name, screen):
    text_surface = font.Font(font_name, size).render(text, True, color)
    text_rect = text_surface.get_rect()
    text_rect.midtop = (x, y)
    screen.blit(text_surface, text_rect)


def banner_sparkle(short, screen):
    # first (long) sparkle starts 654 frames in, ends at 678 frames in, lasts (678 - 654 = 24 frames)
    for banner in os.listdir(join(IMAGES_DIR, 'intro_banner', 'sparkle')):
        if short:
            speed = 12
        else:
            speed = 24
        for i in range(speed):
            show_intro_banner(join(IMAGES_DIR, 'intro_banner', 'sparkle', banner), screen)
        display.flip()


def show_intro_dragon_banner_with_text(screen, clock, background):
    show_intro_banner(INTRO_BANNER_WITH_DRAGON_PATH, screen)
    draw_text("- PUSH ANY KEY -", 15, ORANGE, screen.get_width() / 2, screen.get_height() * 10 / 16, DRAGON_QUEST_FONT_PATH, screen)
    draw_text("K key: A Button", 15, PINK, screen.get_width() / 2, screen.get_height() * 11 / 16, DRAGON_QUEST_FONT_PATH, screen)
    draw_text("J key: B Button", 15, PINK, screen.get_width() / 2, screen.get_height() * 12 / 16, DRAGON_QUEST_FONT_PATH, screen)
    draw_text("I key: Start", 15, PINK, screen.get_width() / 2, screen.get_height() * 13 / 16, DRAGON_QUEST_FONT_PATH, screen)
    draw_text("WASD / Arrow Keys: Move", 15, PINK, screen.get_width() / 2, screen.get_height() * 14 / 16, DRAGON_QUEST_FONT_PATH, screen)
    draw_text("(↑ ← ↓ →)", 15, PINK, screen.get_width() / 2, screen.get_height() * 15 / 16, SMB_FONT_PATH, screen)
    # TODO: Might be good to add these control keys to an F1 help screen.
    display.flip()
    intro_banner_with_text_enabled = True
    intro_banner_with_text_enabled_start_time = get_ticks()

    last_long_sparkle_clock_check = None
    last_first_short_sparkle_clock_check = None
    last_second_short_sparkle_clock_check = None

    first_long_sparkle_done = False
    first_short_sparkle_done = False
    second_short_sparkle_done = False
    while intro_banner_with_text_enabled:
        frames_since_banner_launch = convert_to_frames_since_start_time(intro_banner_with_text_enabled_start_time)
        if int(frames_since_banner_launch) >= 32:
            # first long sparkle
            if not first_long_sparkle_done:
                first_long_sparkle_done = True
                last_long_sparkle_clock_check = get_ticks()
                # print(f'{frames_since_program_launch} long sparkle')
                banner_sparkle(short=False, screen=screen)
            else:
                if get_ticks() - last_long_sparkle_clock_check >= convert_to_milliseconds(256):
                    # print(f'{frames_since_program_launch} long sparkle')
                    last_long_sparkle_clock_check = get_ticks()
                    banner_sparkle(short=False, screen=screen)
        if int(frames_since_banner_launch) >= 160:
            # first short sparkle
            if not first_short_sparkle_done:
                first_short_sparkle_done = True
                last_first_short_sparkle_clock_check = get_ticks()
                # print(f'{frames_since_program_launch} short sparkle')
                banner_sparkle(short=True, screen=screen)
            else:
                if get_ticks() - last_first_short_sparkle_clock_check >= convert_to_milliseconds(256):
                    last_first_short_sparkle_clock_check = get_ticks()
                    # print(f'{frames_since_program_launch} short sparkle')
                    banner_sparkle(short=True, screen=screen)
        # second short sparkle
        if int(frames_since_banner_launch) >= 192:
            if not second_short_sparkle_done:
                second_short_sparkle_done = True
                last_second_short_sparkle_clock_check = get_ticks()
                # print(f'{frames_since_program_launch} short sparkle')
                banner_sparkle(short=True, screen=screen)
            else:
                if get_ticks() - last_second_short_sparkle_clock_check >= convert_to_milliseconds(256):
                    last_second_short_sparkle_clock_check = get_ticks()
                    # print(f'{frames_since_program_launch} short sparkle')
                    banner_sparkle(short=True, screen=screen)
        clock.tick(FPS)
        for current_event in get():
            if current_event.type == QUIT:
                quit()
                sys.exit()
            if current_event.type == KEYUP:
                intro_banner_with_text_enabled = False
    fade(screen.get_width(), screen.get_height(), fade_out=True, background=background, screen=screen)


def show_start_screen(screen, start_time, clock, background):
    screen.fill(BLACK)
    show_intro_banner(INTRO_BANNER_PATH, screen)
    display.flip()
    waiting = True
    while waiting:
        frames = 60 * (get_ticks() - start_time) / 1000
        clock.tick(FPS)
        for current_event in get():
            if current_event.type == QUIT:
                quit()
                sys.exit()
            if current_event.type == KEYUP:
                waiting = False
        if frames >= 620:  # intro banner with text displays 620 frames in
            waiting = False
    show_intro_dragon_banner_with_text(screen, clock, background)


def wait_for_key(clock):
    waiting = True
    while waiting:
        clock.tick(FPS)
        for current_event in get():
            if current_event.type == QUIT:
                quit()
                sys.exit()
            if current_event.type == KEYUP:
                waiting = False
