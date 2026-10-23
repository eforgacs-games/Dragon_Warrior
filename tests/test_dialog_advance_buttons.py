"""Which keys move dialog on: only the joypad buttons the NES reads at each wait.

K = A (Enter too), J = B (Escape too), I = START, U = SELECT, WASD or the arrow keys = D-pad. Any other key is ignored.
"""
from collections import defaultdict
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import K_DOWN, K_ESCAPE, K_LEFT, K_RETURN, K_RIGHT, K_UP, K_a, K_d, K_i, K_j, K_k, K_q, K_s, K_u, K_w, \
    K_x, K_SPACE, KEYDOWN, QUIT
from pygame.event import Event

from src.common import A_OR_START_KEYS
from src.config.test_config import test_config
from src.game import Game
from tests.mock_map import MockMap

A_AND_B = (K_k, K_RETURN, K_j, K_ESCAPE)
START_AND_SELECT = (K_i, K_u)
D_PAD = (K_UP, K_DOWN, K_LEFT, K_RIGHT, K_w, K_a, K_s, K_d)
NOT_BUTTONS = (K_q, K_x, K_SPACE)


def press(key: int) -> Event:
    return Event(KEYDOWN, key=key)


def held(*keys: int) -> defaultdict:
    """Key states for key.get_pressed: the given keys down, every other one up."""
    return defaultdict(int, {key: 1 for key in keys})


class DialogWaitTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self) -> None:
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.game.current_map = MockMap(self.game.config)
        self.game.current_map.load_map(self.game.player, (0, 0), self.game.game_state.config["TILE_SIZE"])
        self.cmd_menu = self.game.cmd_menu
        self.held_keys = held()
        patch('src.waiting.key.get_pressed', side_effect=lambda: self.held_keys).start()
        patch.object(self.cmd_menu, 'draw_dialog_arrow').start()
        self.addCleanup(patch.stopall)

    def batches_read(self, wait, *batches) -> int:
        """Runs ``wait`` with each batch of events coming off the queue in turn, and returns how many batches it read
        before it was done. Running out of batches means it never stopped waiting."""
        queue = [list(batch) for batch in batches]

        def get(*_args, **_kwargs):
            if not queue:
                raise AssertionError("still waiting after every event")
            return queue.pop(0)

        with patch('src.menu.event.get', side_effect=get):
            wait()
        return len(batches) - len(queue)


class TestArrowWait(DialogWaitTestCase):
    """NES DoWait / TxtCheckInput: JoypadBtns AND #IN_A_OR_B."""

    def wait(self):
        self.cmd_menu.wait_for_dialog_key(shows_arrow=True, skip_text=False, temp_text_start=None, disable_sound=True)

    def test_a_and_b_go_on(self):
        for key in A_AND_B:
            with self.subTest(key=pygame.key.name(key)):
                self.assertEqual(1, self.batches_read(self.wait, [press(key)]))

    def test_start_select_d_pad_and_other_keys_are_ignored(self):
        for key in START_AND_SELECT + D_PAD + NOT_BUTTONS:
            with self.subTest(key=pygame.key.name(key)):
                self.assertEqual(2, self.batches_read(self.wait, [press(key)], [press(K_k)]))

    def test_a_held_from_before_goes_on_at_once(self):
        self.held_keys = held(K_k)
        self.assertEqual(0, self.batches_read(self.wait))
        self.held_keys = held(K_j)
        self.assertEqual(0, self.batches_read(self.wait))

    def test_start_held_does_not(self):
        self.held_keys = held(K_i, K_UP)
        self.assertEqual(1, self.batches_read(self.wait, [press(K_k)]))

    def test_quit_still_closes_the_game(self):
        with patch('src.waiting.quit_game', side_effect=SystemExit) as quit_game, self.assertRaises(SystemExit):
            self.batches_read(self.wait, [press(K_x), Event(QUIT)])
        quit_game.assert_called_once()


class TestEndOfMessageWait(DialogWaitTestCase):
    """The end of a conversation, of a battle and so on: NES WaitForBtnRelease / WaitForBtnPress, any button."""

    def wait(self):
        self.cmd_menu.wait_for_dialog_key(shows_arrow=False, skip_text=False, temp_text_start=None,
                                          disable_sound=True)

    def test_every_button_goes_on(self):
        for key in A_AND_B + START_AND_SELECT + D_PAD:
            with self.subTest(key=pygame.key.name(key)):
                self.assertEqual(1, self.batches_read(self.wait, [press(key)]))

    def test_other_keys_are_ignored(self):
        for key in NOT_BUTTONS:
            with self.subTest(key=pygame.key.name(key)):
                self.assertEqual(2, self.batches_read(self.wait, [press(key)], [press(K_u)]))

    def test_a_held_from_before_has_to_be_pressed_again(self):
        self.held_keys = held(K_k)
        self.assertEqual(2, self.batches_read(self.wait, [], [press(K_k)]))

    def test_shown_through_show_text_in_dialog_box(self):
        """A conversation's last message is this wait, the ones before it the arrow wait."""
        with patch.object(self.cmd_menu, 'window_drop_up_effect'):
            read = self.batches_read(
                lambda: self.cmd_menu.show_text_in_dialog_box(("One.", "Two."), add_quotes=True),
                [press(K_UP)], [press(K_i)], [press(K_k)], [press(K_x)], [press(K_DOWN)])
        # D-pad and START skipped at the arrow, K went on; x skipped at the end, the D-pad closed it
        self.assertEqual(5, read)


