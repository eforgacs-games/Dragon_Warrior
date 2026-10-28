"""The quest journal (src/quest_journal.py): Q on the map, set by QUEST JOURNAL in the options overlay. It lists the
goals the hero has learned of: told by an NPC, found out (the item held, the place reached, the enemy met) or done."""
import json
import os
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from pygame import K_h, K_q, KEYDOWN
from pygame.event import Event

from src.common import set_gettext_language
from src.config.test_config import test_config
from src.guardians import GOLEM
from src.maps import map_lookup
from src.quest_journal import DONE_FORMAT, GOALS, GOLEM_FIGHT, JOURNAL_HINTS, JOURNAL_LEARNED, JOURNAL_OFF, \
    KING_OPENING_SPEECH, NOTHING_HEARD, OPTIONAL_HEADING, THRONE_ROOM_KEY_ADVICE, Progress, hear, journal_pages, \
    journal_texts, open_goals, told_lines
from src.save_file import SaveFile
from src.save_state import decode_snapshot, take_snapshot
from src.story_flags import StoryFlags, story_bits
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
GOLEM_GOAL = "Defeat the Golem guarding Cantlin."

# Garin's grave and the Silver Harp (Brecconary: the mobile fighter at 3,26)
HARP_RUMOR = 0x27
HARP_RUMOR_LINE = "Some say that Garin's grave is home to a Silver Harp."
# The Staff of Rain shrine's old man
STAFF_SHRINE = 0x6C
# A Magic Key shop: no words to quote
KEY_SHOP = 0x0E


def done(text: str) -> str:
    return DONE_FORMAT.format(text)


def told(*sources, **flags) -> StoryFlags:
    story_flags = StoryFlags(**flags)
    for source in sources:
        hear(story_flags, source)
    return story_flags


def pages(flags: StoryFlags | None = None, items=(), weapon='', armor='', hints=False) -> list[str]:
    return journal_pages(Progress.of(flags or StoryFlags(), items, weapon, armor), hints=hints)


def open_texts(flags: StoryFlags | None = None, items=(), weapon='', armor='') -> list[str]:
    return [goal.text for goal in open_goals(Progress.of(flags or StoryFlags(), items, weapon, armor))]


class TestLearning(TestCase):

    def test_nothing_known_at_the_start(self):
        self.assertEqual([NOTHING_HEARD], pages())

    def test_king_loriks_opening_speech_tells_of_the_dragonlord(self):
        self.assertEqual([DRAGONLORD], pages(told(KING_OPENING_SPEECH)))
        # and so has any hero who has left the throne room, which the speech always comes before
        self.assertEqual([DRAGONLORD], pages(StoryFlags(left_throne_room=True)))

    def test_an_npc_line_unlocks_its_goal(self):
        self.assertEqual([HARP], pages(told(HARP_RUMOR)))

    def test_one_npc_can_tell_of_two_goals(self):
        self.assertEqual([HARP, STAFF], pages(told(STAFF_SHRINE)))

    def test_an_npc_who_tells_of_nothing(self):
        self.assertEqual([NOTHING_HEARD], pages(told(0x21, 0x45, None)))  # "Welcome to Tantegel Castle." and radishes

    def test_obtaining_the_item_unlocks_its_goal_as_done(self):
        self.assertEqual([done(HARP)], pages(items=["Silver Harp"]))
        self.assertEqual([done(TOKEN)], pages(items=["Erdrick's Token"]))

    def test_holding_a_key_tells_of_keys(self):
        self.assertEqual([done(KEY)], pages(items=["Magic Key"]))

    def test_the_rainbow_drop_tells_of_the_bridge(self):
        self.assertEqual(BRIDGE, pages(StoryFlags(gwaelin_returned=True), ["Rainbow Drop"])[0])

    def test_carrying_gwaelin(self):
        self.assertEqual([CARRY, done(RESCUE)], pages(StoryFlags(carrying_gwaelin=True)))

    def test_meeting_the_golem(self):
        self.assertEqual([OPTIONAL_HEADING + "\n" + GOLEM_GOAL], pages(told(GOLEM_FIGHT)))

    def test_completed_goals_show_done_after_the_open_ones(self):
        flags = told(HARP_RUMOR, STAFF_SHRINE, 0x54, KING_OPENING_SPEECH)
        self.assertEqual([STAFF, STONES, DRAGONLORD, done(HARP)], pages(flags, ["Silver Harp"]))

    def test_a_goal_heard_of_stays_known_once_done(self):
        flags = told(0x37, golem_defeated=True)
        self.assertEqual([done(GOLEM_GOAL)], pages(flags))

    def test_the_throne_room_guard_tells_of_the_key_only_before_the_hero_leaves(self):
        self.assertEqual([KEY], pages(told(THRONE_ROOM_KEY_ADVICE)))
        self.assertEqual([DRAGONLORD], pages(told(THRONE_ROOM_KEY_ADVICE, left_throne_room=True)))

    def test_the_first_teller_is_kept_unless_it_had_no_words(self):
        flags = told(0x17, 0x26)
        self.assertEqual(0x17, flags.heard_goals['magic_key'])
        flags = told(KEY_SHOP, 0x26)
        self.assertEqual(0x26, flags.heard_goals['magic_key'])
        flags = told(0x26, KEY_SHOP)
        self.assertEqual(0x26, flags.heard_goals['magic_key'])

    def test_after_the_dragonlord(self):
        # the optional goals and the rescue can't be done any more: only what was done stays
        flags = told(0x37, 0x47, 0x3F, 0x40, dragonlord_defeated=True, rainbow_bridge_built=True)
        shown = pages(flags, ["Rainbow Drop"])
        self.assertEqual(HOME, shown[0])
        self.assertIn(done(DRAGONLORD), shown)
        self.assertEqual([HOME], open_texts(flags, ["Rainbow Drop"]))
        for missed in (RESCUE, ARMOR, SWORD, GOLEM_GOAL):
            self.assertNotIn(missed, shown)
            self.assertNotIn(done(missed), shown)
        self.assertIn(done(SWORD), pages(flags, ["Rainbow Drop"], weapon="Erdrick's Sword"))

    def test_the_key_goal_follows_the_locked_doors(self):
        # done while a key is held or no locked door is left in the way
        flags = told(0x17)
        self.assertEqual([KEY], pages(flags))
        self.assertEqual([done(KEY)], pages(flags, ["Magic Key"]))
        self.assertNotIn(KEY, open_texts(told(0x17, gwaelin_returned=True), ["Rainbow Drop"]))


