"""The quest journal (QUEST JOURNAL in the options overlay, Q on the map): what to do next. Not on the NES.

It keeps no state of its own. Each goal below is a condition on what the game already keeps, the story flags
(src/story_flags.py) and the hero's items and equipment, so the journal is worked out afresh every time it's opened,
and an old save shows the right goals as soon as it's loaded.

A goal is shown while it's open: it's available (what it needs is done) and not done yet. The main quest's open goals
come first, in the order the game is usually played, then the optional ones, one dialog box page each. With hints on,
each goal is followed by a page with where to go, from what the townspeople say on the NES
(data/text/dialog_lookup_table.py) and where the game keeps the item (src/items.py treasure and hidden_items, the
shrines' wizards in the dialog table).

The whole game, in order:

    Rescue Princess Gwaelin                 the Swamp Cave, behind a locked door, guarded by the Green Dragon
    Carry her back to King Lorik            while carrying her (F_GOT_GWAELIN)
    Get a Magic Key                         while a locked door is in the way of an open goal and no key is held
    Find the Silver Harp                    Garin's Grave, through a locked door in Garinham
    Trade it for the Staff of Rain          the old man in the shrine north-west of Kol (RainStaffDialog)
    Find the Stones of Sunlight             Tantegel Castle's cellar, behind a locked door
    Find Erdrick's Token                    SEARCH 70 leagues south and 40 east of Tantegel (the Cantlin wizard)
    Get the Rainbow Drop                    the three items to the shrine south of Rimuldar (RnbwDrpDialog)
    Build the Rainbow Bridge                the Rainbow Drop on the shore east of Charlock (F_RNBW_BRDG)
    Find the way down in Charlock           SEARCH behind the Dragonlord's throne (F_PSG_FOUND)
    Defeat the Dragonlord                   deep below Charlock (F_DGNLRD_DEAD)
    Return to King Lorik                    once the Dragonlord is dead

    optional:
    Find Erdrick's Armor                    SEARCH in Hauksness, past the Axe Knight
    Find Erdrick's Sword                    deep in Charlock, once the bridge is built
    Defeat the Golem guarding Cantlin       the Fairy Flute, buried in Kol (F_GOLEM_DEAD)

An item counts as found once anything it leads to is done too: the Silver Harp is given away for the Staff of Rain,
and the Staff and the Stones are given away for the Rainbow Drop.
"""
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from src.story_flags import StoryFlags

# QUEST_JOURNAL (base_config): OFF is the NES (Q does nothing); GOALS shows the open goals; HINTS adds where to go
JOURNAL_OFF = 'Off'
JOURNAL_GOALS = 'Goals'
JOURNAL_HINTS = 'Hints'
JOURNAL_SETTINGS = (JOURNAL_OFF, JOURNAL_GOALS, JOURNAL_HINTS)
DEFAULT_JOURNAL = JOURNAL_GOALS


@dataclass(frozen=True, slots=True)
class Progress:
    """What the goals are worked out from: the story flags, the items held and the equipment."""
    flags: StoryFlags
    items: frozenset[str]
    weapon: str = ''
    armor: str = ''

    @classmethod
    def of(cls, flags: StoryFlags, items: Iterable[str], weapon: str = '', armor: str = '') -> 'Progress':
        return cls(flags, frozenset(items), weapon or '', armor or '')

    def has(self, *items: str) -> bool:
        """Holding any one of these items."""
        return any(item in self.items for item in items)

    # Each quest item counts as found once what it's given away for is held, or its use is done
    @property
    def bridge_built(self) -> bool:
        return self.flags.rainbow_bridge_built

    @property
    def has_rainbow_drop(self) -> bool:
        return self.bridge_built or self.has("Rainbow Drop")

    @property
    def has_staff_of_rain(self) -> bool:
        return self.has_rainbow_drop or self.has("Staff of Rain")

    @property
    def has_silver_harp(self) -> bool:
        return self.has_staff_of_rain or self.has("Silver Harp")

    @property
    def has_stones_of_sunlight(self) -> bool:
        return self.has_rainbow_drop or self.has("Stones of Sunlight")

    @property
    def has_erdricks_token(self) -> bool:
        # The shrine's wizard keeps the Staff and the Stones but gives the Token back (HaveErdToken)
        return self.has_rainbow_drop or self.has("Erdrick's Token")

    @property
    def needs_a_key(self) -> bool:
        """No Magic Key held, while a locked door stands in the way of an open goal: Gwaelin's cell in the Swamp
        Cave, the way to Garin's Grave in Garinham, and Tantegel Castle's cellar."""
        return "Magic Key" not in self.items and not self.flags.dragonlord_defeated and (
                not self.flags.gwaelin_rescued or not self.has_silver_harp or not self.has_stones_of_sunlight)


def always(_progress: Progress) -> bool:
    return True


@dataclass(frozen=True, slots=True)
class Goal:
    """One thing to do: what to do (text), where (hint), when it's done and when it can be started."""
    text: str
    hint: str
    done: Callable[[Progress], bool]
    available: Callable[[Progress], bool] = always
    optional: bool = False

    def is_open(self, progress: Progress) -> bool:
        return self.available(progress) and not self.done(progress)


