"""The party (src/party.py): the HEROES option, the second hero's name at a new quest, and the second hero kept with
the adventure log and the save states."""
import json
import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

import pygame

from src.config.test_config import test_config
from src.game_options import GLOBAL_OPTIONS, PARTY
from src.options_overlay import PRESET_MODERN, PRESET_NES, preset_values
from src.party import PAIR, SOLO, new_hero, party_of, starts_as_party
from src.save_file import COMPANION_KEY, SAVE_FORMAT_VERSION, VERSION_KEY, HeroSave, SaveFile, companion_from_save
from src.save_state import decode_snapshot, restore_snapshot, take_snapshot
from src.settings import Settings
from src.title_menu import BACK_TO_TITLE_MENU
from tests import helpers


class GameTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.addCleanup(patch.stopall)
        self.game = helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True})


class TestTheOption(TestCase):

    def test_one_hero_on_the_nes(self):
        self.assertEqual(SOLO, PARTY.default)
        self.assertIn(PARTY, GLOBAL_OPTIONS)
        self.assertEqual(SOLO, Settings().party)
        self.assertNotIn('PARTY', preset_values(PRESET_NES))  # co-op isn't a convenience: no preset sets it
        self.assertNotIn('PARTY', preset_values(PRESET_MODERN))

    def test_kept_with_the_global_settings(self):
        self.assertEqual(PAIR, Settings.from_json({'party': 2}).party)
        self.assertEqual(SOLO, Settings.from_json({'party': 3}).party)  # not a choice: the default

    def test_starts_as_party(self):
        self.assertTrue(starts_as_party({'PARTY': 2}))
        self.assertFalse(starts_as_party({'PARTY': 1}))
        self.assertFalse(starts_as_party({}))


class TestTheSecondHero(GameTestCase):

    def test_made_from_their_own_name(self):
        """Ann starts with 13 HP and strength 3, as the first hero would (tests/test_game.py)."""
        hero = new_hero(self.game, 'Ann')
        self.assertEqual(('Ann', 1, 13, 13), (hero.name, hero.level, hero.current_hp, hero.max_hp))
        self.assertEqual(3, hero.attack_power)
        self.assertIsNot(self.game.player, hero)

    def test_no_god_mode(self):
        game = helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True,
                                 'GOD_MODE': True})
        self.assertEqual(1, new_hero(game, 'Ann').level)

    def test_the_party(self):
        self.assertEqual([self.game.player], self.game.party)
        self.game.companion = new_hero(self.game, 'Ann')
        self.assertEqual([self.game.player, self.game.companion], self.game.party)
        self.assertEqual([self.game.player], party_of(self.game.player, None))


class TestANewQuest(GameTestCase):

    def begin(self, *names):
        with patch.object(self.game.title_menu, 'select_adventure_log'), \
                patch('src.title_menu.NameSelection') as name_selection, \
                patch.object(self.game.title_menu, 'choose_new_quest_options'), \
                patch.object(self.game, 'start_at_throne_room'):
            name_selection.return_value.select_name.side_effect = list(names)
            result = self.game.title_menu.begin_new_quest()
        return result, name_selection.return_value.select_name

    def test_one_hero(self):
        self.game.config['PARTY'] = SOLO
        self.game.companion = new_hero(self.game, 'Old')  # from a log played before
        result, select_name = self.begin('Ann')
        self.assertIsNone(result)
        self.assertEqual(1, select_name.call_count)
        self.assertEqual('Ann', self.game.player.name)
        self.assertIsNone(self.game.companion)

    def test_two_heroes(self):
        self.game.config['PARTY'] = PAIR
        result, select_name = self.begin('Ann', 'Bob')
        self.assertIsNone(result)
        self.assertEqual("Now the second hero's name.\n", select_name.call_args_list[1].kwargs['prompt'])
        self.assertEqual(('Ann', 'Bob'), (self.game.player.name, self.game.companion.name))
        self.assertEqual(1, self.game.companion.level)

    def test_escape_in_the_second_name_cancels_the_quest(self):
        self.game.config['PARTY'] = PAIR
        name = self.game.player.name
        result, _ = self.begin('Ann', None)
        self.assertIs(BACK_TO_TITLE_MENU, result)
        self.assertEqual(name, self.game.player.name)
        self.assertIsNone(self.game.companion)


