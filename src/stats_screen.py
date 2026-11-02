"""The stats page: the adventure's play statistics (src/play_stats.py), over the map. Not on the NES.

The STATS key (P, as bound, src/controls.py) opens it on the map, when the STATS PAGE option is ON (the options
overlay; OFF is the NES, which has none). Like the message log, it opens only when START would pause the game, once the
hero and the NPCs have finished their steps (MapHotkeys.press_play_stats, MovementController.resolve_pending_freezes),
and it's drawn and scrolled as the message log is (src/message_log.py MessageLogScreen): one NES-style window fills the
screen, titled STATS, each count on a line of its own with the number on the right, then the monsters defeated, in the
order of the game's enemy table:

    +--STATS----------------------------+
    | PLAY TIME                 1:02:03 |
    | STEPS                        1234 |
    | ...                               |
    | MONSTERS DEFEATED                 |
    |  Slime                         12 |
    | UP/DOWN:SCROLL  B:CLOSE           |
    +-----------------------------------+

B, Esc, START or the STATS key close it, and the map is put back as it was. The play time doesn't count while it's
open (MapHotkeys.open_requested).
"""
from collections.abc import Callable
from typing import override

from pygame import K_ESCAPE

from src.common import B_BUTTON_KEYS, START_BUTTON_KEYS
from src.controls import KeySet
from src.enemy_lookup import enemy_string_lookup
from src.message_log import LINE_WIDTH, MessageLogScreen, text_width
from src.play_stats import PlayStats, play_time_text
from src.windows import WindowText

STATS_TITLE = WindowText("STATS", 4, 0)
STATS_KEYS = KeySet('PLAY_STATS')
CLOSE_KEYS = B_BUTTON_KEYS + START_BUTTON_KEYS + STATS_KEYS + (K_ESCAPE,)

PLAY_TIME = "PLAY TIME"
STEPS = "STEPS"
FIGHTS_WON = "FIGHTS WON"
FIGHTS_FLED = "FIGHTS FLED"
FIGHTS_LOST = "FIGHTS LOST"
DEATHS = "DEATHS"
GOLD_EARNED = "GOLD EARNED"
GOLD_SPENT = "GOLD SPENT"
CHESTS_OPENED = "CHESTS OPENED"
MONSTERS_DEFEATED = "MONSTERS DEFEATED"
# Each monster's name is indented under MONSTERS_DEFEATED
MONSTER_INDENT = ' '


def aligned(label: str, value: str, width: int = LINE_WIDTH) -> str:
    """The label, then the value at the right of a line ``width`` tiles wide (a blank between them at least)."""
    return label + ' ' * max(1, width - text_width(label) - text_width(value)) + value


def monsters_in_order(monsters: dict[str, int]) -> list[tuple[str, int]]:
    """The monsters defeated, in the enemy table's order (src/enemy_lookup.py), any other name after them."""
    order = {name: place for place, name in enumerate(enemy_string_lookup)}
    return sorted(monsters.items(), key=lambda monster: (order.get(monster[0], len(order)), monster[0]))


def stat_lines(stats: PlayStats, _: Callable[[str], str] = str) -> list[str]:
    """The page's lines: each count, then the monsters defeated if there are any. ``_`` translates them."""
    counts = (
        (PLAY_TIME, play_time_text(stats.play_time_ms)),
        (STEPS, str(stats.steps)),
        (FIGHTS_WON, str(stats.fights_won)),
        (FIGHTS_FLED, str(stats.fights_fled)),
        (FIGHTS_LOST, str(stats.fights_lost)),
        (DEATHS, str(stats.deaths)),
        (GOLD_EARNED, str(stats.gold_earned)),
        (GOLD_SPENT, str(stats.gold_spent)),
        (CHESTS_OPENED, str(stats.chests_opened)),
    )
    lines = [aligned(_(label), value) for label, value in counts]
    monsters = monsters_in_order(stats.monsters_defeated)
    if monsters:
        lines += ['', _(MONSTERS_DEFEATED)]
        lines += [aligned(MONSTER_INDENT + _(name), str(count)) for name, count in monsters]
    return lines


def screen_texts() -> list[str]:
    """The page's own text, for the translation catalog (the monsters' names are the enemy table's, and the hint is
    the message log's)."""
    return [STATS_TITLE.text, PLAY_TIME, STEPS, FIGHTS_WON, FIGHTS_FLED, FIGHTS_LOST, DEATHS, GOLD_EARNED, GOLD_SPENT,
            CHESTS_OPENED, MONSTERS_DEFEATED]


class StatsScreen(MessageLogScreen):
    """The stats page over the map, run until it's closed (see the module docstring)."""
    title = STATS_TITLE
    close_keys = CLOSE_KEYS

    @override
    def screen_lines(self) -> list[str]:
        return stat_lines(self.game.play_stats, self._)

    @override
    def first_top(self) -> int:
        """The page starts at the top, with the play time."""
        return 0
