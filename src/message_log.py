"""The message log: the last dialog lines shown, to read again. Not on the NES.

Every message the dialog window prints on the map (CommandMenu.show_text_line_in_dialog_box) is kept here, up to
``MAX_ENTRIES``, the oldest dropped first: what the NPCs say, with who said it, and what the hero reads or finds. A
fight's messages aren't kept (they would push the hints out), and nor are the short messages the game shows over the
map for a moment (the game speed, a save state).

The MESSAGE LOG key (L, as bound, src/controls.py) opens the log on the map, when the MESSAGE LOG option is ON (the
options overlay; OFF is the NES, which has none). Like the options overlay, it opens only when START would pause the
game, once the hero and the NPCs have finished their steps (Game.handle_message_log_key,
MovementController.resolve_pending_freezes). One NES-style window fills the screen, titled MESSAGE LOG, the newest
message at the bottom:

    +--MESSAGE LOG----------------------+
    | GUARD: `Welcome to Tantegel       |
    |   Castle.'                        |
    | ...                               |
    |                                   |
    | UP/DOWN:SCROLL  B:CLOSE           |
    +-----------------------------------+

Each message is wrapped to the window, a speaker's name before what they said; up and down scroll a line, left and
right a page. B, Esc, START or the MESSAGE LOG key close it, and the map is put back as it was. Its loop is the only
one running while it's open, so the map, the NPCs and the timers wait, as they do for the options overlay.
"""
import re
import unicodedata
from collections import deque
from collections.abc import Callable, Iterable
from typing import NamedTuple

from pygame import K_ESCAPE, K_DOWN, K_LEFT, K_RIGHT, K_UP, KEYDOWN, Rect, Surface, display

from src.common import B_BUTTON_KEYS, DOWN_KEYS, LEFT_KEYS, RIGHT_KEYS, START_BUTTON_KEYS, UP_KEYS, \
    set_gettext_language
from src.controls import KeySet
from src.cursor import BlinkingCursor
from src.options_overlay import darken
from src.selection import frame_events, next_frame
from src.translated_window import draw_translated_window
from src.windows import Window, WindowLayout, WindowText

MAX_ENTRIES = 50

# The whole screen: 16 blocks wide and 15 high
LOG_WINDOW = Window(0, 0, 16, 15)
LOG_TITLE = WindowText("MESSAGE LOG", 4, 0)
TEXT_COLUMN = 2
FIRST_ROW = 2
VISIBLE_LINES = 12  # double spaced, from tile row 2 to 24
HINT_ROW = 27
LINE_WIDTH = 28  # tiles, from column 2 to inside the right border
CONTINUATION_INDENT = 2  # a message's later lines start under its text, after the speaker
HINT = "UP/DOWN:SCROLL  B:CLOSE"
EMPTY = "NO MESSAGES YET"

LOG_KEYS = KeySet('MESSAGE_LOG')
CLOSE_KEYS = B_BUTTON_KEYS + START_BUTTON_KEYS + LOG_KEYS + (K_ESCAPE,)

# A speaker's name, by the NPC's sprite (src/maps.py NPC tables)
SPEAKERS = {
    'KING_LORIK': "KING LORIK", 'PRINCESS_GWAELIN': "GWAELIN", 'DRAGONLORD': "DRAGONLORD", 'GUARD': "GUARD",
    'SOLDIER': "SOLDIER", 'MERCHANT': "MERCHANT", 'MAN': "MAN", 'WOMAN': "WOMAN", 'WISE_MAN': "WISE MAN",
}


class LogEntry(NamedTuple):
    """A message as it was shown (translated), and who said it (a SPEAKERS key, or None)."""
    text: str
    speaker: str | None = None


def speaker_of(character: str | None) -> str | None:
    """The speaker an NPC is shown as ("MAN_2" is a MAN), or None for one with no name here."""
    if not character:
        return None
    sprite = re.sub(r'_?\d+$', '', character)
    return sprite if sprite in SPEAKERS else None


class MessageLog:
    """The messages, oldest first."""

    def __init__(self, size: int = MAX_ENTRIES):
        self.entries: deque[LogEntry] = deque(maxlen=size)

    def record(self, text: str, speaker: str | None = None) -> None:
        text = ' '.join(text.split())  # one line: the window wraps it again
        if text:
            self.entries.append(LogEntry(text, speaker))

    def clear(self) -> None:
        self.entries.clear()

    def to_save(self) -> list[list[str | None]]:
        """The messages as JSON values, oldest first: [text, speaker] each (a save state, src/save_state.py)."""
        return [[entry.text, entry.speaker] for entry in self.entries]

    def restore(self, entries: Iterable[LogEntry]) -> None:
        """Put back the messages a snapshot kept (decoded_entries), in place of the ones there now."""
        self.entries.clear()
        self.entries.extend(entries)

    def __len__(self) -> int:
        return len(self.entries)


