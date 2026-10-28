"""The quest journal (QUEST JOURNAL in the options overlay, Q on the map): the goals the hero knows of. Not on the NES.

On the NES the player learns what to do from what the townspeople say, so the journal only lists a goal once the hero
has learned of it, the way the player would have:

- told of it: an NPC said something about it (each goal's told_by: the NPC's NES dialog byte, as the dialog table
  data/text/dialog_lookup_table.py and the maps' NPC tables (src/npcs.py) key them), or King Lorik's opening speech.
  CommandMenu.run_dialog calls hear after an NPC has spoken, and the hero remembers it in StoryFlags.heard_goals, which
  is saved with the game and in save states;
- found it out: the hero holds the item, has been where the goal is, or has met the enemy (found_out, worked out from the
  story flags and the items each time, so an old save shows these at once). Meeting the Golem is kept as being told;
- done it: a goal that's done is known too, so an old save, which has heard nothing, still shows what it has done.

Each known goal is one dialog box page: the open ones first, the main quest's in the order the game is usually played,
then the optional ones, then the ones done, marked DONE_FORMAT. A goal that can't be done any more (missed: the
optional ones and Gwaelin's rescue once the Dragonlord is dead) isn't shown unless it was done. With nothing known,
the journal says NOTHING_HEARD. With HINTS on, each open goal is followed by a page with what the hero was told of it:
the NPC's own words (Told.line), or, for a goal found out or told of without words to quote, the goal's hint.

The whole game, in order (who tells of each goal: the dialog bytes in told_by):

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
from dataclasses import dataclass, field

from src.story_flags import GoalSource, StoryFlags

# QUEST_JOURNAL (base_config): OFF is the NES (Q does nothing); LEARNED shows the goals the hero knows of; HINTS adds
# what was said about each
JOURNAL_OFF = 'Off'
JOURNAL_LEARNED = 'Learned'
JOURNAL_HINTS = 'Hints'
JOURNAL_SETTINGS = (JOURNAL_OFF, JOURNAL_LEARNED, JOURNAL_HINTS)
# Older builds' GOALS: every open goal, known or not. It loads as LEARNED (src/options_screen.py Switch.renamed).
LEGACY_JOURNAL_GOALS = 'Goals'

# The sources of what the hero is told that aren't an NPC's dialog byte
KING_OPENING_SPEECH = 'KING_OPENING_SPEECH'  # King Lorik's words as a new quest starts (Drawer.run_automatic_initial_dialog)
GOLEM_FIGHT = 'GOLEM_FIGHT'  # stepping in front of the Golem (Game.check_guardian_fight)

# The throne room guard at 5,6 (dialog byte $24) speaks of the key only until the hero has left the throne room
# (ThrnRmDialog2: TextBlock17 entry 0, then TextBlock6 entry 3, which doesn't)
THRONE_ROOM_KEY_ADVICE = 0x24


@dataclass(frozen=True, slots=True)
class Progress:
    """What the goals are worked out from: the story flags (with the goals heard of), the items held and the
    equipment."""
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

    @property
    def dragonlord_defeated(self) -> bool:
        return self.flags.dragonlord_defeated

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
        Cave, the way to Garin's Grave in Garinham, and Tantegel Castle's cellar.

        Charlock's three locked doors aren't on the way to anything the journal asks for: the two on the ground floor
        (DLCstlGFDat) lead to the stairs down at GF(4,14) and GF(15,14), but the way to the Dragonlord, and to
        Erdrick's Sword on sublevel 2, is the hidden staircase behind the throne (F_PSG_FOUND), reached through the
        barriers without a door; the one on the bottom floor (DLBFDat) only closes off a side room
        (tests/test_map_connectivity.py checks this)."""
        return "Magic Key" not in self.items and not self.dragonlord_defeated and (
                not self.flags.gwaelin_rescued or not self.has_silver_harp or not self.has_stones_of_sunlight)


def never(_: Progress) -> bool:
    return False


