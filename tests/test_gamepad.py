"""Gamepad support (src/gamepad.py, #382): a controller presses the keyboard's keys, through the same hooks as
auto-grind's virtual joypad, so every loop reads it unchanged. There is no real controller under the dummy drivers:
the tests feed the gamepad fake controllers (FakeBackend, FakePad)."""
import os
from collections import defaultdict
from unittest import TestCase
from unittest.mock import MagicMock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from pygame import K_BACKSPACE, K_DOWN, K_F1, K_LEFT, K_RIGHT, K_UP, K_i, K_j, K_k, K_u, KEYDOWN, KEYUP, KMOD_SHIFT

from src.config.test_config import test_config
from src.cursor import IN_A, IN_B
from src.direction import Direction
from src.gamepad import DOWN, LEFT, RIGHT, UP, Gamepad, PadState, SdlBackend, is_gamepad, pad_direction, \
    stick_direction
from src.selection import Answer, run_selection, stop_at_edges
from src.waiting import NES_FPS, WINDOW_CONTEXT, game_speed, gamepad, poll_virtual_joypad, reset_game_speed, \
    set_gamepad, set_speed_keys_enabled, with_virtual_keys
from tests.test_battle_controller import BattlePromptFrames, RUN

# The pad buttons (SDL GameController names) for the NES ones: Nintendo's positional layout
PAD_A, PAD_B, PAD_START, PAD_SELECT = 'b', 'a', 'start', 'back'


def pad(*buttons: str, stick_x: float = 0.0, stick_y: float = 0.0) -> PadState:
    return PadState(frozenset(buttons), stick_x, stick_y)


class FakePad:
    """A controller whose state the test sets. Reading it too often means a loop never got the press it waited for."""

    def __init__(self) -> None:
        self.state = pad()
        self.plugged_in = True
        self.closed = False
        self.reads = 0
        self.read_limit = 5000

    def attached(self) -> bool:
        return self.plugged_in

    def read(self) -> PadState:
        self.reads += 1
        if self.reads > self.read_limit:
            raise AssertionError("still reading the pad: the press never reached the game")
        return self.state

    def close(self) -> None:
        self.closed = True


class FakeBackend:
    """The controllers plugged in, in order."""

    def __init__(self, *pads: FakePad) -> None:
        self.pads = list(pads)
        self.opened = 0

    def count(self) -> int:
        return len(self.pads)

    def open_first(self) -> FakePad | None:
        self.opened += 1
        return self.pads[0] if self.pads else None


def queued(event_type=KEYDOWN) -> list[pygame.event.Event]:
    """The events of a type on the queue, left there."""
    events = pygame.event.get(event_type)
    for current_event in events:
        pygame.event.post(current_event)
    return events


class GamepadTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((64, 64))

    def setUp(self):
        pygame.event.clear()
        reset_game_speed()
        self.pad = FakePad()
        self.backend = FakeBackend(self.pad)
        self.gamepad = Gamepad(self.backend)
        self.gamepad.connect()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.gamepad.disconnect()
        patch.stopall()
        reset_game_speed()
        pygame.event.clear()


