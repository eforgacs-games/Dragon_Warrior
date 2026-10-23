"""The performance benchmark (tools/benchmark.py) and its results, report and comparison (tools/benchmark_results.py)."""
import argparse
import json
import os
import tempfile
from src.waiting import NES_FPS
from unittest import TestCase
from unittest.mock import patch

from tools import benchmark
from tools.benchmark_results import SceneResult, TimeStats, format_comparison, format_report, percentile, \
    results_from_json, results_to_json


def scene_result(scene='courtyard', speed=1, frame_mean=2.0, **fields) -> SceneResult:
    return SceneResult(scene=scene, speed=speed, passes=100, frame_ms=TimeStats(frame_mean, frame_mean, 3.0, 9.0),
                       draw_ms=TimeStats(1.5, 1.5, 2.5, 8.0), logic_ms=TimeStats(0.1, 0.1, 0.2, 1.0),
                       map_frames=600, shown_frames=540, wall_seconds=10.0, cpu_seconds=4.0, flips=600, updates=50,
                       **fields)


class TestTimeStats(TestCase):

    def test_percentile_is_nearest_rank(self):
        values = list(range(1, 101))
        self.assertEqual(95, percentile(values, 95))
        self.assertEqual(100, percentile(values, 100))
        self.assertEqual(7, percentile([7], 95))
        self.assertEqual(4, percentile([4, 1, 3, 2], 95))

    def test_stats(self):
        stats = TimeStats.of([1.0, 2.0, 3.0, 10.0])
        self.assertEqual((4.0, 2.5, 10.0, 10.0), (stats.mean, stats.median, stats.p95, stats.max))
        self.assertEqual(TimeStats(), TimeStats.of([]))
        self.assertEqual('4.00 / 2.50 / 10.00 / 10.00', stats.describe())


class TestSceneResult(TestCase):

    def test_rates(self):
        result = scene_result(speed=8)
        self.assertEqual(8 * NES_FPS, result.target_fps)
        self.assertEqual(60.0, result.map_fps)
        self.assertEqual(54.0, result.shown_fps)
        self.assertEqual(40.0, result.cpu_percent)
        self.assertEqual(0.0, SceneResult('battle', 1).map_fps)

    def test_json_round_trip(self):
        results = [scene_result(), SceneResult('battle', 8, status='n/a: TypeError: no')]
        loaded, metadata = results_from_json(results_to_json(results, {'commit': 'abc1234'}))
        self.assertEqual(results, loaded)
        self.assertEqual({'commit': 'abc1234'}, metadata)

    def test_unknown_version_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'version'):
            results_from_json(json.dumps({'version': 99, 'results': []}))


class TestTables(TestCase):

    def test_report_lists_each_run_and_why_a_scene_did_not_run(self):
        text = format_report([scene_result(), SceneResult('battle', 8, status='n/a: TypeError: no')])
        lines = text.splitlines()
        self.assertEqual(4, len(lines))
        self.assertIn('| courtyard | 1x | 100 | 0.10 / 0.10 / 0.20 / 1.00 | 1.50 / 1.50 / 2.50 / 8.00 |', lines[2])
        self.assertIn('60 (100%)', lines[2])
        self.assertIn('4.0 (40%)', lines[2])
        self.assertIn('| battle | 8x | n/a: TypeError: no |', lines[3])

    def test_comparison_shows_the_change(self):
        text = format_comparison([scene_result(frame_mean=2.0)], [scene_result(frame_mean=1.5)])
        row = text.splitlines()[2]
        self.assertTrue(row.startswith('| courtyard | 1x | 2.00 → 1.50 (-25%) | 3.00 → 3.00 (+0%) |'), row)

    def test_comparison_marks_scenes_one_side_did_not_run(self):
        before = [scene_result(), SceneResult('battle', 1, status='n/a: TypeError: no')]
        after = [scene_result(), scene_result('battle'), scene_result('cantlin')]
        rows = format_comparison(before, after).splitlines()[2:]
        self.assertEqual(['courtyard', 'battle', 'cantlin'], [row.split(' | ')[0].strip('| ') for row in rows])
        self.assertIn('| n/a → 2.00 |', rows[1])
        self.assertIn('| n/a → 2.00 |', rows[2])


class TestBenchmarkParts(TestCase):

    def test_parse_scene_names_and_speeds(self):
        self.assertEqual([benchmark.SCENES_BY_NAME['battle'], benchmark.SCENES_BY_NAME['cantlin']],
                         benchmark.parse_names('battle, cantlin'))
        with self.assertRaisesRegex(argparse.ArgumentTypeError, 'Unknown scene'):
            benchmark.parse_names('battle,moon')
        self.assertEqual([1, 8], benchmark.parse_speeds('1,8'))
        with self.assertRaises(argparse.ArgumentTypeError):
            benchmark.parse_speeds('3')

    def test_every_scene_script_parses(self):
        for scene in benchmark.SCENES:
            with self.subTest(scene.name):
                _presses, end_frame = benchmark.scene_length(scene, frames=600)
                self.assertGreater(end_frame, 0)
        _presses, end_frame = benchmark.scene_length(benchmark.SCENES_BY_NAME['cantlin'], frames=123)
        self.assertEqual(123, end_frame)

    def test_long_passes_are_counted_as_loops_of_their_own(self):
        meter = benchmark.SceneMeter()
        meter.add_pass(0.1, 2.0)
        meter.add_pass(150.0, 2.0)
        meter.add_cut_pass(50.0)
        meter.add_cut_pass(250.0)
        result = meter.result(benchmark.SCENES_BY_NAME['battle'], 1, wall_seconds=1.0, cpu_seconds=0.5)
        self.assertEqual(1, result.passes)
        self.assertEqual(2, result.own_loop_passes)
        self.assertAlmostEqual(0.402, result.own_loop_seconds)
        self.assertAlmostEqual(2.1, result.frame_ms.mean)

    def test_best_run_is_the_fastest_that_ran(self):
        slow, fast = scene_result(frame_mean=3.0), scene_result(frame_mean=1.0)
        failed = SceneResult('courtyard', 1, status='n/a: TypeError: no')
        self.assertIs(fast, benchmark.best_run([slow, failed, fast]))
        self.assertIs(failed, benchmark.best_run([failed]))


class TestBenchmarkRun(TestCase):

    def test_smoke_run_and_compare(self):
        with tempfile.TemporaryDirectory() as out_dir, patch('builtins.print') as printed, \
                patch.object(benchmark, 'print_progress'):
            out = os.path.join(out_dir, 'results.json')
            self.assertEqual(0, benchmark.main(['--scenes', 'throne_room', '--speeds', '8', '--frames', '10',
                                                '--json', out]))
            with open(out) as results_file:
                results, metadata = results_from_json(results_file.read())
            self.assertEqual(0, benchmark.main(['--compare', out, out]))
        [result] = results
        self.assertEqual(('throne_room', 8, 'ok'), (result.scene, result.speed, result.status))
        self.assertGreater(result.passes, 0)
        self.assertGreater(result.map_frames, 0)
        self.assertGreaterEqual(result.flips, result.passes)
        self.assertEqual(10, metadata['frames'])
        self.assertIn('| throne_room | 8x |', printed.call_args_list[0].args[0])
        self.assertIn('(+0%)', printed.call_args_list[1].args[0])
