# Constants
import ntpath
import os
import time
from enum import IntEnum
from os.path import join, sep, exists

from pygame import Surface, image, transform, mixer, font
from pygame.time import get_ticks

from src.config import SFX_DIR, MUSIC_ENABLED, ORCHESTRA_MUSIC_ENABLED, MUSIC_DIR, IMAGES_DIR, FONTS_DIR, TEXT_SPEED, SOUND_ENABLED, FPS, TILE_SIZE


class Direction(IntEnum):
    DOWN = 0
    LEFT = 1
    UP = 2
    RIGHT = 3


# Files/Directories
root_project_path = os.getcwd().split('DragonWarrior', 1)[0]


def find_file(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)


def retrieve_audio_resource(_sound_library, path, sound):
    if sound is None:
        canonicalized_path = path.replace('/', sep).replace('\\', sep)
        sound = mixer.Sound(canonicalized_path)
        _sound_library[path] = sound
    return sound


# Sound

_sound_library = {}

# menu
text_beep_sfx = join(SFX_DIR, 'text_beep.wav')
special_item_sfx = join(SFX_DIR, '21 Dragon Quest 1 - Special Item.mp3')
stairs_up_sfx = join(SFX_DIR, '29 Dragon Quest 1 - Stairs Up.mp3')
stairs_down_sfx = join(SFX_DIR, '30 Dragon Quest 1 - Stairs Down.mp3')
menu_button_sfx = join(SFX_DIR, '32 Dragon Quest 1 - Menu Button.mp3')
confirmation_sfx = join(SFX_DIR, '33 Dragon Quest 1 - Confirmation.mp3')
# movement

bump_sfx = join(SFX_DIR, '42 Dragon Quest 1 - Bumping into Walls.mp3')
open_treasure_sfx = join(SFX_DIR, '44 Dragon Quest 1 - Open Treasure.mp3')


def play_sound(path='data/sound/sfx'):
    if SOUND_ENABLED:
        global _sound_library
        sound = _sound_library.get(path)
        sound = retrieve_audio_resource(_sound_library, path, sound)
        sound.play()


# Music

_music_library = {}
if ORCHESTRA_MUSIC_ENABLED:
    intro_overture = join(MUSIC_DIR, 'orchestra', '01 Overture March (London Philharmonic Orchestra Version).mp3')
    tantegel_castle_throne_room_music = join(MUSIC_DIR, 'orchestra', '02 Chateau Ladutorm.mp3')
    tantegel_castle_courtyard_music = join(MUSIC_DIR, 'orchestra', '02 Chateau Ladutorm.mp3')
    village_music = join(MUSIC_DIR, 'orchestra', '03 People.mp3')
    overworld_music = join(MUSIC_DIR, 'orchestra', '04 Unknown World.mp3')
    dungeon_floor_1_music = \
        dungeon_floor_2_music = \
        dungeon_floor_3_music = \
        dungeon_floor_4_music = \
        dungeon_floor_5_music = \
        dungeon_floor_6_music = \
        dungeon_floor_7_music = \
        dungeon_floor_8_music = join(MUSIC_DIR, 'orchestra', '06 Dungeon.mp3')
else:
    intro_overture = join(MUSIC_DIR, 'NES', '01 Dragon Quest 1 - Intro ~ Overture.mp3')
    tantegel_castle_throne_room_music = join(MUSIC_DIR, 'NES', '02 Dragon Quest 1 - Tantegel Castle.mp3')
    tantegel_castle_courtyard_music = join(MUSIC_DIR, 'NES', '03 Dragon Quest 1 - Tantegel Castle (Lower).mp3')
    village_music = join(MUSIC_DIR, 'NES', '04 Dragon Quest 1 - Peaceful Village.mp3')
    overworld_music = join(MUSIC_DIR, 'NES', '05 Dragon Quest 1 - Kingdom of Alefgard.mp3')
    dungeon_floor_1_music = join(MUSIC_DIR, 'NES', '06 Dragon Quest 1 - Dark Dungeon ~ Floor 1.mp3')
    dungeon_floor_2_music = join(MUSIC_DIR, 'NES', '07 Dragon Quest 1 - Dark Dungeon ~ Floor 2.mp3')
    dungeon_floor_3_music = join(MUSIC_DIR, 'NES', '08 Dragon Quest 1 - Dark Dungeon ~ Floor 3.mp3')
    dungeon_floor_4_music = join(MUSIC_DIR, 'NES', '09 Dragon Quest 1 - Dark Dungeon ~ Floor 4.mp3')
    dungeon_floor_5_music = join(MUSIC_DIR, 'NES', '10 Dragon Quest 1 - Dark Dungeon ~ Floor 5.mp3')
    dungeon_floor_6_music = join(MUSIC_DIR, 'NES', '11 Dragon Quest 1 - Dark Dungeon ~ Floor 6.mp3')
    dungeon_floor_7_music = join(MUSIC_DIR, 'NES', '12 Dragon Quest 1 - Dark Dungeon ~ Floor 7.mp3')
    dungeon_floor_8_music = join(MUSIC_DIR, 'NES', '13 Dragon Quest 1 - Dark Dungeon ~ Floor 8.mp3')


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
ICON_PATH = join(IMAGES_DIR, 'walking_hero.gif')