class TestStick(TestCase):

    def test_deadzone(self):
        self.assertIsNone(stick_direction(0.0, 0.0, None))
        self.assertIsNone(stick_direction(0.45, -0.3, None))
        self.assertEqual(RIGHT, stick_direction(0.55, 0.0, None))
        self.assertEqual(UP, stick_direction(0.0, -0.9, None))

    def test_once_pressed_it_lets_go_lower(self):
        # no flicker for a stick resting by the edge of the deadzone
        self.assertEqual(RIGHT, stick_direction(0.4, 0.0, RIGHT))
        self.assertIsNone(stick_direction(0.3, 0.0, RIGHT))
        self.assertIsNone(stick_direction(0.4, 0.0, None))

    def test_the_axis_pushed_furthest_wins(self):
        self.assertEqual(DOWN, stick_direction(0.6, 0.7, None))
        self.assertEqual(LEFT, stick_direction(-0.7, 0.6, None))

    def test_no_diagonal_jitter(self):
        # around 45 degrees the direction held stays until the other axis is clearly further
        self.assertEqual(RIGHT, stick_direction(0.68, 0.72, RIGHT))
        self.assertEqual(RIGHT, stick_direction(0.72, 0.68, RIGHT))
        self.assertEqual(DOWN, stick_direction(0.72, 0.68, DOWN))
        self.assertEqual(DOWN, stick_direction(0.5, 0.9, RIGHT))
        self.assertEqual(RIGHT, stick_direction(0.9, 0.5, DOWN))

    def test_d_pad_in_nes_order_and_before_the_stick(self):
        self.assertEqual(UP, pad_direction(pad('dpup', 'dpdown', 'dpleft'), None))
        self.assertEqual(DOWN, pad_direction(pad('dpdown', 'dpright'), None))
        self.assertEqual(LEFT, pad_direction(pad('dpleft', stick_x=0.9), None))
        self.assertEqual(RIGHT, pad_direction(pad(stick_x=0.9), None))


class TestKeys(GamepadTestCase):

    def test_each_button_presses_its_key(self):
        for pad_state, pressed_key in ((pad(PAD_A), K_k), (pad(PAD_B), K_j), (pad(PAD_START), K_i),
                                       (pad(PAD_SELECT), K_u), (pad('dpup'), K_UP), (pad('dpdown'), K_DOWN),
                                       (pad('dpleft'), K_LEFT), (pad('dpright'), K_RIGHT),
                                       (pad(stick_x=-1.0), K_LEFT), (pad(stick_y=1.0), K_DOWN)):
            with self.subTest(pad=pad_state):
                pygame.event.clear()
                self.pad.state = pad_state
                poll_virtual_joypad()
                presses = queued()
                self.assertEqual([pressed_key], [current_event.key for current_event in presses])
                self.assertTrue(is_gamepad(presses[0]))
                self.assertEqual('', presses[0].unicode)  # no letter typed
                self.assertEqual({pressed_key}, self.gamepad.held)
                self.assertTrue(with_virtual_keys(defaultdict(int))[pressed_key])
                # held: no second press
                poll_virtual_joypad()
                self.assertEqual(1, len(queued()))
                self.pad.state = pad()
                poll_virtual_joypad()
                self.assertEqual([pressed_key], [current_event.key for current_event in queued(KEYUP)])
                self.assertEqual(set(), self.gamepad.held)

    def test_one_direction_at_a_time(self):
        self.pad.state = pad('dpup', 'dpright')
        poll_virtual_joypad()
        self.assertEqual({K_UP}, self.gamepad.held)
        self.pad.state = pad('dpright')
        poll_virtual_joypad()
        self.assertEqual({K_RIGHT}, self.gamepad.held)

    def test_buttons_together(self):
        self.pad.state = pad(PAD_A, 'dpleft')
        poll_virtual_joypad()
        self.assertEqual({K_k, K_LEFT}, self.gamepad.held)

    def test_unmapped_buttons_do_nothing(self):
        self.pad.state = pad('x', 'y', 'guide')
        poll_virtual_joypad()
        self.assertEqual([], queued())
        self.assertEqual(set(), self.gamepad.held)

    def test_left_bumper_presses_f1(self):
        # load state 1
        self.pad.state = pad('leftshoulder')
        poll_virtual_joypad()
        [press] = queued()
        self.assertEqual((K_F1, 0), (press.key, press.mod & KMOD_SHIFT))
        self.assertTrue(is_gamepad(press))
        self.assertEqual({K_F1}, self.gamepad.held)

    def test_right_bumper_presses_shift_f1(self):
        # save state 1
        self.pad.state = pad('rightshoulder')
        poll_virtual_joypad()
        [press] = queued()
        self.assertEqual(K_F1, press.key)
        self.assertTrue(press.mod & KMOD_SHIFT)
        self.assertEqual({K_F1}, self.gamepad.held)

    def test_left_trigger_holds_backspace_until_let_go(self):
        # rewind, for as long as the trigger is pulled
        self.pad.state = pad('lefttrigger')
        poll_virtual_joypad()
        self.assertEqual([K_BACKSPACE], [press.key for press in queued()])
        poll_virtual_joypad()
        self.assertEqual(1, len(queued()))  # held: one press
        self.assertTrue(with_virtual_keys(defaultdict(int))[K_BACKSPACE])
        self.pad.state = pad()
        poll_virtual_joypad()
        self.assertEqual([K_BACKSPACE], [release.key for release in queued(KEYUP)])
        self.assertEqual(set(), self.gamepad.held)

    def test_right_trigger_steps_through_the_speeds(self):
        speeds = []
        for _ in range(6):
            self.pad.state = pad('righttrigger')
            poll_virtual_joypad()
            poll_virtual_joypad()  # held: once per pull
            speeds.append(game_speed())
            self.pad.state = pad()
            poll_virtual_joypad()
        self.assertEqual([2, 4, 8, 16, 1, 2], speeds)
        self.assertEqual([], queued())  # no key, so no window reads it and auto-grind carries on

    def test_the_speed_trigger_does_nothing_with_game_speed_off(self):
        # the options overlay's GAME SPEED switch (src/options_overlay.py), off on the NES, as for the keys 1 to 5
        set_speed_keys_enabled(False)
        self.pad.state = pad('righttrigger')
        poll_virtual_joypad()
        self.assertEqual(1, game_speed())
        self.assertEqual([], queued())


