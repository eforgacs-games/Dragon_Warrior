"""Auto-grind's way to an inn and back (AUTO-INN, src/auto_grind.py): the shortest walk across maps. Not NES.

A route is a walk over (map, cell) places, found with Dijkstra's algorithm from the hero to the nearest goal:

- in a map, a step to any of the four neighbours the hero can walk onto: not impassable, no fixed NPC, no guardian
  (src/guardians.py) waiting there. Swamps and force fields cost more (they hurt), and hills too (the hero pauses);
- a map is left only where the route means to: a step onto a town, cave or castle, or off a town's edge
  (DragonWarriorMap.is_step_warp), or onto stairs, which are then taken with the STAIRS command. Any other such place
  is avoided, so the hero never changes maps by accident (STAIRS set to STEP ON takes stairs by stepping onto them);
- the place the exit leads to is its stairs entry's destination (DragonWarriorMap.staircases), where the hero starts on
  the next map.

The goals are where the hero can talk to an innkeeper whose night he can pay for (``inn_goals``: next to him, or across
the counter, facing him), or the tile auto-grind started on (the way back). Roaming NPCs aren't on the map the route is
planned on: the hero waits for them, or a new route goes round them (``blocked``).

Maps are only loaded as the search reaches them, and kept (``RouteMaps``); the layouts are the game's own
(Game.layouts), with the rainbow bridge and the opened doors in them.
"""
import heapq
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, cast

from src.coordinates import Cell
from src.guardians import guardian_at
from src import map_layouts
from src.maps import all_impassable_tiles, map_lookup
from src.menu_functions import get_opposite_direction
from src.npc_movement import step
from src.npcs import NPC
from src.shops import INN_COSTS
from src.story_flags import StoryFlags

if TYPE_CHECKING:
    from src.maps import DragonWarriorMap

# The cost of a step onto each kind of tile (1 for the rest), and of changing maps
TILE_COSTS = {'HILLS': 2, 'MARSH': 8, 'BARRIER': 30}
MAP_CHANGE_COST = 4
# The NES dialog byte of each town's innkeeper (DialogLookup's InnDialog entries)
INNKEEPER_DIALOG = {'Kol': 0x11, 'Brecconary': 0x12, 'Garinham': 0x13, 'Cantlin': 0x14, 'Rimuldar': 0x15}
DIRECTIONS = range(4)
# The floor tiles' names by their value in a layout (src/map_layouts.py ROOF = 0 ... TOP_LEFT_RIGHT_COAST = 35)
TILE_NAMES = tuple(name for name, value in sorted(
    ((name, value) for name, value in vars(map_layouts).items() if name.isupper() and isinstance(value, int)),
    key=lambda item: item[1]))

Place = tuple[str, Cell]  # (map identifier, (row, column))


class Exit(Enum):
    WALK = 'walk'  # a step onto it changes maps
    STAIRS = 'stairs'  # the STAIRS command on it changes maps


@dataclass(frozen=True, slots=True)
class Goal:
    place: Place
    facing: int | None = None  # the direction to face there (an innkeeper), or None
    town: str | None = None  # the inn's town


@dataclass
class Leg:
    """The part of a route on the map the hero is on: the cells to walk through (the first is where he stands), and
    what the last one is: an exit (and how it's taken) or the goal."""
    cells: list[Cell]
    exit: Exit | None = None
    goal: Goal | None = None


class RouteMaps:
    """The maps a search reaches, loaded once (map_lookup), with the game's live layouts and the map the hero is on."""

    def __init__(self, game: Any) -> None:
        self.game = game
        self.loaded: dict[str, DragonWarriorMap] = {}

    def get(self, identifier: str) -> 'DragonWarriorMap':
        current_map = self.game.current_map
        if identifier == current_map.identifier:
            return current_map
        if identifier not in self.loaded:
            self.loaded[identifier] = map_lookup[identifier](self.game.config)
        loaded = self.loaded[identifier]
        loaded.layout = self.game.layouts.map_layout_lookup[identifier]
        return loaded

    def layout(self, identifier: str) -> list[list[int]]:
        if identifier == self.game.current_map.identifier:
            return self.game.current_map.layout
        return self.game.layouts.map_layout_lookup[identifier]

    def tile(self, identifier: str, cell: Cell) -> str | None:
        """The tile's name, without loading the map (the layouts only hold floor tiles, TILE_NAMES)."""
        layout = self.layout(identifier)
        row, column = cell
        if not (0 <= row < len(layout) and 0 <= column < len(layout[0])):
            return None
        return TILE_NAMES[layout[row][column]]

    def fixed_npc_cells(self, identifier: str) -> set[Cell]:
        current_map = self.game.current_map
        if identifier == current_map.identifier:
            return {(character.row, character.column) for character in current_map.fixed_characters}
        return {npc_cell(identifier, npc) for npc in map_class(identifier).npc_table if not npc.mobile}


def map_class(identifier: str) -> 'type[DragonWarriorMap]':
    return cast('type[DragonWarriorMap]', map_lookup[identifier])


