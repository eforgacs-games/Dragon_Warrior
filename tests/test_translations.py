"""Every catalog (the Korean, the Japanese, ...: src/languages.py) has to keep up with the game's text.

When a test here fails because of new text, run
    uv run --frozen python data/text/locales/catalog_tools.py add <locale code: ko, ja, ...>
fill in the new msgstr entries at the end of data/text/locales/<code>/LC_MESSAGES/base.po and commit it. There's no
compile step: the game compiles base.po in memory when it runs (src/catalog.py). A message that really should stay
English (a dev-only debug key, say) goes in ENGLISH_ONLY in catalog_tools.py, with the reason.
"""
import builtins
import string
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from data.text.intro_lookup_table import ControlInfo
from data.text.locales import catalog_tools
from src import catalog
from src.common import set_gettext_language
from src.config.test_config import test_config
from src.languages import CATALOG_LANGUAGES
from src.text import WRAP_LENGTH, DialogBoxWrapper

# Translations that may leave a placeholder out on purpose (the Korean line reads better without the hero's name)
PLACEHOLDER_DROPPED = ("Return to the Inn for a rest if thou art wounded in battle, {}.",)


def placeholder_count(text: str) -> int:
    return sum(1 for _, field, _, _ in string.Formatter().parse(text) if field is not None)


def keep_builtin_gettext():
    """set_gettext_language('Korean') installs _ into builtins; returns a function that puts things back."""
    had_builtin = hasattr(builtins, '_')
    old_builtin = getattr(builtins, '_', None)

    def restore():
        if had_builtin:
            builtins._ = old_builtin  # type: ignore[attr-defined]
        elif hasattr(builtins, '_'):
            del builtins._  # type: ignore[attr-defined]

    return restore


def catalogs() -> dict[str, dict[str, str]]:
    """Each catalog's msgid -> msgstr (header included), by language name."""
    return {language.name: catalog_tools.read_po(catalog_tools.catalog_path(language.locale_code or ''))
            for language in CATALOG_LANGUAGES}


class TestCatalogs(TestCase):
    """The checks every catalog passes, each language a subTest."""

    @classmethod
    def setUpClass(cls):
        cls.catalogs = catalogs()
        cls.translations = {name: {msgid: msgstr for msgid, msgstr in po.items() if msgid and msgstr}
                            for name, po in cls.catalogs.items()}

    def test_every_language_has_a_catalog(self):
        self.assertIn('Korean', self.catalogs)
        self.assertGreater(len(self.translations['Korean']), 700)

    def test_every_message_has_a_translation(self):
        for name, po in self.catalogs.items():
            missing = catalog_tools.missing_translations(po)
            with self.subTest(language=name):
                self.assertFalse(missing, "\n{} message(s) have no {} translation:\n\n{}\n{}".format(
                    len(missing), name,
                    '\n'.join(catalog_tools.po_entry(msgid, '', locations) for msgid, locations in missing.items()),
                    __doc__))

    def test_every_catalog_has_the_korean_catalogs_messages(self):
        # Messages no longer in the game stay in a catalog until they're cleaned up from all of them at once
        korean = set(self.catalogs['Korean'])
        for name, po in self.catalogs.items():
            with self.subTest(language=name):
                self.assertEqual(sorted(korean - set(po)), [])

    def test_english_only_messages_are_still_in_the_game(self):
        extracted = catalog_tools.extract_messages()
        stale = [msgid for msgid in catalog_tools.ENGLISH_ONLY if msgid not in extracted]
        self.assertFalse(stale, f"ENGLISH_ONLY lists text the game no longer has: {stale}")

    def test_gettext_calls_can_be_extracted(self):
        # _(f"...") or _("...".format(...)) is looked up after the values are filled in, so it never matches the
        # catalog. Use _("... {} ...").format(...) instead.
        self.assertFalse(catalog_tools.unextractable_gettext_calls())

    def test_translations_keep_placeholders(self):
        for name, translations in self.translations.items():
            problems = []
            for msgid, msgstr in translations.items():
                count = placeholder_count(msgid)
                markers = [f"<{i}>" for i in range(count)]
                try:
                    formatted = msgstr.format(*markers)
                except (IndexError, KeyError, ValueError) as error:
                    problems.append(f"{msgid!r} -> {msgstr!r}: {error!r}")
                    continue
                if msgid not in PLACEHOLDER_DROPPED and not all(marker in formatted for marker in markers):
                    problems.append(f"{msgid!r} -> {msgstr!r}: a placeholder is missing")
            with self.subTest(language=name):
                self.assertFalse(problems, '\n'.join(problems))

    def test_translations_keep_trailing_newlines(self):
        # Battle lines ending in \n are joined with the next line ("... draws near!\n" + "Command?\n")
        for name, translations in self.translations.items():
            problems = [f"{msgid!r} -> {msgstr!r}" for msgid, msgstr in translations.items()
                        if msgid.endswith('\n') != msgstr.endswith('\n')]
            with self.subTest(language=name):
                self.assertFalse(problems, '\n'.join(problems))

    def test_lines_fit_the_dialog_box(self):
        # draw_text wraps at spaces only (break_long_words=False), so a run of text with no space in it longer than
        # the dialog box would run past its edge. A Hangul syllable or a kana or kanji is one NES tile wide in
        # Unifont, like an English letter in the NES font.
        wrapper = DialogBoxWrapper(width=WRAP_LENGTH, break_long_words=False)
        for name, translations in self.translations.items():
            too_long = [line for msgstr in translations.values() for line in wrapper.wrap(msgstr)
                        if len(line) > WRAP_LENGTH]
            with self.subTest(language=name):
                self.assertFalse(too_long, too_long)


