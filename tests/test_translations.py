"""The Korean catalog has to keep up with the game's text.

When a test here fails because of new text, run
    uv run --frozen python data/text/locales/catalog_tools.py add
fill in the new msgstr entries at the end of data/text/locales/ko/LC_MESSAGES/base.po, then run
    uv run --frozen python data/text/locales/catalog_tools.py compile
and commit both base.po and base.mo. A message that really should stay English (a dev-only debug key, say) goes in
ENGLISH_ONLY in catalog_tools.py, with the reason.
"""
import builtins
import gettext
import io
import os
import string
from unittest import TestCase

from data.text.intro_lookup_table import ControlInfo
from data.text.locales import catalog_tools
from src.common import set_gettext_language
from src.config.test_config import test_config
from src.text import WRAP_LENGTH, DialogBoxWrapper

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

# Translations that leave a placeholder out on purpose (the Korean line reads better without the hero's name)
PLACEHOLDER_DROPPED = ("Return to the Inn for a rest if thou art wounded in battle, {}.",)


def placeholder_count(text: str) -> int:
    return sum(1 for _, field, _, _ in string.Formatter().parse(text) if field is not None)


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

    def test_compiled_catalog_matches_po(self):
        with open(catalog_tools.KOREAN_MO, 'rb') as mo_file:
            compiled = gettext.GNUTranslations(mo_file)
        expected = gettext.GNUTranslations(io.BytesIO(catalog_tools.mo_bytes(self.po)))
        out_of_date = sorted(msgid for msgid in set(compiled._catalog) | set(expected._catalog)  # type: ignore
                             if compiled._catalog.get(msgid) != expected._catalog.get(msgid))  # type: ignore
        self.assertFalse(out_of_date, "base.mo is out of date with base.po; run "
                                      "`uv run --frozen python data/text/locales/catalog_tools.py compile`. "
                                      f"Differing messages: {out_of_date}")

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


class TestKoreanText(TestCase):

    def setUp(self):
        # set_gettext_language('Korean') installs _ into builtins; put things back afterwards
        self.had_builtin = hasattr(builtins, '_')
        self.old_builtin = getattr(builtins, '_', None)
        self._ = set_gettext_language('Korean')

    def tearDown(self):
        if self.had_builtin:
            builtins._ = self.old_builtin  # type: ignore[attr-defined]
        elif hasattr(builtins, '_'):
            del builtins._  # type: ignore[attr-defined]

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
        self.assertEqual("Edward은/는 비밀 통로를 발견했다!", _("{} discovers the Secret Passage.").format("Edward"))
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
