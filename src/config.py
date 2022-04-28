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
MUSIC_ENABLED = True
SOUND_ENABLED = True
ORCHESTRA_MUSIC_ENABLED = False
FULLSCREEN_ENABLED = False
SHOW_FPS = False
COLOR_KEY = (0, 128, 128)
TEXT_SPEED = "Fast"
