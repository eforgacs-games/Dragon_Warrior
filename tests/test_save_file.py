"""The save file format (src/save_file.py): saves on disk and the playtest checkpoints read and write back unchanged."""
import json
import os
import tempfile
from unittest import TestCase

import pygame

from src.checkpoints import CHECKPOINT_NAMES, FACING_KEY, checkpoint_path
from src.config.test_config import test_config
from src.options_screen import Options
from src.save_file import SaveFile, first_open_log, log_for_unchosen_save, logs_named, save_files, save_slot_number, \
    used_logs, write_save
from src.story_flags import StoryFlags
from tests.helpers import new_game

# A save as CommandMenu.save writes it, byte for byte (json.dumps with indent=4, keys in this order)
CURRENT_FORMAT_SAVE = '''{
    "Name": "Erdrick",
    "Experience": 1350,
    "Gold": 412,
    "CurrentHP": 31,
    "CurrentMP": 7,
    "Weapon": "Copper Sword",
    "Armor": "Leather Armor",
    "Shield": "Small Shield",
    "WearingDragonScale": true,
    "WearingFightersRing": false,
    "WearingCursedBelt": false,
    "WearingDeathNecklace": false,
    "Inventory": [
        "Torch",
        "Magic Key",
        "Herb"
    ],
    "Spells": [
        "HEAL",
        "HURT"
    ],
    "CurrentMap": "TantegelThroneRoom",
    "PlayerRow": 10,
    "PlayerColumn": 13,
    "StoryFlags": {
        "charlock_stairs_revealed": false,
        "rainbow_bridge_built": false,
        "carrying_gwaelin": false,
        "gwaelin_returned": false,
        "death_necklace_found": false,
        "left_throne_room": true,
        "golem_defeated": false,
        "dragonlord_defeated": false,
        "green_dragon_defeated": false
    },
    "MessageSpeed": "Fast",
    "DialogStyle": "Modern",
    "NpcsMakeWay": false
}'''


