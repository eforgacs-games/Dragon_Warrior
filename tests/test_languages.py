"""The languages' declarations (src/languages.py), and the Korean behavior they replace, byte for byte: the quote
marks, and the battle lines Korean puts together itself."""
import builtins
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

from src.battle import Battle
from src.catalog import po_path
from src.common import set_gettext_language
from src.dialog_box import OPEN_QUOTES
from src.korean_particles import KoreanText, get_postposition, particle
from src.languages import CATALOG_LANGUAGES, ENGLISH, KOREAN, LANGUAGE_NAMES, LANGUAGES, NES_QUOTE_MARKS, \
    language_for_locale, language_named

ENEMY_NAMES = ('Slime', 'Ghost', 'Magician', 'Axe Knight', 'Golem', 'Red Dragon', 'Dragonlord', 'Metal Slime')
HERO_NAMES = ('Edward', 'Michael', 'Adam', '검객', '용사', 'Lorikeet', '7')


def old_quote(language: str, text: str) -> str:
    """CommandMenu.add_dialog_quotes and Ending.quote before src/languages.py."""
    if language == 'Korean' and not text.isascii():
        return f"'{text}'"
    return f"`{text}’"


class TestRegistry(TestCase):

    def test_names_are_unique_and_english_comes_first(self):
        self.assertEqual(len(LANGUAGE_NAMES), len(set(LANGUAGE_NAMES)))
        self.assertIs(ENGLISH, LANGUAGES[0])
        self.assertEqual(('English', 'Korean'), LANGUAGE_NAMES[:2])

    def test_option_labels_are_unique(self):
        labels = [language.option_label for language in LANGUAGES]
        self.assertEqual(len(labels), len(set(labels)))

    def test_every_translation_has_a_catalog(self):
        self.assertNotIn(ENGLISH, CATALOG_LANGUAGES)
        for language in CATALOG_LANGUAGES:
            with self.subTest(language=language.name):
                self.assertTrue(po_path(language.locale_code or '').is_file())

    def test_language_named(self):
        for language in LANGUAGES:
            self.assertIs(language, language_named(language.name))
        # anything else plays in English, as it always has (set_gettext_language('French'))
        for name in ('French', '', None):
            self.assertIs(ENGLISH, language_named(name))

    def test_language_for_locale(self):
        self.assertIs(KOREAN, language_for_locale('ko_KR'))
        self.assertIs(ENGLISH, language_for_locale('en_US'))
        self.assertIs(ENGLISH, language_for_locale(None))

    def test_open_quotes_include_every_languages(self):
        for language in LANGUAGES:
            self.assertIn(language.quote_marks[0], OPEN_QUOTES)
        self.assertEqual(('`', "'", '‘', '“'), OPEN_QUOTES[:4])


class TestUnchangedKorean(TestCase):
    """What the code that asked for 'Korean' by name did, the Korean declaration does."""

    def setUp(self):
        had_builtin, old_builtin = hasattr(builtins, '_'), getattr(builtins, '_', None)

        def restore():
            if had_builtin:
                builtins._ = old_builtin  # type: ignore[attr-defined]
            elif hasattr(builtins, '_'):
                del builtins._  # type: ignore[attr-defined]
        self.addCleanup(restore)
        self._ = set_gettext_language('Korean')

    def test_gettext_returns_korean_text(self):
        self.assertIsInstance(self._("Thou art a fool!"), KoreanText)
        self.assertEqual("어리석은 놈!", self._("Thou art a fool!"))
        self.assertEqual(self._("Thou art a fool!"), builtins._("Thou art a fool!"))  # type: ignore[attr-defined]

    def test_quotes(self):
        for language in ('English', 'Korean'):
            for text in ("I am Gwaelin.", self._("I am Gwaelin, daughter of Lorik."), "Edward", "검객"):
                with self.subTest(language=language, text=text):
                    self.assertEqual(old_quote(language, text), language_named(language).quote(text))
        self.assertEqual(NES_QUOTE_MARKS, ENGLISH.quote_marks)

    def battle(self, language: str) -> Battle:
        battle = Battle.__new__(Battle)
        battle.config = {'LANGUAGE': language}
        battle._ = set_gettext_language(language)
        return battle

    def test_enemy_draws_near(self):
        battle = self.battle('Korean')
        for name in ENEMY_NAMES:
            battle.enemy = SimpleNamespace(name=name)
            korean_name = self._(name)
            old = self._('{} draws near!\n').format(korean_name + get_postposition(korean_name, "이", "가"))
            with self.subTest(name=name):
                self.assertEqual(old, battle.get_enemy_draws_near_string())

    def test_enemy_defeated(self):
        battle = self.battle('Korean')
        for name in ENEMY_NAMES:
            korean_name = self._(name)
            old = f"{korean_name + get_postposition(korean_name, '을', '를')} 물리쳤다!\n"
            with self.subTest(name=name):
                self.assertEqual(old, battle.get_enemy_defeated_string(SimpleNamespace(name=name)))

    def test_level_up(self):
        battle = self.battle('Korean')
        for name in HERO_NAMES:
            cmd_menu = Mock()
            battle.display_level_up_message(cmd_menu, SimpleNamespace(level=4, name=name))
            with self.subTest(name=name):
                # the beep as before: show_line_in_dialog_box's default, disable_sound=False
                cmd_menu.show_line_in_dialog_box.assert_called_once_with(
                    f"{name + particle(name, '은/는')} 5레벨로 올랐다!", add_quotes=False, disable_sound=False)


class TestUnchangedEnglish(TestCase):

    def test_battle_lines(self):
        battle = Battle.__new__(Battle)
        battle.config = {'LANGUAGE': 'English'}
        battle._ = set_gettext_language('English')
        for name, line in (('Slime', 'A Slime draws near!\n'), ('Axe Knight', 'An Axe Knight draws near!\n')):
            battle.enemy = SimpleNamespace(name=name)
            self.assertEqual(line, battle.get_enemy_draws_near_string())
        self.assertEqual("Thou hast done well in defeating the Dragonlord.\n",
                         battle.get_enemy_defeated_string(SimpleNamespace(name='Dragonlord 2')))
        cmd_menu = Mock()
        battle.display_level_up_message(cmd_menu, SimpleNamespace(level=4, name='Edward'))
        cmd_menu.show_line_in_dialog_box.assert_called_once_with(
            "Courage and wit have served thee well.\nThou hast been promoted to the next level.\n", add_quotes=False,
            disable_sound=True)
