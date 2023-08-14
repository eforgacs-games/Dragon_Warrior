import os
from os.path import join

from pygame import image, display, QUIT, quit, Rect, Surface, event, KEYDOWN
from pygame.time import get_ticks
from pygame.transform import scale

from data.text.intro_lookup_table import ControlInfo
from src.calculation import Calculation
from src.color import BLACK, PINK, ORANGE
from src.common import accept_keys
from src.directories import Directories
from src.text import draw_text
from src.visual_effects import fade


def show_intro_banner(intro_banner_path, screen, no_blit) -> Rect:
    intro_banner = image.load(intro_banner_path)
    intro_banner = scale(intro_banner, (screen.get_width(), intro_banner.get_height() * 2))
    intro_banner_rect = intro_banner.get_rect()
    intro_banner_rect.midtop = (screen.get_width() / 2, screen.get_height() * 1 / 6)
    screen.blit(intro_banner, intro_banner_rect) if not no_blit else None
    return intro_banner_rect


class Intro:
    def __init__(self, config):
        self.config = config
        self.directories = Directories(config)
        self.calculation = Calculation(config)
        self.last_long_sparkle_clock_check = None
        self.last_first_short_sparkle_clock_check = None
        self.last_second_short_sparkle_clock_check = None

        self.first_long_sparkle_done = False
        self.first_short_sparkle_done = False
        self.second_short_sparkle_done = False

    def show_start_screen(self, screen, start_time, clock, config):
        screen.fill(BLACK)

        intro_banner_rect = show_intro_banner(self.directories.INTRO_BANNER_PATH, screen, config['NO_BLIT'])
        display.update(intro_banner_rect)
        waiting = True
        while waiting:
            clock.tick(config['FPS'])
            for current_event in event.get():
                if current_event.type == QUIT:
                    quit()
                elif current_event.type == KEYDOWN:
                    if current_event.key in accept_keys:
                        waiting = False
            if self.calculation.convert_to_frames_since_start_time(
                    start_time) >= 620:  # intro banner with text displays 620 frames in
                waiting = False
            display.update(intro_banner_rect)
        self.show_intro_dragon_banner_with_text(screen, clock, config)

    def show_intro_dragon_banner_with_text(self, screen, clock, config):
        show_intro_banner(self.directories.INTRO_BANNER_WITH_DRAGON_PATH, screen, config['NO_BLIT'])
        self.draw_banner_text(screen)
        display.flip()
        intro_banner_with_text_enabled = True
        intro_banner_with_text_enabled_start_time = get_ticks()

        while intro_banner_with_text_enabled:
            self.handle_all_sparkles(intro_banner_with_text_enabled_start_time, screen)
            clock.tick(config['FPS'])
            for current_event in event.get():
                if current_event.type == QUIT:
                    quit()
                elif current_event.type == KEYDOWN:
                    if current_event.key in accept_keys:
                        intro_banner_with_text_enabled = False
            display.flip()
        fade(fade_out=True, screen=screen, config=config)

    def handle_all_sparkles(self, start_time, screen):
        frames_since_banner_launch = self.calculation.convert_to_frames_since_start_time(start_time)
        if frames_since_banner_launch >= 32:
            self.first_long_sparkle_done, self.last_long_sparkle_clock_check = self.handle_sparkles(screen,
                                                                                                    self.first_long_sparkle_done,
                                                                                                    self.last_long_sparkle_clock_check,
                                                                                                    short=False)
            if frames_since_banner_launch >= 160:  # 32 + 128
                self.first_short_sparkle_done, self.last_first_short_sparkle_clock_check = self.handle_sparkles(screen,
                                                                                                                self.first_short_sparkle_done,
                                                                                                                self.last_first_short_sparkle_clock_check,
                                                                                                                short=True)
                if frames_since_banner_launch >= 192:  # 32 + 128 + 32
                    self.second_short_sparkle_done, self.last_second_short_sparkle_clock_check = self.handle_sparkles(
                        screen,
                        self.second_short_sparkle_done,
                        self.last_second_short_sparkle_clock_check,
                        short=True)

    def banner_sparkle(self, short: bool, screen: Surface) -> None:
        # first (long) sparkle starts 654 frames in, ends at 678 frames in, lasts (678 - 654 = 24 frames)
        # first (short) sparkle starts 782 frames in, ends at 794 frames in, lasts (794 - 782 = 12 frames)
        for banner in os.listdir(join(self.directories.IMAGES_DIR, 'intro_banner', 'sparkle')):
            before_frame = self.calculation.convert_to_frames(get_ticks())
            if short:
                frames_per_slide = 1.5
            else:
                frames_per_slide = 3
            while self.calculation.convert_to_frames(get_ticks()) < before_frame + frames_per_slide:
                intro_banner_rect = show_intro_banner(
                    join(self.directories.IMAGES_DIR, 'intro_banner', 'sparkle', banner),
                    screen, False)
                display.update(intro_banner_rect)

    def repeated_sparkle(self, screen: Surface, clock_check, short, ticks) -> int | float:
        if ticks - clock_check >= self.calculation.convert_to_milliseconds(256):
            clock_check = ticks
            self.banner_sparkle(short, screen)
        return clock_check

    def handle_sparkles(self, screen, done, clock_check, short):
        if not done:
            # print(f'{frames_since_program_launch} sparkle')
            self.banner_sparkle(short, screen)
            # return sparkle_done, last_sparkle_clock_check
            return True, get_ticks()
        else:
            return True, self.repeated_sparkle(screen, clock_check, short, get_ticks())

    def draw_banner_text(self, screen: Surface) -> None:
        control_info = ControlInfo(self.config)
        draw_text(control_info.push_start, screen.get_width() / 2, screen.get_height() * 10 / 16, screen, self.config,
                  ORANGE, alignment='center', letter_by_letter=False)
        for i in range(11, 15):
            draw_text(control_info.controls[i - 11], screen.get_width() / 2, screen.get_height() * i / 16, screen,
                      self.config, PINK, text_wrap_length=23, alignment='center', letter_by_letter=False)
        draw_text("(↑ ← ↓ →)", screen.get_width() / 2, screen.get_height() * 15 / 16, screen, self.config, PINK,
                  font_name=self.directories.SMB_FONT_PATH, alignment='center', letter_by_letter=False)
