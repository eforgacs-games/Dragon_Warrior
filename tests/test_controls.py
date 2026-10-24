"""Remappable controls (src/controls.py): the bindings as data, the live key sets the game reads, the controls file,
the help that shows the bindings, and the CONTROLS screen (src/controls_screen.py) that rebinds them."""
import json
import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from pygame import K_1, K_2, K_3, K_4, K_5, K_DELETE, K_DOWN, K_ESCAPE, K_F1, K_F2, K_F4, K_F9, K_F11, K_LEFT, \
    K_LSHIFT, K_RETURN, K_RIGHT, K_TAB, K_UP, K_a, K_d, K_g, K_h, K_i, K_j, K_k, K_l, K_m, K_p, K_q, K_s, K_u, \
    K_w, KEYDOWN, KEYUP, KMOD_LSHIFT, KMOD_SHIFT
from pygame.event import Event

from data.text.intro_lookup_table import ControlInfo
from src import common
from src.config.test_config import test_config
from src.direction import Direction
from src.controls import ACTIONS, ACTIONS_BY_NAME, KEY_SLOTS, Binding, Controls, KeySet, actions_for_event, \
    apply_controls, current_controls, key_label, parse_binding, binding_name, pressed, \
    reset_controls, set_controls, set_controls_listener
from src.controls_screen import CELL_CURSOR_COLUMNS, CHANGED_TOO, CONTROLS_WINDOW, DEFAULTS_RESTORED, HINT, \
    LABEL_COLUMN, NEEDS_A_KEY, VISIBLE_ROWS, Cell, ControlsScreen, controls_layout, screen_texts
from src.settings import Settings, load_settings, save_settings
from src.waiting import SPEED_KEYS, game_speed, handle_speed_key, reset_game_speed
from src.window_renderer import window_tiles
from tests import helpers


def key(pressed_key, mod=0):
    return Event(KEYDOWN, key=pressed_key, mod=mod)


def row_of(name):
    return [action.name for action in ACTIONS].index(name)


class ControlsTestCase(TestCase):

    def setUp(self):
        reset_controls()
        self.addCleanup(reset_controls)

    @staticmethod
    def rebound(**changes) -> Controls:
        """The default controls with some actions' keys changed (by name: a tuple of keys), in use."""
        controls = Controls.defaults()
        for name, keys in changes.items():
            controls.keys[name] = [Binding(*binding) if isinstance(binding, tuple) else Binding(binding)
                                   for binding in keys]
        set_controls(controls)
        return controls


