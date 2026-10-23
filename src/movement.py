"""MovementController: the hero's and the NPCs' movement on the map, which used to live on Game.

Game runs the main loop and the frame pipeline (Game.map_frame) and calls this for each frame's movement. The
controller holds a reference to the game (MovementGame) and reads what it shares with the rest of the game (the
player, the map, the camera) from it each time, since the game replaces some of them (a map change makes a new map).
Where an NPC may step, as far as the map goes, is src/npc_movement.py; when the NPCs move is src/npc_schedule.py.
"""
import random
from typing import Any, Protocol

from pygame import key

from src.calculation import Calculation, get_tile_id_by_coordinates
from src.camera import Camera
from src.common import B_BUTTON_KEYS, DOWN_KEYS, LEFT_KEYS, RIGHT_KEYS, UP_KEYS, is_facing_down, \
    is_facing_laterally, is_facing_left, is_facing_medially, is_facing_right, is_facing_up
from src.direction import Direction
from src.directories import Directories
from src.game_functions import set_character_position
from src.game_state import GameState
from src.npc_movement import npc_may_step_onto, step
from src.npc_schedule import NPCSchedule, POP_UP_FRAME
from src.player.player import Player
from src.sound import Sound
from src.sprites.fixed_character import FixedCharacter
from src.sprites.roaming_character import RoamingCharacter
from src.waiting import MAP_CONTEXT, with_virtual_keys


# A tile is 16 NES pixels across, and the hero and the NPCs walk one NES pixel a frame
NES_PIXELS_PER_TILE = 16
# NES DoJoyUp etc. (Bank00) only start a step when FrameCounter & $0F is 0. A step is 16 frames long too.
STEP_SYNC_FRAMES = NES_PIXELS_PER_TILE
# RUN BUTTON (not NES, the options overlay): holding B, the hero walks twice as fast, a step in 8 frames
RUN_SPEED_FACTOR = 2
RUN_STEP_FRAMES = STEP_SYNC_FRAMES // RUN_SPEED_FACTOR
# NES ChkBlkSand (Bank03, LCE0A): a step onto a hill block is followed by three WaitForNMI, with nothing moving, before
# the step's fight roll
HILL_PAUSE_FRAMES = 3

# NES CheckInputs (Bank03) checks up, then down, then left, then right
# (the keys are the player's, src/controls.py)
DIRECTION_KEYS = ((Direction.UP.value, UP_KEYS), (Direction.DOWN.value, DOWN_KEYS),
                  (Direction.LEFT.value, LEFT_KEYS), (Direction.RIGHT.value, RIGHT_KEYS))


def held_direction(current_key) -> int | None:
    """The direction the held keys point the hero in, or None if no direction key is held."""
    for direction, keys in DIRECTION_KEYS:
        if any(current_key[direction_key] for direction_key in keys):
            return direction
    return None


class MovementGame(Protocol):
    """What MovementController uses of the Game. It reads them from the Game each time, since the Game replaces some
    of them (a map change makes a new map and a new CommandMenu)."""
    config: dict
    game_state: GameState
    current_map: Any
    player: Player
    camera: Camera
    tile_size: int
    drawer: Any
    cmd_menu: Any
    paused: bool
    # START or A pressed while someone is between tiles: see MovementController.resolve_pending_freezes
    pause_requested: bool
    # SELECT or Tab: the options overlay, which waits for the same moment as the pause
    options_requested: bool
    # The MESSAGE LOG key: the message log, which waits for the same moment as the pause
    message_log_requested: bool
    # G: auto-grind (src/auto_grind.py), which starts at the same moment as the pause
    auto_grind_requested: bool
    # M: the dungeon map (src/dungeon_map.py), which opens at the same moment as the pause
    dungeon_map_requested: bool
    cmd_menu_requested: bool
    # A with SMART A on: run_smart_command when the COMMAND window would open
    smart_a_pending: bool
    # Shift + F1/F2/F3 or F1/F2/F3: a save state to save or load (Game.handle_save_state_keys), and once it's due
    state_request: tuple[str, int] | None
    state_request_due: tuple[str, int] | None

    def count_step(self) -> None: ...

    def open_options(self) -> None: ...

    def open_dungeon_map(self) -> None: ...
    def open_message_log(self) -> None: ...

    def start_auto_grind(self) -> None: ...

    def run_smart_command(self) -> bool: ...

    def roll_for_fight(self, column: int, row: int, tile: str | None) -> None: ...


