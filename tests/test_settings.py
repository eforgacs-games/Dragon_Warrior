"""The global settings (src/settings.py): zoom, fullscreen, game speed and language, kept in one file in the user's
config folder, read at start and written when one changes; and the LANGUAGE row of the options overlay, which switches
the language at once. Every test here keeps its settings file in a temporary folder (SETTINGS_PATH)."""
import json
import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from pygame import FULLSCREEN, K_2, K_3, K_DOWN, K_F11, K_RIGHT, K_u, KEYDOWN, Rect, Surface
from pygame.event import Event

from src import settings as settings_module
from src.common import set_gettext_language
from src.config.test_config import test_config
from src.options_overlay import OPTION_ROWS, OPTIONS_TITLE
from src.settings import SETTINGS_ENV_VAR, USER_SETTINGS, Settings, SettingsStore, load_settings, save_settings, \
    settings_path
from src.waiting import game_speed, get_events, reset_game_speed, set_speed_listener
from src.windows import COMMAND_ENTRIES, COMMAND_TITLE
from src.zoom import set_zoom_listener
from tests import helpers

KOREAN = set_gettext_language('Korean')
GAP = 2


def key(pressed_key):
    return Event(KEYDOWN, key=pressed_key, mod=0)


def presses(*keys):
    results = []
    for pressed_key in keys:
        results += [[]] * GAP + [[key(pressed_key)]]
    return results


class TempDirTestCase(TestCase):

    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.path = os.path.join(temp_dir.name, 'config', 'settings.json')

    def write(self, text: str) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'w', encoding='utf-8') as settings_file:
            settings_file.write(text)

    def saved(self) -> dict:
        with open(self.path, encoding='utf-8') as settings_file:
            return json.load(settings_file)


class TestSettingsFile(TempDirTestCase):

    def test_round_trip(self):
        settings = Settings(zoom=3, fullscreen=True, game_speed=4, language='Korean')
        self.assertTrue(save_settings(self.path, settings))
        self.assertEqual(settings, load_settings(self.path))

    def test_format(self):
        save_settings(self.path, Settings(zoom=3, language='Korean'))
        self.assertEqual({'version': 1, 'zoom': 3, 'fullscreen': False, 'game_speed': 1, 'language': 'Korean'},
                         self.saved())
        self.assertEqual(['settings.json'], os.listdir(os.path.dirname(self.path)))  # no temporary file left over

    def test_missing_file_is_the_defaults(self):
        self.assertEqual(Settings(), load_settings(self.path))
        self.assertEqual(Settings(), load_settings(None))

    def test_corrupt_file_is_the_defaults(self):
        for text in ('', 'not json', '{"zoom": 3', '[1, 2]', 'null', '"Korean"', '\udcff'):
            with self.subTest(text=text):
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
                with open(self.path, 'w', encoding='utf-8', errors='surrogateescape') as settings_file:
                    settings_file.write(text)
                self.assertEqual(Settings(), load_settings(self.path))

    def test_not_utf8_is_the_defaults(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'wb') as settings_file:
            settings_file.write(b'\xff\xfe\x00garbage')
        self.assertEqual(Settings(), load_settings(self.path))

    def test_each_bad_value_is_its_default_alone(self):
        self.write(json.dumps({'zoom': 'big', 'fullscreen': 'yes', 'game_speed': 3, 'language': 'Klingon'}))
        self.assertEqual(Settings(), load_settings(self.path))
        self.write(json.dumps({'zoom': 0, 'fullscreen': 1, 'game_speed': True, 'language': None}))
        self.assertEqual(Settings(), load_settings(self.path))
        self.write(json.dumps({'zoom': 4, 'fullscreen': 'yes', 'game_speed': 16, 'language': 'Klingon'}))
        self.assertEqual(Settings(zoom=4, game_speed=16), load_settings(self.path))

    def test_a_folder_that_cannot_be_written_is_only_a_warning(self):
        self.write('')
        blocked = os.path.join(self.path, 'settings.json')  # a "folder" that is a file
        with patch('builtins.print') as warning:
            self.assertFalse(save_settings(blocked, Settings(zoom=3)))
        warning.assert_called_once()
        store = SettingsStore(blocked)
        with patch('builtins.print'):
            self.assertTrue(store.update(zoom=3))
        self.assertEqual(3, store.settings.zoom)

    def test_where_the_file_is(self):
        self.assertIsNone(settings_path({'SETTINGS_PATH': None}))
        self.assertIsNone(settings_path({}))
        self.assertEqual(self.path, settings_path({'SETTINGS_PATH': self.path}))
        with patch.dict(os.environ, {SETTINGS_ENV_VAR: self.path}):
            self.assertEqual(self.path, settings_path({'SETTINGS_PATH': USER_SETTINGS}))
        with patch.dict(os.environ, {SETTINGS_ENV_VAR: ''}), \
                patch.object(settings_module, 'user_config_dir', return_value='/config/dragon-warrior'):
            self.assertEqual(os.path.join('/config/dragon-warrior', 'settings.json'),
                             settings_path({'SETTINGS_PATH': USER_SETTINGS}))

    def test_tests_never_touch_the_real_settings(self):
        self.assertIsNone(test_config['SETTINGS_PATH'])
        # tests/conftest.py: anything left with USER_SETTINGS goes to a temporary folder
        self.assertIn('dragon_warrior_test_settings_', settings_path({'SETTINGS_PATH': USER_SETTINGS}))

    def test_store_writes_only_changes(self):
        store = SettingsStore(self.path)
        self.assertFalse(store.update(game_speed=1))
        self.assertFalse(os.path.exists(self.path))
        self.assertTrue(store.update(game_speed=2))
        self.assertEqual(2, self.saved()['game_speed'])
        with self.assertRaises(TypeError):
            store.update(volume=11)