def after_the_dragonlord(progress: Progress) -> bool:
    """Once the Dragonlord is dead, the optional goals and Gwaelin's rescue can't be done any more."""
    return progress.dragonlord_defeated


@dataclass(frozen=True, slots=True)
class Told:
    """Something said of a goal: who says it (an NPC's dialog byte, or KING_OPENING_SPEECH or GOLEM_FIGHT) and the
    words to show as its hint, the same text as the dialog table's (so it has the same translation), or None to show
    the goal's own hint (when what is said depends on an answer, or names the hero)."""
    source: GoalSource
    line: str | None = None


@dataclass(frozen=True, slots=True)
class Goal:
    """One thing to do.

    key: the name it's kept under in StoryFlags.heard_goals.
    text: what to do; hint: where, shown when no NPC's words are.
    done: when it's done.
    found_out: when the hero knows of it without being told (holding the item, having been there, having met it).
    told_by: who tells of it.
    missed: when it can't be done any more.
    short_text: what to do in fewer words, for its DONE_FORMAT page when text would take the whole dialog box."""
    key: str
    text: str
    hint: str
    done: Callable[[Progress], bool]
    # Function fields default through default_factory, so the class holds no function attribute that would read as
    # a method (self.found_out(progress) calls the stored function, not a bound method)
    found_out: Callable[[Progress], bool] = field(default_factory=lambda: never)
    told_by: tuple[Told, ...] = ()
    missed: Callable[[Progress], bool] = field(default_factory=lambda: never)
    optional: bool = False
    short_text: str | None = None

    @property
    def done_text(self) -> str:
        return self.short_text or self.text

    def is_known(self, progress: Progress) -> bool:
        return self.key in progress.flags.heard_goals or self.found_out(progress) or self.done(progress)

    def is_open(self, progress: Progress) -> bool:
        return self.is_known(progress) and not self.done(progress) and not self.missed(progress)

    def is_done(self, progress: Progress) -> bool:
        return self.is_known(progress) and self.done(progress)

    def line_from(self, source: GoalSource | None) -> str | None:
        """What ``source`` said of this goal, if there are words to show."""
        return next((told.line for told in self.told_by if told.source == source), None)

    def hint_for(self, progress: Progress) -> str:
        """What the hero was told of it, or else its hint."""
        return self.line_from(progress.flags.heard_goals.get(self.key)) or self.hint