GOALS = (
    # The princess: NES DoGwaelinRescue sets F_GOT_GWAELIN, DoKingDialog F_RTN_GWAELIN
    Goal("Rescue Princess Gwaelin.",
         "She is held in the Swamp Cave, south of Kol, behind a locked door. A dragon guards her.",
         done=lambda p: p.flags.gwaelin_rescued or p.flags.dragonlord_defeated),
    Goal("Carry Princess Gwaelin back to King Lorik.",
         "King Lorik waits in Tantegel Castle.",
         done=lambda p: p.flags.gwaelin_returned,
         available=lambda p: p.flags.carrying_gwaelin),
    Goal("Get a Magic Key.",
         "Magic Keys are sold in Tantegel Castle, Rimuldar and Cantlin.",
         done=lambda p: not p.needs_a_key),
    # The Silver Harp -> the Staff of Rain (RainStaffDialog)
    Goal("Find the Silver Harp.",
         "It lies deep in Garin's Grave. The way down is behind a locked door in Garinham.",
         done=lambda p: p.has_silver_harp),
    Goal("Take the Silver Harp to the old man in the shrine.",
         "The shrine is north and west of Kol. He gives the Staff of Rain for the harp.",
         done=lambda p: p.has_staff_of_rain,
         available=lambda p: p.has_silver_harp),
    Goal("Find the Stones of Sunlight.",
         "They are in the cellar of Tantegel Castle, behind a locked door.",
         done=lambda p: p.has_stones_of_sunlight),
    # Erdrick's Token: SEARCH on the overworld (hidden_items), hinted by the Cantlin wizard (ErdTknDialog)
    Goal("Find Erdrick's Token.",
         "From Tantegel Castle travel 70 leagues to the south and 40 to the east, and search.",
         done=lambda p: p.has_erdricks_token),
    # The three items -> the Rainbow Drop (RnbwDrpDialog)
    Goal("Take the Stones of Sunlight, the Staff of Rain and Erdrick's Token to the old man in the shrine.",
         "The shrine is far to the south of Rimuldar. He gives the Rainbow Drop.",
         done=lambda p: p.has_rainbow_drop,
         available=lambda p: p.has_staff_of_rain and p.has_stones_of_sunlight and p.has_erdricks_token),
    # The bridge: NES F_RNBW_BRDG
    Goal("Use the Rainbow Drop to make a bridge to Charlock.",
         "Hold it up at the water's edge east of Charlock, on the western shore of Rimuldar's land.",
         done=lambda p: p.bridge_built,
         available=lambda p: p.has_rainbow_drop),
    # Charlock: NES F_PSG_FOUND, then F_DGNLRD_DEAD
    Goal("Find the hidden way down in Charlock.",
         "Search behind the Dragonlord's throne.",
         done=lambda p: p.flags.charlock_stairs_revealed or p.flags.dragonlord_defeated,
         available=lambda p: p.bridge_built),
    Goal("Defeat the Dragonlord.",
         "He waits in the deepest part of Charlock.",
         done=lambda p: p.flags.dragonlord_defeated,
         available=lambda p: p.bridge_built),
    Goal("Return to King Lorik.",
         "Tantegel Castle awaits thy return.",
         done=lambda p: False,
         available=lambda p: p.flags.dragonlord_defeated),
    # Optional: the NES never asks for these
    Goal("Find Erdrick's Armor.",
         "It is hidden in the ruins of Hauksness, far to the south. Beware its guardian.",
         done=lambda p: p.armor == "Erdrick's Armor" or p.flags.dragonlord_defeated,
         optional=True),
    Goal("Find Erdrick's Sword.",
         "It lies deep within Charlock.",
         done=lambda p: p.weapon == "Erdrick's Sword" or p.flags.dragonlord_defeated,
         available=lambda p: p.bridge_built,
         optional=True),
    Goal("Defeat the Golem guarding Cantlin.",
         "Golem fears the music of the flute. The Fairy Flute is in Kol, four steps south of the bath.",
         done=lambda p: p.flags.golem_defeated or p.flags.dragonlord_defeated,
         optional=True),
)

# Shown before the optional goals, when there are any
OPTIONAL_HEADING = "If thou wishest:"


def open_goals(progress: Progress, goals: Iterable[Goal] = GOALS) -> list[Goal]:
    """The open goals, the main quest's first, each in table order."""
    open_ones = [goal for goal in goals if goal.is_open(progress)]
    return [goal for goal in open_ones if not goal.optional] + [goal for goal in open_ones if goal.optional]


def journal_pages(progress: Progress, hints: bool, _: Callable[[str], str] = str) -> list[str]:
    """A dialog box page per open goal, and with hints, a page after it with where to go. The first optional goal
    starts with OPTIONAL_HEADING. ``_`` translates them (set_gettext_language)."""
    pages = []
    goals = open_goals(progress)
    first_optional = next((goal for goal in goals if goal.optional), None)
    for goal in goals:
        text = _(goal.text)
        pages.append(_(OPTIONAL_HEADING) + "\n" + text if goal is first_optional else text)
        if hints:
            pages.append(_(goal.hint))
    return pages


def game_progress(game) -> Progress:
    player = game.player
    return Progress.of(game.story_flags, player.inventory, player.weapon, player.armor)


def journal_texts() -> list[str]:
    """Every text the journal can show, for the translation catalog (catalog_tools.dynamic_messages)."""
    return [OPTIONAL_HEADING] + [text for goal in GOALS for text in (goal.text, goal.hint)]
