"""
MapManager — owns all map-transition and warp logic that previously lived on Game.

Holds change_map and its helpers.  Game keeps a reference to this object and
delegates to it; MapManager holds a back-reference to Game so it can reach
shared resources (player, camera, screen, music_player, …).
"""

from pygame import Surface
from pygame.time import get_ticks

from src import maps
from src.camera import Camera
from src.common import BLACK
from src.direction import Direction
from src.game_functions import set_character_position
from src.maps import map_lookup
from src.menu import CommandMenu
from src.visual_effects import fade


class MapManager:
    def __init__(self, game):
        self.game = game

    # ------------------------------------------------------------------ #
    #  Properties forwarding to game                                       #
    # ------------------------------------------------------------------ #

    @property
    def player(self):
        return self.game.player

    @property
    def current_map(self):
        return self.game.current_map

    @current_map.setter
    def current_map(self, value):
        self.game.current_map = value

    @property
    def last_map(self):
        return self.game.last_map

    @last_map.setter
    def last_map(self, value):
        self.game.last_map = value

    @property
    def screen(self):
        return self.game.screen

    @property
    def config(self):
        return self.game.config

    @property
    def tile_size(self):
        return self.game.tile_size

    @property
    def layouts(self):
        return self.game.layouts

    @property
    def music_enabled(self):
        return self.game.music_enabled

    @property
    def music_player(self):
        return self.game.music_player

    @property
    def sound(self):
        return self.game.sound

    @property
    def directories(self):
        return self.game.directories

    @property
    def drawer(self):
        return self.game.drawer

    @property
    def game_state(self):
        return self.game.game_state

    # ------------------------------------------------------------------ #
    #  Warp detection                                                      #
    # ------------------------------------------------------------------ #

    def handle_warps(self):
        immediate_move_maps = ('Brecconary', 'Cantlin', 'Hauksness', 'Rimuldar', 'CharlockB1', 'MagicTemple',
                               'Alefgard', 'MountainCaveB1', 'MountainCaveB2')
        if self.game.auto_stairs:
            movement_threshold = self.game.tiles_moved_since_spawn > 0
        else:
            movement_threshold = self.game.tiles_moved_since_spawn > 2 or (
                self.game.tiles_moved_since_spawn > 1 and self.current_map.identifier in immediate_move_maps)

        if movement_threshold:
            for staircase_location, staircase_dict in self.current_map.staircases.items():
                if (self.player.row, self.player.column) == staircase_location:
                    self.process_warp(staircase_dict)
                    break

    def process_warp(self, staircase_dict):
        self.player.bumped = False
        match staircase_dict['stair_direction']:
            case 'down':
                self.sound.play_sound(self.directories.stairs_down_sfx)
            case 'up':
                self.sound.play_sound(self.directories.stairs_up_sfx)
        next_map = map_lookup[staircase_dict['map']](self.config)
        self.change_map(next_map)

    # ------------------------------------------------------------------ #
    #  Map change                                                          #
    # ------------------------------------------------------------------ #

    def change_map(self, next_map: maps.DragonWarriorMap) -> None:
        """Change to a different map."""
        if self.last_map is not None:
            came_from_throne_room = self.current_map.identifier == 'TantegelThroneRoom'
            came_from_courtyard = self.current_map.identifier == 'TantegelCourtyard'
        else:
            came_from_throne_room = True
            came_from_courtyard = False
        self.game_state.pause_all_movement()
        self.last_map = self.current_map
        self.current_map = next_map
        moving_within_tantegel_castle = came_from_throne_room or came_from_courtyard
        if not self.game.allow_save_prompt:
            if came_from_throne_room:
                self.game.allow_save_prompt = True
        self.current_map.layout = self.layouts.map_layout_lookup[self.current_map.__class__.__name__]
        fade(fade_out=True, screen=self.screen, config=self.game_state.config)
        self.set_big_map()
        self.set_roaming_character_positions()
        if self.music_enabled:
            if not moving_within_tantegel_castle and not self.config['ORCHESTRA_MUSIC_ENABLED']:
                from pygame import mixer
                mixer.music.stop()
        if not self.player.is_dead:
            current_map_staircase_dict = self.last_map.staircases[(self.player.row, self.player.column)]
            destination_coordinates = current_map_staircase_dict.get('destination_coordinates')
        else:
            current_map_staircase_dict = None
            destination_coordinates = (10, 13)  # TantegelThroneRoom, in front of King Lorik
        self.current_map.destination_coordinates = destination_coordinates
        if destination_coordinates:
            self.set_underlying_tiles_on_map_change(destination_coordinates)
        self.current_map.load_map(self.player, destination_coordinates, self.tile_size)
        if not self.current_map.is_dark:
            self.game.torch_active = False
            self.game_state.radiant_active = False
        self.handle_player_direction_on_map_change(current_map_staircase_dict)
        self.game.camera = Camera(hero_position=(int(self.player.column), int(self.player.row)),
                                  current_map=self.current_map, screen=self.screen, tile_size=self.tile_size)
        self.game.loop_count = 1
        self.game_state.unpause_all_movement()
        self.game.tiles_moved_since_spawn = 0
        self.game.cmd_menu = CommandMenu(self.game)
        # TODO: Allow music to continue playing when moving within Tantegel Castle.
        self.music_player.load_and_play_music(self.current_map.music_file_path)
        if destination_coordinates:
            self.game.camera.set_camera_position((destination_coordinates[1], destination_coordinates[0]),
                                                 self.tile_size)
        self.drawer.draw_all(self.screen, self.game.loop_count, self.game.big_map, self.current_map, self.player,
                             self.game.cmd_menu, self.game.foreground_rects, self.game.enable_animate,
                             self.game.camera, self.game.initial_dialog_enabled, self.game.events,
                             self.game.skip_text, self.game.allow_save_prompt, self.game_state,
                             self.game.torch_active, self.game.color)
        fade(fade_out=False, screen=self.screen, config=self.game_state.config)

    def set_underlying_tiles_on_map_change(self, destination_coordinates):
        if self.player.current_tile in ('BRICK_STAIR_DOWN', 'GRASS_STAIR_DOWN', 'CAVE'):
            self.current_map.character_key['HERO']['underlying_tile'] = 'BRICK_STAIR_UP'
        elif self.player.current_tile == 'BRICK_STAIR_UP' and self.current_map.identifier != 'Alefgard':
            self.current_map.character_key['HERO']['underlying_tile'] = 'BRICK_STAIR_DOWN'
        else:
            self.current_map.character_key['HERO']['underlying_tile'] = self.current_map.get_tile_by_value(
                self.current_map.layout[destination_coordinates[0]][destination_coordinates[1]])

    def set_big_map(self):
        self.game.big_map = Surface(
            (self.current_map.width, self.current_map.height)).convert()
        self.game.big_map.fill(BLACK)
        self.drawer.background = self.game.big_map.subsurface(0, 0, self.current_map.width,
                                                               self.current_map.height).convert_alpha()

    def handle_player_direction_on_map_change(self, current_map_staircase_dict):
        if not self.player.is_dead:
            destination_direction = current_map_staircase_dict.get('direction')
            if destination_direction:
                self.player.direction_value = destination_direction
        else:
            self.player.direction_value = Direction.UP.value

    def set_roaming_character_positions(self):
        for roaming_character in self.current_map.roaming_characters:
            roaming_character.last_roaming_clock_check = get_ticks()
            set_character_position(roaming_character, self.tile_size)
