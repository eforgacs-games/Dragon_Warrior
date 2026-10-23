"""Autosave (src/autosave.py): a save state slot of its own, written on entering a town or castle and every few
minutes, and CONTINUE AUTOSAVE on the title menu. Not NES."""
import json
import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from src.autosave import AUTOSAVE_INTERVAL_MS, AUTOSAVE_MAPS, autosave_path, has_autosave, read_autosave
from src.config.test_config import test_config
from src.direction import Direction
from src.maps import map_lookup
from src.options_screen import AUTOSAVE_SAVE_KEY, DEFAULT_OPTIONS, apply_options, options_from_save
from src.save_file import save_files
from src.save_state import STATE_FORMAT_VERSION, VERSION_KEY, take_snapshot
from src.title_menu import BACK_TO_TITLE_MENU
from src.title_windows import title_menu_layout
from src.windows import CONTINUE_AUTOSAVE, FULL_MENU_LAYOUT, NEW_QUEST_LAYOUT, with_autosave_entry
from tests import helpers

# Grass by Tantegel Castle, and Brecconary's entrance on the overworld (src/maps.py Alefgard)
ALEFGARD_GRASS = (50, 44)
BRECCONARY_ON_THE_OVERWORLD = (48, 56)


def comparable(snapshot: dict) -> dict:
    return json.loads(json.dumps(snapshot))


class AutosaveTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()

    def setUp(self):
        pygame.event.clear()
        self.save_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.save_dir.cleanup)
        self.clock = [0]
        patch('src.autosave.get_ticks', lambda: self.clock[0]).start()
        self.addCleanup(patch.stopall)
        self.game = self.new_game()

    def new_game(self, **overrides):
        return helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True,
                                 'SAVE_DIR': self.save_dir.name, 'AUTOSAVE': True, **overrides})

    def go_to(self, map_name, coordinates=None):
        next_map = map_lookup[map_name](self.game.config)
        self.game.change_map(next_map, destination_coordinates=coordinates or next_map.initial_coordinates,
                             direction=Direction.DOWN.value)

    def frame(self):
        self.game.map_frame()

    @property
    def path(self):
        return autosave_path(self.save_dir.name)


