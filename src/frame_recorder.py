"""
A frame recorder for finding visual glitches: it keeps a copy of every frame the game presents, then reports which
frames changed and which ones look like a flicker.

The game presents a frame with ``pygame.display.flip`` or ``pygame.display.update``, called through the ``display``
module everywhere (``from pygame import display``). While a FrameRecorder is recording, those two are replaced on the
``pygame.display`` module with wrappers that copy the picture first; ``stop`` puts the originals back. Nothing is
wrapped while nobody records, so the game runs exactly as before.

What a frame holds is what the player would see after that call. The game's window is always SCALED, and pygame
presents the whole screen surface for every ``update`` on a SCALED display (it's a ``flip`` there), so by default each
frame is the whole screen surface. With ``partial_updates=True``, ``update(rects)`` shows only those parts of it and
the rest stays as the last frame showed it, as on a plain software display. Each frame also keeps when it was
presented (game time), the function that presented it (``caller``, e.g. ``menu.CommandMenu.window_drop_up_effect``)
and the recorder's ``label`` at the time, which a script or test can set to say what it was doing.

A "frame" here is one flip or update. The game draws most frames once each, but holds some pictures with a wait (a
fade step, a blinking cursor) rather than drawing them again, so a frame can stay on screen for longer than 1/60 s.
In a recording made in real time, each frame's time tells them apart (``find_flickers(max_ms=...)``).

Frames are kept compressed in memory (a frame that repeats the one before shares its data), so recording a long scene
costs a few tens of KB per changed frame.

Three ways in:
- Tests: ``with recording() as frames: ...`` then ``assert_no_one_frame_flickers(frames)``.
- Scripts: ``uv run python -m tools.record_frames --checkpoint throne_room --script "wait:600,a,a" --out /tmp/frames``
  (tools/record_frames.py) plays a scripted scene headless and saves the frames and a report.
- Playing with ``--dev``: F8 starts recording and F8 again stops it and saves to FRAME_RECORDINGS_DIR
  (src/debug_tools.py).
"""
import hashlib
import os
import sys
import tempfile
import zlib
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Sequence, overload

from pygame import BLEND_RGB_ADD, BLEND_RGB_SUB, Rect, Surface, display, image, mask

from src.waiting import NES_FPS, game_ticks

# Where F8 in --dev saves its recordings, one folder per recording
FRAME_RECORDINGS_DIR = os.path.join(tempfile.gettempdir(), 'dragon_warrior_frames')

# Sources of the caller to skip when naming who presented a frame
_SKIPPED_MODULES = (__name__, 'pygame')


@dataclass(frozen=True, eq=False)
class Frame:
    """One presented frame: its number in the recording, who presented it and the picture."""
    index: int
    time: int  # game_ticks() when it was presented (game milliseconds)
    caller: str  # module.function that called flip or update
    label: str  # FrameRecorder.label when it was presented
    size: tuple[int, int]
    digest: bytes  # a hash of the picture: two frames show the same picture exactly when their digests match
    compressed: bytes  # the picture, zlib-compressed RGB bytes

    def pixels(self) -> bytes:
        return zlib.decompress(self.compressed)

    def surface(self) -> Surface:
        return image.frombytes(self.pixels(), self.size, 'RGB')

    def same_picture(self, other: 'Frame') -> bool:
        return self.digest == other.digest

    def describe(self) -> str:
        return f"frame {self.index} ({self.caller}{', ' + self.label if self.label else ''})"


def _caller_name() -> str:
    frame: Any = sys._getframe(1)
    while frame is not None and frame.f_globals.get('__name__', '').startswith(_SKIPPED_MODULES):
        frame = frame.f_back
    if frame is None:
        return '?'
    module = frame.f_globals.get('__name__', '?').rsplit('.', 1)[-1]
    return f"{module}.{getattr(frame.f_code, 'co_qualname', frame.f_code.co_name)}"


