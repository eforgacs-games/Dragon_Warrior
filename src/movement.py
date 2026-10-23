"""MovementController: the hero's and the NPCs' movement on the map, which used to live on Game.

Game runs the main loop and the frame pipeline (Game.map_frame) and calls this for each frame's movement. The
controller holds a reference to the game (MovementGame) and reads what it shares with the rest of the game (the
player, the map, the camera) from it each time, since the game replaces some of them (a map change makes a new map).
Where an NPC may step, as far as the map goes, is src/npc_movement.py; when the NPCs move is src/npc_schedule.py.
"""
import random
from typing import Any, Protocol

from pygame import K_DOWN, K_LEFT, K_RIGHT, K_UP, K_a, K_d, K_s, K_w, key

from src.calculation import Calculation
from src.camera import Camera
from src.common import is_facing_down, is_facing_laterally, is_facing_left, is_facing_medially, is_facing_right, \
    is_facing_up
from src.direction import Direction
from src.directories import Directories
from src.game_functions import set_character_position
from src.game_state import GameState
from src.npc_movement import npc_may_step_onto, step
from src.npc_schedule import NPCSchedule, POP_UP_FRAME
from src.player.player import Player
from src.sound import Sound
from src.sprites.roaming_character import RoamingCharacter


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
    freeze_pending: bool

    world_frozen: bool

    def count_step(self) -> None: ...

    def check_next_tile(self, character) -> None: ...

    def character_in_path(self, character) -> bool: ...

    def npc_crosses_cover_boundary(self, character) -> bool: ...

    def is_impassable(self, tile) -> bool: ...

    def move_and_handle_sides_collision(self, next_pos_x: int, next_pos_y: int) -> tuple: ...


class MovementController:
    """The hero's and the NPCs' movement, frame by frame. Game.map_frame calls it once a frame."""

    def __init__(self, game: MovementGame):
        self.game = game
        self.sound = Sound(game.config)
        self.calculation = Calculation(game.config)
        self.directories = Directories(game.config)
        # Pixels the hero and the NPCs move a frame: one NES pixel (TILE_SIZE is 16 * SCALE), so a step takes
        # STEP_SYNC_FRAMES (16) frames at any SCALE, like the NES
        self.speed = game.config["TILE_SIZE"] // 16
        # NES FrameCounter, NPCUpdateCntr and CharLeftRight (src/npc_schedule.py): when the hero may start a step, which
        # NPCs may move on each frame, and the walking frame
        self.npc_schedule = NPCSchedule()
        # Whether this frame is an IdleUpdate frame (the hero standing, see idle_frame), and whether the hero's step
        # ends on it
        self.idle_update = False
        self.step_ends = False
        # NPCS_MAKE_WAY: the roaming NPC the hero just bumped into, and the hero's direction (see ask_npc_to_make_way)
        self.npc_asked_to_make_way: tuple[RoamingCharacter, int] | None = None

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

    def handle_player_movement(self) -> None:
        """
        Checks if the game is paused or if movement is disabled; if not,
        moves the player based on the current key state.
        """
        if self.game.world_frozen:
            # NES: every command, the pause and the windows they open end with JMP JoypadCheckLoop, which resets
            # FrameCounter, so a direction held as they close starts a step at once. They open between NPC turns
            # (resolve_pending_freezes), when FrameCounter & $0F is 0 already, so the NPCs carry on where they were.
            self.frame_counter = 0
            return
        if not self.game_state.enable_movement:
            return
        if self.game.freeze_pending and not self.player.is_moving:
            # NES GameEngineLoop only reads START and A between steps (DoJoyUp etc. move a whole tile before
            # returning), so a step already under way is finished, but no new one is started. PausePrepLoop and
            # DoNCCmdWindow keep counting frames until the end of the NPCs' turn.
            return
        self.move_player(key.get_pressed())

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
            self.game.count_step()
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
        self.game.check_next_tile(character)
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
                blocked = self.game.is_impassable(character.next_tile_id)
            if blocked or self.game.character_in_path(character) or (
                    character is not self.player and self.game.npc_crosses_cover_boundary(character)):
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
            self.camera.pos = self.game.move_and_handle_sides_collision(next_cam_pos_x, next_cam_pos_y)

    @staticmethod
    def finish_step(character: Player | RoamingCharacter) -> None:
        character.is_moving, character.next_tile_checked = False, False
        character.step_origin = character.step_destination = None

    def do_sprites(self) -> None:
        """One frame on the map, after the hero's part: NMI counts it (INC FrameCounter), then NES DoSprites (Bank00)
        moves the walking animation and the roaming NPCs on (src/npc_schedule.py). Like DoSprites, it runs on every
        frame the map is up, whether the hero is walking or standing.
        On the frame the hero has stood still for $31 frames, IdleUpdate (Bank03) opens the pop-up window, whose
        drawing calls DoSprites (WndCalcBufAddr, Bank01), then sets FrameCounter to $32 and calls DoSprites again, so
        that frame has two. The drawer draws the window from then on, until the hero moves."""
        self.npc_schedule.count_frame()
        if self.idle_update and self.frame_counter == POP_UP_FRAME:
            self.game.drawer.display_hovering_stats = True
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
            self.move_roaming_characters(start_new_steps=not self.game.freeze_pending)
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

    def update_roaming_character_positions(self) -> None:
        for roaming_character in self.current_map.roaming_characters:
            if not roaming_character.is_moving:
                set_character_position(roaming_character, tile_size=self.tile_size)

    def bump_and_reset(self, character, pre_bump_next_tile, pre_bump_next_next_tile):
        if character.next_tile_id != pre_bump_next_tile:
            character.next_tile_id = pre_bump_next_tile
        if character.next_next_tile_id != pre_bump_next_next_tile:
            character.next_next_tile_id = pre_bump_next_next_tile
        self.bump(character)

    def bump(self, character):
        if character.identifier == 'HERO':
            # NES CheckCollision (DirectionBlocked) plays SFX_WALL_BUMP on every blocked step. Game.move_player only
            # tries a step every 16 frames while the hero is held against something, so that's how often it plays.
            if character.current_tile not in ('BRICK_STAIR_UP', 'BRICK_STAIR_DOWN', 'GRASS_STAIR_DOWN'):
                self.sound.play_sound(self.directories.bump_sfx)
        character.bumped = True
