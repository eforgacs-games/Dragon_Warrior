"""The cursor of the NES selection windows (Bank01 WndDoSelect and the routines after it).

Every selection window (the COMMAND windows, SPELL, ITEM, the shops, BUY/SELL, YES/NO, the title menus and the
alphabet) shows the same cursor: the right pointing arrow tile, TL_RIGHT_ARROW ($42), in the tile before the selected
entry (the window data's cursor home X). It is a background tile like the window's text, so it is drawn in the
window color, color 1 of background palette 0, which turns red at low HP (AddPalByte, ChkLowHPPal).

It blinks off the frame counter (UpdateCursorGFX, called every frame by WndGetButtons): the arrow is shown while
FrameCounter AND #$1F is below #$10 and replaced by TL_BLANK_TILE1 while it isn't, so 16 frames on and 16 off.
WndInitSelect sets FrameCounter to 5 when the window opens, and WndUpdateCrsrPos sets it to 5 again whenever the
cursor moves, so a new window or a moved cursor always starts visible, for the 11 frames left of the "on" half.

When A or B is pressed (WndAPressed, WndBPressed), WndUpdateCrsrPos draws the arrow one last time and the selection
loop ends, so nothing redraws that tile any more: the chosen entry's arrow stays on, without blinking, while the
window stays on the screen (behind the windows the selection opens, for example).
"""
from pygame import Rect, Surface

from src.color import BLACK
from src.waiting import NES_FPS, game_ticks as get_ticks  # game time: runs N times as fast at speed N

# TL_RIGHT_ARROW ($42), as the NES draws it: 8x8 pixels, its point 2 pixels in from the tile's left edge and one row
# lower than the letters (which use rows 0 to 6), so it lines up with the middle of the entry's text.
CURSOR_TILE = (
    "........",
    "..#.....",
    "..##....",
    "..###...",
    "..####..",
    "..###...",
    "..##....",
    "..#.....",
)
# UpdateCursorGFX: AND #$1F, CMP #$10
CURSOR_BLINK_MASK = 0x1F
CURSOR_HIDDEN_FROM = 0x10
# WndInitSelect and WndUpdateCrsrPos: LDA #$05, STA FrameCounter
CURSOR_RESET_FRAME = 0x05

# Defines.asm: the joypad buttons, as bits of JoypadBtns
IN_A = 0x01
IN_B = 0x02
IN_SELECT = 0x04
IN_START = 0x08
IN_UP = 0x10
IN_DOWN = 0x20
IN_LEFT = 0x40
IN_RIGHT = 0x80
# WndProcessInput: the order its LSRs test the buttons in; the first one pressed is the only one handled
WND_PROCESS_ORDER = (IN_A, IN_B, IN_UP, IN_DOWN, IN_LEFT, IN_RIGHT)
# WndGetButtons: LDA FrameCounter, AND #$0F: the retrigger times out when this is 0
RETRIGGER_FRAME_MASK = 0x0F


# The dialog's down arrow (TxtWaitAnim) blinks on the frame count too: on for this many frames, then off as long. 32
# frames is 533 ms at normal speed, about the 530 ms real-time timer (USEREVENT arrow_fade) it used to blink on.
DIALOG_ARROW_BLINK_FRAMES = 32


def dialog_arrow_visible(ticks: int | None = None) -> bool:
    """Whether the dialog's down arrow is on now. It counts NES frames of game time (src/waiting.py game_ticks), like
    BlinkingCursor, so it blinks N times as fast at game speed N, together with everything else."""
    now = get_ticks() if ticks is None else ticks
    return now * NES_FPS // 1000 // DIALOG_ARROW_BLINK_FRAMES % 2 == 0


def cursor_visible_on_frame(frame_counter: int) -> bool:
    """UpdateCursorGFX: whether the arrow (rather than a blank tile) is drawn on this value of FrameCounter."""
    return frame_counter & CURSOR_BLINK_MASK < CURSOR_HIDDEN_FROM