class MovementController:
    """The hero's and the NPCs' movement, frame by frame. Game.map_frame calls it once a frame."""

    def __init__(self, game: MovementGame):
        self.game = game
        self.sound = Sound(game.config)
        self.calculation = Calculation(game.config)
        self.directories = Directories(game.config)
        # Pixels the hero and the NPCs move a frame: one NES pixel (TILE_SIZE is 16 * SCALE), so a step takes
        # STEP_SYNC_FRAMES (16) frames at any SCALE, like the NES
        self.speed = game.config["TILE_SIZE"] // NES_PIXELS_PER_TILE
        # NES FrameCounter, NPCUpdateCntr and CharLeftRight (src/npc_schedule.py): when the hero may start a step, which
        # NPCs may move on each frame, and the walking frame
        self.npc_schedule = NPCSchedule()
        # Whether the hero is standing still this frame (NES IdleUpdate, see idle_frame), and whether the hero's
        # step ends on it
        self.hero_standing = False
        self.step_ends = False
        # NPCS_MAKE_WAY: the roaming NPC the hero just bumped into, and the hero's direction (see ask_npc_to_make_way)
        self.npc_asked_to_make_way: tuple[RoamingCharacter, int] | None = None
        # Frames left of the pause after a step onto a hill (HILL_PAUSE_FRAMES, see hill_pause_frame)
        self.hill_pause_frames = 0
        # Frames the hero has stood waiting for the NPCs to finish their steps before a pause or the command window
        # (see everyone_on_a_tile)
        self.freeze_wait_frames = 0
        # RUN BUTTON: whether the hero's step under way is a running one, at twice the speed (see move_player)
        self.running_step = False

    # What the controller uses of the Game, read from it each time

    @property
    def config(self) -> dict:
        return self.game.config

    @property
    def game_state(self) -> GameState:
        return self.game.game_state

    @property
    def current_map(self) -> Any:
        return self.game.current_map

    @property
    def player(self) -> Player:
        return self.game.player

    @property
    def camera(self) -> Camera:
        return self.game.camera

    @property
    def tile_size(self) -> int:
        return self.game.tile_size

    @property
    def frame_counter(self) -> int:
        """NES FrameCounter: a held direction only starts a step when it's a multiple of 16 (see move_player), and
        it decides which NPCs move (src/npc_schedule.py)."""
        return self.npc_schedule.frame_counter

    @frame_counter.setter
    def frame_counter(self, value: int) -> None:
        self.npc_schedule.frame_counter = value

    # When nothing moves: windows, the pause and the light growing

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
        return (self.game.paused or self.game.cmd_menu.launch_signaled or self.game.cmd_menu.menu.is_enabled()
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
        return (self.game.pause_requested or self.game.options_requested or self.game.cmd_menu_requested
                or getattr(self.game, 'message_log_requested', False) is True
                or getattr(self.game, 'auto_grind_requested', False) is True
                or getattr(self.game, 'dungeon_map_requested', False) is True
                or getattr(self.game, 'state_request', None) is not None
                or getattr(self.game, 'state_request_due', None) is not None)

    @property
    def sprites_animate(self) -> bool:
        return self.game_state.enable_animate and not self.world_frozen

    def everyone_on_a_tile(self) -> bool:
        """Whether the hero and every roaming NPC are standing exactly on a tile, not partway through a step."""
        if self.player.is_moving:
            return False
        frames_per_step = self.tile_size // self.speed
        if self.freeze_wait_frames > frames_per_step:
            # Every NPC step finishes within this many frames; one that hasn't is stuck (e.g. the hero stepped
            # into the tile it was walking to), so don't wait on it forever.
            return True
        return all(not roaming_character.is_moving or (roaming_character.rect.x % self.tile_size == 0 and
                                                       roaming_character.rect.y % self.tile_size == 0)
                   for roaming_character in self.current_map.roaming_characters)

    def resolve_pending_freezes(self) -> None:
        """
        Pause, open the options overlay (not NES) or open the command window, once the hero and the NPCs have finished
        their steps.
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
        if self.game.pause_requested:
            self.game.pause_requested = False
            self.game.paused = True
            return
        if self.game.options_requested:
            self.game.options_requested = False
            self.game.open_options()
            return
        if getattr(self.game, 'dungeon_map_requested', False) is True:
            self.game.dungeon_map_requested = False
            self.game.open_dungeon_map()
        if getattr(self.game, 'message_log_requested', False) is True:
            self.game.message_log_requested = False
            self.game.open_message_log()
            return
        if getattr(self.game, 'auto_grind_requested', False) is True:
            self.game.auto_grind_requested = False
            self.game.start_auto_grind()
            return
        if getattr(self.game, 'state_request', None) is not None:
            # A save state (Game.handle_save_state_keys): saved or loaded at the end of this map frame (Game.map_frame,
            # or of the next one when the key was read between frames), with nobody starting a step meanwhile
            self.game.state_request_due, self.game.state_request = self.game.state_request, None
            return
        if getattr(self.game, 'state_request_due', None) is not None:
            return
        self.game.cmd_menu_requested = False
        if getattr(self.game, 'smart_a_pending', False) is True:
            # SMART A (Game.handle_a_button): the command that applies here runs instead of the COMMAND window
            self.game.smart_a_pending = False
            if self.game.run_smart_command():
                return
        self.game.drawer.display_hovering_stats = True
        self.game.cmd_menu.launch_signaled = True
        self.game_state.pause_all_movement()

    # The hero's walking

    def handle_player_movement(self) -> None:
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
        self.move_player(with_virtual_keys(key.get_pressed(), MAP_CONTEXT))

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
            # DoJoyUp etc. start with ChkRemovePopUp: any direction press closes the pop-up window, even a tap that
            # only turns the hero
            self.game.drawer.remove_pop_up(self.game.cmd_menu)
            running = self.run_button_held(current_key)
            if self.frame_counter % STEP_SYNC_FRAMES and not (
                    running and self.frame_counter % STEP_SYNC_FRAMES == RUN_STEP_FRAMES and self.run_step_is_clear()):
                self.idle_frame()
                return
            self.player.is_moving = True
            self.running_step = running
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
            self.running_step = False
            self.idle_frame()
            self.ask_npc_to_make_way()
        else:
            # TODO(ELF): sometimes self.tiles_moved_since_spawn gets set to 1 when spawning -
            #  should always be 0 when the map starts.
            self.game.count_step()
            # FrameCounter goes back to 0 once this frame's DoSprites has run (see sprites_frame)
            self.step_ends = True
        self.finish_step(self.player)

    def run_button_held(self, current_key) -> bool:
        """RUN BUTTON (RUN_BUTTON, not NES): with it on, B held while walking makes the step a running one, which moves
        2 NES pixels a frame, so it takes RUN_STEP_FRAMES (8) frames instead of 16. Only the walking is faster: a step
        counts once for the fight roll, the step effects and everything else, and the NPCs and the timers keep their
        own pace, since FrameCounter keeps counting as it does (sprites_frame). B means nothing else on the map."""
        return bool(self.config.get('RUN_BUTTON')) and any(current_key[b_key] for b_key in B_BUTTON_KEYS)

    def run_step_is_clear(self) -> bool:
        """Whether a running step may start half way through FrameCounter's 16 (on its 8th frame): only into a block
        the hero can walk onto, on the map, with no one in it. Anything else (a wall, an NPC, the map's edge or a town
        gate) waits for the next multiple of 16, where the NES's own checks bump or leave the map as walking does, so a
        bump always resets FrameCounter on an NPC turn's last frame, as on the NES."""
        row, column = step(self.player.row, self.player.column, self.player.direction_value)
        layout = self.current_map.layout
        if not (0 <= row < len(layout) and 0 <= column < len(layout[row])) or self.current_map.is_map_exit(row, column):
            return False
        next_tile = self.calculation.get_next_tile_identifier(self.player.column, self.player.row,
                                                              self.player.direction_value, self.current_map)
        return not self.is_impassable(next_tile) and not self.character_in_path(self.player)

    @property
    def hero_speed(self) -> int:
        """Pixels the hero moves a frame: one NES pixel, two on a running step (RUN BUTTON)."""
        return self.speed * RUN_SPEED_FACTOR if self.running_step else self.speed

    def speed_of(self, character: Player | RoamingCharacter) -> int:
        return self.hero_speed if character is self.player else self.speed

    def idle_frame(self) -> None:
        """NES IdleUpdate (Bank03): wait for the next frame, which counts it in FrameCounter (NMI: INC FrameCounter,
        which sprites_frame does on every frame on the map). On the 49th ($31) frame of standing still, the pop-up status
        window is shown and FrameCounter is set to $32, skipping a count, so the steps after a long wait line up a
        frame earlier. FrameCounter is one byte."""
        self.hero_standing = True

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

    def hill_pause_frame(self) -> None:
        """One of the HILL_PAUSE_FRAMES frames NES ChkBlkSand waits after a step onto a hill (three WaitForNMI). Nothing
        moves and nothing animates (no DoSprites), and FrameCounter stays at the 0 the step left it at, as
        JoypadCheckLoop resets it afterwards anyway. The step's fight roll (ChkSandFight) comes after the last one."""
        self.hill_pause_frames -= 1
        if self.hill_pause_frames:
            return
        column, row = self.player.rect.x // self.tile_size, self.player.rect.y // self.tile_size
        self.game.roll_for_fight(column, row, get_tile_id_by_coordinates(column, row, self.current_map))

    # A character's step, pixel by pixel

    def move_laterally(self, character: Player | RoamingCharacter) -> None:
        speed = self.speed_of(character)
        if is_facing_left(character):
            self.move(character, delta_x=-speed, delta_y=0)
        elif is_facing_right(character):
            self.move(character, delta_x=speed, delta_y=0)

    def move_medially(self, character: Player | RoamingCharacter) -> None:
        speed = self.speed_of(character)
        if is_facing_up(character):
            self.move(character, delta_x=0, delta_y=speed)
        elif is_facing_down(character):
            self.move(character, delta_x=0, delta_y=-speed)

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
                self.bump_and_reset(character, character.next_tile_id, character.next_next_tile_id)
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

    @staticmethod
    def finish_step(character: Player | RoamingCharacter) -> None:
        character.is_moving, character.next_tile_checked = False, False
        character.step_origin = character.step_destination = None

    # Collision

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

    def npc_crosses_cover_boundary(self, character: Player | RoamingCharacter) -> bool:
        """NES $B839-$B84F: an NPC can't step into or out of a covered area."""
        next_row, next_column = step(character.row, character.column, character.direction_value)
        return self.current_map.crosses_cover_boundary(character.row, character.column, next_row, next_column)

    def is_impassable(self, tile: str | None) -> bool:
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
        speed = self.hero_speed
        min_bound = 0
        if self.player.rect.x < min_bound:
            self.player.rect.x = min_bound
            self.bump(self.player)
            next_pos_x += -speed
        elif self.player.rect.x > max_x_bound:
            self.player.rect.x = max_x_bound
            self.bump(self.player)
            next_pos_x += speed
        elif self.player.rect.y < min_bound:
            self.player.rect.y = min_bound
            self.bump(self.player)
            next_pos_y -= speed
        elif self.player.rect.y > max_y_bound:
            self.player.rect.y = max_y_bound
            self.bump(self.player)
            next_pos_y += speed
        return next_pos_x, next_pos_y

    def bump_and_reset(self, character, pre_bump_next_tile, pre_bump_next_next_tile):
        if character.next_tile_id != pre_bump_next_tile:
            character.next_tile_id = pre_bump_next_tile
        if character.next_next_tile_id != pre_bump_next_next_tile:
            character.next_next_tile_id = pre_bump_next_next_tile
        self.bump(character)

    def bump(self, character):
        if character.identifier == 'HERO':
            # NES CheckCollision (DirectionBlocked) plays SFX_WALL_BUMP on every blocked step. move_player only
            # tries a step every 16 frames while the hero is held against something, so that's how often it plays.
            if character.current_tile not in ('BRICK_STAIR_UP', 'BRICK_STAIR_DOWN', 'GRASS_STAIR_DOWN'):
                self.sound.play_sound(self.directories.bump_sfx)
        character.bumped = True

    # The NPCs and the walking animation (NES DoSprites)

    def sprites_frame(self) -> None:
        """One frame on the map, after the hero's part: NMI counts it (INC FrameCounter), then NES DoSprites (Bank00)
        moves the walking animation and the roaming NPCs on (src/npc_schedule.py). Like DoSprites, it runs on every
        frame the map is up, whether the hero is walking or standing.
        On the frame the hero has stood still for $31 frames, IdleUpdate (Bank03) opens the pop-up window, whose
        drawing calls DoSprites (WndCalcBufAddr, Bank01), then sets FrameCounter to $32 and calls DoSprites again, so
        that frame has two. The drawer draws the window from then on, until the hero moves."""
        self.npc_schedule.count_frame()
        if self.hero_standing and self.frame_counter == POP_UP_FRAME:
            self.game.drawer.display_hovering_stats = True
            self.update_sprites()
            self.frame_counter = POP_UP_FRAME + 1
        self.hero_standing = False
        self.update_sprites()
        if self.step_ends:
            # NES: DoJoyUp etc. return through ChkSpecialLoc to GameEngineLoop -> JoypadCheckLoop
            self.step_ends = False
            if self.running_step:
                # RUN BUTTON: a running step can end half way through an NPC turn, which goes on: FrameCounter keeps
                # its place in the turn, so only the count of frames stood still (the pop-up window's) starts again
                self.frame_counter %= STEP_SYNC_FRAMES
            else:
                self.frame_counter = 0
            self.running_step = False

    def update_sprites(self) -> None:
        """NES DoSprites: the walking animation and the roaming NPCs."""
        self.npc_schedule.start_sprites()
        if self.game_state.enable_roaming and self.current_map.roaming_characters:
            # NES UpdateNPCs1: no NPC starts a new step once a pause or the command window has been asked for
            self.move_roaming_characters(start_new_steps=not self.freeze_pending)
            self.update_roaming_character_positions()
        # A request to make way is only for the frame right after the bump
        self.npc_asked_to_make_way = None
        self.npc_schedule.end_sprites()

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
        way if nothing is in the way (move checks it)."""
        roaming_character.direction_value = random.choice(list(map(int, Direction)))
        self.begin_npc_step(roaming_character)

    def begin_npc_step(self, roaming_character: RoamingCharacter) -> bool:
        """Take the first pixel of a step the way the NPC faces, if nothing is in the way (move checks it).
        Returns whether the step started."""
        set_character_position(roaming_character, self.tile_size)
        start = roaming_character.rect.copy()
        self.continue_npc_step(roaming_character)
        # A blocked step reserves nothing (move), and the NPC stays where it is
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

    def update_roaming_character_positions(self) -> None:
        for roaming_character in self.current_map.roaming_characters:
            if not roaming_character.is_moving:
                set_character_position(roaming_character, tile_size=self.tile_size)
