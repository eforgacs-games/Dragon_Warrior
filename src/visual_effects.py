import sys
from array import array

from pygame import Surface, display, image, mask, transform
from src.waiting import game_ticks as get_ticks  # game time: runs N times as fast at speed N

from src.common import BLACK
from src.waiting import NES_FPS, check_for_quit, wait, wait_frames


SMOOTH_FADE_STEP_MS = 5  # the 'Smooth' fade (not an NES effect): one alpha step every 5 ms


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
    black_overlay = Surface((width, height))  # lgtm [py/call/wrong-arguments]
    black_overlay.fill(BLACK)

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

        black_overlay.set_alpha(opacity)
        screen.blit(black_overlay, (0, 0)) if not config['NO_BLIT'] else None
        display.update()
        check_for_quit()
        wait(SMOOTH_FADE_STEP_MS, config)

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


# A swamp step (NES DoSwampDamage -> RedFlashScreen): the red overlay is shown for 3 frames
SWAMP_FLASH_FRAMES = 3


def flash_transparent_color(color, screen, config, transparency=192) -> None:
    """Show the screen tinted with ``color`` for SWAMP_FLASH_FRAMES frames (the swamp damage flash). The wait goes
    through src.waiting, so it follows the game speed and NO_WAIT."""
    draw_transparent_color(color, screen, transparency, config.get('NO_BLIT'))
    show_frames(SWAMP_FLASH_FRAMES, config)


# NES force field damage (Bank03, LCE30-LCE42): three times over, WaitForNMI, RedFlashScreen (which waits a frame
# before loading RedFlashPal), WaitForNMI, then LoadRegBGPal (which waits a frame before loading the map's palette).
# A palette load shows from the next NMI, so the screen is as it was for 2 frames, then red for 2, three times.
FORCE_FIELD_FLASHES = 3
FORCE_FIELD_FLASH_FRAMES = 2


def force_field_flash(color, screen, config, transparency=192) -> None:
    """The screen flashing red three times when the hero steps onto a force field (barrier), 12 frames in all. A
    swamp step flashes once (flash_transparent_color)."""
    no_blit = config.get('NO_BLIT')
    original = screen.copy()
    for _ in range(FORCE_FIELD_FLASHES):
        show_frames(FORCE_FIELD_FLASH_FRAMES, config)
        draw_transparent_color(color, screen, transparency, no_blit)
        show_frames(FORCE_FIELD_FLASH_FRAMES, config)
        if not no_blit:
            screen.blit(original, (0, 0))
    display.flip()


# NES BWScreenFlash (Bank03, LDB37): eight times, two frames in color (WaitForNMI x2) and then three in greyscale
# (PPUControl1 = %00011001, WaitForNMI x3), 40 frames in all. Used when a spell is cast (PlyrCastSpell) and by a few
# story events (the Rainbow Drop shrine without Erdrick's Token, ...).
BW_FLASH_COUNT = 8
BW_FLASH_COLOR_FRAMES = 2
BW_FLASH_GREY_FRAMES = 3


def bw_screen_flash(screen: Surface, config) -> None:
    """Flash the screen between color and greyscale, as NES BWScreenFlash does."""
    if config['NO_BLIT']:
        return
    for _ in range(BW_FLASH_COUNT):
        wait_frames(BW_FLASH_COLOR_FRAMES, config)
        greyscale_screen(screen, config, frames=BW_FLASH_GREY_FRAMES)


def greyscale_screen(screen: Surface, config: dict, frames: int = 30) -> None:
    """Show the screen in greyscale for the given number of frames, then restore it
    (the NES does this by setting the greyscale bit of PPUControl1)."""
    if config['NO_BLIT']:
        return
    original = screen.copy()
    screen.blit(transform.grayscale(original), (0, 0))
    display.flip()
    wait_frames(frames, config)
    screen.blit(original, (0, 0))
    display.flip()


# ---------------------------------------------------------------------------------------------------- #
#  NES palette effects used in battle (issue #96)                                                       #
# ---------------------------------------------------------------------------------------------------- #

