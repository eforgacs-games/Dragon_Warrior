import random
import sys

from pygame import init, Surface, USEREVENT, quit, FULLSCREEN, RESIZABLE, DOUBLEBUF, mixer, QUIT, event, display, time, \
    key, K_j, K_k, K_i, K_u, K_UP, K_w, K_DOWN, K_s, K_LEFT, K_a, K_RIGHT, K_d, surface
from pygame.display import set_mode, set_caption
from pygame.event import get
from pygame.time import Clock
from pygame.time import get_ticks

import src.menu as menu
from src import maps
from src.camera import Camera
from src.common import Direction, play_sound, bump_sfx, menu_button_sfx, stairs_down_sfx, stairs_up_sfx, BLACK, is_facing_medially, is_facing_laterally
from src.common import get_tile_by_coordinates, is_facing_up, is_facing_down, is_facing_left, is_facing_right
from src.config import NES_RES, SHOW_FPS
from src.config import SCALE, TILE_SIZE, FULLSCREEN_ENABLED, MUSIC_ENABLED, FPS
from src.maps import get_character_position, get_next_coordinates, map_lookup
from src.player.player import Player
from src.sprites.roaming_character import handle_roaming_character_sides_collision


def draw_menu_on_subsurface(menu_to_draw, subsurface):
    return menu_to_draw.draw(subsurface)


