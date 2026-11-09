"""AUTO-INN: auto-grind's trip to the nearest inn it can pay for, a night there, and the walk back. Not NES.

AutoGrind (src/auto_grind.py) starts a trip (``InnTrip``) on the map when it can't go on: HP low with no heal to cast,
or, with AUTO-HEAL on, no MP left for a heal (with KEEP 1 HEAL, the HEAL kept is for this walk). The trip then drives
the hero on the map in its place, with the same virtual joypad:

- it walks the route (src/grind_route.py) a step at a time, holding the direction to the next cell; a new route is
  worked out on every map it arrives on, and when a roaming NPC has stood in the way for STUCK_FRAMES frames (round
  them, ``blocked``);
- stairs on the way are taken with the STAIRS command (A, STAIRS in the COMMAND window, A);
- at the inn it faces the innkeeper, across the counter, and TALKs: auto-grind's A taps answer YES (the YES/NO window's
  cursor starts on YES), and move the night's lines on. Gold spent means the night was had (DialogLookup.inn_sleep);
- it then walks back to the tile auto-grind started on, and auto-grind paces again from there.

Fights on the way are auto-grind's as ever (FIGHT, heals, the stops). HP low with no heal on a map with random fights
stops it; in a town there are none, so it walks on. No route (no inn it can pay for or get to, or no way back) stops
it too.
"""
from enum import Enum
from typing import TYPE_CHECKING

from src.coordinates import Cell
from src.grind_route import Exit, Goal, Leg, RouteMaps, find_route, first_leg, inn_goals
from src.menu import COMMAND_METHODS
from src.windows import COMMAND_ROWS

if TYPE_CHECKING:
    from src.auto_grind import AutoGrind
    from src.virtual_joypad import VirtualJoypad

# How long the hero may stand still while walking (a roaming NPC in the way) before the route goes round
STUCK_FRAMES = 90
# How many times in a row a command (TALK, STAIRS) or a new route may come to nothing before the trip gives up
ATTEMPTS = 4
COMMAND_TALK = COMMAND_METHODS.index('talk')
COMMAND_STAIRS = COMMAND_METHODS.index('stairs')


class Phase(Enum):
    TO_INN = 'to the inn'
    HOME = 'back to grinding'


class TripResult(Enum):
    WALKING = 'walking'
    HOME = 'home'  # back on the tile auto-grind started on
    NO_INN = 'no inn'  # no inn it can pay for and get to
    LOST = 'lost'  # no way back, or a command that does nothing