class TestDefaults(ControlsTestCase):

    def test_the_key_sets_are_the_keys_the_game_has_always_used(self):
        self.assertEqual((K_k, K_RETURN), common.A_BUTTON_KEYS)
        self.assertEqual((K_j, K_ESCAPE), common.B_BUTTON_KEYS)
        self.assertEqual((K_i,), common.START_BUTTON_KEYS)
        self.assertEqual((K_u,), common.SELECT_BUTTON_KEYS)
        self.assertEqual((K_UP, K_w), common.UP_KEYS)
        self.assertEqual((K_DOWN, K_s), common.DOWN_KEYS)
        self.assertEqual((K_LEFT, K_a), common.LEFT_KEYS)
        self.assertEqual((K_RIGHT, K_d), common.RIGHT_KEYS)
        self.assertEqual({K_ESCAPE, K_j}, set(common.reject_keys))
        self.assertEqual({K_RETURN, K_i, K_k}, set(common.accept_keys))
        self.assertEqual({K_1: 1, K_2: 2, K_3: 4, K_4: 8, K_5: 16}, dict(SPEED_KEYS))

    def test_the_extra_actions(self):
        expected = {'SMART_A': K_RETURN, 'OPTIONS': K_TAB, 'HELP': K_h, 'AUTO_GRIND': K_g, 'AUTO_BATTLE': K_F4,
                    'INVULNERABLE': K_F9, 'FULLSCREEN': K_F11, 'LOAD_STATE_1': K_F1, 'LOAD_STATE_2': K_F2,
                    'QUEST_JOURNAL': K_q, 'MAP': K_m}
        for name, expected_key in expected.items():
            with self.subTest(name):
                self.assertEqual([name], actions_for_event(key(expected_key)))
        self.assertEqual([Binding(K_F1, KMOD_SHIFT)], current_controls().keys['SAVE_STATE_1'])

    def test_every_action_has_a_label_and_the_nes_buttons_a_key(self):
        for action in ACTIONS:
            with self.subTest(action.name):
                self.assertLessEqual(len(action.label), CELL_CURSOR_COLUMNS[0] - LABEL_COLUMN)
                if action.nes:
                    self.assertTrue(action.keys)
                    self.assertFalse(action.modifiers)

    def test_no_two_default_keys_clash(self):
        controls = Controls.defaults()
        for action in ACTIONS:
            for binding in action.keys:
                with self.subTest(action.name, key=binding_name(binding)):
                    self.assertIsNone(controls.owner_of(binding, action))

    def test_the_default_pad_buttons(self):
        pad = Controls.defaults().pad
        self.assertEqual(('b', 'a', 'start', 'back'), (pad['A'], pad['B'], pad['START'], pad['SELECT']))
        self.assertEqual('righttrigger', pad['NEXT_SPEED'])
        self.assertEqual(('leftshoulder', 'rightshoulder', 'lefttrigger'),
                         (pad['LOAD_STATE_1'], pad['SAVE_STATE_1'], pad['REWIND']))
        self.assertEqual('y', pad['MAP'])  # the top face button: the dungeon map (#408)

    def test_no_two_default_pad_buttons_clash(self):
        buttons = [button for button in Controls.defaults().pad.values() if button is not None]
        self.assertEqual(len(buttons), len(set(buttons)), buttons)


class TestModifiers(ControlsTestCase):

    def test_shift_f1_saves_and_f1_loads(self):
        self.assertEqual(['LOAD_STATE_1'], actions_for_event(key(K_F1)))
        self.assertEqual(['SAVE_STATE_1'], actions_for_event(key(K_F1, KMOD_LSHIFT)))
        self.assertTrue(pressed(key(K_F2, KMOD_LSHIFT), 'SAVE_STATE_2'))
        self.assertFalse(pressed(key(K_F2, KMOD_LSHIFT), 'LOAD_STATE_2'))

    def test_a_key_without_modifiers_is_pressed_with_any(self):
        self.assertTrue(pressed(key(K_g, KMOD_LSHIFT), 'AUTO_GRIND'))
        self.assertTrue(pressed(key(K_k, KMOD_LSHIFT), 'A'))

    def test_only_key_presses(self):
        self.assertFalse(pressed(Event(KEYUP, key=K_h, mod=0), 'HELP'))

    def test_the_nes_buttons_take_no_modifiers(self):
        controls = Controls.defaults()
        controls.bind_key('A', 0, Binding(K_l, KMOD_SHIFT))
        self.assertEqual([Binding(K_l)], controls.keys['A'])


class TestLiveKeySets(ControlsTestCase):

    def test_a_rebind_applies_to_the_sets_made_at_import(self):
        self.rebound(A=(K_l,), UP=(K_p,))
        self.assertIn(K_l, common.A_BUTTON_KEYS)
        self.assertNotIn(K_k, common.A_BUTTON_KEYS)
        self.assertIn(K_RETURN, common.A_BUTTON_KEYS)  # SMART_A is an extra A
        self.assertIn(K_l, common.A_OR_START_KEYS)
        self.assertIn(K_p, common.D_PAD_KEYS)
        self.assertIn(K_l, common.ANY_BUTTON_KEYS)
        self.assertEqual(K_l, common.A_BUTTON_KEYS[0])

    def test_a_key_set_works_like_a_set_with_sets(self):
        self.assertEqual(frozenset({K_UP}), common.D_PAD_KEYS & {K_UP, K_k})
        self.assertEqual(frozenset({K_k}), {K_UP, K_k} - common.D_PAD_KEYS)
        self.assertEqual(8, len(common.D_PAD_KEYS))

    def test_fixed_keys(self):
        keys = KeySet('SELECT', fixed=(K_TAB,))
        self.assertEqual((K_u, K_TAB), keys)
        self.assertEqual((K_u, K_TAB, K_i), keys + (K_i,))

    def test_unknown_action(self):
        with self.assertRaises(ValueError):
            KeySet('JUMP')

    def test_the_speed_keys_follow(self):
        self.rebound(SPEED_2=(K_p,))
        self.assertEqual(2, SPEED_KEYS[K_p])
        self.assertNotIn(K_2, SPEED_KEYS)
        reset_game_speed()
        self.assertTrue(handle_speed_key(key(K_p)))
        self.assertEqual(2, game_speed())
        self.assertFalse(handle_speed_key(key(K_2)))
        reset_game_speed()

    def test_next_speed_key(self):
        self.rebound(NEXT_SPEED=(K_p,))
        reset_game_speed()
        speeds = []
        for _ in range(6):
            handle_speed_key(key(K_p))
            speeds.append(game_speed())
        reset_game_speed()
        self.assertEqual([2, 4, 8, 16, 1, 2], speeds)


