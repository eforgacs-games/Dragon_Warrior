import argparse
import json
import os
import random
import re
import shutil
import sys
from typing import List, Tuple

from pygame import FULLSCREEN, K_1, K_2, K_3, K_4, K_DOWN, K_LEFT, K_RIGHT, K_UP, K_a, K_d, K_i, K_k, K_s, \
    K_u, K_w, QUIT, RESIZABLE, display, event, image, init, key, quit, K_F1, K_F2, K_F3, K_F4, K_F11, time, KEYDOWN, SCALED, \
    K_RETURN, VIDEORESIZE
from pygame.display import set_mode, set_caption
from pygame.event import get
from pygame.time import Clock
from pygame.time import get_ticks

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.text.intro_lookup_table import ControlInfo
from src import maps
from src.adventure_log import AdventureLogOverlay, adventure_log_overlay_texts
from src.battle import Battle
from src.calculation import Calculation, get_tile_id_by_coordinates
from src.camera import Camera
from src.checkpoints import CHECKPOINT_NAMES, CHECKPOINT_SAVE_DIR, FACING_KEY, read_checkpoint
from src.color import WHITE, is_low_hp, window_color
from src.common import reject_keys, Graphics, RED, is_facing_medially, is_facing_laterally, \
    set_gettext_language
from src.common import is_facing_up, is_facing_down, is_facing_left, is_facing_right
from src.config.dev_config import dev_config
from src.config.prod_config import prod_config
from src.debug_tools import DebugTools
from src.constants import (
    ARROW_BLINK_INTERVAL_MS,
    TANTEGEL_CURSED_ROW, TANTEGEL_OVERWORLD_EXIT,
)
from src.direction import Direction
from src.directories import Directories
from src.drawer import Drawer
from src.encounters import ENEMY_GROUPS, encounter_group, roll_encounter
from src.game_functions import set_character_position, get_next_coordinates, GameFunctions
from src.game_state import GameState
from src.guardians import guardian_at
from src.intro import Intro
from src.items import TreasureChestHistory
from src.map_layouts import MapLayouts
from src.maps import map_lookup
from src.menu import CommandMenu, Menu
from src.menu_functions import NameSelection
from src.movement import Movement
from src.music_player import MusicPlayer
from src.player.player import Player
from src.sound import Sound
from src.sprites.fixed_character import FixedCharacter
from src.sprites.roaming_character import RoamingCharacter
from src.battle_controller import BattleController
from src.ending import Ending
from src.story_flags import StoryFlags
from src.map_manager import MapManager
from src.pygame_compat import arrow_fade
from src.visual_effects import fade, flash_transparent_color
from src.waiting import wait


SAVE_FILE_PATTERN = re.compile(r'save_slot_(\d+)\.json')


def save_slot_number(save_file_name: str) -> int:
    """The adventure log number in a save file's name, e.g. 2 for save_slot_2.json."""
    match = SAVE_FILE_PATTERN.fullmatch(save_file_name)
    if match is None:
        raise ValueError(f"Not a save file name: {save_file_name}")
    return int(match.group(1))


