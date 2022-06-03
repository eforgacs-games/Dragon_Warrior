from os.path import join, realpath, dirname

FPS = 60
REPLIT_DATA_DIR = '..\\data'
DATA_DIR = join(dirname(dirname(realpath(__file__))), 'data')
FONTS_DIR = join(DATA_DIR, 'fonts')
IMAGES_DIR = join(DATA_DIR, 'images')
SOUND_DIR = join(DATA_DIR, 'sound')

MUSIC_DIR = join(SOUND_DIR, 'music')
SFX_DIR = join(SOUND_DIR, 'sfx')

SCALE = 2
TILE_SIZE = 16 * SCALE
NES_RES = (256, 240)
DEV_MODE = False
if DEV_MODE:
    MUSIC_ENABLED = False  # lgtm [py/unreachable-statement]
    SOUND_ENABLED = False
    ORCHESTRA_MUSIC_ENABLED = False
    FULLSCREEN_ENABLED = False
    SPLASH_SCREEN_ENABLED = False
    INITIAL_DIALOG_ENABLED = False
else:
    MUSIC_ENABLED = True
    SOUND_ENABLED = True
    ORCHESTRA_MUSIC_ENABLED = False
    FULLSCREEN_ENABLED = False
    SPLASH_SCREEN_ENABLED = True
    INITIAL_DIALOG_ENABLED = True
ORCHESTRA_MUSIC_ENABLED = True
SHOW_FPS = False
# This prints out the current coordinates that the player is standing on.
SHOW_COORDINATES = False
COLOR_KEY = (0, 128, 128)
TEXT_SPEED = "Fast"