GWEN = HeroSave(name='Gwen', experience=7000, inventory=['Torch', None, 'Herb'], current_hp=60, current_mp=24,
                weapon='Copper Sword', armor='Chain Mail', shield='Small Shield', wearing_fighters_ring=True,
                spells=['HEAL', 'HURT', 'SLEEP', 'RADIANT'])


class TestTheAdventureLog(GameTestCase):

    def save_and_read(self) -> dict:
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.game.cmd_menu.directories.save_dir = tmp_dir
            self.game.player.adventure_log = 2
            self.assertTrue(self.game.cmd_menu.save())
            with open(os.path.join(tmp_dir, 'save_slot_2.json')) as save_file:
                return json.load(save_file)

    def test_saved_and_loaded(self):
        self.game.companion = new_hero(self.game, 'Gwen')
        GWEN.restore(self.game.companion)
        save = self.save_and_read()
        self.assertEqual(SAVE_FORMAT_VERSION, save[VERSION_KEY])
        self.assertEqual(GWEN.to_save(), save[COMPANION_KEY])
        self.assertNotIn('Gold', save[COMPANION_KEY])  # the party's gold is the first hero's
        loaded = helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True})
        with patch.object(loaded.map_mgr, 'change_map'):
            loaded.load_game(save)
        companion = loaded.companion
        self.assertEqual(('Gwen', 7000, 60, 24), (companion.name, companion.total_experience, companion.current_hp,
                                                  companion.current_mp))
        self.assertEqual(('Copper Sword', 'Chain Mail', 'Small Shield'),
                         (companion.weapon, companion.armor, companion.shield))
        self.assertEqual(['Torch', None, 'Herb'], companion.inventory.with_empty_slots())
        self.assertEqual(GWEN.spells, companion.spells)
        self.assertEqual(companion.get_level_by_experience(), companion.level)

    def test_one_hero_has_no_companion_entry(self):
        self.assertNotIn(COMPANION_KEY, self.save_and_read())

    def test_loading_a_log_with_one_hero_leaves_the_party(self):
        self.game.companion = new_hero(self.game, 'Gwen')
        with patch.object(self.game.map_mgr, 'change_map'):
            self.game.load_game({"Name": "Erdrick", "Experience": 0, "Gold": 0, "Inventory": []})
        self.assertIsNone(self.game.companion)

    def test_a_damaged_companion_is_none(self):
        for record in ('Gwen', {'Name': 'Gwen'}, None):
            with self.subTest(record=record):
                self.assertIsNone(companion_from_save({COMPANION_KEY: record}))

    def test_restoring_copies_the_spells(self):
        hero = new_hero(self.game, 'Gwen')
        GWEN.restore(hero)
        hero.spells.append('HEALMORE')
        self.assertEqual(['HEAL', 'HURT', 'SLEEP', 'RADIANT'], GWEN.spells)

    def test_round_trip(self):
        save = SaveFile(name='Ann', experience=0, gold=5, inventory=[], companion=GWEN)
        self.assertEqual(save, SaveFile.from_save(json.loads(json.dumps(save.to_save()))))


class TestTheSaveStates(GameTestCase):

    def test_kept_and_put_back(self):
        self.game.companion = new_hero(self.game, 'Gwen')
        GWEN.restore(self.game.companion)
        snapshot = json.loads(json.dumps(take_snapshot(self.game)))
        self.game.companion.current_hp = 1
        restore_snapshot(self.game, snapshot, fade_in=False)
        self.assertEqual(('Gwen', 60), (self.game.companion.name, self.game.companion.current_hp))
        self.game.companion = None
        restore_snapshot(self.game, snapshot, fade_in=False)
        self.assertEqual('Gwen', self.game.companion.name)

    def test_one_hero(self):
        snapshot = json.loads(json.dumps(take_snapshot(self.game)))
        self.assertIsNone(snapshot['companion'])
        self.game.companion = new_hero(self.game, 'Gwen')
        restore_snapshot(self.game, snapshot, fade_in=False)
        self.assertIsNone(self.game.companion)

    def test_a_version_4_state_has_one_hero(self):
        snapshot = json.loads(json.dumps(take_snapshot(self.game)))
        del snapshot['companion']
        snapshot['version'] = 4
        self.assertIsNone(decode_snapshot(snapshot)['companion'])
