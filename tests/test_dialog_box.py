import os
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame

from src.config.test_config import test_config
from src.dialog_box import DIALOG_COLUMNS, DIALOG_ROWS, SCROLL_FRAMES, CharacterStep, DialogBuffer, ScrollStep, \
    frames_per_character, plays_text_beep, tiles
from src.game import Game
from tests.mock_map import MockMap

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


def print_lines(buffer: DialogBuffer, text: str, quoted: bool, wait: bool = False) -> list:
    """Prints one message the way CommandMenu does, and returns every step."""
    steps = list(buffer.print_message(text, quoted))
    if wait:
        steps += list(buffer.start_wait())
        steps += list(buffer.finish_wait())
    else:
        steps += list(buffer.end_message())
    return steps


def beeps(steps) -> str:
    """The printed characters that beep."""
    return ''.join(step.char for step in steps if isinstance(step, CharacterStep) and step.beep)


class TestDialogBufferLayout(TestCase):

    def setUp(self) -> None:
        self.buffer = DialogBuffer()

    def test_window_is_8_rows_of_22(self):
        self.assertEqual(8, DIALOG_ROWS)
        self.assertEqual(22, DIALOG_COLUMNS)
        self.assertEqual([''] * 8, self.buffer.lines)

    def test_quoted_text_wraps_whole_words_with_an_indent(self):
        print_lines(self.buffer, "`Welcome to Tantegel Castle.’", quoted=True)
        self.assertEqual(['`Welcome to Tantegel', ' Castle.’'], self.buffer.visible_lines)

    def test_narration_uses_all_22_columns(self):
        print_lines(self.buffer, "Thou hast found the Silver Harp.", quoted=False)
        self.assertEqual(['Thou hast found the', 'Silver Harp.'], self.buffer.visible_lines)
        self.buffer.clear()
        print_lines(self.buffer, "abcdefghij abcdefghijk next", quoted=False)
        self.assertEqual(['abcdefghij abcdefghijk', 'next'], self.buffer.visible_lines)

    def test_newline_starts_a_new_row(self):
        print_lines(self.buffer, "A Slime draws near!\nCommand?\n", quoted=False)
        self.assertEqual(['A Slime draws near!', 'Command?'], self.buffer.visible_lines)
        self.assertEqual((2, 0), (self.buffer.row, self.buffer.column))

    def test_messages_stack_below_each_other(self):
        print_lines(self.buffer, "`Hello.’", quoted=True, wait=True)
        self.assertEqual(['`Hello.’'], self.buffer.visible_lines)
        # the arrow's row is where the next quoted message goes (no blank row for indented text)
        print_lines(self.buffer, "`Goodbye.’", quoted=True)
        self.assertEqual(['`Hello.’', '`Goodbye.’'], self.buffer.lines[:2])

    def test_narration_leaves_a_blank_row_after_a_wait(self):
        print_lines(self.buffer, "Thou hast found the Tablet.", quoted=False, wait=True)
        print_lines(self.buffer, "The tablet reads as follows:", quoted=False)
        self.assertEqual(['Thou hast found the', 'Tablet.', '', 'The tablet reads as', 'follows:'],
                         self.buffer.lines[:5])

    def test_battle_messages_do_not_leave_blank_rows(self):
        print_lines(self.buffer, "Erdrick attacks!\n", quoted=False)
        print_lines(self.buffer, "The Slime's Hit Points have been reduced by 3.\n", quoted=False)
        self.assertEqual(['Erdrick attacks!', "The Slime's Hit Points", 'have been reduced by', '3.'],
                         self.buffer.visible_lines)

    def test_wait_puts_arrow_on_the_next_row(self):
        list(self.buffer.print_message("`Hello.’", True))
        list(self.buffer.start_wait())
        self.assertEqual(1, self.buffer.row)

    def test_window_scrolls_up_one_row_at_a_time(self):
        for number in range(8):
            print_lines(self.buffer, f"Line {number}.", quoted=False)
        # the eighth message ends on the bottom row, so ending it scrolls the window
        self.assertEqual([f'Line {number}.' for number in range(1, 8)] + [''], self.buffer.lines)
        self.assertEqual(7, self.buffer.row)
        steps = print_lines(self.buffer, "Line 8.", quoted=False)
        self.assertEqual([f'Line {number}.' for number in range(2, 9)] + [''], self.buffer.lines)
        self.assertEqual(1, sum(isinstance(step, ScrollStep) for step in steps))

    def test_long_message_scrolls_mid_message(self):
        text = "`" + " ".join(["word"] * 40) + "’"
        steps = print_lines(self.buffer, text, quoted=True)
        self.assertTrue(any(isinstance(step, ScrollStep) for step in steps))
        self.assertTrue(self.buffer.lines[-1] == '')
        self.assertTrue(all(len(line) <= DIALOG_COLUMNS for line in self.buffer.lines))
        self.assertTrue(self.buffer.lines[-2].endswith('word’'))

    def test_clear_empties_the_window(self):
        print_lines(self.buffer, "`Hello.’", quoted=True)
        self.buffer.clear()
        self.assertEqual([], self.buffer.visible_lines)
        self.assertEqual((0, 0), (self.buffer.row, self.buffer.column))

    def test_blank_at_start_of_row_is_dropped(self):
        steps = print_lines(self.buffer, "abcdefghijklmnopqrstuv wxyz", quoted=False)
        self.assertEqual(['abcdefghijklmnopqrstuv', 'wxyz'], self.buffer.visible_lines)
        self.assertEqual(len('abcdefghijklmnopqrstuvwxyz'), sum(isinstance(step, CharacterStep) for step in steps))


