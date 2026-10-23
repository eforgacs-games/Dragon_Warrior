"""The Korean catalog has to keep up with the game's text.

When a test here fails because of new text, run
    uv run --frozen python data/text/locales/catalog_tools.py add
fill in the new msgstr entries at the end of data/text/locales/ko/LC_MESSAGES/base.po and commit it. There's no
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
from src.text import WRAP_LENGTH, DialogBoxWrapper

# Translations that leave a placeholder out on purpose (the Korean line reads better without the hero's name)
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


class TestKoreanCatalog(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.po = catalog_tools.read_po()
        cls.translations = {msgid: msgstr for msgid, msgstr in cls.po.items() if msgid and msgstr}

    def test_every_message_has_a_korean_translation(self):
        missing = catalog_tools.missing_translations(self.po)
        self.assertFalse(missing, "\n{} message(s) have no Korean translation in {}:\n\n{}\n{}".format(
            len(missing), catalog_tools.KOREAN_PO.relative_to(catalog_tools.ROOT),
            '\n'.join(catalog_tools.po_entry(msgid, '', locations) for msgid, locations in missing.items()),
            __doc__))

    def test_english_only_messages_are_still_in_the_game(self):
        extracted = catalog_tools.extract_messages()
        stale = [msgid for msgid in catalog_tools.ENGLISH_ONLY if msgid not in extracted]
        self.assertFalse(stale, f"ENGLISH_ONLY lists text the game no longer has: {stale}")

    def test_gettext_calls_can_be_extracted(self):
        # _(f"...") or _("...".format(...)) is looked up after the values are filled in, so it never matches the
        # catalog. Use _("... {} ...").format(...) instead.
        self.assertFalse(catalog_tools.unextractable_gettext_calls())

    def test_translations_keep_placeholders(self):
        problems = []
        for msgid, msgstr in self.translations.items():
            count = placeholder_count(msgid)
            markers = [f"<{i}>" for i in range(count)]
            try:
                formatted = msgstr.format(*markers)
            except (IndexError, KeyError, ValueError) as error:
                problems.append(f"{msgid!r} -> {msgstr!r}: {error!r}")
                continue
            if msgid not in PLACEHOLDER_DROPPED and not all(marker in formatted for marker in markers):
                problems.append(f"{msgid!r} -> {msgstr!r}: a placeholder is missing")
        self.assertFalse(problems, '\n'.join(problems))

    def test_translations_keep_trailing_newlines(self):
        # Battle lines ending in \n are joined with the next line ("... draws near!\n" + "Command?\n")
        problems = [f"{msgid!r} -> {msgstr!r}" for msgid, msgstr in self.translations.items()
                    if msgid.endswith('\n') != msgstr.endswith('\n')]
        self.assertFalse(problems, '\n'.join(problems))

    def test_korean_lines_fit_the_dialog_box(self):
        # draw_text wraps at spaces only (break_long_words=False), so a run of text with no space in it longer than
        # the dialog box would run past its edge
        wrapper = DialogBoxWrapper(width=WRAP_LENGTH, break_long_words=False)
        too_long = [line for msgstr in self.translations.values() for line in wrapper.wrap(msgstr)
                    if len(line) > WRAP_LENGTH]
        self.assertFalse(too_long, too_long)


class TestRuntimeCatalog(TestCase):
    """The game compiles base.po in memory (src/catalog.py) instead of reading a committed base.mo."""

    @classmethod
    def setUpClass(cls):
        cls.po = catalog_tools.read_po()
        cls.korean = catalog.load_translations('ko')

    def test_every_translated_message_comes_out_as_in_the_po(self):
        wrong = [msgid for msgid, msgstr in self.po.items() if msgid and msgstr and self.korean.gettext(msgid) != msgstr]
        self.assertFalse(wrong, f"compiled differently from base.po: {wrong}")

    def test_untranslated_messages_fall_back_to_english(self):
        untranslated = [msgid for msgid, msgstr in self.po.items() if msgid and not msgstr]
        self.assertEqual(untranslated, [self.korean.gettext(msgid) for msgid in untranslated])

    def test_placeholders_survive_compiling(self):
        for msgid, msgstr in self.po.items():
            if msgid and msgstr and placeholder_count(msgid):
                with self.subTest(msgid=msgid):
                    self.assertEqual(placeholder_count(msgstr), placeholder_count(self.korean.gettext(msgid)))

    def test_header_is_read(self):
        self.assertEqual('utf-8', self.korean.charset().lower())

    def test_po_has_no_contexts_or_plurals(self):
        # src/catalog.py reads plain msgid/msgstr entries only
        po_text = catalog_tools.KOREAN_PO.read_text(encoding='utf-8')
        for keyword in ('msgctxt', 'msgid_plural'):
            with self.subTest(keyword=keyword):
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
        self.assertEqual("F1: 조작 방법 보기", control_info.help_button)
        self.assertEqual("1-4: 게임 속도 조절", control_info.speed_controls)