def _update_rects(args: tuple) -> list[Rect] | None:
    """The rectangles a ``display.update(*args)`` call shows, or None for the whole screen."""
    if not args or args[0] is None:
        return None
    rects = args[0]
    if len(args) == 4 or isinstance(rects, Rect) or (len(rects) == 4 and all(isinstance(n, (int, float)) for n in rects)):
        return [Rect(*args) if len(args) == 4 else Rect(rects)]
    return [Rect(rect) for rect in rects if rect is not None]


class FrameRecorder(Sequence[Frame]):
    """Records every frame presented while it's started. It's a sequence of its frames (``len``, indexing, iterating).

    :param on_frame: Called with each new Frame, after the real flip or update. A script can drive input from it.
    :param max_frames: Stop keeping frames after this many (the game carries on), so a forgotten recording can't eat
        all the memory.
    :param partial_updates: Whether ``update(rects)`` presents only those rectangles (a display that isn't SCALED)
        rather than the whole screen (the game's SCALED display).
    """

    def __init__(self, on_frame: Callable[[Frame], None] | None = None, max_frames: int | None = None,
                 partial_updates: bool = False) -> None:
        self.frames: list[Frame] = []
        self.partial_updates = partial_updates
        self.label = ''
        self.on_frame = on_frame
        self.max_frames = max_frames
        self._presented: Surface | None = None
        self._real_flip: Callable[..., Any] | None = None
        self._real_update: Callable[..., Any] | None = None

    # Starting and stopping

    @property
    def recording(self) -> bool:
        return self._real_flip is not None

    def start(self) -> 'FrameRecorder':
        if self.recording:
            return self
        self._real_flip, self._real_update = display.flip, display.update
        display.flip, display.update = self._flip, self._update  # type: ignore[assignment]
        return self

    def stop(self) -> None:
        if not self.recording:
            return
        display.flip, display.update = self._real_flip, self._real_update  # type: ignore[assignment]
        self._real_flip = self._real_update = None

    def __enter__(self) -> 'FrameRecorder':
        return self.start()

    def __exit__(self, *_exc_info) -> None:
        self.stop()

    # The sequence of frames

    def __len__(self) -> int:
        return len(self.frames)

    def __iter__(self) -> Iterator[Frame]:
        return iter(self.frames)

    @overload
    def __getitem__(self, index: int) -> Frame: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[Frame]: ...

    def __getitem__(self, index):
        return self.frames[index]

    # Recording

    def _flip(self, *args, **kwargs):
        self.capture(None)
        result = self._real_flip(*args, **kwargs)  # type: ignore[misc]
        self._frame_presented()
        return result

    def _update(self, *args, **kwargs):
        self.capture(_update_rects(args) if self.partial_updates else None)
        result = self._real_update(*args, **kwargs)  # type: ignore[misc]
        self._frame_presented()
        return result

    def _frame_presented(self) -> None:
        if self.on_frame is not None and self.frames:
            self.on_frame(self.frames[-1])

    def capture(self, rects: Sequence[Rect] | None = None) -> Frame | None:
        """Record the frame a flip (``rects`` None) or an update of ``rects`` presents now."""
        screen = display.get_surface()
        if screen is None or (self.max_frames is not None and len(self.frames) >= self.max_frames):
            return None
        if rects is None or self._presented is None or self._presented.get_size() != screen.get_size():
            self._presented = screen.copy()
        else:
            for rect in rects:
                self._presented.blit(screen, rect, rect)
        pixels = image.tobytes(self._presented, 'RGB')
        digest = hashlib.blake2b(pixels, digest_size=16).digest()
        last = self.frames[-1] if self.frames else None
        compressed = last.compressed if last is not None and last.digest == digest else zlib.compress(pixels, 1)
        frame = Frame(len(self.frames), game_ticks(), _caller_name(), self.label, self._presented.get_size(), digest,
                      compressed)
        self.frames.append(frame)
        return frame


@contextmanager
def recording(**kwargs) -> Iterator[FrameRecorder]:
    """``with recording() as frames:`` records every frame presented inside the block. Takes FrameRecorder's
    arguments."""
    recorder = FrameRecorder(**kwargs)
    recorder.start()
    try:
        yield recorder
    finally:
        recorder.stop()