class Game:
    def __init__(self, config):

        self.config = config
        self.sound = Sound(config)
        self.graphics = Graphics(config)
        self.directories = Directories(config)
        self.calculation = Calculation(config)
        self.game_functions = GameFunctions(config)
        self.movement = Movement(self.config)
        self.show_arrow = True
        self.game_state = GameState(config=config)
        self.music_player = MusicPlayer(config)

        # load/save

        self.save_dir_contents = None

        self._ = _ = set_gettext_language(config['LANGUAGE'])
        self.drawer = Drawer(self.game_state)
        # map/graphics
        self.big_map = None
        self.layouts = MapLayouts()
        self.fullscreen_enabled = self.game_state.config["FULLSCREEN_ENABLED"]
        self.auto_stairs = self.game_state.config["AUTO_STAIRS"]
        # text
        self.initial_dialog_enabled = self.game_state.config["INITIAL_DIALOG_ENABLED"]
        self.skip_text = False

        # intro
        self.start_time = get_ticks()
        self.splash_screen_enabled = self.game_state.config["SPLASH_SCREEN_ENABLED"]
        # engine
        self.fps = self.game_state.config["FPS"]
        self.last_map = None
        self.last_zone = None
        self.last_amount_of_tiles_moved = 0
        self.tiles_moved_since_spawn = 0

        self.loop_count = 1
        self.foreground_rects = []
        self.repel_timer = 0  # NES RepelTimer, set by REPEL or Fairy Water
        # NES MjArmrHP: counts steps taken in Magic Armor; every 4th one heals 1 HP (see armor_step_heal)
        self.magic_armor_steps = 0
        self.chest_history = TreasureChestHistory()  # which treasure chests have been opened
        self.story_flags = StoryFlags()  # all story progress; saved and loaded as one
        self.speed = 2

        self.auto_battle = self.game_state.config["AUTO_BATTLE"]
        self.invulnerable = self.game_state.config["INVULNERABLE"]

        # debugging
        self.show_coordinates = self.game_state.config["SHOW_COORDINATES"]
        init()
        time.set_timer(arrow_fade, ARROW_BLINK_INTERVAL_MS)
        self.paused = False
        # START or A pressed while the hero or an NPC is between tiles: the pause or command window waits until everyone
        # has finished their step (NES PausePrepLoop / DoNCCmdWindow), see resolve_pending_freezes
        self.pause_requested = False
        self.cmd_menu_requested = False
        self.freeze_wait_frames = 0
        # Create the game window.
        if self.fullscreen_enabled:
            # according to pygame docs: "SCALED is considered an experimental API and may change in future releases."
            self.flags = FULLSCREEN | SCALED
            # self.flags = FULLSCREEN
        else:
            self.flags = RESIZABLE | SCALED
            # self.flags = RESIZABLE
        # flags = RESIZABLE | SCALED allows for the graphics to stretch to fit the window
        # without SCALED, it will show more of the map, but will also not center the camera
        # it might be a nice comfort addition to add to center the camera, while also showing more of the map
        self.scale = self.game_state.config["SCALE"]
        # video_infos = display.Info()
        # current_screen_width, current_screen_height = video_infos.current_w, video_infos.current_h
        nes_res = self.game_state.config["NES_RES"]
        win_width, win_height = nes_res[0] * self.scale, nes_res[1] * self.scale
        self.screen = self.set_screen(win_height, win_width)
        # self.screen.set_alpha(None)
        set_caption(_("Dragon Warrior"))

        # self.current_map can be changed to other maps for development purposes

        self.current_map = maps.map_lookup[self.game_state.config["START_MAP"]](self.game_state.config)

        self.battle_ctrl = BattleController(self)
        self.ending = Ending(self)
        self.map_mgr = MapManager(self)
        self.debug_tools = DebugTools(self) if config.get('DEBUG_KEYS') else None

        self.set_big_map()

        self.set_roaming_character_positions()

        self.player = Player(center_point=None,
                             images=self.current_map.scale_sprite_sheet(self.directories.UNARMED_HERO_PATH),
                             current_map=self.current_map, god_mode=self.game_state.config['GOD_MODE'],
                             fighters_ring_attack_bonus=self.game_state.config['FIGHTERS_RING_ATTACK_BONUS'])
        self.last_coordinates = None
        self.player.restore_hp()
        self.tile_size = self.game_state.config["TILE_SIZE"]
        self.current_map.load_map(self.player, None, self.tile_size)
        self.load_window_palette()

        # Good for debugging,
        # and will be useful later when the player's level increases and the stats need to be increased to match

        # self.player.total_experience = 26000
        # self.player.level = self.player.get_level_by_experience()
        # self.player.update_stats_to_current_level()

        self.player.current_tile = get_tile_id_by_coordinates(self.player.rect.x // self.tile_size,
                                                              self.player.rect.y // self.tile_size, self.current_map)
        self.camera = Camera((int(self.player.column), int(self.player.row)), self.current_map, self.screen,
                             self.tile_size)
        self.cmd_menu = CommandMenu(self)

        self.clock = Clock()
        self.music_enabled = self.game_state.music_enabled

        if self.splash_screen_enabled:
            self.music_player.load_and_play_music(self.directories.intro_overture)
        else:
            self.music_player.load_and_play_music(self.current_map.music_file_path)
        self.events = get()

        display.set_icon(image.load(self.directories.ICON_PATH))
        # pg.event.set_allowed([pg.QUIT])

    def set_screen(self, win_height, win_width):
        """Stub for setting the screen."""
        return set_mode((win_width, win_height), self.flags)

    def main(self) -> None:
        """
        Main loop.
        :return: None
        """
        if self.splash_screen_enabled:
            intro = Intro(self.config)
            intro.show_start_screen(self.screen, self.start_time, self.clock, self.game_state.config)
            self.music_player.load_and_play_music(self.directories.intermezzo)
            self.show_main_menu_screen(self.screen)
        if self.config.get('CHECKPOINT'):
            self.load_checkpoint(self.config['CHECKPOINT'])
        self.drawer.draw_all(self.screen, self.loop_count, self.big_map, self.current_map, self.player, self.cmd_menu,
                             self.foreground_rects, self.game_state.enable_animate, self.camera,
                             self.initial_dialog_enabled,
                             self.events, self.skip_text, self.story_flags.left_throne_room, self.game_state,
                             self.color)
        while True:
            self.clock.tick(self.fps)
            self.get_events()
            self.drawer.draw_all(self.screen, self.loop_count, self.big_map, self.current_map, self.player,
                                 self.cmd_menu, self.foreground_rects, self.sprites_animate, self.camera,
                                 self.initial_dialog_enabled, self.events, self.skip_text, self.story_flags.left_throne_room,
                                 self.game_state, self.color)
            display.flip()
            self.loop_count += 1

    def show_main_menu_screen(self, screen) -> None:
        if not os.path.exists(self.directories.save_dir):
            os.makedirs(self.directories.save_dir)
        self.save_dir_contents = self.save_files()
        if len(self.save_dir_contents) == 0:
            begin_quest_empty_log_function_lookup = {
                0: self.begin_new_quest,
            }
            selection = self.game_functions.main_menu_selection(get_ticks(), screen,
                                                                self.directories.main_menu_empty_log_unselected,
                                                                self.directories.main_menu_empty_log_0, [],
                                                                no_blit=self.game_state.config['NO_BLIT'])
            begin_quest_empty_log_function_lookup[selection]()
        else:
            if len(self.save_dir_contents) < 3:
                partially_full_log_function_lookup = {
                    0: self.continue_quest,
                    1: self.change_message_speed,
                    2: self.begin_new_quest,
                    3: self.copy_quest,
                    4: self.erase_quest,
                }
                selection = self.game_functions.main_menu_selection(get_ticks(), screen,
                                                                    self.directories.main_menu_partially_full_log_unselected,
                                                                    self.directories.main_menu_partially_full_log_0,
                                                                    [
                                                                        self.directories.main_menu_partially_full_log_1,
                                                                        self.directories.main_menu_partially_full_log_2,
                                                                        self.directories.main_menu_partially_full_log_3,
                                                                        self.directories.main_menu_partially_full_log_4],
                                                                    no_blit=self.game_state.config['NO_BLIT'])
                partially_full_log_function_lookup[selection]()
            elif len(self.save_dir_contents) == 3:
                # NES with every log used: CONTINUE A QUEST, CHANGE MESSAGE SPEED, ERASE AN ADVENTURE LOG
                full_log_function_lookup = {
                    0: self.continue_quest,
                    1: self.change_message_speed,
                    2: self.erase_quest,
                }
                selection = self.game_functions.main_menu_selection(get_ticks(), screen,
                                                                    self.directories.continue_quest_full_log_unselected,
                                                                    self.directories.continue_quest_full_log_0,
                                                                    [self.directories.continue_quest_full_log_1,
                                                                     self.directories.continue_quest_full_log_2],
                                                                    no_blit=self.game_state.config['NO_BLIT'])
                full_log_function_lookup[selection]()
            else:
                print("Error: More than 3 save files detected. Exiting.")
                exit(1)

    def begin_new_quest(self):
        self.select_adventure_log(self.screen)
        name_selection = NameSelection(self.config)
        self.player.name = name_selection.select_name(get_ticks(), self.screen, self.cmd_menu)
        self.player.set_initial_stats()
        self.sound.play_sound(self.directories.menu_button_sfx)
        fade(fade_out=True, screen=self.screen, config=self.game_state.config)
        self.music_player.load_and_play_music(self.current_map.music_file_path)
        self.cmd_menu = CommandMenu(self)

    def save_files(self) -> list[str]:
        """The adventure log save files in the save folder, ignoring anything else that might be there."""
        if not os.path.isdir(self.directories.save_dir):
            return []
        return sorted(name for name in os.listdir(self.directories.save_dir) if SAVE_FILE_PATTERN.fullmatch(name))

    def continue_quest(self):
        # make the window the right size based on self.save_dir_contents
        # populate the save file list with the player names
        # allow the user to select a save file
        # load the save file
        if len(self.save_dir_contents) == 1:
            save_path = os.path.join(self.directories.save_dir, self.save_dir_contents[0])
            self.game_functions.main_menu_selection(get_ticks(), self.screen,
                                                    self.directories.one_adventure_log_unselected,
                                                    self.directories.one_adventure_log_0,
                                                    [],
                                                    no_blit=self.game_state.config['NO_BLIT'],
                                                    overlay=self.adventure_log_overlay(save_path))
        if self.save_dir_contents:
            # TODO(#234): let the player pick the log when there are several. Until then, continue the most recently
            # saved one rather than silently starting a new game.
            save_file_name = max(self.save_dir_contents,
                                 key=lambda name: os.path.getmtime(os.path.join(self.directories.save_dir, name)))
            with open(os.path.join(self.directories.save_dir, save_file_name)) as save_file:
                loaded_save = json.load(save_file)
            self.sound.play_sound(self.directories.menu_button_sfx)
            # load_game has already cut to black, faded the starting map in, started its music and made a new
            # CommandMenu, as NES StartAtThroneRoom does; fading out again here would show the map twice
            self.load_game(loaded_save)
            # Save back to the same log, so continuing and saving doesn't create another save file
            self.player.adventure_log = save_slot_number(save_file_name)
            return

        self.sound.play_sound(self.directories.menu_button_sfx)
        fade(fade_out=True, screen=self.screen, config=self.game_state.config)
        self.music_player.load_and_play_music(self.current_map.music_file_path)
        self.cmd_menu = CommandMenu(self)

    def adventure_log_overlay(self, save_path: str) -> AdventureLogOverlay:
        """The name of the hero in save_path, to draw on the one_adventure_log screenshot's "ADVENTURE LOG 1:" line
        (Bank01 LogList1Dat2; see src/adventure_log.py)."""
        return AdventureLogOverlay(adventure_log_overlay_texts(save_path), self.game_state.config)

    def change_message_speed(self):
        # Toggle between fast (no wait) and normal speed. No sub-menu images exist, so just flip the flag.
        self.game_state.config['NO_WAIT'] = not self.game_state.config['NO_WAIT']
        self.sound.play_sound(self.directories.menu_button_sfx)

    def copy_quest(self):
        src_slot = self.game_functions.main_menu_selection(
            get_ticks(), self.screen,
            self.directories.empty_log_adventure_log_path,
            self.directories.ADVENTURE_LOG_1_PATH,
            [self.directories.ADVENTURE_LOG_2_PATH, self.directories.ADVENTURE_LOG_3_PATH],
            no_blit=self.game_state.config['NO_BLIT']) + 1
        dst_slot = self.game_functions.main_menu_selection(
            get_ticks(), self.screen,
            self.directories.empty_log_adventure_log_path,
            self.directories.ADVENTURE_LOG_1_PATH,
            [self.directories.ADVENTURE_LOG_2_PATH, self.directories.ADVENTURE_LOG_3_PATH],
            no_blit=self.game_state.config['NO_BLIT']) + 1
        src_path = os.path.join(self.directories.save_dir, f'save_slot_{src_slot}.json')
        dst_path = os.path.join(self.directories.save_dir, f'save_slot_{dst_slot}.json')
        if os.path.exists(src_path) and src_slot != dst_slot:
            shutil.copy2(src_path, dst_path)
        self.sound.play_sound(self.directories.menu_button_sfx)

    def erase_quest(self):
        slot = self.game_functions.main_menu_selection(
            get_ticks(), self.screen,
            self.directories.empty_log_adventure_log_path,
            self.directories.ADVENTURE_LOG_1_PATH,
            [self.directories.ADVENTURE_LOG_2_PATH, self.directories.ADVENTURE_LOG_3_PATH],
            no_blit=self.game_state.config['NO_BLIT']) + 1
        save_path = os.path.join(self.directories.save_dir, f'save_slot_{slot}.json')
        if os.path.exists(save_path):
            os.remove(save_path)
            self.save_dir_contents = self.save_files()
        self.sound.play_sound(self.directories.menu_button_sfx)

    def select_adventure_log(self, screen):
        self.player.adventure_log = self.game_functions.main_menu_selection(get_ticks(), screen,
                                                                            self.directories.empty_log_adventure_log_path,
                                                                            self.directories.ADVENTURE_LOG_1_PATH,
                                                                            [
                                                                                self.directories.ADVENTURE_LOG_2_PATH,
                                                                                self.directories.ADVENTURE_LOG_3_PATH]) + 1

    def get_events(self) -> None:
        """
        High-level event loop method that delegates to smaller helpers.
        """
        self.events = get()
        self._handle_pygame_events(self.events)
        self._handle_player_movement()
        self.handle_battles()
        if not self.player.is_moving:
            set_character_position(self.player, tile_size=self.tile_size)
        self._handle_map_updates()
        self.resolve_pending_freezes()
        self._handle_post_move_checks()
        self.ending.check_for_end_game_trigger()
        self._handle_debugging_info()
        event.pump()

    def _handle_debugging_info(self) -> None:
        """
        Prints debug data such as coordinates or FPS if debug/SHOW_FPS is enabled.
        """
        if self.show_coordinates:
            self._debug_coordinates()
        if self.game_state.config["SHOW_FPS"]:
            print(self.clock.get_fps())

    def _debug_coordinates(self) -> None:
        """
        Show coordinates and distance from a reference point, if desired.
        """
        if not self.last_coordinates:
            self.last_coordinates = self.player.column, self.player.row
            print(f"Current coordinates: {self.player.column, self.player.row}")
            # print("Distance from Tantegel Castle:",
            #       self.calculation.get_distance_from_tantegel(self.player.column, self.player.row))
        else:
            if self.last_coordinates != (self.player.column, self.player.row):
                print(f"Current coordinates: {self.player.column, self.player.row}")
                # print("Distance from Tantegel Castle:",
                #       self.calculation.get_distance_from_tantegel(self.player.column, self.player.row))
                self.last_coordinates = self.player.column, self.player.row

    def _handle_post_move_checks(self) -> None:
        """
        Sets the player's next tile, updates images, environment damage, and death checks.
        """
        self.player.current_tile = get_tile_id_by_coordinates(self.player.rect.x // self.tile_size,
                                                              self.player.rect.y // self.tile_size,
                                                              self.current_map)
        self.cmd_menu.current_tile = self.player.current_tile
        self.player.next_tile_id = self.calculation.get_next_tile_identifier(self.player.column, self.player.row,
                                                                             self.player.direction_value,
                                                                             self.current_map)
        self.player.next_coordinates = get_next_coordinates(self.player.rect.x // self.tile_size,
                                                            self.player.rect.y // self.tile_size,
                                                            self.player.direction_value)
        self.player.next_next_coordinates = get_next_coordinates(self.player.rect.x // self.tile_size,
                                                                 self.player.rect.y // self.tile_size,
                                                                 self.player.direction_value, offset_from_character=2)
        self.set_player_images_by_equipment()
        self.handle_environment_damage()
        self.handle_death()

    def _handle_map_updates(self) -> None:
        """
        Updates character positions and handles warp logic.
        """
        if self.game_state.enable_roaming and not self.world_frozen and self.current_map.roaming_characters:
            # NES UpdateNPCs1: no NPC starts a new step once a pause or the command window has been asked for
            self.move_roaming_characters(start_new_steps=not self.freeze_pending)
            self.update_roaming_character_positions()
        # currently can't process staircases right next to one another, need to fix
        # a quick fix would be to add an exception in the conditional for
        # the map where staircases right next to each other need to be enabled,
        # as done with Cantlin and others below
        self.handle_warps()

    def _handle_player_movement(self) -> None:
        """
        Checks if the game is paused or if movement is disabled; if not,
        moves the player based on the current key state.
        """
        if not self.game_state.enable_movement or self.world_frozen:
            return
        if self.freeze_pending and not self.player.is_moving:
            # NES GameEngineLoop only reads START and A between steps (DoJoyUp etc. move a whole tile before
            # returning), so a step already under way is finished, but no new one is started.
            return
        self.move_player(key.get_pressed())

    @property
    def world_frozen(self) -> bool:
        """
        Whether everything on the map is stopped: the hero and NPCs don't move and sprites don't animate.
        NES: StopNPCMove is set while the command window is up (ShowNCCmdWindow), and nothing calls DoSprites while
        the game is paused (GamePaused) or a window waits for a button (WaitForBtnPress), so walking animation stops
        too. Dialogs, shops and YES/NO prompts run in their own loops inside a command, so the main loop (and
        everything that moves) doesn't run at all until they close.
        This is the one place movement is gated, rather than relying on the GameState flags alone, because those
        are turned back on in many places (e.g. every menu command ends with unpause_all_movement).
        """
        return self.paused or self.cmd_menu.launch_signaled or self.cmd_menu.menu.is_enabled()

    @property
    def freeze_pending(self) -> bool:
        return self.pause_requested or self.cmd_menu_requested

    @property
    def sprites_animate(self) -> bool:
        return self.game_state.enable_animate and not self.world_frozen

    def everyone_on_a_tile(self) -> bool:
        """Whether the hero and every roaming NPC are standing exactly on a tile, not partway through a step."""
        if self.player.is_moving:
            return False
        if self.freeze_wait_frames > self.tile_size // self.speed:
            # Every NPC step finishes within this many frames; one that hasn't is stuck (e.g. the hero stepped
            # into the tile it was walking to), so don't wait on it forever.
            return True
        return all(not roaming_character.is_moving or (roaming_character.rect.x % self.tile_size == 0 and
                                                       roaming_character.rect.y % self.tile_size == 0)
                   for roaming_character in self.current_map.roaming_characters)

    def resolve_pending_freezes(self) -> None:
        """
        Pause, or open the command window, once the hero and the NPCs have finished their steps.
        NES PausePrepLoop (START) and DoNCCmdWindow (A) keep calling DoSprites until FrameCounter & $0F == 1, the
        frame on which every NPC is lined up on a tile, and only then pause or set StopNPCMove. START is checked
        before A (CheckInputs), so a pause wins.
        """
        if not self.freeze_pending:
            self.freeze_wait_frames = 0
            return
        if not self.everyone_on_a_tile():
            if not self.player.is_moving:
                self.freeze_wait_frames += 1
            return
        self.freeze_wait_frames = 0
        if self.pause_requested:
            self.pause_requested = False
            self.paused = True
            return
        self.cmd_menu_requested = False
        self.drawer.display_hovering_stats = True
        self.cmd_menu.launch_signaled = True
        self.game_state.pause_all_movement()

    def _handle_pygame_events(self, events: List[event.Event]) -> None:
        """
        Handles low-level pygame events such as QUIT, KEYDOWN, arrow fade toggles, and window resize.
        """
        for current_event in events:
            if current_event.type == QUIT:
                quit()
            elif current_event.type == KEYDOWN:
                self.handle_keypresses(current_event)
            elif current_event.type == arrow_fade:
                self.show_arrow = not self.show_arrow
            elif current_event.type == VIDEORESIZE:
                self._handle_window_resize(current_event)

    def _handle_window_resize(self, resize_event) -> None:
        """
        Handles window resize, maximize, and minimize events.
        With SCALED flag, PyGame automatically scales the game surface to fit the new window size.
        """
        # The SCALED flag automatically handles scaling, but we can add visual feedback here
        if self.config.get("SHOW_COORDINATES", False):
            # Show window size info when coordinates are enabled (debug mode)
            print(f"Window resized to: {resize_event.w}x{resize_event.h}")

    def set_window_color(self, color: tuple[int, int, int]) -> None:
        """Set the color of every window (their borders, text and cursors; NES background palette 0's color 1) and
        redraw the windows that are kept drawn (the COMMAND window), so nothing lags behind."""
        self.color = color
        cmd_menu = getattr(self, 'cmd_menu', None)
        if cmd_menu is not None:
            cmd_menu.refresh_window_color()

    def load_window_palette(self) -> None:
        """NES PrepBGPalLoad (Bank03): whenever the background palettes are loaded, AddPalByte's ChkLowHPPal makes the
        window color red if HP is low and white otherwise. They are loaded by every fade in or out (PalFadeIn and
        PalFadeOut: changing maps, the inn), by LoadRegBGPal right after HP changes (PlayerHit, swamp and force field
        damage, HEAL/HEALMORE's PlyrAddHP, HerbHeal) and by StartAtThroneRoom. Nothing else turns the windows red,
        so a level up, which raises the max HP but not HP, changes nothing until the next load."""
        self.set_window_color(window_color(self.player.current_hp, self.player.max_hp))

    def clear_low_hp_palette(self) -> None:
        """NES ChkLowHP (MovementUpdates, after every step): if HP isn't low, the window color is set back to white
        ($30 to $3F01). It never turns the windows red."""
        if not is_low_hp(self.player.current_hp, self.player.max_hp):
            self.set_window_color(WHITE)

    def count_step(self):
        self.tiles_moved_since_spawn += 1
        self.game_state.tiles_moved_total += 1
        # NES GameEngineLoop: the radiant timer (#216) and CheckRepelTimer are outside CheckForTriggers, so they keep
        # ticking (and wear off) after the Dragonlord's defeat
        self.game_state.tick_radiant_timer()
        self.tick_repel_timer()
        self.check_for_triggers()

    def check_for_triggers(self):
        """NES CheckForTriggers (Bank03, reached from ChkSpecialLoc after every completed step): MovementUpdates only
        runs while F_DGNLRD_DEAD is clear. Once the Dragonlord is dead it branches to ChkCstlEnd instead, which only
        checks for the end-game trigger in front of King Lorik (Ending.check_for_end_game_trigger) and then falls into
        CheckBlockDmg like before.

        CheckBlockDmg isn't here: it's split between handle_warps (map-changing tiles, still checked after the
        Dragonlord), handle_environment_damage and handle_battles, which each stop at ChkOtherBlocks' own
        F_DGNLRD_DEAD check, as the NES does."""
        if self.story_flags.dragonlord_defeated:
            return
        self.movement_updates()

    def movement_updates(self):
        """NES MovementUpdates, in order: the armor's HP regeneration (MovmtIncHP), ChkLowHP (clear_low_hp_palette),
        CheckTantCursed, then the guardian checks (CheckAxeKnight, CheckGrnDragon, CheckGolem). Only runs while the
        Dragonlord is alive (check_for_triggers)."""
        self.armor_step_heal()
        self.clear_low_hp_palette()  # NES MovementUpdates: ChkLowHP comes just before CheckTantCursed
        self.check_tantegel_cursed()
        self.check_guardian_fight()

    def armor_step_heal(self):
        """NES MovementUpdates/MovmtIncHP: Erdrick's Armor heals 1 HP every step. Magic Armor increments MjArmrHP every
        step and heals 1 HP when its low 2 bits wrap to 0, i.e. every 4th step in it. HP is capped at the maximum.
        (ChkLowHP, which comes next, is clear_low_hp_palette.)"""
        if self.player.armor == "Erdrick's Armor":
            heal = True
        elif self.player.armor == "Magic Armor":
            self.magic_armor_steps = (self.magic_armor_steps + 1) & 0xFF
            heal = self.magic_armor_steps & 0x03 == 0
        else:
            heal = False
        if heal:
            self.player.current_hp = min(self.player.current_hp + 1, self.player.max_hp)

    def check_tantegel_cursed(self):
        """NES CheckTantCursed (part of MovementUpdates, run every step while the Dragonlord is alive): a cursed player
        who reaches Y=27 of Tantegel's ground floor is told "Cursed one, be gone!" and CheckMapExit forces them out of
        the castle."""
        if self.current_map.identifier != 'TantegelCourtyard' or not self.player.is_cursed:
            return
        if self.player.rect.y // self.tile_size != TANTEGEL_CURSED_ROW:
            return
        self.cmd_menu.show_text_in_dialog_box(self._("Cursed one, be gone!"), add_quotes=True,
                                              skip_text=self.skip_text)
        self.leave_tantegel()

    def check_guardian_fight(self):
        """NES MovementUpdates (CheckAxeKnight, CheckGrnDragon, CheckGolem): stepping onto a guardian's tile starts
        its fixed fight (InitFight). It's queued so handle_battles starts it this same frame."""
        # The step has only just finished, so the hero's row and column haven't caught up with its rect yet
        coordinates = self.player.rect.y // self.tile_size, self.player.rect.x // self.tile_size
        guardian = guardian_at(self.current_map.identifier, coordinates, self.story_flags)
        if guardian is not None:
            self.battle_ctrl.queue_scripted_battle(guardian.enemy_name)

    def leave_tantegel(self, direction: int | None = None):
        map_name, coordinates = TANTEGEL_OVERWORLD_EXIT
        self.change_map(map_lookup[map_name](self.config), destination_coordinates=coordinates, direction=direction)

    def tick_repel_timer(self):
        """NES CheckRepelTimer: the timer drops by 2 per step. REPEL (odd start) ends at 1, Fairy Water (even) at 0."""
        if not self.repel_timer:
            return
        self.repel_timer -= 2
        if self.repel_timer in (0, 1):
            if self.repel_timer:
                message = self._("REPEL has lost its effect.")
            else:
                message = self._("The Fairy Water has lost its effect.")
            self.repel_timer = 0
            self.cmd_menu.show_text_in_dialog_box(message, skip_text=self.skip_text)

    def handle_battles(self):
        if self.battle_ctrl.pending_scripted_battle:
            # A fixed fight: the Dragonlord or the Silver Harp, asked for by a dialog that has now closed, or a guardian
            # the hero has just stepped up to.
            self.battle_ctrl.run_pending_scripted_battle()
            # NES: InitFight takes the place of CheckBlockDmg, so this step can't also bring a random fight
            self.last_amount_of_tiles_moved = self.tiles_moved_since_spawn
            return
        # NES ChkOtherBlocks: once the Dragonlord is dead, no more random fights
        if self.story_flags.dragonlord_defeated:
            return
        if self.tiles_moved_since_spawn > 0 and self.tiles_moved_since_spawn != self.last_amount_of_tiles_moved:
            self.last_amount_of_tiles_moved = self.tiles_moved_since_spawn
            # NES CheckBlockDmg runs once per step, on the block the player has just stepped onto. The player's
            # column/row and current_tile aren't updated until later in the frame, so read them from the sprite.
            column, row = self.player.rect.x // self.tile_size, self.player.rect.y // self.tile_size
            group = encounter_group(self.current_map.identifier, column, row)
            if group is None:
                return
            self.last_zone = group
            tile = get_tile_id_by_coordinates(column, row, self.current_map)
            enemies_in_current_zone = ENEMY_GROUPS[group] if self.game_state.config["FORCE_BATTLE"] else \
                roll_encounter(self.current_map.identifier, tile, column, row)
            self.battle_ctrl.launch_battle = enemies_in_current_zone is not None
            if enemies_in_current_zone is not None and not self.game_state.config["NO_BATTLES"]:
                self.battle_ctrl.run_battle(enemies_in_current_zone)
            self.battle_ctrl.battle_menu_row = 0
            self.battle_ctrl.battle_menu_column = 0

    def battle(self, enemies_in_current_zone):
        self.battle_ctrl.run_battle(enemies_in_current_zone)

    def handle_battle_prompts(self, run_away: bool, current_battle: Battle) -> bool:
        return self.battle_ctrl.handle_battle_prompts(run_away, current_battle)

    def enemy_run_away(self, current_battle, enemy):
        return self.battle_ctrl.enemy_run_away(current_battle, enemy)

    def fight(self, current_battle):
        self.battle_ctrl.fight(current_battle)

    def hero_attack(self, current_battle):
        self.battle_ctrl.hero_attack(current_battle)

    def enemy_move(self, current_battle: Battle) -> bool:
        return self.battle_ctrl.enemy_move(current_battle)

    def execute_enemy_pattern(self, current_battle, current_enemy_pattern, current_index, enemy):
        self.battle_ctrl.execute_enemy_pattern(current_battle, current_enemy_pattern, current_index, enemy)

    def increment_and_execute_enemy_pattern(self, current_battle, current_index, enemy):
        self.battle_ctrl.increment_and_execute_enemy_pattern(current_battle, current_index, enemy)

    def enemy_attack(self, current_battle):
        self.battle_ctrl.enemy_attack(current_battle)

    def execute_enemy_attack(self, current_battle):
        self.battle_ctrl.execute_enemy_attack(current_battle)

    def enemy_attack_message(self, enemy):
        self.battle_ctrl.enemy_attack_message(enemy)

    def receive_damage(self, attack_damage):
        # God mode or invulnerable: take no damage
        if self.player.god_mode or self.invulnerable:
            return

        self.sound.play_sound(self.directories.receive_damage_2_sfx)
        self.player.current_hp -= attack_damage
        if self.player.current_hp < 0:
            self.player.current_hp = 0
        self.battle_ctrl.player_hit_effect()  # NES PlayerHit: screen shake, red flash on a deathblow
        self.load_window_palette()  # NES PlayerHit: LoadRegBGPal, after the screen shake (red if HP is now low)
        self.drawer.draw_hovering_stats_window(self.screen, self.player, self.color)
        # create_window(6, 1, 8, 3, BATTLE_MENU_FIGHT_PATH, self.screen, self.color)
        self.cmd_menu.show_line_in_dialog_box(self._("Thy Hit Points decreased by {}.\n").format(attack_damage),
                                              add_quotes=False, disable_sound=True, hide_arrow=True, skip_text=True if
            self.player.current_hp == 0 else False)
        # print(f"{self.player.name} HP: {self.player.current_hp}/{self.player.max_hp}")

    def set_player_images_by_equipment(self):
        if self.story_flags.carrying_gwaelin:
            self.player.images = self.current_map.scale_sprite_sheet(self.directories.HERO_CARRYING_PRINCESS_PATH)
            self.player.set_images(self.player.images)
        elif self.player.weapon:
            if self.player.shield:
                self.player.images = self.current_map.scale_sprite_sheet(self.directories.ARMED_HERO_WITH_SHIELD_PATH)
                self.player.set_images(self.player.images)

            else:
                self.player.images = self.current_map.scale_sprite_sheet(self.directories.ARMED_HERO_PATH)
                self.player.set_images(self.player.images)
        elif self.player.shield:
            self.player.images = self.current_map.scale_sprite_sheet(self.directories.UNARMED_HERO_WITH_SHIELD_PATH)
            self.player.set_images(self.player.images)
        else:
            self.player.images = self.current_map.scale_sprite_sheet(self.directories.UNARMED_HERO_PATH)
            self.player.set_images(self.player.images)

    def handle_death(self):
        if self.player.current_hp <= 0:
            self.player.current_hp = 0
            self.player.is_dead = True
            self.load_window_palette()  # 0 HP is always low
            if self.battle_ctrl.launch_battle and not self.game_state.config["NO_BATTLES"]:
                self.graphics.create_window(6, 1, 8, 3, self.directories.BATTLE_MENU_FIGHT_PATH, self.screen, self.color)
                self.battle_ctrl.launch_battle = False
                display.flip()
            else:
                self.drawer.draw_all_tiles_in_current_map(self.current_map, self.drawer.background)
                display.flip()
            self.music_player.load_and_play_music(self.directories.death_sfx, 1)
            self.game_state.enable_movement = False
            wait(self.calculation.convert_to_milliseconds(318), self.game_state.config)
            event.clear()  # keys pressed during the death music are dropped

            self.cmd_menu.show_text_in_dialog_box(self._("Thou art dead."), disable_sound=True)
            self.set_post_death_attributes()
        else:
            self.player.is_dead = False

    def set_post_death_attributes(self):
        # NES DeathText: dying clears F_GOT_GWAELIN, so Gwaelin is back in the Swamp Cave (F_RTN_GWAELIN is untouched)
        self.story_flags.carrying_gwaelin = False
        self.repel_timer = 0  # NES StartAtThroneRoom (SetStartPos) clears RepelTimer
        self.player.gold = self.player.gold // 2
        # NES StartAtThroneRoom sets HP before MapChngNoSound fades the throne room in, so the fade's palette load
        # (ChkLowHPPal) sees the new HP: a cursed hero comes back with 1 HP, which is always low, so the king's words
        # are in red windows; anyone else comes back with full HP and white windows.
        self.player.current_hp = 1 if self.player.is_cursed else self.player.max_hp
        self.load_window_palette()
        next_map = map_lookup['TantegelThroneRoom'](self.config)
        self.change_map(next_map)
        self.player.is_dead = False
        if self.player.is_cursed:
            # NES DeathText: the king then says "Thou hast failed and thou art cursed." and ChangeMaps puts the player
            # outside the castle, facing down.
            self.cmd_menu.show_text_in_dialog_box(
                (self._("Thou hast failed and thou art cursed."), self._("Leave at once!")), add_quotes=True,
                skip_text=self.skip_text)
            self.leave_tantegel(direction=Direction.DOWN.value)
            return
        self.game_state.is_post_death_dialog = True

    def handle_environment_damage(self):
        # NES ChkOtherBlocks: once the Dragonlord is dead, swamps and barriers no longer hurt
        if self.story_flags.dragonlord_defeated:
            return
        if not self.player.armor == "Erdrick's Armor":
            if not self.player.is_moving:
                if self.player.current_tile == 'MARSH':
                    if not self.player.received_environment_damage:
                        self.damage_step(damage_amount=2)
                elif self.player.current_tile == 'BARRIER':
                    if not self.player.received_environment_damage:
                        self.damage_step(damage_amount=15)
            else:
                self.player.received_environment_damage = False

    def damage_step(self, damage_amount):
        # God mode or invulnerable: take no damage
        if self.player.god_mode or self.invulnerable:
            return

        self.player.current_hp -= damage_amount
        self.sound.play_sound(self.directories.swamp_sfx)
        self.player.received_environment_damage = True
        flash_transparent_color(RED, self.screen, self.calculation, no_blit=self.game_state.config['NO_BLIT'])
        # NES DoSwampDamage and the force field damage: RedFlashScreen, then LoadRegBGPal with the new HP
        self.load_window_palette()
        self.drawer.draw_all(self.screen, self.loop_count, self.big_map, self.current_map, self.player, self.cmd_menu,
                             self.foreground_rects, self.game_state.enable_animate, self.camera,
                             self.initial_dialog_enabled,
                             self.events, self.skip_text, self.story_flags.left_throne_room, self.game_state,
                             self.color)
        display.flip()

    def handle_warps(self):
        self.map_mgr.handle_warps()

    def process_warp(self, staircase_dict):
        self.map_mgr.process_warp(staircase_dict)

    def handle_keypresses(self, current_keydown_event):
        if self.paused:
            # NES GamePaused only reads START until the game is unpaused
            self.handle_start_button(current_keydown_event)
            self.handle_fullscreen_toggle(current_keydown_event)
            return
        self.handle_b_button(current_keydown_event)
        self.handle_a_button(current_keydown_event)
        self.handle_start_button(current_keydown_event)
        self.handle_select_button(current_keydown_event)
        # TODO: Allow for zoom in and out if Ctrl + PLUS | MINUS is pressed (or scroll wheel is moved). (modernization)
        # if key[pg.K_LCTRL] and (key[pg.K_PLUS] or key[pg.K_KP_PLUS]):
        #     self.scale = self.scale + 1
        self.handle_help_button(current_keydown_event)
        self.handle_enter_key(current_keydown_event)
        self.handle_fps_changes(current_keydown_event)
        self.handle_fullscreen_toggle(current_keydown_event)
        self.handle_auto_stairs_toggle(current_keydown_event)
        self.handle_auto_battle_toggle(current_keydown_event)
        self.handle_invulnerability_toggle(current_keydown_event)
        if self.debug_tools is not None:
            # Dev config only (DEBUG_KEYS): F5 warp, F6 give, F7 load a checkpoint
            self.debug_tools.handle_keydown(current_keydown_event)

    def handle_help_button(self, keydown_event):
        if keydown_event.key == K_F1:
            control_info = ControlInfo(self.config)
            # one page per group of keys, so nothing runs past the bottom of the dialog box
            self.cmd_menu.show_text_in_dialog_box(control_info.help_pages)

    def handle_b_button(self, keydown_event):
        if keydown_event.key in reject_keys:
            # B button
            # using reject_keys adds ESC as an option to unlaunch the command menu
            self.unlaunch_menu(self.cmd_menu)
            # print("J key pressed (B button).")

    def handle_a_button(self, keydown_event):
        if keydown_event.key == K_k:
            # A button
            # print("K key pressed (A button).")
            if self.world_frozen or self.pause_requested:
                return
            # The window opens once the hero and the NPCs have finished their steps (resolve_pending_freezes)
            self.cmd_menu_requested = True
            self.resolve_pending_freezes()

    def handle_start_button(self, keydown_event):
        if keydown_event.key == K_i:
            # Start button
            if self.paused:
                self.paused = False
            elif not (self.cmd_menu.launch_signaled or self.cmd_menu.menu.is_enabled()):
                # NES CheckInputs: START only pauses from the map, not while a window is up. The hero finishes the
                # step under way first (resolve_pending_freezes).
                self.pause_requested = True
                self.cmd_menu_requested = False
                self.resolve_pending_freezes()

    def handle_enter_key(self, keydown_event):
        if keydown_event.key == K_RETURN:
            # A shortcut for TAKE/DOOR/TALK, so it follows the same rule as the A button: NES GameEngineLoop only reads
            # commands between steps (DoJoyUp etc. move a whole tile before returning to CheckInputs). Mid-step, or
            # while a pause or the command window is pending or open (where Enter picks a menu item), it does nothing.
            if self.player.is_moving or self.world_frozen or self.freeze_pending:
                return
            if self.player.current_tile == 'TREASURE_BOX':
                self.drawer.draw_hovering_stats_window(self.screen, self.player, color=self.color)
                self.cmd_menu.take()
            elif self.player.next_tile_id == 'DOOR':
                self.cmd_menu.door()
            elif self.cmd_menu.check_across_from_npc() and not self.game_state.is_initial_dialog:
                self.drawer.draw_hovering_stats_window(self.screen, self.player, color=self.color)
                self.cmd_menu.talk()

    @staticmethod
    def handle_select_button(keydown_event):
        if keydown_event.key == K_u:
            # Select button
            pass

    def handle_fps_changes(self, keydown_event) -> None:
        if keydown_event.key == K_1:
            self.fps = 60
            self.draw_temporary_text(self._("Game set to normal speed.\n({} FPS)".format(self.fps)))
        if keydown_event.key == K_2:
            self.fps = 120
            self.draw_temporary_text(self._("Game set to double speed.\n({} FPS)".format(self.fps)))
        if keydown_event.key == K_3:
            self.fps = 240
            self.draw_temporary_text(self._("Game set to triple speed.\n({} FPS)".format(self.fps)))
        if keydown_event.key == K_4:
            self.fps = 480
            self.draw_temporary_text(self._("Game set to quadruple speed.\n({} FPS)".format(self.fps)))

    def handle_fullscreen_toggle(self, keydown_event) -> None:
        """Toggle between fullscreen and windowed mode when F11 is pressed."""
        if keydown_event.key == K_F11:
            self.fullscreen_enabled = not self.fullscreen_enabled
            if self.fullscreen_enabled:
                self.flags = FULLSCREEN | SCALED
                mode_text = self._("Fullscreen mode enabled")
            else:
                self.flags = RESIZABLE | SCALED
                mode_text = self._("Windowed mode enabled")

            # Recreate the window with new flags
            nes_res = self.game_state.config["NES_RES"]
            win_width, win_height = nes_res[0] * self.scale, nes_res[1] * self.scale
            self.screen = set_mode((win_width, win_height), self.flags)
            set_caption(self._("Dragon Warrior"))

            # Show feedback to user
            self.draw_temporary_text(mode_text)

    def handle_auto_stairs_toggle(self, keydown_event) -> None:
        """Toggle auto-stairs mode when F2 is pressed."""
        if keydown_event.key == K_F2:
            self.auto_stairs = not self.auto_stairs
            if self.auto_stairs:
                mode_text = self._("Auto-stairs enabled")
            else:
                mode_text = self._("Auto-stairs disabled")
            self.draw_temporary_text(mode_text)

    def handle_auto_battle_toggle(self, keydown_event) -> None:
        """Toggle auto-battle mode when F3 is pressed."""
        if keydown_event.key == K_F3:
            self.auto_battle = not self.auto_battle
            if self.auto_battle:
                mode_text = self._("Auto-battle enabled\n(Repeats: {})").format(self.battle_ctrl.last_battle_action)
            else:
                mode_text = self._("Auto-battle disabled")
            self.draw_temporary_text(mode_text)

    def handle_invulnerability_toggle(self, keydown_event) -> None:
        """Toggle invulnerability mode when F4 is pressed."""
        if keydown_event.key == K_F4:
            self.invulnerable = not self.invulnerable
            if self.invulnerable:
                mode_text = self._("Invulnerability enabled")
            else:
                mode_text = self._("Invulnerability disabled")
            self.draw_temporary_text(mode_text)

    def update_roaming_character_positions(self) -> None:
        for roaming_character in self.current_map.roaming_characters:
            if not roaming_character.is_moving:
                set_character_position(roaming_character, tile_size=self.tile_size)

    def draw_temporary_text(self, text: Tuple[str] | List[str] | str, add_quotes=False) -> None:
        self.cmd_menu.show_text_in_dialog_box(text, add_quotes=add_quotes, temp_text_start=get_ticks(), skip_text=False)

    def process_staircase_warps(self, staircase_location: tuple, staircase_dict: dict) -> None:
        if (self.player.row, self.player.column) == staircase_location:
            self.process_warp(staircase_dict)

    def change_map(self, next_map: maps.DragonWarriorMap, destination_coordinates: tuple | None = None,
                   direction: int | None = None) -> None:
        self.map_mgr.change_map(next_map, destination_coordinates, direction)

    def set_underlying_tiles_on_map_change(self, destination_coordinates, initial_hero_location):
        self.map_mgr.set_underlying_tiles_on_map_change(destination_coordinates, initial_hero_location)

    def reset_initial_hero_location_tile(self):
        self.map_mgr.reset_initial_hero_location_tile()

    def set_big_map(self):
        self.map_mgr.set_big_map()

    def handle_player_direction_on_map_change(self, current_map_staircase_dict):
        self.map_mgr.handle_player_direction_on_map_change(current_map_staircase_dict)

    def set_roaming_character_positions(self):
        self.map_mgr.set_roaming_character_positions()

    def unlaunch_menu(self, menu_to_unlaunch: Menu) -> None:
        """
        Un-launch a menu.
        :return: None
        """
        menu_to_unlaunch.launch_signaled = False
        if menu_to_unlaunch.menu.get_id() == 'command':
            if self.cmd_menu.menu.is_enabled():
                self.game_state.unpause_all_movement()
                self.cmd_menu.window_drop_up_effect(6, 1, 8, 5)
                self.cmd_menu.menu.disable()
        self.drawer.draw_all_tiles_in_current_map(self.current_map, self.drawer.background)

    def move_player(self, current_key) -> None:
        """
        Move the player in a specified direction.
        :param current_key: The key currently being pressed by the user.
        """
        # TODO(ELF): Allow for key taps, to just face in a particular direction
        # block establishes direction if needed and whether to start or stop moving
        # TODO(ELF): separate dependency of camera pos and player pos
        curr_pos_x, curr_pos_y = self.camera.pos

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
                if curr_pos_y % self.tile_size == 0:
                    if not self.player.bumped:
                        # TODO(ELF): sometimes self.tiles_moved_since_spawn gets set to 1 when spawning -
                        #  should always be 0 when the map starts.
                        self.count_step()
                    else:
                        self.player.bumped = False
                    self.finish_step(self.player)
                    return
            elif is_facing_laterally(self.player):
                if curr_pos_x % self.tile_size == 0:
                    if not self.player.bumped:
                        self.count_step()
                    else:
                        self.player.bumped = False
                    self.finish_step(self.player)
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
        self.cmd_menu.camera_position = \
            curr_cam_pos_x, curr_cam_pos_y = next_cam_pos_x, next_cam_pos_y = self.camera.pos
        self.check_next_tile(character)
        character.next_tile_id = self.calculation.get_next_tile_identifier(character.column, character.row,
                                                                           character.direction_value,
                                                                           self.current_map)
        character.next_next_tile_id = self.calculation.get_next_tile_identifier(character.column, character.row,
                                                                                character.direction_value,
                                                                                self.current_map, offset=2)
        if character.step_destination is None:
            # Start of a step: check it once, then reserve the destination until the character arrives
            if self.is_impassable(character.next_tile_id) or self.character_in_path(character) or (
                    character is not self.player and self.npc_crosses_cover_boundary(character)):
                self.movement.bump_and_reset(character, character.next_tile_id, character.next_next_tile_id)
                delta_x = delta_y = 0
            else:
                character.step_origin = (character.column, character.row)
                character.step_destination = self.get_next_coordinates(character.column, character.row,
                                                                      character.direction_value)
        if delta_x or delta_y:
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
        if character.identifier == 'HERO' and self.game_state.enable_movement:
            self.camera.pos = self.move_and_handle_sides_collision(next_cam_pos_x, next_cam_pos_y)

    def check_next_tile(self, character: Player | RoamingCharacter) -> None:
        if not character.next_tile_checked or not character.next_tile_id:
            character.next_tile_id = self.calculation.get_next_tile_identifier(character.column, character.row,
                                                                               character.direction_value,
                                                                               self.current_map)
        character.next_next_tile_id = self.calculation.get_next_tile_identifier(character.column, character.row,
                                                                                character.direction_value,
                                                                                self.current_map, offset=2)

    def character_in_path(self, character: Player | RoamingCharacter | FixedCharacter) -> bool:
        """Whether the tile in front of a character is taken by someone else: where they stand, or the origin and
        destination of a step they're taking (NES: an NPC can't move onto the player's position or next position, or
        onto another NPC's)."""
        next_coordinates = self.get_next_coordinates(character.column, character.row, character.direction_value)
        others = [*self.current_map.fixed_characters, *self.current_map.roaming_characters, self.player]
        for other in others:
            if other is character:
                continue
            if next_coordinates in ((other.column, other.row), other.step_origin, other.step_destination):
                return True
        return False

    @staticmethod
    def finish_step(character: Player | RoamingCharacter) -> None:
        character.is_moving, character.next_tile_checked = False, False
        character.step_origin = character.step_destination = None

    def npc_crosses_cover_boundary(self, character: Player | RoamingCharacter) -> bool:
        """NES $B839-$B84F: an NPC can't step into or out of a covered area."""
        next_coordinates = self.get_next_coordinates(character.column, character.row, character.direction_value)
        if next_coordinates is None:
            return False
        next_column, next_row = next_coordinates
        return self.current_map.crosses_cover_boundary(character.row, character.column, next_row, next_column)

    def get_next_coordinates(self, character_column: int, character_row: int, direction: int) -> tuple | None:
        if character_row < len(self.current_map.layout) and character_column < len(self.current_map.layout[0]):
            if direction == Direction.UP.value:
                return character_column, character_row - 1
            elif direction == Direction.DOWN.value:
                return character_column, character_row + 1
            elif direction == Direction.LEFT.value:
                return character_column - 1, character_row
            elif direction == Direction.RIGHT.value:
                return character_column + 1, character_row
        return None

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
        max_x_bound, max_y_bound = self.current_map.width - self.tile_size, self.current_map.height - self.tile_size
        min_bound = 0
        if self.player.rect.x < min_bound:
            self.player.rect.x = min_bound
            self.movement.bump(self.player)
            next_pos_x += -self.speed
        elif self.player.rect.x > max_x_bound:
            self.player.rect.x = max_x_bound
            self.movement.bump(self.player)
            next_pos_x += self.speed
        elif self.player.rect.y < min_bound:
            self.player.rect.y = min_bound
            self.movement.bump(self.player)
            next_pos_y -= self.speed
        elif self.player.rect.y > max_y_bound:
            self.player.rect.y = max_y_bound
            self.movement.bump(self.player)
            next_pos_y += self.speed
        return next_pos_x, next_pos_y

    def move_roaming_characters(self, start_new_steps: bool = True) -> None:
        """
        Move all roaming characters in the current map.
        :param start_new_steps: False lets characters partway through a step finish it, but none start a new one.
        :return: None
        """
        for roaming_character in self.current_map.roaming_characters:
            curr_pos_x, curr_pos_y = roaming_character.rect.x, roaming_character.rect.y
            # set_character_position(roaming_character)
            if roaming_character.last_roaming_clock_check is None or \
                    get_ticks() - roaming_character.last_roaming_clock_check >= 1000:
                roaming_character.last_roaming_clock_check = get_ticks()
                if not roaming_character.is_moving:
                    if not start_new_steps:
                        continue
                    roaming_character.direction_value = random.choice(list(map(int, Direction)))
                else:  # character not moving and no input
                    continue
                set_character_position(roaming_character, self.tile_size)
                roaming_character.last_rect = roaming_character.rect.copy()
                roaming_character.is_moving = True
            else:  # determine if character has reached new tile
                if is_facing_medially(roaming_character):
                    if curr_pos_y % self.tile_size == 0:
                        self.finish_step(roaming_character)
                        continue
                elif is_facing_laterally(roaming_character):
                    if curr_pos_x % self.tile_size == 0:
                        self.finish_step(roaming_character)
                        continue
            if is_facing_medially(roaming_character):
                self.move_medially(roaming_character)
            elif is_facing_laterally(roaming_character):
                self.move_laterally(roaming_character)
            # handle_roaming_character_sides_collision(self.current_map, roaming_character)

    def load_game(self, save_file: dict, direction: int | None = None) -> None:
        """Continue a saved game (see CommandMenu.save for what is kept).

        NES LoadSavedData (Bank03) restores the hero and the ModsnSpells, PlayerFlags and StoryFlags bytes as they
        were saved. MainGameEngine then clears the treasure chest history, and StartAtThroneRoom clears the repel
        timer, gives a cursed hero 1 HP and loads the starting map, whose InitMapData applies the story flags (the
        throne room chests are gone once F_LEFT_THROOM is set). The NES always starts in the throne room; this game
        starts where the save was made, which is always beside King Lorik.

        Everything loaded, including the facing (direction, or the map's own: up, toward King Lorik, in the throne
        room, as NES ContinueReset clears CharDirection to 0), is in place before the map's first frame is drawn.
        StartAtThroneRoom loads BlackPalPtr straight away and changes maps with MapChngNoSound, which skips the fade
        out, so the screen cuts to black and the map appears with a single PalFadeIn."""
        self.player.name = save_file["Name"]
        self.player.total_experience = save_file["Experience"]
        self.player.level = self.player.get_level_by_experience()
        self.player.update_stats_to_current_level()
        self.player.gold = save_file["Gold"]
        self.player.current_hp = save_file.get("CurrentHP", self.player.max_hp)
        self.player.current_mp = save_file.get("CurrentMP", self.player.max_mp)
        self.player.weapon = save_file.get("Weapon", "")
        self.player.armor = save_file.get("Armor", "")
        self.player.shield = save_file.get("Shield", "")
        self.player.wearing_dragon_scale = save_file.get("WearingDragonScale", False)
        self.player.wearing_fighters_ring = save_file.get("WearingFightersRing", False)
        self.player.wearing_cursed_belt = save_file.get("WearingCursedBelt", False)
        self.player.wearing_death_necklace = save_file.get("WearingDeathNecklace", False)
        self.player.update_attack_power()
        self.player.update_defense_power()
        self.player.inventory = save_file["Inventory"]
        self.player.spells = save_file.get("Spells", [])
        self.story_flags = StoryFlags.from_save(save_file)
        self.chest_history = TreasureChestHistory()
        self.repel_timer = 0
        if self.player.is_cursed:
            # NES StartAtThroneRoom (LCB6B): a cursed hero always starts with 1 HP
            self.player.current_hp = 1
        # NES StartAtThroneRoom: the fade in after loading sets the window color for the loaded HP (ChkLowHPPal)
        self.load_window_palette()
        # Reload the starting map even if it's the one already shown, so the loaded flags apply to it
        saved_map = save_file.get("CurrentMap")
        if saved_map in map_lookup:
            next_map = map_lookup[saved_map](self.config)
            destination = (save_file.get("PlayerRow"), save_file.get("PlayerColumn"))
            if destination[0] is None:
                destination = next_map.initial_coordinates
        elif self.current_map.identifier in map_lookup:
            next_map = map_lookup[self.current_map.identifier](self.config)
            destination = (self.player.row, self.player.column)
        else:
            return
        self.map_mgr.change_map(next_map, destination_coordinates=destination, direction=direction,
                                fade_out_first=False)

    def load_checkpoint(self, name: str) -> None:
        """Start from a playtest checkpoint (src/checkpoints.py): a save file in data/checkpoints/, loaded the same
        way as a saved game. The one thing saves don't keep, the hero's facing, is passed to load_game so it's in place
        before the first frame. Saving with King Lorik from then on writes to CHECKPOINT_SAVE_DIR, not to the real save
        slots."""
        checkpoint = read_checkpoint(name)
        if not self.config.get('SAVE_DIR'):
            os.makedirs(CHECKPOINT_SAVE_DIR, exist_ok=True)
            self.config['SAVE_DIR'] = CHECKPOINT_SAVE_DIR  # before load_game makes the new CommandMenu
        facing = checkpoint.get(FACING_KEY)
        self.load_game(checkpoint, direction=Direction[facing].value if facing else None)
        # King Lorik's automatic greeting belongs to the throne room
        self.initial_dialog_enabled = self.initial_dialog_enabled and self.current_map.identifier == 'TantegelThroneRoom'


def run():
    parser = argparse.ArgumentParser(description="Dragon Warrior")
    parser.add_argument("--dev", action="store_true",
                        help="run with dev_config (god mode, no battles, coordinates visible, debug keys)")
    parser.add_argument("--checkpoint", choices=CHECKPOINT_NAMES,
                        help="start from a playtest checkpoint in data/checkpoints/ (see PLAYTEST.md); saves go to "
                             f"{CHECKPOINT_SAVE_DIR} instead of src/saves")
    args = parser.parse_args()
    config = dev_config if args.dev else prod_config
    if args.checkpoint:
        config = {**config, 'CHECKPOINT': args.checkpoint, 'SPLASH_SCREEN_ENABLED': False}
    game = Game(config=config)
    game.main()


if __name__ == "__main__":
    run()
