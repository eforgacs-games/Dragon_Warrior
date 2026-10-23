import argparse
import os
import random
import sys
from typing import List, Tuple

from pygame import FULLSCREEN, K_DOWN, K_LEFT, K_RIGHT, K_UP, K_a, K_d, K_i, K_k, K_s, \
    K_w, RESIZABLE, display, event, image, init, key, K_F1, K_F2, K_F3, K_F4, K_F11, KEYDOWN, SCALED, \
    K_RETURN, VIDEORESIZE
from pygame.display import set_mode, set_caption
from pygame.event import get
from pygame.time import Clock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.text.intro_lookup_table import ControlInfo
from src import maps
from src.calculation import Calculation, get_tile_id_by_coordinates
from src.camera import Camera
from src.checkpoints import CHECKPOINT_NAMES, CHECKPOINT_SAVE_DIR, FACING_KEY, checkpoint_hero_name, read_checkpoint
from src.color import LOW_HP_RED, RED, WHITE, is_low_hp, window_color
from src.common import A_OR_START_KEYS, Graphics, is_facing_medially, is_facing_laterally, \
    set_gettext_language
from src.common import is_facing_up, is_facing_down, is_facing_left, is_facing_right
from src.config.dev_config import dev_config
from src.config.prod_config import prod_config
from src.debug_tools import DebugTools
from src.constants import (
    TANTEGEL_CURSED_ROW, TANTEGEL_OVERWORLD_EXIT,
)
from src.direction import Direction
from src.directories import Directories
from src.drawer import Drawer
from src.encounters import ENEMY_GROUPS, encounter_group, roll_encounter
from src.game_functions import set_character_position, GameFunctions
from src.game_state import GameState
from src.guardians import guardian_at
from src.intro import Intro
from src.items import TreasureChestHistory
from src.map_layouts import MapLayouts
from src.maps import map_lookup
from src.menu import CommandMenu
from src.movement import Movement
from src.music_player import MusicPlayer
from src.npc_schedule import NPCSchedule, POP_UP_FRAME
from src.npc_movement import npc_may_step_onto, step
from src.options_screen import apply_options
from src.save_file import SaveFile
from src.player.player import Player
from src.sound import Sound
from src.sprites.fixed_character import FixedCharacter
from src.sprites.roaming_character import RoamingCharacter
from src.battle_controller import BattleController
from src.ending import Ending
from src.story_flags import StoryFlags
from src.title_menu import TitleMenu
from src.waiting import SPEED_KEYS, FramePacer, clear_events_keeping_quit, game_speed, reset_game_speed, set_game_speed
from src.waiting import game_ticks as get_ticks  # game time: runs N times as fast at speed N
from src.map_manager import MapManager
from src.visual_effects import flash_transparent_color, force_field_flash
from src.waiting import quit_if_requested, wait
from src.windows import COMMAND_WINDOW




# NES DoJoyUp etc. (Bank00) only start a step when FrameCounter & $0F is 0. A step is 16 frames long too.
STEP_SYNC_FRAMES = 16
# NES ChkBlkSand (Bank03, LCE0A): a step onto a hill block is followed by three WaitForNMI, with nothing moving, before
# the step's fight roll
HILL_PAUSE_FRAMES = 3

# NES CheckInputs (Bank03) checks up, then down, then left, then right
DIRECTION_KEYS = ((Direction.UP.value, (K_UP, K_w)), (Direction.DOWN.value, (K_DOWN, K_s)),
                  (Direction.LEFT.value, (K_LEFT, K_a)), (Direction.RIGHT.value, (K_RIGHT, K_d)))


def held_direction(current_key) -> int | None:
    """The direction the held keys point the hero in, or None if no direction key is held."""
    for direction, keys in DIRECTION_KEYS:
        if any(current_key[direction_key] for direction_key in keys):
            return direction
    return None