# Comparing frames

@dataclass(frozen=True)
class FrameDiff:
    """How one frame differs from the one before it."""
    before: Frame
    after: Frame
    pixels: int  # pixels that changed
    rows: int  # pixel rows with at least one change
    bounds: Rect | None  # the smallest rectangle around every change (None if nothing changed)

    def describe(self) -> str:
        if self.bounds is None:
            return f"{self.after.describe()}: unchanged"
        box = self.bounds
        return (f"{self.after.describe()}: {self.pixels} pixels in {self.rows} rows changed, "
                f"box x={box.x} y={box.y} w={box.width} h={box.height}")


def _region_key(frame: Frame, region: Rect | None) -> bytes:
    if region is None:
        return frame.digest
    return hashlib.blake2b(image.tobytes(frame.surface().subsurface(region), 'RGB'), digest_size=16).digest()


def diff_frames(before: Frame, after: Frame) -> FrameDiff:
    """Count the pixels and rows that changed between two frames, and box them in."""
    if before.same_picture(after):
        return FrameDiff(before, after, 0, 0, None)
    if before.size != after.size:
        width, height = after.size
        return FrameDiff(before, after, width * height, height, Rect(0, 0, width, height))
    before_pixels, after_pixels = before.pixels(), after.pixels()
    width, height = after.size
    pitch = width * 3
    rows = sum(before_pixels[row * pitch:(row + 1) * pitch] != after_pixels[row * pitch:(row + 1) * pitch]
               for row in range(height))
    before_surface = image.frombytes(before_pixels, before.size, 'RGB')
    after_surface = image.frombytes(after_pixels, after.size, 'RGB')
    # |before - after| per channel, from the two saturating subtractions; black where nothing changed
    difference = before_surface.copy()
    difference.blit(after_surface, (0, 0), special_flags=BLEND_RGB_SUB)
    other_way = after_surface.copy()
    other_way.blit(before_surface, (0, 0), special_flags=BLEND_RGB_SUB)
    difference.blit(other_way, (0, 0), special_flags=BLEND_RGB_ADD)
    changed = mask.from_threshold(difference, (0, 0, 0, 255), (1, 1, 1, 255))
    changed.invert()
    boxes: list[Rect] = changed.get_bounding_rects()  # type: ignore[assignment]  # the stub says list[int]
    return FrameDiff(before, after, changed.count(), rows, boxes[0].unionall(boxes[1:]) if boxes else None)


def changes(frames: Sequence[Frame]) -> list[FrameDiff]:
    """The frames that differ from the one before them, with what changed."""
    return [diff_frames(frames[index - 1], frames[index]) for index in range(1, len(frames))
            if not frames[index - 1].same_picture(frames[index])]


@dataclass(frozen=True)
class Flicker:
    """A picture shown for at most a few frames between two frames that show the same picture as each other."""
    before: Frame
    frames: tuple[Frame, ...]  # the odd frames out
    after: Frame

    @property
    def duration_ms(self) -> int:
        """How long the odd picture was on screen, in game milliseconds (0 if nothing waited in between, as with
        NO_WAIT)."""
        return self.after.time - self.frames[0].time

    def describe(self) -> str:
        first, last = self.frames[0], self.frames[-1]
        odd = first.describe() if first is last else f"frames {first.index}-{last.index} ({first.caller})"
        return (f"{odd} differs from frame {self.before.index} before it and frame {self.after.index} after it, "
                f"which match each other; on screen {self.duration_ms} ms")