class TestWhenItsWritten(AutosaveTestCase):

    def test_not_at_once(self):
        self.frame()
        self.assertFalse(has_autosave(self.save_dir.name))

    def test_on_entering_a_town_from_the_overworld(self):
        self.go_to('Alefgard', ALEFGARD_GRASS)
        self.frame()
        self.assertFalse(has_autosave(self.save_dir.name))
        self.go_to('Brecconary')
        self.frame()
        self.assertTrue(has_autosave(self.save_dir.name))
        snapshot = read_autosave(self.save_dir.name)
        self.assertEqual('Brecconary', snapshot['map'])
        self.assertEqual(STATE_FORMAT_VERSION, snapshot[VERSION_KEY])

    def test_every_town_and_castle(self):
        self.assertEqual(('TantegelCourtyard', 'Brecconary', 'Garinham', 'Kol', 'Rimuldar', 'Cantlin'),
                         AUTOSAVE_MAPS)
        for map_name in AUTOSAVE_MAPS:
            with self.subTest(map_name):
                if os.path.exists(self.path):
                    os.remove(self.path)
                self.go_to('Alefgard', ALEFGARD_GRASS)
                self.frame()
                self.go_to(map_name)
                self.frame()
                self.assertEqual(map_name, read_autosave(self.save_dir.name)['map'])

    def test_not_on_entering_a_cave_or_charlock(self):
        for map_name in ('ErdricksCaveB1', 'CharlockB1', 'Hauksness'):
            with self.subTest(map_name):
                self.go_to('Alefgard', ALEFGARD_GRASS)
                self.frame()
                self.go_to(map_name)
                self.frame()
                self.assertFalse(has_autosave(self.save_dir.name))

    def test_not_going_from_the_courtyard_to_the_throne_room(self):
        self.go_to('TantegelCourtyard')
        self.frame()
        self.go_to('TantegelThroneRoom')
        self.frame()
        self.assertFalse(has_autosave(self.save_dir.name))

    def test_every_few_minutes(self):
        self.go_to('Alefgard', ALEFGARD_GRASS)
        self.clock[0] = AUTOSAVE_INTERVAL_MS - 1
        self.frame()
        self.assertFalse(has_autosave(self.save_dir.name))
        self.clock[0] = AUTOSAVE_INTERVAL_MS
        self.frame()
        self.assertEqual('Alefgard', read_autosave(self.save_dir.name)['map'])
        # and the interval starts again
        os.remove(self.path)
        self.clock[0] = 2 * AUTOSAVE_INTERVAL_MS - 1
        self.frame()
        self.assertFalse(has_autosave(self.save_dir.name))
        self.clock[0] = 2 * AUTOSAVE_INTERVAL_MS
        self.frame()
        self.assertTrue(has_autosave(self.save_dir.name))

    def test_entering_a_town_starts_the_interval_again(self):
        self.go_to('Alefgard', ALEFGARD_GRASS)
        self.clock[0] = AUTOSAVE_INTERVAL_MS - 10
        self.frame()
        self.go_to('Kol')
        self.frame()
        os.remove(self.path)
        self.clock[0] = AUTOSAVE_INTERVAL_MS
        self.frame()
        self.assertFalse(has_autosave(self.save_dir.name))

    def test_waits_for_the_hero_to_finish_the_step(self):
        self.go_to('Alefgard', ALEFGARD_GRASS)
        self.frame()
        self.go_to('Brecconary')
        self.game.player.is_moving = True
        with patch.object(self.game.movement, 'handle_player_movement'):
            self.frame()
            self.assertFalse(has_autosave(self.save_dir.name))
            self.game.player.is_moving = False
            self.frame()
        self.assertTrue(has_autosave(self.save_dir.name))

    def test_off_is_the_nes(self):
        self.game.config['AUTOSAVE'] = False
        self.go_to('Alefgard', ALEFGARD_GRASS)
        self.frame()
        self.go_to('Brecconary')
        self.clock[0] = 10 * AUTOSAVE_INTERVAL_MS
        self.frame()
        self.assertFalse(has_autosave(self.save_dir.name))
        self.assertEqual([], os.listdir(self.save_dir.name))

    def test_the_adventure_logs_are_untouched(self):
        self.go_to('Alefgard', ALEFGARD_GRASS)
        self.frame()
        self.go_to('Brecconary')
        self.frame()
        self.assertEqual([], save_files(self.save_dir.name))
        self.assertEqual(['autosave.json'], os.listdir(self.save_dir.name))

    def test_a_failed_write_doesnt_stop_the_game(self):
        self.clock[0] = AUTOSAVE_INTERVAL_MS
        with patch('src.autosave.write_snapshot', side_effect=OSError("disk full")), patch('builtins.print'):
            self.frame()
        self.assertFalse(has_autosave(self.save_dir.name))


class TestSetting(AutosaveTestCase):

    def test_kept_per_adventure_log(self):
        self.assertTrue(options_from_save({AUTOSAVE_SAVE_KEY: True}).autosave)
        self.assertFalse(options_from_save({AUTOSAVE_SAVE_KEY: False}).autosave)

    def test_an_older_save_keeps_the_configs(self):
        # A save from before AUTOSAVE was kept, or a new quest, leaves the config's (base_config: ON)
        for config_value in (True, False):
            config = {'AUTOSAVE': config_value}
            apply_options(config, options_from_save({}))
            self.assertIs(config_value, config['AUTOSAVE'])
            apply_options(config, DEFAULT_OPTIONS)
            self.assertIs(config_value, config['AUTOSAVE'])

    def test_off_by_default_as_on_the_nes(self):
        # A new option defaults to the NES (#409): the MODERN preset turns it on
        from src.config.base_config import base_config
        from src.config.dev_config import dev_config
        self.assertFalse(base_config['AUTOSAVE'])
        self.assertFalse(test_config['AUTOSAVE'])
        self.assertFalse(dev_config['AUTOSAVE'])


