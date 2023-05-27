from typing import List, Iterable

from pygame import image, display
from pygame.transform import scale

from src.common import convert_to_frames_since_start_time, IMAGES_ENEMIES_DIR, WHITE, create_window, \
    HOVERING_STATS_BACKGROUND_PATH, play_sound, menu_button_sfx
from src.config import TILE_SIZE, SCALE
from src.menu import Menu
from src.text import draw_text


class Drawer:

    @staticmethod
    def alternate_blink(image_1, image_2, right_arrow_start, screen):
        while convert_to_frames_since_start_time(right_arrow_start) <= 16:
            selected_image = scale(image.load(image_1), (screen.get_width(), screen.get_height()))
            screen.blit(selected_image, (0, 0))
            # draw_text(">BEGIN A NEW QUEST", screen.get_width() / 2, screen.get_height() / 3, self.screen)
            display.update(selected_image.get_rect())
        while 16 < convert_to_frames_since_start_time(right_arrow_start) <= 32:
            unselected_image = scale(image.load(image_2), (screen.get_width(), screen.get_height()))
            screen.blit(unselected_image, (0, 0))
            # draw_text(" BEGIN A NEW QUEST", screen.get_width() / 2, screen.get_height() / 3, self.screen)
            display.update(unselected_image.get_rect())

    @staticmethod
    def position_and_draw_enemy_image(screen, enemy_image, enemy_name):
        if enemy_name in ('Slime', 'Red Slime', 'Metal Slime'):
            screen.blit(enemy_image, (8 * TILE_SIZE, 7 * TILE_SIZE))
        elif enemy_name in ('Drakee', 'Magidrakee', 'Drakeema'):
            # might need work
            screen.blit(enemy_image, (7.75 * TILE_SIZE, 6.25 * TILE_SIZE))
        elif enemy_name in ('Ghost', 'Poltergeist', 'Specter'):
            screen.blit(enemy_image, (7.8 * TILE_SIZE, 5.9 * TILE_SIZE))
        elif enemy_name in ('Magician', 'Warlock', 'Wizard'):
            screen.blit(enemy_image, (7.3 * TILE_SIZE, 6 * TILE_SIZE))
        elif enemy_name in ('Scorpion', 'Metal Scorpion', 'Rogue Scorpion'):
            screen.blit(enemy_image, (7.4 * TILE_SIZE, 6.5 * TILE_SIZE))
        elif enemy_name in ('Druin', 'Druinlord'):
            screen.blit(enemy_image, (8 * TILE_SIZE, 6.5 * TILE_SIZE))
        elif enemy_name in ('Droll', 'Drollmagi'):
            screen.blit(enemy_image, (7.5 * TILE_SIZE, 6 * TILE_SIZE))
        elif enemy_name in ('Skeleton', 'Wraith', 'Wraith Knight', 'Demon Knight'):
            screen.blit(enemy_image, (7.46 * TILE_SIZE, 5.74 * TILE_SIZE))
        elif enemy_name in ('Wolf', 'Wolflord', 'Werewolf'):
            screen.blit(enemy_image, (7.11 * TILE_SIZE, 5.95 * TILE_SIZE))
        elif enemy_name in ('Goldman', 'Golem', 'Stoneman'):
            screen.blit(enemy_image, (7.1 * TILE_SIZE, 5.6 * TILE_SIZE))
        elif enemy_name in ('Wyvern', 'Magiwyvern', 'Starwyvern'):
            screen.blit(enemy_image, (7.25 * TILE_SIZE, 5.5 * TILE_SIZE))
        elif enemy_name in ('Knight', 'Axe Knight', 'Armored Knight'):
            screen.blit(enemy_image, (7.1 * TILE_SIZE, 5.75 * TILE_SIZE))
        elif enemy_name in ('Green Dragon', 'Blue Dragon', 'Red Dragon'):
            screen.blit(enemy_image, (6.5 * TILE_SIZE, 6.25 * TILE_SIZE))
        elif enemy_name == 'Dragonlord':
            screen.blit(enemy_image, (7.5 * TILE_SIZE, 6 * TILE_SIZE))
        elif enemy_name == 'Dragonlord 2':
            # need to have this blit over the text box on the bottom
            screen.blit(enemy_image, (5.1 * TILE_SIZE, 4 * TILE_SIZE))
        else:
            screen.blit(enemy_image, (7.544 * TILE_SIZE, 6.1414 * TILE_SIZE))

    def show_enemy_image(self, screen, enemy_name):
        enemy_name_without_spaces = enemy_name.replace(" ", "")
        enemy_image = image.load(
            f'{IMAGES_ENEMIES_DIR}/{enemy_name_without_spaces}.png').convert_alpha()
        enemy_image = scale(enemy_image, (enemy_image.get_width() * SCALE,
                                          enemy_image.get_height() * SCALE))
        self.position_and_draw_enemy_image(screen, enemy_image, enemy_name)

    @staticmethod
    def handle_sprite_animation(enable_animate, character_dict):
        if enable_animate:
            character_dict['character'].animate()
        else:
            character_dict['character'].pause()

    def handle_sprite_drawing_and_animation(self, current_map, foreground_rects, background, enable_animate):
        for character_dict in current_map.characters.values():
            foreground_rects.append(character_dict['character_sprites'].draw(background)[0])
            self.handle_sprite_animation(enable_animate, character_dict)

    @staticmethod
    def draw_all_tiles_in_current_map(current_map, background) -> None:
        for tile, tile_dict in current_map.floor_tile_key.items():
            if tile in current_map.tile_types_in_current_map and tile_dict.get('group'):
                tile_dict['group'].draw(background)

    @staticmethod
    def draw_hovering_stats_window(screen, player, color=WHITE):
        create_window(1, 2, 4, 6, HOVERING_STATS_BACKGROUND_PATH, screen, color)
        draw_text(player.name[:4], TILE_SIZE * 2.99, TILE_SIZE * 2, screen, color=color, alignment='center',
                  letter_by_letter=False)
        draw_stats_strings_with_alignments(f"{player.level}", 2.99, screen, color=color)
        draw_stats_strings_with_alignments(f"{player.current_hp}", 3.99, screen, color=color)
        draw_stats_strings_with_alignments(f"{player.current_mp}", 4.99, screen, color=color)
        draw_stats_strings_with_alignments(f"{player.gold}", 5.99, screen, color=color)
        draw_stats_strings_with_alignments(f"{player.total_experience}", 6.99, screen, color=color)


