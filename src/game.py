import random
import sys
from typing import List, Tuple

from pygame import FULLSCREEN, KEYUP, K_1, K_2, K_3, K_4, K_DOWN, K_LEFT, K_RIGHT, K_UP, K_a, K_d, K_i, K_j, K_k, K_s, K_u, K_w, QUIT, RESIZABLE, Surface, \
    display, event, image, init, key, mixer, quit
from pygame.display import set_mode, set_caption
from pygame.event import get
from pygame.time import Clock
from pygame.time import get_ticks

import src.menu as menu
from data.text.dialog import show_text_in_dialog_box
from data.text.dialog_lookup_table import DialogLookup
from src import maps
from src.camera import Camera
from src.common import Direction, menu_button_sfx, stairs_down_sfx, stairs_up_sfx, BLACK, is_facing_medially, \
    is_facing_laterally, \
    WHITE, intro_overture, DRAGON_QUEST_FONT_PATH, village_music, get_surrounding_tile_values, ICON_PATH
from src.common import get_tile_id_by_coordinates, is_facing_up, is_facing_down, is_facing_left, is_facing_right
from src.config import NES_RES, SHOW_FPS, SPLASH_SCREEN_ENABLED, SHOW_COORDINATES, INITIAL_DIALOG_ENABLED
from src.config import SCALE, TILE_SIZE, FULLSCREEN_ENABLED, MUSIC_ENABLED, FPS
from src.game_functions import set_character_position, get_next_coordinates
from src.intro import Intro
from src.map_layouts import MapLayouts
from src.maps import map_lookup
from src.movement import bump_and_reset
from src.player.player import Player
from src.sound import bump, play_sound
from src.sprites.fixed_character import FixedCharacter
from src.sprites.roaming_character import RoamingCharacter
from src.text import draw_text
from src.visual_effects import fade