class TestBinding(ControlsTestCase):

    def test_a_free_key(self):
        controls = Controls.defaults()
        self.assertTrue(controls.bind_key('A', 0, Binding(K_l)))
        self.assertEqual([Binding(K_l)], controls.keys['A'])
        self.assertTrue(controls.bind_key('A', 1, Binding(K_p)))
        self.assertEqual([Binding(K_l), Binding(K_p)], controls.keys['A'])

    def test_a_past_the_last_key_goes_in_the_next_slot(self):
        controls = Controls.defaults()
        controls.bind_key('START', KEY_SLOTS - 1, Binding(K_p))
        self.assertEqual([Binding(K_i), Binding(K_p)], controls.keys['START'])

    def test_a_key_another_action_has_is_swapped(self):
        controls = Controls.defaults()
        self.assertTrue(controls.bind_key('A', 0, Binding(K_j)))
        self.assertEqual([Binding(K_j)], controls.keys['A'])
        self.assertEqual([Binding(K_k), Binding(K_ESCAPE)], controls.keys['B'])

    def test_into_an_empty_slot_the_other_action_loses_it(self):
        controls = Controls.defaults()
        self.assertTrue(controls.bind_key('A', 1, Binding(K_ESCAPE)))
        self.assertEqual([Binding(K_k), Binding(K_ESCAPE)], controls.keys['A'])
        self.assertEqual([Binding(K_j)], controls.keys['B'])

    def test_an_nes_button_keeps_its_last_key(self):
        controls = Controls.defaults()
        self.assertFalse(controls.bind_key('A', 1, Binding(K_i)))  # START's only key
        self.assertEqual(Controls.defaults(), controls)
        self.assertFalse(controls.clear_key('START', 0))
        self.assertTrue(controls.clear_key('B', 1))
        self.assertFalse(controls.clear_key('B', 0))

    def test_an_extra_action_can_lose_its_key(self):
        controls = Controls.defaults()
        self.assertTrue(controls.bind_key('A', 1, Binding(K_h)))
        self.assertEqual([], controls.keys['HELP'])
        self.assertTrue(controls.clear_key('AUTO_GRIND', 0))
        self.assertEqual([], controls.keys['AUTO_GRIND'])

    def test_its_own_other_slot_swaps(self):
        controls = Controls.defaults()
        self.assertTrue(controls.bind_key('UP', 0, Binding(K_w)))
        self.assertEqual([Binding(K_w), Binding(K_UP)], controls.keys['UP'])

    def test_the_same_key_changes_nothing(self):
        self.assertFalse(Controls.defaults().bind_key('A', 0, Binding(K_k)))

    def test_shift_and_plain_f1_both_fit_but_not_an_nes_button(self):
        controls = Controls.defaults()
        # an NES button ignores modifiers, so F1 for A would also be pressed by Shift+F1
        self.assertTrue(controls.bind_key('A', 1, Binding(K_F1)))
        self.assertEqual([], controls.keys['LOAD_STATE_1'])
        self.assertEqual([], controls.keys['SAVE_STATE_1'])

    def test_pad_buttons_swap(self):
        controls = Controls.defaults()
        self.assertTrue(controls.bind_pad('A', 'a'))
        self.assertEqual(('a', 'b'), (controls.pad['A'], controls.pad['B']))
        self.assertTrue(controls.bind_pad('HELP', 'y'))
        self.assertTrue(controls.bind_pad('HELP', None))
        self.assertIsNone(controls.pad['HELP'])


