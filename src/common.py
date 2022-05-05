# Constants
import ntpath
import os
import time
from enum import IntEnum
from os.path import join, sep, exists

import pygame

from src.config import SFX_DIR, SOUND_ENABLED, MUSIC_ENABLED, ORCHESTRA_MUSIC_ENABLED, MUSIC_DIR, IMAGES_DIR, FONTS_DIR, TEXT_SPEED


class Direction(IntEnum):
    DOWN = 0
    LEFT = 1
    UP = 2
    RIGHT = 3


def get_opposite_direction(direction: int) -> int:
    if direction >= 2:
        return direction - 2
    else:
        return direction + 2


# Files/Directories
root_project_path = os.getcwd().split('DragonWarrior', 1)[0]


def find_file(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)


def retrieve_audio_resource(_sound_library, path, sound):
    if sound is None:
        canonicalized_path = path.replace('/', sep).replace('\\', sep)
        sound = pygame.mixer.Sound(canonicalized_path)
        _sound_library[path] = sound
    return sound


# Sound

_sound_library = {}

# menu
menu_button_sfx = join(SFX_DIR, '32 Dragon Quest 1 - Menu Button (22khz mono).wav')
text_beep_sfx = join(SFX_DIR, 'text_beep.wav')
# movement
bump_sfx = join(SFX_DIR, '42 Dragon Quest 1 - Bumping into Walls (22khz mono).wav')
stairs_down_sfx = join(SFX_DIR, '30 Dragon Quest 1 - Stairs Down (22khz mono).wav')
stairs_up_sfx = join(SFX_DIR, '29 Dragon Quest 1 - Stairs Up (22khz mono).wav')


def play_sound(path='data/sound/sfx'):
    if SOUND_ENABLED:
        global _sound_library
        sound = _sound_library.get(path)
        sound = retrieve_audio_resource(_sound_library, path, sound)
        sound.play()


# Music

_music_library = {}
if ORCHESTRA_MUSIC_ENABLED:
    tantegel_castle_throne_room_music = join(MUSIC_DIR, 'orchestra', '02 Chateau Ladutorm.mp3')
    tantegel_castle_courtyard_music = join(MUSIC_DIR, 'orchestra', '02 Chateau Ladutorm.mp3')
    village_music = join(MUSIC_DIR, 'orchestra', '03 People.mp3')
    overworld_music = join(MUSIC_DIR, 'orchestra', '04 Unknown World.mp3')
else:
    intro_overture = join(MUSIC_DIR, 'NES', '01 Dragon Quest 1 - Intro ~ Overture (22khz mono).ogg')
    tantegel_castle_throne_room_music = join(MUSIC_DIR, 'NES', '02 Dragon Quest 1 - Tantegel Castle (22khz_mono).ogg')
    tantegel_castle_courtyard_music = join(MUSIC_DIR, 'NES', '03 Dragon Quest 1 - Tantegel Castle (Lower) (22khz mono).ogg')
    village_music = join(MUSIC_DIR, 'NES', '04 Dragon Quest 1 - Peaceful Village (22khz mono).ogg')
    overworld_music = join(MUSIC_DIR, 'NES', '05 Dragon Quest 1 - Kingdom of Alefgard (22khz mono).ogg')


def play_music(path='data/sound/music'):
    if MUSIC_ENABLED:
        global _music_library
        music = _music_library.get(path)
        music = retrieve_audio_resource(_music_library, path, music)
        music.play(-1)


# Images

BLACK, WHITE, RED, ORANGE, PINK = (0, 0, 0), (255, 255, 255), (255, 0, 0), (234, 158, 34), (243, 106, 255)
_image_library = {}
MAP_TILES_PATH = join(IMAGES_DIR, 'tileset.png')
UNARMED_HERO_PATH = join(IMAGES_DIR, 'unarmed_hero.png')
ARMED_HERO_PATH = join(IMAGES_DIR, 'armed_hero.png')
KING_LORIK_PATH = join(IMAGES_DIR, 'king_lorik.png')
GUARD_PATH = join(IMAGES_DIR, 'guard.png')
MAN_PATH = join(IMAGES_DIR, 'man.png')
WOMAN_PATH = join(IMAGES_DIR, 'woman.png')
WISE_MAN_PATH = join(IMAGES_DIR, 'wise_man.png')
SOLDIER_PATH = join(IMAGES_DIR, 'soldier.png')
MERCHANT_PATH = join(IMAGES_DIR, 'merchant.png')
PRINCESS_GWAELIN_PATH = join(IMAGES_DIR, 'princess_gwaelin.png')
DRAGONLORD_PATH = join(IMAGES_DIR, 'dragonlord.png')
INTRO_BANNER_PATH = join(IMAGES_DIR, 'intro_banner', 'intro_banner.png')
INTRO_BANNER_WITH_DRAGON_PATH = join(IMAGES_DIR, 'intro_banner', 'intro_banner_with_dragon.png')


