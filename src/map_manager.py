"""
MapManager — owns all map-transition and warp logic that previously lived on Game.

Holds change_map and its helpers.  Game keeps a reference to this object and
delegates to it; MapManager holds a back-reference to Game so it can reach
shared resources (player, camera, screen, music_player, …).
"""

from src import maps
from src.camera import Camera
from src.constants import RAINBOW_BRIDGE_COORDINATES, THRONE_ROOM_DOOR_COORDINATES, THRONE_ROOM_START_COORDINATES
from src.coordinates import Cell
from src.direction import Direction
from src.drawer import map_surface
from src.game_functions import set_character_position
from src.map_layouts import BRICK, DOOR, TREASURE_BOX
from src.maps import map_lookup
from src.menu import CommandMenu
from src.visual_effects import cut_to_black, screen_fade


class MapManager:
    def __init__(self, game):
        self.game = game
        # The (row, column) of the stairs a random fight started on: the hero stays there after the fight, and the
        # stairs aren't taken until the hero steps off them (or uses STAIRS). See stay_on_stairs.
        self.fought_on_stairs: Cell | None = None

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
        hero is still standing on them. With STAIRS set to STEP ON, stairs are taken by stepping onto them, so that
        step's warp is held back until the hero steps off (or uses STAIRS), instead of happening in the frame right
        after the fight."""
        self.fought_on_stairs = row, column

    def handle_warps(self):
        if self.fought_on_stairs is not None:
            if self.fought_on_stairs == (self.player.row, self.player.column):
                return
            self.fought_on_stairs = None
        location = self.player.row, self.player.column
        staircase_dict = self.current_map.staircases.get(location)
        if staircase_dict is None or not self.game.tiles_moved_since_spawn:
            return
        if not self.current_map.is_step_warp(*location):
            # Stairs: the NES only takes them by the STAIRS command (CheckStairs)
            if not self.game.auto_stairs:
                return  # STAIRS set to NES
            # STAIRS set to STEP ON (not NES): taken by stepping onto them, but only after a few steps on a new map,
            # so the hero doesn't go straight back down the stairs they came up
            immediate_move_maps = ('CharlockB1', 'MagicTemple', 'MountainCaveB1', 'MountainCaveB2')
            if not (self.game.tiles_moved_since_spawn > 2 or (
                    self.game.tiles_moved_since_spawn > 1 and self.current_map.identifier in immediate_move_maps)):
                return
        self.process_warp(staircase_dict)

    def process_warp(self, staircase_dict):
        self.player.bumped = False
        next_map = map_lookup[staircase_dict['map']](self.config)
        self.change_map(next_map, stairs_sound=True)

    # ------------------------------------------------------------------ #
    #  Map change                                                          #
    # ------------------------------------------------------------------ #

    def change_map(self, next_map: maps.DragonWarriorMap, destination_coordinates: Cell | None = None,
                   direction: int | None = None, fade_out_first: bool = True, stairs_sound: bool = False) -> None:
        """Change to a different map. Pass destination_coordinates (and optionally direction) to warp somewhere other
        than where the staircase the player is standing on leads, e.g. for RETURN or when loading a save.
        fade_out_first=False cuts straight to black instead of fading the old screen out, as NES StartAtThroneRoom
        (Bank03, LCB47) does: it loads BlackPalPtr at once and changes maps with MapChngNoSound (Bank00, LB091),
        which skips ScreenFadeOut, so the only fade is MapChngNoSound's PalFadeIn.
        stairs_sound=True plays the stairs sound once the old screen has faded out, as NES MapChngWithSound (Bank00,
        LB097-LB0B6) does: ScreenFadeOut, display off, then SFX_STAIRS, before the new map is drawn. It is the same
        sound going up or down stairs."""
        self.game_state.pause_all_movement()
        self.last_map = self.current_map
        self.current_map = next_map
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
        if stairs_sound:
            self.sound.play_sound(self.directories.stairs_sfx)  # SFX_STAIRS
        self.set_big_map()
        self.set_roaming_character_positions()
        is_warp = destination_coordinates is not None
        came_up_stairs = False
        if is_warp:
            current_map_staircase_dict = None
        elif not self.player.is_dead:
            current_map_staircase_dict = self.last_map.staircases[(self.player.row, self.player.column)]
            destination_coordinates = current_map_staircase_dict.get('destination_coordinates')
            came_up_stairs = self.on_stairs_up()
        else:
            current_map_staircase_dict = None
            destination_coordinates = THRONE_ROOM_START_COORDINATES
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
            self.handle_player_direction_on_map_change(current_map_staircase_dict, came_up_stairs)
        self.game.camera = Camera(hero_position=(int(self.player.column), int(self.player.row)),
                                  current_map=self.current_map, screen=self.screen, tile_size=self.tile_size)
        self.game.loop_count = 1
        self.game_state.unpause_all_movement()
        self.game.reset_step_count()
        self.fought_on_stairs = None
        # NES PalFadeIn: fading the new map in loads the palettes, so the windows turn red or white for the current HP
        # (ChkLowHPPal). This is where a level up's new max HP first changes the window color.
        self.game.load_window_palette()
        self.game.cmd_menu = CommandMenu(self.game)
        # NES LB10E: the old map's music plays on through the fade-out until the new map is drawn, then ResumeMusicTbl
        # starts the new map's music from the beginning, on every map change. That includes moving within Tantegel
        # Castle: the throne room has MSC_THRN_ROOM, the rest of the castle MSC_TANTAGEL2 (the lower version)
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
        # The frame the fade-in starts from. Nothing reads the joypad in it: on the NES the map fades in before the
        # game reads any button (Drawer.drawing_fade_in_frame)
        self.drawer.drawing_fade_in_frame = True
        try:
            self.drawer.draw_all(self.game, self.game_state.enable_animate)
        finally:
            self.drawer.drawing_fade_in_frame = False
        # NES MapChngNoSound/MapChngWithSound (LB133): the map's music starts (ResumeMusicTbl), then PalFadeIn
        screen_fade(fade_out=False, screen=self.screen, config=self.game_state.config)

    def apply_rainbow_bridge(self):
        # NES ChkRnbwBrdg: once F_RNBW_BRDG is set, the overworld block at (64, 49) is always read as BLK_BRIDGE
        if self.current_map.identifier == 'Alefgard' and self.game.story_flags.rainbow_bridge_built:
            row, column = RAINBOW_BRIDGE_COORDINATES
            self.current_map.layout[row][column] = self.current_map.floor_tile_key['BRIDGE']['val']

    def apply_chest_history(self):
        # NES InitMapData and GetBlockID: update the chest and door histories for the new map, then show opened chests
        # and doors as brick
        map_name = self.current_map.identifier
        if map_name != 'TantegelThroneRoom':
            self.game.story_flags.left_throne_room = True  # NES ChkThRoomMap sets F_LEFT_THROOM
        self.game.chest_history.enter_map(map_name, self.game.story_flags.left_throne_room)
        self.game.chest_history.apply_to_layout(map_name, self.current_map.layout, TREASURE_BOX, BRICK)
        # NES ChkOverworldMap clears the door history on the overworld, and ChkLeftThRoom writes the throne room door
        # into it with the chests, so a continued game never finds that door locked again; every other door locks
        # again, and opened doors show as brick
        self.game.door_history.enter_map(map_name, self.game.story_flags.left_throne_room,
                                         THRONE_ROOM_DOOR_COORDINATES)
        self.game.door_history.apply_to_layout(map_name, self.current_map.layout,
                                               self.layouts.door_coordinates.get(map_name, ()), DOOR, BRICK)

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
        """A black surface for the new map, which its first frame draws every tile on (Drawer.draw_all). It is the
        background until then too: that used to be a copy of it, but nothing shows the background before the first
        frame redraws it, and a copy of Alefgard's takes about 30 ms."""
        self.game.big_map = map_surface(self.current_map.width, self.current_map.height)
        self.drawer.background = self.game.big_map

    def handle_player_direction_on_map_change(self, current_map_staircase_dict, came_up_stairs: bool = False):
        if not self.player.is_dead:
            if came_up_stairs:
                # NES CheckStairs StairUpFound (Bank03, LD9E0): coming up any stairs, the hero always faces left
                self.player.direction_value = Direction.LEFT.value
                return
            destination_direction = current_map_staircase_dict.get('direction')
            if destination_direction:
                self.player.direction_value = destination_direction
        else:
            self.player.direction_value = Direction.UP.value

    def on_stairs_up(self) -> bool:
        """Whether the hero is standing on a stairs up block (BLK_STAIR_UP) of the map being left."""
        layout = self.last_map.layout
        row, column = self.player.row, self.player.column
        if not (0 <= row < len(layout) and 0 <= column < len(layout[0])):
            return False
        return maps.STAIR_DIRECTIONS.get(layout[row][column]) == 'up'

    def set_roaming_character_positions(self):
        # NES InitMapData: NPCUpdateCntr starts at 0 on every map, so pair 0 (the first two roaming NPCs) moves first
        self.game.movement.npc_schedule.new_map()
        for roaming_character in self.current_map.roaming_characters:
            set_character_position(roaming_character, self.tile_size)
