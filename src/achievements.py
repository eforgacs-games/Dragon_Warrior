"""Achievements (#425): things done in the game, kept from one adventure to the next. Not on the NES.

With the ACHIEVEMENTS option ON (the options overlay's OTHER page; OFF is the NES), each achievement is unlocked the
first time what it asks for is true as one of the game's events happens (src/game_events.py: every step, fight, level,
death, gold and chest), so one that a story event earns (Gwaelin brought home, the Rainbow Bridge) is unlocked by the
next step at the latest. They're checked after the play statistics have counted the event (src/play_stats.py: Game
subscribes those first), and read them, the story flags and the hero. With the option OFF nothing is checked, so
turning it on later unlocks what the adventure has already done as the next event happens.

Nothing is unlocked while a cheat is on: god mode, the debug keys or the CHEATS option (F4 auto-battle and F9
invulnerability), whether they're in use or not.

Unlocking one shows a banner at the top of the map for BANNER_MS (AchievementBanner, drawn by Game.main over the map
each frame), one after another if there are more; one unlocked in a fight waits for the map. The TROPHIES key (T, as
bound, src/controls.py) opens the achievements page on the map, drawn and scrolled as the stats page is
(src/stats_screen.py): how many are unlocked, then each one, with the day it was unlocked, and what it asks for.

    +--ACHIEVEMENTS---------------------+     +-ACHIEVEMENT--------------+
    | UNLOCKED                     3/19 |     | FIRST VICTORY            |
    |                                   |     +--------------------------+
    | FIRST VICTORY          2026-11-05 |
    |   Win a fight.                    |
    | ...                               |
    +-----------------------------------+

They belong to whoever plays on this computer, not to an adventure log, so they're kept in their own file next to the
global settings (src/settings.py), achievements.json in the per-user config folder:

    {"version": 1, "unlocked": {"first_victory": "2026-11-05", ...}}

with the day each was unlocked. Keys this build doesn't know (a newer build's achievements) and entries it doesn't
know are kept and written back. A config whose settings are kept nowhere (SETTINGS_PATH None: the tests) keeps the
achievements nowhere too, only for the run. A file that can't be read is no achievements; one that can't be written
prints a warning.
"""
import json
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from os.path import dirname, join
from typing import TYPE_CHECKING, Any, override

from pygame import K_ESCAPE, Surface
from pygame.time import get_ticks

from src.common import B_BUTTON_KEYS, START_BUTTON_KEYS
from src.controls import KeySet
from src.enemy_lookup import enemy_string_lookup
from src.game_events import EventBus, GameEvent
from src.json_files import atomic_write_json
from src.languages import language_named
from src.message_log import LINE_WIDTH, MessageLogScreen, wrap
from src.play_stats import SAME_MONSTER
from src.settings import settings_path
from src.stats_screen import aligned
from src.translated_window import draw_translated_window
from src.windows import Window, WindowLayout, WindowText

if TYPE_CHECKING:
    from src.game import Game  # src.game imports this module

ACHIEVEMENTS_FILE_NAME = 'achievements.json'
FORMAT_VERSION = 1
UNLOCKED = 'unlocked'

MAX_LEVEL = 30
MAX_GOLD = 0xFFFF  # NES: GoldLB/GoldUB max out at $FFFF
DRAGONLORD = 'Dragonlord'
# Every kind of monster, the Dragonlord's two forms as one (src/play_stats.py SAME_MONSTER)
EVERY_MONSTER = frozenset(SAME_MONSTER.get(name, name) for name in enemy_string_lookup)
# The challenges' limits
LOW_LEVEL = 20
FAST_PLAY_TIME_MS = 2 * 60 * 60 * 1000  # two hours
MANY_FIGHTS = 100
MANY_ESCAPES = 50
MANY_STEPS = 10000

# The cheats under which nothing is unlocked (config keys)
CHEATS = ('GOD_MODE', 'DEBUG_KEYS', 'CHEAT_KEYS')


def defeated(game: Any, monster: str) -> bool:
    return game.play_stats.monsters_defeated.get(monster, 0) > 0


def dragonlord_defeated(game: Any) -> bool:
    return defeated(game, DRAGONLORD)


@dataclass(frozen=True, slots=True)
class Achievement:
    """One achievement: its key (in the file), its title, what it asks for, and whether the game has done it."""
    key: str
    title: str
    description: str
    earned: Callable[[Any], bool]