class InnTrip:
    """One trip (see the module docstring)."""

    def __init__(self, grind: 'AutoGrind', home: tuple[str, Cell], maps: RouteMaps) -> None:
        self.grind = grind
        self.game = grind.game
        self.home = home
        self.maps = maps
        self.phase = Phase.TO_INN
        self.goals: list[Goal] = []
        self.leg: Leg | None = None
        self.leg_map: str | None = None
        self.blocked: set[Cell] = set()
        # The COMMAND window entry being chosen (TALK, STAIRS), whether A has chosen it, and what to check after it
        self.command: int | None = None
        self.command_chosen = False
        self.gold_before = 0
        self.attempts = 0
        self.last_cell: Cell | None = None
        self.still_since = 0

    def plan(self) -> bool:
        """A new route from where the hero stands. Returns whether there is one."""
        game = self.game
        if self.phase == Phase.TO_INN:
            self.goals = inn_goals(self.maps, game.player.gold)
        else:
            self.goals = [Goal(self.home)]
        start = (game.current_map.identifier, self.grind.hero_cell())
        route = find_route(self.maps, start, self.goals, game.story_flags, self.blocked)
        self.leg = first_leg(route, self.goals) if route is not None else None
        self.leg_map = game.current_map.identifier
        return self.leg is not None

    def drive(self, joypad: 'VirtualJoypad') -> TripResult:
        """One poll of the map (AutoGrind.walk), with no heal to cast: the next key."""
        grind, game = self.grind, self.game
        if self.command is not None:
            return self.run_command(joypad)
        if game.player.is_moving:
            return TripResult.WALKING
        cell = grind.hero_cell()
        if self.leg is None or self.leg_map != game.current_map.identifier or cell not in self.leg.cells:
            self.blocked.clear()
            if not self.plan():
                return TripResult.NO_INN if self.phase == Phase.TO_INN else TripResult.LOST
        assert self.leg is not None
        cells = self.leg.cells
        index = cells.index(cell)
        if index == len(cells) - 1:
            return self.arrive(joypad)
        next_cell = cells[index + 1]
        if cell != self.last_cell:
            self.last_cell, self.still_since = cell, joypad.now
        elif joypad.now - self.still_since > STUCK_FRAMES:
            return self.go_round(joypad)
        direction = grind.direction_between(cell, next_cell)
        assert direction is not None
        grind.hold_direction(joypad, direction)
        return TripResult.WALKING

    def go_round(self, joypad: 'VirtualJoypad') -> TripResult:
        """Someone has stood in the way too long: a route round the roaming NPCs, where they stand now."""
        self.attempts += 1
        if self.attempts > ATTEMPTS:
            return TripResult.LOST
        current_map = self.game.current_map
        self.blocked = {cell for character in current_map.roaming_characters
                        for cell in ((character.row, character.column), character.step_destination) if cell}
        self.still_since = joypad.now
        if not self.plan():
            self.blocked.clear()  # no way round: wait for them on the old route
            self.plan()
        return TripResult.WALKING

    def arrive(self, joypad: 'VirtualJoypad') -> TripResult:
        """At the end of the leg: take the stairs, talk to the innkeeper, or be home."""
        grind = self.grind
        assert self.leg is not None
        goal = self.leg.goal
        if self.leg.exit is None and self.phase == Phase.TO_INN and goal is not None and goal.facing is not None \
                and self.game.player.direction_value != goal.facing:
            # Turn to the innkeeper: held until the hero faces him (the counter, or the innkeeper, is in the way, so it
            # only turns him). A tap could be let go before the walking reads it.
            grind.hold_direction(joypad, goal.facing)
            return TripResult.WALKING
        joypad.release_all(grind.direction_keys_held(joypad))
        if self.leg.exit == Exit.STAIRS:
            self.start_command(COMMAND_STAIRS)
        elif self.leg.exit == Exit.WALK:
            return TripResult.WALKING  # the map changes as the step ends
        elif self.phase == Phase.HOME:
            return TripResult.HOME
        else:
            self.gold_before = self.game.player.gold
            self.start_command(COMMAND_TALK)
        return TripResult.WALKING

    def start_command(self, entry: int) -> None:
        self.command, self.command_chosen = entry, False

    def run_command(self, joypad: 'VirtualJoypad') -> TripResult:
        """Choose the COMMAND window entry (A to open it, the cursor to the entry, A), then see what it did once the
        window has closed."""
        grind, game, cmd_menu = self.grind, self.game, self.game.cmd_menu
        window = cmd_menu.menu
        opening = game.cmd_menu_requested or cmd_menu.launch_signaled
        command = self.command
        assert command is not None
        if window.is_enabled():
            target = (command % COMMAND_ROWS, command // COMMAND_ROWS)
            key = grind.cursor_key((window.row, window.column), target)
            if (window.row, window.column) == target:
                self.command_chosen = True
            grind.tap(joypad, key)
            return TripResult.WALKING
        if opening:
            return TripResult.WALKING
        moved_on = self.leg_map != game.current_map.identifier
        stayed = command == COMMAND_TALK and game.player.gold < self.gold_before
        if moved_on or stayed:
            # Down the stairs, or a night at the inn: the next leg
            self.command, self.attempts, self.leg = None, 0, None
            if stayed:
                self.phase = Phase.HOME
                grind.show(game._("Auto-grind: back to grinding"))
            return TripResult.WALKING
        if self.command_chosen:
            # Chosen, and nothing came of it ("There is no one there.", not enough gold): again, a few times
            self.command_chosen = False
            self.attempts += 1
            if self.attempts > ATTEMPTS:
                return TripResult.LOST
        grind.tap(joypad, grind.a_key())  # open the COMMAND window (or SMART A's TALK or STAIRS)
        return TripResult.WALKING
