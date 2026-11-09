"""The quest journal's records (src/records.py): Erdrick's Tablet and King Lorik's charge, kept to read again with Q."""
import os
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from pygame import K_q, KEYDOWN
from pygame.event import Event

from src.config.test_config import test_config
from src.cursor import IN_A, IN_B
from src.dungeon_map import DungeonMap
from src.languages import LANGUAGE_NAMES, language_named
from src.common import set_gettext_language
from src.message_log import text_width
from src.quest_journal import JOURNAL_HINTS, JOURNAL_LEARNED, KING_OPENING_SPEECH, NOTHING_HEARD, hear
from src.records import GOALS_ENTRY, JOURNAL_TITLE, JOURNAL_WINDOW_WIDTH, KING_LORIK_CHARGE, RECORDS, TABLET, \
    TABLET_COORDINATES, TABLET_HEADING, TABLET_LINES, TEXT_COLUMN, choose_journal_page, journal_layout, \
    king_lorik_charge, known_records, read
from src.selection import Answer
from src.story_flags import StoryFlags
from tests import helpers

TABLET_RECORD, KING_RECORD = RECORDS


def keys(records) -> list[str]:
    return [record.key for record in records]


class TestKnown(TestCase):

    def test_nothing_at_the_start(self):
        self.assertEqual([], known_records(StoryFlags(), DungeonMap()))

    def test_the_tablet_once_read(self):
        flags = StoryFlags()
        read(flags, TABLET)
        read(flags, TABLET)
        self.assertEqual([TABLET], flags.read_records)
        self.assertEqual([TABLET], keys(known_records(flags)))

    def test_the_tablet_seen_on_the_dungeon_map(self):
        # A save from before the records were kept: the dungeon map has seen the tablet's chest
        dungeon_map = DungeonMap.from_save({'ErdricksCaveB2': [12, 12, 'AAAAAAAAAAAAAAAAAAAA']})
        self.assertEqual([], known_records(StoryFlags(), dungeon_map))
        dungeon_map.floors['ErdricksCaveB2'].see(*TABLET_COORDINATES)
        self.assertEqual([TABLET], keys(known_records(StoryFlags(), dungeon_map)))

    def test_king_loriks_charge_once_heard(self):
        self.assertEqual([KING_LORIK_CHARGE], keys(known_records(StoryFlags(left_throne_room=True))))
        flags = StoryFlags()
        hear(flags, KING_OPENING_SPEECH)
        self.assertEqual([KING_LORIK_CHARGE], keys(known_records(flags)))


class TestPages(TestCase):

    def test_the_tablet(self):
        self.assertEqual(TABLET_LINES, TABLET_RECORD.pages('Ed', str))

    def test_king_loriks_charge_names_the_hero(self):
        pages = KING_RECORD.pages('Ed', str)
        self.assertEqual("Now, Ed, thou must help us recover the Ball of Light and restore peace to our land.", pages[3])
        self.assertEqual("May the light shine upon thee, Ed.", pages[-1])

    def test_korean(self):
        _ = set_gettext_language('Korean')
        for record in RECORDS:
            for page, line in zip(record.pages('Ed', _), record.pages('Ed', str)):
                with self.subTest(record=record.key, line=line):
                    self.assertNotEqual(line, page)


class TestJournalWindow(TestCase):

    def test_layout(self):
        layout = journal_layout([GOALS_ENTRY, "ERDRICK'S TABLET", "KING LORIK"])
        self.assertEqual(4, layout.window.height)  # an entry a block, and a block for the borders
        self.assertEqual(JOURNAL_TITLE, layout.title.text)
        self.assertEqual(((1, 2), (1, 4), (1, 6)), layout.cursor_tiles)

    def test_every_entry_fits_in_every_language(self):
        room = 2 * JOURNAL_WINDOW_WIDTH - TEXT_COLUMN - 1  # tiles from the text column to the right border
        for language in LANGUAGE_NAMES:
            _ = set_gettext_language(language)
            for text in [GOALS_ENTRY, JOURNAL_TITLE] + [record.title for record in RECORDS]:
                with self.subTest(language=language, text=text):
                    self.assertLessEqual(text_width(_(text)), room)
        set_gettext_language('English')


class GameTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.game = helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True})


class TestInTheGame(GameTestCase):

    def test_reading_the_tablet_keeps_it(self):
        cmd_menu = self.game.cmd_menu
        with patch.object(cmd_menu, 'show_text_in_dialog_box') as show, patch.object(cmd_menu, 'open_chest'):
            cmd_menu.take_tablet()
        self.assertEqual((cmd_menu.found_item_text('Tablet'), TABLET_HEADING) + TABLET_LINES, show.call_args.args[0])
        self.assertEqual([TABLET], self.game.story_flags.read_records)

    def test_king_loriks_speech_is_the_records(self):
        king = self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']
        self.assertEqual(king_lorik_charge(self.game.player.name), king['dialog'])

    def test_choosing_in_the_journal_window(self):
        records = [TABLET_RECORD, KING_RECORD]
        for answer, chosen in ((Answer(IN_A, 0), GOALS_ENTRY), (Answer(IN_A, 1), TABLET_RECORD),
                               (Answer(IN_A, 2), KING_RECORD), (Answer(IN_B, 1), None)):
            with self.subTest(answer=answer), patch('src.records.run_selection', return_value=answer):
                self.assertEqual(chosen, choose_journal_page(self.game, records))


class TestQKey(GameTestCase):

    def press_q(self, chosen=None, setting=JOURNAL_LEARNED):
        self.game.config['QUEST_JOURNAL'] = setting
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show, \
                patch('src.map_hotkeys.choose_journal_page', return_value=chosen) as choose:
            self.game.handle_keypresses(Event(KEYDOWN, key=K_q, mod=0))
        return show, choose

    def test_without_records_the_goals_at_once(self):
        show, choose = self.press_q()
        choose.assert_not_called()
        self.assertEqual([NOTHING_HEARD], show.call_args.args[0])

    def test_with_a_record_the_journal_window_first(self):
        read(self.game.story_flags, TABLET)
        show, choose = self.press_q(TABLET_RECORD)
        self.assertEqual([TABLET_RECORD], choose.call_args.args[1])
        self.assertEqual(list(TABLET_LINES), show.call_args.args[0])

    def test_goals_from_the_journal_window(self):
        read(self.game.story_flags, TABLET)
        show, _ = self.press_q(GOALS_ENTRY, JOURNAL_HINTS)
        self.assertEqual([NOTHING_HEARD], show.call_args.args[0])

    def test_b_closes_the_journal_window(self):
        read(self.game.story_flags, TABLET)
        show, _ = self.press_q(None)
        show.assert_not_called()

    def test_king_loriks_charge_with_the_heros_name(self):
        self.game.story_flags.left_throne_room = True
        show, _ = self.press_q(KING_RECORD)
        self.assertEqual(list(king_lorik_charge(self.game.player.name)), show.call_args.args[0])


class TestLanguages(TestCase):

    def test_every_language_has_quote_marks(self):
        for language in LANGUAGE_NAMES:
            with self.subTest(language=language):
                self.assertTrue(language_named(language).quote("x"))
