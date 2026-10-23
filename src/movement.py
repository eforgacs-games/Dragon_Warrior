"""MovementController: the hero's and the NPCs' movement on the map, which used to live on Game.

Game runs the main loop and the frame pipeline (Game.map_frame) and calls this for each frame's movement. The
controller holds a reference to the game (MovementGame) and reads what it shares with the rest of the game (the
player, the map, the camera) from it each time, since the game replaces some of them (a map change makes a new map).
Where an NPC may step, as far as the map goes, is src/npc_movement.py; when the NPCs move is src/npc_schedule.py.
"""
from typing import TYPE_CHECKING, Any, Protocol

from src.calculation import Calculation
from src.directories import Directories
from src.game_state import GameState
from src.sound import Sound

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


class MovementController:
    """The hero's and the NPCs' movement, frame by frame. Game.map_frame calls it once a frame."""

    def __init__(self, game: MovementGame):
        self.game = game
        self.sound = Sound(game.config)
        self.calculation = Calculation(game.config)
        self.directories = Directories(game.config)

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
