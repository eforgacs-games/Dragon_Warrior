import locale
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
FULLSCREEN_ENABLED = False
DEV_MODE = False
ENABLE_DARKNESS = True
MUSIC_ENABLED = False if DEV_MODE else True
SOUND_ENABLED = False if DEV_MODE else True
SPLASH_SCREEN_ENABLED = False if DEV_MODE else True
INITIAL_DIALOG_ENABLED = False if DEV_MODE else True
ORCHESTRA_MUSIC_ENABLED = False
SHOW_FPS = False
LOCALE, CHARACTER_ENCODING = locale.getlocale()
LANGUAGE = LOCALE.split("_")[0]
# This prints out the current coordinates that the player is standing on.
SHOW_COORDINATES = False
COLOR_KEY = (0, 128, 128)
TEXT_SPEED = "Fast"
