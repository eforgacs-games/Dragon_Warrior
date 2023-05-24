# Constants
import ntpath
import os
from enum import IntEnum
from os.path import join, sep, exists

from pygame import Surface, image, transform, mixer, font, PixelArray
from pygame.time import get_ticks

from src.config import SFX_DIR, ORCHESTRA_MUSIC_ENABLED, MUSIC_DIR, IMAGES_DIR, FONTS_DIR, SOUND_ENABLED, FPS, TILE_SIZE


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
death_sfx = join(SFX_DIR, '20 Dragon Quest 1 - Thou Hast Died.mp3')
special_item_sfx = join(SFX_DIR, '21 Dragon Quest 1 - Special Item.mp3')
victory_sfx = join(SFX_DIR, '25 Dragon Quest 1 - Victory.mp3')
improvement_sfx = join(SFX_DIR, '26 Dragon Quest 1 - Improvement.mp3')
stairs_up_sfx = join(SFX_DIR, '29 Dragon Quest 1 - Stairs Up.mp3')
stairs_down_sfx = join(SFX_DIR, '30 Dragon Quest 1 - Stairs Down.mp3')
swamp_sfx = join(SFX_DIR, '31 Dragon Quest 1 - Swamp.mp3')
menu_button_sfx = join(SFX_DIR, '32 Dragon Quest 1 - Menu Button.mp3')
confirmation_sfx = join(SFX_DIR, '33 Dragon Quest 1 - Confirmation.mp3')
hit_sfx = join(SFX_DIR, '34 Dragon Quest 1 - Hit.mp3')
excellent_move_sfx = join(SFX_DIR, '35 Dragon Quest 1 - Excellent Move.mp3')
attack_sfx = join(SFX_DIR, '36 Dragon Quest 1 - Attack.mp3')
receive_damage_sfx = join(SFX_DIR, '37 Dragon Quest 1 - Receive Damage.mp3')
receive_damage_2_sfx = join(SFX_DIR, '38 Dragon Quest 1 - Receive Damage (2).mp3')
prepare_attack_sfx = join(SFX_DIR, '39 Dragon Quest 1 - Prepare to Attack.mp3')
missed_sfx = join(SFX_DIR, '40 Dragon Quest 1 - Missed!.mp3')
missed_2_sfx = join(SFX_DIR, '41 Dragon Quest 1 - Missed! (2).mp3')
spell_sfx = join(SFX_DIR, '43 Dragon Quest 1 - Cast A Spell.mp3')

# items

torch_sfx = join(SFX_DIR, 'torch.wav')

# movement

bump_sfx = join(SFX_DIR, '42 Dragon Quest 1 - Bumping into Walls.mp3')
open_treasure_sfx = join(SFX_DIR, '44 Dragon Quest 1 - Open Treasure.mp3')
open_door_sfx = join(SFX_DIR, '45 Dragon Quest 1 - Open Door.mp3')


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
    battle_music = join(MUSIC_DIR, 'orchestra', '05 Fight.mp3')
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
    battle_music = join(MUSIC_DIR, 'NES', '14 Dragon Quest 1 - A Monster Draws Near.mp3')

# Images

BLACK, WHITE, RED, ORANGE, PINK = (0, 0, 0), (255, 255, 255), (255, 0, 0), (234, 158, 34), (243, 106, 255)
_image_library = {}
MAP_TILES_PATH = join(IMAGES_DIR, 'tileset.png')
UNARMED_HERO_PATH = join(IMAGES_DIR, 'unarmed_hero.png')
UNARMED_HERO_WITH_SHIELD_PATH = join(IMAGES_DIR, 'unarmed_hero_with_shield.png')
ARMED_HERO_PATH = join(IMAGES_DIR, 'armed_hero.png')
ARMED_HERO_WITH_SHIELD_PATH = join(IMAGES_DIR, 'armed_hero_with_shield.png')
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
BATTLE_BACKGROUND_PATH = join(IMAGES_DIR, 'battle_background.png')
IMAGES_ENEMIES_DIR = join(IMAGES_DIR, 'enemies')

# menus/windows