class TestContinueAutosave(AutosaveTestCase):

    def write_autosave_in_brecconary(self):
        self.go_to('Alefgard', ALEFGARD_GRASS)
        self.frame()
        self.go_to('Brecconary')
        self.game.player.gold = 1234
        self.game.player.name = 'Loto'
        self.frame()
        return comparable(take_snapshot(self.game))

    def continue_autosave(self, game):
        with patch('src.save_state.screen_fade'), patch.object(game.music_player, 'load_and_play_music'):
            return game.title_menu.continue_autosave()

    def test_puts_the_game_back(self):
        saved = self.write_autosave_in_brecconary()
        game = self.new_game()
        self.assertIsNone(self.continue_autosave(game))
        self.assertEqual('Brecconary', game.current_map.identifier)
        self.assertEqual(1234, game.player.gold)
        self.assertEqual('Loto', game.player.name)
        self.assertEqual({**saved, 'random': None}, {**comparable(take_snapshot(game)), 'random': None})

    def test_no_autosave_goes_back_to_the_title_menu(self):
        self.assertIs(BACK_TO_TITLE_MENU, self.continue_autosave(self.game))

    def test_an_unreadable_autosave_goes_back_to_the_title_menu(self):
        with open(self.path, 'w') as autosave_file:
            autosave_file.write('{"version": 0}')
        self.assertIs(BACK_TO_TITLE_MENU, self.continue_autosave(self.game))
        self.assertEqual('TantegelThroneRoom', self.game.current_map.identifier)

    def run_title_menu(self, game, selection):
        with patch.object(game.game_functions, 'main_menu_selection', return_value=selection) as menu, \
                patch('src.save_state.screen_fade'), patch.object(game.music_player, 'load_and_play_music'):
            result = game.title_menu.show_title_menu(game.screen)
        return result, menu.call_args.args[2]

    def test_the_title_menu_entry(self):
        game = self.new_game()
        # no autosave: the NES title menu
        with patch.object(game.title_menu, 'begin_new_quest', return_value=None):
            _, layout = self.run_title_menu(game, 0)
        self.assertEqual(NEW_QUEST_LAYOUT, layout)
        self.write_autosave_in_brecconary()
        game = self.new_game()
        result, layout = self.run_title_menu(game, 1)
        self.assertEqual(with_autosave_entry(NEW_QUEST_LAYOUT), layout)
        self.assertIsNone(result)
        self.assertEqual('Brecconary', game.current_map.identifier)

    def test_the_entry_is_last_and_the_window_grows_a_block(self):
        layout = title_menu_layout(1, autosave=True)
        self.assertEqual(FULL_MENU_LAYOUT.window.height + 1, layout.window.height)
        self.assertEqual(CONTINUE_AUTOSAVE, layout.texts[-1].text)
        self.assertEqual(FULL_MENU_LAYOUT.texts, layout.texts[:-1])
        self.assertEqual((1, FULL_MENU_LAYOUT.cursor_tiles[-1][1] + 2), layout.cursor_tiles[-1])
        from src.window_renderer import window_tiles
        for used in range(4):
            window_tiles(title_menu_layout(used, autosave=True))  # ValueError for text outside the window

    def test_korean_entry_fits(self):
        from src.common import set_gettext_language
        from src.directories import Directories
        from src.text import set_font_by_ascii_chars
        _ = set_gettext_language('Korean')
        korean = _(CONTINUE_AUTOSAVE)
        self.assertNotEqual(CONTINUE_AUTOSAVE, korean)
        font = set_font_by_ascii_chars([korean], 16, None, Directories(test_config))
        # no wider than the NES entries' translations, which fit
        widest = max(font.size(_(text.text))[0] for text in FULL_MENU_LAYOUT.texts)
        self.assertLessEqual(font.size(korean)[0], widest)
