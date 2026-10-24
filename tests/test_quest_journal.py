"""The quest journal (src/quest_journal.py): Q on the map, set by QUEST JOURNAL in the options overlay."""
import os
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from pygame import K_h, K_q, KEYDOWN
from pygame.event import Event

from src.common import set_gettext_language
from src.config.test_config import test_config
from src.quest_journal import GOALS, JOURNAL_GOALS, JOURNAL_HINTS, JOURNAL_OFF, OPTIONAL_HEADING, Progress, \
    journal_pages, journal_texts, open_goals
from src.story_flags import StoryFlags
from src.text import WRAP_LENGTH, DialogBoxWrapper
from tests import helpers

RESCUE = "Rescue Princess Gwaelin."
CARRY = "Carry Princess Gwaelin back to King Lorik."
KEY = "Get a Magic Key."
HARP = "Find the Silver Harp."
STAFF = "Take the Silver Harp to the old man in the shrine."
STONES = "Find the Stones of Sunlight."
TOKEN = "Find Erdrick's Token."
DROP = "Take the Stones of Sunlight, the Staff of Rain and Erdrick's Token to the old man in the shrine."
BRIDGE = "Use the Rainbow Drop to make a bridge to Charlock."
STAIRS = "Find the hidden way down in Charlock."
DRAGONLORD = "Defeat the Dragonlord."
HOME = "Return to King Lorik."
ARMOR = "Find Erdrick's Armor."
SWORD = "Find Erdrick's Sword."
GOLEM = "Defeat the Golem guarding Cantlin."


def goals(items=(), weapon='', armor='', **flags):
    return [goal.text for goal in open_goals(Progress.of(StoryFlags(**flags), items, weapon, armor))]


class TestOpenGoals(TestCase):

    def test_a_new_quest(self):
        self.assertEqual([RESCUE, KEY, HARP, STONES, TOKEN, ARMOR, GOLEM], goals(left_throne_room=True))

    def test_a_magic_key_drops_the_key_goal(self):
        self.assertNotIn(KEY, goals(["Magic Key"]))

    def test_carrying_gwaelin(self):
        self.assertEqual([CARRY, KEY, HARP, STONES, TOKEN], goals(carrying_gwaelin=True)[:5])

    def test_gwaelin_returned(self):
        open_ones = goals(["Gwaelin's Love"], gwaelin_returned=True)
        self.assertNotIn(RESCUE, open_ones)
        self.assertNotIn(CARRY, open_ones)

    def test_dying_with_gwaelin_puts_her_back_in_the_cave(self):
        # NES DeathText clears F_GOT_GWAELIN: she has to be rescued again
        self.assertEqual(RESCUE, goals()[0])

    def test_the_silver_harp_leads_to_the_staff_of_rain(self):
        open_ones = goals(["Silver Harp"])
        self.assertNotIn(HARP, open_ones)
        self.assertIn(STAFF, open_ones)
        open_ones = goals(["Staff of Rain"])
        self.assertNotIn(HARP, open_ones)
        self.assertNotIn(STAFF, open_ones)

    def test_the_rainbow_drop_needs_all_three(self):
        for missing in ("Staff of Rain", "Stones of Sunlight", "Erdrick's Token"):
            with self.subTest(missing=missing):
                held = {"Staff of Rain", "Stones of Sunlight", "Erdrick's Token"} - {missing}
                self.assertNotIn(DROP, goals(held))
        self.assertIn(DROP, goals(["Staff of Rain", "Stones of Sunlight", "Erdrick's Token"]))

    def test_the_rainbow_drop_means_the_three_were_found(self):
        # RnbwDrpDialog takes the Stones and the Staff; the Token is kept, but the drop alone is enough
        self.assertEqual([BRIDGE, ARMOR, GOLEM], goals(["Rainbow Drop", "Magic Key"], gwaelin_returned=True))

    def test_no_key_goal_once_every_locked_door_is_behind_the_hero(self):
        self.assertNotIn(KEY, goals(["Rainbow Drop"], gwaelin_returned=True))

    def test_the_bridge_opens_charlock(self):
        self.assertEqual([STAIRS, DRAGONLORD, ARMOR, SWORD, GOLEM],
                         goals(["Rainbow Drop"], gwaelin_returned=True, rainbow_bridge_built=True))
        self.assertEqual([DRAGONLORD], goals(["Rainbow Drop"], "Erdrick's Sword", "Erdrick's Armor",
                                             gwaelin_returned=True, rainbow_bridge_built=True,
                                             charlock_stairs_revealed=True, golem_defeated=True))

    def test_the_optional_goals(self):
        self.assertNotIn(ARMOR, goals(armor="Erdrick's Armor"))
        self.assertNotIn(GOLEM, goals(golem_defeated=True))
        self.assertNotIn(SWORD, goals())  # only once Charlock can be reached

    def test_after_the_dragonlord(self):
        self.assertEqual([HOME], goals(["Rainbow Drop"], rainbow_bridge_built=True, dragonlord_defeated=True))

    def test_there_is_always_something_to_do(self):
        # every story flag and item combination along the way leaves at least one goal open
        flag_names = [name for name in StoryFlags.__dataclass_fields__]
        for index in range(1 << len(flag_names)):
            flags = {name: bool(index >> bit & 1) for bit, name in enumerate(flag_names)}
            self.assertTrue(goals(**flags), flags)