DIALOG_BOX_BACKGROUND_PATH = join(IMAGES_DIR, 'dialog_box_background.png')
COMMAND_MENU_BACKGROUND_PATH = join(IMAGES_DIR, 'command_menu_background.png')
COMMAND_MENU_STATIC_BACKGROUND_PATH = join(IMAGES_DIR, 'command_menu_static.png')
CONFIRMATION_BACKGROUND_PATH = join(IMAGES_DIR, 'confirmation.png')
CONFIRMATION_YES_BACKGROUND_PATH = join(IMAGES_DIR, 'confirmation_yes.png')
CONFIRMATION_NO_BACKGROUND_PATH = join(IMAGES_DIR, 'confirmation_no.png')
HOVERING_STATS_BACKGROUND_PATH = join(IMAGES_DIR, 'hovering_stats_window.png')
STATUS_WINDOW_BACKGROUND_PATH = join(IMAGES_DIR, 'status_window_background.png')
IMAGES_MENUS_DIR = join(IMAGES_DIR, 'menus')
IMAGES_MENUS_ITEM_MENU_DIR = join(IMAGES_MENUS_DIR, 'item_menu')
ITEM_MENU_1_BACKGROUND_PATH = join(IMAGES_MENUS_ITEM_MENU_DIR, 'item_menu_background_1.png')
ITEM_MENU_2_BACKGROUND_PATH = join(IMAGES_MENUS_ITEM_MENU_DIR, 'item_menu_background_2.png')
item_menu_background_lookup = {1: ITEM_MENU_1_BACKGROUND_PATH,
                               2: ITEM_MENU_2_BACKGROUND_PATH}

# main menu

# begin quest

BEGIN_QUEST_DIR = join(IMAGES_MENUS_DIR, 'begin_quest')
BEGIN_QUEST_PATH = join(BEGIN_QUEST_DIR, 'begin_quest.png')
BEGIN_QUEST_SELECTED_PATH = join(BEGIN_QUEST_DIR, 'begin_quest_selected.png')

# adventure log

ADVENTURE_LOG_DIR = join(IMAGES_MENUS_DIR, 'adventure_log')
ADVENTURE_LOG_PATH = join(ADVENTURE_LOG_DIR, 'adventure_log.png')
ADVENTURE_LOG_1_PATH = join(ADVENTURE_LOG_DIR, 'adventure_log_1.png')
ADVENTURE_LOG_2_PATH = join(ADVENTURE_LOG_DIR, 'adventure_log_2.png')
ADVENTURE_LOG_3_PATH = join(ADVENTURE_LOG_DIR, 'adventure_log_3.png')

# name selection

NAME_SELECTION_DIR = join(IMAGES_MENUS_DIR, 'name_selection')