def get_image(path):
    global _image_library
    image = _image_library.get(path)
    if image is None:
        canonicalized_path = path.replace('/', sep).replace('\\', sep)
        if exists(canonicalized_path):
            image = pygame.image.load(canonicalized_path).convert_alpha()
            _image_library[path] = image
        else:
            image = pygame.image.load(find_file(ntpath.basename(canonicalized_path), root_project_path)).convert_alpha()
            _image_library[path] = image
    return image


# Fonts

pygame.font.init()
DRAGON_QUEST_FONT_PATH = join(FONTS_DIR, 'dragon-quest.ttf')
if exists(DRAGON_QUEST_FONT_PATH):
    DRAGON_QUEST_FONT = pygame.font.Font(DRAGON_QUEST_FONT_PATH, 15)
else:
    DRAGON_QUEST_FONT = pygame.font.Font(find_file('dragon-quest.ttf', root_project_path), 15)

SMB_FONT_PATH = join(FONTS_DIR, 'super_mario_bros__nes_font.ttf')
SMB_FONT = pygame.font.Font(SMB_FONT_PATH, 15)



# Characters


def is_facing_down(character):
    return character.direction == Direction.DOWN.value


def is_facing_up(character):
    return character.direction == Direction.UP.value


def is_facing_right(character):
    return character.direction == Direction.RIGHT.value


def is_facing_left(character):
    return character.direction == Direction.LEFT.value


def is_facing_medially(character):
    return is_facing_up(character) or is_facing_down(character)


def is_facing_laterally(character):
    return is_facing_left(character) or is_facing_right(character)


# Maps


def get_tile_by_coordinates(column: int, row: int, game_map) -> str:
    """
    Retrieve the tile name from the coordinates of the tile on the map.
    :param column: The column of the tile.
    :param row: The row of the tile.
    @rtype: str
    """
    if row < len(game_map.layout) and column < len(game_map.layout[0]):
        return game_map.get_tile_by_value(game_map.layout[row][column])


def print_with_beep_sfx(string_to_print):
    match TEXT_SPEED:
        case "Slow":
            sleep_time = 0.03
        case "Medium":
            sleep_time = 0.02
        case "Fast":
            sleep_time = 0.01
        case _:
            sleep_time = 0
    for char in string_to_print:
        # prints in chunks, not one fluid print
        play_sound(text_beep_sfx)
        print(char, end='', flush=True)
        time.sleep(sleep_time)
        # pygame.time.wait(1)
    print("\n")


def convert_to_frames(time_to_convert):
    return 60 * (time_to_convert / 1000)


def convert_to_milliseconds(FPS):
    return int((FPS / 60) * 1000)


def get_surrounding_tiles(coordinates, map_layout, radius=1):
    x = coordinates[0]
    y = coordinates[1]
    neighbors = [
        map_layout[x - 1][y - 1],
        map_layout[x - 1][y],
        map_layout[x - 1][y + 1],

        map_layout[x][y - 1],
        map_layout[x][y + 1],

        map_layout[x + 1][y - 1],
        map_layout[x + 1][y],
        map_layout[x + 1][y + 1]
    ]
    if radius > 1:
        for i in range(2, radius):
            neighbors.append(map_layout[x - i][y - i])
            neighbors.append(map_layout[x - i][y])
            neighbors.append(map_layout[x - i][y + i])

            neighbors.append(map_layout[x][y - i])
            neighbors.append(map_layout[x][y + i])

            neighbors.append(map_layout[x + i][y - i])
            neighbors.append(map_layout[x + i][y])
            neighbors.append(map_layout[x + i][y + i])

    return neighbors