class TestTextBeep(TestCase):

    def test_beep_on_odd_columns_of_quoted_text(self):
        steps = print_lines(DialogBuffer(), "`Hello.’", quoted=True)
        # ` H e l l o .’ in columns 0-6 (.’ is one tile, TXT_PRD_QUOTE): H(1), l(3), o(5)
        self.assertEqual('Hlo', beeps(steps))
        # ? and ’ are two tiles: ` H i ? ’ puts ’ in column 4
        self.assertEqual('H?', beeps(print_lines(DialogBuffer(), "`Hi?’", quoted=True)))
        self.assertEqual('H.’', beeps(print_lines(DialogBuffer(), "`Hi.’", quoted=True)))

    def test_blanks_do_not_beep_and_do_not_shift_the_cadence(self):
        steps = print_lines(DialogBuffer(), "`a b c d’", quoted=True)
        # ` a _ b _ c _ d ’: a(1), b(3), c(5), d(7) all odd; the blanks in the even columns
        self.assertEqual('abcd', beeps(steps))
        steps = print_lines(DialogBuffer(), "`ab cd’", quoted=True)
        # ` a b _ c d ’: a(1), the blank in column 3, d(5)
        self.assertEqual('ad', beeps(steps))

    def test_narration_does_not_beep(self):
        self.assertEqual('', beeps(print_lines(DialogBuffer(), "Thou hast found 5 GOLD.", quoted=False)))
        self.assertEqual('', beeps(print_lines(DialogBuffer(), "A Slime draws near!\nCommand?\n", quoted=False)))

    def test_wrapped_rows_keep_the_column_parity(self):
        steps = print_lines(DialogBuffer(), "`Welcome to Tantegel Castle.’", quoted=True)
        second_row = [step for step in steps if isinstance(step, CharacterStep) and step.row == 1]
        # ' Castle.’' starts in column 1, so C, s, l, .’ beep
        self.assertEqual('Csl.’', ''.join(step.char for step in second_row if step.beep))

    def test_beep_count_for_a_message(self):
        text = "`Welcome to Tantegel Castle.’"
        steps = print_lines(DialogBuffer(), text, quoted=True)
        printed = [step for step in steps if isinstance(step, CharacterStep)]
        beeping = [step for step in printed if step.beep]
        self.assertEqual(sum(1 for step in printed if step.char != ' ' and step.column % 2 == 1), len(beeping))
        self.assertEqual(13, len(beeping))

    def test_period_and_end_quote_are_one_tile(self):
        self.assertEqual(['`', 'H', 'i', '.’'], tiles('`Hi.’'))
        self.assertEqual(['.', '.', '?', '’'], tiles('..?’'))
        self.assertEqual(['.', '.’'], tiles('..’'))
        buffer = DialogBuffer()
        steps = print_lines(buffer, "`Hello.’", quoted=True)
        self.assertEqual(7, sum(1 for step in steps if isinstance(step, CharacterStep)))
        self.assertEqual(['`Hello.’'], buffer.visible_lines)
        # 21 letters and .’ fill all 22 columns of a narration row
        buffer = DialogBuffer()
        list(buffer.print_message('a' * 21 + '.’', quoted=False))
        self.assertEqual((0, 22), (buffer.row, buffer.column))

    def test_plays_text_beep(self):
        self.assertTrue(plays_text_beep('a', 1, indented=True))
        self.assertFalse(plays_text_beep('a', 2, indented=True))
        self.assertFalse(plays_text_beep(' ', 1, indented=True))
        self.assertFalse(plays_text_beep('a', 1, indented=False))