class TestFile(ControlsTestCase):

    def test_names(self):
        self.assertEqual("Shift+F1", binding_name(Binding(K_F1, KMOD_SHIFT)))
        self.assertEqual("k", binding_name(Binding(K_k)))
        self.assertEqual(Binding(K_F1, KMOD_SHIFT), parse_binding("Shift+F1"))
        self.assertEqual(Binding(K_RETURN), parse_binding("RETURN"))
        for bad in ("Hyper+F1", "NOT_A_KEY", 3, None, ""):
            self.assertIsNone(parse_binding(bad))

    def test_round_trip(self):
        controls = Controls.defaults()
        controls.bind_key('A', 0, Binding(K_l))
        controls.bind_key('SAVE_STATE_1', 0, Binding(K_p, KMOD_SHIFT))
        controls.bind_pad('HELP', 'y')
        data = json.loads(json.dumps(controls.to_json()))
        self.assertEqual(["l"], data['keys']['A'])
        self.assertEqual(["Shift+p"], data['keys']['SAVE_STATE_1'])
        self.assertEqual(controls, Controls.from_json(data))

    def test_bad_data_is_the_defaults(self):
        for data in (None, [], "keys", {'keys': 3, 'pad': []}):
            self.assertEqual(Controls.defaults(), Controls.from_json(data))

    def test_bad_entries_are_dropped(self):
        controls = Controls.from_json({'keys': {'A': ["NOT_A_KEY", "l"], 'B': ["l", "j"], 'START': []},
                                       'pad': {'A': 'not a button', 'B': 'b'}})
        self.assertEqual([Binding(K_l)], controls.keys['A'])
        self.assertEqual([Binding(K_j)], controls.keys['B'])  # l is A's
        self.assertEqual([Binding(K_i)], controls.keys['START'])  # an NES button with no key keeps its own
        self.assertIsNone(controls.pad['A'])
        self.assertEqual('b', controls.pad['B'])

    def test_a_missing_action_keeps_its_defaults_unless_taken(self):
        controls = Controls.from_json({'keys': {'A': ["h"]}})
        self.assertEqual([Binding(K_h)], controls.keys['A'])
        self.assertEqual([], controls.keys['HELP'])
        self.assertEqual([Binding(K_j), Binding(K_ESCAPE)], controls.keys['B'])

    def test_kept_with_the_global_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'sub', 'settings.json')
            self.assertIsNone(load_settings(path).controls)
            controls = Controls.defaults()
            controls.bind_key('START', 0, Binding(K_p))
            self.assertTrue(save_settings(path, Settings(controls=controls.to_json())))
            with open(path) as settings_file:
                self.assertEqual(["p"], json.load(settings_file)['controls']['keys']['START'])
            self.assertEqual(controls, Controls.from_json(load_settings(path).controls))

    def test_bad_controls_in_the_settings(self):
        self.assertIsNone(Settings.from_json({'controls': "nonsense"}).controls)
        settings = Settings.from_json({'controls': {'keys': {'A': ["NOT_A_KEY"]}}, 'zoom': 2})
        self.assertEqual(Controls.defaults().to_json(), settings.controls)
        self.assertEqual(2, settings.zoom)

    def test_the_game_loads_them_and_saves_each_change(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'settings.json')
            saved = Controls.defaults()
            saved.bind_key('START', 0, Binding(K_p))
            save_settings(path, Settings(controls=saved.to_json(), zoom=2))
            helpers.new_game({**test_config, 'SETTINGS_PATH': path, 'NO_BLIT': True})
            self.addCleanup(set_controls_listener, None)
            self.assertEqual(saved, current_controls())
            changed = current_controls().copy()
            changed.bind_key('HELP', 0, Binding(K_l))
            apply_controls(changed)
            self.assertEqual(changed, Controls.from_json(load_settings(path).controls))
            self.assertEqual(2, load_settings(path).zoom)  # the other settings are kept