# The NES master palette, indexed by NES color number ($00-$3F). These are the RGB values the game's images use.
NES_PALETTE: tuple[tuple[int, int, int], ...] = (
    (116, 116, 116), (36, 24, 140), (0, 0, 168), (68, 0, 156), (140, 0, 116), (168, 0, 16), (164, 0, 0),
    (124, 8, 0), (64, 44, 0), (0, 68, 0), (0, 80, 0), (0, 60, 20), (24, 60, 92), (0, 0, 0), (0, 0, 0), (0, 0, 0),
    (188, 188, 188), (0, 112, 236), (32, 56, 236), (128, 0, 240), (188, 0, 188), (228, 0, 88), (216, 40, 0),
    (200, 76, 12), (136, 112, 0), (0, 148, 0), (0, 168, 0), (0, 144, 56), (0, 128, 136), (0, 0, 0), (0, 0, 0),
    (0, 0, 0),
    (252, 252, 252), (60, 188, 252), (92, 148, 252), (204, 136, 252), (244, 120, 252), (252, 116, 180),
    (252, 116, 96), (252, 152, 56), (240, 188, 60), (128, 208, 16), (76, 220, 72), (88, 248, 152), (0, 232, 216),
    (120, 120, 120), (0, 0, 0), (0, 0, 0),
    (252, 252, 252), (168, 228, 252), (196, 212, 252), (212, 200, 252), (252, 196, 252), (252, 196, 216),
    (252, 188, 176), (252, 216, 168), (252, 228, 160), (224, 252, 160), (168, 240, 188), (176, 252, 204),
    (156, 252, 240), (196, 196, 196), (0, 0, 0), (0, 0, 0),
)
PAL_BLACK = 0x0F
NES_RED = NES_PALETTE[0x16]  # RedFlashPal (Bank00): every color is $16

# NES PalFadeIn (Bank03, $C529) walks PalModByte through $30, $20, $10, $00, waiting 4 frames before each step.
# AddPalByte subtracts PalModByte from every palette color, and a color that drops below $00 becomes black.
FADE_IN_STEPS = (0x30, 0x20, 0x10, 0x00)
FADE_STEP_FRAMES = 4
FADE_FULL_BLACK = 0x40  # anything $40 or more turns every color black


def _build_color_lookup() -> dict[tuple[int, int, int], int]:
    lookup: dict[tuple[int, int, int], int] = {}
    for index, rgb in enumerate(NES_PALETTE):
        lookup.setdefault(rgb, index)
    # White is both $20 and $30; the enemy palettes use $30 (EnSPPals, RegSPPal).
    lookup[NES_PALETTE[0x30]] = 0x30
    lookup[NES_PALETTE[PAL_BLACK]] = PAL_BLACK
    return lookup


_NES_COLOR_LOOKUP = _build_color_lookup()


def nes_color_index(rgb) -> int:
    """The NES color number for an RGB color, picking the nearest palette entry for colors not in the palette."""
    rgb = tuple(rgb[:3])
    if rgb in _NES_COLOR_LOOKUP:
        return _NES_COLOR_LOOKUP[rgb]
    return min(_NES_COLOR_LOOKUP.items(),
               key=lambda item: sum((a - b) ** 2 for a, b in zip(item[0], rgb)))[1]


def nes_faded_color(rgb, darkening: int) -> tuple[int, int, int]:
    """NES AddPalByte/ChkPalFade ($C680): subtract ``darkening`` (NES PalModByte, $10 per brightness row) from the
    color number; below $00 is black."""
    index = nes_color_index(rgb) - darkening
    return NES_PALETTE[PAL_BLACK] if index < 0 else NES_PALETTE[index]


def fade_surface(surface: Surface, darkening: int) -> Surface:
    """A copy of a sprite with every opaque pixel's NES color darkened by ``darkening`` (NES PalModByte, $10 per
    brightness row)."""
    faded = surface.copy()
    if darkening == 0:
        return faded
    colors: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    for x in range(faded.get_width()):
        for y in range(faded.get_height()):
            r, g, b, a = faded.get_at((x, y))
            if a:
                rgb = (r, g, b)
                if rgb not in colors:
                    colors[rgb] = nes_faded_color(rgb, darkening)
                faded.set_at((x, y), (*colors[rgb], a))
    return faded