class Game:
    npc_asked_to_make_way: tuple[RoamingCharacter, int] | None

    def __init__(self, config):

        self.config = config
        self.sound = Sound(config)
        self.graphics = Graphics(config)
        self.directories = Directories(config)
        self.calculation = Calculation(config)
        self.game_functions = GameFunctions(config)
        self.movement = Movement(self.config)
        # Only still passed to confirmation_prompt, which ignores it: the dialog's down arrow blinks on its own
        # (src/cursor.py DialogArrowBlink)
        self.show_arrow = True
        self.game_state = GameState(config=config)
        self.music_player = MusicPlayer(config)

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

        # engine: keys 1 to 4 change the game speed (self.fps); it lasts until the game is closed, and isn't saved
        reset_game_speed()
        # intro
        self.start_time = get_ticks()
        self.splash_screen_enabled = self.game_state.config["SPLASH_SCREEN_ENABLED"]
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
        # Pixels the hero and the NPCs move a frame: one NES pixel (TILE_SIZE is 16 * SCALE), so a step takes
        # STEP_SYNC_FRAMES (16) frames at any SCALE, like the NES
        self.speed = self.game_state.config["TILE_SIZE"] // 16
        # NES FrameCounter, NPCUpdateCntr and CharLeftRight (src/npc_schedule.py): when the hero may start a step, which
        # NPCs may move on each frame, and the walking frame
        self.npc_schedule = NPCSchedule()
        # Whether this frame is an IdleUpdate frame (the hero standing, see idle_frame), and whether the hero's step
        # ends on it
        self.idle_update = False
        self.step_ends = False
        # Frames left of the pause after a step onto a hill (HILL_PAUSE_FRAMES, see hill_pause_frame)
        self.hill_pause_frames = 0
        # NPCS_MAKE_WAY: the roaming NPC the hero just bumped into, and the hero's direction (see ask_npc_to_make_way)
        self.npc_asked_to_make_way = None

        self.auto_battle = self.game_state.config["AUTO_BATTLE"]
        self.invulnerable = self.game_state.config["INVULNERABLE"]

        # debugging
        self.show_coordinates = self.game_state.config["SHOW_COORDINATES"]
        init()
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
        self.title_menu = TitleMenu(self)

        self.clock = Clock()
        # Half a step at most between two draws: every step is drawn at least once while it's under way, so the drawer
        # sees the hero moving (which closes the pop-up window), and he never moves more than a tile between two draws
        self.frame_pacer = FramePacer(max_frames=STEP_SYNC_FRAMES // 2)

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
            self.title_menu.show_main_menu_screen(self.screen)
        if self.config.get('CHECKPOINT'):
            self.load_checkpoint(self.config['CHECKPOINT'])
        self.drawer.draw_all(self.screen, self.loop_count, self.big_map, self.current_map, self.player, self.cmd_menu,
                             self.foreground_rects, self.game_state.enable_animate, self.camera,
                             self.initial_dialog_enabled,
                             self.events, self.skip_text, self.story_flags.left_throne_room, self.game_state,
                             self.color)
        while True:
            self.clock.tick(self.fps)
            self.run_due_frames()
            self.drawer.draw_all(self.screen, self.loop_count, self.big_map, self.current_map, self.player,
                                 self.cmd_menu, self.foreground_rects, self.sprites_animate, self.camera,
                                 self.initial_dialog_enabled, self.events, self.skip_text, self.story_flags.left_throne_room,
                                 self.game_state, self.color)
            display.flip()
            self.loop_count += 1

    def start_at_throne_room(self) -> None:
        """Start a new quest in the throne room the way NES MainGameEngine does for every start: StartAtThroneRoom
        (Bank03, LCB47) loads BlackPalPtr at once, so the title menu's windows cut to black with no fade out, and
        MapChngNoSound (Bank00, LB091) draws the throne room while the palettes are black, starts its music in place
        of the menu's (ResumeMusicTbl) and fades it in with one PalFadeIn. change_map does all of that and makes the
        new CommandMenu."""
        throne_room = map_lookup['TantegelThroneRoom'](self.config)
        self.map_mgr.change_map(throne_room, destination_coordinates=throne_room.initial_coordinates,
                                direction=self.player.direction_value, fade_out_first=False)

    def run_due_frames(self) -> None:
        """Read the events, then run the frames on the map that are due before the next draw (FramePacer): one at a
        time while drawing keeps up with 60 * N FPS, more when it doesn't, so walking and the NPCs keep pace with the
        game speed and the game clock everything else reads. A frame that changes the map, or opens something with a
        loop of its own (a battle, a dialog), ends the run: the next one starts after the next draw."""
        frames = self.frame_pacer.frames_due()
        self.read_events()
        for _ in range(frames):
            current_map = self.current_map
            self.map_frame()
            if self.current_map is not current_map or self.frame_pacer.stalled():
                return

    def get_events(self) -> None:
        """Read the events, then run one frame on the map."""
        self.read_events()
        self.map_frame()

    def read_events(self) -> None:
        """Take the events off the queue (draw_all reads them too) and handle the keys and the window's events."""
        self.events = get()
        self._handle_pygame_events(self.events)

    def map_frame(self) -> None:
        """One frame on the map (one NES frame): the hero, fights, the NPCs and what the step leads to."""
        if self.hill_pause_frames:
            self.hill_pause_frame()
            event.pump()
            return
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
        self.player.next_coordinates = step(self.player.rect.y // self.tile_size, self.player.rect.x // self.tile_size,
                                            self.player.direction_value)
        self.player.next_next_coordinates = step(self.player.rect.y // self.tile_size,
                                                 self.player.rect.x // self.tile_size, self.player.direction_value,
                                                 offset=2)
        self.set_player_images_by_equipment()
        self.handle_environment_damage()
        self.handle_death()

    def _handle_map_updates(self) -> None:
        """
        Updates character positions and handles warp logic.
        """
        if not self.world_frozen:
            self.do_sprites()
        # currently can't process staircases right next to one another, need to fix
        # a quick fix would be to add an exception in the conditional for
        # the map where staircases right next to each other need to be enabled,
        # as done with Cantlin and others below
        self.handle_warps()

    @property
    def frame_counter(self) -> int:
        """NES FrameCounter: a held direction only starts a step when it's a multiple of 16 (see move_player), and
        it decides which NPCs move (src/npc_schedule.py)."""
        return self.npc_schedule.frame_counter

    @frame_counter.setter
    def frame_counter(self, value: int) -> None:
        self.npc_schedule.frame_counter = value

    def do_sprites(self) -> None:
        """One frame on the map, after the hero's part: NMI counts it (INC FrameCounter), then NES DoSprites (Bank00)
        moves the walking animation and the roaming NPCs on (src/npc_schedule.py). Like DoSprites, it runs on every
        frame the map is up, whether the hero is walking or standing.
        On the frame the hero has stood still for $31 frames, IdleUpdate (Bank03) opens the pop-up window, whose
        drawing calls DoSprites (WndCalcBufAddr, Bank01), then sets FrameCounter to $32 and calls DoSprites again, so
        that frame has two. The drawer draws the window from then on, until the hero moves."""
        self.npc_schedule.count_frame()
        if self.idle_update and self.frame_counter == POP_UP_FRAME:
            self.drawer.display_hovering_stats = True
            self.run_sprites()
            self.frame_counter = POP_UP_FRAME + 1
        self.idle_update = False
        self.run_sprites()
        if self.step_ends:
            # NES: DoJoyUp etc. return through ChkSpecialLoc to GameEngineLoop -> JoypadCheckLoop
            self.step_ends = False
            self.frame_counter = 0

    def run_sprites(self) -> None:
        """NES DoSprites: the walking animation and the roaming NPCs."""
        self.npc_schedule.start_sprites()
        if self.game_state.enable_roaming and self.current_map.roaming_characters:
            # NES UpdateNPCs1: no NPC starts a new step once a pause or the command window has been asked for
            self.move_roaming_characters(start_new_steps=not self.freeze_pending)
            self.update_roaming_character_positions()
        # A request to make way is only for the frame right after the bump
        self.npc_asked_to_make_way = None
        self.npc_schedule.end_sprites()

    def _handle_player_movement(self) -> None:
        """
        Checks if the game is paused or if movement is disabled; if not,
        moves the player based on the current key state.
        """
        if self.world_frozen:
            # NES: every command, the pause and the windows they open end with JMP JoypadCheckLoop, which resets
            # FrameCounter, so a direction held as they close starts a step at once. They open between NPC turns
            # (resolve_pending_freezes), when FrameCounter & $0F is 0 already, so the NPCs carry on where they were.
            self.frame_counter = 0
            return
        if not self.game_state.enable_movement:
            return
        if self.freeze_pending and not self.player.is_moving:
            # NES GameEngineLoop only reads START and A between steps (DoJoyUp etc. move a whole tile before
            # returning), so a step already under way is finished, but no new one is started. PausePrepLoop and
            # DoNCCmdWindow keep counting frames until the end of the NPCs' turn.
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
        It's also frozen while RADIANT's or a torch's light grows (light_growing).
        """
        return (self.paused or self.cmd_menu.launch_signaled or self.cmd_menu.menu.is_enabled()
                or self.light_growing)

    @property
    def light_growing(self) -> bool:
        """Whether RADIANT's or a torch's light is still growing. NES LightIncreaseLoop (DoSpell, Bank03, about 24
        frames: a PostMoveUpdate of LIGHT_REDRAW_FRAMES for each 2 blocks) and UseTorch redraw the light before they
        return, with the NPCs still stopped, so nothing reads the joypad and nothing moves until it's done (#307).
        Drawer.handle_darkness advances the light, and only runs while the darkness is drawn."""
        return (bool(self.game_state.pending_light_redraws) and self.current_map.is_dark
                and self.game_state.config['ENABLE_DARKNESS'])

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
        frame on which every NPC is lined up on a tile, and only then (before that frame's DoSprites, so before any NPC
        starts a step) pause or set StopNPCMove. START is checked
        before A (CheckInputs), so a pause wins.
        """
        if not self.freeze_pending:
            self.freeze_wait_frames = 0
            return
        if not self.everyone_on_a_tile():
            if not self.player.is_moving:
                self.freeze_wait_frames += 1
            return
        if not self.npc_schedule.between_turns:
            # The next frame would be an NPC turn's decision frame only once this one is the last of a turn
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
            quit_if_requested(current_event)
            if current_event.type == KEYDOWN:
                self.handle_keypresses(current_event)
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
        """Set the color of every window (their borders, text and cursors; NES background palette 0's color 1). Every
        window is generated in this color each time it is drawn (src/window_renderer.py), the COMMAND window included,
        so there is no window to redraw ahead of time.

        The map's palette 0 tiles (towns, castles, bridges and water) use that same color, so they change with the
        windows. When they do, the whole map is redrawn, as when the hero steps under a roof; a map that hasn't been
        drawn yet (loop_count 1) is drawn in full on its first frame anyway."""
        self.color = color
        current_map = getattr(self, 'current_map', None)
        if current_map is not None and current_map.set_low_hp_palette(color == LOW_HP_RED):
            drawer = getattr(self, 'drawer', None)
            if drawer is not None and drawer.background is not None and self.loop_count != 1:
                drawer.draw_all_tiles_in_current_map(current_map, drawer.background)

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
            tile = get_tile_id_by_coordinates(column, row, self.current_map)
            # NES CheckBlockDmg: swamp and force field damage come before the fight roll, and a hero they kill
            # doesn't fight (handle_death, later this frame, shows the death on the map)
            self.handle_environment_damage(tile)
            if self.player.current_hp <= 0:
                return
            if tile == 'HILLS':
                # NES ChkBlkSand: the fight roll waits for the hill's pause (hill_pause_frame)
                self.hill_pause_frames = HILL_PAUSE_FRAMES
                return
            self.roll_for_fight(column, row, tile)

    def hill_pause_frame(self) -> None:
        """One of the HILL_PAUSE_FRAMES frames NES ChkBlkSand waits after a step onto a hill (three WaitForNMI). Nothing
        moves and nothing animates (no DoSprites), and FrameCounter stays at the 0 the step left it at, as
        JoypadCheckLoop resets it afterwards anyway. The step's fight roll (ChkSandFight) comes after the last one."""
        self.hill_pause_frames -= 1
        if self.hill_pause_frames:
            return
        column, row = self.player.rect.x // self.tile_size, self.player.rect.y // self.tile_size
        self.roll_for_fight(column, row, get_tile_id_by_coordinates(column, row, self.current_map))

    def roll_for_fight(self, column: int, row: int, tile: str | None) -> None:
        """NES CheckBlockDmg's fight roll for the block the hero has just stepped onto, and the fight if it starts."""
        group = encounter_group(self.current_map.identifier, column, row)
        if group is None:
            return
        self.last_zone = group
        enemies_in_current_zone = ENEMY_GROUPS[group] if self.game_state.config["FORCE_BATTLE"] else \
            roll_encounter(self.current_map.identifier, tile, column, row)
        if enemies_in_current_zone is not None and not self.game_state.config["NO_BATTLES"]:
            self.battle_ctrl.run_battle(enemies_in_current_zone)
        self.battle_ctrl.battle_menu_row = 0
        self.battle_ctrl.battle_menu_column = 0

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
                # The command window, red now, with the arrow on the command that was chosen (WndAPressed)
                self.battle_ctrl.draw_command_window(True)
                self.battle_ctrl.launch_battle = False
                display.flip()
            else:
                self.drawer.draw_all_tiles_in_current_map(self.current_map, self.drawer.background)
                display.flip()
            self.music_player.load_and_play_music(self.directories.death_sfx, 1)
            self.game_state.enable_movement = False
            wait(self.calculation.convert_to_milliseconds(318), self.game_state.config)
            clear_events_keeping_quit()  # keys pressed during the death music are dropped (a window close isn't)

            # NES DeathText: the game then loops until JoypadBtns AND #$09, A or START (held or not)
            self.cmd_menu.show_text_in_dialog_box(self._("Thou art dead."), disable_sound=True,
                                                  advance_keys=A_OR_START_KEYS)
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
        # NES DeathText -> StartAtThroneRoom (LEDDE): the screen cuts to black and the throne room fades in once
        next_map = map_lookup['TantegelThroneRoom'](self.config)
        self.change_map(next_map, fade_out_first=False)
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

    def handle_environment_damage(self, tile: str | None = None):
        """Swamp and force field damage for the block the hero stands on (current_tile unless tile is given), once
        per step. handle_battles calls it with the block just stepped onto, before the fight roll."""
        # NES ChkOtherBlocks: once the Dragonlord is dead, swamps and barriers no longer hurt
        if self.story_flags.dragonlord_defeated:
            return
        if tile is None:
            tile = self.player.current_tile
        if not self.player.armor == "Erdrick's Armor":
            if not self.player.is_moving:
                if tile == 'MARSH':
                    if not self.player.received_environment_damage:
                        self.damage_step(damage_amount=2)
                elif tile == 'BARRIER':
                    if not self.player.received_environment_damage:
                        self.damage_step(damage_amount=15, force_field=True)
            else:
                self.player.received_environment_damage = False

    def damage_step(self, damage_amount, force_field=False):
        # God mode or invulnerable: take no damage
        if self.player.god_mode or self.invulnerable:
            return

        self.player.current_hp = max(self.player.current_hp - damage_amount, 0)
        self.sound.play_sound(self.directories.swamp_sfx)
        self.player.received_environment_damage = True
        if force_field:
            # NES force field damage (LCE30): the screen flashes red three times
            force_field_flash(RED, self.screen, self.game_state.config)
        else:
            # NES DoSwampDamage: one red flash
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

    def handle_keypresses(self, current_keydown_event):
        if self.paused:
            # NES GamePaused only reads START until the game is unpaused
            self.handle_start_button(current_keydown_event)
            self.handle_fullscreen_toggle(current_keydown_event)
            return
        # B does nothing on the map: in the COMMAND window it is read with the other buttons (CommandMenu.select_command)
        self.handle_a_button(current_keydown_event)
        self.handle_start_button(current_keydown_event)
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
            elif not (self.cmd_menu.launch_signaled or self.cmd_menu.menu.is_enabled() or self.light_growing):
                # NES CheckInputs: START only pauses from the map, not while a window is up or the light grows. The
                # hero finishes the step under way first (resolve_pending_freezes).
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

    @property
    def fps(self) -> int:
        """The most frames per second the main loop draws: the NES's 60 times the game speed (src/waiting.py). Walking,
        NPC steps and light changes count map frames (frame_counter too), which run at that rate even when drawing
        can't keep up with it (run_due_frames), so they speed up with everything else."""
        return self.game_state.config["FPS"] * game_speed()

    def handle_fps_changes(self, keydown_event) -> None:
        """Keys 1 to 4: normal, 2x, 4x or 8x game speed (60, 120, 240 or 480 FPS). It applies everywhere: the map, battles,
        dialogs, menus and effects (src/waiting.py reads these keys in their loops and waits too, without this text)."""
        speed = SPEED_KEYS.get(keydown_event.key)
        if speed is None:
            return
        set_game_speed(speed)
        if speed == 1:
            speed_text = self._("Game set to normal speed.\n({} FPS)").format(self.fps)
        else:
            speed_text = self._("Game set to {}x speed.\n({} FPS)").format(speed, self.fps)
        self.draw_temporary_text(speed_text)

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
        """Show a settings message (F2, keys 1 to 4, ...) for a second. It's not part of the game, so it stays up for a
        real second at any game speed: the dialog closes 1000 game milliseconds after temp_text_start, so start it
        that much later at higher speeds."""
        temp_text_start = get_ticks() + 1000 * (game_speed() - 1)
        self.cmd_menu.show_text_in_dialog_box(text, add_quotes=add_quotes, temp_text_start=temp_text_start,
                                              skip_text=False)

    def process_staircase_warps(self, staircase_location: tuple, staircase_dict: dict) -> None:
        if (self.player.row, self.player.column) == staircase_location:
            self.map_mgr.process_warp(staircase_dict)

    def change_map(self, next_map: maps.DragonWarriorMap, destination_coordinates: tuple | None = None,
                   direction: int | None = None, fade_out_first: bool = True) -> None:
        self.map_mgr.change_map(next_map, destination_coordinates, direction, fade_out_first=fade_out_first)

    def set_big_map(self):
        self.map_mgr.set_big_map()

    def set_roaming_character_positions(self):
        self.map_mgr.set_roaming_character_positions()

    def unlaunch_menu(self, menu_to_unlaunch: CommandMenu) -> None:
        """
        Close the COMMAND window (Bank03 ClrNCCmdWnd: RemoveWindow, and the NPCs move again).
        :return: None
        """
        menu_to_unlaunch.launch_signaled = False
        if menu_to_unlaunch is not self.cmd_menu:
            # OUTSIDE, RETURN or the Wings changed the map (and the COMMAND menu) under this window, which the new map
            # already replaced: just close it. Its drop-up would paint the old map's tiles and characters over the new
            # map for a few frames.
            menu_to_unlaunch.menu.disable()
        elif menu_to_unlaunch.menu.is_enabled():
            self.game_state.unpause_all_movement()
            menu_to_unlaunch.window_drop_up_effect(*COMMAND_WINDOW)
            menu_to_unlaunch.menu.disable()
        self.drawer.draw_all_tiles_in_current_map(self.current_map, self.drawer.background)

    def move_player(self, current_key) -> None:
        """
        One frame of the hero's walking, the way NES CheckInputs (Bank03) and DoJoyUp/DoJoyDown/DoJoyLeft/DoJoyRight
        (Bank00) handle the D-pad:
        - Between steps, CheckJoyUp etc. point the hero in the held direction (STA CharDirection) on the frame it's
          read, before anything else. Up wins over down, down over left, left over right.
        - DoJoyUp etc. only start a step when FrameCounter & $0F is 0 (UpSynced...). Otherwise they drop their return
          address and JMP IdleUpdate, which waits a frame (WaitForNMI, where NMI does INC FrameCounter) and reads the
          pad again. So a tap that's let go before then only turns the hero.
        - A step takes 16 frames, then GameEngineLoop's JoypadCheckLoop resets FrameCounter to 0, so a direction held
          (the same one or a new one) starts the next step on the very next frame: no pause between steps.
        - From standing still, FrameCounter has been counting since the last step, so the first step starts on the
          next frame that is a multiple of 16: 0 to 15 frames after the press.
        - A wall or an NPC in the way (CheckCollision -> DirectionBlocked) plays SFX_WALL_BUMP, resets FrameCounter
          and goes to IdleUpdate, so holding into it bumps every 16 frames. The overworld, towns and dungeons all use
          the same check.
        :param current_key: The key currently being pressed by the user.
        """
        # TODO(ELF): separate dependency of camera pos and player pos
        if not self.player.is_moving:
            direction = held_direction(current_key)
            if direction is None:
                self.idle_frame()
                return
            self.player.direction_value = direction
            if self.frame_counter % STEP_SYNC_FRAMES:
                self.idle_frame()
                return
            self.player.is_moving = True
        # not sure if setting the player sprites to dirty makes a difference
        self.current_map.player_sprites.dirty = 1
        if is_facing_medially(self.player):
            self.move_medially(self.player)
            on_a_tile = self.camera.pos[1] % self.tile_size == 0
        elif is_facing_laterally(self.player):
            self.move_laterally(self.player)
            on_a_tile = self.camera.pos[0] % self.tile_size == 0
        else:
            on_a_tile = True
        self.current_map.player_sprites.dirty = 1
        if not on_a_tile:
            return
        if self.player.bumped:
            # NES DirectionBlocked: no step is taken; FrameCounter is reset, then IdleUpdate waits a frame
            self.player.bumped = False
            self.frame_counter = 0
            self.idle_frame()
            self.ask_npc_to_make_way()
        else:
            # TODO(ELF): sometimes self.tiles_moved_since_spawn gets set to 1 when spawning -
            #  should always be 0 when the map starts.
            self.count_step()
            # FrameCounter goes back to 0 once this frame's DoSprites has run (see do_sprites)
            self.step_ends = True
        self.finish_step(self.player)

    def ask_npc_to_make_way(self) -> None:
        """Quality of life, not NES (NPCS_MAKE_WAY, on by default): when the hero bumps into a roaming NPC, that NPC
        steps out of the way on the next frame (see make_way). On the NES it stays put and only moves when its own
        random turn comes. NPCs that never move (shopkeepers, guards at their posts, King Lorik: everyone not in the
        map's roaming list) never make way."""
        if not self.config.get('NPCS_MAKE_WAY'):
            return
        blocked_at = step(self.player.row, self.player.column, self.player.direction_value)
        for roaming_character in self.current_map.roaming_characters:
            if not roaming_character.is_moving and (roaming_character.row, roaming_character.column) == blocked_at:
                self.npc_asked_to_make_way = roaming_character, self.player.direction_value
                return

    def idle_frame(self) -> None:
        """NES IdleUpdate (Bank03): wait for the next frame, which counts it in FrameCounter (NMI: INC FrameCounter,
        which do_sprites does on every frame on the map). On the 49th ($31) frame of standing still, the pop-up status
        window is shown and FrameCounter is set to $32, skipping a count, so the steps after a long wait line up a
        frame earlier. FrameCounter is one byte."""
        self.idle_update = True

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
            destination = step(character.row, character.column, character.direction_value)
            if isinstance(character, RoamingCharacter):
                # NES UpdateNPCs1: NPCs keep to the NES map and walk on fewer tiles, see src/npc_movement.py
                blocked = not npc_may_step_onto(self.current_map, destination)
            else:
                blocked = self.is_impassable(character.next_tile_id)
            if blocked or self.character_in_path(character) or (
                    character is not self.player and self.npc_crosses_cover_boundary(character)):
                self.movement.bump_and_reset(character, character.next_tile_id, character.next_next_tile_id)
                delta_x = delta_y = 0
            else:
                character.step_origin = (character.row, character.column)
                character.step_destination = destination
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
        next_coordinates = step(character.row, character.column, character.direction_value)
        others = [*self.current_map.fixed_characters, *self.current_map.roaming_characters, self.player]
        for other in others:
            if other is character:
                continue
            if next_coordinates in ((other.row, other.column), other.step_origin, other.step_destination):
                return True
        return False

    @staticmethod
    def finish_step(character: Player | RoamingCharacter) -> None:
        character.is_moving, character.next_tile_checked = False, False
        character.step_origin = character.step_destination = None

    def npc_crosses_cover_boundary(self, character: Player | RoamingCharacter) -> bool:
        """NES $B839-$B84F: an NPC can't step into or out of a covered area."""
        next_row, next_column = step(character.row, character.column, character.direction_value)
        return self.current_map.crosses_cover_boundary(character.row, character.column, next_row, next_column)

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
        One frame of the roaming characters, NES UpdateNPCs1 (Bank00, $B76F): on the first frame of its 16-frame turn
        (src/npc_schedule.py), each NPC of the pair whose turn it is turns to a random direction (SetNPCDir) and starts
        a step that way, unless something is in the way (HaltNPCMoveCalcs: it stays put, facing that way). An NPC that
        is stepping moves 1 NES pixel a frame (NPCProcessCont), so it arrives on the last frame of its turn.
        :param start_new_steps: False lets characters partway through a step finish it, but none start a new one
            (NES StopNPCMove).
        """
        roaming_characters = self.current_map.roaming_characters
        deciding = []
        making_way = None
        if self.npc_schedule.is_decision_frame and start_new_steps:
            if self.npc_asked_to_make_way is not None:
                # A bump resets FrameCounter, so the frame after it is always a decision frame: the step aside starts
                # with every NPC on a tile, and ends on the turn's last frame like any other step
                npc, hero_direction = self.npc_asked_to_make_way
                if npc in roaming_characters and not npc.is_moving and self.make_way(npc, hero_direction):
                    making_way = npc
            # Empty slots (NES: X and Y 0), past the end or of removed NPCs, keep their place in the turns
            slots_on_turn = self.npc_schedule.slots_on_turn()
            deciding = [roaming_character for index, roaming_character in enumerate(roaming_characters)
                        if (index if roaming_character.slot is None else roaming_character.slot) in slots_on_turn
                        and not roaming_character.is_moving]
        for roaming_character in roaming_characters:
            if roaming_character in deciding:
                if roaming_character.turns_to_rest:
                    # Just made way: it stays where it is for this turn, so it doesn't walk straight back
                    roaming_character.turns_to_rest -= 1
                else:
                    self.start_npc_step(roaming_character)
            elif roaming_character.is_moving and roaming_character is not making_way:
                self.continue_npc_step(roaming_character)

    def start_npc_step(self, roaming_character: RoamingCharacter) -> None:
        """NES SetNPCDir and the checks after it: turn to a random direction, and take the first pixel of a step that
        way if nothing is in the way (Game.move checks it)."""
        roaming_character.direction_value = random.choice(list(map(int, Direction)))
        self.begin_npc_step(roaming_character)

    def begin_npc_step(self, roaming_character: RoamingCharacter) -> bool:
        """Take the first pixel of a step the way the NPC faces, if nothing is in the way (Game.move checks it).
        Returns whether the step started."""
        set_character_position(roaming_character, self.tile_size)
        start = roaming_character.rect.copy()
        self.continue_npc_step(roaming_character)
        # A blocked step reserves nothing (Game.move), and the NPC stays where it is
        roaming_character.is_moving = roaming_character.step_destination is not None
        if roaming_character.is_moving:
            roaming_character.last_rect = start
        return roaming_character.is_moving

    def make_way(self, roaming_character: RoamingCharacter, hero_direction: int) -> bool:
        """NPCS_MAKE_WAY (not NES): step out of the hero's way, to one side (either, picked at random) if it can, or
        else one tile further along the hero's direction, away from the hero. Each step is the ordinary NPC step
        (begin_npc_step), so every rule a random step obeys holds: walkable tiles and the map, the roof cover boundary,
        other characters and their reserved steps, and the hero's tile; it just starts at once instead of on the NPC's
        turn. If no way is free it stays put, facing the way it was. Returns whether it moved.
        After making way it rests through its next turn (turns_to_rest), so it doesn't step straight back into the
        hero's path: it stands still for at least 64 frames (about a second) after arriving."""
        sideways = [direction for direction in map(int, Direction) if direction % 2 != hero_direction % 2]
        facing = roaming_character.direction_value
        for direction in [*random.sample(sideways, len(sideways)), hero_direction]:
            roaming_character.direction_value = direction
            if self.begin_npc_step(roaming_character):
                roaming_character.turns_to_rest = 1
                return True
        roaming_character.direction_value = facing
        return False

    def continue_npc_step(self, roaming_character: RoamingCharacter) -> None:
        """NES NPCProcessCont: move 1 NES pixel, and finish the step on arriving."""
        if is_facing_medially(roaming_character):
            self.move_medially(roaming_character)
            arrived = roaming_character.rect.y % self.tile_size == 0
        else:
            self.move_laterally(roaming_character)
            arrived = roaming_character.rect.x % self.tile_size == 0
        if arrived and roaming_character.step_destination is not None:
            self.finish_step(roaming_character)
            set_character_position(roaming_character, self.tile_size)

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
        save = SaveFile.from_save(save_file)
        save.restore_player(self.player)
        self.story_flags = save.story_flags
        # NES LoadSavedData (LFBC8): the log's message speed; and this game's dialog style and NPCS MAKE WAY. Older
        # saves: NORMAL, CLASSIC, ON
        apply_options(self.game_state.config, save.options)
        self.chest_history = TreasureChestHistory()
        self.repel_timer = 0
        if self.player.is_cursed:
            # NES StartAtThroneRoom (LCB6B): a cursed hero always starts with 1 HP
            self.player.current_hp = 1
        # NES StartAtThroneRoom: the fade in after loading sets the window color for the loaded HP (ChkLowHPPal)
        self.load_window_palette()
        # Reload the starting map even if it's the one already shown, so the loaded flags apply to it
        if save.current_map in map_lookup:
            next_map = map_lookup[save.current_map](self.config)
            destination = (save.player_row, save.player_column)
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
        before the first frame. The checkpoint's hero name, "Arthur", is given in the game's language (검객 in
        Korean). Saving with King Lorik from then on writes to CHECKPOINT_SAVE_DIR, not to the real save slots."""
        checkpoint = read_checkpoint(name)
        checkpoint['Name'] = checkpoint_hero_name(checkpoint['Name'], self.config['LANGUAGE'])
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
