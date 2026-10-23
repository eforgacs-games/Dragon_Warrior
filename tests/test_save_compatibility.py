"""Saves from every format load in this build (#434): the adventure logs (src/save_file.py) and the save states
(src/save_state.py). tests/sample_saves/ keeps a sample of each format; a format change adds the sample of the format
it replaces, with what it should load as below."""
import json
import os
import re
import shutil
import tempfile
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from src.config.test_config import test_config
from src.options_screen import Options
from src.save_file import SAVE_FORMAT_VERSION, VERSION_KEY, SaveFile, migrate_save, save_format_version, write_save
from src.save_state import STATE_FORMAT_VERSION, VERSION_KEY as STATE_VERSION_KEY, read_state, state_path
from src.story_flags import StoryFlags
from tests import helpers

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), 'sample_saves')
ADVENTURE_LOGS_DIR = os.path.join(SAMPLES_DIR, 'adventure_logs')
SAVE_STATES_DIR = os.path.join(SAMPLES_DIR, 'save_states')
SAMPLE_NAME = re.compile(r'version_(\d+)(_.*)?\.json')
STATE_SAMPLE_NAME = re.compile(r'state_version_(\d+)\.json')

# What each sample adventure log loads as: (name, experience, gold, HP, MP), (weapon, armor, shield), the slots (None
# for an emptied one), the spells, the story flags and the options
EXPECTED_LOGS = {
    # The first JSON saves (2023): name, experience, gold and the items. HP and MP are full, and the save could only
    # be made after leaving the throne room
    'version_0_2023_first_json.json': (
        ('Ed', 7, 120, None, None), ('', '', ''), ['Torch', 'Herb', 'Herb'], [],
        StoryFlags(left_throne_room=True), Options()),
    # 2026-06: HP, MP, the equipment, the spells and the position
    'version_0_2026_06_stats_and_position.json': (
        ('Loto', 1100, 250, 40, 12), ('Copper Sword', 'Chain Mail', 'Small Shield'),
        ['Torch', 'Magic Key', 'Wings', "Dragon's Scale"], ['HEAL', 'HURT', 'SLEEP'],
        StoryFlags(left_throne_room=True), Options()),
    # 2026-10: the worn Dragon's Scale and Fighter's Ring, and the Rainbow Bridge and Charlock stairs as flat keys;
    # Gwaelin's Love means she was returned
    'version_0_2026_10_flat_story_keys.json': (
        ('Erdrick', 26000, 3000, 120, 80), ('Flame Sword', 'Magic Armor', 'Large Shield'),
        ["Dragon's Scale", "Fighter's Ring", "Gwaelin's Love", 'Rainbow Drop', 'Herb'],
        ['HEAL', 'HURT', 'SLEEP', 'RADIANT', 'STOPSPELL', 'OUTSIDE', 'RETURN', 'REPEL', 'HEALMORE'],
        StoryFlags(rainbow_bridge_built=True, gwaelin_returned=True, left_throne_room=True), Options()),
    # 2026-10: the StoryFlags entry (before the green dragon's flag), the first options, the curse flags, and the
    # inventory packed, as before #390
    'version_0_2026_10_story_flags_packed_inventory.json': (
        ('Gwen', 4000, 900, 60, 30), ('Broad Sword', 'Half Plate', 'Large Shield'),
        ['Torch', 'Cursed Belt', 'Silver Harp', 'Magic Key', 'Magic Key'],
        ['HEAL', 'HURT', 'SLEEP', 'RADIANT', 'STOPSPELL'],
        StoryFlags(gwaelin_returned=True, left_throne_room=True, golem_defeated=True),
        Options('Slow', 'Modern', False)),
    # The last saves before the format version: every option, and the inventory's slots with an emptied one (#390)
    'version_0_2026_10_empty_slots_all_options.json': (
        ('Lora', 9000, 1500, 90, 50), ('Hand Axe', 'Full Plate', 'Silver Shield'),
        ['Torch', None, 'Fairy Flute', 'Magic Key'], ['HEAL', 'HURT'],
        StoryFlags(rainbow_bridge_built=True, left_throne_room=True, green_dragon_defeated=True),
        Options('Fast', 'Classic', True, 'Smooth', False, 'HalfHP')),
    'version_1.json': (
        ('Gwaelin', 12000, 2400, 100, 70), ('Broad Sword', 'Magic Armor', 'Silver Shield'),
        ["Dragon's Scale", None, 'Silver Harp', 'Wings', 'Herb', 'Magic Key'],
        ['HEAL', 'HURT', 'SLEEP', 'RADIANT', 'STOPSPELL', 'OUTSIDE', 'RETURN'],
        StoryFlags(gwaelin_returned=True, left_throne_room=True),
        Options('Normal', 'Modern', True, 'NES', True, 'ThreeQuartersHP')),
}