def silhouette_surface(surface: Surface, color, keep_black: bool = False) -> Surface:
    """A copy of a sprite with every opaque pixel set to one color (NES RedFlashPal sets all 12 colors to $16).
    With keep_black, black pixels stay black, the way palette color 0 does when a background palette is swapped."""
    shape = mask.from_surface(surface)
    if keep_black:
        shape.erase(mask.from_threshold(surface, (0, 0, 0, 255), (1, 1, 1, 255)), (0, 0))
    result = surface.copy()
    result.blit(shape.to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0)), (0, 0))
    return result


def red_flash_overlay(screen: Surface) -> Surface:
    """NES RedFlashScreen ($EE14) loads RedFlashPal into the background palettes: colors 1-3 of every background
    palette become red ($16) and color 0, the universal black, stays black. Returns that overlay for the screen."""
    not_black = mask.from_threshold(screen, (0, 0, 0, 255), (1, 1, 1, 255))
    not_black.invert()
    return not_black.to_surface(setcolor=NES_RED, unsetcolor=(0, 0, 0, 0))


# ---------------------------------------------------------------------------------------------------- #
#  Full-screen NES palette fades (PalFadeOut / PalFadeIn)                                               #
# ---------------------------------------------------------------------------------------------------- #

# NES PalFadeOut (Bank03, $C212) starts PalModByte at $00 and adds $10 until it reaches $50: it waits 4 frames, then
# loads both palettes darkened by PalModByte, five times ($00, $10, $20, $30, $40), 20 frames in all. The first load
# ($00) changes nothing, and the last ($40) turns every color black.
FADE_OUT_STEPS = (0x00, 0x10, 0x20, 0x30, FADE_FULL_BLACK)

FADE_STYLE_NES = 'NES'
FADE_STYLE_SMOOTH = 'Smooth'  # the black overlay alpha fade (fade()): a modern option, not NES behavior
FADE_STYLES = (FADE_STYLE_NES, FADE_STYLE_SMOOTH)

_NEAREST_NES_COLOR: dict[tuple[int, int, int], int] = {}


def nearest_nes_color_index(rgb) -> int:
    """nes_color_index, cached: a screen has few colors, but a fade looks each one up for every step."""
    rgb = tuple(rgb[:3])
    if rgb not in _NEAREST_NES_COLOR:
        _NEAREST_NES_COLOR[rgb] = nes_color_index(rgb)
    return _NEAREST_NES_COLOR[rgb]


def nes_fade_palette(darkening: int) -> list[tuple[int, int, int]]:
    """The 64 NES colors after AddPalByte/ChkPalFade ($C680) subtracts ``darkening`` (NES PalModByte) from each color
    number: entry n is the color n becomes, black if n - darkening is below $00."""
    return [NES_PALETTE[index - darkening] if index >= darkening else NES_PALETTE[PAL_BLACK]
            for index in range(len(NES_PALETTE))]


def nes_indexed_surface(surface: Surface) -> Surface:
    """An 8-bit copy of surface whose pixel values are NES color numbers ($00-$3F), so that a fade step is only a
    set_palette (nes_fade_palette) and one blit. Every color the game draws comes from the NES palette (white is $30,
    as in every NES palette the fades load, and black is $0F); any other color, such as one in a screenshot or an
    anti-aliased font, gets the nearest NES color, so it fades like that color."""
    width, height = surface.get_size()
    pixels = array('I')
    pixels.frombytes(image.tobytes(surface, 'RGBX'))
    color_numbers = {value: nearest_nes_color_index(value.to_bytes(4, sys.byteorder)) for value in set(pixels)}
    indexed = image.frombytes(bytes(map(color_numbers.__getitem__, pixels)), (width, height), 'P')
    indexed.set_palette(nes_fade_palette(0))
    return indexed


