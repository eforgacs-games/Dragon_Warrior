"""The party's second hero on the map (co-op, src/party.py): one step behind the first, like a Dragon Quest II party.
Not on the NES.

The first hero leads; the second walks onto the block the first has just left, in step with them: each step the
first hero takes from block A, the second takes from where they stand to A, frame for frame, running steps too (RUN
BUTTON). A bump (a wall, an NPC) moves neither. On a new map (stairs, a door, a warp, a load or a save state) the
second hero starts on the first hero's block, under them, and comes out from under them with the first step.

The second hero blocks the NPCs as the first does (MovementController.character_in_path), but not the first hero,
who can turn back and step onto their block: they swap places, the second taking the first's old block. They're
drawn under the first hero, in their own colors: the first hero's blue (NES $11) is green ($1A) on them
(COMPANION_COLORS), with the sprite sheet for their own weapon and shield.

Nothing here runs without a second hero: ``sync`` takes the second hero off the map if the party has none.
"""
from typing import TYPE_CHECKING, Any

from pygame import PixelArray, Surface
from pygame.sprite import LayeredDirty
from pygame.transform import scale

from src.direction import Direction

from src.maps_functions import get_center_point, parse_animated_sprite_sheet
from src.sprites.animated_sprite import AnimatedSprite

if TYPE_CHECKING:
    from src.game import Game  # src.game imports this module
    from src.player.player import Player

IDENTIFIER = 'HERO_2'
LEADER = 'HERO'
# The hero's sprites' blue (NES $11), and what it is on the second hero (NES $1A)
HERO_BLUE = (32, 56, 236)
COMPANION_GREEN = (0, 168, 0)
COMPANION_COLORS = {HERO_BLUE: COMPANION_GREEN}

Cell = tuple[int, int]


def recolored(sheet: Surface, colors: dict[tuple[int, int, int], tuple[int, int, int]]) -> Surface:
    """A copy of the sprite sheet with each of ``colors``' keys drawn in its value."""
    copy = sheet.copy()
    pixels = PixelArray(copy)
    for old, new in colors.items():
        pixels.replace(old, new)
    del pixels  # unlocks the surface
    return copy


def direction_between(origin: Cell, destination: Cell) -> int | None:
    """The direction of a step from one block to the next one, None if they aren't next to each other."""
    rows, columns = destination[0] - origin[0], destination[1] - origin[1]
    return {(-1, 0): Direction.UP.value, (1, 0): Direction.DOWN.value, (0, -1): Direction.LEFT.value,
            (0, 1): Direction.RIGHT.value}.get((rows, columns))


