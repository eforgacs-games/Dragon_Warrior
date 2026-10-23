"""The generated name entry screen (src/name_entry.py) against the 72 NES screenshots it replaces, 0 differing pixels
at every scale (see tests/nes_screen_diff.py), and the NES name entry input (WndEnterName)."""
import os
import tempfile
from unittest import TestCase
from unittest.mock import MagicMock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame  # noqa: E402
from pygame import K_BACKSPACE, K_DOWN, K_ESCAPE, K_RETURN, K_RIGHT, K_TAB, K_UP, K_LEFT, K_j, K_k, \
    KEYDOWN  # noqa: E402

from src.color import RED, WHITE  # noqa: E402
from src.config.test_config import test_config  # noqa: E402
from src.directories import Directories  # noqa: E402
from src.menu_functions import NameSelection  # noqa: E402
from src.name_entry import BACK, END, NameEntry, render_name_entry_screen  # noqa: E402
from src.windows import ALPHABET_COLUMNS, ALPHABET_ROWS  # noqa: E402
from tests.nes_screen_diff import compare_with_screenshot  # noqa: E402

SCALES = (1, 2, 3)
DIFF_DIR = os.path.join(tempfile.gettempdir(), 'dragon_warrior_screen_diffs')
# The alphabet's characters in screenshot order (0_upper_A.png to 60_period.png), then BACK and END
ALPHABET = ''.join(ALPHABET_ROWS)


def name_selection_screenshots(directories: Directories) -> tuple[list[str], list[str]]:
    """The 63 screenshots with the cursor on each entry (in selection order: the alphabet, BACK, END) and the 9
    without a cursor, with 0 to 8 characters entered (their slots are blank: the game drew the name over them)."""
    folder = os.path.dirname(directories.NAME_SELECTION_UPPER_A)
    files = sorted(os.listdir(folder), key=lambda file_name: int(file_name.split('_')[0]))
    paths = [os.path.join(folder, file_name) for file_name in files]
    return paths[:63], paths[63:]


def entry_at(index: int) -> NameEntry:
    """A new name entry with the cursor on the index-th entry of the screenshots (the alphabet, BACK, END)."""
    entry = NameEntry()
    if index < len(ALPHABET):
        entry.move_to(ALPHABET[index])
    elif index == len(ALPHABET):
        entry.row, entry.column = len(ALPHABET_ROWS) - 1, 6
    else:
        entry.move_to_end()
    return entry


def entry_with_blanks(length: int) -> NameEntry:
    entry = NameEntry()
    for _ in range(length):
        entry.enter(' ')
    return entry


