from statistics import mean
from typing import List, Iterable

from pygame import image, display, KEYDOWN, event, Surface, Rect
from pygame.sprite import Group
from pygame.time import get_ticks
from pygame.transform import scale

from src.calculation import Calculation
from src.common import WHITE, BLACK, Graphics
from src.directories import Directories
from src.enemy_lookup import enemy_image_position_lookup
from src.game_functions import get_surrounding_rect
from src.menu import Menu, CommandMenu
from src.sound import Sound
from src.text import draw_text


class Drawer:

    def __init__(self, game_state):

        self.game_state = game_state
        self.scale = self.game_state.config["SCALE"]
        self.display_hovering_stats = False
        self.background = None
        self.not_moving_time_start = None
        self.hovering_stats_displayed = False
        self.graphics = Graphics(game_state.config)
        self.directories = Directories(game_state.config)
        self.sound = Sound(game_state.config)
        self.calculation = Calculation(game_state.config)

    def position_and_draw_enemy_image(self, screen, enemy_image, enemy_name):
        tile_size = self.game_state.config["TILE_SIZE"]
        enemy_position = enemy_image_position_lookup.get(enemy_name)
        if enemy_position:
            screen.blit(enemy_image, (enemy_position[0] * tile_size, enemy_position[1] * tile_size))
        else:
            average_x = mean(value[0] for value in enemy_image_position_lookup.values())
            average_y = mean(value[1] for value in enemy_image_position_lookup.values())
            screen.blit(enemy_image, average_x, average_y)

    def show_enemy_image(self, screen, enemy_name):
        enemy_name_without_spaces = enemy_name.replace(" ", "")
        enemy_path = f'{self.directories.IMAGES_ENEMIES_DIR}/{enemy_name_without_spaces}.png'
        # Load the base image through cache
        enemy_image_base = self.graphics.get_image(enemy_path)
        # Get scaled version through cache
        scaled_size = (enemy_image_base.get_width() * self.scale, enemy_image_base.get_height() * self.scale)
        enemy_image = self.graphics.get_scaled_image(enemy_path, scaled_size)
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

    def draw_hovering_stats_window(self, screen, player, color=WHITE):
        tile_size = self.game_state.config["TILE_SIZE"]
        self.graphics.create_window(1, 2, 4, 6, self.directories.HOVERING_STATS_BACKGROUND_PATH, screen, color)
        draw_text(player.name[:4], tile_size * 2.99, tile_size * 2, screen, self.game_state.config, color=color,
                  alignment='center', letter_by_letter=False)
        self.draw_stats_strings_with_alignments(f"{player.level}", 2.99, screen, color=color)
        if len(str(player.current_hp)) < 5:
            self.draw_stats_strings_with_alignments(f"{player.current_hp}", 3.99, screen, color=color)
        else:
            self.draw_stats_strings_with_alignments("∞", 3.99, screen, color=color)
        if len(str(player.current_mp)) < 5:
            self.draw_stats_strings_with_alignments(f"{player.current_mp}", 4.99, screen, color=color)
        else:
            self.draw_stats_strings_with_alignments("∞", 4.99, screen, color=color)
        if len(str(player.gold)) < 5:
            self.draw_stats_strings_with_alignments(f"{player.gold}", 5.99, screen, color=color)
        else:
            self.draw_stats_strings_with_alignments("∞", 5.99, screen, color=color)
        if len(str(player.total_experience)) < 5:
            self.draw_stats_strings_with_alignments(f"{player.total_experience}", 6.99, screen, color=color)
        else:
            self.draw_stats_strings_with_alignments("∞", 6.99, screen, color=color)

    def set_to_post_initial_dialog(self, command_menu: CommandMenu):
        self.game_state.is_initial_dialog = False
        command_menu.set_king_lorik_dialog()
        self.game_state.enable_movement = True
        self.game_state.unpause_all_movement()

    def run_automatic_post_death_dialog(self, events, skip_text, command_menu):
        self.game_state.enable_movement = False
        for current_event in events:
            if current_event.type == KEYDOWN or skip_text:
                command_menu.show_text_in_dialog_box(
                    command_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['post_death_dialog'],
                    add_quotes=True, skip_text=skip_text)
                self.game_state.is_post_death_dialog = False
                set_to_save_prompt(command_menu)
                self.game_state.enable_movement = True

    def run_automatic_initial_dialog(self, events, skip_text, cmd_menu):
        self.game_state.enable_movement = False
        key_pressed = any([current_event.type == KEYDOWN for current_event in events])
        if skip_text or (key_pressed and not self.game_state.automatic_initial_dialog_run):
            if self.game_state.game_loaded_from_save:
                cmd_menu.show_text_in_dialog_box(
                    cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['load_from_save_dialog'],
                    add_quotes=True, skip_text=skip_text)
            else:
                cmd_menu.show_text_in_dialog_box(
                    cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'], add_quotes=True,
                    skip_text=skip_text)
            self.set_to_post_initial_dialog(cmd_menu)
            self.game_state.automatic_initial_dialog_run = True

    def handle_initial_dialog(self, initial_dialog_enabled, cmd_menu, events, skip_text, allow_save_prompt):
        if initial_dialog_enabled:
            if self.game_state.is_initial_dialog:
                display.flip()
                self.display_hovering_stats = False
                cmd_menu.launch_signaled = False
                self.run_automatic_initial_dialog(events, skip_text, cmd_menu)
                event.clear()
            else:
                if allow_save_prompt:
                    set_to_save_prompt(cmd_menu)
                else:
                    self.set_to_post_initial_dialog(cmd_menu)

        else:
            self.set_to_post_initial_dialog(cmd_menu)
            if not cmd_menu.menu.is_enabled():
                self.game_state.enable_movement = True

    def handle_darkness(self, screen, torch_active):
        tile_size = self.game_state.config["TILE_SIZE"]
        darkness = Surface((screen.get_width(), screen.get_height()))  # lgtm [py/call/wrong-arguments]
        if torch_active:
            # Light with radius of 1
            darkness_hole = darkness.subsurface((screen.get_width() / 2) - tile_size,
                                                (screen.get_height() / 2) - (tile_size * 1.5),
                                                tile_size * 3,
                                                tile_size * 3)
        elif self.game_state.radiant_active:
            # Light with radius of 2, expanding to 3...

            # darkness_hole = darkness.subsurface((self.screen.get_width() / 2) - TILE_SIZE * 2, (self.screen.get_height() / 2) - (TILE_SIZE * 2.5),
            #                                     TILE_SIZE * 5,
            #                                     TILE_SIZE * 5)
            # darkness.fill(BLACK)
            # darkness_hole.fill(WHITE)
            # darkness.set_colorkey(WHITE)
            # self.screen.blit(darkness, (0, 0))
            # Light with radius of 3
            darkness_hole = darkness.subsurface((screen.get_width() / 2) - tile_size * 3,
                                                (screen.get_height() / 2) - tile_size * 3.5,
                                                tile_size * 7,
                                                tile_size * 7)

            if self.game_state.radiant_start is None:
                self.game_state.radiant_start = self.game_state.tiles_moved_total
                self.sound.play_sound(self.directories.torch_sfx)
                self.sound.play_sound(self.directories.torch_sfx)
            else:
                if self.game_state.tiles_moved_total - self.game_state.radiant_start >= 200:
                    self.game_state.radiant_active = False
                    self.game_state.radiant_start = None
                elif self.game_state.tiles_moved_total - self.game_state.radiant_start >= 140:
                    # Light with radius of 1
                    darkness_hole = darkness.subsurface((screen.get_width() / 2) - tile_size,
                                                        (screen.get_height() / 2) - (tile_size * 1.5),
                                                        tile_size * 3,
                                                        tile_size * 3)
                elif self.game_state.tiles_moved_total - self.game_state.radiant_start >= 80:
                    # Light with radius of 2
                    darkness_hole = darkness.subsurface((screen.get_width() / 2) - tile_size * 2,
                                                        (screen.get_height() / 2) - (tile_size * 2.5),
                                                        tile_size * 5,
                                                        tile_size * 5)

        else:
            darkness_hole = darkness.subsurface((screen.get_width() / 2),
                                                (screen.get_height() / 2) - (tile_size / 2), tile_size,
                                                tile_size)
        darkness.fill(BLACK)
        darkness_hole.fill(WHITE)
        darkness.set_colorkey(WHITE)
        screen.blit(darkness, (0, 0)) if not self.game_state.config['NO_BLIT'] else None

    def draw_all(self, screen, loop_count, big_map, current_map, player, cmd_menu, foreground_rects, enable_animate,
                 camera, initial_dialog_enabled, events, skip_text, allow_save_prompt, game_state, torch_active,
                 color) -> None:
        """
        Draw map, sprites, background, menu and other surfaces.
        :return: None
        """

        screen.fill(BLACK)
        width_offset = 0
        height_offset = 0
        tile_size = self.game_state.config["TILE_SIZE"]
        if loop_count == 1:
            self.background = big_map.subsurface(0, 0, current_map.width - width_offset,
                                                 current_map.height - height_offset).convert()
            # draw everything once on the first go-around
            self.draw_all_tiles_in_current_map(current_map, self.background)
        try:
            surrounding_tile_values = get_surrounding_tile_values(
                (player.rect.y // tile_size, player.rect.x // tile_size), current_map.layout)
            player_surrounding_tiles = convert_numeric_tile_list_to_unique_tile_values(current_map,
                                                                                       surrounding_tile_values)
            all_roaming_character_surrounding_tiles = self.get_all_roaming_character_surrounding_tiles(current_map)
            all_fixed_character_underlying_tiles = get_fixed_character_underlying_tiles(current_map)
            tile_types_to_draw = replace_characters_with_underlying_tiles([player.current_tile] +
                                                                          all_roaming_character_surrounding_tiles +
                                                                          all_fixed_character_underlying_tiles,
                                                                          current_map.character_key)
            if player.is_moving:
                tile_types_to_draw += replace_characters_with_underlying_tiles(
                    list(filter(None, player_surrounding_tiles)), current_map.character_key)
                self.not_moving_time_start = None
                self.display_hovering_stats = False
                if self.hovering_stats_displayed:
                    cmd_menu.window_drop_up_effect(1, 2, 4, 6)
                    self.hovering_stats_displayed = False
            else:
                if not self.not_moving_time_start:
                    self.not_moving_time_start = get_ticks()
                else:
                    if self.calculation.convert_to_frames_since_start_time(self.not_moving_time_start) >= 51:
                        self.display_hovering_stats = True
        except IndexError:
            all_roaming_character_surrounding_tiles = self.get_all_roaming_character_surrounding_tiles(current_map)
            all_fixed_character_underlying_tiles = get_fixed_character_underlying_tiles(current_map)
            tile_types_to_draw = replace_characters_with_underlying_tiles([player.current_tile] +
                                                                          all_roaming_character_surrounding_tiles +
                                                                          all_fixed_character_underlying_tiles,
                                                                          current_map.character_key)

            # tile_types_to_draw = list(filter(lambda x: not self.is_impassable(x), tile_types_to_draw))

        group_to_draw = Group()
        camera_screen_rect = Rect(player.rect.x - tile_size * 8, player.rect.y - tile_size * 7,
                                  screen.get_width(), screen.get_height())
        double_camera_screen_rect = camera_screen_rect.inflate(camera_screen_rect.width * 0.25,
                                                               camera_screen_rect.height * 0.25)
        fixed_character_rects = [fixed_character.rect for fixed_character in current_map.fixed_characters]
        roaming_character_rects = [
            roaming_character.rect if roaming_character.is_moving else get_surrounding_rect(roaming_character,
                                                                                            self.game_state.config[
                                                                                                "TILE_SIZE"]) for
            roaming_character in
            current_map.roaming_characters]
        for tile, tile_dict in current_map.floor_tile_key.items():
            if tile_dict.get('group') and tile in set(tile_types_to_draw):
                for tile_to_draw in tile_dict['group']:
                    if camera_screen_rect.colliderect(tile_to_draw.rect):
                        if player.is_moving:
                            if get_surrounding_rect(player, tile_size).colliderect(tile_to_draw.rect):
                                group_to_draw.add(tile_to_draw)
                                # tiles_drawn.append(tile)
                        else:
                            if player.rect.colliderect(tile_to_draw.rect):
                                group_to_draw.add(tile_to_draw)
                                # tiles_drawn.append(tile)
                        for fixed_character_rect in fixed_character_rects:
                            if fixed_character_rect.colliderect(tile_to_draw):
                                group_to_draw.add(tile_to_draw)
                                # tiles_drawn.append(tile)

                    if double_camera_screen_rect.colliderect(tile_to_draw.rect):
                        for roaming_character_rect in roaming_character_rects:
                            if roaming_character_rect.colliderect(tile_to_draw):
                                group_to_draw.add(tile_to_draw)
                                # tiles_drawn.append(tile)
        # print(f"{len(tiles_drawn)}: {tiles_drawn}")
        group_to_draw.draw(self.background)
        # to make this work in all maps: draw tile under hero, AND tiles under NPCs
        # in addition to the trajectory of the NPCs
        self.handle_sprite_drawing_and_animation(current_map, foreground_rects, self.background,
                                                 enable_animate)
        screen.blit(self.background, camera.pos) if not self.game_state.config['NO_BLIT'] else None
        if current_map.identifier == 'TantegelThroneRoom':
            self.handle_initial_dialog(initial_dialog_enabled, cmd_menu, events, skip_text, allow_save_prompt)
            self.handle_post_death_dialog(game_state, cmd_menu, events, skip_text)
        if current_map.is_dark and self.game_state.config["ENABLE_DARKNESS"]:
            self.handle_darkness(screen, torch_active)
        if self.display_hovering_stats:
            if not self.hovering_stats_displayed:
                cmd_menu.window_drop_down_effect(1, 2, 4, 6)
                self.hovering_stats_displayed = True
            self.draw_hovering_stats_window(screen, player, color)
        self.handle_menu_launch(screen, cmd_menu, cmd_menu)
        if cmd_menu.menu.is_enabled():
            cmd_menu.menu.update(events)
        else:
            if not game_state.is_initial_dialog:
                game_state.enable_movement = True

    def handle_post_death_dialog(self, game_state, cmd_menu, events, skip_text):
        if game_state.is_post_death_dialog:
            self.display_hovering_stats = False
            cmd_menu.launch_signaled = False
            self.run_automatic_post_death_dialog(events, skip_text, cmd_menu)
            event.clear()

    def draw_stats_strings_with_alignments(self, stat_string, y_position, screen, color):
        tile_size = self.game_state.config["TILE_SIZE"]
        if len(stat_string) > 4:
            draw_text(stat_string, tile_size * 3.2, tile_size * y_position, screen, self.game_state.config, color=color,
                      alignment='center', letter_by_letter=False)
        elif len(stat_string) > 3:
            draw_text(stat_string, tile_size * 3.44, tile_size * y_position, screen, self.game_state.config,
                      color=color, alignment='center', letter_by_letter=False)
        elif len(stat_string) > 2:
            draw_text(stat_string, tile_size * 3.67, tile_size * y_position, screen, self.game_state.config,
                      color=color, alignment='center', letter_by_letter=False)
        elif len(stat_string) > 1:
            draw_text(stat_string, tile_size * 3.99, tile_size * y_position, screen, self.game_state.config,
                      color=color, alignment='center', letter_by_letter=False)
        else:
            draw_text(stat_string, tile_size * 4.2, tile_size * y_position, screen, self.game_state.config, color=color,
                      alignment='center', letter_by_letter=False)

    def get_all_roaming_character_surrounding_tiles(self, current_map) -> List[str]:
        tile_size = self.game_state.config["TILE_SIZE"]
        all_roaming_character_surrounding_tiles = []
        for roaming_character in current_map.roaming_characters:
            roaming_character_surrounding_tile_values = get_surrounding_tile_values(
                (roaming_character.rect.y // tile_size, roaming_character.rect.x // tile_size), current_map.layout)
            roaming_character_surrounding_tiles = convert_numeric_tile_list_to_unique_tile_values(current_map,
                                                                                                  roaming_character_surrounding_tile_values)
            for tile in roaming_character_surrounding_tiles:
                all_roaming_character_surrounding_tiles.append(tile)
        return all_roaming_character_surrounding_tiles

    def handle_menu_launch(self, screen, cmd_menu, menu_to_launch: Menu) -> None:
        tile_size = self.game_state.config['TILE_SIZE']
        if menu_to_launch.launch_signaled:
            if menu_to_launch.menu.get_id() == 'command':
                command_menu_subsurface = screen.subsurface(
                    (6 * tile_size,  # 11 (first empty square to the left of menu)
                     tile_size),  # 4
                    (8 * tile_size,
                     5 * tile_size)
                )
                if not cmd_menu.menu.is_enabled():
                    self.sound.play_sound(self.directories.menu_button_sfx)
                    cmd_menu.window_drop_down_effect(6, 1, 8, 5)
                    cmd_menu.menu.enable()
                else:
                    menu_to_launch.menu.draw(command_menu_subsurface)
                    display.update(command_menu_subsurface.get_rect())


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


def get_fixed_character_underlying_tiles(current_map) -> List[str]:
    all_fixed_character_underlying_tiles = []
    for fixed_character in current_map.fixed_characters:
        fixed_character_coordinates = current_map.characters[fixed_character.identifier]['coordinates']
        all_fixed_character_underlying_tiles.append(
            current_map.get_tile_by_value(
                current_map.layout[fixed_character_coordinates[0]][fixed_character_coordinates[1]]))
    return all_fixed_character_underlying_tiles


def set_to_save_prompt(cmd_menu):
    cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'] = \
        cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['returned_dialog']
