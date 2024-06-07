from pygame import Surface, display, time
from pygame.time import get_ticks

from src.common import BLACK


def fade(fade_out: bool, screen: Surface, config) -> None:
    """
    Fade to/from current scene to/from black.
    @param screen: The screen.
    @param config: The game configuration.
    :return: None
    @type fade_out: bool
    If true, fades out. If false, fades in.
    """
    width, height = screen.get_width(), screen.get_height()
    fade_surface = Surface((width, height))  # lgtm [py/call/wrong-arguments]
    fade_surface.fill(BLACK)
    # TODO(ELF): Fix fade in. Maybe this link will help? https://stackoverflow.com/questions/54881269/pygame-fade-to-black-function
    #  https://stackoverflow.com/questions/58540537/how-to-fade-the-screen-out-and-back-in-using-pygame

    # Initialize opacity
    opacity = 255 if not fade_out else 0

    # Adjust the range based on fade direction
    alpha_range = range(255, -1, -1) if not fade_out else range(256)

    for alpha in alpha_range:
        fade_surface.set_alpha(opacity)
        screen.blit(fade_surface, (0, 0)) if not config['NO_BLIT'] else None
        display.update(fade_surface.get_rect())
        if not config['NO_WAIT']:
            time.delay(5)

        # Update opacity based on fade direction
        if fade_out:
            opacity += 1
        else:
            opacity -= 1


def draw_transparent_color(color, screen, transparency, no_blit):
    color_flash_surface = Surface((screen.get_width(), screen.get_height()))
    color_flash_surface.set_alpha(transparency)
    color_flash_surface.fill(color)
    if not no_blit:
        screen.blit(color_flash_surface, (0, 0))


def flash_transparent_color(color, screen, calculation, transparency=192, no_blit=False):
    start_time = get_ticks()
    draw_transparent_color(color, screen, transparency, no_blit)
    while calculation.convert_to_frames_since_start_time(start_time) < 3:
        display.flip()
