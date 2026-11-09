"""Game events: what has just happened in the game, announced on the Game's EventBus (``game.event_bus``) for whatever
wants to know. Not on the NES.

Each event is announced in one place, where it happens, and says what happened, not who will be told: the play
statistics (src/play_stats.py subscribe_play_stats) are counted from them, and achievements (#425) and multiplayer
(#438) are to be built on them too. Every event carries ``hero``, which hero it happened to: always HERO (0) for now,
with room for a second one.

The events, and where each is announced:

- StepTaken: StepTriggers.count_step (src/step_triggers.py), every step that ends on a new block;
- FightWon, FightLost, RanAway: BattleController.fight_enemy (src/battle_controller.py), as a fight ends. FightWon names
  the enemy; the Dragonlord's two forms are one fight, won as 'Dragonlord 2'. RanAway is the hero running away, not an
  enemy that does;
- LevelUp: Battle.check_player_level_up (src/battle.py, NES DoLevelUp), with the new level, which may be more than one
  above the old one;
- HeroDied: HeroDeath.handle_death (src/hero_death.py), in a fight or on the map;
- GoldEarned: a won fight's gold (Battle.enemy_defeated), a treasure chest's (CommandMenu.take_gold) and what shops pay
  for what the hero sells or trades in (data/text/dialog_lookup_table.py); GoldSpent: what shops and inns are paid;
- ChestOpened: CommandMenu.open_chest (src/menu.py, NES GetTreasure), every chest taken, an empty one too.

Handlers run at once, in the order they subscribed, those for the event's own type before those for a type it's a kind
of (a handler for GameEvent hears every event). One that raises doesn't stop the others: its traceback is printed (so
a crash log's recent output has it, src/crash_log.py) and the game goes on.
"""
import sys
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

HERO = 0  # the one hero there is so far

E = TypeVar('E', bound='GameEvent')


@dataclass(frozen=True, slots=True)
class GameEvent:
    """Something that has just happened in the game, to ``hero``."""
    hero: int = field(default=HERO, kw_only=True)


@dataclass(frozen=True, slots=True)
class StepTaken(GameEvent):
    pass


@dataclass(frozen=True, slots=True)
class FightWon(GameEvent):
    enemy_name: str


@dataclass(frozen=True, slots=True)
class FightLost(GameEvent):
    pass


@dataclass(frozen=True, slots=True)
class RanAway(GameEvent):
    pass


@dataclass(frozen=True, slots=True)
class LevelUp(GameEvent):
    level: int


@dataclass(frozen=True, slots=True)
class HeroDied(GameEvent):
    pass


@dataclass(frozen=True, slots=True)
class GoldEarned(GameEvent):
    amount: int


@dataclass(frozen=True, slots=True)
class GoldSpent(GameEvent):
    amount: int


@dataclass(frozen=True, slots=True)
class ChestOpened(GameEvent):
    pass


class EventBus:
    """Who is told of each kind of event (see the module docstring)."""

    def __init__(self) -> None:
        self._handlers: dict[type[GameEvent], list[Callable[[Any], None]]] = {}

    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None:
        """Stop telling ``handler`` of ``event_type``; nothing happens if it wasn't subscribed."""
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def emit(self, event: GameEvent) -> None:
        """Tell every handler of the event's type, and of each type it's a kind of, of ``event``."""
        for event_type in type(event).__mro__:
            # A copy: a handler may subscribe or unsubscribe as it runs
            for handler in list(self._handlers.get(event_type, ())):
                try:
                    handler(event)
                except Exception:  # noqa: BLE001 - one handler's bug mustn't stop the others or the game
                    print(f"Error in a handler of {type(event).__name__}:", file=sys.stderr)
                    traceback.print_exc()