def find_flickers(frames: Sequence[Frame], max_length: int = 1, region: Rect | None = None,
                  max_ms: float | None = None) -> list[Flicker]:
    """Runs of at most ``max_length`` frames whose picture differs from the frames on either side of them, while those
    two match: something shown for a frame or two that shouldn't have been. With ``region``, only that part of the
    screen is compared (to leave out a blinking cursor elsewhere, say).

    Frames are counted as the game presents them, so a picture the game holds with a wait (a fade step, a blink) is
    one frame too. With ``max_ms``, only pictures on screen for less than that long count, which tells them apart in
    a recording made in real time (not with NO_WAIT, where nothing takes any time)."""
    region_keys: dict[bytes, bytes] = {}  # by digest: frames that repeat a picture needn't be decompressed again
    keys = []
    for frame in frames:
        if frame.digest not in region_keys:
            region_keys[frame.digest] = _region_key(frame, region)
        keys.append(region_keys[frame.digest])
    runs: list[tuple[int, int]] = []  # (first index, length) of each run of the same picture
    for index, key in enumerate(keys):
        if runs and keys[runs[-1][0]] == key:
            runs[-1] = (runs[-1][0], runs[-1][1] + 1)
        else:
            runs.append((index, 1))
    result = []
    for start in range(len(runs)):
        length = 0
        for end in range(start + 1, len(runs)):
            if keys[runs[end][0]] == keys[runs[start][0]]:
                if 0 < length <= max_length:
                    first = runs[start + 1][0]
                    flicker = Flicker(frames[first - 1], tuple(frames[first:first + length]), frames[runs[end][0]])
                    if max_ms is None or flicker.duration_ms < max_ms:
                        result.append(flicker)
                break
            length += runs[end][1]
            if length > max_length:
                break
    return result


def find_one_frame_flickers(frames: Sequence[Frame], region: Rect | None = None) -> list[Flicker]:
    """Frames that differ from both neighbours while the neighbours match each other."""
    return find_flickers(frames, max_length=1, region=region)


def assert_no_flickers(frames: Sequence[Frame], max_length: int = 1, region: Rect | None = None) -> None:
    """For tests: fail, listing them, if find_flickers finds any."""
    flickers = find_flickers(frames, max_length, region)
    if flickers:
        raise AssertionError(f"{len(flickers)} flicker(s) in {len(frames)} frames:\n" +
                             "\n".join(flicker.describe() for flicker in flickers))


def assert_no_one_frame_flickers(frames: Sequence[Frame], region: Rect | None = None) -> None:
    """For tests: fail, listing them, if any frame differs from both neighbours while they match each other."""
    assert_no_flickers(frames, max_length=1, region=region)


# Reports and files

# In a real-time recording: a picture on screen for less than 2 NES frames
REAL_TIME_FLICKER_MS = 2 * 1000 / NES_FPS


def report(frames: Sequence[Frame], max_flicker_length: int = 2) -> str:
    """A plain-text report: every change from one frame to the next, then the suspicious patterns: pictures shown for
    at most ``max_flicker_length`` frames between two matching ones, each with how long it was on screen."""
    if not frames:
        return "No frames were presented.\n"
    distinct = 1 + sum(not before.same_picture(after) for before, after in zip(frames, frames[1:]))
    lines = [f"{len(frames)} frames presented, {distinct} changes of picture (counting the first frame).", "",
             "Changes (each picture is held until the next change):", f"{frames[0].describe()}: first frame"]
    lines += [change.describe() for change in changes(frames)]
    flickers = find_flickers(frames, max_length=max_flicker_length)
    lines += ["", f"Suspicious: pictures shown for at most {max_flicker_length} frame(s) between two matching frames"]
    lines += [f"- {flicker.describe()}" for flicker in flickers] or ["- none"]
    return "\n".join(lines) + "\n"


def save_recording(frames: Sequence[Frame], out_dir: str, all_frames: bool = False) -> str:
    """Save ``report.txt`` and a PNG per picture to ``out_dir``: ``frame_00012.png`` for each frame that changed the
    picture (a frame not saved shows the same picture as the last one saved before it), or every frame with
    ``all_frames``. Returns the report."""
    os.makedirs(out_dir, exist_ok=True)
    for index, frame in enumerate(frames):
        if all_frames or index == 0 or not frames[index - 1].same_picture(frame):
            image.save(frame.surface(), os.path.join(out_dir, f'frame_{frame.index:05d}.png'))
    text = report(frames)
    with open(os.path.join(out_dir, 'report.txt'), 'w', encoding='utf-8') as report_file:
        report_file.write(text)
    return text
