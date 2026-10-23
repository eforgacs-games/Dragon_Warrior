"""The numbers tools/benchmark.py measures: the per-scene results, their JSON file, and the tables that report and
compare them (Markdown, so a table can be pasted into a pull request as it is)."""
import json
import math
import statistics
from dataclasses import asdict, dataclass, field
from typing import Any

RESULTS_VERSION = 1
NOT_AVAILABLE = 'n/a'


@dataclass(frozen=True)
class TimeStats:
    """Milliseconds: the mean, median, 95th percentile and longest of a list of times."""
    mean: float = 0.0
    median: float = 0.0
    p95: float = 0.0
    max: float = 0.0

    @classmethod
    def of(cls, milliseconds: list[float]) -> 'TimeStats':
        if not milliseconds:
            return cls()
        return cls(mean=statistics.fmean(milliseconds), median=statistics.median(milliseconds),
                   p95=percentile(milliseconds, 95), max=max(milliseconds))

    def describe(self) -> str:
        return f'{self.mean:.2f} / {self.median:.2f} / {self.p95:.2f} / {self.max:.2f}'


def percentile(values: list[float], percent: float) -> float:
    """The nearest-rank percentile: the smallest value that at least ``percent``% of the values are at or below."""
    ordered = sorted(values)
    rank = max(1, math.ceil(percent / 100 * len(ordered)))
    return ordered[rank - 1]


@dataclass
class SceneResult:
    """One scene at one game speed.

    A pass is one time round the main loop: the game logic (the map frames due, Game.run_due_frames) and the drawing
    (Drawer.draw_all and display.flip). Passes that took longer than the benchmark's OWN_LOOP_MS ran a loop of their
    own (a battle, a dialog, a menu or a map change); they aren't in the frame times, only in ``own_loop_passes`` and
    ``own_loop_seconds``, and the CPU time, flips and updates cover them too."""
    scene: str
    speed: int
    status: str = 'ok'  # 'ok', or why the scene couldn't run (NOT_AVAILABLE and the error)
    passes: int = 0
    logic_ms: TimeStats = field(default_factory=TimeStats)
    draw_ms: TimeStats = field(default_factory=TimeStats)
    frame_ms: TimeStats = field(default_factory=TimeStats)
    own_loop_passes: int = 0
    own_loop_seconds: float = 0.0
    map_frames: int = 0
    shown_frames: int = 0  # presented frames, at most one per frame of game time
    wall_seconds: float = 0.0
    cpu_seconds: float = 0.0
    flips: int = 0
    updates: int = 0

    @property
    def key(self) -> tuple[str, int]:
        return self.scene, self.speed

    @property
    def ran(self) -> bool:
        return self.status == 'ok'

    @property
    def target_fps(self) -> int:
        return 60 * self.speed

    @property
    def map_fps(self) -> float:
        """Map frames run per real second."""
        return self.map_frames / self.wall_seconds if self.wall_seconds else 0.0

    @property
    def shown_fps(self) -> float:
        """Frames presented per real second, counting at most one per frame of game time (so at most 60 x speed)."""
        return self.shown_frames / self.wall_seconds if self.wall_seconds else 0.0

    @property
    def cpu_percent(self) -> float:
        """CPU time as a share of real time: 100% is a busy loop, a low share is time spent sleeping."""
        return 100 * self.cpu_seconds / self.wall_seconds if self.wall_seconds else 0.0


def results_to_json(results: list[SceneResult], metadata: dict) -> str:
    return json.dumps({'version': RESULTS_VERSION, 'metadata': metadata,
                       'results': [asdict(result) for result in results]}, indent=2)


def results_from_json(text: str) -> tuple[list[SceneResult], dict]:
    data = json.loads(text)
    if data.get('version') != RESULTS_VERSION:
        raise ValueError(f"Unsupported benchmark results version {data.get('version')!r}")
    return [scene_result_from_dict(entry) for entry in data['results']], data.get('metadata', {})