# menus/windows

DIALOG_BOX_BACKGROUND_PATH = join(IMAGES_DIR, 'dialog_box_background.png')
COMMAND_MENU_BACKGROUND_PATH = join(IMAGES_DIR, 'command_menu_background.png')
COMMAND_MENU_STATIC_BACKGROUND_PATH = join(IMAGES_DIR, 'command_menu_static.png')
CONFIRMATION_BACKGROUND_PATH = join(IMAGES_DIR, 'confirmation.png')
CONFIRMATION_YES_BACKGROUND_PATH = join(IMAGES_DIR, 'confirmation_yes.png')
CONFIRMATION_NO_BACKGROUND_PATH = join(IMAGES_DIR, 'confirmation_no.png')
HOVERING_STATS_BACKGROUND_PATH = join(IMAGES_DIR, 'hovering_stats_window.png')
BEGIN_QUEST_PATH = join(IMAGES_DIR, 'begin_quest.png')
BEGIN_QUEST_SELECTED_PATH = join(IMAGES_DIR, 'begin_quest_selected.png')

# shops

IMAGES_SHOPS_DIR = join(IMAGES_DIR, 'shops')
IMAGES_SHOPS_BRECCONARY_PATH = join(IMAGES_SHOPS_DIR, 'brecconary')
IMAGES_SHOPS_BRECCONARY_WEAPONS_PATH = join(IMAGES_SHOPS_BRECCONARY_PATH, 'weapons')
BRECCONARY_WEAPONS_SHOP_PATH = join(IMAGES_SHOPS_BRECCONARY_WEAPONS_PATH, 'brecconary_shop.png')
BRECCONARY_WEAPONS_SHOP_BAMBOO_POLE_PATH = join(IMAGES_SHOPS_BRECCONARY_WEAPONS_PATH, 'brecconary_shop_bamboo_pole.png')
BRECCONARY_WEAPONS_SHOP_CLUB_PATH = join(IMAGES_SHOPS_BRECCONARY_WEAPONS_PATH, 'brecconary_shop_club.png')
BRECCONARY_WEAPONS_SHOP_COPPER_SWORD_PATH = join(IMAGES_SHOPS_BRECCONARY_WEAPONS_PATH, 'brecconary_shop_copper_sword.png')
BRECCONARY_WEAPONS_SHOP_CLOTHES_PATH = join(IMAGES_SHOPS_BRECCONARY_WEAPONS_PATH, 'brecconary_shop_clothes.png')
BRECCONARY_WEAPONS_SHOP_LEATHER_ARMOR_PATH = join(IMAGES_SHOPS_BRECCONARY_WEAPONS_PATH, 'brecconary_shop_leather_armor.png')
BRECCONARY_WEAPONS_SHOP_SMALL_SHIELD_PATH = join(IMAGES_SHOPS_BRECCONARY_WEAPONS_PATH, 'brecconary_shop_small_shield.png')


def get_image(path):
    global _image_library
    image_to_load = _image_library.get(path)
    if image_to_load is None:
        canonicalized_path = path.replace('/', sep).replace('\\', sep)
        if exists(canonicalized_path):
            image_to_load = image.load(canonicalized_path).convert_alpha()
            _image_library[path] = image_to_load
        else:
            image_to_load = image.load(find_file(ntpath.basename(canonicalized_path), root_project_path)).convert_alpha()
            _image_library[path] = image_to_load
    return image_to_load


