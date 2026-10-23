"""The NES dialog window's text buffer: where each character lands, when the window scrolls, and which characters
make the text beep. This is the layout and timing half of dialog text; CommandMenu (src/menu.py) draws it.

Everything here follows the dialog engine in Bank01 of the disassembly (DoDialog and the routines it calls):

- The window holds 8 rows of 22 characters (DialogOutBuf, $B0 bytes; DialogToScreenBuf: "Total rows=8",
  "Total columns = 22"). Opening a dialog window clears it and puts the cursor at the top left (ShowWindow,
  WND_DIALOG: ClearDialogOutBuf, WndTxtXCoord = WndTxtYCoord = 0).
- Words wrap whole: if a word's last character would land past column 21, it starts on the next row
  (CalcWordCoord / CheckForNewLine). A blank at the start of a row is dropped (TextToPPU: CheckXCoordIndent).
- Moving past the last row scrolls the window up one row; the top row drops off and the cursor stays on the
  bottom row (MoveToNextLine -> ScrollDialog -> Scroll1Line). Nothing else clears it until the window closes.
- An open quote turns on a one-column indent (GetTxtWord: TxtSetIndent): the quote sits in column 0, the text and
  every wrapped row start in column 1 (TextToPPU, LineDone).
- Each character waits MessageSpeed + 1 frames (TextToPPU: "LDX MessageSpeed / WaitForNMI / DEX / BPL").
- The text sound plays only for indented (quoted) text, only for printable characters (not blanks), and only in
  odd columns, so every other column (TextToPPU: "Only play text SFX every other printable character").
- A period followed by the closing quote is one tile, TXT_PRD_QUOTE ($52), so it takes one column, one character's
  wait and at most one beep.
- A wait (the down arrow) first moves to a new row, shows the arrow there, and after the button press the text
  continues on that row if indented, or one row further down if not (WaitFound, DoWait). The end of a message
  moves to a new row and back to column 0 (DialogEndFound).
"""
import re
from dataclasses import dataclass
from collections.abc import Iterator

DIALOG_ROWS = 8  # DialogToScreenBuf: "Total rows=8"
DIALOG_COLUMNS = 22  # CalcWndYByteNum: "22 text characters per line"
ARROW_COLUMN = 11  # TxtWaitAnim: the arrow goes in screen column $10; dialog columns start at screen column 5

# MessageSpeed: #$00-fast, #$01-normal, #$02-slow (MSG_FAST, MSG_NORMAL, MSG_SLOW)
MESSAGE_SPEEDS = {'Fast': 0, 'Normal': 1, 'Slow': 2}
# ScrollDialog: one WaitForNMI, then Display2ScrollLines (two rows and a WaitForNMI each) until all 8 rows are done
SCROLL_ROWS_PER_FRAME = 2
SCROLL_FRAMES = 1 + DIALOG_ROWS // SCROLL_ROWS_PER_FRAME

OPEN_QUOTES = ('`', "'", '‘', '“')
BLANK = ' '
PERIOD_END_QUOTE = '.’'  # TXT_PRD_QUOTE ($52): one tile, '.'' in the disassembly's text comments


def tiles(word: str) -> list[str]:
    """Splits text into the tiles it takes on screen: one per character, except a period and closing quote together."""
    return re.findall(re.escape(PERIOD_END_QUOTE) + '|.', word)


def frames_per_character(text_speed: str) -> int:
    """TextToPPU waits MessageSpeed + 1 frames after each character (the DEX/BPL loop runs MessageSpeed + 1 times).
    Unknown settings fall back to Normal, the speed a new game starts with (NewQuest: MSG_NORMAL)."""
    return MESSAGE_SPEEDS.get(text_speed, MESSAGE_SPEEDS['Normal']) + 1


def plays_text_beep(char: str, column: int, indented: bool) -> bool:
    """TextToPPU's text SFX check: only with an indent active (quoted text), only for a printable character
    (anything below TL_BLANK_TILE1), and only when WndTxtXCoord is odd (LSR / BCC skips even columns)."""
    return indented and char != BLANK and column % 2 == 1


@dataclass(frozen=True, slots=True)
class CharacterStep:
    """One character written to the window (one TextToPPU call that reaches the PPU)."""
    row: int
    column: int
    char: str  # the tile's text: one character, or two for PERIOD_END_QUOTE
    beep: bool


@dataclass(frozen=True, slots=True)
class ScrollStep:
    """The window scrolled up one row (ScrollDialog)."""


DialogStep = CharacterStep | ScrollStep


