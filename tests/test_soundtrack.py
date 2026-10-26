import json
import os
from unittest import TestCase
from unittest.mock import patch

import pygame

from src.config.base_config import base_config
from src.config.test_config import test_config
from src.directories import MUSIC_NAMES, Directories, music_name, music_paths
from src.options_screen import Options, apply_options, options_from_config, options_from_save, options_to_save
from src.paths import data_path
from src.save_state import restore_snapshot, take_snapshot
from src.smoke_test import game_file_paths
from src.soundtrack import DEFAULT_SOUNDTRACK, LEGACY_ORCHESTRA_CONFIG_KEY, LEGACY_ORCHESTRA_SAVE_KEY, SOUNDTRACK_KEY, \
    SOUNDTRACK_SAVE_KEY, SOUNDTRACKS, Soundtrack, migrate_legacy_music_config, soundtrack, soundtrack_from_save
from tests import helpers

SFC_DIR = data_path('sound', 'music', 'SFC')
# The jingles: the same NES clips with every soundtrack
JINGLE_NAMES = ('death_music', 'inn_music', 'princess_gwaelins_love_music', 'victory_music', 'level_up_music')


def sfc_track(name: str) -> str:
    return os.path.join(SFC_DIR, name)


class TestMusicPaths(TestCase):

    def test_every_soundtrack_names_every_music_and_every_file_exists(self):
        for chosen in SOUNDTRACKS:
            with self.subTest(soundtrack=chosen):
                paths = music_paths(chosen)
                self.assertEqual(set(MUSIC_NAMES), set(paths))
                for name, path in paths.items():
                    self.assertTrue(os.path.isfile(path), f"{name}: {path}")

    def test_each_soundtrack_plays_from_its_own_folder(self):
        # the NES's fight loop is in the sound effects folder, with the rest of the soundtrack's later tracks
        folders = {Soundtrack.NES: (data_path('sound', 'music', 'NES'), data_path('sound', 'sfx')),
                   Soundtrack.SFC: (SFC_DIR,), Soundtrack.ORCHESTRA: (data_path('sound', 'music', 'orchestra'),)}
        for chosen, allowed in folders.items():
            for name, path in music_paths(chosen).items():
                with self.subTest(soundtrack=chosen, music=name):
                    self.assertTrue(path.startswith(allowed), path)

    def test_the_sfc_soundtrack_maps_each_moment_to_its_track(self):
        paths = music_paths(Soundtrack.SFC)
        self.assertEqual({
            'intro_overture': sfc_track('09 Overture March (Original Game Sound).mp3'),
            'intermezzo': sfc_track('10 Intermezzo (SFC Version).mp3'),
            'tantegel_castle_throne_room_music': sfc_track('11 Chateau Ladutorm (SFC Version).mp3'),
            'tantegel_castle_courtyard_music': sfc_track('11 Chateau Ladutorm (SFC Version).mp3'),
            'village_music': sfc_track('12 People (SFC Version).mp3'),
            'overworld_music': sfc_track('13 Unknown World (SFC Version).mp3'),
            'battle_music': sfc_track('14 Fight (SFC Version).mp3'),
            'regular_fight_music': sfc_track('14 Fight (SFC Version).mp3'),
            'end_boss_music': sfc_track('16 King Dragon (SFC Version).mp3'),
            'ending_music': sfc_track('17 Finale (SFC Version).mp3'),
            **{f'dungeon_floor_{floor}_music': sfc_track('15 Dungeon (SFC Version).mp3') for floor in range(1, 9)},
        }, paths)

    def test_the_me_sound_collection_is_kept_but_not_played_yet(self):
        me_collection = sfc_track('18 ME Sound Collection.mp3')
        self.assertTrue(os.path.isfile(me_collection))
        self.assertNotIn(me_collection, music_paths(Soundtrack.SFC).values())

    def test_the_orchestra_folder_holds_only_the_orchestral_set(self):
        orchestra_dir = data_path('sound', 'music', 'orchestra')
        self.assertEqual(['01', '02', '03', '04', '05', '06', '07', '08', 'Android_iOS'],
                         sorted(name[:2] if name[0].isdigit() else name for name in os.listdir(orchestra_dir)))

    def test_every_soundtrack_uses_the_nes_jingles(self):
        nes = Directories({**test_config, SOUNDTRACK_KEY: Soundtrack.NES})
        for chosen in (Soundtrack.SFC, Soundtrack.ORCHESTRA):
            directories = Directories({**test_config, SOUNDTRACK_KEY: chosen})
            for name in JINGLE_NAMES:
                with self.subTest(soundtrack=chosen, jingle=name):
                    self.assertEqual(getattr(nes, name), getattr(directories, name))
                    self.assertIn(os.path.join('sound', 'sfx'), getattr(directories, name))

    def test_directories_follow_the_config(self):
        config = {**test_config, SOUNDTRACK_KEY: Soundtrack.NES}
        directories = Directories(config)
        for chosen in SOUNDTRACKS:
            config[SOUNDTRACK_KEY] = chosen
            self.assertEqual(music_paths(chosen)['overworld_music'], directories.overworld_music)

    def test_music_name_finds_the_map_music_in_every_soundtrack(self):
        for chosen in SOUNDTRACKS:
            with self.subTest(soundtrack=chosen):
                self.assertEqual('overworld_music', music_name(music_paths(chosen)['overworld_music']))
                # the NES intermezzo is the village music's file: a village's music is the village music
                self.assertEqual('village_music', music_name(music_paths(chosen)['village_music']))