class TestHotPlug(GamepadTestCase):

    def setUp(self):
        super().setUp()
        self.backend.pads.clear()

    def test_plugged_in_later(self):
        poll_virtual_joypad()
        self.assertIsNone(self.gamepad.device)
        self.backend.pads.append(self.pad)
        self.pad.state = pad(PAD_A)
        poll_virtual_joypad()
        self.assertIs(self.pad, self.gamepad.device)
        self.assertEqual({K_k}, self.gamepad.held)

    def test_unplugged_lets_go(self):
        self.backend.pads.append(self.pad)
        self.pad.state = pad(PAD_A, 'dpdown')
        poll_virtual_joypad()
        self.pad.plugged_in = False
        self.backend.pads.clear()
        poll_virtual_joypad()
        self.assertIsNone(self.gamepad.device)
        self.assertTrue(self.pad.closed)
        self.assertEqual(set(), self.gamepad.held)
        self.assertEqual({K_k, K_DOWN}, {current_event.key for current_event in queued(KEYUP)})

    def test_several_pads_use_the_first_and_keep_it(self):
        second = FakePad()
        second.state = pad(PAD_B)
        self.backend.pads.extend((self.pad, second))
        self.pad.state = pad(PAD_A)
        poll_virtual_joypad()
        self.assertEqual({K_k}, self.gamepad.held)
        # a third one plugged in: the one in use stays, without being opened again
        self.backend.pads.append(FakePad())
        opened = self.backend.opened
        poll_virtual_joypad()
        self.assertEqual(opened, self.backend.opened)
        # the first one unplugged: the next one takes over
        self.pad.plugged_in = False
        self.backend.pads.remove(self.pad)
        poll_virtual_joypad()
        self.assertIs(second, self.gamepad.device)
        self.assertEqual({K_j}, self.gamepad.held)

    def test_nothing_read_while_nothing_changes(self):
        poll_virtual_joypad()
        poll_virtual_joypad()
        self.assertEqual(0, self.backend.opened)