class TestTheGameFollowsTheBindings(ControlsTestCase):

    def setUp(self):
        super().setUp()
        self.game = helpers.new_game({**test_config, 'NO_BLIT': True, 'RENDER_TEXT': False, 'NO_WAIT': True})

    def test_start(self):
        self.rebound(START=(K_p,))
        self.game.handle_keypresses(key(K_i))
        self.assertFalse(self.game.pause_requested)
        self.game.handle_keypresses(key(K_p))
        self.assertTrue(self.game.paused or self.game.pause_requested)

    def test_a_opens_the_command_window(self):
        self.rebound(A=(K_l,))
        self.game.handle_keypresses(key(K_k))
        self.assertFalse(self.game.cmd_menu_requested)
        with patch.object(self.game.movement, 'resolve_pending_freezes'):
            self.game.handle_keypresses(key(K_l))
        self.assertTrue(self.game.cmd_menu_requested)

    def test_the_toggles(self):
        self.rebound(INVULNERABLE=(K_p,))
        before = self.game.invulnerable
        with patch.object(self.game, 'draw_temporary_text'):
            self.game.handle_keypresses(key(K_F9))
            self.assertEqual(before, self.game.invulnerable)
            self.game.handle_keypresses(key(K_p))
        self.assertNotEqual(before, self.game.invulnerable)

    def test_save_states(self):
        self.rebound(SAVE_STATE_2=((K_p, KMOD_SHIFT),), LOAD_STATE_2=(K_p,))
        with patch.object(self.game.movement, 'resolve_pending_freezes'):
            self.game.handle_save_state_keys(key(K_p, KMOD_LSHIFT))
            self.assertEqual(('save', 2), self.game.state_request)
            self.game.state_request = None
            self.game.handle_save_state_keys(key(K_p))
            self.assertEqual(('load', 2), self.game.state_request)
            self.game.state_request = None
            self.game.handle_save_state_keys(key(K_F2))
        self.assertIsNone(self.game.state_request)

    def test_rewind(self):
        self.rebound(REWIND=(K_p,))
        with patch.object(self.game.rewind, 'start') as start, patch.object(self.game.rewind, 'stop') as stop:
            self.game._handle_pygame_events([key(pygame.K_BACKSPACE)])
            start.assert_not_called()
            self.game._handle_pygame_events([key(K_p)])
            start.assert_called_once()
            self.game._handle_pygame_events([Event(KEYUP, key=K_p, mod=0)])
            stop.assert_called_once()

    def test_walking(self):
        from src.movement import held_direction
        self.rebound(LEFT=(K_p,))
        held = {K_p}
        keyboard = type('Held', (), {'__getitem__': lambda _self, held_key: held_key in held})()
        self.assertEqual(Direction.LEFT.value, held_direction(keyboard))


class TestHelpShowsTheBindings(ControlsTestCase):

    def lines(self, language='English'):
        return [line for page in ControlInfo({**test_config, 'LANGUAGE': language}).help_pages
                for line in page.split('\n')]

    def test_defaults(self):
        lines = self.lines()
        for line in ("K: A Button", "J/ESC: B Button", "I: Start", "U/TAB: Options", "ARROWS/WASD: Move",
                     "ENTER: Smart A", "H: Show Controls", "1-5: Game Speed", "G: Auto-grind", "F4: Auto-Battle",
                     "SHIFT+F1-F3: Save state", "F1-F3: Load state", "BACKSPACE: Rewind"):
            self.assertIn(line, lines)

    def test_rebound(self):
        self.rebound(A=(K_l, K_p), UP=(K_i,), START=(K_w,), SPEED_1=(K_a,), HELP=(), SAVE_STATE_1=((K_s, KMOD_SHIFT),))
        lines = self.lines()
        for line in ("L/P: A Button", "W: Start", "I,DOWN,LEFT,RIGHT/-,S,A,D: Move", "-: Show Controls",
                     "A/2/3/4/5: Game Speed", "SHIFT+S/SHIFT+F2/SHIFT+F3: Save state"):
            self.assertIn(line, lines)

    def test_korean(self):
        self.rebound(A=(K_l,))
        lines = self.lines('Korean')
        self.assertIn("L: A 버튼", lines)
        self.assertIn("화살표 키/WASD: 이동", lines)