class TestMigration(TestCase):

    def test_a_save_with_the_old_switch(self):
        self.assertEqual(Soundtrack.ORCHESTRA, soundtrack_from_save({LEGACY_ORCHESTRA_SAVE_KEY: True}))
        self.assertEqual(Soundtrack.NES, soundtrack_from_save({LEGACY_ORCHESTRA_SAVE_KEY: False}))
        self.assertEqual(DEFAULT_SOUNDTRACK, soundtrack_from_save({}))
        self.assertEqual(DEFAULT_SOUNDTRACK, soundtrack_from_save({SOUNDTRACK_SAVE_KEY: 'Kazoo'}))
        # the new entry wins over an old one
        self.assertEqual(Soundtrack.SFC, soundtrack_from_save({SOUNDTRACK_SAVE_KEY: 'SFC',
                                                                LEGACY_ORCHESTRA_SAVE_KEY: False}))

    def test_an_adventure_log_with_the_old_switch(self):
        self.assertEqual(Soundtrack.NES, options_from_save({'Name': 'Ed', LEGACY_ORCHESTRA_SAVE_KEY: False}).soundtrack)
        self.assertEqual(Soundtrack.ORCHESTRA,
                         options_from_save({'Name': 'Ed', LEGACY_ORCHESTRA_SAVE_KEY: True}).soundtrack)

    def test_options_save_the_new_entry_only(self):
        entries = options_to_save(Options(soundtrack=Soundtrack.SFC))
        self.assertEqual('SFC', entries[SOUNDTRACK_SAVE_KEY])
        self.assertNotIn(LEGACY_ORCHESTRA_SAVE_KEY, entries)
        self.assertEqual(Soundtrack.SFC, options_from_save(json.loads(json.dumps(entries))).soundtrack)

    def test_apply_and_read_back_from_the_config(self):
        config: dict = {}
        apply_options(config, Options(soundtrack=Soundtrack.SFC))
        self.assertEqual(Soundtrack.SFC, config[SOUNDTRACK_KEY])
        self.assertEqual(Soundtrack.SFC, options_from_config(config).soundtrack)

    def test_a_config_with_the_old_switch(self):
        self.assertEqual(Soundtrack.NES, soundtrack({**base_config, LEGACY_ORCHESTRA_CONFIG_KEY: False}))
        self.assertEqual(Soundtrack.ORCHESTRA, soundtrack({LEGACY_ORCHESTRA_CONFIG_KEY: True}))
        self.assertEqual(Soundtrack.ORCHESTRA, soundtrack(base_config))
        config = {**base_config, LEGACY_ORCHESTRA_CONFIG_KEY: False}
        migrate_legacy_music_config(config)
        self.assertEqual(Soundtrack.NES, config[SOUNDTRACK_KEY])
        self.assertNotIn(LEGACY_ORCHESTRA_CONFIG_KEY, config)
        # a config without it is left alone
        config = {SOUNDTRACK_KEY: Soundtrack.SFC}
        migrate_legacy_music_config(config)
        self.assertEqual({SOUNDTRACK_KEY: Soundtrack.SFC}, config)


class TestGameMigration(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()

    def new_game(self, **overrides):
        return helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True, **overrides})

    def test_a_game_started_with_the_old_switch_plays_what_it_meant(self):
        game = self.new_game(**{LEGACY_ORCHESTRA_CONFIG_KEY: False})
        self.assertEqual(Soundtrack.NES, game.config[SOUNDTRACK_KEY])
        self.assertNotIn(LEGACY_ORCHESTRA_CONFIG_KEY, game.config)
        self.assertIn(os.path.join('music', 'NES'), game.current_map.music_file_path)

    def test_a_save_state_with_the_old_switch(self):
        game = self.new_game(**{SOUNDTRACK_KEY: Soundtrack.SFC})
        snapshot = take_snapshot(game)
        options = snapshot['options']
        del options[SOUNDTRACK_SAVE_KEY]
        options[LEGACY_ORCHESTRA_SAVE_KEY] = False
        with patch.object(game.music_player, 'load_and_play_music') as load_and_play_music:
            restore_snapshot(game, json.loads(json.dumps(snapshot)), fade_in=False)
        self.assertEqual(Soundtrack.NES, game.config[SOUNDTRACK_KEY])
        # the map stayed, so its music starts again from the NES set
        load_and_play_music.assert_called_once_with(game.directories.tantegel_castle_throne_room_music)
        self.assertIn(os.path.join('music', 'NES'), game.current_map.music_file_path)


class TestSmokeTestCoversEverySoundtrack(TestCase):

    def test_every_soundtracks_files_are_checked(self):
        file_paths = game_file_paths(test_config)
        for chosen in SOUNDTRACKS:
            with self.subTest(soundtrack=chosen):
                self.assertLessEqual(set(music_paths(chosen).values()), file_paths)
