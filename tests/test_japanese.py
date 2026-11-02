"""The Japanese translation (data/text/locales/ja), with the names and terms of the official DRAGON QUEST script
(data/text/official_script/glossary_ja.tsv)."""
import builtins
import csv
import os
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from pygame import K_RETURN

from src.battle import Battle
from src.checkpoints import checkpoint_hero_name
from src.common import set_gettext_language
from src.config.base_config import language_from_locale
from src.config.test_config import test_config
from src.dialog_box import DialogBuffer
from src.languages import JAPANESE, language_named
from src.menu_functions import NameSelection
from src.paths import data_path
from src.player.player_stats import get_total_name_score
from tests.test_name_entry import key_event

GLOSSARY = data_path('text', 'official_script', 'glossary_ja.tsv')


class JapaneseTestCase(TestCase):

    def setUp(self):
        had_builtin, old_builtin = hasattr(builtins, '_'), getattr(builtins, '_', None)

        def restore():
            if had_builtin:
                builtins._ = old_builtin  # type: ignore[attr-defined]
            elif hasattr(builtins, '_'):
                del builtins._  # type: ignore[attr-defined]
        self.addCleanup(restore)
        self._ = set_gettext_language('Japanese')


class TestJapaneseText(JapaneseTestCase):

    def test_spot_check_translations(self):
        _ = self._
        self.assertEqual("あなたは 死にました。", _("Thou art dead."))
        self.assertEqual("スライムが あらわれた！\n", _('{} draws near!\n').format(_('Slime')))
        self.assertEqual("Edwardは やくそうを 使った！", _("{} used the Herb.").format("Edward"))
        self.assertEqual("南に 3..", _("{} to the south and..").format(3))
        self.assertEqual("ドラゴンクエスト", _("Dragon Warrior"))

    def test_names_follow_the_glossary(self):
        with open(GLOSSARY, encoding='utf-8', newline='') as glossary_file:
            rows = [row for row in csv.DictReader(glossary_file, delimiter='\t') if row['kind'] in
                    ('item', 'spell', 'monster')]
        self.assertGreater(len(rows), 80)
        for row in rows:
            with self.subTest(name=row['english_nes']):
                self.assertEqual(row['ours'], self._(row['english_nes']))
                if row['japanese_official']:
                    self.assertEqual(row['japanese_official'], row['ours'])

    def test_untranslated_text_falls_back_to_english(self):
        self.assertEqual("F5: Warp", self._("F5: Warp"))


class TestJapaneseLanguage(TestCase):

    def test_declaration(self):
        self.assertIs(JAPANESE, language_named('Japanese'))
        self.assertEqual(('日本語', 'ja'), (JAPANESE.option_label, JAPANESE.locale_code))
        self.assertEqual('Japanese', language_from_locale('ja_JP'))

    def test_spoken_lines_are_quoted_and_indented(self):
        quoted = JAPANESE.quote("ようこそ！")
        self.assertEqual("「ようこそ！」", quoted)
        self.assertEqual("`Edward’", JAPANESE.quote("Edward"))  # still ASCII: the NES's
        buffer = DialogBuffer()
        steps = list(buffer.print_message(quoted, quoted=True))
        self.assertEqual("「ようこそ！」", buffer.lines[0])
        self.assertTrue(any(step.beep for step in steps))  # quoted text beeps, as on the NES

    def test_checkpoint_hero(self):
        name = checkpoint_hero_name('Arthur', 'Japanese')
        self.assertEqual('たびびと', name)
        self.assertEqual(0x0D, get_total_name_score(name) & 0x0F)


class TestJapaneseBattleLines(JapaneseTestCase):

    def battle(self) -> Battle:
        battle = Battle.__new__(Battle)
        battle.config = {'LANGUAGE': 'Japanese'}
        battle._ = self._
        return battle

    def test_lines(self):
        battle = self.battle()
        battle.enemy = SimpleNamespace(name='Axe Knight')
        self.assertEqual("あくまのきしが あらわれた！\n", battle.get_enemy_draws_near_string())
        self.assertEqual("りゅうおうを やっつけた！\n", battle.get_enemy_defeated_string(SimpleNamespace(name='Dragonlord 2')))

    def test_level_up_is_shown_silently_like_the_nes_line(self):
        cmd_menu = Mock()
        self.battle().display_level_up_message(cmd_menu, SimpleNamespace(level=4, name='Edward'))
        cmd_menu.show_line_in_dialog_box.assert_called_once_with(
            self._("Courage and wit have served thee well.\nThou hast been promoted to the next level.\n"),
            add_quotes=False, disable_sound=True)


class TestJapaneseNameEntry(JapaneseTestCase):
    """The name entry is the NES's Latin one in every language (Hangul and kana entry would come later); the name
    typed shows in the Japanese text, in Unifont with it."""

    def test_a_name_is_entered_and_shown(self):
        config = dict(test_config, NO_BLIT=True, LANGUAGE='Japanese')
        command_menu = Mock()
        command_menu.game.game_state.config = config
        events = [key_event(pygame.K_e, 'E'), key_event(pygame.K_d, 'd'), key_event(K_RETURN)]
        with patch('src.waiting.event.get', side_effect=[[event] for event in events]), \
                patch('src.menu_functions.display'), patch('src.menu_functions.Sound'):
            name = NameSelection(config).select_name(0, pygame.Surface((256, 240)), command_menu)
        self.assertEqual('Ed', name)
        self.assertEqual("Edは やくそうを 使った！", self._("{} used the Herb.").format(name))