class TestRuntimeCatalog(TestCase):
    """The game compiles base.po in memory (src/catalog.py) instead of reading a committed base.mo."""

    @classmethod
    def setUpClass(cls):
        cls.catalogs = catalogs()
        cls.compiled = {language.name: catalog.load_translations(language.locale_code or '')
                        for language in CATALOG_LANGUAGES}

    def test_every_translated_message_comes_out_as_in_the_po(self):
        for name, po in self.catalogs.items():
            compiled = self.compiled[name]
            wrong = [msgid for msgid, msgstr in po.items() if msgid and msgstr and compiled.gettext(msgid) != msgstr]
            with self.subTest(language=name):
                self.assertFalse(wrong, f"compiled differently from base.po: {wrong}")

    def test_untranslated_messages_fall_back_to_english(self):
        for name, po in self.catalogs.items():
            untranslated = [msgid for msgid, msgstr in po.items() if msgid and not msgstr]
            with self.subTest(language=name):
                self.assertEqual(untranslated, [self.compiled[name].gettext(msgid) for msgid in untranslated])

    def test_placeholders_survive_compiling(self):
        for name, po in self.catalogs.items():
            for msgid, msgstr in po.items():
                if msgid and msgstr and placeholder_count(msgid):
                    with self.subTest(language=name, msgid=msgid):
                        self.assertEqual(placeholder_count(msgstr),
                                         placeholder_count(self.compiled[name].gettext(msgid)))

    def test_header_is_read(self):
        for name, compiled in self.compiled.items():
            with self.subTest(language=name):
                self.assertEqual('utf-8', compiled.charset().lower())

    def test_po_has_no_contexts_or_plurals(self):
        # src/catalog.py reads plain msgid/msgstr entries only
        for language in CATALOG_LANGUAGES:
            po_text = catalog_tools.catalog_path(language.locale_code or '').read_text(encoding='utf-8')
            for keyword in ('msgctxt', 'msgid_plural'):
                with self.subTest(language=language.name, keyword=keyword):
                    self.assertNotIn(f'\n{keyword} ', po_text)

    def test_tricky_strings_compile(self):
        po_text = (
            'msgid ""\nmsgstr "Content-Type: text/plain; charset=UTF-8\\n"\n\n'
            '#: src/example.py:1\nmsgid ""\n"Line one\\n"\n"Line \\"two\\""\nmsgstr "첫 줄\\n\\"둘째\\" 줄"\n\n'
            'msgid "{} wins."\nmsgstr "{} 승리."\n\n'
            'msgid "Not translated yet"\nmsgstr ""\n'
        )
        with tempfile.TemporaryDirectory() as directory:
            po_file = Path(directory, 'base.po')
            po_file.write_text(po_text, encoding='utf-8')
            translations = catalog.compile_po(po_file)
        self.assertEqual('첫 줄\n"둘째" 줄', translations.gettext('Line one\nLine "two"'))
        self.assertEqual('Edward 승리.', translations.gettext('{} wins.').format('Edward'))
        self.assertEqual('Not translated yet', translations.gettext('Not translated yet'))

    def test_compiles_without_writing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            po_file = Path(directory, 'base.po')
            po_file.write_text('msgid ""\nmsgstr "Content-Type: text/plain; charset=UTF-8\\n"\n\n'
                               'msgid "Hello"\nmsgstr "안녕"\n', encoding='utf-8')
            self.assertEqual('안녕', catalog.compile_po(po_file).gettext('Hello'))
            self.assertEqual([po_file], list(Path(directory).iterdir()))

    def test_compiled_once_per_run(self):
        restore_builtin_gettext = keep_builtin_gettext()
        self.addCleanup(restore_builtin_gettext)
        catalog.load_translations.cache_clear()
        with patch('src.catalog.read_po', wraps=catalog.read_po) as read_po:
            for _ in range(3):
                set_gettext_language('Korean')
            catalog.load_translations('ko')
        self.assertEqual(1, read_po.call_count)
        self.assertIs(catalog.load_translations('ko'), catalog.load_translations('ko'))