class TestNoController(TestCase):

    def test_nothing_changes(self):
        pygame.init()
        pygame.event.clear()
        sdl = Gamepad(SdlBackend())
        sdl.connect()
        self.addCleanup(sdl.disconnect)
        self.assertEqual(0, SdlBackend().count())  # the dummy drivers have no controller
        real = defaultdict(int)
        self.assertIs(real, with_virtual_keys(real))
        poll_virtual_joypad()
        self.assertIsNone(sdl.device)
        self.assertEqual(set(), sdl.held)
        self.assertEqual([], queued())

    def test_the_game_connects_one(self):
        from tests.helpers import new_game
        new_game(dict(test_config))
        self.addCleanup(set_gamepad, None)
        self.assertIsInstance(gamepad(), Gamepad)
        self.assertIsInstance(gamepad().backend, SdlBackend)


class TestAutoGrind(GamepadTestCase):

    def test_a_button_stops_it_like_a_key(self):
        from src.auto_grind import StopReason
        from tests.test_auto_grind import GRASS, GrindTestCase
        grind_case = GrindTestCase()
        game = grind_case.new_game()
        self.gamepad.connect()  # the game connected the real one
        grind = game.auto_grind
        self.addCleanup(grind.joypad.disconnect)
        patch.object(game, 'draw_temporary_text').start()
        patch.object(game.sound, 'play_sound').start()
        grind_case.game, grind_case.player, grind_case.grind = game, game.player, grind
        grind_case.go_to('Alefgard', GRASS)
        self.assertTrue(grind.start())
        self.pad.state = pad(PAD_B)
        poll_virtual_joypad(WINDOW_CONTEXT)
        self.assertFalse(grind.active)
        self.assertEqual(StopReason.KEY, grind.last_stop)
        # used up, like a key
        self.assertEqual([], [current_event for current_event in queued() if is_gamepad(current_event)])

    def test_the_speed_trigger_does_not(self):
        from tests.test_auto_grind import GRASS, GrindTestCase
        grind_case = GrindTestCase()
        game = grind_case.new_game()
        self.gamepad.connect()
        grind = game.auto_grind
        self.addCleanup(grind.joypad.disconnect)
        patch.object(game, 'draw_temporary_text').start()
        patch.object(game.sound, 'play_sound').start()
        grind_case.game, grind_case.player, grind_case.grind = game, game.player, grind
        grind_case.go_to('Alefgard', GRASS)
        self.assertTrue(grind.start())
        self.pad.state = pad('righttrigger')
        poll_virtual_joypad(WINDOW_CONTEXT)
        self.assertTrue(grind.active)
        self.assertEqual(2, game_speed())


class TestMapFrame(GamepadTestCase):
    """The map loop (Game.read_events and the hero's walking) reads the pad."""

    def setUp(self):
        super().setUp()
        from tests.helpers import new_game
        from tests.mock_map import MockMap
        self.game = new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True,
                                 'SAVE_STATES': True, 'REWIND': True})  # their switches on (off on the NES)
        self.gamepad.connect()  # the game connected the real one
        self.game.current_map = MockMap(self.game.config)
        self.game.current_map.load_map(self.game.player, (0, 0), self.game.game_state.config["TILE_SIZE"])

    def press(self, *buttons: str) -> None:
        self.pad.state = pad(*buttons)
        self.game.read_events()
        self.pad.state = pad()
        self.game.read_events()

    def test_a_opens_the_command_window(self):
        with patch.object(self.game.movement, 'resolve_pending_freezes'):
            self.press(PAD_A)
        self.assertTrue(self.game.cmd_menu_requested)

    def test_every_button_reaches_the_map_as_its_key(self):
        for button, pressed_key in ((PAD_A, K_k), (PAD_B, K_j), (PAD_START, K_i), (PAD_SELECT, K_u)):
            with self.subTest(button=button), patch.object(self.game, 'handle_keypresses') as keypresses:
                self.press(button)
                self.assertEqual([pressed_key], [call.args[0].key for call in keypresses.call_args_list])

    def test_bumpers_load_and_save_state_1(self):
        for button, request in (('leftshoulder', ('load', 1)), ('rightshoulder', ('save', 1))):
            with self.subTest(button=button), patch.object(self.game.movement, 'resolve_pending_freezes'):
                self.game.state_request = None
                self.press(button)
                self.assertEqual(request, self.game.state_request)

    def test_left_trigger_rewinds_while_held(self):
        rewind = self.game.rewind
        with patch.object(rewind, 'start') as start, patch.object(rewind, 'stop') as stop:
            self.pad.state = pad('lefttrigger')
            self.game.read_events()
            start.assert_called_once_with()
            stop.assert_not_called()
            self.pad.state = pad()
            self.game.read_events()
            stop.assert_called_once_with()

    def test_select_opens_the_options(self):
        with patch('src.game.OptionsOverlay') as overlay:
            self.press(PAD_SELECT)
        overlay.return_value.run.assert_called_once_with()

    def test_d_pad_and_stick_turn_the_hero(self):
        player = self.game.player
        for pad_state, direction in ((pad('dpright'), Direction.RIGHT), (pad(stick_y=-1.0), Direction.UP),
                                     (pad(stick_x=-1.0), Direction.LEFT)):
            with self.subTest(direction=direction):
                self.pad.state = pad_state
                player.is_moving = False
                self.game.movement.handle_player_movement()
                self.assertEqual(direction.value, player.direction_value)