class GameTestCase(TempDirTestCase):
    """A Game whose settings file is in the temporary folder."""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        super().setUp()
        self.addCleanup(set_zoom_listener, None)
        self.addCleanup(set_speed_listener, None)
        self.addCleanup(reset_game_speed)

    def new_game(self, **overrides):
        config = {**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True, 'LANGUAGE': 'English',
                  'SETTINGS_PATH': self.path, **overrides}
        return helpers.new_game(config)


class TestReadAtStart(GameTestCase):

    def test_no_file_changes_nothing(self):
        game = self.new_game()
        self.assertEqual('English', game.config['LANGUAGE'])
        self.assertFalse(game.fullscreen_enabled)
        self.assertEqual(1, game_speed())
        self.assertFalse(os.path.exists(self.path))  # nothing is written until something changes

    def test_a_corrupt_file_changes_nothing(self):
        self.write('{"language": "Korean", ')
        game = self.new_game()
        self.assertEqual('English', game.config['LANGUAGE'])

    def test_saved_language_wins_over_the_locale(self):
        # base_config's LANGUAGE comes from the locale (language_from_locale); the saved one replaces it
        save_settings(self.path, Settings(language='Korean'))
        game = self.new_game(LANGUAGE='English')
        self.assertEqual('Korean', game.config['LANGUAGE'])
        self.assertEqual(KOREAN("TALK"), game.cmd_menu._("TALK"))
        save_settings(self.path, Settings(language='English'))
        self.assertEqual('English', self.new_game(LANGUAGE='Korean').config['LANGUAGE'])

    def test_without_a_saved_language_the_locale_decides(self):
        save_settings(self.path, Settings(zoom=3))
        for language in ('English', 'Korean'):
            with self.subTest(language=language):
                self.assertEqual(language, self.new_game(LANGUAGE=language).config['LANGUAGE'])

    def test_saved_speed(self):
        save_settings(self.path, Settings(game_speed=4))
        game = self.new_game()
        self.assertEqual(4, game_speed())
        self.assertEqual(240, game.fps)

    def test_saved_zoom_sizes_the_new_window(self):
        save_settings(self.path, Settings(zoom=3))
        with patch('src.game.set_zoom') as set_zoom:
            self.new_game()
        set_zoom.assert_called_once_with(3)

    def test_saved_fullscreen_opens_in_fullscreen(self):
        save_settings(self.path, Settings(zoom=3, fullscreen=True))
        with patch('src.game.set_mode', return_value=Surface((512, 480))) as set_mode, \
                patch('src.game.set_zoom') as set_zoom, patch('src.game.set_windowed_zoom') as set_windowed_zoom:
            game = self.new_game()
        self.assertTrue(game.fullscreen_enabled)
        self.assertTrue(set_mode.call_args.args[1] & FULLSCREEN)
        # the zoom is for the window it goes back to
        set_zoom.assert_not_called()
        set_windowed_zoom.assert_called_once_with(3)


class TestSavedWhenChanged(GameTestCase):

    def test_game_speed(self):
        game = self.new_game()
        with patch.object(game, 'draw_temporary_text'):
            game.handle_keypresses(key(K_3))  # on the map
        self.assertEqual(4, self.saved()['game_speed'])
        with patch('src.waiting.event.get', return_value=[key(K_2)]):
            get_events()  # in a dialog, a battle, a menu
        self.assertEqual(2, self.saved()['game_speed'])

    def test_fullscreen(self):
        game = self.new_game()
        with patch('src.game.set_mode', return_value=Surface((512, 480))), patch.object(game, 'draw_temporary_text'):
            game.handle_keypresses(key(K_F11))
            self.assertTrue(self.saved()['fullscreen'])
            game.handle_keypresses(key(K_F11))
            self.assertFalse(self.saved()['fullscreen'])

    def test_zoom(self):
        self.new_game()
        # src/zoom.py set_zoom tells the listener the game gave it (tests/test_zoom.py checks that it does)
        from src import zoom
        assert zoom._zoom_listener is not None
        zoom._zoom_listener(3)
        self.assertEqual(3, self.saved()['zoom'])

    def test_language(self):
        game = self.new_game()
        rows = [row.label for row in OPTION_ROWS]
        with patch('src.selection.event.get', side_effect=presses(*(K_DOWN,) * rows.index("LANGUAGE"), K_RIGHT, K_u)), \
                patch('src.selection.wait_frames'):
            from src.options_overlay import OptionsOverlay
            OptionsOverlay(game).run()
        self.assertEqual('Korean', self.saved()['language'])
        # and nothing else was written
        self.assertEqual({'version': 1, 'zoom': None, 'fullscreen': False, 'game_speed': 1, 'language': 'Korean'},
                         self.saved())

    def test_a_new_game_starts_with_what_was_saved(self):
        game = self.new_game()
        with patch.object(game, 'draw_temporary_text'):
            game.handle_keypresses(key(K_3))
        game.set_language('Korean')
        set_speed_listener(None)
        reset_game_speed()
        again = self.new_game()
        self.assertEqual(('Korean', 4), (again.config['LANGUAGE'], game_speed()))