GOALS = (
    # The princess: NES DoGwaelinRescue sets F_GOT_GWAELIN, DoKingDialog F_RTN_GWAELIN
    Goal("rescue_gwaelin", "Rescue Princess Gwaelin.",
         "She is held in the Swamp Cave, south of Kol, behind a locked door. A dragon guards her.",
         done=lambda p: p.flags.gwaelin_rescued,
         told_by=(
             # Tantegel: the female villager at 8,13 and the guard at 15,20 (ChkPrncsDialog1 and 2)
             Told(0x62, "Where oh where can I find Princess Gwaelin?"),
             Told(0x63, "Where oh where can I find Princess Gwaelin?"),
             # Brecconary: the guard at 10,26 (ChkPrncsDialog3)
             Told(0x64, "Tell King Lorik that the search for his daughter hath failed."),
             # The throne room: the mobile guard at 7,5 (ChkPrncsDialog4): what he says depends on the answer
             Told(0x65),
             # Garinham: the wizard at 2,17, and the mobile male villager at 18,12
             Told(0x40, "Many believe that Princess Gwaelin is hidden away in a cave."),
             Told(0x44, "It is said that the Princess was kidnapped and taken eastward.")),
         missed=after_the_dragonlord),
    Goal("return_gwaelin", "Carry Princess Gwaelin back to King Lorik.",
         "King Lorik waits in Tantegel Castle.",
         done=lambda p: p.flags.gwaelin_returned,
         found_out=lambda p: p.flags.carrying_gwaelin),
    Goal("magic_key", "Get a Magic Key.",
         "Magic Keys are sold in Tantegel Castle, Rimuldar and Cantlin.",
         done=lambda p: not p.needs_a_key,
         found_out=lambda p: p.has("Magic Key"),
         told_by=(
             # Tantegel: the mobile guard at 19,2
             Told(0x17, "Thou must have a key to open a door."),
             # The throne room: the guard at 5,6, before the hero has left the throne room (THRONE_ROOM_KEY_ADVICE)
             Told(THRONE_ROOM_KEY_ADVICE, "If thou hast collected all the Treasure Chests,\na key will be found."),
             # Brecconary: the male villager at 20,10; Kol: the guard at 1,23
             Told(0x26, "There is a town where magic keys can be purchased."),
             Told(0x34, "Rimuldar is the place to buy keys."),
             # The key shops in Cantlin, Rimuldar and Tantegel (MagicKeyDialog)
             Told(0x0C), Told(0x0D), Told(0x0E))),
    # The Silver Harp -> the Staff of Rain (RainStaffDialog)
    Goal("silver_harp", "Find the Silver Harp.",
         "It lies deep in Garin's Grave. The way down is behind a locked door in Garinham.",
         done=lambda p: p.has_silver_harp,
         told_by=(
             # Brecconary: the mobile fighter at 3,26; Garinham: the wizard at 14,1
             Told(0x27, "Some say that Garin's grave is home to a Silver Harp."),
             Told(0x3A, "The harp attracts enemies.\nStay away from the grave in Garinham."),
             # The Staff of Rain shrine's old man
             Told(0x6C, "There is a Silver Harp that beckons to the creatures of the Dragonlord."))),
    Goal("staff_of_rain", "Take the Silver Harp to the old man in the shrine.",
         "The shrine is north and west of Kol. He gives the Staff of Rain for the harp.",
         done=lambda p: p.has_staff_of_rain,
         told_by=(Told(0x6C, "Bring this to me and I will reward thee with the Staff of Rain."),)),
    Goal("stones_of_sunlight", "Find the Stones of Sunlight.",
         "They are in the cellar of Tantegel Castle, behind a locked door.",
         done=lambda p: p.has_stones_of_sunlight,
         # Rimuldar: the mobile guard at 8,16
         told_by=(Told(0x54, "Thou shalt find the Stones of Sunlight in Tantegel Castle,\nif thou has not found them "
                             "yet."),)),
    # Erdrick's Token: SEARCH on the overworld (hidden_items), hinted by the Cantlin wizard (ErdTknDialog)
    Goal("erdricks_token", "Find Erdrick's Token.",
         "From Tantegel Castle travel 70 leagues to the south and 40 to the east, and search.",
         done=lambda p: p.has_erdricks_token,
         told_by=(
             # Brecconary, Kol and Rimuldar: the mobile villagers who ask for proof
             Told(0x30, "Art thou the descendant of Erdrick?\nHast thou any proof?"),
             # Cantlin: the wizard at 15,16, and the mobile wizard at 14,28 he sends the hero to
             Told(0x46, "To learn how proof may be obtained that thy ancestor was the great Erdrick, see a man in "
                        "this very town."),
             Told(0x6B, "From Tantegel Castle travel 70 leagues to the south and 40 to the east."),
             # The Rainbow Drop shrine's old man, to a hero without the token (RnbwDrpDialog)
             Told(0x6D, "In thy task thou hast failed. Alas, I fear thou art not the one Erdrick predicted would "
                        "save us."))),
    # The three items -> the Rainbow Drop (RnbwDrpDialog)
    Goal("rainbow_drop", "Take the Stones of Sunlight, the Staff of Rain and Erdrick's Token to the old man in the shrine.",
         "The shrine is far to the south of Rimuldar. He gives the Rainbow Drop.",
         done=lambda p: p.has_rainbow_drop,
         short_text="Get the Rainbow Drop.",
         told_by=(
             # Tantegel: the female villager at 27,5
             Told(0x1A, "When the sun and rain meet, a Rainbow Bridge shall appear."),
             # Rimuldar: the wizard at 3,23: what he says depends on the answer
             Told(0x61),
             # The Rainbow Drop shrine's old man: what he says depends on what the hero holds
             Told(0x6D))),
    # The bridge: NES F_RNBW_BRDG
    Goal("rainbow_bridge", "Use the Rainbow Drop to make a bridge to Charlock.",
         "Hold it up at the water's edge east of Charlock, on the western shore of Rimuldar's land.",
         done=lambda p: p.bridge_built,
         found_out=lambda p: p.has_rainbow_drop,
         told_by=(
             Told(0x1A, "When the sun and rain meet, a Rainbow Bridge shall appear."),
             # Rimuldar: the wizard at 6,13
             Told(0x53, "Over the western part of this island Erdrick created a rainbow."))),
    # Charlock: NES F_PSG_FOUND, then F_DGNLRD_DEAD
    Goal("charlock_passage", "Find the hidden way down in Charlock.",
         "Search behind the Dragonlord's throne.",
         done=lambda p: p.flags.charlock_stairs_revealed or p.dragonlord_defeated,
         told_by=(Told(0x53, "ʼTis also said that he entered the darkness from a hidden entrance in the room of the "
                             "Dragonlord."),)),
    Goal("dragonlord", "Defeat the Dragonlord.",
         "He waits in the deepest part of Charlock.",
         done=lambda p: p.dragonlord_defeated,
         # Every new quest starts with King Lorik's speech, before the hero can leave the throne room
         found_out=lambda p: p.flags.left_throne_room,
         told_by=(
             Told(KING_OPENING_SPEECH, "The Dragonlord must be defeated."),
             # Brecconary: the mobile male villager at 25,22 (the line ends in a comma)
             Told(0x31),
             # Rimuldar: the mobile fighters at 23,11 and 5,25; Cantlin: the mobile guard at 5,6
             Told(0x52, "The scales of the Dragonlord are as hard as steel."),
             Told(0x5B, "In this world is there any sword that can pierce the scales of the Dragonlord?"),
             Told(0x60),
             # The Dragonlord himself
             Told(0x70))),
    Goal("return_to_lorik", "Return to King Lorik.",
         "Tantegel Castle awaits thy return.",
         done=never,
         found_out=lambda p: p.dragonlord_defeated),
    # Optional: the NES never asks for these
    Goal("erdricks_armor", "Find Erdrick's Armor.",
         "It is hidden in the ruins of Hauksness, far to the south. Beware its guardian.",
         done=lambda p: p.armor == "Erdrick's Armor",
         told_by=(
             # Garinham: the mobile wizard at 12,8; Cantlin: the mobile guard at 22,9 and the mobile shopkeepers at
             # 25,17 and 3,26
             Told(0x3F, "They say that Erdrick's armor was hidden long ago."),
             Told(0x4D, "It is said that many have held Erdrick's armor."),
             Told(0x4C, "Grandfather used to say that his friend, Wynn, had buried something of great value at the "
                        "foot of a tree behind his shop."),
             Told(0x4E, "My Grandfather Wynn once had a shop on the east side of Hauksness.")),
         missed=after_the_dragonlord,
         optional=True),
    Goal("erdricks_sword", "Find Erdrick's Sword.",
         "It lies deep within Charlock.",
         done=lambda p: p.weapon == "Erdrick's Sword",
         told_by=(
             # Cantlin: the wizard at 22,22
             Told(0x47, "ʼTis said that Erdrick's sword could cleave steel."),
             # Kol: the wizard at 1,1 (ChkWeaponDialog): his words name the hero
             Told(0x68)),
         missed=after_the_dragonlord,
         optional=True),
    Goal("golem", "Defeat the Golem guarding Cantlin.",
         "Golem fears the music of the flute. The Fairy Flute is in Kol, four steps south of the bath.",
         done=lambda p: p.flags.golem_defeated,
         told_by=(
             # Kol: the mobile guard at 12,10, the mobile wizard at 20,8 and the mobile wizard at 2,12 (who asks of the
             # flute)
             Told(0x37, "Golem is afraid of the music of the flute, so ʼtis said."),
             Told(0x39, "In legends it is said that fairies know how to put Golem to sleep."),
             Told(0x5E),
             Told(GOLEM_FIGHT)),
         missed=after_the_dragonlord,
         optional=True),
)