# The CONTROLS screen

GAP = 2  # frames with nothing pressed after each press


def script(*events):
    """event.get's results, once a frame: each event (a key, or an Event), then GAP frames of none."""
    results = []
    for current in events:
        results += [[]] * GAP + [[current if isinstance(current, Event) else key(current)]]
    return results


class ScreenTestCase(ControlsTestCase):

    def setUp(self):
        super().setUp()
        self.game = helpers.new_game({**test_config, 'NO_BLIT': True, 'RENDER_TEXT': False, 'NO_WAIT': True})
        clock = [0]

        def next_frame(frames=1, *_args, **_kwargs):
            clock[0] += round(frames * 1000 / 60)
        patch('src.cursor.get_ticks', lambda: clock[0]).start()
        patch('src.selection.wait_frames', side_effect=next_frame).start()
        self.addCleanup(patch.stopall)

    def run_screen(self, *events):
        """Run the screen through these events (it must close by the end); returns the screen."""
        screen = ControlsScreen(self.game)
        with patch('src.selection.event.get', side_effect=script(*events) + [[key(K_ESCAPE)]]), \
                patch.object(self.game.sound, 'play_sound'):
            screen.run()
        return screen


class TestControlsScreen(ScreenTestCase):

    def test_rebind_a_key(self):
        # A BUTTON, KEY 1: A, then the key
        self.run_screen(K_RETURN, K_l)
        self.assertEqual([Binding(K_l)], current_controls().keys['A'])

    def test_rebind_the_second_key(self):
        self.run_screen(*(K_DOWN,) * row_of('START'), K_RIGHT, K_k, K_p)
        self.assertEqual([Binding(K_i), Binding(K_p)], current_controls().keys['START'])

    def test_a_swap_is_named(self):
        screen = self.run_screen(K_k, K_j)
        self.assertEqual([Binding(K_j)], current_controls().keys['A'])
        self.assertEqual([Binding(K_k), Binding(K_ESCAPE)], current_controls().keys['B'])
        self.assertEqual(CHANGED_TOO.format("B BUTTON"), screen.hint)

    def test_a_refusal_is_named(self):
        screen = self.run_screen(K_RIGHT, K_k, K_i)  # A's KEY 2 to START's only key
        self.assertEqual(Controls.defaults(), current_controls())
        self.assertEqual(NEEDS_A_KEY.format("A BUTTON"), screen.hint)

    def test_modifiers(self):
        self.run_screen(*(K_DOWN,) * row_of('SAVE_STATE_1'), K_RETURN,
                        Event(KEYDOWN, key=K_LSHIFT, mod=KMOD_LSHIFT), key(K_p, KMOD_LSHIFT))
        self.assertEqual([Binding(K_p, KMOD_SHIFT)], current_controls().keys['SAVE_STATE_1'])

    def test_a_modifier_alone_is_bound_when_let_go(self):
        self.run_screen(*(K_DOWN,) * row_of('HELP'), K_RETURN, Event(KEYDOWN, key=K_LSHIFT, mod=KMOD_LSHIFT),
                        Event(KEYUP, key=K_LSHIFT, mod=0))
        self.assertEqual([Binding(K_LSHIFT)], current_controls().keys['HELP'])

    def test_the_speed_keys_are_read_as_keys(self):
        reset_game_speed()
        self.run_screen(*(K_DOWN,) * row_of('HELP'), K_RETURN, K_3)
        self.assertEqual([Binding(K_3)], current_controls().keys['HELP'])
        self.assertEqual([Binding(K_h)], current_controls().keys['SPEED_4'])  # swapped
        self.assertEqual(1, game_speed())

    def test_nothing_pressed_changes_nothing(self):
        with patch('src.controls_screen.CAPTURE_MS', 0):
            screen = self.run_screen(K_RETURN)
        self.assertEqual(Controls.defaults(), current_controls())
        self.assertEqual(HINT, screen.hint)

    def test_clear(self):
        self.run_screen(*(K_DOWN,) * row_of('HELP'), K_u)
        self.assertEqual([], current_controls().keys['HELP'])
        self.run_screen(*(K_DOWN,) * row_of('AUTO_GRIND'), K_DELETE)
        self.assertEqual([], current_controls().keys['AUTO_GRIND'])
        self.run_screen(K_DELETE)  # A's only key stays
        self.assertEqual([Binding(K_k)], current_controls().keys['A'])

    def test_reset_to_defaults(self):
        self.rebound(A=(K_l,), START=(K_p,))
        screen = self.run_screen(*(K_DOWN,) * (len(ACTIONS) + 3), K_l)  # A is L now
        self.assertEqual(Controls.defaults(), current_controls())
        self.assertEqual(DEFAULTS_RESTORED, screen.hint)

    def test_the_arrows_enter_and_escape_always_work(self):
        # the D-pad, A and B moved off them: they still move, choose and close here
        self.rebound(UP=(K_w,), DOWN=(K_s,), LEFT=(K_a,), RIGHT=(K_d,), A=(K_l,), B=(K_p,), SMART_A=())
        self.run_screen(K_DOWN, K_RIGHT, K_LEFT, K_RETURN, K_g)
        self.assertEqual([Binding(K_g)], current_controls().keys['B'])
        self.assertEqual([Binding(K_p)], current_controls().keys['AUTO_GRIND'])  # swapped

    def test_the_bound_keys_work_too(self):
        self.run_screen(K_s, K_d, K_k, K_p)  # B's KEY 2
        self.assertEqual([Binding(K_j), Binding(K_p)], current_controls().keys['B'])

    def test_b_closes_it(self):
        with patch('src.selection.event.get', side_effect=script(K_j)), patch.object(self.game.sound, 'play_sound'):
            ControlsScreen(self.game).run()

    def test_every_change_is_applied_and_saved(self):
        saved = []
        set_controls_listener(saved.append)
        self.addCleanup(set_controls_listener, None)
        self.run_screen(K_RETURN, K_l)
        self.assertEqual([current_controls()], saved)

    def test_the_pad_cell_without_a_controller(self):
        screen = self.run_screen(K_RIGHT, K_RIGHT, K_RETURN)
        self.assertEqual("NO CONTROLLER", screen.hint)
        self.assertEqual('b', current_controls().pad['A'])

    def test_the_pad_cell_with_a_controller(self):
        with patch('src.controls._pad_reader', lambda _ms: 'y'), patch('src.controls._pad_connected', lambda: True):
            self.run_screen(K_RIGHT, K_RIGHT, K_RETURN)
        self.assertEqual('y', current_controls().pad['A'])
        self.run_screen(K_RIGHT, K_RIGHT, K_u)
        self.assertIsNone(current_controls().pad['A'])