class TestLanguageSwitch(GameTestCase):
    """Changing LANGUAGE in the options overlay applies at once, without a restart."""

    def setUp(self):
        super().setUp()
        self.game = self.new_game()
        self.config = self.game.game_state.config
        patch('src.selection.wait_frames').start()
        self.addCleanup(patch.stopall)

    def run_overlay(self, *keys, translations=None):
        """Run the overlay; ``translations`` gets the translate function of every draw of the window."""
        from src.options_overlay import OptionsOverlay
        drawn = [] if translations is None else translations

        def draw(overlay, *_args):
            drawn.append(overlay._)
        with patch('src.selection.event.get', side_effect=presses(*keys)), \
                patch.object(OptionsOverlay, 'draw', autospec=True, side_effect=draw):
            OptionsOverlay(self.game).run()

    def to_language(self):
        rows = [row.label for row in OPTION_ROWS]
        return (*(K_DOWN,) * rows.index("LANGUAGE"), K_RIGHT)

    def test_the_overlay_redraws_in_the_new_language(self):
        translations = []
        self.run_overlay(*self.to_language(), K_u, translations=translations)
        self.assertEqual("OPTIONS", translations[0](OPTIONS_TITLE.text))
        self.assertEqual(KOREAN(OPTIONS_TITLE.text), translations[-1](OPTIONS_TITLE.text))
        self.assertEqual("언어", translations[-1]("LANGUAGE"))
        # and back
        translations.clear()
        self.run_overlay(*self.to_language(), K_u, translations=translations)
        self.assertEqual("설정", translations[0](OPTIONS_TITLE.text))
        self.assertEqual("OPTIONS", translations[-1](OPTIONS_TITLE.text))
        self.assertEqual('English', self.config['LANGUAGE'])

    def dialog_entry(self):
        """A guard's line (GuardDialog1), as the next TALK would show it."""
        line = "If thou art planning to take a rest, first see King Lorik."
        for characters in self.game.cmd_menu.dialog_lookup.lookup_table.values():
            for entry in characters.values():
                if entry['dialog'] in (line, KOREAN(line)):
                    return entry['dialog']
        self.fail("no guard")

    def test_dialog_after_the_switch(self):
        line = "If thou art planning to take a rest, first see King Lorik."
        self.assertEqual(line, self.dialog_entry())
        self.run_overlay(*self.to_language(), K_u)
        self.assertEqual(KOREAN(line), self.dialog_entry())
        self.assertNotEqual(line, KOREAN(line))
        # and a line the game itself shows
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text:
            self.game.handle_keypresses(key(K_2))
        self.assertEqual(KOREAN("Game set to {}x speed.\n({} FPS)").format(2, 120), show_text.call_args.args[0])

    def test_king_loriks_line_carries_over(self):
        cmd_menu = self.game.cmd_menu
        cmd_menu.set_king_lorik_dialog(left_throne_room=True)
        self.run_overlay(*self.to_language(), K_u)
        king_lorik = cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']
        self.assertIs(king_lorik['returned_dialog'], king_lorik['dialog'])

    def test_menu_after_the_switch(self):
        self.run_overlay(*self.to_language(), K_u)
        cmd_menu = self.game.cmd_menu
        self.assertFalse(cmd_menu.command_window_in_nes_font())
        with patch('src.menu.draw_text') as draw_text, patch('src.menu.draw_window', return_value=Rect(0, 0, 1, 1)):
            cmd_menu.draw_command_window()
        drawn = [call.args[0] for call in draw_text.call_args_list]
        self.assertEqual([KOREAN(COMMAND_TITLE.text)] + [KOREAN(entry) for entry in COMMAND_ENTRIES], drawn)

    def test_a_battle_after_the_switch(self):
        self.run_overlay(*self.to_language(), K_u)
        from src.battle import Battle
        battle = Battle(self.config, 'Slime', self.game.current_map)
        self.assertEqual(KOREAN("FIGHT"), battle._("FIGHT"))
        self.assertEqual(KOREAN("FIGHT"), self.game.battle_ctrl._("FIGHT"))

    def test_window_caption(self):
        self.run_overlay(*self.to_language(), K_u)
        self.assertEqual(KOREAN("Dragon Warrior"), pygame.display.get_caption()[0])
        self.game.set_language('English')
        self.assertEqual("Dragon Warrior", pygame.display.get_caption()[0])