# In the page's order: the story, the challenges, then the rest
ACHIEVEMENTS = (
    Achievement('first_victory', "FIRST VICTORY", "Win a fight.",
                lambda game: game.play_stats.fights_won > 0),
    Achievement('golem', "STONE GUARDIAN", "Defeat the Golem.",
                lambda game: defeated(game, 'Golem')),
    Achievement('green_dragon', "DRAGON'S LAIR", "Defeat the Green Dragon.",
                lambda game: defeated(game, 'Green Dragon')),
    Achievement('gwaelin_home', "HOMECOMING", "Bring Princess Gwaelin home.",
                lambda game: game.story_flags.gwaelin_returned),
    Achievement('death_necklace', "CURSED", "Find the Death Necklace.",
                lambda game: game.story_flags.death_necklace_found),
    Achievement('rainbow_bridge', "RAINBOW BRIDGE", "Make the Rainbow Bridge.",
                lambda game: game.story_flags.rainbow_bridge_built),
    Achievement('erdricks_heir', "ERDRICK'S HEIR", "Wear Erdrick's Armor and wield Erdrick's Sword.",
                lambda game: game.player.armor == "Erdrick's Armor" and game.player.weapon == "Erdrick's Sword"),
    Achievement('dragonlord', "DRAGONLORD", "Defeat the Dragonlord.", dragonlord_defeated),
    Achievement('no_deaths', "UNDYING", "Defeat the Dragonlord without dying.",
                lambda game: dragonlord_defeated(game) and game.play_stats.deaths == 0),
    Achievement('low_level', "UNDERDOG", "Defeat the Dragonlord at level 20 or lower.",
                lambda game: dragonlord_defeated(game) and game.player.level <= LOW_LEVEL),
    Achievement('fast', "SWIFT", "Defeat the Dragonlord in under two hours of play.",
                lambda game: dragonlord_defeated(game) and game.play_stats.play_time_ms < FAST_PLAY_TIME_MS),
    Achievement('every_monster', "MONSTER HUNTER", "Defeat every kind of monster.",
                lambda game: EVERY_MONSTER <= set(game.play_stats.monsters_defeated)),
    Achievement('metal_slime', "QUICKSILVER", "Defeat a Metal Slime.",
                lambda game: defeated(game, 'Metal Slime')),
    Achievement('level_10', "LEVEL 10", "Reach level 10.", lambda game: game.player.level >= 10),
    Achievement('level_20', "LEVEL 20", "Reach level 20.", lambda game: game.player.level >= 20),
    Achievement('level_30', "LEVEL 30", "Reach the highest level.", lambda game: game.player.level >= MAX_LEVEL),
    Achievement('many_fights', "CENTURION", "Win 100 fights.",
                lambda game: game.play_stats.fights_won >= MANY_FIGHTS),
    Achievement('many_escapes', "DISCRETION", "Run away from 50 fights.",
                lambda game: game.play_stats.fights_fled >= MANY_ESCAPES),
    Achievement('many_steps', "WANDERER", "Take 10000 steps.",
                lambda game: game.play_stats.steps >= MANY_STEPS),
    Achievement('max_gold', "RICHES", "Carry 65535 gold.", lambda game: game.player.gold >= MAX_GOLD),
    Achievement('first_death', "THOU ART DEAD", "Die for the first time.",
                lambda game: game.play_stats.deaths > 0),
)
ACHIEVEMENTS_BY_KEY = {achievement.key: achievement for achievement in ACHIEVEMENTS}


def achievements_path(config: dict) -> str | None:
    """The achievements file: next to the settings file (src/settings.py settings_path), or None if those are kept
    nowhere."""
    settings = settings_path(config)
    return join(dirname(settings), ACHIEVEMENTS_FILE_NAME) if settings else None


def load_unlocked(path: str | None) -> tuple[dict[str, str], dict[str, Any]]:
    """The file's unlocked achievements (key: the day, as text) and its other entries; none if there's no file or it
    can't be read."""
    if not path:
        return {}, {}
    try:
        with open(path, encoding='utf-8') as achievements_file:
            data = json.load(achievements_file)
    except (OSError, UnicodeDecodeError, ValueError):
        return {}, {}
    if not isinstance(data, dict):
        return {}, {}
    unlocked = data.get(UNLOCKED)
    unlocked = {str(key): str(day) for key, day in unlocked.items()} if isinstance(unlocked, dict) else {}
    others = {key: value for key, value in data.items() if key not in (UNLOCKED, 'version')}
    if type(data.get('version')) is int and data['version'] > FORMAT_VERSION:
        others['version'] = data['version']
    return unlocked, others


def save_unlocked(path: str, unlocked: dict[str, str], others: dict[str, Any]) -> bool:
    """Write the file in one step (src/json_files.py). Returns whether it was written."""
    try:
        atomic_write_json(path, {'version': FORMAT_VERSION, **others, UNLOCKED: unlocked}, indent=2,
                          trailing_newline=True)
    except OSError as error:
        print(f"Could not save the achievements to {path}: {error}")
        return False
    return True


def cheating(game: Any) -> bool:
    config = game.game_state.config
    return any(config.get(cheat) for cheat in CHEATS)


