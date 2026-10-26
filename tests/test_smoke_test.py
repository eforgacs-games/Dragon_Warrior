"""--smoke-test (src/smoke_test.py, src/game.py run_smoke_test): the scripted scenes the release workflow plays on each
build, run here in-process from source on SDL's dummy drivers."""
import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from pygame import K_DOWN, K_RIGHT, K_k  # noqa: E402

from src import smoke_test  # noqa: E402
from src.config.test_config import test_config  # noqa: E402
from src.game import run_smoke_test  # noqa: E402
from src.smoke_test import BUTTON_HOLD_FRAMES, SMOKE_SCENES, STEP_FRAMES, STEP_GAP, SceneLog, SmokeScene, \
    expect_fight, expect_maps, expect_window, parse_smoke_script, play_scene, play_smoke_scenes  # noqa: E402
from src.virtual_joypad import virtual_joypad  # noqa: E402
from src.waiting import game_speed  # noqa: E402
from tests import helpers  # noqa: E402


class TestParseSmokeScript(TestCase):
    def test_buttons_directions_and_waits(self):
        presses, end = parse_smoke_script('wait:10, a, down, right:48')
        a_down = 10
        down_down = a_down + BUTTON_HOLD_FRAMES + STEP_GAP
        right_down = down_down + STEP_FRAMES + STEP_GAP
        self.assertEqual([(a_down, K_k, BUTTON_HOLD_FRAMES), (down_down, K_DOWN, STEP_FRAMES), (right_down, K_RIGHT, 48)],
                         presses)
        self.assertEqual(right_down + 48 + STEP_GAP, end)

    def test_unknown_step(self):
        with self.assertRaises(ValueError):
            parse_smoke_script('a,jump')

    def test_every_scene_parses(self):
        for scene in SMOKE_SCENES:
            presses, end = parse_smoke_script(scene.script)
            self.assertTrue(presses, scene.name)
            self.assertGreater(end, 0)


class TestChecks(TestCase):
    def test_expect_maps(self):
        log = SceneLog()
        for identifier in ('TantegelThroneRoom', 'TantegelThroneRoom', 'TantegelCourtyard'):
            log.saw_map(identifier)
        self.assertEqual(['TantegelThroneRoom', 'TantegelCourtyard'], log.maps)
        self.assertEqual([], expect_maps('TantegelCourtyard')(None, log))
        self.assertEqual(1, len(expect_maps('Alefgard')(None, log)))

    def test_expect_window_and_fight(self):
        log = SceneLog()
        self.assertEqual(1, len(expect_window(None, log)))
        self.assertEqual(1, len(expect_fight(None, log)))
        log.window_polls, log.fights = 3, [object()]
        self.assertEqual([], expect_window(None, log))
        self.assertEqual([], expect_fight(None, log))


class SmokeGameTestCase(TestCase):
    language = 'English'

    def setUp(self):
        self.save_dir = tempfile.TemporaryDirectory(prefix='dragon_warrior_smoke_')
        self.addCleanup(self.save_dir.cleanup)
        self.game = helpers.new_game({**test_config, 'LANGUAGE': self.language, 'SAVE_DIR': self.save_dir.name})


class TestSmokeScenesEnglish(SmokeGameTestCase):
    def test_every_scene_plays(self):
        self.assertEqual([], play_smoke_scenes(self.game))
        # The scenes leave the game as they found it: no joypad connected, normal speed
        self.assertIsNone(virtual_joypad())
        self.assertEqual(1, game_speed())

    def test_run_smoke_test_passes(self):
        with patch('builtins.print') as printed:
            status = run_smoke_test(self.game)
        self.assertEqual(0, status, printed.call_args_list)

    def test_a_check_that_fails_is_reported(self):
        scene = SmokeScene('nowhere', 'wait:10', check=expect_maps('Alefgard'))
        problems = play_scene(self.game, scene)
        self.assertEqual(1, len(problems))
        self.assertTrue(problems[0].startswith('nowhere: never reached Alefgard'))

    def test_an_exception_from_the_game_is_raised(self):
        with patch.object(self.game, 'map_frame', side_effect=RuntimeError('boom')), \
                self.assertRaisesRegex(RuntimeError, 'boom'):
            play_smoke_scenes(self.game)
        self.assertIsNone(virtual_joypad())
        self.assertEqual(1, game_speed())

    def test_run_smoke_test_fails_on_an_exception(self):
        with patch.object(self.game, 'map_frame', side_effect=RuntimeError('boom')), \
                patch('builtins.print'), patch('traceback.print_exc'):
            self.assertEqual(1, run_smoke_test(self.game))

    def test_run_smoke_test_fails_on_a_missing_file(self):
        missing = ['missing: data/fonts/unifont.otf']
        with patch.object(smoke_test, 'check_game_files', return_value=missing), \
                patch.object(smoke_test, 'play_smoke_scenes') as play, patch('builtins.print') as printed:
            self.assertEqual(1, run_smoke_test(self.game))
        play.assert_not_called()
        printed.assert_any_call(missing[0])

    def test_a_stuck_scene_times_out(self):
        with self.assertRaises(TimeoutError):
            play_scene(self.game, SmokeScene('stuck', 'wait:100000'), max_seconds=0.2)
        self.assertIsNone(virtual_joypad())


class TestSmokeScenesKorean(SmokeGameTestCase):
    language = 'Korean'

    def test_every_scene_plays(self):
        self.assertEqual([], play_smoke_scenes(self.game))

    def test_untranslated_game_is_reported(self):
        with patch.object(self.game, '_', lambda text: text):
            self.assertEqual(1, len(smoke_test.check_game_language(self.game)))