class TestHints(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.font.init()

    def test_hints_show_the_npcs_words(self):
        self.assertEqual([HARP, HARP_RUMOR_LINE], pages(told(HARP_RUMOR), hints=True))

    def test_without_words_the_goals_own_hint(self):
        self.assertEqual([KEY, "Magic Keys are sold in Tantegel Castle, Rimuldar and Cantlin."],
                         pages(told(KEY_SHOP), hints=True))
        self.assertEqual([CARRY, "King Lorik waits in Tantegel Castle.", done(RESCUE)],
                         pages(StoryFlags(carrying_gwaelin=True), hints=True))

    def test_no_hint_after_a_done_goal(self):
        self.assertEqual([done(HARP)], pages(told(HARP_RUMOR), ["Silver Harp"], hints=True))

    def test_korean(self):
        _ = set_gettext_language('Korean')
        self.assertEqual(["은 하프를 찾자.", _(HARP_RUMOR_LINE)],
                         journal_pages(Progress.of(told(HARP_RUMOR), []), hints=True, _=_))
        self.assertEqual([_(NOTHING_HEARD)], journal_pages(Progress.of(StoryFlags(), []), hints=True, _=_))
        for text in journal_texts() + told_lines():
            self.assertNotEqual(text, _(text))

    def test_every_page_fits_the_dialog_box(self):
        # The dialog box fits 5 rows above the continue arrow (tests/test_control_info.py). The NPCs' words aren't
        # checked: they're shown as the NPC shows them, scrolling on as they do then.
        for language in ('English', 'Korean'):
            _ = set_gettext_language(language)
            heading = _(OPTIONAL_HEADING) + "\n"
            texts = ([(heading if goal.optional else "") + _(goal.text) for goal in GOALS] +
                     [_(DONE_FORMAT).format(_(goal.done_text)) for goal in GOALS] +
                     [_(goal.hint) for goal in GOALS] + [_(NOTHING_HEARD)])
            for text in texts:
                rows = DialogBoxWrapper(width=WRAP_LENGTH, break_long_words=False).wrap(text)
                with self.subTest(language=language, text=text):
                    self.assertLessEqual(len(rows), 5)


class TestOldSaves(TestCase):

    def test_an_old_save_has_heard_nothing(self):
        bits = {name: False for name in story_bits()}
        flags = StoryFlags.from_save({'StoryFlags': bits})
        self.assertEqual({}, flags.heard_goals)

    def test_an_old_save_still_knows_what_it_has_done_and_holds(self):
        flags = StoryFlags.from_save({'StoryFlags': {'gwaelin_returned': True, 'left_throne_room': True}})
        self.assertEqual([DRAGONLORD, done(RESCUE), done(CARRY), done(STONES)],
                         pages(flags, ["Stones of Sunlight", "Gwaelin's Love"]))

    def test_a_save_from_before_the_story_flags_entry(self):
        flags = StoryFlags.from_save({'Inventory': ["Gwaelin's Love"]})
        self.assertEqual({}, flags.heard_goals)
        self.assertIn(done(RESCUE), pages(flags))

    def test_bad_entries_are_left_out(self):
        flags = StoryFlags.from_save({'StoryFlags': {'heard_goals': {'silver_harp': 39, 'golem': [1], '3': None}}})
        self.assertEqual({'silver_harp': 39}, flags.heard_goals)
        self.assertEqual({}, StoryFlags.from_save({'StoryFlags': {'heard_goals': 'harp'}}).heard_goals)


class GameTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.game = helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True})