class TestSaveFileRoundTrip(TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

    def test_a_current_format_save_round_trips_byte_for_byte(self):
        save = SaveFile.from_save(json.loads(CURRENT_FORMAT_SAVE))
        path = os.path.join(self.tmp_dir.name, 'save_slot_1.json')
        write_save(path, save.to_save())
        with open(path) as save_file:
            self.assertEqual(CURRENT_FORMAT_SAVE, save_file.read())

    def test_a_current_format_save_reads_every_field(self):
        save = SaveFile.from_save(json.loads(CURRENT_FORMAT_SAVE))
        self.assertEqual(('Erdrick', 1350, 412, 31, 7), (save.name, save.experience, save.gold, save.current_hp,
                                                          save.current_mp))
        self.assertEqual(('Copper Sword', 'Leather Armor', 'Small Shield'), (save.weapon, save.armor, save.shield))
        self.assertEqual((True, False, False, False), (save.wearing_dragon_scale, save.wearing_fighters_ring,
                                                       save.wearing_cursed_belt, save.wearing_death_necklace))
        self.assertEqual(['Torch', 'Magic Key', 'Herb'], save.inventory)
        self.assertEqual(['HEAL', 'HURT'], save.spells)
        self.assertEqual(('TantegelThroneRoom', 10, 13), (save.current_map, save.player_row, save.player_column))
        self.assertEqual(StoryFlags(left_throne_room=True), save.story_flags)
        self.assertEqual(Options('Fast', 'Modern', False), save.options)

    def test_every_checkpoint_round_trips(self):
        """A checkpoint has no HP, MP or options (they load as full, NORMAL, CLASSIC and ON) and may have Facing,
        which only load_checkpoint reads. Everything else it has is written back as it was, and reading what's
        written gives the same save."""
        for name in CHECKPOINT_NAMES:
            with self.subTest(name), open(checkpoint_path(name)) as checkpoint_file:
                checkpoint = json.load(checkpoint_file)
                save = SaveFile.from_save(checkpoint)
                written = save.to_save()
                for key, value in checkpoint.items():
                    if key != FACING_KEY:
                        self.assertEqual(value, written[key], key)
                self.assertEqual(save, SaveFile.from_save(json.loads(json.dumps(written, indent=4))))

    def test_older_saves_get_the_load_defaults(self):
        save = SaveFile.from_save({'Name': 'Ed', 'Experience': 0, 'Gold': 0, 'Inventory': [],
                                   'RainbowBridgeBuilt': True})
        self.assertEqual((None, None, '', '', ''), (save.current_hp, save.current_mp, save.weapon, save.armor,
                                                     save.shield))
        self.assertEqual(([], None, None, None), (save.spells, save.current_map, save.player_row, save.player_column))
        self.assertTrue(save.story_flags.rainbow_bridge_built)
        self.assertTrue(save.story_flags.left_throne_room)
        self.assertEqual(Options(), save.options)

    def test_missing_required_keys_raise(self):
        with self.assertRaises(KeyError):
            SaveFile.from_save({'Name': 'Ed', 'Experience': 0, 'Gold': 0})


class TestSaveFromTheGame(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()
        pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

    def test_loading_and_saving_a_save_writes_it_back_byte_for_byte(self):
        game = new_game()
        game.load_game(json.loads(CURRENT_FORMAT_SAVE))
        game.cmd_menu.directories.save_dir = self.tmp_dir.name
        game.player.adventure_log = 2
        game.cmd_menu.save()
        with open(os.path.join(self.tmp_dir.name, 'save_slot_2.json')) as save_file:
            self.assertEqual(CURRENT_FORMAT_SAVE, save_file.read())

    def test_every_checkpoint_loads_as_its_file_says(self):
        for name in CHECKPOINT_NAMES:
            with self.subTest(name), open(checkpoint_path(name)) as checkpoint_file:
                checkpoint = json.load(checkpoint_file)
                game = new_game()
                game.load_game(checkpoint)
                player = game.player
                self.assertEqual((checkpoint['Name'], checkpoint['Experience'], checkpoint['Gold']),
                                 (player.name, player.total_experience, player.gold))
                self.assertEqual(checkpoint['Inventory'], player.inventory)
                self.assertEqual((checkpoint['Weapon'], checkpoint['Armor'], checkpoint['Shield']),
                                 (player.weapon, player.armor, player.shield))
                self.assertEqual(StoryFlags.from_save(checkpoint), game.story_flags)
                self.assertEqual(checkpoint['CurrentMap'], game.current_map.identifier)


class TestSaveSlots(TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.save_dir = self.tmp_dir.name

    def write(self, log: int, name: str) -> None:
        write_save(os.path.join(self.save_dir, f'save_slot_{log}.json'), {'Name': name})

    def test_only_the_three_logs_are_save_files(self):
        for file_name in ('save_slot_0.json', 'save_slot_4.json', 'notes.txt'):
            open(os.path.join(self.save_dir, file_name), 'w').close()
        self.write(2, 'Ed')
        self.assertEqual(['save_slot_2.json'], save_files(self.save_dir))
        self.assertEqual([], save_files(os.path.join(self.save_dir, 'missing')))

    def test_save_slot_number(self):
        self.assertEqual(3, save_slot_number('save_slot_3.json'))
        with self.assertRaises(ValueError):
            save_slot_number('save_slot_4.json')

    def test_used_and_open_logs(self):
        self.write(1, 'Ed')
        self.write(3, 'Loto')
        self.assertEqual([(1, 'Ed'), (3, 'Loto')], used_logs(self.save_dir, save_files(self.save_dir)))
        self.assertEqual(2, first_open_log(self.save_dir))
        self.assertEqual([3], logs_named(self.save_dir, 'Loto'))

    def test_log_for_unchosen_save(self):
        self.write(1, 'Ed')
        self.assertEqual(1, log_for_unchosen_save(self.save_dir, 'Ed'))
        self.assertEqual(2, log_for_unchosen_save(self.save_dir, 'Loto'))
        self.write(2, 'Ed')
        self.assertIsNone(log_for_unchosen_save(self.save_dir, 'Ed'))
