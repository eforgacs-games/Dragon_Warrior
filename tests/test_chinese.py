"""The Traditional and Simplified Chinese translations (data/text/locales/zh_TW, zh_CN), with the names and terms of the
official DRAGON QUEST script (data/text/official_script/glossary_zh_Hant.tsv, glossary_zh_Hans.tsv)."""
import builtins
import csv
import os
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from src.battle import Battle
from src.catalog import po_path, read_po
from src.checkpoints import checkpoint_hero_name
from src.common import set_gettext_language
from src.config.base_config import language_from_locale
from src.dialog_box import DialogBuffer
from src.languages import SIMPLIFIED_CHINESE, TRADITIONAL_CHINESE, Language
from src.line_breaks import NO_BREAK_BEFORE
from src.paths import data_path
from src.player.player_stats import get_total_name_score
from src.text import WRAP_LENGTH, DialogBoxWrapper

GLOSSARIES = {TRADITIONAL_CHINESE: 'glossary_zh_Hant.tsv', SIMPLIFIED_CHINESE: 'glossary_zh_Hans.tsv'}
# Characters only the other script writes this way (Simplified 龙 and 剑, Traditional 龍 and 劍)
OTHER_SCRIPTS_CHARACTERS = {TRADITIONAL_CHINESE: '龙剑门说这', SIMPLIFIED_CHINESE: '龍劍門說這'}


class ChineseTestCase(TestCase):
    language: Language = TRADITIONAL_CHINESE

    def setUp(self):
        had_builtin, old_builtin = hasattr(builtins, '_'), getattr(builtins, '_', None)

        def restore():
            if had_builtin:
                builtins._ = old_builtin  # type: ignore[attr-defined]
            elif hasattr(builtins, '_'):
                del builtins._  # type: ignore[attr-defined]
        self.addCleanup(restore)
        self._ = set_gettext_language(self.language.name)

    def battle(self) -> Battle:
        battle = Battle.__new__(Battle)
        battle.config = {'LANGUAGE': self.language.name}
        battle._ = self._
        return battle


class TestTraditionalChinese(ChineseTestCase):
    language = TRADITIONAL_CHINESE

    def test_spot_check_translations(self):
        _ = self._
        self.assertEqual("你死掉了。", _("Thou art dead."))
        self.assertEqual("史萊姆出現了！\n", _('{} draws near!\n').format(_('Slime')))
        self.assertEqual("Edward使用了藥草！", _("{} used the Herb.").format("Edward"))
        self.assertEqual("勇者鬥惡龍", _("Dragon Warrior"))

    def test_declaration(self):
        self.assertEqual(('繁體中文', 'zh_TW'), (self.language.option_label, self.language.locale_code))
        for locale in ('zh_TW', 'zh_HK', 'zh_MO', 'zh_Hant_TW'):
            self.assertEqual('Traditional Chinese', language_from_locale(locale))

    def test_spoken_lines_are_quoted(self):
        self.assertEqual("「歡迎光臨！」", self.language.quote("歡迎光臨！"))

    def test_battle_lines(self):
        battle = self.battle()
        battle.enemy = SimpleNamespace(name='Axe Knight')
        self.assertEqual("惡魔騎士出現了！\n", battle.get_enemy_draws_near_string())
        self.assertEqual("幹掉了龍王！\n", battle.get_enemy_defeated_string(SimpleNamespace(name='Dragonlord 2')))