# Fonts

font.init()
DRAGON_QUEST_FONT_PATH = join(FONTS_DIR, 'dragon-quest.ttf')
if exists(DRAGON_QUEST_FONT_PATH):
    DRAGON_QUEST_FONT = font.Font(DRAGON_QUEST_FONT_PATH, 15)
else:
    DRAGON_QUEST_FONT = font.Font(find_file('dragon-quest.ttf', root_project_path), 15)

SMB_FONT_PATH = join(FONTS_DIR, 'super_mario_bros__nes_font.ttf')
SMB_FONT = font.Font(SMB_FONT_PATH, 15)


# Characters


def is_facing_down(character):
    return character.direction_value == Direction.DOWN.value


def is_facing_up(character):
    return character.direction_value == Direction.UP.value


def is_facing_right(character):
    return character.direction_value == Direction.RIGHT.value


def is_facing_left(character):
    return character.direction_value == Direction.LEFT.value


def is_facing_medially(character):
    return is_facing_up(character) or is_facing_down(character)


def is_facing_laterally(character):
    return is_facing_left(character) or is_facing_right(character)


# Maps


def get_tile_id_by_coordinates(column: int, row: int, game_map) -> str:
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
    # TODO(ELF): change FPS to be self.fps (the actual FPS setting if it is changed to double/triple/quadruple etc. speed).
    return FPS * time_to_convert / 1000


def convert_to_milliseconds(fps_to_convert):
    # TODO(ELF): change FPS to be self.fps (the actual FPS setting if it is changed to double/triple/quadruple etc. speed).
    return fps_to_convert / FPS * 1000


def get_surrounding_tile_values(coordinates, map_layout):
    x = coordinates[0]
    y = coordinates[1]
    try:
        left = map_layout[x - 1][y] if x - 1 >= 0 else None
    except IndexError:
        left = None
    try:
        down = map_layout[x][y - 1] if y - 1 >= 0 else None
    except IndexError:
        down = None
    try:
        right = map_layout[x][y + 1]
    except IndexError:
        right = None
    try:
        up = map_layout[x + 1][y]
    except IndexError:
        up = None
    neighbors = [x for x in [left, down, right, up] if x is not None]
    return set(neighbors + [map_layout[x][y]])


def get_next_tile_identifier(character_column: int, character_row: int, direction_value: int, current_map, offset: int = 1) -> str:
    """
    Retrieve the identifier (human-readable name) of the next tile in front of a particular character.
    :type character_column: int
    :type character_row: int
    :param character_column: The character's column within the map layout.
    :param character_row: The character's row within the map layout.
    :param direction_value: The direction which the character is facing.
    :param current_map: The current map class.
    :param offset: How many tiles offset of the character to check. Defaults to 1 (the next tile).
    :return: str: The next tile that the character will step on (e.g., 'BRICK').
    """
    if direction_value == Direction.UP.value:
        return get_tile_id_by_coordinates(character_column, character_row - offset, current_map)
    elif direction_value == Direction.DOWN.value:
        return get_tile_id_by_coordinates(character_column, character_row + offset, current_map)
    elif direction_value == Direction.LEFT.value:
        return get_tile_id_by_coordinates(character_column - offset, character_row, current_map)
    elif direction_value == Direction.RIGHT.value:
        return get_tile_id_by_coordinates(character_column + offset, character_row, current_map)


def convert_to_frames_since_start_time(start_time):
    return convert_to_frames(get_ticks() - start_time)


def create_window(x, y, width, height, window_background, screen):
    window_box = Surface((TILE_SIZE * width, TILE_SIZE * height))  # lgtm [py/call/wrong-arguments]
    set_window_background(window_box, window_background)
    screen.blit(window_box, (TILE_SIZE * x, TILE_SIZE * y))
    return window_box


def set_window_background(black_box, background_path):
    black_box.fill(BLACK)
    background_image = image.load(background_path)
    background_image = transform.scale(background_image, black_box.get_size())
    black_box.blit(background_image, black_box.get_rect())