def goals_by_teller(goals: Iterable[Goal]) -> dict[GoalSource, tuple[Goal, ...]]:
    """Who tells of which goals."""
    told_by: dict[GoalSource, tuple[Goal, ...]] = {}
    for goal in goals:
        for told in goal.told_by:
            told_by[told.source] = told_by.get(told.source, ()) + (goal,)
    return told_by


GOALS_TOLD_BY = goals_by_teller(GOALS)

# Shown before the optional goals, when there are any
OPTIONAL_HEADING = "If thou wishest:"
# A goal that's done
DONE_FORMAT = "Done: {}"
# Shown when the hero knows of no goal
NOTHING_HEARD = "Thou hast heard of nothing yet."


def hear(flags: StoryFlags, source: GoalSource | None) -> None:
    """The hero has just been told something by ``source`` (an NPC's dialog byte, KING_OPENING_SPEECH or GOLEM_FIGHT):
    remember each goal it tells of. The first teller is kept, unless it had no words to show and this one has."""
    if source is None or (source == THRONE_ROOM_KEY_ADVICE and flags.left_throne_room):
        return
    for goal in GOALS_TOLD_BY.get(source, ()):
        told_before = flags.heard_goals.get(goal.key)
        if told_before is None or (goal.line_from(told_before) is None and goal.line_from(source) is not None):
            flags.heard_goals[goal.key] = source