NAME_SELECTION_UPPER_A = join(NAME_SELECTION_DIR, '0_upper_A.png')
NAME_SELECTION_UPPER_B = join(NAME_SELECTION_DIR, '1_upper_B.png')
NAME_SELECTION_UPPER_C = join(NAME_SELECTION_DIR, '2_upper_C.png')
NAME_SELECTION_UPPER_D = join(NAME_SELECTION_DIR, '3_upper_D.png')
NAME_SELECTION_UPPER_E = join(NAME_SELECTION_DIR, '4_upper_E.png')
NAME_SELECTION_UPPER_F = join(NAME_SELECTION_DIR, '5_upper_F.png')
NAME_SELECTION_UPPER_G = join(NAME_SELECTION_DIR, '6_upper_G.png')
NAME_SELECTION_UPPER_H = join(NAME_SELECTION_DIR, '7_upper_H.png')
NAME_SELECTION_UPPER_I = join(NAME_SELECTION_DIR, '8_upper_I.png')
NAME_SELECTION_UPPER_J = join(NAME_SELECTION_DIR, '9_upper_J.png')
NAME_SELECTION_UPPER_K = join(NAME_SELECTION_DIR, '10_upper_K.png')
NAME_SELECTION_UPPER_L = join(NAME_SELECTION_DIR, '11_upper_L.png')
NAME_SELECTION_UPPER_M = join(NAME_SELECTION_DIR, '12_upper_M.png')
NAME_SELECTION_UPPER_N = join(NAME_SELECTION_DIR, '13_upper_N.png')
NAME_SELECTION_UPPER_O = join(NAME_SELECTION_DIR, '14_upper_O.png')
NAME_SELECTION_UPPER_P = join(NAME_SELECTION_DIR, '15_upper_P.png')
NAME_SELECTION_UPPER_Q = join(NAME_SELECTION_DIR, '16_upper_Q.png')
NAME_SELECTION_UPPER_R = join(NAME_SELECTION_DIR, '17_upper_R.png')
NAME_SELECTION_UPPER_S = join(NAME_SELECTION_DIR, '18_upper_S.png')
NAME_SELECTION_UPPER_T = join(NAME_SELECTION_DIR, '19_upper_T.png')
NAME_SELECTION_UPPER_U = join(NAME_SELECTION_DIR, '20_upper_U.png')
NAME_SELECTION_UPPER_V = join(NAME_SELECTION_DIR, '21_upper_V.png')
NAME_SELECTION_UPPER_W = join(NAME_SELECTION_DIR, '22_upper_W.png')
NAME_SELECTION_UPPER_X = join(NAME_SELECTION_DIR, '23_upper_X.png')
NAME_SELECTION_UPPER_Y = join(NAME_SELECTION_DIR, '24_upper_Y.png')
NAME_SELECTION_UPPER_Z = join(NAME_SELECTION_DIR, '25_upper_Z.png')
NAME_SELECTION_HYPHEN = join(NAME_SELECTION_DIR, '26_-.png')
NAME_SELECTION_SINGLE_QUOTE = join(NAME_SELECTION_DIR, "27_'.png")
NAME_SELECTION_EXCLAMATION_POINT = join(NAME_SELECTION_DIR, '28_!.png')
NAME_SELECTION_QUESTION_MARK = join(NAME_SELECTION_DIR, '29_question_mark.png')
NAME_SELECTION_OPEN_PARENTHESIS = join(NAME_SELECTION_DIR, '30_(.png')
NAME_SELECTION_CLOSE_PARENTHESIS = join(NAME_SELECTION_DIR, '31_).png')
NAME_SELECTION_SPACE = join(NAME_SELECTION_DIR, '32_space.png')
NAME_SELECTION_LOWER_A = join(NAME_SELECTION_DIR, '33_a.png')
NAME_SELECTION_LOWER_B = join(NAME_SELECTION_DIR, '34_b.png')
NAME_SELECTION_LOWER_C = join(NAME_SELECTION_DIR, '35_c.png')
NAME_SELECTION_LOWER_D = join(NAME_SELECTION_DIR, '36_d.png')
NAME_SELECTION_LOWER_E = join(NAME_SELECTION_DIR, '37_e.png')
NAME_SELECTION_LOWER_F = join(NAME_SELECTION_DIR, '38_f.png')
NAME_SELECTION_LOWER_G = join(NAME_SELECTION_DIR, '39_g.png')
NAME_SELECTION_LOWER_H = join(NAME_SELECTION_DIR, '40_h.png')
NAME_SELECTION_LOWER_I = join(NAME_SELECTION_DIR, '41_i.png')
NAME_SELECTION_LOWER_J = join(NAME_SELECTION_DIR, '42_j.png')
NAME_SELECTION_LOWER_K = join(NAME_SELECTION_DIR, '43_k.png')
NAME_SELECTION_LOWER_L = join(NAME_SELECTION_DIR, '44_l.png')
NAME_SELECTION_LOWER_M = join(NAME_SELECTION_DIR, '45_m.png')
NAME_SELECTION_LOWER_N = join(NAME_SELECTION_DIR, '46_n.png')
NAME_SELECTION_LOWER_O = join(NAME_SELECTION_DIR, '47_o.png')
NAME_SELECTION_LOWER_P = join(NAME_SELECTION_DIR, '48_p.png')
NAME_SELECTION_LOWER_Q = join(NAME_SELECTION_DIR, '49_q.png')
NAME_SELECTION_LOWER_R = join(NAME_SELECTION_DIR, '50_r.png')
NAME_SELECTION_LOWER_S = join(NAME_SELECTION_DIR, '51_s.png')
NAME_SELECTION_LOWER_T = join(NAME_SELECTION_DIR, '52_t.png')
NAME_SELECTION_LOWER_U = join(NAME_SELECTION_DIR, '53_u.png')
NAME_SELECTION_LOWER_V = join(NAME_SELECTION_DIR, '54_v.png')
NAME_SELECTION_LOWER_W = join(NAME_SELECTION_DIR, '55_w.png')
NAME_SELECTION_LOWER_X = join(NAME_SELECTION_DIR, '56_x.png')
NAME_SELECTION_LOWER_Y = join(NAME_SELECTION_DIR, '57_y.png')
NAME_SELECTION_LOWER_Z = join(NAME_SELECTION_DIR, '58_z.png')
NAME_SELECTION_COMMA = join(NAME_SELECTION_DIR, '59_,.png')
NAME_SELECTION_PERIOD = join(NAME_SELECTION_DIR, '60_period.png')
NAME_SELECTION_BACK = join(NAME_SELECTION_DIR, '61_BACK.png')
NAME_SELECTION_END = join(NAME_SELECTION_DIR, '62_END.png')
NAME_SELECTION_STATIC_IMAGE_LEN_0 = join(NAME_SELECTION_DIR, '63_static_image_len_0.png')
NAME_SELECTION_STATIC_IMAGE_LEN_1 = join(NAME_SELECTION_DIR, '64_static_image_len_1.png')
NAME_SELECTION_STATIC_IMAGE_LEN_2 = join(NAME_SELECTION_DIR, '65_static_image_len_2.png')
NAME_SELECTION_STATIC_IMAGE_LEN_3 = join(NAME_SELECTION_DIR, '66_static_image_len_3.png')
NAME_SELECTION_STATIC_IMAGE_LEN_4 = join(NAME_SELECTION_DIR, '67_static_image_len_4.png')
NAME_SELECTION_STATIC_IMAGE_LEN_5 = join(NAME_SELECTION_DIR, '68_static_image_len_5.png')
NAME_SELECTION_STATIC_IMAGE_LEN_6 = join(NAME_SELECTION_DIR, '69_static_image_len_6.png')
NAME_SELECTION_STATIC_IMAGE_LEN_7 = join(NAME_SELECTION_DIR, '70_static_image_len_7.png')
NAME_SELECTION_STATIC_IMAGE_LEN_8 = join(NAME_SELECTION_DIR, '71_static_image_len_8.png')