class TestSimplifiedChinese(ChineseTestCase):
    language = SIMPLIFIED_CHINESE

    def test_spot_check_translations(self):
        _ = self._
        self.assertEqual("你死掉了。", _("Thou art dead."))
        self.assertEqual("史莱姆出现了！\n", _('{} draws near!\n').format(_('Slime')))
        self.assertEqual("Edward使用了药草！", _("{} used the Herb.").format("Edward"))
        self.assertEqual("勇者斗恶龙", _("Dragon Warrior"))

    def test_declaration(self):
        self.assertEqual(('简体中文', 'zh_CN'), (self.language.option_label, self.language.locale_code))
        for locale in ('zh_CN', 'zh_SG', 'zh'):
            self.assertEqual('Simplified Chinese', language_from_locale(locale))

    def test_spoken_lines_are_quoted(self):
        self.assertEqual("“欢迎光临！”", self.language.quote("欢迎光临！"))

    def test_battle_lines(self):
        battle = self.battle()
        battle.enemy = SimpleNamespace(name='Axe Knight')
        self.assertEqual("恶魔骑士出现了！\n", battle.get_enemy_draws_near_string())
        self.assertEqual("干掉了龙王！\n", battle.get_enemy_defeated_string(SimpleNamespace(name='Dragonlord 2')))


class TestBothScripts(TestCase):

    def test_names_follow_the_glossaries(self):
        for language, glossary in GLOSSARIES.items():
            _ = set_gettext_language(language.name)
            with open(data_path('text', 'official_script', glossary), encoding='utf-8', newline='') as file:
                rows = [row for row in csv.DictReader(file, delimiter='\t') if row['kind'] in ('item', 'spell', 'monster')]
            self.assertGreater(len(rows), 80)
            for row in rows:
                with self.subTest(language=language.name, name=row['english_nes']):
                    self.assertEqual(row['ours'], _(row['english_nes']))
                    if row['chinese_official']:
                        self.assertEqual(row['chinese_official'], row['ours'])
        set_gettext_language('English')

    def test_each_catalog_is_in_its_own_script(self):
        for language, characters in OTHER_SCRIPTS_CHARACTERS.items():
            text = ''.join(read_po(po_path(language.locale_code or '')).values())
            with self.subTest(language=language.name):
                self.assertFalse(set(characters) & set(text), set(characters) & set(text))

    def test_no_wrapped_row_starts_with_closing_punctuation(self):
        for language in GLOSSARIES:
            wrapper = DialogBoxWrapper(width=WRAP_LENGTH, break_long_words=False, breaks_anywhere=True)
            for message in read_po(po_path(language.locale_code or '')).values():
                for row in wrapper.wrap(message):
                    with self.subTest(language=language.name, row=row):
                        self.assertFalse(row and row[0] in NO_BREAK_BEFORE and len(row) < WRAP_LENGTH)

    def test_a_long_quoted_line_wraps_in_the_dialog_window(self):
        for language in GLOSSARIES:
            _ = set_gettext_language(language.name)
            line = language.quote(_("It is told that in ages past Erdrick fought demons with a Ball of Light."))
            buffer = DialogBuffer()
            list(buffer.print_message(line, quoted=True, breaks_anywhere=True))
            rows = buffer.visible_lines
            with self.subTest(language=language.name):
                self.assertGreater(len(rows), 1)
                self.assertTrue(all(row.startswith(' ') for row in rows[1:]))  # the NES indent
        set_gettext_language('English')

    def test_checkpoint_heroes_get_the_strongest_stats(self):
        for language in GLOSSARIES:
            name = checkpoint_hero_name('Arthur', language.name)
            self.assertEqual(language.checkpoint_hero_name, name)
            self.assertEqual(0x0D, get_total_name_score(name) & 0x0F)

    def test_level_up_is_shown_silently_like_the_nes_line(self):
        for language in GLOSSARIES:
            _ = set_gettext_language(language.name)
            battle = Battle.__new__(Battle)
            battle.config = {'LANGUAGE': language.name}
            battle._ = _
            cmd_menu = Mock()
            battle.display_level_up_message(cmd_menu, SimpleNamespace(level=4, name='Edward'))
            cmd_menu.show_line_in_dialog_box.assert_called_once_with(
                _("Courage and wit have served thee well.\nThou hast been promoted to the next level.\n"),
                add_quotes=False, disable_sound=True)
        set_gettext_language('English')
