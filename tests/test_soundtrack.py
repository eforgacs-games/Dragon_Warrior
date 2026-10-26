import json
import os
from unittest import TestCase
from unittest.mock import patch

import pygame

from src.config.base_config import base_config
from src.config.test_config import test_config
from src.chiptune import parse_track_ref
from src.directories import CLIP_NAMES, MUSIC_NAMES, Directories, clip_paths, music_name, music_paths
from src.options_screen import Options, apply_options, options_from_config, options_from_save, options_to_save
from src.paths import data_path
from src.save_state import restore_snapshot, take_snapshot
from src.smoke_test import game_file_paths
from src.soundtrack import DEFAULT_SOUNDTRACK, LEGACY_ORCHESTRA_CONFIG_KEY, LEGACY_ORCHESTRA_SAVE_KEY, SOUNDTRACK_KEY, \
    SOUNDTRACK_SAVE_KEY, SOUNDTRACKS, Soundtrack, migrate_legacy_music_config, soundtrack, soundtrack_from_save
from tests import helpers

SFC_DIR = data_path('sound', 'music', 'SFC')


def sfc_track(name: str) -> str:
    return os.path.join(SFC_DIR, name)


def file_of(path_or_track: str) -> str:
    track = parse_track_ref(path_or_track)
    return track.path if track else path_or_track


class TestMusicPaths(TestCase):

    def test_every_soundtrack_names_every_music_and_every_file_exists(self):
        for chosen in SOUNDTRACKS:
            with self.subTest(soundtrack=chosen):
                paths = music_paths(chosen)
                self.assertEqual(set(MUSIC_NAMES), set(paths))
                for name, path in {**paths, **clip_paths(chosen)}.items():
                    self.assertTrue(os.path.isfile(file_of(path)), f"{name}: {path}")

    def test_each_soundtrack_plays_from_its_own_folder(self):
        folders = {Soundtrack.NES: data_path('sound', 'music', 'NES'), Soundtrack.SFC: SFC_DIR,
                   Soundtrack.ORCHESTRA: data_path('sound', 'music', 'orchestra')}
        for chosen, folder in folders.items():
            for name, path in music_paths(chosen).items():
                with self.subTest(soundtrack=chosen, music=name):
                    self.assertTrue(path.startswith(folder), path)

    def test_the_nes_soundtrack_is_the_nsf_and_the_sfc_soundtrack_is_spc_files(self):
        nsf = data_path('sound', 'music', 'NES', 'dragon_warrior.nsf')
        for name, path in {**music_paths(Soundtrack.NES), **clip_paths(Soundtrack.NES)}.items():
            with self.subTest(music=name):
                self.assertEqual(nsf, file_of(path))
        for name, path in {**music_paths(Soundtrack.SFC), **clip_paths(Soundtrack.SFC)}.items():
            if name != 'intro_overture':  # the Dragon Quest I & II overture has no SPC here: its recording
                with self.subTest(music=name):
                    self.assertTrue(path.endswith('.spc'), path)

    def test_the_sfc_mp3s_are_gone_but_the_overture(self):
        self.assertEqual(['09 Overture March (Original Game Sound).mp3'],
                         [name for name in os.listdir(SFC_DIR) if name.endswith('.mp3')])

    def test_every_soundtrack_has_jingles(self):
        nes = Directories({**test_config, SOUNDTRACK_KEY: Soundtrack.NES})
        orchestra = Directories({**test_config, SOUNDTRACK_KEY: Soundtrack.ORCHESTRA})
        sfc = Directories({**test_config, SOUNDTRACK_KEY: Soundtrack.SFC})
        for name in CLIP_NAMES:
            with self.subTest(jingle=name):
                # the orchestral album has none: the NES's
                self.assertEqual(getattr(nes, name), getattr(orchestra, name))
                self.assertTrue(getattr(nes, name).startswith(data_path('sound', 'music', 'NES')))
                self.assertTrue(getattr(sfc, name).startswith(SFC_DIR))

    def test_the_orchestra_folder_holds_only_the_orchestral_set(self):
        orchestra_dir = data_path('sound', 'music', 'orchestra')
        self.assertEqual(['01', '02', '03', '04', '05', '06', '07', '08', 'Android_iOS'],
                         sorted(name[:2] if name[0].isdigit() else name for name in os.listdir(orchestra_dir)))

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
                tracks = {*music_paths(chosen).values(), *clip_paths(chosen).values()}
                self.assertLessEqual({file_of(track) for track in tracks}, file_paths)