def fade_style(config) -> str:
    """The configured fade (FADE_STYLE): 'NES', the default, or 'Smooth'."""
    return FADE_STYLE_SMOOTH if config.get('FADE_STYLE') == FADE_STYLE_SMOOTH else FADE_STYLE_NES


def nes_palette_fade(fade_out: bool, screen: Surface, config) -> None:
    """Fade the whole screen the NES way, background and sprites together (both palettes are loaded at each step).

    Fading out (PalFadeOut, $C212), the screen as it is now goes through PalModByte $00, $10, $20, $30 and $40 (all
    black), 4 frames before each: 20 frames. Fading in (PalFadeIn, $C529), the screen as it is now is the picture to
    fade in to: it starts black (the palettes are black, from BlackPal or the last fade out) and goes through $30,
    $20, $10 and $00, 4 frames before each: 16 frames. Each color number has PalModByte subtracted from it, so a
    color drops one brightness row ($10) per step, white ($30) through $20 and light grey ($10) to dark grey ($00),
    and anything that goes below $00 is black; black ($0F) stays black.

    The waits go through src.waiting, so they follow the game speed and NO_WAIT. Building the color number surface
    takes about 15 ms at scale 2 and is done during the first 4-frame wait; each step after that is a set_palette and
    one blit (well under 1 ms)."""
    steps = FADE_OUT_STEPS if fade_out else FADE_IN_STEPS
    if config.get('NO_BLIT'):
        for _ in steps:
            wait_frames(FADE_STEP_FRAMES, config)
        return
    picture = screen.copy()
    if not fade_out:
        screen.fill(BLACK)
        display.flip()
    started = get_ticks()
    indexed = nes_indexed_surface(picture)
    first_wait = max(0.0, FADE_STEP_FRAMES * 1000 / NES_FPS - (get_ticks() - started))
    for step, darkening in enumerate(steps):
        if step == 0:
            wait(first_wait, config)
        else:
            wait_frames(FADE_STEP_FRAMES, config)
        if darkening == 0:
            screen.blit(picture, (0, 0))  # the colors exactly as they were, even ones that aren't NES colors
        else:
            indexed.set_palette(nes_fade_palette(darkening))
            screen.blit(indexed, (0, 0))
        display.flip()


def screen_fade(fade_out: bool, screen: Surface, config, draw_callback=None) -> None:
    """Fade the screen to black (fade_out) or from black to what is on it now, the way FADE_STYLE says: 'NES' (the
    default) is the NES palette fade (nes_palette_fade), 'Smooth' the black overlay alpha fade (fade). Every
    transition that the NES does with PalFadeOut or PalFadeIn calls this, so they all follow the option."""
    if fade_style(config) == FADE_STYLE_SMOOTH:
        fade(fade_out=fade_out, screen=screen, config=config, draw_callback=draw_callback)
    else:
        nes_palette_fade(fade_out, screen, config)


def cut_to_black(screen: Surface, config) -> None:
    """The screen going black at once, as when the NES loads BlackPal without fading (StartAtThroneRoom, LCB47)."""
    if not config.get('NO_BLIT'):
        screen.fill(BLACK)
        display.flip()


def show_frames(frames: int, config) -> None:
    """Show the current screen for a number of NES frames (NES_FPS, 60.0988 a second)."""
    display.flip()
    wait(round(frames * 1000 / NES_FPS), config)


def enemy_fade_in(screen: Surface, image: Surface, position, config, repeats: int = 2) -> None:
    """The enemy appearing: NES LoadEnemyGFX ($E44F) loads the enemy's sprite palette, then calls PalFadeIn twice.
    Only the sprite palettes fade (LoadBGPal shares RAM with EnSprtXPos, which is cleared to 0, PAL_SKIP_BG, just
    before), so the enemy alone goes from a black shadow through $30/$20/$10/$00 darker palettes, then does it
    again: 4 frames per step, 36 frames in all. The first load uses the PalModByte left by the last fade in
    ($F0, all black). The final form's DoEndFight runs PalFadeIn four times (repeats=4)."""
    if config.get('NO_BLIT'):
        return
    steps = [(FADE_FULL_BLACK, FADE_STEP_FRAMES)] + [(step, FADE_STEP_FRAMES) for step in FADE_IN_STEPS] * repeats
    faded: dict[int, Surface] = {}
    for darkening, frames in steps:
        if darkening not in faded:
            faded[darkening] = fade_surface(image, darkening)
        screen.blit(faded[darkening], position)
        show_frames(frames, config)
    screen.blit(image, position)
    display.flip()