class Game:

    def __init__(self):
        # Initialize pygame
        self.draw_text_start = None
        self.temporary_text_on_screen = None
        self.fps = FPS
        self.last_map = None
        self.start_time = get_ticks()
        self.tiles_moved_since_spawn = 0
        self.loop_count = 1
        self.foreground_rects = []
        init()

        self.paused = False
        # Create the game window.
        if FULLSCREEN_ENABLED:
            # if it's segfaulting, try maybe not using the SCALED flag
            # flags = FULLSCREEN | SCALED
            flags = FULLSCREEN
        else:
            # flags = RESIZABLE | SCALED
            flags = RESIZABLE
        # flags = RESIZABLE | SCALED allows for the graphics to stretch to fit the window
        # without SCALED, it will show more of the map, but will also not center the camera
        # it might be a nice comfort addition to add to center the camera, while also showing more of the map
        self.scale = SCALE
        # video_infos = display.Info()
        # current_screen_width, current_screen_height = video_infos.current_w, video_infos.current_h
        self.win_width, self.win_height = NES_RES[0] * self.scale, NES_RES[1] * self.scale
        self.speed = 2
        # self.win_width = current_screen_width
        # self.win_height = current_screen_height
        self.screen = set_mode((self.win_width, self.win_height), flags)
        # self.screen.set_alpha(None)
        set_caption("Dragon Warrior")

        # self.current_map can be changed to other maps for development purposes

        self.current_map = maps.TantegelThroneRoom()
        # self.current_map = maps.TantegelCourtyard()
        # self.current_map = maps.Alefgard()
        # self.current_map = maps.Brecconary()
        # self.current_map = maps.Garinham()
        # self.current_map = maps.ErdricksCaveB1()
        # self.current_map = maps.Rimuldar()
        # self.current_map = maps.Cantlin()

        self.big_map = Surface(
            (self.current_map.width, self.current_map.height)).convert()  # lgtm [py/call/wrong-arguments]
        self.big_map.fill(BLACK)

        for roaming_character in self.current_map.roaming_characters:
            roaming_character.last_roaming_clock_check = get_ticks()
            set_character_position(roaming_character)
        # Make the big scrollable map
        self.background = self.big_map.subsurface(0, 0, self.current_map.width, self.current_map.height).convert()
        self.player = Player(center_point=None, images=None)
        self.current_map.load_map(self.player, None)

        # Good for debugging, and will be useful later when the player's level increases and the stats need to be increased to match

        # self.player.total_experience = 26000
        # self.player.level = self.player.get_level_by_experience()
        # self.player.update_stats_to_current_level()

        initial_hero_location = self.current_map.get_initial_character_location('HERO')
        self.player.row, self.player.column = initial_hero_location.take(0), initial_hero_location.take(1)
        self.player.current_tile = get_tile_id_by_coordinates(self.player.rect.x // TILE_SIZE,
                                                              self.player.rect.y // TILE_SIZE, self.current_map)
        self.player.next_tile_id = self.get_next_tile_identifier(self.player.column, self.player.row,
                                                                 self.current_map.player.direction_value)
        self.player.next_next_tile_id = self.get_next_tile_identifier(self.player.column, self.player.row,
                                                                      self.current_map.player.direction_value, offset=3)
        self.camera = Camera((int(self.player.column), int(self.player.row)), self.current_map, self.screen)
        self.cmd_menu = menu.CommandMenu(self.background, self.current_map, self.player, self.screen, self.camera.get_pos())

        self.enable_animate, self.enable_roaming, self.enable_movement = True, True, True
        self.clock = Clock()
        self.music_enabled = MUSIC_ENABLED
        if SPLASH_SCREEN_ENABLED:
            self.load_and_play_music(intro_overture)
        else:
            self.load_and_play_music(self.current_map.music_file_path)
        self.events = get()

        display.set_icon(image.load(ICON_PATH))
        self.player.restore_hp()
        # pg.event.set_allowed([pg.QUIT])

    def main(self) -> None:
        """
        Main loop.
        :return: None
        """
        if SPLASH_SCREEN_ENABLED:
            intro = Intro()
            intro.show_start_screen(self.screen, self.start_time, self.clock, self.background)
            self.show_main_menu_screen(self.screen)
        self.draw_all()
        while True:
            self.clock.tick(self.fps)
            self.get_events()
            self.draw_all()
            self.update_screen()
            self.loop_count += 1

    def show_main_menu_screen(self, screen) -> None:
        main_menu_screen_enabled = True
        self.load_and_play_music(village_music)
        while main_menu_screen_enabled:
            screen.fill(BLACK)
            # totally dummy option for now, just a placeholder
            for i in range(128):
                draw_text(">BEGIN A NEW QUEST", 15, WHITE, screen.get_width() / 2, screen.get_height() / 3, DRAGON_QUEST_FONT_PATH, self.screen)
                display.flip()
            for i in range(128):
                draw_text(" BEGIN A NEW QUEST", 15, WHITE, screen.get_width() / 2, screen.get_height() / 3, DRAGON_QUEST_FONT_PATH, self.screen)
                display.flip()
            self.clock.tick(self.fps)
            for current_event in get():
                if current_event.type == QUIT:
                    quit()
                    sys.exit()
                elif current_event.type == KEYUP:
                    main_menu_screen_enabled = False
        play_sound(menu_button_sfx)
        fade(screen.get_width(), screen.get_height(), fade_out=True, background=self.background, screen=self.screen)
        self.load_and_play_music(self.current_map.music_file_path)

    def get_events(self) -> None:
        """
        Handle all events in main loop.
        :return: None
        """
        self.events = get()
        for current_event in self.events:
            if current_event.type == QUIT:
                quit()
                sys.exit()
        event.pump()
        current_key = key.get_pressed()
        if not self.player.is_moving:
            set_character_position(self.player)
        if self.enable_movement:
            self.move_player(current_key)
        if self.enable_roaming and self.current_map.roaming_characters:
            self.move_roaming_characters()
            self.update_roaming_character_positions()

        # currently can't process staircases right next to one another, need to fix
        # a quick fix would be to add an exception in the conditional for
        # the map where staircases right next to each other need to be enabled,
        # as done with Cantlin below
        if self.tiles_moved_since_spawn > 1 or self.current_map.identifier in (
                'Cantlin', 'Hauksness', 'Rimuldar', 'CharlockB1'):
            for staircase_location, staircase_dict in self.current_map.staircases.items():
                self.process_staircase_warps(staircase_dict, staircase_location)

        self.handle_keypresses(current_key)

        self.player.current_tile = get_tile_id_by_coordinates(self.player.rect.x // TILE_SIZE,
                                                              self.player.rect.y // TILE_SIZE, self.current_map)
        self.cmd_menu.current_tile = self.player.current_tile

        self.player.next_coordinates = get_next_coordinates(self.player.rect.x // TILE_SIZE,
                                                            self.player.rect.y // TILE_SIZE,
                                                            self.player.direction_value)
        self.player.next_next_coordinates = get_next_coordinates(self.player.rect.x // TILE_SIZE,
                                                                 self.player.rect.y // TILE_SIZE,
                                                                 self.player.direction_value, offset_from_character=2)

        # Debugging area

        # This prints out the current tile that the player is standing on.
        # print(f"self.player.current_tile: {self.player.current_tile}")

        if SHOW_COORDINATES:
            print(f"{self.player.row, self.player.column}")

        # This prints out the next coordinates that the player will land on.
        # print(self.player.next_coordinates)

        # This prints out the next tile that the player will land on.
        # print(get_tile_id_by_coordinates(self.player.next_coordinates[1], self.player.next_coordinates[0], self.current_map))

        # This prints out the current FPS.
        if SHOW_FPS:
            print(self.clock.get_fps())

        # This prints out the next tile, and the next next tile.
        # print(f'Next tile: {self.player.next_tile}')
        # print(f'Next next tile: {self.player.next_next_tile}')
        # print(f'{self.get_character_identifier_by_coordinates(self.player.next_coordinates)}')
        # print(f'{self.get_character_identifier_by_coordinates(self.player.next_next_coordinates)}')

        event.pump()

    def handle_keypresses(self, current_key):
        if current_key[K_j]:
            # B button
            self.unlaunch_menu(self.cmd_menu)
            self.draw_all_tiles_in_current_map()
            # print("J key pressed (B button).")
        if current_key[K_k]:
            # A button
            # print("K key pressed (A button).")
            if not self.player.is_moving:
                # pause_all_movement may be temporarily commented out for dialog box debugging purposes.
                self.cmd_menu.launch_signaled = True
                self.pause_all_movement()
        if current_key[K_i]:
            # Start button
            if self.paused:
                self.unpause_all_movement()
            else:
                self.pause_all_movement()
            print("I key pressed (Start button).")
        if current_key[K_u]:
            # Select button
            print("U key pressed (Select button).")
        # TODO: Allow for zoom in and out if Ctrl + PLUS | MINUS is pressed. (modernization)
        # if key[pg.K_LCTRL] and (key[pg.K_PLUS] or key[pg.K_KP_PLUS]):
        #     self.scale = self.scale + 1
        self.handle_fps_changes(current_key)

    def handle_fps_changes(self, current_key) -> None:
        if current_key[K_1]:
            self.draw_temporary_text(("Game set to normal speed.",))
            self.fps = 60
        if current_key[K_2]:
            self.draw_temporary_text(("Game set to double speed.",))
            self.fps = 120
        if current_key[K_3]:
            self.draw_temporary_text(("Game set to triple speed.",))
            self.fps = 240
        if current_key[K_4]:
            self.draw_temporary_text(("Game set to quadruple speed.",))
            self.fps = 480

    def update_roaming_character_positions(self) -> None:
        for character, character_dict in self.current_map.characters.items():
            if character_dict['character'].__class__.__name__ == 'RoamingCharacter':
                if not character_dict['character'].is_moving:
                    set_character_position(character_dict['character'])

    def draw_temporary_text(self, text: Tuple[str] | List[str], add_quotes=False) -> None:
        self.temporary_text_on_screen = True
        self.draw_text_start = get_ticks()
        show_text_in_dialog_box(text, self.background, self.camera.get_pos(), self.current_map, self.screen,
                                add_quotes=add_quotes,
                                temp_text_start=self.draw_text_start)

    def process_staircase_warps(self, staircase_dict: dict, staircase_location: tuple) -> None:
        if (self.player.row, self.player.column) == staircase_location:
            self.player.bumped = False
            match staircase_dict['stair_direction']:
                case 'down':
                    play_sound(stairs_down_sfx)
                case 'up':
                    play_sound(stairs_up_sfx)
            self.change_map(map_lookup[staircase_dict['map']]())

    def draw_all(self) -> None:
        """
        Draw map, sprites, background, menu and other surfaces.
        :return: None
        """
        self.screen.fill(BLACK)
        # if isinstance(self.current_map, maps.Alefgard):
        #     # width_offset = 2336
        #     width_offset = TILE_SIZE * self.player.column + 24
        #     height_offset = TILE_SIZE * self.player.row + 25
        # else:
        width_offset = 0
        height_offset = 0
        if self.loop_count == 1:
            self.background = self.big_map.subsurface(0, 0, self.current_map.width - width_offset,
                                                      self.current_map.height - height_offset)
        # this for loop is a good place to look to improve overall FPS, reduce frame drops, etc.
        # while the improvements up until now have been significant enough to keep the FPS at 60
        # even while on the overworld map, there are still improvements that can be made:
        # some basic pseudocode --

        # TODO: Improve implementation of the following "not moving" optimization.

        # one optimization to make while not moving:

        # on overworld map:
        #     if not self.player.is_moving:
        #         there are no roaming characters, so only update the middle square where the player is
        #     else:
        #         do the normal logic
        # on non-overworld maps
        #     if not self.player.is_moving:
        #         only update the middle square where the player is
        #         and the squares where roaming characters are now or will be
        #     else:
        #         do the normal logic

        # right now we're pretty close with the surrounding tiles check, but we could be doing better

        # print(self.background.get_rect())
        if self.loop_count == 1:
            # draw everything once on the first go-around
            self.draw_all_tiles_in_current_map()
        # performance optimization to only draw the tile type that the hero is standing on, and surrounding tiles
        # won't work where there are moving NPCs, so only use this in the overworld
        # if not self.current_map.roaming_characters:
        # basically, if you're in the overworld or another map with no roaming characters
        try:
            surrounding_tile_values = get_surrounding_tile_values(
                (self.player.rect.y // TILE_SIZE, self.player.rect.x // TILE_SIZE), self.current_map.layout)
            player_surrounding_tiles = self.convert_numeric_tile_list_to_unique_tile_values(surrounding_tile_values)
            all_roaming_character_surrounding_tiles = self.get_all_roaming_character_surrounding_tiles()
            all_fixed_character_underlying_tiles = self.get_fixed_character_underlying_tiles()
            tile_types_to_draw = self.replace_characters_with_underlying_tiles([self.player.current_tile] +
                                                                               all_roaming_character_surrounding_tiles +
                                                                               all_fixed_character_underlying_tiles)
            if self.player.is_moving:
                tile_types_to_draw += self.replace_characters_with_underlying_tiles(
                    list(filter(None, player_surrounding_tiles)))
        except IndexError:
            all_roaming_character_surrounding_tiles = self.get_all_roaming_character_surrounding_tiles()
            all_fixed_character_underlying_tiles = self.get_fixed_character_underlying_tiles()
            tile_types_to_draw = self.replace_characters_with_underlying_tiles([self.player.current_tile] +
                                                                               all_roaming_character_surrounding_tiles +
                                                                               all_fixed_character_underlying_tiles)

            # tile_types_to_draw = list(filter(lambda x: not self.is_impassable(x), tile_types_to_draw))

        for tile, tile_dict in self.current_map.floor_tile_key.items():
            if tile_dict.get('group') and tile in set(tile_types_to_draw):
                tile_dict['group'].draw(self.background)

        # also check if group is in current window, default screen size is 15 tall x 16 wide
        # to make this work in all maps: draw tile under hero, AND tiles under NPCs
        # in addition to the trajectory of the NPCs
        self.handle_sprite_drawing_and_animation()
        self.screen.blit(self.background, self.camera.get_pos())
        if INITIAL_DIALOG_ENABLED:
            if self.in_initial_king_lorik_conversation():
                self.enable_movement = False
                for current_event in self.events:
                    if current_event.type == KEYUP:
                        show_text_in_dialog_box(self.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'],
                                                self.background, self.camera.get_pos(), self.current_map, self.screen)
                        self.set_to_post_initial_dialog()
                        self.enable_movement = True
            else:
                self.handle_menu_launch(self.cmd_menu)
        else:
            self.set_to_post_initial_dialog()
            self.handle_menu_launch(self.cmd_menu)

    def set_to_post_initial_dialog(self):
        self.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['is_initial_dialog'] = False
        self.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'] = \
            self.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['post_initial_dialog']

    def in_initial_king_lorik_conversation(self):
        return INITIAL_DIALOG_ENABLED and self.current_map.identifier == 'TantegelThroneRoom' and \
               self.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['is_initial_dialog']

    def handle_sprite_drawing_and_animation(self):
        for character_dict in self.current_map.characters.values():
            self.foreground_rects.append(character_dict['character_sprites'].draw(self.background)[0])
            if self.enable_animate:
                character_dict['character'].animate()
            else:
                character_dict['character'].pause()

    def get_fixed_character_underlying_tiles(self) -> List[str]:
        all_fixed_character_underlying_tiles = []
        for fixed_character in self.current_map.fixed_characters:
            fixed_character_coordinates = self.current_map.characters[fixed_character.identifier]['coordinates']
            all_fixed_character_underlying_tiles.append(
                self.current_map.get_tile_by_value(
                    self.current_map.layout[fixed_character_coordinates[0]][fixed_character_coordinates[1]]))
        return all_fixed_character_underlying_tiles

    def get_all_roaming_character_surrounding_tiles(self) -> List[str]:
        all_roaming_character_surrounding_tiles = []
        for roaming_character in self.current_map.roaming_characters:
            roaming_character_surrounding_tile_values = get_surrounding_tile_values(
                (roaming_character.rect.y // TILE_SIZE, roaming_character.rect.x // TILE_SIZE), self.current_map.layout)
            roaming_character_surrounding_tiles = self.convert_numeric_tile_list_to_unique_tile_values(
                roaming_character_surrounding_tile_values)
            for tile in roaming_character_surrounding_tiles:
                all_roaming_character_surrounding_tiles.append(tile)
        return all_roaming_character_surrounding_tiles

    def draw_all_tiles_in_current_map(self) -> None:
        for tile, tile_dict in self.current_map.floor_tile_key.items():
            if tile in self.current_map.tile_types_in_current_map:
                tile_dict['group'].draw(self.background)

    def replace_characters_with_underlying_tiles(self, tile_types_to_draw: List[str]) -> List[str]:
        for character in self.current_map.character_key.keys():
            if character in tile_types_to_draw:
                tile_types_to_draw = list(
                    map(lambda x: x.replace(character, self.current_map.character_key[character]['underlying_tile']),
                        tile_types_to_draw))
        return tile_types_to_draw

    def convert_numeric_tile_list_to_unique_tile_values(self, numeric_tile_list: List[int]) -> List[str]:
        converted_tiles = []
        for tile_value in set(numeric_tile_list):
            converted_tiles.append(self.current_map.get_tile_by_value(tile_value))
        return converted_tiles

    def handle_menu_launch(self, menu_to_launch: menu.Menu) -> None:
        if menu_to_launch.launch_signaled:
            if menu_to_launch.menu.get_id() == 'command':
                command_menu_subsurface = self.screen.subsurface(
                    (6 * TILE_SIZE,  # 11 (first empty square to the left of menu)
                     TILE_SIZE),  # 4
                    (8 * TILE_SIZE,
                     5 * TILE_SIZE)
                )
                command_menu_subsurface.fill(BLACK)
                rect = menu_to_launch.menu.draw(command_menu_subsurface)
                display.update()
            else:
                rect = None
                print("No menu launched")
            if not menu_to_launch.launched:
                self.launch_menu(menu_to_launch.menu.get_id())
            else:
                self.foreground_rects.append(rect)

    def update_screen(self) -> None:
        """Update the screen's display."""
        if self.cmd_menu.launched:
            self.cmd_menu.menu.update(self.events)
        display.update()

    def change_map(self, next_map: maps.DragonWarriorMap) -> None:
        """
        Change to a different map.
        :param next_map: The next map to be loaded.
        :return: None
        """
        self.pause_all_movement()
        self.last_map = self.current_map
        self.current_map = next_map
        fade(self.screen.get_width(), self.screen.get_height(), fade_out=True, background=self.background,
             screen=self.screen)
        self.big_map = Surface(
            (self.current_map.width, self.current_map.height)).convert()  # lgtm [py/call/wrong-arguments]
        self.big_map.fill(BLACK)
        for roaming_character in self.current_map.roaming_characters:
            roaming_character.last_roaming_clock_check = get_ticks()
            set_character_position(roaming_character)
        if self.music_enabled:
            mixer.music.stop()
        layouts = MapLayouts()
        self.current_map.layout = layouts.map_layout_lookup[self.current_map.__class__.__name__]
        current_map_staircase_dict = self.last_map.staircases[(self.player.row, self.player.column)]
        destination_coordinates = current_map_staircase_dict.get('destination_coordinates')
        if not destination_coordinates:
            self.current_map.load_map(self.player, None)
        else:
            self.current_map.layout[self.current_map.get_initial_character_location('HERO')[0][0]][
                self.current_map.get_initial_character_location('HERO')[0][1]] = \
                self.current_map.floor_tile_key[self.current_map.character_key['HERO']['underlying_tile']][
                    'val']
            if self.current_map.character_key['HERO']['underlying_tile'] != self.current_map.get_tile_by_value(
                    self.current_map.layout[destination_coordinates[0]][destination_coordinates[1]]):
                self.current_map.character_key['HERO']['underlying_tile'] = self.current_map.get_tile_by_value(
                    self.current_map.layout[destination_coordinates[0]][destination_coordinates[1]])
            self.current_map.layout[destination_coordinates[0]][destination_coordinates[1]] = 33
            self.current_map.load_map(self.player, destination_coordinates)
        destination_direction = current_map_staircase_dict.get('direction')
        if destination_direction:
            self.current_map.player.direction_value = destination_direction
        initial_hero_location = self.current_map.get_initial_character_location('HERO')
        self.player.row, self.player.column = initial_hero_location.take(0), initial_hero_location.take(1)
        self.camera = Camera(hero_position=(int(self.player.column), int(self.player.row)),
                             current_map=self.current_map, screen=self.screen)
        # self.fade(self.current_map.width, self.current_map.height, fade_out=False)
        self.loop_count = 1
        self.unpause_all_movement()
        self.tiles_moved_since_spawn = 0
        self.cmd_menu.current_map = self.current_map
        self.cmd_menu.map_name = self.current_map.__class__.__name__
        self.cmd_menu.characters = self.current_map.characters
        self.load_and_play_music(self.current_map.music_file_path)
        if destination_coordinates:
            self.camera.set_camera_position((destination_coordinates[1], destination_coordinates[0]))
        self.cmd_menu.dialog_lookup = DialogLookup(self.player)

        # play_music(self.current_map.music_file_path)

    def load_and_play_music(self, music_path):
        """Loads and plays music on repeat."""
        if self.music_enabled:
            mixer.music.load(music_path)
            mixer.music.play(-1)

    def unlaunch_menu(self, menu_to_unlaunch: menu.Menu) -> None:
        """
        Un-launch a menu.
        :return: None
        """
        menu_to_unlaunch.launch_signaled = False
        if menu_to_unlaunch.menu.get_id() == 'command':
            self.unpause_all_movement()
        menu_to_unlaunch.launched = False

    def unpause_all_movement(self) -> None:
        """
        Unpause movement of animation, roaming, and character.
        :return: None
        """
        self.enable_animate, self.enable_roaming, self.enable_movement = True, True, True
        self.paused = False

    def pause_all_movement(self) -> None:
        """
        Pause movement of animation, roaming, and character.
        :return: None
        """
        self.enable_animate, self.enable_roaming, self.enable_movement = False, False, False
        self.paused = True

    def launch_menu(self, menu_to_launch: str) -> None:
        """
        Launch either the command menu, which is used by the player to interact with the world in the game, or a dialog box.
        :param menu_to_launch:
        :return: None
        """
        if menu_to_launch == 'command':
            self.player.next_tile_id = self.get_next_tile_identifier(self.player.column, self.player.row,
                                                                     self.player.direction_value)
            if not self.cmd_menu.launched:
                play_sound(menu_button_sfx)
            self.cmd_menu.launched = True

    def move_player(self, current_key) -> None:
        """
        Move the player in a specified direction.
        :param current_key: The key currently being pressed by the user.
        """
        # TODO(ELF): Allow for key taps, to just face in a particular direction
        # block establishes direction if needed and whether to start or stop moving
        # TODO(ELF): separate dependency of camera pos and player pos
        curr_pos_x, curr_pos_y = self.camera.get_pos()

        if not self.player.is_moving:
            if current_key[K_UP] or current_key[K_w]:
                self.player.direction_value = Direction.UP.value
            elif current_key[K_DOWN] or current_key[K_s]:
                self.player.direction_value = Direction.DOWN.value
            elif current_key[K_LEFT] or current_key[K_a]:
                self.player.direction_value = Direction.LEFT.value
            elif current_key[K_RIGHT] or current_key[K_d]:
                self.player.direction_value = Direction.RIGHT.value
            else:  # player not moving and no moving key pressed
                return
            self.player.is_moving = True
        else:  # determine if player has reached new tile
            # not sure if setting the player sprites to dirty makes a difference
            self.current_map.player_sprites.dirty = 1
            if is_facing_medially(self.player):
                if curr_pos_y % TILE_SIZE == 0:
                    if not self.player.bumped:
                        self.tiles_moved_since_spawn += 1
                    self.player.is_moving, self.player.next_tile_checked = False, False
                    return
            elif is_facing_laterally(self.player):
                if curr_pos_x % TILE_SIZE == 0:
                    if not self.player.bumped:
                        self.tiles_moved_since_spawn += 1
                    else:
                        self.player.bumped = False
                    self.player.is_moving, self.player.next_tile_checked = False, False
                    return
        if is_facing_medially(self.player):
            self.move_medially(self.player)
        elif is_facing_laterally(self.player):
            self.move_laterally(self.player)
        self.current_map.player_sprites.dirty = 1

    def move_laterally(self, character: Player | RoamingCharacter) -> None:
        if is_facing_left(character):
            self.move(character, delta_x=-self.speed, delta_y=0)
        elif is_facing_right(character):
            self.move(character, delta_x=self.speed, delta_y=0)

    def move_medially(self, character: Player | RoamingCharacter) -> None:
        if is_facing_up(character):
            self.move(character, delta_x=0, delta_y=self.speed)
        elif is_facing_down(character):
            self.move(character, delta_x=0, delta_y=-self.speed)

    def move(self, character: Player | RoamingCharacter, delta_x: int, delta_y: int) -> None:
        """
        The method that actuates movement of characters from within the move_player method.
        :param character: Character to move
        :param delta_x: Change in x position.
        :param delta_y: Change in y position.
        :return: None
        """
        # coords = numpy.argwhere(self.current_map.layout_numpy_array)
        # x_min, y_min = coords.min(axis=0)
        # x_max, y_max = coords.max(axis=0)
        # b = cropped = self.current_map.layout_numpy_array[x_min:x_max + 1, y_min:y_max + 1]
        # # print(b)

        self.cmd_menu.camera_position = curr_cam_pos_x, curr_cam_pos_y = next_cam_pos_x, next_cam_pos_y = self.camera.get_pos()
        self.check_next_tile(character)
        character.next_tile_id = self.get_next_tile_identifier(character_column=character.column,
                                                               character_row=character.row,
                                                               direction_value=character.direction_value)
        character.next_next_tile_id = self.get_next_tile_identifier(character_column=character.column,
                                                                    character_row=character.row,
                                                                    direction_value=character.direction_value, offset=2)
        if self.is_impassable(character.next_tile_id):
            bump_and_reset(character, character.next_tile_id, character.next_next_tile_id)
        elif self.character_in_path(character):
            bump_and_reset(character, character.next_tile_id, character.next_next_tile_id)
        else:
            if delta_x:
                character.rect.x += delta_x
                # this causes the fade out to happen a square before the player touches a staircase
                next_cam_pos_x = curr_cam_pos_x + -delta_x
                # character.column += delta_x // 2
            if delta_y:
                character.rect.y += -delta_y
                # this causes the fade out to happen a square before the player touches a staircase
                next_cam_pos_y = curr_cam_pos_y + delta_y
                # character.row += -delta_y // 2
        if character.identifier == 'HERO' and self.enable_movement:
            self.camera.set_pos(self.move_and_handle_sides_collision(next_cam_pos_x, next_cam_pos_y))

    def check_next_tile(self, character: Player | RoamingCharacter) -> None:
        if not character.next_tile_checked or not character.next_tile_id:
            character.next_tile_id = self.get_next_tile_identifier(character_column=character.column,
                                                                   character_row=character.row,
                                                                   direction_value=character.direction_value)
        character.next_next_tile_id = self.get_next_tile_identifier(character_column=character.column,
                                                                    character_row=character.row,
                                                                    direction_value=character.direction_value, offset=2)

    def character_in_path(self, character: RoamingCharacter | FixedCharacter) -> bool:
        fixed_character_locations = [(fixed_character.column, fixed_character.row) for fixed_character in
                                     self.current_map.fixed_characters]
        roaming_character_locations = [(roaming_character.column, roaming_character.row) for roaming_character in
                                       self.current_map.roaming_characters]
        next_coordinates = self.get_next_coordinates(character.column, character.row, character.direction_value)
        return next_coordinates in fixed_character_locations + roaming_character_locations + [
            (self.player.column, self.player.row)]

    def get_next_tile_identifier(self, character_column: int, character_row: int, direction_value: int,
                                 offset: int = 1) -> str:
        """
        Retrieve the identifier (human-readable name) of the next tile in front of a particular character.
        :type character_column: int
        :type character_row: int
        :param character_column: The character's column within the map layout.
        :param character_row: The character's row within the map layout.
        :param direction_value: The direction which the character is facing.
        :param offset: How many tiles offset of the character to check. Defaults to 1 (the next tile).
        :return: str: The next tile that the character will step on (e.g., 'BRICK').
        """
        if direction_value == Direction.UP.value:
            return get_tile_id_by_coordinates(character_column, character_row - offset, self.current_map)
        elif direction_value == Direction.DOWN.value:
            return get_tile_id_by_coordinates(character_column, character_row + offset, self.current_map)
        elif direction_value == Direction.LEFT.value:
            return get_tile_id_by_coordinates(character_column - offset, character_row, self.current_map)
        elif direction_value == Direction.RIGHT.value:
            return get_tile_id_by_coordinates(character_column + offset, character_row, self.current_map)

    def get_next_coordinates(self, character_column: int, character_row: int, direction: int) -> tuple:
        if character_row < len(self.current_map.layout) and character_column < len(self.current_map.layout[0]):
            if direction == Direction.UP.value:
                return character_column, character_row - 1
            elif direction == Direction.DOWN.value:
                return character_column, character_row + 1,
            elif direction == Direction.LEFT.value:
                return character_column - 1, character_row
            elif direction == Direction.RIGHT.value:
                return character_column + 1, character_row

    def is_impassable(self, tile: str) -> bool:
        """
        Check if a tile is impassable (a tile that blocks the player from moving).
        :param tile: Tile to be checked for impassibility.
        :return: bool: A boolean value stating whether the tile is impassable.
        """
        return tile in self.current_map.impassable_tiles

    def move_and_handle_sides_collision(self, next_pos_x: int, next_pos_y: int) -> tuple:
        """
        Move while handling collision with the sides of the map (for the player).
        :type next_pos_x: int
        :type next_pos_y: int
        :param next_pos_x: Next x position (in terms of tile size).
        :param next_pos_y: Next y position (in terms of tile size).
        :return: tuple: The x, y coordinates (in terms of tile size) of the next position of the player.
        """
        max_x_bound, max_y_bound, min_bound = self.current_map.width - TILE_SIZE, self.current_map.height - TILE_SIZE, 0
        if self.player.rect.x < min_bound:
            self.player.rect.x = min_bound
            bump(self.player)
            next_pos_x += -self.speed
        elif self.player.rect.x > max_x_bound:
            self.player.rect.x = max_x_bound
            bump(self.player)
            next_pos_x += self.speed
        elif self.player.rect.y < min_bound:
            self.player.rect.y = min_bound
            bump(self.player)
            next_pos_y -= self.speed
        elif self.player.rect.y > max_y_bound:
            self.player.rect.y = max_y_bound
            bump(self.player)
            next_pos_y += self.speed
        return next_pos_x, next_pos_y

    def move_roaming_characters(self) -> None:
        """
        Move all roaming characters in the current map.
        :return: None
        """
        for roaming_character in self.current_map.roaming_characters:
            curr_pos_x, curr_pos_y = roaming_character.rect.x, roaming_character.rect.y
            # set_character_position(roaming_character)
            if roaming_character.last_roaming_clock_check is None or get_ticks() - roaming_character.last_roaming_clock_check >= 1000:
                roaming_character.last_roaming_clock_check = get_ticks()
                if not roaming_character.is_moving:
                    roaming_character.direction_value = random.choice(list(map(int, Direction)))
                else:  # character not moving and no input
                    return
                roaming_character.is_moving = True
            else:  # determine if character has reached new tile
                if is_facing_medially(roaming_character):
                    if curr_pos_y % TILE_SIZE == 0:
                        roaming_character.is_moving, roaming_character.next_tile_checked = False, False
                        return
                elif is_facing_laterally(roaming_character):
                    if curr_pos_x % TILE_SIZE == 0:
                        roaming_character.is_moving, roaming_character.next_tile_checked = False, False
                        return
            if is_facing_medially(roaming_character):
                self.move_medially(roaming_character)
            elif is_facing_laterally(roaming_character):
                self.move_laterally(roaming_character)
            # handle_roaming_character_sides_collision(self.current_map, roaming_character)


def run():
    game = Game()
    game.main()


if __name__ == "__main__":
    run()