class TestControlsLayout(ControlsTestCase):

    def texts(self, cell=Cell(0, 0), top=0):
        return [(text.text, text.column, text.row) for text in controls_layout(current_controls(), cell, top, HINT).texts]

    def test_the_first_rows(self):
        texts = self.texts()
        self.assertEqual([("KEY 1", 12, 2), ("KEY 2", 19, 2), ("PAD", 26, 2)], texts[:3])
        self.assertEqual([("A BUTTON", 1, 4), ("K", 12, 4), ("-", 19, 4), ("EAST", 26, 4)], texts[3:7])
        self.assertEqual([("B BUTTON", 1, 6), ("J", 12, 6), ("ESC", 19, 6), ("SOUTH", 26, 6)], texts[7:11])
        self.assertEqual((HINT, 2, 26), texts[-1])

    def test_it_scrolls(self):
        layout = controls_layout(current_controls(), Cell(len(ACTIONS), 0), len(ACTIONS) + 1 - VISIBLE_ROWS, HINT)
        self.assertEqual("RESET TO DEFAULTS", layout.texts[-2].text)
        self.assertEqual(((1, 4 + 2 * (VISIBLE_ROWS - 1)),), layout.cursor_tiles)

    def test_every_page_fits_the_window_in_the_nes_font(self):
        self.rebound(SAVE_STATE_1=((K_F1, KMOD_SHIFT),), A=(K_LSHIFT, K_RETURN))
        for top in range(len(ACTIONS) + 2 - VISIBLE_ROWS):
            window_tiles(controls_layout(current_controls(), Cell(top, 0), top, HINT))
        for hint in screen_texts():
            window_tiles(controls_layout(current_controls(), Cell(0, 0), 0, hint.format("INVINCIBLE")))

    def test_key_labels_fit_their_cells(self):
        import pygame as pg
        for name in dir(pg):
            if name.startswith('K_') and isinstance(getattr(pg, name), int):
                for mod in (0, KMOD_SHIFT):
                    with self.subTest(name):
                        self.assertLessEqual(len(key_label(Binding(getattr(pg, name), mod))), 6)

    def test_window(self):
        self.assertEqual((0, 0, 16, 15), tuple(CONTROLS_WINDOW))