def open_goals(progress: Progress, goals: Iterable[Goal] = GOALS) -> list[Goal]:
    """The known goals not done yet, the main quest's first, each in table order."""
    open_ones = [goal for goal in goals if goal.is_open(progress)]
    return [goal for goal in open_ones if not goal.optional] + [goal for goal in open_ones if goal.optional]


def done_goals(progress: Progress, goals: Iterable[Goal] = GOALS) -> list[Goal]:
    """The known goals done, in table order."""
    return [goal for goal in goals if goal.is_done(progress)]


def journal_pages(progress: Progress, hints: bool, _: Callable[[str], str] = str) -> list[str]:
    """A dialog box page per open goal, with hints followed by a page of what was said of it, then a page per goal
    done; NOTHING_HEARD if there are none. The first optional goal starts with OPTIONAL_HEADING. ``_`` translates them
    (set_gettext_language)."""
    pages = []
    open_ones = open_goals(progress)
    first_optional = next((goal for goal in open_ones if goal.optional), None)
    for goal in open_ones:
        text = _(goal.text)
        pages.append(_(OPTIONAL_HEADING) + "\n" + text if goal is first_optional else text)
        if hints:
            pages.append(_(goal.hint_for(progress)))
    pages += [_(DONE_FORMAT).format(_(goal.done_text)) for goal in done_goals(progress)]
    return pages or [_(NOTHING_HEARD)]


def game_progress(game) -> Progress:
    player = game.player
    return Progress.of(game.story_flags, player.inventory, player.weapon, player.armor)


def journal_texts() -> list[str]:
    """Every text of its own the journal can show, for the translation catalog (catalog_tools.dynamic_messages). The
    NPCs' words (Told.line) are the dialog table's, translated with it."""
    return [OPTIONAL_HEADING, DONE_FORMAT, NOTHING_HEARD] + [
        text for goal in GOALS for text in (goal.text, goal.hint, goal.short_text) if text is not None]


def told_lines() -> list[str]:
    """Every NPC line the journal can show as a hint."""
    return sorted({told.line for goal in GOALS for told in goal.told_by if told.line is not None})