# shops

IMAGES_SHOPS_DIR = join(IMAGES_DIR, 'shops')
IMAGES_SHOPS_BRECCONARY_DIR = join(IMAGES_SHOPS_DIR, 'brecconary')
IMAGES_SHOPS_BRECCONARY_WEAPONS_DIR = join(IMAGES_SHOPS_BRECCONARY_DIR, 'weapons')
BRECCONARY_WEAPONS_SHOP_PATH = join(IMAGES_SHOPS_BRECCONARY_WEAPONS_DIR, 'brecconary_shop.png')
BRECCONARY_WEAPONS_SHOP_BAMBOO_POLE_PATH = join(IMAGES_SHOPS_BRECCONARY_WEAPONS_DIR, 'brecconary_shop_bamboo_pole.png')
BRECCONARY_WEAPONS_SHOP_CLUB_PATH = join(IMAGES_SHOPS_BRECCONARY_WEAPONS_DIR, 'brecconary_shop_club.png')
BRECCONARY_WEAPONS_SHOP_COPPER_SWORD_PATH = join(IMAGES_SHOPS_BRECCONARY_WEAPONS_DIR, 'brecconary_shop_copper_sword.png')
BRECCONARY_WEAPONS_SHOP_CLOTHES_PATH = join(IMAGES_SHOPS_BRECCONARY_WEAPONS_DIR, 'brecconary_shop_clothes.png')
BRECCONARY_WEAPONS_SHOP_LEATHER_ARMOR_PATH = join(IMAGES_SHOPS_BRECCONARY_WEAPONS_DIR, 'brecconary_shop_leather_armor.png')
BRECCONARY_WEAPONS_SHOP_SMALL_SHIELD_PATH = join(IMAGES_SHOPS_BRECCONARY_WEAPONS_DIR, 'brecconary_shop_small_shield.png')


# battle menu
BATTLE_MENU_DIR = join(IMAGES_MENUS_DIR, 'battle_menu')

BATTLE_MENU_FIGHT_PATH = join(BATTLE_MENU_DIR, 'battle_menu_fight.png')
BATTLE_MENU_SPELL_PATH = join(BATTLE_MENU_DIR, 'battle_menu_spell.png')
BATTLE_MENU_ITEM_PATH = join(BATTLE_MENU_DIR, 'battle_menu_item.png')
BATTLE_MENU_RUN_PATH = join(BATTLE_MENU_DIR, 'battle_menu_run.png')
BATTLE_MENU_STATIC_PATH = join(BATTLE_MENU_DIR, 'battle_menu_static.png')

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

DRAGON_QUEST_FONT = font.Font(DRAGON_QUEST_FONT_PATH, 15)

SMB_FONT_PATH = join(FONTS_DIR, 'super_mario_bros__nes_font.ttf')
SMB_FONT = font.Font(SMB_FONT_PATH, 15)

UNIFONT_PATH = join(FONTS_DIR, 'unifont.ttf')


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
    current_tile = [map_layout[x][y]] if x < len(map_layout) and y < len(map_layout[0]) else None
    if current_tile:
        all_neighbors = set(neighbors + current_tile)
    else:
        all_neighbors = set(neighbors)
    return all_neighbors


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


def create_window(x, y, width, height, window_background, screen, color=WHITE) -> Surface:
    window_box = Surface((TILE_SIZE * width, TILE_SIZE * height))  # lgtm [py/call/wrong-arguments]
    set_window_background(window_box, window_background, color=color)
    screen.blit(window_box, (TILE_SIZE * x, TILE_SIZE * y))
    return window_box


def set_window_background(black_box, background_path, color=WHITE):
    black_box.fill(BLACK)
    background_image = image.load(background_path)
    if color == RED:
        transform.threshold(background_image, background_image, WHITE, (1, 1, 1), RED, 1, None, True)
            # image_pixel_array = PixelArray(background_image)
            # image_pixel_array.replace(WHITE, RED)
    background_image = transform.scale(background_image, black_box.get_size())
    black_box.blit(background_image, black_box.get_rect())