class TestKoreanText(TestCase):

    def setUp(self):
        self.addCleanup(keep_builtin_gettext())
        self._ = set_gettext_language('Korean')

    def test_spot_check_translations(self):
        _ = self._
        self.assertEqual("잘 왔다, Edward.\n나는 왕 중의 왕, 용왕이다.",
                         _("Welcome, {}.\nI am the Dragonlord--King of Kings.").format("Edward"))
        self.assertEqual("어리석은 놈!", _("Thou art a fool!"))
        self.assertEqual("빛의 구슬을 찾았다!", _("Thou hast found the Ball of Light."))
        self.assertEqual("만세!\n만세!\nEdward 만세!", _("Hurrah!\nHurrah!\nLong live {}!").format("Edward"))
        self.assertEqual("저는 로릭 왕의 딸 로라입니다.", _("I am Gwaelin, daughter of Lorik."))
        self.assertEqual("몸에 저주가 걸려 있다.", _("A curse is upon thy body."))
        self.assertEqual("성채 도시 메르키드에 오신 것을 환영합니다.", _("Welcome to Cantlin, the castle town."))
        self.assertEqual("Edward는 비밀 통로를 발견했다!", _("{} discovers the Secret Passage.").format("Edward"))
        self.assertEqual("남쪽으로 3, 그리고..", _("{} to the south and..").format(3))
        self.assertEqual("게임이 2배속으로 설정되었습니다.\n(120 FPS)",
                         _("Game set to {}x speed.\n({} FPS)").format(2, 120))

    def test_names_used_through_variables_are_translated(self):
        _ = self._
        self.assertEqual("로토의 증표", _("Erdrick's Token"))
        self.assertEqual("죽음의 목걸이", _("Death Necklace"))
        self.assertEqual("호이미", _("HEAL"))
        self.assertEqual("용왕", _("Dragonlord 2"))

    def test_untranslated_text_falls_back_to_english(self):
        self.assertEqual("F5: Warp", self._("F5: Warp"))

    def test_control_info_in_korean(self):
        control_info = ControlInfo({**test_config, 'LANGUAGE': 'Korean'})
        self.assertEqual("H: 조작 방법 보기", control_info.help_button)
        self.assertEqual("1-5: 게임 속도 조절", control_info.speed_controls)
