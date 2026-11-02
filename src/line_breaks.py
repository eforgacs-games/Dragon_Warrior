"""Where a line of Chinese text may break (not an NES feature: the NES game is English, which breaks at blanks).

Chinese is written without blanks between words, so a line may break between any two characters, except that
closing punctuation (。，」…) never starts a line and opening punctuation (「『) never ends one, as in Chinese
typesetting. A run of narrow characters, such as the hero's name or a number, stays whole. A Language with
breaks_anywhere (src/languages.py) wraps its text with break_units; the others break at blanks only.
"""
import unicodedata

# Never at the start of a line: they close what comes before them
NO_BREAK_BEFORE = frozenset('。，、．！？；：）」』”’〉》】…～—・.,!?;:)')
# Never at the end of a line: they open what comes after them
NO_BREAK_AFTER = frozenset('（「『“‘〈《【(')
WIDE = ('W', 'F')  # unicodedata.east_asian_width of the characters Unifont draws two tiles wide (CJK)


def is_wide(character: str) -> bool:
    return unicodedata.east_asian_width(character) in WIDE


def may_break_between(before: str, after: str) -> bool:
    """Whether a line may break between two characters with no blank between them: next to a wide one, unless that
    would put closing punctuation at the start of a line or opening punctuation at the end of one."""
    if after in NO_BREAK_BEFORE or before in NO_BREAK_AFTER:
        return False
    return is_wide(before) or is_wide(after)


def break_units(word: str) -> list[str]:
    """Splits text without blanks into the pieces a line may break between, e.g. '「你好，Edward。」' into
    ['「你', '好，', 'Edward。」']."""
    units: list[str] = []
    for index, character in enumerate(word):
        if units and not may_break_between(word[index - 1], character):
            units[-1] += character
        else:
            units.append(character)
    return units
