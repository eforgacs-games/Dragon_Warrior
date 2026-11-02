"""Line breaking for Chinese (src/line_breaks.py, Language.breaks_anywhere): a line may end between any two characters,
never before closing punctuation or after opening punctuation, and every other language wraps exactly as before."""
import re
import textwrap
from unittest import TestCase

from src.catalog import po_path, read_po
from src.dialog_box import DialogBuffer, words
from src.languages import CATALOG_LANGUAGES, LANGUAGES
from src.line_breaks import NO_BREAK_AFTER, NO_BREAK_BEFORE, break_units, may_break_between
from src.message_log import text_width, wrap
from src.text import WRAP_LENGTH, DialogBoxWrapper

CHINESE_LINE = "勇者Edward啊！去打倒龍王，把光之石取回來吧！我會為你祈禱……「願光明與你同在。」"
LOG_WIDTH, LOG_INDENT = 28, 2


class OldDialogBoxWrapper(textwrap.TextWrapper):
    """DialogBoxWrapper before breaks_anywhere, inlined."""

    def wrap(self, text):
        return [line for para in text.split('\n') for line in textwrap.TextWrapper.wrap(self, para)]


def old_words(paragraph: str) -> list[str]:
    """What DialogBuffer.print_message wrapped whole before breaks_anywhere, inlined."""
    return re.findall(r' |[^ ]+', paragraph)


def old_log_wrap(text: str, width: int, indent: int) -> list[str]:
    """message_log.wrap before breaks_anywhere, inlined."""
    lines: list[str] = []
    line = ''
    for word in text.split(' '):
        candidate = f'{line} {word}' if line else word
        if text_width(candidate) <= width - (indent if lines else 0):
            line = candidate
            continue
        if line:
            lines.append(line)
        line = word
        while text_width(line) > width - (indent if lines else 0):
            cut = len(line)
            while text_width(line[:cut]) > width - (indent if lines else 0):
                cut -= 1
            lines.append(line[:cut])
            line = line[cut:]
    if line:
        lines.append(line)
    return [(' ' * indent if number else '') + text for number, text in enumerate(lines)]


def printed_rows(text: str, quoted: bool = False, breaks_anywhere: bool = False) -> list[str]:
    buffer = DialogBuffer()
    list(buffer.print_message(text, quoted, breaks_anywhere=breaks_anywhere))
    return buffer.visible_lines


class TestBreakUnits(TestCase):

    def test_every_chinese_character_is_its_own_unit(self):
        self.assertEqual(['打', '開', '寶', '箱'], break_units('打開寶箱'))

    def test_closing_punctuation_stays_with_the_character_before(self):
        self.assertEqual(['得', '到', '了', '金', '幣。'], break_units('得到了金幣。'))
        self.assertEqual(['好', '棒', '哦！」'], break_units('好棒哦！」'))
        self.assertEqual(['可', '是……'], break_units('可是……'))

    def test_opening_punctuation_stays_with_the_character_after(self):
        self.assertEqual(['「你', '好，', 'Edward。」'], break_units('「你好，Edward。」'))
        self.assertEqual(['“勇', '者”'], break_units('“勇者”'))

    def test_names_and_numbers_stay_whole(self):
        self.assertEqual(['Edward', '使', '用', '了', '藥', '草。'], break_units('Edward使用了藥草。'))
        self.assertEqual(['還', '差', '120', '點'], break_units('還差120點'))
        self.assertEqual(['Thou'], break_units('Thou'))

    def test_may_break_between(self):
        self.assertTrue(may_break_between('龍', '王'))
        self.assertTrue(may_break_between('d', '使'))
        self.assertFalse(may_break_between('E', 'd'))
        self.assertFalse(may_break_between('王', '。'))
        self.assertFalse(may_break_between('「', '王'))


class TestWrappingChinese(TestCase):

    def assert_well_broken(self, rows: list[str], width: int):
        self.assertGreater(len(rows), 1)
        for row in rows:
            self.assertLessEqual(len(row), width, rows)
            self.assertNotIn(row.lstrip()[0], NO_BREAK_BEFORE, rows)
            self.assertNotIn(row[-1], NO_BREAK_AFTER, rows)
        self.assertEqual(CHINESE_LINE, ''.join(row.lstrip() for row in rows))

    def test_draw_texts_wrapper(self):
        rows = DialogBoxWrapper(width=WRAP_LENGTH, break_long_words=False, breaks_anywhere=True).wrap(CHINESE_LINE)
        self.assertEqual(WRAP_LENGTH, len(rows[0]))  # full rows, not a row per sentence
        self.assert_well_broken(rows, WRAP_LENGTH)

    def test_dialog_window(self):
        self.assert_well_broken(printed_rows(CHINESE_LINE, breaks_anywhere=True), 22)

    def test_quoted_dialog_keeps_the_nes_indent(self):
        rows = printed_rows("「" + CHINESE_LINE + "」", quoted=True, breaks_anywhere=True)
        self.assertTrue(rows[0].startswith('「勇者'))
        self.assertTrue(all(row.startswith(' ') for row in rows[1:]), rows)

    def test_message_log(self):
        rows = wrap(CHINESE_LINE, LOG_WIDTH, LOG_INDENT, breaks_anywhere=True)
        self.assertTrue(all(text_width(row) <= LOG_WIDTH for row in rows), rows)
        self.assert_well_broken(rows, LOG_WIDTH)

    def test_without_breaks_anywhere_a_chinese_line_only_breaks_at_blanks(self):
        wrapper = DialogBoxWrapper(width=WRAP_LENGTH, break_long_words=False)
        self.assertEqual([CHINESE_LINE], wrapper.wrap(CHINESE_LINE))
        self.assertEqual([CHINESE_LINE], words(CHINESE_LINE))


class TestOtherLanguagesWrapAsBefore(TestCase):
    """English, Korean and Japanese break at blanks only, byte for byte as before breaks_anywhere."""

    def test_only_chinese_breaks_anywhere(self):
        self.assertEqual({'Traditional Chinese', 'Simplified Chinese'},
                         {language.name for language in LANGUAGES if language.breaks_anywhere})

    def test_every_line_wraps_as_before(self):
        old_wrapper = OldDialogBoxWrapper(width=WRAP_LENGTH, break_long_words=False)
        for language in CATALOG_LANGUAGES:
            if language.breaks_anywhere:
                continue
            wrapper = DialogBoxWrapper(width=WRAP_LENGTH, break_long_words=False,
                                       breaks_anywhere=language.breaks_anywhere)
            catalog = read_po(po_path(language.locale_code or ''))
            messages = [*catalog, *catalog.values()]  # the English msgids too
            with self.subTest(language=language.name):
                for message in messages:
                    self.assertEqual(old_wrapper.wrap(message), wrapper.wrap(message))
                    for paragraph in message.split('\n'):
                        self.assertEqual(old_words(paragraph), words(paragraph, language.breaks_anywhere))
                        self.assertEqual(old_log_wrap(paragraph, LOG_WIDTH, LOG_INDENT),
                                         wrap(paragraph, LOG_WIDTH, LOG_INDENT, language.breaks_anywhere))