class TestNameEntryScreen(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.cursor_screenshots, cls.length_screenshots = name_selection_screenshots(Directories(test_config))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def assert_matches(self, entry, screenshot, nes_pixel, cursor_visible, color=WHITE):
        generated = render_name_entry_screen(entry, color, nes_pixel, cursor_visible)
        name = f'name_entry_{os.path.basename(screenshot)[:-4]}_{nes_pixel}'
        result = compare_with_screenshot(generated, screenshot, nes_pixel, window_color=color, diff_dir=DIFF_DIR,
                                         name=name)
        self.assertEqual(0, result.differing_pixels, str(result))

    def test_there_are_72_screenshots(self):
        self.assertEqual(63, len(self.cursor_screenshots))
        self.assertTrue(self.cursor_screenshots[61].endswith('61_BACK.png'))
        self.assertTrue(self.cursor_screenshots[62].endswith('62_END.png'))
        self.assertEqual(9, len(self.length_screenshots))

    def test_cursor_on_every_entry(self):
        for scale in SCALES:
            for index, screenshot in enumerate(self.cursor_screenshots):
                with self.subTest(scale=scale, screenshot=os.path.basename(screenshot)):
                    self.assert_matches(entry_at(index), screenshot, scale, cursor_visible=True)

    def test_every_name_length(self):
        for scale in SCALES:
            for length, screenshot in enumerate(self.length_screenshots):
                with self.subTest(scale=scale, length=length):
                    self.assert_matches(entry_with_blanks(length), screenshot, scale, cursor_visible=None)

    def test_cursor_hidden_on_every_entry(self):
        # The "off" half of the blink blanks the cursor's tile: the screenshot without a cursor, wherever it is
        for index in range(len(self.cursor_screenshots)):
            with self.subTest(entry=index):
                self.assert_matches(entry_at(index), self.length_screenshots[0], 2, cursor_visible=False)

    def test_low_hp_red(self):
        # Not shown in the game (the title screen is white), but the palette swap is exact too
        self.assert_matches(entry_at(0), self.cursor_screenshots[0], 2, cursor_visible=True, color=RED)

    def test_a_different_screen_differs(self):
        generated = render_name_entry_screen(entry_at(0), WHITE, 1, True)
        self.assertGreater(compare_with_screenshot(generated, self.cursor_screenshots[1], 1).differing_pixels, 0)
        generated = render_name_entry_screen(entry_with_blanks(1), WHITE, 1, None)
        self.assertGreater(compare_with_screenshot(generated, self.length_screenshots[0], 1).differing_pixels, 0)

    def test_drawn_by_name_selection(self):
        # What the game actually draws on its screen, at its own scale
        config = dict(test_config, NO_BLIT=False)
        screen = pygame.Surface((256 * config['SCALE'], 240 * config['SCALE']))
        with patch('src.menu_functions.display'):
            NameSelection(config).draw(screen, entry_at(len(ALPHABET) + 1), cursor_visible=True)
        result = compare_with_screenshot(screen, self.cursor_screenshots[62], config['SCALE'], diff_dir=DIFF_DIR,
                                         name='name_entry_game_end')
        self.assertEqual(0, result.differing_pixels, str(result))


class TestNameEntryCursor(TestCase):
    """WndUpPressed, WndDownPressed, WndDoLeftPressed, WndRightPressed and WndSpclMoveCrsr."""

    def test_selection_results(self):
        entry = NameEntry()
        for index, character in enumerate(ALPHABET):
            entry.move_to(character)
            self.assertEqual(index, entry.cursor_index)
            self.assertEqual(character, entry.selection)
        entry.row, entry.column = 5, 6
        self.assertEqual((61, BACK), (entry.cursor_index, entry.selection))
        entry.move_to_end()
        self.assertEqual((64, END), (entry.cursor_index, entry.selection))

    def test_edges(self):
        entry = NameEntry()
        self.assertFalse(entry.move_up())
        self.assertFalse(entry.move_left())
        entry.column = ALPHABET_COLUMNS - 1
        self.assertFalse(entry.move_right())
        entry.move_to_end()
        self.assertFalse(entry.move_down())
        self.assertFalse(entry.move_right())

    def test_down_to_back_and_end(self):
        for character, selection in (('q', '.'), ('r', BACK), ('s', BACK), ('t', END), ('u', END),
                                     ('v', END), ('l', 'w')):
            with self.subTest(character=character):
                entry = NameEntry()
                entry.move_to(character)
                self.assertTrue(entry.move_down())
                self.assertEqual(selection, entry.selection)

    def test_up_from_back_and_end_keeps_the_column(self):
        entry = NameEntry()
        entry.move_to('s')
        entry.move_down()
        entry.move_up()
        self.assertEqual('r', entry.selection)
        entry.move_to('v')
        entry.move_down()
        entry.move_up()
        self.assertEqual('u', entry.selection)

    def test_left_and_right_along_the_last_row(self):
        entry = NameEntry()
        entry.move_to('.')
        self.assertTrue(entry.move_right())
        self.assertEqual(BACK, entry.selection)
        self.assertTrue(entry.move_right())
        self.assertEqual(END, entry.selection)
        self.assertTrue(entry.move_left())
        self.assertEqual(BACK, entry.selection)
        self.assertTrue(entry.move_left())
        self.assertEqual('.', entry.selection)


class TestNameEntryName(TestCase):
    """WndProcessChar, WndDoBackspace, WndMaxNameLength and WndStorePlyrName."""

    def test_enter_and_end(self):
        entry = NameEntry()
        for character in 'Ed':
            entry.move_to(character)
            entry.select()
        self.assertFalse(entry.finished)
        entry.move_to_end()
        entry.select()
        self.assertTrue(entry.finished)
        self.assertEqual('Ed', entry.name)

    def test_the_8th_character_ends_the_name(self):
        entry = NameEntry()
        for character in 'Erdrick':
            entry.enter(character)
        self.assertFalse(entry.finished)
        entry.enter('s')
        self.assertTrue(entry.finished)
        entry.enter('x')
        self.assertEqual('Erdricks', entry.name)

    def test_back_keeps_the_character(self):
        # WndDoBackspace only moves the index back: END keeps what's after it
        entry = NameEntry()
        for character in 'Abc':
            entry.enter(character)
        entry.back()
        entry.back()
        self.assertEqual(1, entry.index)
        self.assertEqual(['A', 'b', 'c'], entry.characters[:3])
        entry.enter('x')
        entry.end()
        self.assertEqual('Axc', entry.name)

    def test_back_at_the_start(self):
        entry = NameEntry()
        entry.back()
        entry.erase()
        self.assertEqual(0, entry.index)

    def test_select_back(self):
        entry = NameEntry()
        entry.enter('A')
        entry.row, entry.column = 5, 6
        entry.select()
        self.assertEqual(0, entry.index)
        self.assertEqual('A', entry.name)

    def test_erase_removes_the_character(self):
        entry = NameEntry()
        entry.enter('A')
        entry.enter('B')
        entry.erase()
        self.assertEqual('A', entry.name)
        self.assertEqual([None] * 7, entry.characters[1:])

    def test_blanks(self):
        entry = NameEntry()
        for character in 'A B ':
            entry.enter(character)
        self.assertEqual('A B', entry.name)


def key_event(key: int, unicode: str = '') -> MagicMock:
    current_event = MagicMock()
    current_event.type = KEYDOWN
    current_event.key = key
    current_event.unicode = unicode
    return current_event


class TestSelectName(TestCase):
    """NameSelection.select_name, with the keyboard and with joystick input."""

    def setUp(self):
        self.config = dict(test_config, NO_BLIT=True)
        self.command_menu = MagicMock()
        self.command_menu.game.game_state.config = self.config
        self.screen = pygame.Surface((256, 240))

    def select_name(self, events: list) -> str:
        with patch('src.menu_functions.event.get', side_effect=[[current_event] for current_event in events]), \
                patch('src.menu_functions.display'), patch('src.menu_functions.Sound'):
            return NameSelection(self.config).select_name(0, self.screen, self.command_menu)

    def test_typed(self):
        self.assertEqual('Ed', self.select_name([key_event(pygame.K_e, 'E'), key_event(pygame.K_d, 'd'),
                                                 key_event(K_RETURN)]))

    def test_typed_backspace_and_ignored_characters(self):
        self.assertEqual('Eo', self.select_name([key_event(pygame.K_e, 'E'), key_event(pygame.K_d, 'd'),
                                                 key_event(K_BACKSPACE), key_event(pygame.K_5, '5'),
                                                 key_event(pygame.K_o, 'o'), key_event(K_RETURN)]))

    def test_return_needs_a_name(self):
        self.assertEqual('A', self.select_name([key_event(K_RETURN), key_event(pygame.K_a, 'A'),
                                                key_event(K_RETURN)]))

    def test_typed_8th_character_ends_the_name(self):
        self.assertEqual('Lorikeet', self.select_name([key_event(0, character) for character in 'Lorikeet']))

    def test_joystick(self):
        # Tab, then: A on A, right, A on B, B (back), down, A on M, then down 4 times to w, right 6 times to END, A
        events = [key_event(K_TAB), key_event(K_k), key_event(K_RIGHT), key_event(K_k), key_event(K_j),
                  key_event(K_DOWN), key_event(K_k)]
        events += [key_event(K_DOWN)] * 4 + [key_event(K_LEFT)] + [key_event(K_RIGHT)] * 7 + [key_event(K_UP),
                                                                                               key_event(K_DOWN)]
        events += [key_event(K_k)]
        with patch('src.menu_functions.toggle_joystick_input', return_value=True):
            self.assertEqual('AM', self.select_name(events))

    def test_escape_while_typing_leaves_the_name_entry(self):
        self.assertIsNone(self.select_name([key_event(pygame.K_e, 'E'), key_event(K_ESCAPE, '\x1b')]))

    def test_escape_with_joystick_input_leaves_the_name_entry(self):
        # Escape is not the B button here (it would only delete the A): the name entry is left
        with patch('src.menu_functions.toggle_joystick_input', return_value=True):
            self.assertIsNone(self.select_name([key_event(K_TAB), key_event(K_k), key_event(K_ESCAPE, '\x1b')]))

    def test_j_with_joystick_input_still_goes_back_one_character(self):
        # A on A, A on A, B (J): back one character, then right and A on B, then down 5 and right 8 to END, A
        events = [key_event(K_TAB), key_event(K_k), key_event(K_k), key_event(K_j), key_event(K_RIGHT), key_event(K_k)]
        events += [key_event(K_DOWN)] * 5 + [key_event(K_RIGHT)] * 8 + [key_event(K_k)]
        with patch('src.menu_functions.toggle_joystick_input', return_value=True):
            self.assertEqual('AB', self.select_name(events))