# NES ChkDrop (LDEC5-LDEFB), the rainbow bridge: BridgeFlashCntr = 4 cycles of PPUDataByte from $21 up to $2C (the
# CMP #$2D ends a cycle), then $11, the color it was, after which the CMP #$12 ends the animation. Before each write
# BuildBridgeLoop1 waits 5 frames (WaitForNMI x5), and AddPPUBufEntry puts it in background palette 0, color 3
# ($3F03), the overworld's $11 blue (OverworldPal) that the water, shore, town, castle and bridge blocks use (block
# palette 0 in GFXTilesTbl). 49 colors, 245 frames, while MSC_RNBW_BRDG plays.
RAINBOW_FLASH_CYCLES = 4
RAINBOW_FLASH_FIRST_COLOR = 0x21
RAINBOW_FLASH_END_COLOR = 0x2D  # not shown: the cycle ends when PPUDataByte reaches it
RAINBOW_FLASH_WATER_COLOR = 0x11  # OverworldPal's palette 0 color 3, and the last color written
RAINBOW_FLASH_FRAMES = 5


def rainbow_flash_colors() -> list[int]:
    """The colors ChkDrop writes to $3F03, in order: $21-$2C four times, then $11."""
    cycle = list(range(RAINBOW_FLASH_FIRST_COLOR, RAINBOW_FLASH_END_COLOR))
    return cycle * RAINBOW_FLASH_CYCLES + [RAINBOW_FLASH_WATER_COLOR]


def rainbow_bridge_flash(screen: Surface, config) -> None:
    """NES ChkDrop's rainbow flash: every pixel in the water blue ($11) takes each color of rainbow_flash_colors in
    turn, RAINBOW_FLASH_FRAMES frames before each, the way rewriting palette entry $3F03 recolors it. The hero's
    sprite palette (RegSPPal) has no $11, so only the map's blue changes; the last color is $11 itself, so the screen
    ends as it was."""
    if config.get('NO_BLIT'):
        return
    original = screen.copy()
    water = mask.from_threshold(original, (*NES_PALETTE[RAINBOW_FLASH_WATER_COLOR], 255), (1, 1, 1, 255))
    overlays: dict[int, Surface] = {}
    for color in rainbow_flash_colors():
        wait_frames(RAINBOW_FLASH_FRAMES, config)
        screen.blit(original, (0, 0))
        if color != RAINBOW_FLASH_WATER_COLOR:
            if color not in overlays:
                overlays[color] = water.to_surface(setcolor=NES_PALETTE[color], unsetcolor=(0, 0, 0, 0))
            screen.blit(overlays[color], (0, 0))
        display.flip()
        check_for_quit()


# NES PaletteFlash ($EF38): 5 times, wait 3 frames, load the red flash sprite palette, wait 2 frames, reload the
# enemy palette (LoadEnPalette). Palette writes land on the next NMI, so the enemy is red 2 frames out of every 5.
ENEMY_FLASH_COUNT = 5
ENEMY_FLASH_NORMAL_FRAMES = 3
ENEMY_FLASH_RED_FRAMES = 2


# SplFlshBGPal (Bank00, $9A97): every color is $10. Despite its name, PaletteFlash loads it as the sprite palette
# when an enemy casts a spell (EnCastSpell, LEC03-LEC0D), so the enemy flashes grey.
NES_SPELL_FLASH_GREY = NES_PALETTE[0x10]