class TestInTheGame(GameTestCase):

    def talk_to(self, map_name: str, npc_name: str) -> None:
        game = self.game
        current_map = SimpleNamespace(identifier=map_name)
        with patch.object(game.cmd_menu, 'show_text_in_dialog_box'):
            game.cmd_menu.run_dialog(npc_name, current_map)

    def test_talking_to_an_npc_unlocks_the_goal(self):
        self.talk_to('Brecconary', 'SOLDIER_2')  # dialog byte $27
        self.assertEqual({'silver_harp': HARP_RUMOR}, self.game.story_flags.heard_goals)

    def test_the_golem_fight_counts_as_meeting_him(self):
        with patch('src.game.guardian_at', return_value=GOLEM), \
                patch.object(self.game.battle_ctrl, 'queue_scripted_battle'):
            self.game.check_guardian_fight()
        self.assertEqual({'golem': GOLEM_FIGHT}, self.game.story_flags.heard_goals)

    def test_saved_and_loaded_with_the_adventure_log(self):
        hear(self.game.story_flags, HARP_RUMOR)
        hear(self.game.story_flags, GOLEM_FIGHT)
        saved = json.loads(json.dumps({'Name': 'Ed', 'Experience': 0, 'Gold': 0, 'Inventory': [],
                                       'StoryFlags': self.game.story_flags.to_save()}))
        loaded = SaveFile.from_save(saved).story_flags
        self.assertEqual({'silver_harp': HARP_RUMOR, 'golem': GOLEM_FIGHT}, loaded.heard_goals)
        self.assertEqual([HARP, OPTIONAL_HEADING + "\n" + GOLEM_GOAL], pages(loaded))

    def test_kept_in_save_states(self):
        hear(self.game.story_flags, HARP_RUMOR)
        snapshot = json.loads(json.dumps(take_snapshot(self.game)))
        hear(self.game.story_flags, GOLEM_FIGHT)
        restored = decode_snapshot(snapshot)['story_flags']
        self.assertEqual({'silver_harp': HARP_RUMOR}, restored.heard_goals)
        # a copy: hearing more after the state was taken doesn't change it
        self.assertIsNot(restored.heard_goals, self.game.story_flags.heard_goals)


class TestQKey(GameTestCase):

    def press_q(self, setting):
        self.game.config['QUEST_JOURNAL'] = setting
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show:
            self.game.handle_keypresses(Event(KEYDOWN, key=K_q, mod=0))
        return show

    def test_off_is_the_nes(self):
        self.press_q(JOURNAL_OFF).assert_not_called()

    def test_nothing_heard_at_the_start(self):
        self.assertEqual([NOTHING_HEARD], self.press_q(JOURNAL_LEARNED).call_args.args[0])

    def test_learned(self):
        hear(self.game.story_flags, HARP_RUMOR)
        self.assertEqual([HARP], self.press_q(JOURNAL_LEARNED).call_args.args[0])

    def test_learned_with_hints(self):
        hear(self.game.story_flags, HARP_RUMOR)
        self.assertEqual([HARP, HARP_RUMOR_LINE], self.press_q(JOURNAL_HINTS).call_args.args[0])

    def test_follows_the_story(self):
        self.game.story_flags.carrying_gwaelin = True
        self.assertEqual(CARRY, self.press_q(JOURNAL_LEARNED).call_args.args[0][0])

    def test_listed_in_the_help(self):
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show:
            self.game.handle_keypresses(Event(KEYDOWN, key=K_h, mod=0))
        self.assertIn("Q: Quest Journal", "\n".join(show.call_args.args[0]))


class TestNpcTables(TestCase):

    def test_every_npc_source_is_an_npcs_dialog_byte(self):
        bytes_in_maps = {npc.dialog for map_class in map_lookup.values()
                         for npc in getattr(map_class, 'npc_table', ())}
        for goal in GOALS:
            for teller in goal.told_by:
                if isinstance(teller.source, int):
                    with self.subTest(goal=goal.key, source=hex(teller.source)):
                        self.assertIn(teller.source, bytes_in_maps)