class TestDialogWait(GamepadTestCase):
    """A dialog box waits for A or B (CommandMenu.wait_for_dialog_key) and reads the pad."""

    def setUp(self):
        super().setUp()
        from tests.helpers import new_game
        from tests.mock_map import MockMap
        self.game = new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True})
        self.gamepad.connect()
        self.game.current_map = MockMap(self.game.config)
        self.game.current_map.load_map(self.game.player, (0, 0), self.game.game_state.config["TILE_SIZE"])
        patch.object(self.game.cmd_menu, 'draw_dialog_arrow').start()

    def wait(self):
        self.game.cmd_menu.wait_for_dialog_key(shows_arrow=True, skip_text=False, temp_text_start=None,
                                               disable_sound=True)

    def test_a_and_b_go_on(self):
        for button in (PAD_A, PAD_B):
            with self.subTest(button=button):
                self.pad.reads = 0
                self.pad.state = pad(button)
                self.wait()

    def test_start_does_not(self):
        self.pad.state = pad(PAD_START)
        self.pad.read_limit = 50  # a few frames' worth of reads
        with self.assertRaises(AssertionError):
            self.wait()


class TestMenuSelection(GamepadTestCase):
    """run_selection, the loop of every blocking window, one pad state per NES frame."""

    def setUp(self):
        super().setUp()
        self.frames = 0
        self.script: list[PadState] = []

        def next_frame(*_args, **_kwargs):
            self.frames += 1
            if self.frames > 200:
                raise AssertionError("still selecting")
            self.pad.state = self.script.pop(0) if self.script else pad()
        patch('src.cursor.get_ticks', lambda: -(-self.frames * 1000 // NES_FPS)).start()
        patch('src.selection.wait_frames', side_effect=next_frame).start()

    def select(self, *states: PadState) -> Answer:
        self.script = list(states)
        return run_selection(MagicMock(), move=stop_at_edges(3))

    def test_down_then_a(self):
        self.assertEqual(Answer(IN_A, 1), self.select(pad('dpdown'), pad(), pad(PAD_A)))

    def test_stick_down_twice_then_a(self):
        self.assertEqual(Answer(IN_A, 2), self.select(pad(stick_y=0.9), pad(), pad(stick_y=0.9), pad(),
                                                      pad(PAD_A)))

    def test_b(self):
        self.assertEqual(IN_B, self.select(pad(), pad(PAD_B)).button)

    def test_start_and_select_do_not_answer(self):
        self.assertEqual(Answer(IN_A, 0), self.select(pad(PAD_START), pad(), pad(PAD_SELECT), pad(), pad(PAD_A)))


class TestNameEntry(TestCase):
    """A controller can't type: its buttons are joystick input on the name entry screen, without Tab."""

    def test_buttons_pick_letters(self):
        from src.menu_functions import NameSelection
        config = dict(test_config, NO_BLIT=True)
        command_menu = MagicMock()
        command_menu.game.game_state.config = config

        def button(pressed_key):
            return pygame.event.Event(KEYDOWN, key=pressed_key, mod=0, unicode='', gamepad=True)
        # A on A, right, A on B, then A on B six more times: the 8th character ends the name
        events = [button(K_k), button(K_RIGHT)] + [button(K_k)] * 7
        with patch('src.selection.event.get', side_effect=[[current_event] for current_event in events]), \
                patch('src.selection.wait_frames'), patch('src.menu_functions.display'), \
                patch('src.menu_functions.Sound'), patch('src.menu_functions.toggle_joystick_input') as toggle:
            name = NameSelection(config).select_name(0, pygame.Surface((256, 240)), command_menu)
        self.assertEqual('ABBBBBBB', name)
        toggle.assert_not_called()  # no "Joystick input enabled." box


@patch('src.battle_controller.display')
@patch('src.battle_controller.time')
class TestBattleCommand(BattlePromptFrames):
    """The battle's command window reads the pad (BattlePromptFrames runs it a frame at a time)."""

    def setUp(self):
        pygame.init()
        pygame.display.set_mode((64, 64))
        self.pad = FakePad()
        self.gamepad = Gamepad(FakeBackend(self.pad))
        self.gamepad.connect()
        self.addCleanup(self.gamepad.disconnect)
        super().setUp()

    def pad_press(self, *buttons: str):
        """Two frames with nothing down, then the buttons down for a frame; let go on the next frame."""
        self.frames(2)
        self.pad.state = pad(*buttons)
        result = self.frame()
        self.pad.state = pad()
        return result

    def test_down_moves_to_run(self, _time, _display):
        self.pad_press('dpdown')
        self.assertEqual(RUN, self.selection)

    def test_a_fights(self, _time, _display):
        with patch.object(self.controller, 'fight') as fight, self.patch_enemy_move():
            self.pad_press(PAD_A)
        fight.assert_called_once_with(self.battle)
        self.assertEqual(1, self.battle.turn)


class TestDevices(TestCase):
    """Reading SDL's controllers and plain joysticks, with stand-ins for pygame's objects."""

    def test_controller(self):
        from src.gamepad import ControllerDevice
        controller = MagicMock()
        down = {pygame.CONTROLLER_BUTTON_B, pygame.CONTROLLER_BUTTON_DPAD_LEFT}
        axes = {pygame.CONTROLLER_AXIS_LEFTX: 32767, pygame.CONTROLLER_AXIS_LEFTY: -16384,
                pygame.CONTROLLER_AXIS_TRIGGERRIGHT: 30000, pygame.CONTROLLER_AXIS_TRIGGERLEFT: 1000}
        controller.get_button.side_effect = lambda number: number in down
        controller.get_axis.side_effect = lambda axis: axes.get(axis, 0)
        state = ControllerDevice(controller).read()
        self.assertEqual(frozenset({'b', 'dpleft', 'righttrigger'}), state.buttons)
        self.assertAlmostEqual(1.0, state.stick_x)
        self.assertAlmostEqual(-0.5, state.stick_y, places=3)

    def test_joystick(self):
        from src.gamepad import JoystickDevice
        joystick = MagicMock()
        joystick.get_numbuttons.return_value = 10
        joystick.get_button.side_effect = lambda number: number in (1, 9)
        joystick.get_numhats.return_value = 1
        joystick.get_hat.return_value = (0, 1)
        joystick.get_numaxes.return_value = 2
        joystick.get_axis.side_effect = lambda axis: (0.25, 0.75)[axis]
        # JoystickDevice counts the joysticks when opened, which raises if an earlier test on this worker quit pygame
        with patch('pygame.joystick.get_count', return_value=1):
            state = JoystickDevice(joystick).read()
        self.assertEqual(frozenset({'b', 'start', 'dpup'}), state.buttons)
        self.assertEqual((0.25, 0.75), (state.stick_x, state.stick_y))
