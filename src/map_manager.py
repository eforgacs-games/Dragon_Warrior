"""
MapManager — owns all map-transition and warp logic that previously lived on Game.

Holds change_map and its helpers.  Game keeps a reference to this object and
delegates to it; MapManager holds a back-reference to Game so it can reach
shared resources (player, camera, screen, music_player, …).
"""

from pygame import Surface

from src import maps
from src.camera import Camera
from src.common import BLACK
from src.constants import RAINBOW_BRIDGE_COORDINATES, THRONE_ROOM_DOOR_COORDINATES
from src.direction import Direction
from src.game_functions import set_character_position
from src.map_layouts import BRICK, TREASURE_BOX
from src.maps import map_lookup
from src.menu import CommandMenu
from src.visual_effects import cut_to_black, screen_fade


class MapManager:
    def __init__(self, game):
        self.game = game
        # The (row, column) of the stairs a random fight started on: the hero stays there after the fight, and the
        # stairs aren't taken until the hero steps off them (or uses STAIRS). See stay_on_stairs.
        self.fought_on_stairs: tuple[int, int] | None = None

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

    def stay_on_stairs(self, row: int, column: int) -> None:
        """A random fight has just started on the block the hero stepped onto (Bank03 CheckBlockDmg -> DoRandomFight).
        The NES never takes stairs on its own: only the STAIRS command does (ChkStairsUp/Down), so after the fight the
        hero is still standing on them. Here stairs are taken by stepping onto them, so that step's warp is held back
        until the hero steps off (or uses STAIRS), instead of happening in the frame right after the fight."""
        self.fought_on_stairs = row, column

    def handle_warps(self):
        if self.fought_on_stairs is not None:
            if self.fought_on_stairs == (self.player.row, self.player.column):
                return
            self.fought_on_stairs = None
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

    def change_map(self, next_map: maps.DragonWarriorMap, destination_coordinates: tuple | None = None,
                   direction: int | None = None, fade_out_first: bool = True) -> None:
        """Change to a different map. Pass destination_coordinates (and optionally direction) to warp somewhere other
        than where the staircase the player is standing on leads, e.g. for RETURN or when loading a save.
        fade_out_first=False cuts straight to black instead of fading the old screen out, as NES StartAtThroneRoom
        (Bank03, LCB47) does: it loads BlackPalPtr at once and changes maps with MapChngNoSound (Bank00, LB091),
        which skips ScreenFadeOut, so the only fade is MapChngNoSound's PalFadeIn."""
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
        self.current_map.layout = self.layouts.map_layout_lookup[self.current_map.__class__.__name__]
        self.apply_rainbow_bridge()
        if isinstance(self.current_map, maps.CharlockB1) and self.game.story_flags.charlock_stairs_revealed:
            # NES GetBlockID: once F_PSG_FOUND is set, the block behind the throne reads as stairs down for good
            self.current_map.reveal_hidden_staircase()
        self.apply_chest_history()
        self.place_princess_gwaelin()
        if self.game.story_flags.dragonlord_defeated:
            self.current_map.apply_dragonlord_defeated()
        if fade_out_first:
            # NES ScreenFadeOut ($A743) -> PalFadeOut, for MapChngWithSound and MapChngFadeNoSound
            screen_fade(fade_out=True, screen=self.screen, config=self.game_state.config)
        else:
            cut_to_black(self.screen, self.game_state.config)
        self.set_big_map()
        self.set_roaming_character_positions()
        if not moving_within_tantegel_castle and not self.config['ORCHESTRA_MUSIC_ENABLED']:
            self.music_player.stop_music()
        is_warp = destination_coordinates is not None
        if is_warp:
            current_map_staircase_dict = None
        elif not self.player.is_dead:
            current_map_staircase_dict = self.last_map.staircases[(self.player.row, self.player.column)]
            destination_coordinates = current_map_staircase_dict.get('destination_coordinates')
        else:
            current_map_staircase_dict = None
            destination_coordinates = (10, 13)  # TantegelThroneRoom, in front of King Lorik
        self.current_map.destination_coordinates = destination_coordinates
        if is_warp and destination_coordinates is not None:
            # Not arriving by stairs, so the hero stands on whatever tile is at the destination
            row, column = destination_coordinates
            self.current_map.character_key['HERO']['underlying_tile'] = self.current_map.get_tile_by_value(
                self.current_map.layout[row][column])
        elif destination_coordinates:
            self.set_underlying_tiles_on_map_change(destination_coordinates)
        self.current_map.load_map(self.player, destination_coordinates, self.tile_size)
        if not self.current_map.is_dark:
            self.game_state.reset_light()
        if direction is not None:
            self.player.direction_value = direction
        elif current_map_staircase_dict is not None or self.player.is_dead:
            self.handle_player_direction_on_map_change(current_map_staircase_dict)
        self.game.camera = Camera(hero_position=(int(self.player.column), int(self.player.row)),
                                  current_map=self.current_map, screen=self.screen, tile_size=self.tile_size)
        self.game.loop_count = 1
        self.game_state.unpause_all_movement()
        self.game.tiles_moved_since_spawn = 0
        self.fought_on_stairs = None
        # NES PalFadeIn: fading the new map in loads the palettes, so the windows turn red or white for the current HP
        # (ChkLowHPPal). This is where a level up's new max HP first changes the window color.
        self.game.load_window_palette()
        self.game.cmd_menu = CommandMenu(self.game)
        # TODO: Allow music to continue playing when moving within Tantegel Castle.
        self.music_player.load_and_play_music(self.current_map.music_file_path)
        if destination_coordinates:
            self.game.camera.set_camera_position((destination_coordinates[1], destination_coordinates[0]),
                                                 self.tile_size)
        # load_map gave the hero the unarmed sprite sheet and every character its first image (facing down); show the
        # right sheet and each one's facing in the frame the fade-in starts from, not only once the main loop has
        # animated them (the guards used to turn round the frame after the fade)
        self.game.set_player_images_by_equipment()
        for character_dict in self.current_map.characters.values():
            character_dict['character'].show_facing()
        self.drawer.draw_all(self.screen, self.game.loop_count, self.game.big_map, self.current_map, self.player,
                             self.game.cmd_menu, self.game.foreground_rects, self.game_state.enable_animate,
                             self.game.camera, self.game.initial_dialog_enabled, self.game.events,
                             self.game.skip_text, self.game.story_flags.left_throne_room, self.game_state,
                             self.game.color)
        # NES MapChngNoSound/MapChngWithSound (LB133): the map's music starts (ResumeMusicTbl), then PalFadeIn
        screen_fade(fade_out=False, screen=self.screen, config=self.game_state.config)

    def apply_rainbow_bridge(self):
        # NES ChkRnbwBrdg: once F_RNBW_BRDG is set, the overworld block at (64, 49) is always read as BLK_BRIDGE
        if self.current_map.identifier == 'Alefgard' and self.game.story_flags.rainbow_bridge_built:
            row, column = RAINBOW_BRIDGE_COORDINATES
            self.current_map.layout[row][column] = self.current_map.floor_tile_key['BRIDGE']['val']

    def apply_chest_history(self):
        # NES InitMapData and GetBlockID: update the chest history for the new map, then show opened chests as brick
        map_name = self.current_map.identifier
        if map_name != 'TantegelThroneRoom':
            self.game.story_flags.left_throne_room = True  # NES ChkThRoomMap sets F_LEFT_THROOM
        self.game.chest_history.enter_map(map_name, self.game.story_flags.left_throne_room)
        self.game.chest_history.apply_to_layout(map_name, self.current_map.layout, TREASURE_BOX, BRICK)
        if map_name == 'TantegelThroneRoom' and self.game.story_flags.left_throne_room:
            # NES ChkLeftThRoom: the throne room door is removed with the chests, so a continued game never finds
            # it locked again
            row, column = THRONE_ROOM_DOOR_COORDINATES
            self.current_map.layout[row][column] = BRICK
    def place_princess_gwaelin(self):
        """Put Gwaelin where the NES story flags say she is before the map's NPCs are loaded."""
        if self.current_map.identifier == 'TantegelThroneRoom' and self.game.story_flags.gwaelin_returned:
            # NES ChkGwaelinNPC: she's in the throne room's static NPC table, and only removed while F_RTN_GWAELIN
            # is clear
            self.current_map.include_npc('PRINCESS_GWAELIN')
        elif self.current_map.identifier == 'SwampCave' and self.game.story_flags.gwaelin_rescued:
            # NES GetBaseBlockID: once F_DONE_GWAELIN is set, her block in the Swamp Cave is read as brick floor
            self.current_map.exclude_npc('PRINCESS_GWAELIN')

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
        # NES InitMapData: NPCUpdateCntr starts at 0 on every map, so pair 0 (the first two roaming NPCs) moves first
        self.game.npc_schedule.new_map()
        for roaming_character in self.current_map.roaming_characters:
            set_character_position(roaming_character, self.tile_size)