def scene_result_from_dict(entry: dict[str, Any]) -> SceneResult:
    times = {name: TimeStats(**entry[name]) for name in ('logic_ms', 'draw_ms', 'frame_ms')}
    return SceneResult(**{**entry, **times})


def markdown_table(header: list[str], rows: list[list[str]]) -> str:
    lines = ['| ' + ' | '.join(header) + ' |', '|' + '---|' * len(header)]
    lines += ['| ' + ' | '.join(row) + ' |' for row in rows]
    return '\n'.join(lines)


def report_row(result: SceneResult) -> list[str]:
    if not result.ran:
        return [result.scene, f'{result.speed}x', result.status] + [''] * 9
    return [result.scene, f'{result.speed}x', str(result.passes), result.logic_ms.describe(), result.draw_ms.describe(),
            f'{result.own_loop_passes} ({result.own_loop_seconds:.1f} s)',
            f'{result.map_fps:.0f} ({100 * result.map_fps / result.target_fps:.0f}%)',
            f'{result.shown_fps:.0f} ({100 * result.shown_fps / result.target_fps:.0f}%)',
            f'{result.wall_seconds:.1f}', f'{result.cpu_seconds:.1f} ({result.cpu_percent:.0f}%)',
            str(result.flips), str(result.updates)]


def format_report(results: list[SceneResult]) -> str:
    header = ['Scene', 'Speed', 'Passes', 'Logic ms (mean / median / p95 / max)', 'Draw ms (mean / median / p95 / max)',
              'Own loops', 'Map FPS', 'Shown FPS', 'Wall s', 'CPU s', 'flip', 'update']
    return markdown_table(header, [report_row(result) for result in results])


# What --compare shows: (column title, how to read it off a result, digits)
COMPARED_METRICS = (
    ('Frame ms mean', lambda result: result.frame_ms.mean, 2),
    ('Frame ms p95', lambda result: result.frame_ms.p95, 2),
    ('Draw ms mean', lambda result: result.draw_ms.mean, 2),
    ('Logic ms mean', lambda result: result.logic_ms.mean, 3),
    ('Map FPS', lambda result: result.map_fps, 0),
    ('Shown FPS', lambda result: result.shown_fps, 0),
    ('CPU %', lambda result: result.cpu_percent, 0),
    ('update', lambda result: result.updates, 0),
)


def change(before: float, after: float, digits: int) -> str:
    """``before → after``, with the change in percent when both are set."""
    text = f'{before:.{digits}f} → {after:.{digits}f}'
    if before:
        text += f' ({100 * (after - before) / before:+.0f}%)'
    return text


def compare_row(scene: str, speed: int, before: SceneResult | None, after: SceneResult | None) -> list[str]:
    cells = [scene, f'{speed}x']
    for _title, read, digits in COMPARED_METRICS:
        if before is None or after is None or not before.ran or not after.ran:
            cells.append(f'{describe_side(before, read, digits)} → {describe_side(after, read, digits)}')
        else:
            cells.append(change(read(before), read(after), digits))
    return cells


def describe_side(result: SceneResult | None, read, digits: int) -> str:
    if result is None or not result.ran:
        return NOT_AVAILABLE
    return f'{read(result):.{digits}f}'


def format_comparison(before: list[SceneResult], after: list[SceneResult]) -> str:
    """A table of each scene and speed in either list: before → after (change), or n/a where a side didn't run it."""
    before_by_key = {result.key: result for result in before}
    after_by_key = {result.key: result for result in after}
    keys = list(dict.fromkeys([result.key for result in before] + [result.key for result in after]))
    header = ['Scene', 'Speed'] + [title for title, _read, _digits in COMPARED_METRICS]
    rows = [compare_row(scene, speed, before_by_key.get((scene, speed)), after_by_key.get((scene, speed)))
            for scene, speed in keys]
    return markdown_table(header, rows)