class Game:
    GAME_TITLE = "Dragon Warrior"
    BACK_FILL_COLOR = BLACK
    MOVE_EVENT = USEREVENT + 1
    ROAMING_CHARACTER_GO_COOLDOWN = 3000

    # time.set_timer(MOVE_EVENT, 100)

    def __init__(self):
        # Initialize pygame
        self.tiles_moved_since_spawn = 0
        self.loop_count = 1
        self.foreground_rects = []
        self.opacity = 0
        init()

        self.paused = False
        # Create the game window.
        if FULLSCREEN_ENABLED:
            flags = FULLSCREEN | DOUBLEBUF
        else:
            flags = RESIZABLE | DOUBLEBUF
        self.scale = SCALE
        # video_infos = display.Info()
        # current_screen_width, current_screen_height = video_infos.current_w, video_infos.current_h
        self.win_width, self.win_height = NES_RES[0] * self.scale, NES_RES[1] * self.scale
        # self.win_width = current_screen_width
        # self.win_height = current_screen_height
        self.screen = set_mode((self.win_width, self.win_height), flags)
        # self.screen.set_alpha(None)
        set_caption(self.GAME_TITLE)
        self.next_tile_checked = False

        # self.current_map can be changed to other maps for development purposes

        self.current_map = maps.TantegelThroneRoom()
        # self.current_map = maps.TantegelCourtyard()
        # self.current_map = maps.Alefgard()
        # self.current_map = maps.Brecconary()
        # self.current_map = maps.Garinham()
        # self.current_map = maps.TestMap(hero_images=self.unarmed_hero_images)
        self.big_map = Surface((self.current_map.width, self.current_map.height)).convert()  # lgtm [py/call/wrong-arguments]
        self.big_map.fill(self.BACK_FILL_COLOR)
        self.speed = 2
        for roaming_character in self.current_map.roaming_characters:
            roaming_character.last_roaming_clock_check = get_ticks()
            get_character_position(roaming_character)
        # Make the big scrollable map
        self.background = self.big_map.subsurface(0, 0, self.current_map.width,
                                                  self.current_map.height).convert()
        self.player = Player(center_point=None, images=None)
        self.current_map.load_map(self.player)
        initial_hero_location = self.current_map.get_initial_character_location('HERO')
        self.hero_layout_row, self.hero_layout_column = initial_hero_location.take(0), initial_hero_location.take(1)
        self.current_tile = get_tile_by_coordinates(self.player.rect.x // TILE_SIZE, self.player.rect.y // TILE_SIZE, self.current_map)
        self.player.next_tile = self.get_next_tile_identifier(character_column=self.hero_layout_column,
                                                              character_row=self.hero_layout_row,
                                                              direction=self.current_map.player.direction)
        self.player.next_next_tile = self.get_next_tile_identifier(character_column=self.hero_layout_column,
                                                                   character_row=self.hero_layout_row,
                                                                   direction=self.current_map.player.direction,
                                                                   offset=3)
        self.dlg_box = menu.DialogBox(self.background, self.hero_layout_column, self.hero_layout_row)
        self.cmd_menu = menu.CommandMenu(self.background, self.hero_layout_column, self.hero_layout_row, self.current_tile, self.current_map.characters,
                                         self.dlg_box, self.player, self.current_map.__class__.__name__)

        self.menus = self.cmd_menu, self.dlg_box
        self.camera = Camera(hero_position=(int(self.hero_layout_column), int(self.hero_layout_row)), current_map=self.current_map)
        self.enable_animate, self.enable_roaming, self.enable_movement = True, True, True
        self.clock = Clock()
        if MUSIC_ENABLED:
            mixer.music.load(self.current_map.music_file_path)
            mixer.music.play(-1)
        self.events = get()
        self.command_menu_subsurface = self.set_background_subsurface(
            left=(self.hero_layout_column - 2) * TILE_SIZE,
            top=(self.hero_layout_row - 6) * TILE_SIZE,
            width=8 * TILE_SIZE,
            height=5 * TILE_SIZE
        )
        self.dialog_box_subsurface = self.set_background_subsurface(
            left=TILE_SIZE,
            top=TILE_SIZE,
            width=12 * TILE_SIZE,
            height=5 * TILE_SIZE
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
        while True:
            self.clock.tick(FPS)
            self.get_events()
            self.draw_all()
            self.update_screen()
            self.loop_count += 1

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
        self.hero_layout_column = self.player.rect.x // TILE_SIZE
        self.hero_layout_row = self.player.rect.y // TILE_SIZE
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

        self.current_tile = get_tile_by_coordinates(self.player.rect.x // TILE_SIZE, self.player.rect.y // TILE_SIZE, self.current_map)
        self.cmd_menu.current_tile = self.current_tile

        self.player.coordinates = self.player.rect.y // TILE_SIZE, self.player.rect.x // TILE_SIZE

        self.player.next_coordinates = get_next_coordinates(self.player.rect.x // TILE_SIZE,
                                                            self.player.rect.y // TILE_SIZE,
                                                            self.player.direction)
        self.player.next_next_coordinates = get_next_coordinates(self.player.rect.x // TILE_SIZE,
                                                                 self.player.rect.y // TILE_SIZE,
                                                                 self.player.direction, offset_from_character=2)

        # Debugging area

        # This prints out the current tile that the player is standing on.
        # print(self.current_tile)

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
        if (self.hero_layout_row, self.hero_layout_column) == staircase_location:
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
        if self.loop_count == 1:
            self.background = self.big_map.subsurface(0, 0, self.current_map.width, self.current_map.height)
        # TODO: this for loop is what is slowing down the overworld map.
        #  make it so that this only executes while moving, or else just draws the squares where there are characters
        for tile, tile_dict in self.current_map.floor_tile_key.items():
            # group = tile_dict.get('group')
            # if group:
            #     group.draw(self.big_map)
            if tile in self.current_map.tiles_in_current_map:
                tile_dict['group'].draw(self.big_map)
                # screen_coordinates = self.screen.get_rect()
                # for sprites in group.sprites():
                # also check if group is in current window, default screen size is 15 tall x 16 wide
        for character_dict in self.current_map.characters.values():
            self.foreground_rects.append(character_dict['character_sprites'].draw(self.background)[0])
            if self.enable_animate:
                character_dict['character'].animate()
            else:
                character_dict['character'].pause()
        for menu_or_dialog_box in self.menus:
            self.handle_menu_launch(menu_or_dialog_box)
        self.screen.blit(self.background, self.camera.get_pos())

    def handle_menu_launch(self, menu_to_launch):
        if menu_to_launch.launch_signaled:
            if menu_to_launch.menu.get_id() == 'command':
                self.command_menu_subsurface = self.set_background_subsurface(
                    left=(self.hero_layout_column - 2) * TILE_SIZE,  # 11 (first empty square to the left of menu)
                    top=(self.hero_layout_row - 6) * TILE_SIZE,  # 4
                    width=8 * TILE_SIZE,
                    height=5 * TILE_SIZE
                )
                rect = draw_menu_on_subsurface(menu_to_launch.menu, self.command_menu_subsurface)
            elif menu_to_launch.menu.get_id() == 'dialog_box':
                self.dialog_box_subsurface = self.set_background_subsurface(
                    # left=(self.hero_layout_column + 6) * TILE_SIZE,
                    # top=(self.hero_layout_row + 6) * TILE_SIZE,
                    left=TILE_SIZE,
                    top=TILE_SIZE,
                    width=12 * TILE_SIZE,
                    height=5 * TILE_SIZE
                )
                rect = draw_menu_on_subsurface(menu_to_launch.menu, self.dialog_box_subsurface)
            else:
                rect = None
                print("No menu launched")
            if not menu_to_launch.launched:
                self.launch_menu(menu_to_launch.menu.get_id())
            else:
                self.foreground_rects.append(rect)

    def set_background_subsurface(self, left, top, width, height) -> surface.Surface:
        return self.background.subsurface(
            left,
            top,
            width,
            height
        )

    def update_screen(self) -> None:
        """Update the screen's display."""
        for menu_or_dialog_box in self.menus:
            if menu_or_dialog_box.launched:
                menu_or_dialog_box.menu.update(self.events)
        display.update()

    def fade(self, width: int, height: int, fade_out: bool) -> None:
        """
        Fade to/from current scene to/from black.
        :return: None
        @param width: int
        Width of surface to fade.
        @param height:
        Height of surface to fade.
        @type fade_out: bool
        If true, fades out. If false, fades in.
        """
        fade = Surface((width, height))  # lgtm [py/call/wrong-arguments]
        fade.fill(BLACK)
        self.opacity = 0
        for alpha in range(300):
            if fade_out:
                self.opacity += 1
            else:
                # TODO(ELF): Fix fade in. Maybe this link will help? https://stackoverflow.com/questions/54881269/pygame-fade-to-black-function
                self.opacity -= 1
            fade.set_alpha(self.opacity)
            self.background.fill(BLACK)
            self.screen.blit(fade, (0, 0))
            display.update()
            time.delay(5)

    def change_map(self, next_map) -> None:
        """
        Change to a different map.
        :param next_map: The next map to be loaded.
        :return: None
        """
        # TODO(ELF): Reset location so that talk function works.
        self.pause_all_movement()
        self.current_map = next_map
        self.big_map = Surface((self.current_map.width, self.current_map.height)).convert()  # lgtm [py/call/wrong-arguments]
        self.fade(self.win_width, self.win_height, fade_out=True)
        if MUSIC_ENABLED:
            mixer.music.stop()
        self.current_map.load_map(self.player)

        initial_hero_location = self.current_map.get_initial_character_location('HERO')
        self.hero_layout_row, self.hero_layout_column = initial_hero_location.take(0), initial_hero_location.take(1)
        self.camera = Camera(hero_position=(int(self.hero_layout_column), int(self.hero_layout_row)), current_map=self.current_map)
        self.fade(self.win_width, self.win_height, fade_out=False)
        self.loop_count = 1
        self.unpause_all_movement()
        self.tiles_moved_since_spawn = 0
        self.cmd_menu.map_name = self.current_map.__class__.__name__
        if MUSIC_ENABLED:
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
            self.player.next_tile = self.get_next_tile_identifier(self.hero_layout_column, self.hero_layout_row, self.player.direction)
            if not self.cmd_menu.launched:
                play_sound(menu_button_sfx)
            self.set_and_append_rect(self.cmd_menu.menu, self.command_menu_subsurface)
            self.cmd_menu.launched = True
        elif menu_to_launch == 'dialog_box':
            self.set_and_append_rect(self.dlg_box.menu, self.dialog_box_subsurface)
            self.dlg_box.launched = True

    def set_and_append_rect(self, menu_to_set, subsurface):
        menu_rect = draw_menu_on_subsurface(menu_to_set, subsurface)
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
                    self.player.is_moving, self.next_tile_checked = False, False
                    return
            elif is_facing_laterally(self.player):
                if curr_pos_x % TILE_SIZE == 0:
                    self.tiles_moved_since_spawn += 1
                    self.player.is_moving, self.next_tile_checked = False, False
                    return

        self.camera.move(self.player.direction)
        if is_facing_medially(self.player):
            self.move_medially(self.player)
        elif is_facing_laterally(self.player):
            self.move_laterally(self.player)
        self.current_map.player_sprites.dirty = 1

    def move_laterally(self, character) -> None:
        if is_facing_left(character):
            if character.identifier == "HERO":
                self.move(delta_x=-self.speed, delta_y=0)
            else:
                self.move_roaming_character(character, delta_x=-self.speed, delta_y=0)
        elif is_facing_right(character):
            if character.identifier == "HERO":
                self.move(delta_x=self.speed, delta_y=0)
            else:
                self.move_roaming_character(character, delta_x=self.speed, delta_y=0)

    def move_medially(self, character) -> None:
        if is_facing_up(character):
            if character.identifier == "HERO":
                self.move(delta_x=0, delta_y=self.speed)
            else:
                self.move_roaming_character(character, delta_x=0, delta_y=self.speed)
        elif is_facing_down(character):
            if character.identifier == "HERO":
                self.move(delta_x=0, delta_y=-self.speed)
            else:
                self.move_roaming_character(character, delta_x=0, delta_y=-self.speed)

    def move(self, delta_x, delta_y) -> None:
        """
        The method that actuates the movement of the player from within the move_player method.
        :param delta_x: Change in x position.
        :param delta_y: Change in y position.
        :return: None
        """
        curr_cam_pos_x, curr_cam_pos_y = self.camera.get_pos()
        next_cam_pos_x, next_cam_pos_y = curr_cam_pos_x, curr_cam_pos_y
        pre_bump_next_tile = self.player.next_tile
        pre_bump_next_next_tile = self.player.next_next_tile
        if not self.next_tile_checked:
            self.player.next_tile = self.get_next_tile_identifier(character_column=self.hero_layout_column,
                                                                  character_row=self.hero_layout_row,
                                                                  direction=self.player.direction)
            self.player.next_next_tile = self.get_next_tile_identifier(character_column=self.hero_layout_column,
                                                                       character_row=self.hero_layout_row,
                                                                       direction=self.player.direction, offset=3)
            self.next_tile_checked = True

        if not self.is_impassable(self.player.next_tile):
            if not self.character_in_path_of_player():
                if delta_x:
                    self.player.rect.x += delta_x
                    next_cam_pos_x = curr_cam_pos_x + -delta_x
                if delta_y:
                    self.player.rect.y += -delta_y
                    next_cam_pos_y = curr_cam_pos_y + delta_y
            else:
                self.bump_and_reset(pre_bump_next_tile, pre_bump_next_next_tile)

        else:
            self.bump_and_reset(pre_bump_next_tile, pre_bump_next_next_tile)

        next_cam_pos_x, next_cam_pos_y = self.handle_sides_collision(next_cam_pos_x, next_cam_pos_y)
        self.camera.set_pos((next_cam_pos_x, next_cam_pos_y))

    def bump_and_reset(self, pre_bump_next_tile, pre_bump_next_next_tile):
        if self.player.next_tile != pre_bump_next_tile:
            self.player.next_tile = pre_bump_next_tile
        if self.player.next_next_tile != pre_bump_next_next_tile:
            self.player.next_next_tile = pre_bump_next_next_tile
        self.bump()

    def bump(self):
        play_sound(bump_sfx)
        self.player.bumped = True

    def character_in_path_of_player(self) -> bool:
        fixed_character_locations = [(fixed_character.column, fixed_character.row) for fixed_character in
                                     self.current_map.fixed_characters]
        roaming_character_locations = [(roaming_character.column, roaming_character.row) for roaming_character in
                                       self.current_map.roaming_characters]
        return self.get_next_coordinates(self.hero_layout_column, self.hero_layout_row,
                                         self.player.direction) in fixed_character_locations or self.get_next_coordinates(self.hero_layout_column,
                                                                                                                          self.hero_layout_row,
                                                                                                                          self.player.direction) in roaming_character_locations

    def get_next_tile_identifier(self, character_column: int, character_row: int, direction, offset=1) -> str:
        """
        Retrieve the next tile in front of a particular character.
        :type character_column: int
        :type character_row: int
        :param character_column: The character's column within the map layout.
        :param character_row: The character's row within the map layout.
        :param direction: The direction which the character is facing.
        :param offset: How many tiles offset of the character to check. Defaults to 1 (the next tile).
        :return: str: The next tile that the character will step on (e.g., 'BRICK').
        """
        if direction == Direction.UP.value:
            return get_tile_by_coordinates(character_column, character_row - offset, self.current_map)
        elif direction == Direction.DOWN.value:
            return get_tile_by_coordinates(character_column, character_row + offset, self.current_map)
        elif direction == Direction.LEFT.value:
            return get_tile_by_coordinates(character_column - offset, character_row, self.current_map)
        elif direction == Direction.RIGHT.value:
            return get_tile_by_coordinates(character_column + offset, character_row, self.current_map)

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

    def handle_sides_collision(self, next_pos_x: int, next_pos_y: int) -> tuple:
        """
        Handle collision with the sides of the map (for the player).
        :type next_pos_x: int
        :type next_pos_y: int
        :param next_pos_x: Next x position (in terms of tile size).
        :param next_pos_y: Next y position (in terms of tile size).
        :return: tuple: The x, y coordinates (in terms of tile size) of the next position of the player.
        """
        max_x_bound, max_y_bound, min_bound = self.current_map.width - TILE_SIZE, self.current_map.height - TILE_SIZE, 0
        if self.player.rect.x < min_bound:
            self.player.rect.x = min_bound
            self.bump()
            next_pos_x += -self.speed
        elif self.player.rect.x > max_x_bound:
            self.player.rect.x = max_x_bound
            self.bump()
            next_pos_x += self.speed
        elif self.player.rect.y < min_bound:
            self.player.rect.y = min_bound
            self.bump()
            next_pos_y -= self.speed
        elif self.player.rect.y > max_y_bound:
            self.player.rect.y = max_y_bound
            self.bump()
            next_pos_y += self.speed
        return next_pos_x, next_pos_y

    def move_roaming_characters(self) -> None:
        """
        Move all roaming characters in the current map.
        :return: None
        """
        for roaming_character in self.current_map.roaming_characters:
            get_character_position(roaming_character)
            now = get_ticks()
            if roaming_character.last_roaming_clock_check is None:
                roaming_character.last_roaming_clock_check = now
            if now - roaming_character.last_roaming_clock_check >= self.ROAMING_CHARACTER_GO_COOLDOWN:
                roaming_character.last_roaming_clock_check = now
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

    def move_roaming_character(self, roaming_character, delta_x, delta_y) -> None:
        """
        The method that actuates the movement of the roaming characters from within the move_roaming_characters method.
        :param delta_x: Change in x position.
        :param delta_y: Change in y position.
        :param roaming_character: Roaming character to be moved.
        :return: None
        """
        next_coordinates = get_next_coordinates(roaming_character.column, roaming_character.row, roaming_character.direction)
        if not roaming_character.next_tile_checked:
            roaming_character.next_tile = self.get_next_tile_identifier(character_column=roaming_character.column,
                                                                        character_row=roaming_character.row,
                                                                        direction=roaming_character.direction)

            roaming_character.next_tile_checked = True
        if not self.is_impassable(roaming_character.next_tile) and (
                roaming_character.column, roaming_character.row) != (self.hero_layout_column, self.hero_layout_row):
            character_value = self.current_map.character_key[roaming_character.identifier]['val']
            underlying_tile_val = self.current_map.tile_key[self.current_map.character_key[roaming_character.identifier]['underlying_tile']]['val']
            if delta_x:
                # set current coordinates to underlying tile value
                self.current_map.layout[roaming_character.row][roaming_character.column] = underlying_tile_val
                # set next coordinates to roaming character value
                self.current_map.layout[next_coordinates[0]][next_coordinates[1]] = character_value
                roaming_character.rect.x += delta_x
                roaming_character.column += delta_x // 2

            if delta_y:
                # set current coordinates to underlying tile value
                self.current_map.layout[roaming_character.row][roaming_character.column] = underlying_tile_val
                # set next coordinates to roaming character value
                self.current_map.layout[next_coordinates[0]][next_coordinates[1]] = character_value
                roaming_character.rect.y += -delta_y
                roaming_character.row += -delta_y // 2


def run():
    game = Game()
    game.main()


if __name__ == "__main__":
    run()