def sample_logs() -> list[str]:
    return sorted(name for name in os.listdir(ADVENTURE_LOGS_DIR) if name.endswith('.json'))


def read_sample(name: str) -> dict:
    with open(os.path.join(ADVENTURE_LOGS_DIR, name)) as sample:
        return json.load(sample)


def sample_version(name: str) -> int:
    match = SAMPLE_NAME.fullmatch(name)
    assert match is not None, f"{name}: sample adventure logs are named version_<n>[_<what>].json"
    return int(match.group(1))


class GameTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()

    def setUp(self):
        self.save_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.save_dir, True)
        self.addCleanup(patch.stopall)

    def new_game(self):
        # A copy of test_config: loading a save applies its options to the config
        game = helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True,
                                 'SAVE_DIR': self.save_dir})
        patch.object(game, 'draw_temporary_text').start()
        return game


class TestSampleAdventureLogs(GameTestCase):

    def test_every_sample_is_checked(self):
        self.assertEqual(sorted(EXPECTED_LOGS), sample_logs())

    def test_there_is_a_sample_of_every_format(self):
        self.assertEqual(set(range(SAVE_FORMAT_VERSION + 1)), {sample_version(name) for name in sample_logs()})
        for name in sample_logs():
            with self.subTest(name):
                self.assertEqual(sample_version(name), save_format_version(read_sample(name)))

    def test_every_sample_reads_as_expected(self):
        for name, expected in EXPECTED_LOGS.items():
            with self.subTest(name):
                save = SaveFile.from_save(read_sample(name))
                stats, equipment, slots, spells, story_flags, options = expected
                self.assertEqual(stats, (save.name, save.experience, save.gold, save.current_hp, save.current_mp))
                self.assertEqual(equipment, (save.weapon, save.armor, save.shield))
                self.assertEqual(slots, save.inventory)
                self.assertEqual(spells, save.spells)
                self.assertEqual(story_flags, save.story_flags)
                self.assertEqual(options, save.options)

    def test_every_sample_loads_in_the_game(self):
        for name, expected in EXPECTED_LOGS.items():
            with self.subTest(name):
                game = self.new_game()
                game.load_game(read_sample(name))
                player = game.player
                stats, equipment, slots, spells, story_flags, options = expected
                name_, experience, gold, current_hp, current_mp = stats
                self.assertEqual((name_, experience, gold), (player.name, player.total_experience, player.gold))
                if player.is_cursed:  # NES StartAtThroneRoom: a cursed hero always starts with 1 HP
                    current_hp = 1
                self.assertEqual(player.max_hp if current_hp is None else current_hp, player.current_hp)
                self.assertEqual(player.max_mp if current_mp is None else current_mp, player.current_mp)
                self.assertEqual(equipment, (player.weapon, player.armor, player.shield))
                self.assertEqual([item for item in slots if item is not None], player.inventory)
                self.assertEqual(slots, player.inventory.with_empty_slots())
                self.assertEqual(spells, player.spells)
                self.assertEqual(story_flags, game.story_flags)
                self.assertEqual('TantegelThroneRoom', game.current_map.identifier)

    def test_every_sample_saves_in_the_current_format(self):
        # Saved again, an older save is in the current format, and reads back as it read before
        for name in EXPECTED_LOGS:
            with self.subTest(name):
                save = SaveFile.from_save(read_sample(name))
                written = json.loads(json.dumps(save.to_save()))
                self.assertEqual(SAVE_FORMAT_VERSION, written[VERSION_KEY])
                self.assertEqual(save, SaveFile.from_save(written))
                self.assertEqual(written, migrate_save(written))

    def test_the_current_format_sample_is_what_this_build_writes(self):
        # Every key the sample has is written back as it is (a key added later with a default may come after them),
        # in the current format: when the format changes, this sample becomes the old format's and a new one is added
        name = f'version_{SAVE_FORMAT_VERSION}.json'
        sample = read_sample(name)
        path = os.path.join(self.save_dir, 'save_slot_1.json')
        write_save(path, SaveFile.from_save(sample).to_save())
        with open(path) as written_file:
            written = json.load(written_file)
        self.assertEqual(sample, {key: written[key] for key in sample})
        self.assertEqual(list(sample), [key for key in written if key in sample])  # in the same order

    def test_migrating_leaves_the_save_alone(self):
        save = read_sample('version_0_2026_10_flat_story_keys.json')
        before = json.dumps(save)
        migrate_save(save)
        self.assertEqual(before, json.dumps(save))

    def test_a_save_from_a_newer_build_loads_what_this_build_knows(self):
        save = {**read_sample(f'version_{SAVE_FORMAT_VERSION}.json'), VERSION_KEY: SAVE_FORMAT_VERSION + 1,
                'SomethingNew': [1, 2, 3]}
        with patch('builtins.print') as printed:
            loaded = SaveFile.from_save(save)
        self.assertIn('newer version', printed.call_args.args[0])
        self.assertEqual('Gwaelin', loaded.name)
        self.assertNotIn('SomethingNew', loaded.to_save())

    def test_a_version_that_isnt_a_number_is_version_0(self):
        for version in (None, 'one', -1, True, 1.5):
            with self.subTest(version):
                self.assertEqual(0, save_format_version({VERSION_KEY: version}))