def to_controls_row() -> tuple[int, ...]:
    """The presses that turn the options overlay to the CONTROLS row's page (START) and go down to it."""
    from src.options_overlay import CONTROLS_ROW, FIXED_ROWS, OPTION_PAGES
    page = next(number for number, shown in enumerate(OPTION_PAGES) if CONTROLS_ROW in shown.rows)
    return (K_i,) * page + (K_DOWN,) * (FIXED_ROWS + OPTION_PAGES[page].rows.index(CONTROLS_ROW))


class TestOptionsOverlayOpensIt(ScreenTestCase):

    def test_controls_row(self):
        from src.options_overlay import OptionsOverlay
        downs = to_controls_row()
        with patch('src.selection.event.get', side_effect=script(*downs, K_k, K_RETURN, K_l, K_ESCAPE, K_u)), \
                patch.object(self.game.sound, 'play_sound'):
            OptionsOverlay(self.game).run()
        self.assertEqual([Binding(K_l)], current_controls().keys['A'])

    def test_left_and_right_do_nothing_there(self):
        from src.options_overlay import OptionsOverlay
        before = dict(self.game.game_state.config)
        downs = to_controls_row()
        with patch('src.selection.event.get', side_effect=script(*downs, K_LEFT, K_RIGHT, K_u)), \
                patch.object(self.game.sound, 'play_sound'), \
                patch('src.options_overlay.ControlsScreen') as screen:
            OptionsOverlay(self.game).run()
        screen.assert_not_called()
        self.assertEqual(before, self.game.game_state.config)


class TestEveryNesButtonKeepsAKey(ControlsTestCase):

    def test_any_sequence_of_binds(self):
        import random
        rng = random.Random(402)
        keys = [K_k, K_j, K_i, K_u, K_UP, K_DOWN, K_LEFT, K_RIGHT, K_w, K_a, K_s, K_d, K_l, K_p, K_F1, K_RETURN]
        controls = Controls.defaults()
        for _ in range(2000):
            action = rng.choice(ACTIONS)
            controls.bind_key(action.name, rng.randrange(KEY_SLOTS), Binding(rng.choice(keys),
                                                                             rng.choice((0, KMOD_SHIFT))))
            if rng.random() < 0.2:
                controls.clear_key(action.name, rng.randrange(KEY_SLOTS))
            for nes in (action for action in ACTIONS if action.nes):
                self.assertTrue(controls.keys[nes.name], nes.name)
            bound = [(binding, ACTIONS_BY_NAME[name]) for name, bindings in controls.keys.items()
                     for binding in bindings]
            for index, (first, first_action) in enumerate(bound):
                for second, second_action in bound[index + 1:]:
                    if first_action is second_action:
                        self.assertNotEqual(first, second)
                    else:
                        self.assertIsNone(None if first.key != second.key else
                                          (first, second) if first.mod == second.mod or not first_action.modifiers
                                          or not second_action.modifiers else None)
            for name, bindings in controls.keys.items():
                self.assertLessEqual(len(bindings), KEY_SLOTS, name)


if __name__ == '__main__':
    pygame.init()
