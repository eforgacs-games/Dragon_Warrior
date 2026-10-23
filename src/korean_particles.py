"""Korean particles (josa) that agree with the word they follow.

Some Korean particles have two forms, picked by whether the word before them ends in a final consonant (batchim):

    은/는  이/가  을/를  과/와  (으)로

A translation can't know which name, item or enemy will be put in its placeholder, so the catalog writes the
combined form right after the placeholder ("{}은/는 {}을/를 발견했다!"), and the text is formatted with
format_with_particles (the Korean gettext function returns KoreanText, whose .format() does it), which replaces each
combined form with the one that fits the substituted word: "용사는 약초를 발견했다!".

How the end of a word is read:

- Hangul: the final syllable's batchim. (으)로 is the special case: a word ending in ㄹ takes 로, like a word with no
  batchim (칼로, not 칼으로).
- Digits: how the number is read in Sino-Korean (일, 이, 삼, ... 십, 백, 천, 만): 1, 7 and 8 end in ㄹ, 3, 6, 0 and
  any round number (십, 백, 천, 만) end in another consonant, and 2, 4, 5 and 9 have none.
- Latin letters (an English hero name such as "Edward"): how the name would be written in Hangul. A name ending in
  "l" ends in ㄹ (Michael -> 마이클), one ending in "m", "n" or "ng" ends in a batchim (Adam -> 아담, Ryan -> 라이언),
  and any other ending has none, since other final consonants get a vowel of their own when transcribed (Edward ->
  에드워드, Mark -> 마크) and vowels and "r" have no batchim (Arthur -> 아서).
- Anything else (punctuation, other scripts, an empty string): the combined form is left as it is, which still reads
  correctly.
"""
import string
from typing import Any
from collections.abc import Mapping, Sequence

HANGUL_FIRST = 0xAC00  # 가
HANGUL_LAST = 0xD7A3  # 힣
JONGSEONG_COUNT = 28  # each initial + medial pair has 27 final consonants plus "none"
JONGSEONG_RIEUL = 8  # ㄹ

# What a word ends in, as far as particles care
NO_BATCHIM = 'none'
RIEUL = 'ㄹ'
OTHER_BATCHIM = 'batchim'

# The last digit of a number read in Sino-Korean: 영 일 이 삼 사 오 육 칠 팔 구
DIGIT_ENDINGS = {'0': OTHER_BATCHIM, '1': RIEUL, '2': NO_BATCHIM, '3': OTHER_BATCHIM, '4': NO_BATCHIM,
                 '5': NO_BATCHIM, '6': OTHER_BATCHIM, '7': RIEUL, '8': RIEUL, '9': NO_BATCHIM}

# combined form -> (after a batchim, after no batchim, after ㄹ)
PARTICLES = {
    '은/는': ('은', '는', '은'),
    '이/가': ('이', '가', '이'),
    '을/를': ('을', '를', '을'),
    '과/와': ('과', '와', '과'),
    '와/과': ('과', '와', '과'),
    '(으)로': ('으로', '로', '로'),
}


def word_ending(word: str) -> str | None:
    """NO_BATCHIM, RIEUL or OTHER_BATCHIM for the end of word, or None if it can't be told (see the module docstring)."""
    if not word:
        return None
    last = word[-1]
    if HANGUL_FIRST <= ord(last) <= HANGUL_LAST:
        jongseong = (ord(last) - HANGUL_FIRST) % JONGSEONG_COUNT
        if jongseong == 0:
            return NO_BATCHIM
        return RIEUL if jongseong == JONGSEONG_RIEUL else OTHER_BATCHIM
    if last.isascii() and last.isdigit():
        digits = word[len(word.rstrip('0123456789')):]
        if digits.strip('0') and digits.endswith('0'):
            return OTHER_BATCHIM  # 십, 백, 천, 만
        return DIGIT_ENDINGS[last]
    if last.isascii() and last.isalpha():
        lowered = word.lower()
        if lowered.endswith('l'):
            return RIEUL
        if lowered.endswith(('m', 'n', 'ng')):
            return OTHER_BATCHIM
        return NO_BATCHIM
    return None


def has_final_consonant(word: str) -> bool:
    """Whether word ends in a batchim (ㄹ included)."""
    return word_ending(word) in (RIEUL, OTHER_BATCHIM)


def particle(word: str, combined: str) -> str:
    """The form of the particle combined (one of PARTICLES, e.g. "을/를") that goes after word."""
    after_batchim, after_none, after_rieul = PARTICLES[combined]
    ending = word_ending(word)
    if ending is None:
        return combined
    return {OTHER_BATCHIM: after_batchim, NO_BATCHIM: after_none, RIEUL: after_rieul}[ending]


def get_postposition(word: str, consonant_josa: str, vowel_josa: str) -> str:
    """consonant_josa after a word ending in a batchim (e.g. "을"), vowel_josa otherwise (e.g. "를")."""
    return consonant_josa if has_final_consonant(word) else vowel_josa


def resolve_leading_particle(word: str, text: str) -> str:
    """text, with a combined particle at its very start replaced by the form that goes after word."""
    for combined in PARTICLES:
        if text.startswith(combined):
            return particle(word, combined) + text[len(combined):]
    return text


_FORMATTER = string.Formatter()


def format_with_particles(template: str, args: Sequence[Any] = (), kwargs: Mapping[str, Any] | None = None) -> str:
    """str.format, except that a combined particle right after a placeholder agrees with the value put there."""
    kwargs = {} if kwargs is None else kwargs
    pieces = []
    previous: str | None = None  # the value just substituted
    next_index = 0
    for literal, field_name, format_spec, conversion in _FORMATTER.parse(template):
        if previous is not None:
            literal = resolve_leading_particle(previous, literal)
        pieces.append(literal)
        if field_name is None:
            previous = None
            continue
        if field_name == '':
            field_name = str(next_index)
            next_index += 1
        value, _ = _FORMATTER.get_field(field_name, args, kwargs)
        value = _FORMATTER.convert_field(value, conversion)
        previous = _FORMATTER.format_field(value, format_spec or '')
        pieces.append(previous)
    return ''.join(pieces)


class KoreanText(str):
    """A translated string whose .format() makes the particles after its placeholders agree with the values."""

    def format(self, *args: Any, **kwargs: Any) -> str:  # type: ignore[override]
        return format_with_particles(str(self), args, kwargs)