class TestSampleSaveStates(GameTestCase):

    def sample_states(self) -> list[str]:
        return sorted(name for name in os.listdir(SAVE_STATES_DIR) if name.endswith('.json'))

    def test_there_is_a_sample_of_every_format(self):
        versions = set()
        for name in self.sample_states():
            match = STATE_SAMPLE_NAME.fullmatch(name)
            self.assertIsNotNone(match, f"{name}: sample states are named state_version_<n>.json")
            assert match is not None
            versions.add(int(match.group(1)))
            with open(os.path.join(SAVE_STATES_DIR, name)) as sample:
                self.assertEqual(int(match.group(1)), json.load(sample)[STATE_VERSION_KEY])
        # Version 1 is the first one (1.0)
        self.assertEqual(set(range(1, STATE_FORMAT_VERSION + 1)), versions)

    def test_every_sample_loads(self):
        # Each one: Gwen in Brecconary, with 321 gold, 180 experience and a Torch, an emptied slot, Fairy Water and
        # a Herb
        for name in self.sample_states():
            with self.subTest(name):
                shutil.copy(os.path.join(SAVE_STATES_DIR, name), state_path(self.save_dir, 2))
                game = self.new_game()
                self.assertIsNotNone(read_state(self.save_dir, 2))
                game.load_state(2)
                game.draw_temporary_text.assert_called_with("State 2 loaded")
                player = game.player
                self.assertEqual(('Gwen', 321, 180), (player.name, player.gold, player.total_experience))
                self.assertEqual(['Torch', None, 'Fairy Water', 'Herb'], player.inventory.with_empty_slots())
                self.assertEqual('Brecconary', game.current_map.identifier)
                self.assertTrue(game.story_flags.left_throne_room)
