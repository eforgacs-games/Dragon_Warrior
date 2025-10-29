from pygame import Surface, display, time
from pygame.time import get_ticks

from src.common import BLACK


def fade(fade_out: bool, screen: Surface, config, draw_callback=None, speed=3) -> None:
    """
    Fade to/from current scene to/from black.
    @param screen: The screen.
    @param config: The game configuration.
    @param draw_callback: Optional callback function to redraw game content (needed for fade_in).
    @param speed: Speed multiplier for fade effect (higher = faster). Default is 3.
    :return: None
    @type fade_out: bool
    If true, fades out. If false, fades in.
    """
    width, height = screen.get_width(), screen.get_height()
    fade_surface = Surface((width, height))  # lgtm [py/call/wrong-arguments]
    fade_surface.fill(BLACK)

    # For fade in, capture the current screen state
    if not fade_out:
        background = screen.copy()

    # Initialize opacity
    opacity = 0 if fade_out else 255

    # Adjust the range based on fade direction and speed
    alpha_range = range(0, 256, speed) if fade_out else range(255, -1, -speed)

    for alpha in alpha_range:
        # For fade in, restore the background before applying the fade
        if not fade_out:
            if draw_callback:
                draw_callback()
            else:
                screen.blit(background, (0, 0))

        fade_surface.set_alpha(opacity)
        screen.blit(fade_surface, (0, 0)) if not config['NO_BLIT'] else None
        display.update()
        if not config['NO_WAIT']:
            time.delay(5)

        # Update opacity based on fade direction
        if fade_out:
            opacity = min(255, opacity + speed)
        else:
            opacity = max(0, opacity - speed)


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