class BlinkingCursor:
    """A selection window's cursor blink, timed like the NES frame counter (see the module docstring).

    restart() is WndInitSelect/WndUpdateCrsrPos (the window opened, or the cursor moved); hold() is the last
    WndUpdateCrsrPos of WndAPressed/WndBPressed, after which the arrow stays on."""

    def __init__(self, ticks: int | None = None):
        self.start_ticks = 0
        self.held = False
        self.restart(ticks)

    def restart(self, ticks: int | None = None) -> None:
        """FrameCounter = 5: the arrow is on, and stays on for the rest of the 16 frame "on" half (11 frames)."""
        self.start_ticks = get_ticks() if ticks is None else ticks
        self.held = False

    def hold(self) -> None:
        """A or B was pressed: the arrow is drawn and stays on until the window is opened again (restart)."""
        self.held = True

    def frames_since_restart(self, ticks: int | None = None) -> int:
        """How many NES frames (WaitForNMI) have gone by since the cursor was restarted: how many frame boundaries
        (every 1/60 s, counted from tick 0, like the NES's VBlanks) have been crossed, so consecutive frames are
        counted exactly, however the milliseconds round."""
        now = get_ticks() if ticks is None else ticks
        return max(0, now * NES_FPS // 1000 - self.start_ticks * NES_FPS // 1000)

    def frame_counter(self, ticks: int | None = None) -> int:
        """The NES FrameCounter: 5 when the cursor was restarted, plus one per NES frame since (it is one byte)."""
        return (CURSOR_RESET_FRAME + self.frames_since_restart(ticks)) & 0xFF

    def visible(self, ticks: int | None = None) -> bool:
        return self.held or cursor_visible_on_frame(self.frame_counter(ticks))


class SelectionButtons:
    """How a selection window reads the joypad: Bank01 WndDoSelect, WndGetButtons and WndProcessInput.

    The window doesn't queue key presses: once per frame (WaitForNMI) it reads the buttons held right now
    (GetJoypadStatus) and acts on them, or not, depending on WndBtnRetrig:

    - WndProcessInput handles one button per press, in the order A, B, up, down, left, right (SELECT and START are
      skipped), and sets WndBtnRetrig to it. While WndBtnRetrig is set, no button at all is read.
    - WndGetButtons clears WndBtnRetrig on a frame that starts with no button held (JoypadBtns, as last read, is 0),
      or on any frame where FrameCounter AND #$0F is 0. So a tap is read once, the moment it is pressed, and a held
      button is read again 11 frames after the cursor moved (WndUpdateCrsrPos sets FrameCounter to 5, and it is
      cleared at 16) or every 16 frames while it doesn't move. Buttons pressed while it is set are only seen then.
    - WndDoSelect opens the window with WndBtnRetrig and JoypadBtns set to IN_RIGHT (and WndInitSelect sets
      FrameCounter to 5), so a button held since before the window opened (from the walk into the fight, say) is
      ignored until it has been let go, or for the first 11 frames if it never is. Anything pressed before the
      window opened is gone: the NES has no event queue.

    The game loop doesn't run in step with the NES frames, so read() catches up on the frames since it last ran: the
    buttons it was given last time are taken to have stayed held until the last of those frames, which sees the new
    ones. Presses given between frames are kept for the next frame, so a tap shorter than a frame isn't lost.
    """

    def __init__(self, cursor: BlinkingCursor):
        self.cursor = cursor
        self.retrigger = 0  # WndBtnRetrig
        self.joypad = 0  # JoypadBtns, as last read
        self.frames_read = 0  # frames since the cursor's restart that read() has gone through
        self.last_held = 0  # the buttons read() was given last
        self.taps = 0  # buttons pressed since the last frame read
        self.open()

    def open(self, held: int = 0, ticks: int | None = None) -> None:
        """WndDoSelect: WndInitSelect (FrameCounter = 5, the cursor drawn), then WndBtnRetrig = JoypadBtns =
        IN_RIGHT. ``held`` is the buttons held as the window opens."""
        self.cursor.restart(ticks)
        self.retrigger = IN_RIGHT
        self.joypad = IN_RIGHT
        self.frames_read = 0
        self.last_held = held
        self.taps = 0

    def read(self, held: int, taps: int = 0, ticks: int | None = None) -> int:
        """WndGetButtons, run for every NES frame since the last read: the buttons the window acts on
        (WndBtnPresses), or 0 if none yet.
        :param held: The buttons held right now.
        :param taps: Buttons pressed since the last read, even if they have been let go already.
        """
        self.taps |= taps
        frames = self.cursor.frames_since_restart(ticks)
        while self.frames_read < frames:
            self.frames_read += 1
            last_frame = self.frames_read == frames
            frame_counter = (CURSOR_RESET_FRAME + self.frames_read) & 0xFF
            # LDA JoypadBtns, BEQ SetRetrigger; LDA FrameCounter, AND #$0F, BNE NoRetrigger
            if not self.joypad or not frame_counter & RETRIGGER_FRAME_MASK:
                self.retrigger = 0
            # GetJoypadStatus
            self.joypad = held | self.taps if last_frame else self.last_held
            if last_frame:
                self.taps = 0
            if self.retrigger:  # LDA WndBtnRetrig, BNE WndGetButtons
                continue
            # (WndBtnRetrig AND JoypadBtns) EOR JoypadBtns: WndBtnRetrig is 0 here, so every button held counts
            if self.joypad:
                if last_frame:
                    self.last_held = held
                return self.joypad
        self.last_held = held
        return 0

    def handled(self, button: int) -> None:
        """WndAPressed, WndBPressed, WndUpPressed...: the button just handled can't be read again until it is let
        go or the retrigger times out (STA WndBtnRetrig)."""
        self.retrigger = button

    def moved(self, ticks: int | None = None) -> None:
        """WndUpdateCrsrPos: FrameCounter = 5 (the arrow restarts visible), then one more WaitForNMI, a frame in
        which the joypad isn't read."""
        self.cursor.restart(ticks)
        self.frames_read = 1


def first_button(presses: int) -> int:
    """WndProcessInput: the one button of ``presses`` the window acts on (0 for none, or only SELECT/START)."""
    return next((button for button in WND_PROCESS_ORDER if presses & button), 0)


def draw_cursor_tile(screen: Surface, x: float, y: float, nes_pixel: int, color: tuple, visible: bool = True) -> Rect:
    """Draw the cursor's tile, the arrow or (not visible) a blank tile, the way UpdateCursorGFX writes either
    TL_RIGHT_ARROW or TL_BLANK_TILE1 into the window.
    :param screen: Where to draw.
    :param x: The tile's left edge, in screen pixels.
    :param y: The tile's top edge, in screen pixels.
    :param nes_pixel: The size of one NES pixel in screen pixels (SCALE).
    :param color: The window color.
    :param visible: Whether to draw the arrow, or only blank the tile.
    :return: The tile's rect, for display.update.
    """
    tile_rect = Rect(int(x), int(y), 8 * nes_pixel, 8 * nes_pixel)
    screen.fill(BLACK, tile_rect)
    if visible:
        for row, line in enumerate(CURSOR_TILE):
            for column, pixel in enumerate(line):
                if pixel == '#':
                    screen.fill(color, (tile_rect.x + column * nes_pixel, tile_rect.y + row * nes_pixel,
                                        nes_pixel, nes_pixel))
    return tile_rect
