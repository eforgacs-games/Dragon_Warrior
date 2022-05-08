import random
import sys

from pygame import init, Surface, USEREVENT, quit, FULLSCREEN, RESIZABLE, mixer, QUIT, event, display, key, K_j, K_k, K_i, K_u, K_UP, K_w, K_DOWN, K_s, \
    K_LEFT, K_a, K_RIGHT, K_d, KEYUP
from pygame.display import set_mode, set_caption
from pygame.event import get
from pygame.time import Clock
from pygame.time import get_ticks

import src.menu as menu
from src import maps
from src.camera import Camera
from src.common import Direction, play_sound, bump_sfx, menu_button_sfx, stairs_down_sfx, stairs_up_sfx, BLACK, is_facing_medially, is_facing_laterally, \
    WHITE, intro_overture, DRAGON_QUEST_FONT_PATH, village_music, get_surrounding_tiles, convert_to_milliseconds
from src.common import get_tile_id_by_coordinates, is_facing_up, is_facing_down, is_facing_left, is_facing_right
from src.config import NES_RES, SHOW_FPS, SPLASH_SCREEN_ENABLED
from src.config import SCALE, TILE_SIZE, FULLSCREEN_ENABLED, MUSIC_ENABLED, FPS
from src.intro import draw_text, Intro
from src.maps import get_character_position, get_next_coordinates, map_lookup
from src.player.player import Player
from src.sprites.roaming_character import handle_roaming_character_sides_collision
from src.visual_effects import fade


def bump(character):
    if character.identifier == 'HERO':
        if not character.last_bump_time:
            character.last_bump_time = get_ticks()
        if get_ticks() - character.last_bump_time >= convert_to_milliseconds(15):
            character.last_bump_time = get_ticks()
            play_sound(bump_sfx)
    character.bumped = True


def bump_and_reset(character, pre_bump_next_tile, pre_bump_next_next_tile):
    if character.next_tile_id != pre_bump_next_tile:
        character.next_tile_id = pre_bump_next_tile
    if character.next_next_tile_id != pre_bump_next_next_tile:
        character.next_next_tile_id = pre_bump_next_next_tile
    bump(character)