def enemy_palette_flash(screen: Surface, image: Surface, position, config, color, keep_black: bool = False) -> None:
    """NES PaletteFlash ($EF38): the enemy flashes in one color, ENEMY_FLASH_COUNT times."""
    if config.get('NO_BLIT'):
        return
    flash = silhouette_surface(image, color, keep_black=keep_black)
    for _ in range(ENEMY_FLASH_COUNT):
        screen.blit(image, position)
        show_frames(ENEMY_FLASH_NORMAL_FRAMES, config)
        screen.blit(flash, position)
        show_frames(ENEMY_FLASH_RED_FRAMES, config)
    screen.blit(image, position)
    display.flip()


def enemy_hit_flash(screen: Surface, image: Surface, position, config, keep_black: bool = False) -> None:
    """The enemy flashing red when the hero hits it (NES PlyrHitEn -> PaletteFlash with RedFlashPalPtr).
    For the final form, which is drawn with background tiles, PaletteFlash swaps in FinalRedBGPal instead, which
    leaves the universal black alone (keep_black=True)."""
    enemy_palette_flash(screen, image, position, config, NES_RED, keep_black=keep_black)


def enemy_spell_flash(screen: Surface, image: Surface, position, config) -> None:
    """The enemy flashing grey as it casts a spell (NES EnCastSpell -> PaletteFlash with SplFlshBGPalPtr)."""
    enemy_palette_flash(screen, image, position, config, NES_SPELL_FLASH_GREY)


# NES PlayerHit ($ED20): ShakeCounter starts at 8. Each pass waits a frame (two if the hero is still alive),
# moves ScrollX (even counter) or ScrollY (odd counter) 2 pixels, waits a frame, reloads the background palette
# (LoadRegBGPal waits another frame) and puts the scroll back. So the screen is moved 2 frames out of 4.
SHAKE_COUNT = 8
SHAKE_PIXELS = 2
SHAKE_STILL_FRAMES = 2
SHAKE_MOVED_FRAMES = 2


def player_hit_shake(screen: Surface, config, deathblow: bool = False, enemy=None, background=None,
                     shake: bool = True) -> None:
    """The screen shake when an enemy hurts the hero, with the red background flash (RedFlashScreen) on the
    blow that kills him. Sprites don't scroll on the NES, so the enemy stays put and isn't tinted red:
    enemy is (image, position) and background is (battle background image, position), used to draw what is
    behind the enemy. The final form doesn't shake or flash (shake=False), but the frames still pass: 4 a pass,
    or 3 on the deathblow, which skips the extra wait."""
    scale = config.get('SCALE', 1)
    if config.get('NO_BLIT') or not shake:
        # On the final form's deathblow, the second wait and RedFlashScreen's wait are both skipped.
        still_frames = SHAKE_STILL_FRAMES - 1 if deathblow and not shake else SHAKE_STILL_FRAMES
        wait(round(SHAKE_COUNT * (still_frames + SHAKE_MOVED_FRAMES) * 1000 / NES_FPS), config)
        return
    original = screen.copy()
    without_enemy = original.copy()
    if enemy is not None and background is not None:
        enemy_image, enemy_position = enemy
        background_image, background_position = background
        enemy_rect = enemy_image.get_rect(topleft=enemy_position)
        area = enemy_rect.move(-background_position[0], -background_position[1])
        without_enemy.blit(background_image, enemy_rect.topleft, area=area)
    for shake_number in range(SHAKE_COUNT):
        show_frames(SHAKE_STILL_FRAMES, config)
        offset = SHAKE_PIXELS * scale
        # ShakeCounter counts down from 8 and moves ScrollX on even counts, so the shakes alternate horizontal and
        # vertical, starting horizontal. Scrolling right/down moves the picture left/up.
        horizontal = shake_number % 2 == 0
        shift = (-offset, 0) if horizontal else (0, -offset)
        screen.blit(without_enemy, shift)
        if deathblow:
            screen.blit(red_flash_overlay(screen), (0, 0))
        if enemy is not None:
            screen.blit(enemy[0], enemy[1])
        show_frames(SHAKE_MOVED_FRAMES, config)
        screen.blit(original, (0, 0))
    display.flip()