def decoded_entries(saved: Iterable[Iterable[str | None]]) -> list[LogEntry]:
    """MessageLog.to_save's messages read back, checked: a speaker that isn't a string is none. Raises ValueError for
    an entry that isn't a [text, speaker] pair."""
    entries = []
    for text, speaker in saved:
        if not isinstance(text, str):
            raise ValueError(f"not a message: {text!r}")
        entries.append(LogEntry(text, speaker if isinstance(speaker, str) else None))
    return entries


def text_width(text: str) -> int:
    """How many NES tiles the text takes: Hangul and other wide characters take two (Unifont)."""
    return sum(2 if unicodedata.east_asian_width(character) in ('W', 'F') else 1 for character in text)


def wrap(text: str, width: int, indent: int = 0) -> list[str]:
    """The text in lines of at most ``width`` tiles, broken between words (a word too long for a line is cut), every
    line after the first starting ``indent`` blanks in."""
    lines: list[str] = []
    line = ''
    for word in text.split(' '):
        candidate = f'{line} {word}' if line else word
        limit = width - (indent if lines else 0)
        if text_width(candidate) <= limit:
            line = candidate
            continue
        if line:
            lines.append(line)
        line = word
        while text_width(line) > width - (indent if lines else 0):
            cut = len(line)
            while text_width(line[:cut]) > width - (indent if lines else 0):
                cut -= 1
            lines.append(line[:cut])
            line = line[cut:]
    if line:
        lines.append(line)
    return [(' ' * indent if number else '') + text for number, text in enumerate(lines)]


def log_lines(entries: Iterable[LogEntry], translate: Callable[[str], str]) -> list[str]:
    """Every message, wrapped to the window, oldest first: the speaker's name, a colon and what was said."""
    lines: list[str] = []
    for entry in entries:
        text = f'{translate(SPEAKERS[entry.speaker])}: {entry.text}' if entry.speaker in SPEAKERS else entry.text
        lines += wrap(text, LINE_WIDTH, CONTINUATION_INDENT)
    return lines


def log_layout(lines: list[str], top: int, hint: str = HINT) -> WindowLayout:
    """The window with the lines from ``top``."""
    shown = lines[top:top + VISIBLE_LINES] or [EMPTY]
    texts = tuple(WindowText(line, TEXT_COLUMN, FIRST_ROW + 2 * number) for number, line in enumerate(shown) if line)
    return WindowLayout(window=LOG_WINDOW, title=LOG_TITLE, texts=texts + (WindowText(hint, TEXT_COLUMN, HINT_ROW),))


def screen_texts() -> list[str]:
    """The text the log shows besides the messages, for the translation catalog."""
    return [LOG_TITLE.text, HINT, EMPTY, *SPEAKERS.values()]


class MessageLogScreen:
    """The log over the map, run until it's closed (see the module docstring)."""

    def __init__(self, game):
        self.game = game
        self.config: dict = game.game_state.config
        self._: Callable[[str], str] = set_gettext_language(self.config.get('LANGUAGE'))
        self.lines = log_lines(game.message_log.entries, self._)
        self.top = self.last_top()

    def last_top(self) -> int:
        return max(0, len(self.lines) - VISIBLE_LINES)

    def run(self) -> None:
        screen = self.game.screen
        background = screen.copy()
        cursor = BlinkingCursor()  # only for its frame pacing, like the other windows' loops
        drawn: int | None = None
        while True:
            if self.top != drawn:
                self.draw(background)
                drawn = self.top
            cursor.visible()
            next_frame()
            for current_event in frame_events():
                if current_event.type != KEYDOWN:
                    continue
                if self.handle_key(current_event.key):
                    self.close(background)
                    return

    def handle_key(self, pressed_key: int) -> bool:
        """Scroll, or return True to close."""
        if pressed_key in CLOSE_KEYS:
            return True
        if pressed_key in UP_KEYS or pressed_key == K_UP:
            self.top = max(0, self.top - 1)
        elif pressed_key in DOWN_KEYS or pressed_key == K_DOWN:
            self.top = min(self.last_top(), self.top + 1)
        elif pressed_key in LEFT_KEYS or pressed_key == K_LEFT:
            self.top = max(0, self.top - VISIBLE_LINES)
        elif pressed_key in RIGHT_KEYS or pressed_key == K_RIGHT:
            self.top = min(self.last_top(), self.top + VISIBLE_LINES)
        return False

    def draw(self, background: Surface) -> None:
        if self.config.get('NO_BLIT'):
            return
        screen = self.game.screen
        screen.blit(background, (0, 0))
        darken(screen)
        draw_translated_window(screen, log_layout(self.lines, self.top), self.game.color, self.config, self._)
        display.update(Rect(0, 0, screen.get_width(), screen.get_height()))

    def close(self, background: Surface) -> None:
        if self.config.get('NO_BLIT'):
            return
        screen = self.game.screen
        screen.blit(background, (0, 0))
        display.update(Rect(0, 0, screen.get_width(), screen.get_height()))
