from pygame import Surface, display, time
from pygame.time import get_ticks

from src.common import BLACK, convert_to_frames_since_start_time


def fade(fade_out: bool, screen: Surface) -> None:
    """
    Fade to/from current scene to/from black.
    @param screen: The screen.
    :return: None
    @type fade_out: bool
    If true, fades out. If false, fades in.
    """
    width, height = screen.get_width(), screen.get_height()
    fade_surface = Surface((width, height))  # lgtm [py/call/wrong-arguments]
    fade_surface.fill(BLACK)
    opacity = 0
    for alpha in range(255):
        if fade_out:
            opacity += 1
        else:
            # TODO(ELF): Fix fade in. Maybe this link will help? https://stackoverflow.com/questions/54881269/pygame-fade-to-black-function
            #  https://stackoverflow.com/questions/58540537/how-to-fade-the-screen-out-and-back-in-using-pygame
            opacity -= 1
        fade_surface.set_alpha(opacity)
        screen.blit(fade_surface, (0, 0))
        display.update(fade_surface.get_rect())
        time.delay(5)


def draw_transparent_color(color, screen, transparency):
    color_flash_surface = Surface((screen.get_width(), screen.get_height()))  # lgtm [py/call/wrong-arguments]
    color_flash_surface.set_alpha(transparency)
    color_flash_surface.fill(color)
    screen.blit(color_flash_surface, (0, 0))


def flash_transparent_color(color, screen, transparency=192):
    start_time = get_ticks()
    draw_transparent_color(color, screen, transparency)
    while convert_to_frames_since_start_time(start_time) < 3:
        display.flip()