class TestMessageSpeed(TestCase):

    def test_frames_per_character(self):
        self.assertEqual(1, frames_per_character('Fast'))
        self.assertEqual(2, frames_per_character('Normal'))
        self.assertEqual(3, frames_per_character('Slow'))
        self.assertEqual(2, frames_per_character('unknown'))

    def test_scroll_takes_5_frames(self):
        self.assertEqual(5, SCROLL_FRAMES)


class TestCommandMenuDialog(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()
        cls.screen = pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self) -> None:
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        # a loaded save sets these in the shared test config (Game.load_game)
        test_config['TEXT_SPEED'] = 'Fast'
        test_config['DIALOG_STYLE'] = 'Classic'
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.game.current_map = MockMap(self.game.config)
        self.game.current_map.load_map(self.game.player, (0, 0), self.game.game_state.config["TILE_SIZE"])
        self.cmd_menu = self.game.cmd_menu

    def test_lines_visible_after_each_message(self):
        seen = []
        original = self.cmd_menu.wait_for_dialog_key

        def record(*args):
            seen.append(self.cmd_menu.dialog_buffer.visible_lines)
            original(*args)

        with patch.object(self.cmd_menu, 'wait_for_dialog_key', side_effect=record):
            self.cmd_menu.show_text_in_dialog_box(("Welcome to Tantegel Castle.", "Thou hast a key.",
                                                   "Goodbye."), add_quotes=True, skip_text=True)
        self.assertEqual([['`Welcome to Tantegel', ' Castle.’'],
                          ['`Welcome to Tantegel', ' Castle.’', '`Thou hast a key.’'],
                          ['`Welcome to Tantegel', ' Castle.’', '`Thou hast a key.’', '`Goodbye.’']], seen)
        # the window closed, so it is empty again
        self.assertEqual([], self.cmd_menu.dialog_buffer.visible_lines)

    def test_new_conversation_starts_empty(self):
        self.cmd_menu.dialog_buffer.rows[0][0] = 'x'
        with patch.object(self.cmd_menu, 'window_drop_up_effect'):
            self.cmd_menu.show_text_in_dialog_box("Hello.", add_quotes=True, skip_text=True)
        self.assertEqual(['`Hello.’'], self.cmd_menu.dialog_buffer.visible_lines)

    def test_nested_text_carries_on_without_drop_down(self):
        with patch.object(self.cmd_menu, 'window_drop_up_effect'):
            self.cmd_menu.show_text_in_dialog_box("Hello.", add_quotes=True, skip_text=True)
            self.cmd_menu.show_text_in_dialog_box("Again.", add_quotes=True, skip_text=True, drop_down=False)
        self.assertEqual(['`Hello.’', '`Again.’'], self.cmd_menu.dialog_buffer.visible_lines)

    def test_battle_text_scrolls_in_a_fresh_window(self):
        self.cmd_menu.show_line_in_dialog_box("Something from before.", add_quotes=False, skip_text=True)
        self.cmd_menu.show_line_in_battle_dialog_box("A Slime draws near!\nCommand?\n")
        for _ in range(4):
            self.cmd_menu.show_line_in_dialog_box("Erdrick attacks!\n", add_quotes=False, skip_text=True,
                                                  hide_arrow=True, disable_sound=True)
        self.assertEqual(['A Slime draws near!', 'Command?'] + ['Erdrick attacks!'] * 4,
                         self.cmd_menu.dialog_buffer.visible_lines)
        for _ in range(3):
            self.cmd_menu.show_line_in_dialog_box("Erdrick attacks!\n", add_quotes=False, skip_text=True,
                                                  hide_arrow=True, disable_sound=True)
        # 9 rows of text in an 8-row window: the first two have scrolled off the top, the bottom row is empty
        self.assertEqual(['Erdrick attacks!'] * 7, self.cmd_menu.dialog_buffer.visible_lines)

    def text_beeps(self, text, **kwargs):
        with patch.object(self.cmd_menu.sound, 'play_sfx') as play_sfx:
            self.cmd_menu.show_line_in_dialog_box(text, skip_text=True, hide_arrow=True, **kwargs)
        return [call for call in play_sfx.call_args_list
                if call.args[0] == self.cmd_menu.directories.text_beep_sfx]

    def test_beep_cadence_in_dialog(self):
        # `Welcome to Tantegel Castle.’ beeps in every odd column that isn't blank: W l o e t a t g l / C s l .’
        self.assertEqual(13, len(self.text_beeps("Welcome to Tantegel Castle.")))
        # `Hello.’ is 7 tiles, since .’ is one (TXT_PRD_QUOTE): H, l and o are in odd columns, .’ in column 6
        self.assertEqual(3, len(self.text_beeps("Hello.")))

    def test_beep_cuts_off_the_last_one_a_frame_early(self):
        # TextToPPU -> DoSFX silences the playing beep at once; the next NMI draws the character and starts the new
        # beep (UpdateSound), and the rest of the MessageSpeed + 1 frames follow
        self.game.game_state.config['NO_WAIT'] = False
        self.game.game_state.config['TEXT_SPEED'] = 'Normal'
        events = []
        try:
            with patch.object(self.cmd_menu.sound, 'stop_sfx', side_effect=lambda: events.append('stop')), \
                    patch.object(self.cmd_menu.sound, 'play_sfx', side_effect=lambda path: events.append('beep')), \
                    patch.object(self.cmd_menu, 'wait_dialog_frames', side_effect=lambda n: events.append(n)), \
                    patch.object(self.cmd_menu, 'draw_dialog_window'), \
                    patch.object(self.cmd_menu, 'draw_dialog_row',
                                 side_effect=lambda row, up_to_column: events.append(f'draw {up_to_column}')):
                self.cmd_menu.show_line_in_dialog_box("Hi.", skip_text=True, hide_arrow=True)
        finally:
            self.game.game_state.config['NO_WAIT'] = True
            self.game.game_state.config['TEXT_SPEED'] = 'Fast'
        # `Hi.’: ` (column 0), H (1, beeps), i (2), .’ (3, beeps)
        self.assertEqual([1, 'draw 1', 1,
                          'stop', 1, 'beep', 'draw 2', 1,
                          1, 'draw 3', 1,
                          'stop', 1, 'beep', 'draw 4', 1], events)

    def test_play_sfx_restarts_on_its_own_channel(self):
        channel = MagicMock()
        self.cmd_menu.sound.config['SOUND_ENABLED'] = True
        try:
            with patch('src.sound.sfx_channel', return_value=channel):
                self.cmd_menu.sound.play_sfx(self.cmd_menu.directories.text_beep_sfx)
                self.cmd_menu.sound.play_sfx(self.cmd_menu.directories.text_beep_sfx)
                self.cmd_menu.sound.stop_sfx()
        finally:
            self.cmd_menu.sound.config['SOUND_ENABLED'] = test_config['SOUND_ENABLED']
        # Channel.play replaces whatever the channel was playing, like DoSFX taking over the SFX slot
        self.assertEqual(2, channel.play.call_count)
        channel.stop.assert_called_once()

    def test_no_beep_for_narration_or_disabled_sound(self):
        self.assertEqual([], self.text_beeps("Thou hast found the Tablet.", add_quotes=False))
        self.assertEqual([], self.text_beeps("Hello.", disable_sound=True))

    def test_frame_waits_per_character(self):
        self.game.game_state.config['NO_WAIT'] = False
        try:
            for speed, frames in (('Fast', 1), ('Normal', 2), ('Slow', 3)):
                self.game.game_state.config['TEXT_SPEED'] = speed
                with patch.object(self.cmd_menu, 'wait_dialog_frames') as wait_frames:
                    self.cmd_menu.show_line_in_dialog_box("Hi there.", skip_text=True, hide_arrow=True)
                # `Hi there.’ is 10 tiles (.’ is one); the blank goes through TextToPPU's wait too. Each tile shows up
                # at the first of its frames (the NMI after TextToPPU), then waits out the rest
                per_tile = [1] if frames == 1 else [1, frames - 1]
                self.assertEqual(per_tile * 10, [call.args[0] for call in wait_frames.call_args_list])
                self.cmd_menu.dialog_buffer.clear()
        finally:
            self.game.game_state.config['NO_WAIT'] = True
            self.game.game_state.config['TEXT_SPEED'] = 'Fast'

    def test_scroll_waits_5_frames(self):
        self.game.game_state.config['NO_WAIT'] = False
        try:
            for _ in range(7):
                list(self.cmd_menu.dialog_buffer.print_message("x", False))
                list(self.cmd_menu.dialog_buffer.end_message())
            with patch.object(self.cmd_menu, 'wait_dialog_frames') as wait_frames:
                self.cmd_menu.show_line_in_dialog_box("x", add_quotes=False, skip_text=True, hide_arrow=True)
            # one character (1 frame at Fast), then ending the message on the bottom row scrolls the window
            self.assertEqual([1] + [1] * SCROLL_FRAMES, [call.args[0] for call in wait_frames.call_args_list])
        finally:
            self.game.game_state.config['NO_WAIT'] = True