class Game:
    GAME_TITLE = "Dragon Warrior"
    BACK_FILL_COLOR = BLACK
    MOVE_EVENT = USEREVENT + 1
    ROAMING_CHARACTER_GO_COOLDOWN = 1000

    # time.set_timer(MOVE_EVENT, 100)

    def __init__(self):
        # Initialize pygame
        self.last_map = None
        self.start_time = get_ticks()
        self.tiles_moved_since_spawn = 0
        self.loop_count = 1
        self.foreground_rects = []
        self.opacity = 0
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
        # self.win_width = current_screen_width
        # self.win_height = current_screen_height
        self.screen = set_mode((self.win_width, self.win_height), flags)
        # self.screen.set_alpha(None)
        set_caption(self.GAME_TITLE)

        # self.current_map can be changed to other maps for development purposes

        self.current_map = maps.TantegelThroneRoom()
        # self.current_map = maps.TantegelCourtyard()
        # self.current_map = maps.Alefgard()
        # self.current_map = maps.Brecconary()
        # self.current_map = maps.Garinham()

        self.big_map = Surface((self.current_map.width, self.current_map.height)).convert()  # lgtm [py/call/wrong-arguments]
        self.big_map.fill(self.BACK_FILL_COLOR)
        self.speed = 2
        for roaming_character in self.current_map.roaming_characters:
            roaming_character.last_roaming_clock_check = get_ticks()
            get_character_position(roaming_character)
        # Make the big scrollable map
        self.background = self.big_map.subsurface(0, 0, self.current_map.width, self.current_map.height).convert()
        self.player = Player(center_point=None, images=None)
        self.current_map.load_map(self.player)
        initial_hero_location = self.current_map.get_initial_character_location('HERO')
        self.player.row, self.player.column = initial_hero_location.take(0), initial_hero_location.take(1)
        self.player.current_tile = get_tile_id_by_coordinates(self.player.rect.x // TILE_SIZE, self.player.rect.y // TILE_SIZE, self.current_map)
        self.player.next_tile_id = self.get_next_tile_identifier(character_column=self.player.column,
                                                                 character_row=self.player.row,
                                                                 direction=self.current_map.player.direction)
        self.player.next_next_tile_id = self.get_next_tile_identifier(character_column=self.player.column,
                                                                      character_row=self.player.row,
                                                                      direction=self.current_map.player.direction,
                                                                      offset=3)
        self.dlg_box = menu.DialogBox(self.background, self.player.column, self.player.row)
        self.cmd_menu = menu.CommandMenu(self.background, self.player.column, self.player.row, self.player.current_tile, self.current_map,
                                         self.dlg_box, self.player)

        self.menus = self.cmd_menu, self.dlg_box
        self.camera = Camera(hero_position=(int(self.player.column), int(self.player.row)),
                             current_map=self.current_map,
                             screen=self.screen)
        self.enable_animate, self.enable_roaming, self.enable_movement = True, True, True
        self.clock = Clock()
        self.music_enabled = MUSIC_ENABLED
        if self.music_enabled:
            if SPLASH_SCREEN_ENABLED:
                mixer.music.load(intro_overture)
            else:
                mixer.music.load(self.current_map.music_file_path)
            mixer.music.play(-1)
        self.events = get()
        self.command_menu_subsurface = self.background.subsurface(
            (self.player.column - 2) * TILE_SIZE,
            (self.player.row - 6) * TILE_SIZE,
            8 * TILE_SIZE,
            5 * TILE_SIZE
        )
        self.dialog_box_subsurface = self.background.subsurface(
            TILE_SIZE,
            TILE_SIZE,
            12 * TILE_SIZE,
            5 * TILE_SIZE
        )

        # pg.event.set_allowed([pg.QUIT])

    def set_win_width_and_height(self):
        self.win_width = NES_RES[0] * self.scale
        self.win_height = NES_RES[1] * self.scale

    def main(self) -> None:
        """
        Main loop.
        :return: None
        """
        if SPLASH_SCREEN_ENABLED:
            intro = Intro()
            intro.show_start_screen(self.screen, self.start_time, self.clock, self.background)
            self.show_main_menu_screen(self.screen)
        while True:
            self.clock.tick(FPS)
            self.get_events()
            self.draw_all()
            self.update_screen()
            self.loop_count += 1

    def show_main_menu_screen(self, screen):
        main_menu_screen_enabled = True
        if self.music_enabled:
            mixer.music.load(village_music)
            mixer.music.play(-1)
        while main_menu_screen_enabled:
            screen.fill(BLACK)
            # totally dummy option for now, just a placeholder
            for i in range(256):
                draw_text(">BEGIN A NEW QUEST", 15, WHITE, screen.get_width() / 2, screen.get_height() / 2, DRAGON_QUEST_FONT_PATH, self.screen)
                display.flip()
            screen.fill(BLACK)
            for i in range(256):
                draw_text(" BEGIN A NEW QUEST", 15, WHITE, screen.get_width() / 2, screen.get_height() / 2, DRAGON_QUEST_FONT_PATH, self.screen)
                display.flip()
            screen.fill(BLACK)
            self.clock.tick(FPS)
            for current_event in get():
                if current_event.type == QUIT:
                    quit()
                    sys.exit()
                elif current_event.type == KEYUP:
                    main_menu_screen_enabled = False
        play_sound(menu_button_sfx)
        fade(screen.get_width(), screen.get_height(), fade_out=True, background=self.background, screen=self.screen)
        if self.music_enabled:
            mixer.music.load(self.current_map.music_file_path)
            mixer.music.play(-1)

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
        self.player.column = self.player.rect.x // TILE_SIZE
        self.player.row = self.player.rect.y // TILE_SIZE
        if self.enable_roaming and self.current_map.roaming_characters:
            self.move_roaming_characters()
        if self.enable_movement:
            self.move_player(current_key)
        if self.tiles_moved_since_spawn > 0:
            for staircase_location, staircase_dict in self.current_map.staircases.items():
                self.process_staircase_warps(staircase_dict, staircase_location)

        if current_key[K_j]:
            # B button
            self.unlaunch_menu(self.cmd_menu)
            self.unlaunch_menu(self.dlg_box)
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

        self.player.current_tile = get_tile_id_by_coordinates(self.player.rect.x // TILE_SIZE, self.player.rect.y // TILE_SIZE, self.current_map)
        self.cmd_menu.current_tile = self.player.current_tile

        self.player.coordinates = self.player.rect.y // TILE_SIZE, self.player.rect.x // TILE_SIZE

        self.player.next_coordinates = get_next_coordinates(self.player.rect.x // TILE_SIZE,
                                                            self.player.rect.y // TILE_SIZE,
                                                            self.player.direction)
        self.player.next_next_coordinates = get_next_coordinates(self.player.rect.x // TILE_SIZE,
                                                                 self.player.rect.y // TILE_SIZE,
                                                                 self.player.direction, offset_from_character=2)

        # Debugging area

        # This prints out the current tile that the player is standing on.
        # print(self.player.current_tile)

        # This prints out the current coordinates that the player is standing on.
        # print(self.player.coordinates)

        # This prints out the next coordinates that the player will land on.
        # print(self.player.next_coordinates)

        # This prints out the next tile that the player will land on.
        # print(get_tile_by_coordinates(self.player.next_coordinates[1], self.player.next_coordinates[0], self.current_map))

        # This prints out the current FPS.
        if SHOW_FPS:
            print(self.clock.get_fps())

        # This prints out the next tile, and the next next tile.
        # print(f'Next tile: {self.player.next_tile}')
        # print(f'Next next tile: {self.player.next_next_tile}')
        # print(f'{self.get_character_identifier_by_coordinates(self.player.next_coordinates)}')
        # print(f'{self.get_character_identifier_by_coordinates(self.player.next_next_coordinates)}')

        event.pump()

    def get_character_identifier_by_coordinates(self, coordinates):
        for character_identifier, character_info in self.current_map.characters.items():
            if character_info['coordinates'] == coordinates:
                return character_identifier
            else:
                return None

    def process_staircase_warps(self, staircase_dict: dict, staircase_location: tuple) -> None:
        if (self.player.row, self.player.column) == staircase_location:
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
        self.screen.fill(self.BACK_FILL_COLOR)
        # if isinstance(self.current_map, maps.Alefgard):
        #     # width_offset = 2336
        #     width_offset = TILE_SIZE * self.player.column + 24
        #     height_offset = TILE_SIZE * self.player.row + 25
        # else:
        width_offset = 0
        height_offset = 0
        if self.loop_count == 1:
            self.background = self.big_map.subsurface(0, 0, self.current_map.width - width_offset, self.current_map.height - height_offset)
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

        # performance optimization to only draw the tile type that the hero is standing on, and surrounding tiles
        # won't work where there are moving NPCs, so only use this in the overworld
        if not self.current_map.roaming_characters:
            # basically, if you're in the overworld, since there are no roaming characters there
            player_surrounding_tiles = self.convert_numeric_tile_list_to_unique_tile_values(
                get_surrounding_tiles(self.player.coordinates, self.current_map.layout, radius=1))
            if self.player.is_moving:
                tile_types_to_draw = list(
                    dict.fromkeys(self.replace_characters_with_underlying_tiles(set(filter(None, [self.player.current_tile] + player_surrounding_tiles)))))
            else:
                tile_types_to_draw = self.replace_characters_with_underlying_tiles([self.player.current_tile])
            if self.loop_count == 1:
                # draw everything once on the first go-around
                self.draw_all_tiles_in_current_map()
            tile_types_to_draw = list(filter(lambda x: not self.is_impassable(x), tile_types_to_draw))
            for tile, tile_dict in self.current_map.floor_tile_key.items():
                if tile in tile_types_to_draw:
                    tile_dict['group'].draw(self.background)
                # also check if group is in current window, default screen size is 15 tall x 16 wide
        else:
            # just draw everything, because you're not in the overworld, and you get 60 FPS pretty consistently even with no GPU
            # could try to optimize this later by only drawing the tiles where there's movement,
            # but the juice might not be worth the squeeze
            if self.loop_count == 1:
                self.draw_all_tiles_in_current_map()
            for tile, tile_dict in self.current_map.floor_tile_key.items():
                if tile in list(filter(lambda x: not self.is_impassable(x), self.current_map.tile_types_in_current_map)):
                    tile_dict['group'].draw(self.background)

        # to make this work in all maps: draw tile under hero, AND tiles under NPCs
        # in addition to the trajectory of the NPCs
        for character_dict in self.current_map.characters.values():
            self.foreground_rects.append(character_dict['character_sprites'].draw(self.background)[0])
            if self.enable_animate:
                character_dict['character'].animate()
            else:
                character_dict['character'].pause()
        for menu_or_dialog_box in self.menus:
            self.handle_menu_launch(menu_or_dialog_box)
        self.screen.blit(self.background, self.camera.get_pos())

    def draw_all_tiles_in_current_map(self):
        for tile, tile_dict in self.current_map.floor_tile_key.items():
            if tile in self.current_map.tile_types_in_current_map:
                tile_dict['group'].draw(self.background)

    def generate_upcoming_numeric_tiles(self):
        if self.player.row and self.player.column:
            hero_upcoming_numeric_tiles = self.get_character_upcoming_numeric_tiles(self.player.row, self.player.column)
        else:
            hero_upcoming_numeric_tiles = []
        character_upcoming_tile_list = []
        for character in self.current_map.roaming_characters:
            if character.row and character.column:
                character_upcoming_tile_list.append(self.get_character_upcoming_numeric_tiles(character.row, character.column))
            # print(f"{character}: {character.row}, {character.column}")
        character_upcoming_numeric_tiles = [item for sublist in character_upcoming_tile_list for item in sublist]
        all_upcoming_tiles = hero_upcoming_numeric_tiles + character_upcoming_numeric_tiles
        return all_upcoming_tiles, character_upcoming_numeric_tiles, character_upcoming_tile_list

    def replace_characters_with_underlying_tiles(self, tile_types_to_draw):
        for character in self.current_map.character_key.keys():
            if character in tile_types_to_draw:
                tile_types_to_draw = list(
                    map(lambda x: x.replace(character, self.current_map.character_key[character]['underlying_tile']), tile_types_to_draw))
        return tile_types_to_draw

    def convert_numeric_tile_list_to_unique_tile_values(self, numeric_tile_list):
        converted_tiles = []
        for tile_value in dict.fromkeys(numeric_tile_list):
            converted_tiles.append(self.current_map.get_tile_by_value(tile_value))
        return converted_tiles

    def get_character_upcoming_numeric_tiles(self, character_row, character_column):
        """Gets upcoming tiles in current row and column, two offset from current position."""
        upcoming_tiles_in_current_row_and_column = []
        for tile in self.current_map.layout[character_row][character_column - 4:character_column + 4]:
            upcoming_tiles_in_current_row_and_column.append(tile)
        for i in range(character_row - 4, character_row + 4):
            upcoming_tiles_in_current_row_and_column.append(self.current_map.layout[i][character_column])
        return upcoming_tiles_in_current_row_and_column

    def handle_menu_launch(self, menu_to_launch):
        if menu_to_launch.launch_signaled:
            if menu_to_launch.menu.get_id() == 'command':
                self.command_menu_subsurface = self.background.subsurface(
                    (self.player.column - 2) * TILE_SIZE,  # 11 (first empty square to the left of menu)
                    (self.player.row - 6) * TILE_SIZE,  # 4
                    8 * TILE_SIZE,
                    5 * TILE_SIZE
                )
                rect = menu.draw_menu_on_subsurface(menu_to_launch.menu, self.command_menu_subsurface)
            elif menu_to_launch.menu.get_id() == 'dialog_box':
                self.dialog_box_subsurface = self.background.subsurface(
                    # left=(self.player.column + 6) * TILE_SIZE,
                    # top=(self.player.row + 6) * TILE_SIZE,
                    TILE_SIZE,
                    TILE_SIZE,
                    12 * TILE_SIZE,
                    5 * TILE_SIZE
                )
                rect = menu.draw_menu_on_subsurface(menu_to_launch.menu, self.dialog_box_subsurface)
            else:
                rect = None
                print("No menu launched")
            if not menu_to_launch.launched:
                self.launch_menu(menu_to_launch.menu.get_id())
            else:
                self.foreground_rects.append(rect)

    def update_screen(self) -> None:
        """Update the screen's display."""
        for menu_or_dialog_box in self.menus:
            if menu_or_dialog_box.launched:
                menu_or_dialog_box.menu.update(self.events)
        display.update()

    def change_map(self, next_map) -> None:
        """
        Change to a different map.
        :param next_map: The next map to be loaded.
        :return: None
        """
        self.pause_all_movement()
        self.last_map = self.current_map
        self.current_map = next_map
        self.big_map = Surface((self.current_map.width, self.current_map.height)).convert()  # lgtm [py/call/wrong-arguments]
        fade(self.current_map.width, self.current_map.height, fade_out=True, background=self.background, screen=self.screen)
        if self.music_enabled:
            mixer.music.stop()
        self.current_map.load_map(self.player)

        initial_hero_location = self.current_map.get_initial_character_location('HERO')
        if initial_hero_location.any():
            self.player.row, self.player.column = initial_hero_location.take(0), initial_hero_location.take(1)
        else:
            if type(self.last_map) == maps.TantegelCourtyard:
                self.player.row, self.player.column = 15, 15
        self.camera = Camera(hero_position=(int(self.player.column), int(self.player.row)), current_map=self.current_map, screen=None)
        # self.fade(self.current_map.width, self.current_map.height, fade_out=False)
        self.loop_count = 1
        self.unpause_all_movement()
        self.tiles_moved_since_spawn = 0
        self.menus = self.cmd_menu, self.dlg_box
        self.cmd_menu.map_name = self.current_map.__class__.__name__
        self.cmd_menu.characters = self.current_map.characters
        if self.music_enabled:
            mixer.music.load(self.current_map.music_file_path)
            mixer.music.play(-1)

        # play_music(self.current_map.music_file_path)

    def unlaunch_menu(self, menu_obj) -> None:
        """
        Un-launch a menu.
        :return: None
        """
        menu_obj.launch_signaled = False
        if menu_obj.menu.get_id() == 'command':
            self.unpause_all_movement()
        menu_obj.launched = False

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

    def launch_menu(self, menu_to_launch) -> None:
        """
        Launch either the command menu, which is used by the player to interact with the world in the game, or a dialog box.
        :param menu_to_launch:
        :return: None
        """
        if menu_to_launch == 'command':
            self.player.next_tile_id = self.get_next_tile_identifier(self.player.column, self.player.row, self.player.direction)
            if not self.cmd_menu.launched:
                play_sound(menu_button_sfx)
            self.set_and_append_rect(self.cmd_menu.menu, self.command_menu_subsurface)
            self.cmd_menu.launched = True
        elif menu_to_launch == 'dialog_box':
            self.set_and_append_rect(self.dlg_box.menu, self.dialog_box_subsurface)
            self.dlg_box.launched = True

    def set_and_append_rect(self, menu_to_set, subsurface):
        menu_rect = menu.draw_menu_on_subsurface(menu_to_set, subsurface)
        if menu_rect:
            self.foreground_rects.append(menu_rect)

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
                self.player.direction = Direction.UP.value
            elif current_key[K_DOWN] or current_key[K_s]:
                self.player.direction = Direction.DOWN.value
            elif current_key[K_LEFT] or current_key[K_a]:
                self.player.direction = Direction.LEFT.value
            elif current_key[K_RIGHT] or current_key[K_d]:
                self.player.direction = Direction.RIGHT.value
            else:  # player not moving and no moving key pressed
                return
            self.player.is_moving = True
        else:  # determine if player has reached new tile
            self.current_map.player_sprites.dirty = 1
            if is_facing_medially(self.player):
                if curr_pos_y % TILE_SIZE == 0:
                    self.tiles_moved_since_spawn += 1
                    self.player.is_moving, self.player.next_tile_checked = False, False
                    return
            elif is_facing_laterally(self.player):
                if curr_pos_x % TILE_SIZE == 0:
                    self.tiles_moved_since_spawn += 1
                    self.player.is_moving, self.player.next_tile_checked = False, False
                    return

        self.camera.move(self.player.direction)
        if is_facing_medially(self.player):
            self.move_medially(self.player)
        elif is_facing_laterally(self.player):
            self.move_laterally(self.player)
        self.current_map.player_sprites.dirty = 1

    def move_laterally(self, character) -> None:
        if is_facing_left(character):
            self.move(character, delta_x=-self.speed, delta_y=0)
        elif is_facing_right(character):
            self.move(character, delta_x=self.speed, delta_y=0)

    def move_medially(self, character) -> None:
        if is_facing_up(character):
            self.move(character, delta_x=0, delta_y=self.speed)
        elif is_facing_down(character):
            self.move(character, delta_x=0, delta_y=-self.speed)

    def move(self, character, delta_x, delta_y) -> None:
        """
        The method that actuates movement of characters from within the move_player method.
        :param character: Character to move
        :param delta_x: Change in x position.
        :param delta_y: Change in y position.
        :return: None
        """

        curr_cam_pos_x, curr_cam_pos_y = next_cam_pos_x, next_cam_pos_y = self.camera.get_pos()
        self.check_next_tile(character)
        if self.is_impassable(character.next_tile_id):
            bump_and_reset(character, character.next_tile_id, character.next_next_tile_id)
        elif self.character_in_path(character):
            bump_and_reset(character, character.next_tile_id, character.next_next_tile_id)
        else:
            if delta_x:
                character.rect.x += delta_x
                character.column += delta_x // 2
                next_cam_pos_x = curr_cam_pos_x + -delta_x
            if delta_y:
                character.rect.y += -delta_y
                character.row += -delta_y // 2
                next_cam_pos_y = curr_cam_pos_y + delta_y
        if character.identifier == 'HERO':
            self.camera.set_pos(self.move_and_handle_sides_collision(next_cam_pos_x, next_cam_pos_y))

    def check_next_tile(self, character):
        if not character.next_tile_checked:
            character.next_tile_id = self.get_next_tile_identifier(character_column=character.column,
                                                                   character_row=character.row,
                                                                   direction=character.direction)
            character.next_next_tile_id = self.get_next_tile_identifier(character_column=character.column,
                                                                        character_row=character.row,
                                                                        direction=character.direction, offset=2)
            character.next_tile_checked = True

    def character_in_path(self, character) -> bool:
        fixed_character_locations = [(fixed_character.column, fixed_character.row) for fixed_character in
                                     self.current_map.fixed_characters]
        roaming_character_locations = [(roaming_character.column, roaming_character.row) for roaming_character in
                                       self.current_map.roaming_characters]
        return self.get_next_coordinates(character.column, character.row,
                                         character.direction) in fixed_character_locations or \
               self.get_next_coordinates(character.column,
                                         character.row,
                                         character.direction) in roaming_character_locations

    def get_next_tile_identifier(self, character_column: int, character_row: int, direction, offset=1) -> str:
        """
        Retrieve the identifier (human-readable name) of the next tile in front of a particular character.
        :type character_column: int
        :type character_row: int
        :param character_column: The character's column within the map layout.
        :param character_row: The character's row within the map layout.
        :param direction: The direction which the character is facing.
        :param offset: How many tiles offset of the character to check. Defaults to 1 (the next tile).
        :return: str: The next tile that the character will step on (e.g., 'BRICK').
        """
        if direction == Direction.UP.value:
            return get_tile_id_by_coordinates(character_column, character_row - offset, self.current_map)
        elif direction == Direction.DOWN.value:
            return get_tile_id_by_coordinates(character_column, character_row + offset, self.current_map)
        elif direction == Direction.LEFT.value:
            return get_tile_id_by_coordinates(character_column - offset, character_row, self.current_map)
        elif direction == Direction.RIGHT.value:
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
            get_character_position(roaming_character)
            if roaming_character.last_roaming_clock_check is None:
                roaming_character.last_roaming_clock_check = get_ticks()
            if get_ticks() - roaming_character.last_roaming_clock_check >= self.ROAMING_CHARACTER_GO_COOLDOWN:
                roaming_character.last_roaming_clock_check = get_ticks()
                if not roaming_character.is_moving:
                    roaming_character.direction = random.choice(list(map(int, Direction)))
                else:  # character not moving and no input
                    return
                roaming_character.is_moving = True
            else:  # determine if character has reached new tile
                if is_facing_medially(roaming_character):
                    if roaming_character.rect.y % TILE_SIZE == 0:
                        roaming_character.is_moving, roaming_character.next_tile_checked = False, False
                        return
                elif is_facing_laterally(roaming_character):
                    if roaming_character.rect.x % TILE_SIZE == 0:
                        roaming_character.is_moving, roaming_character.next_tile_checked = False, False
                        return
            if is_facing_medially(roaming_character):
                self.move_medially(roaming_character)
            elif is_facing_laterally(roaming_character):
                self.move_laterally(roaming_character)
            handle_roaming_character_sides_collision(self.current_map, roaming_character)


def run():
    game = Game()
    game.main()


if __name__ == "__main__":
    run()
