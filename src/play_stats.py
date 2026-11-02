"""Play statistics: what the hero has done on this adventure, for the stats page (src/stats_screen.py) and a base for
achievements. Not on the NES.

Kept per adventure log: saved with the log (SAVE_KEY in the save file, src/save_file.py) and with save states and the
rewind (src/save_state.py), so loading either puts the counts back as they were then. A new quest starts at zero, and
so does a log saved before the counts were kept.

They're always counted, whatever the STATS PAGE option says (it only decides whether P shows them), so turning the page
on shows everything done so far. Each is counted where it happens, in one line:

- play time: Game.run_map_frame ticks the clock (tick) every map frame. It's real time, the same at any game speed
  (keys 1 to 5), and it counts what happens between two map frames too, so fights and dialogs are play. It doesn't
  count while the game is paused (START), nor while one of the screens the map's keys open is up (the options
  overlay, the dungeon map, the message log, the stats page: MapHotkeys.open_requested stops the clock), nor on the
  title screen;
- steps: Game.count_step, every step that ends on a new block;
- fights won, fled and lost: BattleController.fight_enemy. Fled is the hero running away; an enemy that runs away is
  none of the three. A fight won counts its enemy as a monster defeated, by name; the Dragonlord's two forms are one
  fight, counted once, as the Dragonlord;
- deaths: Game.handle_death, in a fight or on the map (a swamp or barrier step);
- gold earned: a won fight's gold (Battle.enemy_defeated), a treasure chest's (CommandMenu.take_gold) and what shops
  pay for what the hero sells or trades in (data/text/dialog_lookup_table.py); gold spent: what shops and inns are
  paid. The gold lost on dying isn't spent;
- chests opened: CommandMenu.open_chest, every chest taken, an empty one too.
"""
from dataclasses import dataclass, field, fields
from typing import Any

from pygame.time import get_ticks

SAVE_KEY = 'PlayStats'
MONSTERS_DEFEATED = 'monsters_defeated'

# The Dragonlord's final form is counted as the Dragonlord: beating his first form only starts it
SAME_MONSTER = {'Dragonlord 2': 'Dragonlord'}

MS_PER_SECOND = 1000
SECONDS_PER_MINUTE = 60
MINUTES_PER_HOUR = 60


@dataclass(slots=True)
class PlayStats:
    """The counts (see the module docstring). ``clock_at`` is the real time (pygame's get_ticks) of the last tick that
    counted, None while the clock is stopped; it isn't saved."""
    play_time_ms: int = 0
    steps: int = 0
    fights_won: int = 0
    fights_fled: int = 0
    fights_lost: int = 0
    deaths: int = 0
    gold_earned: int = 0
    gold_spent: int = 0
    chests_opened: int = 0
    monsters_defeated: dict[str, int] = field(default_factory=dict)
    clock_at: int | None = field(default=None, compare=False, repr=False)

    def tick(self, counting: bool = True, now: int | None = None) -> None:
        """Count the real time since the last tick as play, unless not ``counting`` (the game is paused) or the clock
        was stopped; the clock runs on from now either way."""
        now = get_ticks() if now is None else now
        if counting and self.clock_at is not None:
            self.play_time_ms += max(0, now - self.clock_at)
        self.clock_at = now

    def stop_clock(self) -> None:
        """Count nothing until the next tick (a screen opened over the map has just closed)."""
        self.clock_at = None

    def take_step(self) -> None:
        self.steps += 1

    def won_fight(self, enemy_name: str) -> None:
        self.fights_won += 1
        monster = SAME_MONSTER.get(enemy_name, enemy_name)
        self.monsters_defeated[monster] = self.monsters_defeated.get(monster, 0) + 1

    def ran_away(self) -> None:
        self.fights_fled += 1

    def lost_fight(self) -> None:
        self.fights_lost += 1

    def died(self) -> None:
        self.deaths += 1

    def earn_gold(self, amount: int) -> None:
        self.gold_earned += max(0, amount)

    def spend_gold(self, amount: int) -> None:
        self.gold_spent += max(0, amount)

    def open_chest(self) -> None:
        self.chests_opened += 1

    def to_save(self) -> dict[str, Any]:
        """The counts as JSON values, the monsters as a copy."""
        saved: dict[str, Any] = {name: getattr(self, name) for name in counter_names()}
        saved[MONSTERS_DEFEATED] = dict(self.monsters_defeated)
        return saved

    @classmethod
    def from_save(cls, saved: Any) -> 'PlayStats':
        """Saved counts. Anything missing or that isn't a count (a save from before they were kept has none) is 0."""
        stats = cls()
        if not isinstance(saved, dict):
            return stats
        for name in counter_names():
            setattr(stats, name, count_or_zero(saved.get(name)))
        monsters = saved.get(MONSTERS_DEFEATED)
        if isinstance(monsters, dict):
            stats.monsters_defeated = {str(name): count_or_zero(count) for name, count in monsters.items()
                                       if count_or_zero(count) > 0}
        return stats

    def copy(self) -> 'PlayStats':
        return PlayStats.from_save(self.to_save())


def counter_names() -> tuple[str, ...]:
    """The fields that are a single count: every one but the monsters and the clock."""
    return tuple(stat.name for stat in fields(PlayStats) if stat.name not in (MONSTERS_DEFEATED, 'clock_at'))


def count_or_zero(value: Any) -> int:
    """value if it's a count (an int of 0 or more, not a bool), else 0."""
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def play_time_text(play_time_ms: int) -> str:
    """The play time as hours, minutes and seconds: 0:00:00, 12:34:56, 123:04:05."""
    seconds = play_time_ms // MS_PER_SECOND
    minutes, seconds = divmod(seconds, SECONDS_PER_MINUTE)
    hours, minutes = divmod(minutes, MINUTES_PER_HOUR)
    return f'{hours}:{minutes:02}:{seconds:02}'