class TestDeathWait(DialogWaitTestCase):
    """NES DeathText: JoypadBtns AND #$09, A or START."""

    def wait(self):
        self.cmd_menu.wait_for_dialog_key(shows_arrow=False, skip_text=False, temp_text_start=None,
                                          disable_sound=True, advance_keys=A_OR_START_KEYS)

    def test_a_and_start_go_on(self):
        for key in (K_k, K_RETURN, K_i):
            with self.subTest(key=pygame.key.name(key)):
                self.assertEqual(1, self.batches_read(self.wait, [press(key)]))

    def test_b_select_d_pad_and_other_keys_are_ignored(self):
        for key in (K_j, K_ESCAPE, K_u) + D_PAD + NOT_BUTTONS:
            with self.subTest(key=pygame.key.name(key)):
                self.assertEqual(2, self.batches_read(self.wait, [press(key)], [press(K_i)]))

    def test_held_start_counts(self):
        self.held_keys = held(K_i)
        self.assertEqual(0, self.batches_read(self.wait))

    def test_handle_death_waits_for_a_or_start(self):
        self.game.player.current_hp = 0
        with patch.object(self.cmd_menu, 'show_text_in_dialog_box') as show_text, \
                patch.object(self.game, 'set_post_death_attributes'), \
                patch.object(self.game.music_player, 'load_and_play_music'):
            self.game.handle_death()
        self.assertEqual(A_OR_START_KEYS, show_text.call_args.kwargs['advance_keys'])


class TestStatusWindow(DialogWaitTestCase):
    """NES LCFA4: the status window closes in WaitForBtnRelease, on any button."""

    def show_status(self):
        with patch.object(self.cmd_menu, 'window_drop_down_effect'), \
                patch.object(self.cmd_menu, 'window_drop_up_effect'), \
                patch('src.menu.display'):
            self.cmd_menu.status()

    def test_every_button_closes_it(self):
        for key in A_AND_B + START_AND_SELECT + D_PAD:
            with self.subTest(key=pygame.key.name(key)):
                self.assertEqual(1, self.batches_read(self.show_status, [press(key)]))

    def test_other_keys_are_ignored(self):
        for key in NOT_BUTTONS:
            with self.subTest(key=pygame.key.name(key)):
                self.assertEqual(2, self.batches_read(self.show_status, [press(key)], [press(K_j)]))


class TestKingWaits(DialogWaitTestCase):
    """The throne room waits for a button before the king speaks (NES FirstInputLoop: any button, held or not)."""

    def test_initial_dialog_starts_on_any_button(self):
        for key in A_AND_B + START_AND_SELECT + D_PAD:
            with self.subTest(key=pygame.key.name(key)):
                self.game.game_state.automatic_initial_dialog_run = False
                with patch.object(self.cmd_menu, 'show_text_in_dialog_box') as show_text:
                    self.game.drawer.run_automatic_initial_dialog([press(key)], False, self.cmd_menu)
                show_text.assert_called_once()

    def test_initial_dialog_ignores_other_keys(self):
        for key in NOT_BUTTONS:
            with self.subTest(key=pygame.key.name(key)):
                with patch.object(self.cmd_menu, 'show_text_in_dialog_box') as show_text:
                    self.game.drawer.run_automatic_initial_dialog([press(key)], False, self.cmd_menu)
                show_text.assert_not_called()
                self.assertFalse(self.game.game_state.automatic_initial_dialog_run)

    def test_initial_dialog_starts_on_a_held_button(self):
        self.held_keys = held(K_LEFT)
        with patch.object(self.cmd_menu, 'show_text_in_dialog_box') as show_text:
            self.game.drawer.run_automatic_initial_dialog([], False, self.cmd_menu)
        show_text.assert_called_once()

    def test_post_death_dialog_starts_on_a_button_only(self):
        self.game.game_state.is_post_death_dialog = True
        with patch.object(self.cmd_menu, 'show_text_in_dialog_box') as show_text, \
                patch('src.drawer.set_to_save_prompt'):
            self.game.drawer.run_automatic_post_death_dialog([press(K_x), press(K_SPACE)], False, self.cmd_menu)
            show_text.assert_not_called()
            self.game.drawer.run_automatic_post_death_dialog([press(K_u)], False, self.cmd_menu)
            show_text.assert_called_once()
        self.assertFalse(self.game.game_state.is_post_death_dialog)


class TestEndingWaits(DialogWaitTestCase):

    def test_ball_of_light_ends_on_any_button(self):
        """TextBlock18, entry 10 waits for A or B (TXT_WAIT) twice, then ends (TXT_END1) and LE9F8 WaitForBtnRelease
        waits for any button."""
        with patch.object(self.cmd_menu, 'show_line_in_dialog_box') as show_line, \
                patch.object(self.game, 'change_map'):
            self.game.ending.final_boss_defeated()
        self.assertEqual([False, False, True], [call.kwargs['hide_arrow'] for call in show_line.call_args_list])
