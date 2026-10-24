"""The message log (src/message_log.py): the last dialog messages, kept as they're shown and opened on the map with the
MESSAGE LOG key (L) when the MESSAGE LOG option is on."""
import os
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from pygame import K_DOWN, K_ESCAPE, K_LEFT, K_RIGHT, K_UP, K_i, K_j, K_l, K_p, KEYDOWN
from pygame.event import Event

from src.config.test_config import test_config
from src.controls import Binding, Controls, reset_controls, set_controls
from src.message_log import EMPTY, HINT, HINT_ROW, LINE_WIDTH, MAX_ENTRIES, VISIBLE_LINES, LogEntry, MessageLog, \
    MessageLogScreen, log_layout, log_lines, speaker_of, text_width, wrap
from src.options_overlay import OPTION_ROWS
from src.options_screen import DEFAULT_OPTIONS, options_from_save, options_to_save
from src.window_renderer import window_tiles
from tests import helpers


def key(pressed_key):
    return Event(KEYDOWN, key=pressed_key, mod=0)


def same(text):
    return text


class TestTheLog(TestCase):

    def test_keeps_the_last_50(self):
        log = MessageLog()
        for number in range(60):
            log.record(f"Line {number}")
        self.assertEqual(MAX_ENTRIES, len(log))
        self.assertEqual(LogEntry("Line 10"), log.entries[0])
        self.assertEqual(LogEntry("Line 59"), log.entries[-1])

    def test_one_line_each(self):
        log = MessageLog()
        log.record("A Slime\ndraws  near!", 'GUARD')
        log.record(" \n ")
        self.assertEqual([LogEntry("A Slime draws near!", 'GUARD')], list(log.entries))

    def test_speakers(self):
        self.assertEqual('MAN', speaker_of('MAN_2'))
        self.assertEqual('KING_LORIK', speaker_of('KING_LORIK'))
        self.assertIsNone(speaker_of('SOMETHING_ELSE'))
        self.assertIsNone(speaker_of(None))


class TestWrapping(TestCase):

    def test_whole_words_then_an_indent(self):
        lines = wrap("GUARD: Welcome to Tantegel Castle, where the king awaits thee.", 28, 2)
        self.assertEqual(["GUARD: Welcome to Tantegel", "  Castle, where the king", "  awaits thee."], lines)
        for line in lines:
            self.assertLessEqual(len(line), 28)

    def test_a_long_word_is_cut(self):
        self.assertEqual(["abcdefghij", "  klmnopqr", "  st"], wrap("abcdefghijklmnopqrst", 10, 2))

    def test_korean_is_two_tiles_a_letter(self):
        self.assertEqual(4, text_width("용왕"))
        lines = wrap("용왕을 쓰러뜨리고 로라 공주를 구하여 라다톰 성으로 돌아가거라", 20, 2)
        for line in lines:
            self.assertLessEqual(text_width(line), 20)
        self.assertEqual("용왕을쓰러뜨리고로라공주를구하여라다톰성으로돌아가거라",
                         ''.join(line.strip() for line in lines).replace(' ', ''))

    def test_lines(self):
        entries = [LogEntry("Thou hast found the Silver Harp."), LogEntry("Hello.", 'WISE_MAN')]
        self.assertEqual(["Thou hast found the Silver", "  Harp.", "WISE MAN: Hello."], log_lines(entries, same))


class TestLayout(TestCase):

    def test_empty(self):
        layout = log_layout([], 0)
        self.assertEqual([EMPTY, HINT], [text.text for text in layout.texts])
        self.assertEqual("MESSAGE LOG", layout.title.text)

    def test_the_lines_from_top(self):
        lines = [f"LINE {number}" for number in range(20)]
        layout = log_layout(lines, 5)
        self.assertEqual([f"LINE {number}" for number in range(5, 5 + VISIBLE_LINES)] + [HINT],
                         [text.text for text in layout.texts])
        self.assertEqual([2 + 2 * number for number in range(VISIBLE_LINES)] + [HINT_ROW],
                         [text.row for text in layout.texts])

    def test_fits_the_window(self):
        window_tiles(log_layout(["W" * LINE_WIDTH] * VISIBLE_LINES, 0))


class GameTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        reset_controls()
        self.addCleanup(reset_controls)
        self.game = helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True,
                                      'MESSAGE_LOG': True})
        self.game.game_state.is_initial_dialog = False
        self.cmd_menu = self.game.cmd_menu
        for blocking in ('window_drop_down_effect', 'window_drop_up_effect', 'wait_for_dialog_key'):
            patcher = patch.object(self.cmd_menu, blocking)
            patcher.start()
            self.addCleanup(patcher.stop)


class TestRecording(GameTestCase):

    def test_what_the_dialog_window_shows(self):
        self.cmd_menu.show_text_in_dialog_box(("Thou hast found the Silver Harp.", "Line two."))
        self.assertEqual([LogEntry("Thou hast found the Silver Harp."), LogEntry("Line two.")],
                         list(self.game.message_log.entries))

    def test_an_npc_says_a_quoted_line(self):
        with patch.dict(self.cmd_menu.dialog_lookup.lookup_table,
                        {'TantegelThroneRoom': {'GUARD_3': {'dialog': ("Hello.", "Goodbye.")}}}):
            self.cmd_menu.launch_dialog('GUARD_3', self.game.current_map)
        self.assertEqual([LogEntry("Hello.", 'GUARD'), LogEntry("Goodbye.", 'GUARD')],
                         list(self.game.message_log.entries))
        self.assertIsNone(self.cmd_menu.speaker)
        self.cmd_menu.show_text_in_dialog_box("Narration.")
        self.assertEqual(LogEntry("Narration."), self.game.message_log.entries[-1])

    def test_not_a_fight(self):
        self.cmd_menu.current_battle = object()
        self.addCleanup(setattr, self.cmd_menu, 'current_battle', None)
        self.cmd_menu.show_line_in_dialog_box("A Slime draws near!", skip_text=True)
        self.assertEqual(0, len(self.game.message_log))

    def test_not_a_temporary_message(self):
        self.game.draw_temporary_text("Game set to 2x speed.")
        self.assertEqual(0, len(self.game.message_log))