def npc_cell(identifier: str, npc: NPC) -> Cell:
    """An NPC's layout (row, column), from its map's class (DragonWarriorMap.npc_position), without loading the map."""
    origin = map_class(identifier).nes_origin
    assert origin is not None
    return npc.y + origin[0], npc.x + origin[1]


def exit_kind(current_map: 'DragonWarriorMap', cell: Cell) -> Exit | None:
    """How this cell leaves the map, if it does and the stairs entries say where to."""
    if cell not in current_map.staircases or 'destination_coordinates' not in current_map.staircases[cell]:
        return None
    return Exit.WALK if current_map.is_step_warp(*cell) else Exit.STAIRS


def inn_goals(maps: RouteMaps, gold: int) -> list[Goal]:
    """Where the hero can talk to each innkeeper whose night he can pay for, and the way to face."""
    goals = []
    for town, dialog in INNKEEPER_DIALOG.items():
        if gold < INN_COSTS[town]:
            continue
        innkeeper = next(npc for npc in map_class(town).npc_table if npc.dialog == dialog)
        innkeeper_cell = npc_cell(town, innkeeper)
        for facing in DIRECTIONS:
            back = get_opposite_direction(facing)
            next_to = step(*innkeeper_cell, back)
            # CommandMenu.talk: the NPC in front of the hero, or across a counter (WOOD) from him
            spots = [next_to] + ([step(*next_to, back)] if maps.tile(town, next_to) == 'WOOD' else [])
            for spot in spots:
                tile = maps.tile(town, spot)
                if tile is not None and tile not in all_impassable_tiles:
                    goals.append(Goal((town, spot), facing, town))
    return goals


Route = list[tuple[Place, Exit | None]]


def find_route(maps: RouteMaps, start: Place, goals: Iterable[Goal], story_flags: StoryFlags,
               blocked: Iterable[Cell] = ()) -> Route | None:
    """The cheapest walk from start to any goal (see the module docstring): each place in order, with how it is left
    when that changes maps (the next place is then on the next map). None if no goal can be reached. ``blocked``:
    cells of the start's map to keep off (roaming NPCs in the way)."""
    goal_places = {goal.place for goal in goals}
    if not goal_places:
        return None
    start_map = start[0]
    blocked_cells = set(blocked)
    best: dict[Place, int] = {start: 0}
    # How each place was reached: the place before, and the exit cell and its kind if it's on the next map
    came_from: dict[Place, tuple[Place, Cell | None, Exit | None]] = {}
    queue: list[tuple[int, int, Place]] = [(0, 0, start)]
    order = 0
    fixed_cells: dict[str, set[Cell]] = {}
    while queue:
        cost_so_far, _order, place = heapq.heappop(queue)
        if cost_so_far > best[place]:
            continue
        if place in goal_places:
            return _walk_back(came_from, place)
        identifier, cell = place
        current_map = maps.get(identifier)
        if identifier not in fixed_cells:
            fixed_cells[identifier] = maps.fixed_npc_cells(identifier)
        for direction in DIRECTIONS:
            neighbour = step(*cell, direction)
            tile = maps.tile(identifier, neighbour)
            if tile is None or tile in all_impassable_tiles:
                continue
            if neighbour in fixed_cells[identifier] or (identifier == start_map and neighbour in blocked_cells):
                continue
            if guardian_at(identifier, neighbour, story_flags) is not None:
                continue
            cost = cost_so_far + TILE_COSTS.get(tile, 1)
            reached: Place = (identifier, neighbour)
            exit_cell, kind = None, None
            if reached not in goal_places and (current_map.is_step_warp(*neighbour) or
                                               neighbour in current_map.staircases):
                kind = exit_kind(current_map, neighbour)
                if kind is None:
                    continue  # a way off the map that leads nowhere known
                destination = current_map.staircases[neighbour]
                exit_cell, cost = neighbour, cost + MAP_CHANGE_COST
                reached = (destination['map'], tuple(destination['destination_coordinates']))
            if cost < best.get(reached, cost + 1):
                best[reached] = cost
                came_from[reached] = (place, exit_cell, kind)
                order += 1
                heapq.heappush(queue, (cost, order, reached))
    return None


def _walk_back(came_from: dict[Place, tuple[Place, Cell | None, Exit | None]], place: Place) -> Route:
    route: Route = [(place, None)]
    while place in came_from:
        previous, exit_cell, kind = came_from[place]
        if exit_cell is not None:
            route.append(((previous[0], exit_cell), kind))
        route.append((previous, None))
        place = previous
    route.reverse()
    return route


def first_leg(route: Route, goals: Iterable[Goal]) -> Leg:
    """The part of a route on its first map (see Leg)."""
    identifier = route[0][0][0]
    cells = []
    for (place_map, cell), how in route:
        if place_map != identifier:
            break
        cells.append(cell)
        if how is not None:
            return Leg(cells, exit=how)
    last = (identifier, cells[-1])
    return Leg(cells, goal=next((goal for goal in goals if goal.place == last), None))