class DialogBuffer:
    """The NES dialog window's 8x22 text buffer (DialogOutBuf) and text cursor (WndTxtXCoord, WndTxtYCoord).

    The methods that move the cursor are generators: they change the buffer as they go and yield a step for each
    thing the screen has to show, so the caller can draw and time each one. Use ``list(...)`` to apply them
    without drawing."""

    def __init__(self) -> None:
        self.rows: list[list[str]] = []
        self.row = 0
        self.column = 0
        self.indent = 0
        self.clear()

    def clear(self) -> None:
        """ShowWindow for WND_DIALOG: ClearDialogOutBuf, and the cursor goes back to the top left."""
        self.rows = [[BLANK] * DIALOG_COLUMNS for _ in range(DIALOG_ROWS)]
        self.row = 0
        self.column = 0
        self.indent = 0

    @property
    def lines(self) -> list[str]:
        """The text of each of the 8 rows, top to bottom, without trailing blanks."""
        return [''.join(row).rstrip() for row in self.rows]

    @property
    def visible_lines(self) -> list[str]:
        """The rows that have text on them, top to bottom."""
        return [line for line in self.lines if line]

    def print_message(self, text: str, quoted: bool) -> Iterator[DialogStep]:
        """Print one message (DoDialog's CalcWordCoord/WordToScreen loop). ``quoted`` text starts with an open quote,
        which turns on the indent (GetTxtWord: TxtSetIndent). A "\\n" is a TXT_NEWL (DoNewline)."""
        self.indent = 1 if quoted else 0
        first_char = True
        for paragraph_index, paragraph in enumerate(text.split('\n')):
            if paragraph_index:
                yield from self.do_newline()
            for token in re.findall(r' |[^ ]+', paragraph):
                if token == BLANK:
                    yield from self._put_blank()
                    first_char = False
                    continue
                word = tiles(token)
                # CalcWordCoord / CheckForNewLine: the whole word moves down if its last character would pass the edge
                if self.column + len(word) > DIALOG_COLUMNS and self.column > self.indent:
                    yield from self.move_to_next_line()
                for char in word:
                    if first_char and quoted and char in OPEN_QUOTES and self.column == 1:
                        # TextToPPU: an open quote at the indent moves back a column, so the text lines up after it
                        self.column = 0
                    first_char = False
                    yield from self._put(char)

    def end_message(self) -> Iterator[DialogStep]:
        """DialogEndFound: move to a new row (if anything is on this one) and back to column 0."""
        yield from self.do_newline()
        self.column = 0

    def start_wait(self) -> Iterator[DialogStep]:
        """WaitFound: move to a new row; the down arrow blinks there (TxtWaitAnim uses WndTxtYCoord)."""
        yield from self.do_newline()

    def finish_wait(self) -> Iterator[DialogStep]:
        """After the button press (DoWait: TxtBtnPressed): continue at the indent on the arrow's row, or, without an
        indent, leave that row blank and continue on the next one (WaitFound: MoveToNextLine)."""
        self.column = self.indent
        if not self.indent:
            yield from self.move_to_next_line()

    def do_newline(self) -> Iterator[DialogStep]:
        """DoNewline: go to the next row, unless the cursor is already at the start of one."""
        if self.column != 0:
            yield from self.move_to_next_line()

    def move_to_next_line(self) -> Iterator[DialogStep]:
        """MoveToNextLine: down one row, scrolling the window up once the cursor would pass the last row (CPX #$08),
        then back to the indent (LineDone)."""
        if self.row + 1 >= DIALOG_ROWS:
            self._scroll()
            yield ScrollStep()
        else:
            self.row += 1
        self.column = self.indent

    def _scroll(self) -> None:
        """Scroll1Line: every row moves up one; the top row drops off and the bottom row is cleared."""
        self.rows = self.rows[1:] + [[BLANK] * DIALOG_COLUMNS]

    def _put_blank(self) -> Iterator[DialogStep]:
        if self.column >= DIALOG_COLUMNS:  # TextToPPU -> CheckForNewLine
            yield from self.move_to_next_line()
        if self.column == self.indent:
            return  # TextToPPU: CheckXCoordIndent, a blank at the start of a row is skipped (and takes no time)
        yield from self._put(BLANK)

    def _put(self, char: str) -> Iterator[DialogStep]:
        if self.column >= DIALOG_COLUMNS:  # TextToPPU -> CheckForNewLine, for a word longer than a whole row
            yield from self.move_to_next_line()
        self.rows[self.row][self.column] = char
        yield CharacterStep(self.row, self.column, char, plays_text_beep(char, self.column, bool(self.indent)))
        self.column += 1