class TestPages(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.font.init()

    def test_one_page_per_goal(self):
        progress = Progress.of(StoryFlags(), ["Magic Key"])
        self.assertEqual([RESCUE, HARP, STONES, TOKEN, OPTIONAL_HEADING + "\n" + ARMOR, GOLEM],
                         journal_pages(progress, hints=False))

    def test_hints_follow_each_goal(self):
        pages = journal_pages(Progress.of(StoryFlags(), ["Magic Key"]), hints=True)
        self.assertEqual([RESCUE, "She is held in the Swamp Cave, south of Kol, behind a locked door. A dragon guards "
                                  "her."], pages[:2])
        self.assertEqual(TOKEN, pages[6])
        self.assertTrue(pages[7].endswith("70 leagues to the south and 40 to the east, and search."))
        self.assertEqual(12, len(pages))

    def test_korean(self):
        _ = set_gettext_language('Korean')
        pages = journal_pages(Progress.of(StoryFlags(), ["Magic Key"]), hints=True, _=_)
        self.assertEqual(["로라 공주를 구출하자.", "마이라 남쪽 늪지 동굴의 잠긴 문 너머에 갇혀 있다. 드래곤이 지키고 있다."],
                         pages[:2])
        for text in journal_texts():
            self.assertNotEqual(text, _(text))

    def test_every_page_fits_the_dialog_box(self):
        # The dialog box fits 5 rows above the continue arrow (tests/test_control_info.py)
        for language in ('English', 'Korean'):
            _ = set_gettext_language(language)
            heading = _(OPTIONAL_HEADING) + "\n"
            pages = [(heading if goal.optional else "") + _(goal.text) for goal in GOALS] + [_(goal.hint) for goal in GOALS]
            for text in pages:
                rows = DialogBoxWrapper(width=WRAP_LENGTH, break_long_words=False).wrap(text)
                with self.subTest(language=language, text=text):
                    self.assertLessEqual(len(rows), 5)


class TestQKey(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.game = helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True})

    def press_q(self, setting):
        self.game.config['QUEST_JOURNAL'] = setting
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show:
            self.game.handle_keypresses(Event(KEYDOWN, key=K_q, mod=0))
        return show

    def test_off_is_the_nes(self):
        self.press_q(JOURNAL_OFF).assert_not_called()

    def test_goals(self):
        show = self.press_q(JOURNAL_GOALS)
        show.assert_called_once()
        self.assertEqual(RESCUE, show.call_args.args[0][0])

    def test_hints(self):
        pages = self.press_q(JOURNAL_HINTS).call_args.args[0]
        self.assertEqual([RESCUE, "She is held in the Swamp Cave, south of Kol, behind a locked door. A dragon guards "
                                  "her."], pages[:2])

    def test_follows_the_story(self):
        self.game.story_flags.carrying_gwaelin = True
        self.assertEqual(CARRY, self.press_q(JOURNAL_GOALS).call_args.args[0][0])

    def test_listed_in_the_help(self):
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show:
            self.game.handle_keypresses(Event(KEYDOWN, key=K_h, mod=0))
        self.assertIn("Q: Quest Journal", "\n".join(show.call_args.args[0]))