class Achievements:
    """The unlocked achievements and their file (None: kept only for the run), checked on every game event."""

    def __init__(self, game: 'Game', path: str | None):
        self.game = game
        self.path = path
        self.unlocked, self.other_entries = load_unlocked(path)
        self.banner = AchievementBanner()

    @classmethod
    def from_config(cls, game: 'Game', config: dict) -> 'Achievements':
        return cls(game, achievements_path(config))

    def subscribe(self, events: EventBus) -> None:
        events.subscribe(GameEvent, self.event_happened)

    def event_happened(self, _event: GameEvent) -> None:
        self.check()

    def enabled(self) -> bool:
        return bool(self.game.game_state.config.get('ACHIEVEMENTS')) and not cheating(self.game)

    def check(self) -> list[Achievement]:
        """Unlock every achievement the game has now earned, if the option is on and no cheat is. Returns them."""
        if not self.enabled():
            return []
        earned = [achievement for achievement in ACHIEVEMENTS
                  if achievement.key not in self.unlocked and achievement.earned(self.game)]
        for achievement in earned:
            self.unlocked[achievement.key] = date.today().isoformat()
            self.banner.show(achievement)
        if earned and self.path:
            save_unlocked(self.path, self.unlocked, self.other_entries)
        return earned

    def is_unlocked(self, key: str) -> bool:
        return key in self.unlocked


# The banner: a window at the top of the map with the title of the achievement just unlocked
BANNER_MS = 3000  # real time, whatever the game speed
BANNER_TITLE = WindowText("ACHIEVEMENT", 2, 0)
BANNER_WINDOW = Window(1, 1, 14, 2)


def banner_layout(title: str) -> WindowLayout:
    return WindowLayout(window=BANNER_WINDOW, title=BANNER_TITLE, texts=(WindowText(title, 2, 2),))


class AchievementBanner:
    """The achievements waiting to be shown, and since when the first has been (None: not yet)."""

    def __init__(self) -> None:
        self.waiting: deque[Achievement] = deque()
        self.shown_since: int | None = None

    def show(self, achievement: Achievement) -> None:
        self.waiting.append(achievement)

    def current(self, now: int) -> Achievement | None:
        """The achievement to show now, moving on to the next once one has been up BANNER_MS."""
        if self.waiting and self.shown_since is not None and now - self.shown_since >= BANNER_MS:
            self.waiting.popleft()
            self.shown_since = None
        if not self.waiting:
            return None
        if self.shown_since is None:
            self.shown_since = now
        return self.waiting[0]

    def draw(self, screen: Surface, color: tuple, config: dict, translate: Callable[[str], str]) -> None:
        """Draw the banner over the map (once the map is drawn, before the display is), if one is up."""
        achievement = self.current(get_ticks())
        if achievement is None or config.get('NO_BLIT'):
            return
        draw_translated_window(screen, banner_layout(achievement.title), color, config, translate)


# The page
ACHIEVEMENTS_TITLE = WindowText("ACHIEVEMENTS", 4, 0)
TROPHIES_KEYS = KeySet('TROPHIES')
CLOSE_KEYS = B_BUTTON_KEYS + START_BUTTON_KEYS + TROPHIES_KEYS + (K_ESCAPE,)
UNLOCKED_LABEL = "UNLOCKED"
DESCRIPTION_INDENT = 2


def page_lines(unlocked: dict[str, str], _: Callable[[str], str] = str, breaks_anywhere: bool = False) -> list[str]:
    """The page's lines: how many are unlocked, then each achievement (with the day it was unlocked, if it was) and
    what it asks for. ``_`` translates them."""
    count = sum(1 for achievement in ACHIEVEMENTS if achievement.key in unlocked)
    lines = [aligned(_(UNLOCKED_LABEL), f'{count}/{len(ACHIEVEMENTS)}')]
    for achievement in ACHIEVEMENTS:
        day = unlocked.get(achievement.key)
        lines.append('')
        lines.append(aligned(_(achievement.title), day) if day else _(achievement.title))
        lines += [' ' * DESCRIPTION_INDENT + line
                  for line in wrap(_(achievement.description), LINE_WIDTH - DESCRIPTION_INDENT,
                                   breaks_anywhere=breaks_anywhere)]
    return lines


def achievement_texts() -> list[str]:
    """The achievements' text and the page's and the banner's, for the translation catalog."""
    return [ACHIEVEMENTS_TITLE.text, BANNER_TITLE.text, UNLOCKED_LABEL,
            *(text for achievement in ACHIEVEMENTS for text in (achievement.title, achievement.description))]


class AchievementsScreen(MessageLogScreen):
    """The achievements page over the map, run until it's closed."""
    title = ACHIEVEMENTS_TITLE
    close_keys = CLOSE_KEYS

    @override
    def screen_lines(self) -> list[str]:
        return page_lines(self.game.achievements.unlocked, self._,
                          language_named(self.config.get('LANGUAGE')).breaks_anywhere)

    @override
    def first_top(self) -> int:
        return 0