class Follower:
    """The second hero's place on the map (see the module docstring)."""

    def __init__(self, game: 'Game') -> None:
        self.game = game
        self._sheets: dict[str, Any] = {}
        # The step under way, (from, to), while the first hero takes one
        self.step: tuple[Cell, Cell] | None = None

    @property
    def companion(self) -> 'Player | None':
        return self.game.companion

    @property
    def tile_size(self) -> int:
        return self.game.tile_size

    def on_map(self) -> 'Player | None':
        """The second hero, if they're on the map now."""
        entry = self.game.current_map.characters.get(IDENTIFIER)
        return entry['character'] if entry is not None else None

    def sync(self) -> None:
        """Put the second hero on the map, on the first hero's block, if they aren't on it yet (a new map, a new
        party, a loaded game or state); take them off if the party has no second hero."""
        characters = self.game.current_map.characters
        companion = self.companion
        if companion is None:
            characters.pop(IDENTIFIER, None)
            self.step = None
            return
        entry = characters.get(IDENTIFIER)
        if entry is not None and entry['character'] is companion:
            return
        leader = self.game.player
        self.step = None
        # As DragonWarriorMap.load_map makes the first hero a sprite on the map
        AnimatedSprite.__init__(companion, get_center_point(leader.column, leader.row, tile_size=self.tile_size),
                                leader.direction_value, self.sheet(), IDENTIFIER)
        companion.show_facing()
        self.stand_on(leader.row, leader.column)
        # Drawn before the first hero, so under them when they share a block
        leader_entry = characters.pop(LEADER, None)
        characters[IDENTIFIER] = {'character': companion, 'character_sprites': LayeredDirty(companion),
                                  'tile_value': None, 'coordinates': (leader.row, leader.column)}
        if leader_entry is not None:
            characters[LEADER] = leader_entry

    def stand_on(self, row: int, column: int) -> None:
        companion = self.companion
        assert companion is not None
        companion.row, companion.column = row, column
        companion.step_origin = companion.step_destination = None
        companion.is_moving = False
        companion.rect.topleft = (column * self.tile_size, row * self.tile_size)
        entry = self.game.current_map.characters.get(IDENTIFIER)
        if entry is not None:
            entry['coordinates'] = (row, column)

    def frame(self) -> None:
        """One map frame, after the first hero's: follow their step (see the module docstring)."""
        self.sync()
        companion = self.companion
        if companion is None:
            return
        leader = self.game.player
        if leader.step_origin is not None and leader.step_destination is not None:
            if self.step is None:
                self.start_step(companion, tuple(leader.step_origin))
            if self.step is not None:
                self.move_with(companion, leader)
        elif self.step is not None:
            self.stand_on(*self.step[1])
            self.step = None

    def start_step(self, companion: 'Player', leader_origin: Cell) -> None:
        here = (companion.row, companion.column)
        if here == leader_origin:
            return  # still under the first hero: they come out from under them on the next step
        direction = direction_between(here, leader_origin)
        if direction is None:
            # Not next to the first hero's block (it can't happen while walking): catch up at once
            self.stand_on(*leader_origin)
            return
        companion.direction_value = direction
        companion.is_moving = True
        companion.step_origin, companion.step_destination = here, leader_origin
        self.step = (here, leader_origin)

    def move_with(self, companion: 'Player', leader: 'Player') -> None:
        """Put the second hero as far along their step as the first hero is along theirs."""
        assert self.step is not None and leader.step_origin is not None
        tile = self.tile_size
        origin_row, origin_column = leader.step_origin
        moved = abs(leader.rect.x - origin_column * tile) + abs(leader.rect.y - origin_row * tile)
        (from_row, from_column), (to_row, to_column) = self.step
        moved = min(moved, tile)
        companion.rect.x = from_column * tile + (to_column - from_column) * moved
        companion.rect.y = from_row * tile + (to_row - from_row) * moved

    def update_images(self) -> None:
        """Show the sprite sheet for the second hero's weapon and shield (each frame, as the first hero's:
        Game.set_player_images_by_equipment)."""
        companion = self.on_map()
        if companion is not None:
            sheet = self.sheet()
            if companion.images_map.get(Direction.DOWN.value) is not sheet[0]:
                companion.set_images(sheet)
                companion.show_facing()

    def sheet(self) -> Any:
        """The sprite sheet for the second hero's weapon and shield, in their colors."""
        companion = self.companion
        assert companion is not None
        directories = self.game.directories
        if companion.weapon:
            path = directories.ARMED_HERO_WITH_SHIELD_PATH if companion.shield else directories.ARMED_HERO_PATH
        else:
            path = directories.UNARMED_HERO_WITH_SHIELD_PATH if companion.shield else directories.UNARMED_HERO_PATH
        if path not in self._sheets:
            current_map = self.game.current_map
            sheet = current_map.graphics.get_image(path)
            sheet = scale(sheet, (sheet.get_width() * current_map.scale, sheet.get_height() * current_map.scale))
            self._sheets[path] = parse_animated_sprite_sheet(recolored(sheet, COMPANION_COLORS), self.game.config)
        return self._sheets[path]

    def cells(self) -> list[Cell]:
        """The blocks the second hero holds: where they stand, and their step's two blocks."""
        companion = self.on_map()
        if companion is None:
            return []
        return [(companion.row, companion.column), *(cell for cell in (companion.step_origin,
                                                                         companion.step_destination) if cell)]
