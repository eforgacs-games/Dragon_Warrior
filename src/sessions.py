"""Hero sessions: what the game holds for each hero playing on their own (free roam co-op, #438). Not NES.

The game is one world (the maps' layouts, the story, the chests, the play statistics, the random numbers, the music)
and, for each hero roaming on their own, a session: the hero, the map they're on and the one before, their camera,
their COMMAND window and dialogs (CommandMenu), their fights (BattleController), their steps and what the steps lead
to (MovementController, StepTriggers, FieldEncounters, HeroDamage, HeroDeath), the map changes (MapManager), the
drawing of their view (Drawer), and the step counters, the repel timer and the map keys' requests that go with them
(SESSION_ATTRIBUTES).

Game keeps each of those as a SessionAttribute: ``game.player``, ``game.current_map``, ``game.cmd_menu`` ... read and
write the session in use, so the game's code keeps reading them as it always has. The session in use is a context
variable (``use_session``), so each hero's task (src/tasks.py) has its own: the code running in hero 2's task sees
hero 2, their map and their windows. Without a session set, it's the game's first one (Game.main_session), which is
the whole game as one hero plays it, so nothing changes for one hero or for a party.
"""
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, override

# The Game attributes that are each hero's own (see the module docstring)
SESSION_ATTRIBUTES = (
    'player', 'current_map', 'last_map', 'camera', 'big_map', 'cmd_menu', 'battle_ctrl', 'movement', 'step_triggers',
    'field_encounters', 'hero_damage', 'hero_death', 'map_mgr', 'drawer', 'hotkeys', 'events', 'foreground_rects',
    'loop_count', 'frame_pacer', 'color', 'last_zone', 'last_amount_of_tiles_moved', 'tiles_moved_since_spawn',
    'repel_timer', 'repel_tick_pending', 'magic_armor_steps', 'skip_next_encounter', 'step_roll', 'door_history',
    'last_coordinates', 'paused', 'pause_requested', 'cmd_menu_requested', 'smart_a_pending', 'options_requested',
    'dungeon_map_requested', 'message_log_requested', 'play_stats_requested', 'achievements_requested',
    'player_two_menu_requested', 'auto_grind_requested', 'state_request', 'state_request_due',
)


class HeroSession:
    """One hero's share of the game (SESSION_ATTRIBUTES), set as the game makes them."""

    def __init__(self, name: str) -> None:
        self.name = name

    @override
    def __repr__(self) -> str:
        return f'HeroSession({self.name!r})'


_session: ContextVar[HeroSession | None] = ContextVar('hero_session', default=None)


def session_in_use() -> HeroSession | None:
    """The session set for this context (use_session), or None: the game's first."""
    return _session.get()


@contextmanager
def use_session(session: HeroSession) -> Iterator[HeroSession]:
    """For the length of the block (in this context: this task), the game's per-hero attributes are ``session``'s."""
    token = _session.set(session)
    try:
        yield session
    finally:
        _session.reset(token)


class SessionAttribute:
    """A Game attribute that is each hero's own: read and written in the session in use (see the module docstring).
    Deleting it (as unittest.mock's patch does, putting an attribute back) takes it out of the session."""

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    def __get__(self, game: Any, owner: type | None = None) -> Any:
        if game is None:
            return self
        try:
            return getattr(game.current_session, self.name)
        except AttributeError:
            raise AttributeError(self.name) from None

    def __set__(self, game: Any, value: Any) -> None:
        setattr(game.current_session, self.name, value)

    def __delete__(self, game: Any) -> None:
        try:
            delattr(game.current_session, self.name)
        except AttributeError:
            raise AttributeError(self.name) from None


def add_session_attributes(cls: type) -> type:
    """Make each of SESSION_ATTRIBUTES a SessionAttribute of the class (Game)."""
    for name in SESSION_ATTRIBUTES:
        attribute = SessionAttribute()
        attribute.__set_name__(cls, name)
        setattr(cls, name, attribute)
    return cls