def draw_stats_strings_with_alignments(stat_string, y_position, screen, color=WHITE):
    if len(stat_string) > 4:
        draw_text(stat_string, TILE_SIZE * 3.2, TILE_SIZE * y_position, screen, color=color, alignment='center',
                  letter_by_letter=False)
    elif len(stat_string) > 3:
        draw_text(stat_string, TILE_SIZE * 3.44, TILE_SIZE * y_position, screen, color=color, alignment='center',
                  letter_by_letter=False)
    elif len(stat_string) > 2:
        draw_text(stat_string, TILE_SIZE * 3.67, TILE_SIZE * y_position, screen, color=color, alignment='center',
                  letter_by_letter=False)
    elif len(stat_string) > 1:
        draw_text(stat_string, TILE_SIZE * 3.99, TILE_SIZE * y_position, screen, color=color, alignment='center',
                  letter_by_letter=False)
    else:
        draw_text(stat_string, TILE_SIZE * 4.2, TILE_SIZE * y_position, screen, color=color, alignment='center',
                  letter_by_letter=False)


def replace_characters_with_underlying_tiles(tile_types_to_draw: List[str], current_map_character_key) -> List[str]:
    for character in current_map_character_key.keys():
        if character in tile_types_to_draw:
            tile_types_to_draw = list(
                map(lambda x: x.replace(character, current_map_character_key[character]['underlying_tile']),
                    tile_types_to_draw))
    return tile_types_to_draw


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


def convert_numeric_tile_list_to_unique_tile_values(current_map, numeric_tile_list: Iterable[int]) -> List[str]:
    converted_tiles = []
    for tile_value in set(numeric_tile_list):
        converted_tiles.append(current_map.get_tile_by_value(tile_value))
    return converted_tiles


def get_all_roaming_character_surrounding_tiles(current_map) -> List[str]:
    all_roaming_character_surrounding_tiles = []
    for roaming_character in current_map.roaming_characters:
        roaming_character_surrounding_tile_values = get_surrounding_tile_values(
            (roaming_character.rect.y // TILE_SIZE, roaming_character.rect.x // TILE_SIZE), current_map.layout)
        roaming_character_surrounding_tiles = convert_numeric_tile_list_to_unique_tile_values(current_map,
                                                                                              roaming_character_surrounding_tile_values)
        for tile in roaming_character_surrounding_tiles:
            all_roaming_character_surrounding_tiles.append(tile)
    return all_roaming_character_surrounding_tiles


def get_fixed_character_underlying_tiles(current_map) -> List[str]:
    all_fixed_character_underlying_tiles = []
    for fixed_character in current_map.fixed_characters:
        fixed_character_coordinates = current_map.characters[fixed_character.identifier]['coordinates']
        all_fixed_character_underlying_tiles.append(
            current_map.get_tile_by_value(
                current_map.layout[fixed_character_coordinates[0]][fixed_character_coordinates[1]]))
    return all_fixed_character_underlying_tiles


def handle_menu_launch(screen, cmd_menu, menu_to_launch: Menu) -> None:
    if menu_to_launch.launch_signaled:
        if menu_to_launch.menu.get_id() == 'command':
            command_menu_subsurface = screen.subsurface(
                (6 * TILE_SIZE,  # 11 (first empty square to the left of menu)
                 TILE_SIZE),  # 4
                (8 * TILE_SIZE,
                 5 * TILE_SIZE)
            )
            if not cmd_menu.menu.is_enabled():
                play_sound(menu_button_sfx)
                cmd_menu.window_drop_down_effect(6, 1, 8, 5)
                cmd_menu.menu.enable()
            else:
                menu_to_launch.menu.draw(command_menu_subsurface)
                display.update(command_menu_subsurface.get_rect())


def set_to_save_prompt(cmd_menu):
    cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'] = \
        cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['returned_dialog']