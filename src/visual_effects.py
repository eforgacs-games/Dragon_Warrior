from pygame import Surface, display, time

from src.common import BLACK


def fade(width: int, height: int, fade_out: bool, background, screen) -> None:
    """
    Fade to/from current scene to/from black.
    @param screen: The screen.
    @param background: The background.
    :return: None
    @param width: int
    Width of surface to fade.
    @param height:
    Height of surface to fade.
    @type fade_out: bool
    If true, fades out. If false, fades in.
    """
    fade_surface = Surface((width, height))  # lgtm [py/call/wrong-arguments]
    fade_surface.fill(BLACK)
    opacity = 0
    for alpha in range(300):
        if fade_out:
            opacity += 1
        else:
            # TODO(ELF): Fix fade in. Maybe this link will help? https://stackoverflow.com/questions/54881269/pygame-fade-to-black-function
            opacity -= 1
        fade_surface.set_alpha(opacity)
        background.fill(BLACK)
        screen.blit(fade_surface, (0, 0))
        display.update()
        time.delay(5)
