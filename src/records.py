"""The quest journal's records (Q on the map, src/quest_journal.py): texts the hero has read or been told once, to
read again. Not on the NES.

The NES has one text that's read rather than said, Erdrick's Tablet, at the bottom of Erdrick's Cave
(ChkTrsrErdTablet), and one speech that's only ever given once, King Lorik's charge as a new quest starts
(MainGameEngine). Both are kept here, and both the game and the journal show them from here, so the journal shows the
same words (and the same translations) as the game did.

A record is known once the hero has had it:
- the tablet: once it's read (CommandMenu.take_tablet adds it to StoryFlags.read_records). A save from before the
  records existed counts it as read if the dungeon map (src/dungeon_map.py) has seen the tablet's chest.
- King Lorik's charge: once it's been given (the quest journal heard it), or once the hero has left the throne room,
  which he can't do without hearing it.

With any record known, Q first opens the JOURNAL window: GOALS (the goals, as before) and each known record. A shows
it, B closes the window. With none known, Q shows the goals at once, as it always has.

    +-JOURNAL-----------+
    | > GOALS           |
    |   ERDRICK'S TABLET|
    |   KING LORIK      |
    +-------------------+
"""
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pygame import display

from src.quest_journal import KING_OPENING_SPEECH
from src.selection import run_selection, stop_at_edges
from src.story_flags import StoryFlags
from src.translated_window import draw_translated_window
from src.windows import Window, WindowLayout, WindowText, selection_cursor_tiles

if TYPE_CHECKING:
    from src.dungeon_map import DungeonMap
    from src.game import Game  # src.game imports this module

Translate = Callable[[str], str]

TABLET = 'tablet'
KING_LORIK_CHARGE = 'king_lorik_charge'

# NES ChkTrsrErdTablet: what the tablet says, after "Thou hast found the Tablet." and TABLET_HEADING
TABLET_HEADING = "The tablet reads as follows:"
TABLET_LINES = (
    "I am Erdrick and thou art my descendant.",
    "Three items were needed to reach the Isle of Dragons, which is south of Brecconary.",
    "I gathered these items, reached the island, and there defeated a creature of great evil.",
    "Now I have entrusted the three items to three worthy keepers.",
    "Their descendants will protect the items until thy quest leads thee to seek them out.",
    "When a new evil arises, find the three items, then fight!",
)
# The tablet's chest (src/items.py treasure), for saves from before the records were kept
TABLET_MAP = 'ErdricksCaveB2'
TABLET_COORDINATES = (4, 10)

# NES MainGameEngine: King Lorik's words as a new quest starts (TextBlock17 entry 2). {} is the hero's name.
KING_LORIK_CHARGE_LINES = (
    "Descendant of Erdrick, listen now to my words.",
    "It is told that in ages past Erdrick fought demons with a Ball of Light.",
    "Then came the Dragonlord who stole the precious globe and hid it in the darkness.",
    "Now, {}, thou must help us recover the Ball of Light and restore peace to our land.",
    "The Dragonlord must be defeated.",
    "Take now whatever thou may find in these Treasure Chests to aid thee in thy quest.",
    "Then speak with the guards, for they have much knowledge that may aid thee.",
    "May the light shine upon thee, {}.",
)


def tablet_lines(_: Translate = str) -> tuple[str, ...]:
    """What the tablet says, translated."""
    return tuple(_(line) for line in TABLET_LINES)


def king_lorik_charge(name: str, _: Translate = str) -> tuple[str, ...]:
    """King Lorik's opening speech to the hero ``name``, translated."""
    return tuple(_(line).format(name) for line in KING_LORIK_CHARGE_LINES)


def tablet_seen_on_dungeon_map(dungeon_map: 'DungeonMap | None') -> bool:
    floor = dungeon_map.floors.get(TABLET_MAP) if dungeon_map is not None else None
    return floor is not None and floor.seen(*TABLET_COORDINATES)


@dataclass(frozen=True, slots=True)
class Record:
    """One record: its key (in StoryFlags.read_records), its name in the JOURNAL window, when the hero knows it and
    its dialog box pages."""
    key: str
    title: str
    known: Callable[[StoryFlags, 'DungeonMap | None'], bool]
    pages: Callable[[str, Translate], tuple[str, ...]]


RECORDS = (
    Record(TABLET, "ERDRICK'S TABLET",
           known=lambda flags, dungeon_map: TABLET in flags.read_records or tablet_seen_on_dungeon_map(dungeon_map),
           pages=lambda name, _: tablet_lines(_)),
    Record(KING_LORIK_CHARGE, "KING LORIK",
           known=lambda flags, dungeon_map: flags.left_throne_room or KING_OPENING_SPEECH in flags.heard_goals.values(),
           pages=king_lorik_charge),
)


def read(flags: StoryFlags, key: str) -> None:
    """The hero has just read the record ``key``."""
    if key not in flags.read_records:
        flags.read_records.append(key)


def known_records(flags: StoryFlags, dungeon_map: 'DungeonMap | None' = None) -> list[Record]:
    return [record for record in RECORDS if record.known(flags, dungeon_map)]


# The JOURNAL window: GOALS, then each known record, one block apart
JOURNAL_TITLE = "JOURNAL"
GOALS_ENTRY = "GOALS"
JOURNAL_WINDOW_X, JOURNAL_WINDOW_Y = 3, 2
JOURNAL_WINDOW_WIDTH = 10  # blocks: the longest entry, ERDRICK'S TABLET, from tile column 2
TEXT_COLUMN = 2


def journal_layout(entries: list[str]) -> WindowLayout:
    """The JOURNAL window with ``entries`` (untranslated), one block per entry plus the borders."""
    window = Window(JOURNAL_WINDOW_X, JOURNAL_WINDOW_Y, JOURNAL_WINDOW_WIDTH, len(entries) + 1)
    return WindowLayout(
        window=window, title=WindowText(JOURNAL_TITLE, 2, 0),
        texts=tuple(WindowText(entry, TEXT_COLUMN, 2 + 2 * number) for number, entry in enumerate(entries)),
        cursor_tiles=selection_cursor_tiles(home_column=1, home_row=2, columns=1, column_spacing=0,
                                            rows=len(entries)))


def choose_journal_page(game: 'Game', records: list[Record]) -> Record | str | None:
    """The JOURNAL window: GOALS_ENTRY for the goals, a record, or None if B closed it."""
    cmd_menu = game.cmd_menu
    config = game.game_state.config
    layout = journal_layout([GOALS_ENTRY] + [record.title for record in records])
    covered = cmd_menu.covered_area(layout.window)

    def draw(index: int, cursor_visible: bool) -> None:
        rect = draw_translated_window(game.screen, layout, game.color, config, cmd_menu._, cursor_index=index,
                                      cursor_visible=cursor_visible)
        if not config.get('NO_BLIT'):
            display.update(rect)

    answer = run_selection(draw, 0, move=stop_at_edges(len(layout.cursor_tiles)),
                           sound=cmd_menu.play_menu_button_sound)
    cmd_menu.remove_window(layout.window, covered)
    if not answer.accepted:
        return None
    return GOALS_ENTRY if answer.entry == 0 else records[answer.entry - 1]


def record_texts() -> list[str]:
    """Every text of the records and the JOURNAL window, for the translation catalog (catalog_tools.dynamic_messages)."""
    return [JOURNAL_TITLE, GOALS_ENTRY, *(record.title for record in RECORDS), TABLET_HEADING, *TABLET_LINES,
            *KING_LORIK_CHARGE_LINES]
