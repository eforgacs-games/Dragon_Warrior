"""English (2014): the official English script of the 2014 DRAGON QUEST remake (data/text/locales/en_2014), with its
names and terms (data/text/official_script/glossary_en_2014.tsv), drawn in the NES font."""
import builtins
import csv
import re
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

from src.battle import Battle
from src.catalog import po_path, read_po
from src.common import set_gettext_language
from src.config.base_config import language_from_locale
from src.dialog_box import DialogBuffer
from src.languages import ENGLISH, ENGLISH_2014, language_for_locale, language_named
from src.paths import data_path
from src.windows import item_count_tile_row, translated_name_halves
from tests.helpers import drawn_in_nes_font

GLOSSARY = data_path('text', 'official_script', 'glossary_en_2014.tsv')



def word_in(words: str, text: str) -> bool:
    return re.search(rf"\b{re.escape(words)}\b", text) is not None


def glossary_rows() -> list[dict[str, str]]:
    with open(GLOSSARY, encoding='utf-8', newline='') as glossary_file:
        return list(csv.DictReader(glossary_file, delimiter='\t'))


class English2014TestCase(TestCase):

    def setUp(self):
        had_builtin, old_builtin = hasattr(builtins, '_'), getattr(builtins, '_', None)

        def restore():
            if had_builtin:
                builtins._ = old_builtin  # type: ignore[attr-defined]
            elif hasattr(builtins, '_'):
                del builtins._  # type: ignore[attr-defined]
        self.addCleanup(restore)
        self._ = set_gettext_language('English2014')


class TestEnglish2014Language(TestCase):

    def test_declaration(self):
        self.assertIs(ENGLISH_2014, language_named('English2014'))
        self.assertEqual(('ENGLISH (2014)', 'en_2014'), (ENGLISH_2014.option_label, ENGLISH_2014.locale_code))

    def test_an_english_system_plays_the_nes_english(self):
        for system_locale in ('en_US', 'en_GB.UTF-8', 'en'):
            with self.subTest(system_locale=system_locale):
                self.assertIs(ENGLISH, language_for_locale(system_locale))
                self.assertEqual('English', language_from_locale(system_locale))

    def test_spoken_lines_keep_the_nes_quotes(self):
        quoted = ENGLISH_2014.quote("Welcome, wanderer.")
        self.assertEqual("`Welcome, wanderer.’", quoted)
        buffer = DialogBuffer()
        steps = list(buffer.print_message(quoted, quoted=True))
        self.assertEqual(quoted, buffer.lines[0])
        self.assertTrue(any(step.beep for step in steps))

    def test_the_catalog_is_drawn_in_the_nes_font(self):
        self.assertTrue(drawn_in_nes_font(ENGLISH_2014))


class TestEnglish2014Text(English2014TestCase):

    def test_spot_check_translations(self):
        _ = self._
        self.assertEqual("Thou art defeated.", _("Thou art dead."))
        self.assertEqual("Edward uses a medicinal herb.", _("{} used the Herb.").format("Edward"))
        self.assertEqual("The slime casts Sizz!", _("{} chants the spell of {}.").format(_('Slime'), _('HURT')))
        self.assertEqual("Dragon Quest", _("Dragon Warrior"))

    def test_names_follow_the_glossary(self):
        rows = [row for row in glossary_rows() if row['kind'] in ('item', 'spell', 'monster')]
        self.assertGreater(len(rows), 80)
        for row in rows:
            with self.subTest(name=row['english_nes']):
                self.assertEqual(row['english_2014'], self._(row['english_nes']))

    def test_nes_names_are_gone_from_the_text(self):
        # Every 2014 line says the 2014 name: no NES name the remake renamed is left in any msgstr (but as a word of a
        # 2014 name: Herb in Medicinal Herb)
        catalog = read_po(po_path('en_2014'))
        rows = [row for row in glossary_rows() if row['kind'] in ('item', 'place', 'person', 'monster')]
        new_names = ' / '.join(row['english_2014'] for row in rows)
        renamed = [row['english_nes'] for row in rows if not word_in(row['english_nes'], new_names)]
        self.assertIn('Brecconary', renamed)
        for nes_name in renamed:
            left = [msgstr for msgid, msgstr in catalog.items() if msgid and msgstr != msgid and word_in(nes_name, msgstr)]
            with self.subTest(nes_name=nes_name):
                self.assertEqual([], left)


class TestEnglish2014Windows(English2014TestCase):

    def test_names_are_split_as_the_nes_splits_them(self):
        _ = self._
        self.assertEqual(("Medicinal", "Herb"), translated_name_halves("Herb", _("Herb")))
        self.assertEqual(("Sphere of", "Light"), translated_name_halves("Ball of Light", _("Ball of Light")))
        self.assertEqual(("Sunstone", ""), translated_name_halves("Stones of Sunlight", _("Stones of Sunlight")))
        self.assertEqual(("Staff of", "Rain"), translated_name_halves("Staff of Rain", _("Staff of Rain")))

    def test_a_long_first_half_moves_the_count_down(self):
        self.assertEqual(4, item_count_tile_row("Medicinal", 3))
        self.assertEqual(3, item_count_tile_row("Magic", 3))


class TestEnglish2014BattleLines(English2014TestCase):

    def battle(self) -> Battle:
        battle = Battle.__new__(Battle)
        battle.config = {'LANGUAGE': 'English2014'}
        battle._ = self._
        return battle

    def test_the_article_goes_with_the_2014_name(self):
        battle = self.battle()
        for name, line in (('Slime', "A slime appears!\n"), ('Metal Scorpion', "An iron scorpion appears!\n"),
                           ('Axe Knight', "A knight aberrant appears!\n")):
            battle.enemy = SimpleNamespace(name=name)
            with self.subTest(name=name):
                self.assertEqual(line, battle.get_enemy_draws_near_string())
        self.assertEqual("The Dragonlord is defeated!\n",
                         battle.get_enemy_defeated_string(SimpleNamespace(name='Dragonlord 2')))

    def test_level_up_names_the_hero_and_the_level(self):
        cmd_menu = Mock()
        self.battle().display_level_up_message(cmd_menu, SimpleNamespace(level=4, name='Edward'))
        cmd_menu.show_line_in_dialog_box.assert_called_once_with("Edward reaches level 5!\n", add_quotes=False,
                                                                 disable_sound=True)