class TestTheKey(GameTestCase):

    def test_m_opens_it_on_the_map(self):
        with patch.object(self.game, 'open_message_log') as open_log:
            self.game.handle_keypresses(key(K_l))
        open_log.assert_called_once()
        self.assertFalse(self.game.message_log_requested)

    def test_not_with_the_option_off(self):
        self.game.config['MESSAGE_LOG'] = False
        with patch.object(self.game, 'open_message_log') as open_log:
            self.game.handle_keypresses(key(K_l))
        open_log.assert_not_called()
        self.assertFalse(self.game.message_log_requested)

    def test_it_waits_for_the_heros_step(self):
        self.game.player.is_moving = True
        with patch.object(self.game, 'open_message_log') as open_log:
            self.game.handle_keypresses(key(K_l))
            open_log.assert_not_called()
            self.assertTrue(self.game.movement.freeze_pending)
            self.game.player.is_moving = False
            self.game.movement.resolve_pending_freezes()
        open_log.assert_called_once()

    def test_start_while_pending_pauses_instead(self):
        self.game.player.is_moving = True
        with patch.object(self.game, 'open_message_log') as open_log:
            self.game.handle_keypresses(key(K_l))
            self.game.handle_keypresses(key(K_i))
            self.game.player.is_moving = False
            self.game.movement.resolve_pending_freezes()
        open_log.assert_not_called()
        self.assertTrue(self.game.paused)

    def test_not_while_a_window_is_open(self):
        self.cmd_menu.launch_signaled = True
        self.addCleanup(setattr, self.cmd_menu, 'launch_signaled', False)
        with patch.object(self.game, 'open_message_log') as open_log:
            self.game.handle_keypresses(key(K_l))
        open_log.assert_not_called()

    def test_rebound(self):
        controls = Controls.defaults()
        controls.bind_key('MESSAGE_LOG', 0, Binding(K_p))
        set_controls(controls)
        with patch.object(self.game, 'open_message_log') as open_log:
            self.game.handle_keypresses(key(K_l))
            open_log.assert_not_called()
            self.game.handle_keypresses(key(K_p))
        open_log.assert_called_once()

    def test_the_pad_button(self):
        self.assertEqual('x', Controls.defaults().pad['MESSAGE_LOG'])


class TestTheScreen(GameTestCase):

    def setUp(self):
        super().setUp()
        for number in range(30):
            self.game.message_log.record(f"Message {number}.")
        patch('src.selection.wait_frames').start()
        self.addCleanup(patch.stopall)

    def run_screen(self, *keys):
        screen = MessageLogScreen(self.game)
        events = [[key(pressed_key)] for pressed_key in keys]
        with patch('src.selection.event.get', side_effect=[[]] + events):
            screen.run()
        return screen

    def test_it_starts_at_the_newest(self):
        screen = MessageLogScreen(self.game)
        self.assertEqual(30 - VISIBLE_LINES, screen.top)
        self.assertEqual("Message 29.", screen.lines[-1])

    def test_scrolling(self):
        self.assertEqual(30 - VISIBLE_LINES - 2, self.run_screen(K_UP, K_UP, K_j).top)
        self.assertEqual(30 - VISIBLE_LINES, self.run_screen(K_UP, K_DOWN, K_DOWN, K_j).top)
        self.assertEqual(30 - 2 * VISIBLE_LINES, self.run_screen(K_LEFT, K_j).top)
        self.assertEqual(0, self.run_screen(K_LEFT, K_LEFT, K_LEFT, K_j).top)
        self.assertEqual(30 - VISIBLE_LINES, self.run_screen(K_LEFT, K_RIGHT, K_RIGHT, K_j).top)

    def test_closing(self):
        for close in (K_j, K_ESCAPE, K_i, K_l):
            with self.subTest(key=pygame.key.name(close)):
                self.run_screen(close)

    def test_time_stops_while_it_is_open(self):
        with patch.object(self.game, 'map_frame') as map_frame, \
                patch('src.selection.event.get', side_effect=[[], [], [key(K_j)]]):
            self.game.open_message_log()
        map_frame.assert_not_called()


class TestTheOption(TestCase):

    def test_the_row(self):
        row = next(row for row in OPTION_ROWS if row.config_key == 'MESSAGE_LOG')
        self.assertEqual(("MESSAGE LOG", (False, True), ("OFF (NES)", "ON")), (row.label, row.values, row.value_labels))

    def test_on_by_default_and_saved(self):
        self.assertTrue(DEFAULT_OPTIONS.message_log)
        self.assertTrue(options_from_save({}).message_log)
        off = DEFAULT_OPTIONS.__class__(message_log=False)
        self.assertEqual(off, options_from_save(options_to_save(off)))


class TestThePadButton(TestCase):

    def test_the_top_button_presses_m(self):
        from src.gamepad import Gamepad
        from tests.test_gamepad import FakeBackend, FakePad, pad
        pygame.init()
        pygame.display.set_mode((64, 64))
        pygame.event.clear()
        fake = FakePad()
        gamepad = Gamepad(FakeBackend(fake))
        gamepad.connect()
        self.addCleanup(gamepad.disconnect)
        gamepad.poll()
        fake.state = pad('x')
        gamepad.poll()
        self.assertEqual([K_l], [current_event.key for current_event in pygame.event.get(KEYDOWN)])
