"""MovementController: the hero's and the NPCs' movement on the map, which used to live on Game.

Game runs the main loop and the frame pipeline (Game.map_frame) and calls this for each frame's movement. The
controller holds a reference to the game (MovementGame) and reads what it shares with the rest of the game (the
player, the map, the camera) from it each time, since the game replaces some of them (a map change makes a new map).
Where an NPC may step, as far as the map goes, is src/npc_movement.py; when the NPCs move is src/npc_schedule.py.
"""
import random
from typing import TYPE_CHECKING, Any, Protocol

from src.calculation import Calculation
from src.common import is_facing_medially
from src.direction import Direction
from src.directories import Directories
from src.game_functions import set_character_position
from src.game_state import GameState
from src.npc_schedule import NPCSchedule, POP_UP_FRAME
from src.sound import Sound
from src.sprites.roaming_character import RoamingCharacter

if TYPE_CHECKING:
    from src.camera import Camera
    from src.player.player import Player


class MovementGame(Protocol):
    """What MovementController uses of the Game. It reads them from the Game each time, since the Game replaces some
    of them (a map change makes a new map and a new CommandMenu)."""
    config: dict
    game_state: GameState
    current_map: Any
    player: 'Player'
    camera: 'Camera'
    tile_size: int
    drawer: Any
    freeze_pending: bool

    def move_medially(self, character) -> None: ...

    def move_laterally(self, character) -> None: ...

    def finish_step(self, character) -> None: ...


class MovementController:
    """The hero's and the NPCs' movement, frame by frame. Game.map_frame calls it once a frame."""

    def __init__(self, game: MovementGame):
        self.game = game
        self.sound = Sound(game.config)
        self.calculation = Calculation(game.config)
        self.directories = Directories(game.config)
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
    def player(self) -> 'Player':
        return self.game.player

    @property
    def camera(self) -> 'Camera':
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
            self.game.move_medially(roaming_character)
            arrived = roaming_character.rect.y % self.tile_size == 0
        else:
            self.game.move_laterally(roaming_character)
            arrived = roaming_character.rect.x % self.tile_size == 0
        if arrived and roaming_character.step_destination is not None:
            self.game.finish_step(roaming_character)
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
