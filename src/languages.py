"""The languages the game can be played in, each declared once here (not an NES feature: the NES game is English only).

A language is its name (config LANGUAGE, the saved setting and --language), the name the options overlay's LANGUAGE
row shows, the gettext catalog it is read from (data/text/locales/<code>/LC_MESSAGES/base.po; English is the msgids
themselves) and the few things a catalog can't say: how translated speech is quoted, and the battle lines that a
language puts together from more than one catalog entry (Grammar). The rest of the game asks the language for these
instead of comparing its name.

Adding a language: write its catalog (data/text/locales/catalog_tools.py add <code> lists what to translate) and
add a Language to LANGUAGES. Its text is drawn in Unifont (src/text.py draws anything the NES font hasn't got in
it), which has every CJK character a catalog uses (tests/test_unifont.py).
"""
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import override

from src.korean_particles import KoreanText, get_postposition, particle

type Translate = Callable[[str], str]

ENGLISH_VOWELS = 'AEIOU'
# The NES dialog's quote marks (the font's ` and ’): English speech, and anything left untranslated
NES_QUOTE_MARKS = ('`', '’')


class Grammar:
    """The battle lines made of a catalog line and a name. Each catalog has the line with a placeholder for the name,
    which fits most languages as it is."""

    def enemy_draws_near(self, _: Translate, enemy_name: str) -> str:
        """NES EnAppearText (TextBlock15 entry 2), "A ENM2 draws near!"."""
        return _('{} draws near!\n').format(_(enemy_name))

    def enemy_defeated(self, _: Translate, enemy_name: str) -> str:
        """NES TextBlock15 entry 14, "Thou hast done well in defeating the ENMY."."""
        return _("Thou hast done well in defeating the {}.\n").format(_(enemy_name))

    def level_up(self, _: Translate, hero_name: str, new_level: int) -> str:
        """NES TB16E1, "Courage and wit have served thee well. Thou hast been promoted to the next level."."""
        return _("Courage and wit have served thee well.\nThou hast been promoted to the next level.\n")

    # Whether the text beep sounds while the level up line prints (the NES line prints silently)
    level_up_beeps = False


class EnglishGrammar(Grammar):
    """The NES text: "A" or "An" before the enemy's name (EnAppearText's ENM2 is the name with its article)."""

    @override
    def enemy_draws_near(self, _: Translate, enemy_name: str) -> str:
        line = _('{} draws near!\n').format(_(enemy_name))
        return _('An {}').format(line) if enemy_name[0] in ENGLISH_VOWELS else _('A {}').format(line)


class KoreanGrammar(Grammar):
    """The particle after the enemy's name agrees with it (src/korean_particles.py), and a level up names the hero
    and the new level."""

    @override
    def enemy_draws_near(self, _: Translate, enemy_name: str) -> str:
        name = _(enemy_name)
        return _('{} draws near!\n').format(name + get_postposition(name, "이", "가"))

    @override
    def enemy_defeated(self, _: Translate, enemy_name: str) -> str:
        name = _(enemy_name)
        return f"{name}{get_postposition(name, '을', '를')} 물리쳤다!\n"

    @override
    def level_up(self, _: Translate, hero_name: str, new_level: int) -> str:
        return f"{hero_name}{particle(hero_name, '은/는')} {new_level}레벨로 올랐다!"

    level_up_beeps = True


@dataclass(frozen=True)
class Language:
    name: str  # config LANGUAGE, the saved setting and --language
    option_label: str  # the options overlay's LANGUAGE value, in the language itself so it can be found from any
    # Its catalog, data/text/locales/<locale_code>/LC_MESSAGES/base.po; None: English, the msgids themselves
    locale_code: str | None = None
    # System locales (base_config language_from_locale) that start in this language, by their first letters
    system_locales: tuple[str, ...] = ()
    # What each translation is returned as: KoreanText, whose .format() makes particles agree (src/korean_particles.py)
    text_type: Callable[[str], str] = str
    # How a translated spoken line is quoted (CommandMenu.add_dialog_quotes); a line still in ASCII keeps the NES's
    quote_marks: tuple[str, str] = NES_QUOTE_MARKS
    grammar: Grammar = field(default_factory=Grammar)
    # The playtest checkpoints' hero, CHECKPOINT_HERO_NAME, in this language (src/checkpoints.py); None: unchanged
    checkpoint_hero_name: str | None = None

    @property
    def has_catalog(self) -> bool:
        return self.locale_code is not None

    def quote(self, line: str) -> str:
        """The line in quote marks, as a spoken line is shown."""
        opening, closing = NES_QUOTE_MARKS if line.isascii() else self.quote_marks
        return f"{opening}{line}{closing}"


ENGLISH = Language('English', 'ENGLISH', system_locales=('en',), grammar=EnglishGrammar())
# The checkpoint hero names give the strongest stats, like Arthur (see src/checkpoints.py)
KOREAN = Language('Korean', '한국어', 'ko', system_locales=('ko',), text_type=KoreanText, quote_marks=("'", "'"),
                  grammar=KoreanGrammar(), checkpoint_hero_name='검객')
JAPANESE = Language('Japanese', '日本語', 'ja', system_locales=('ja',), quote_marks=('「', '」'),
                    checkpoint_hero_name='たびびと')

LANGUAGES = (ENGLISH, KOREAN, JAPANESE)
LANGUAGE_NAMES = tuple(language.name for language in LANGUAGES)
CATALOG_LANGUAGES = tuple(language for language in LANGUAGES if language.has_catalog)
_BY_NAME = {language.name: language for language in LANGUAGES}


def language_named(name: str | None) -> Language:
    """The language config LANGUAGE names; English for a name that isn't one (or None)."""
    return _BY_NAME.get(name or '', ENGLISH)


def language_for_locale(locale_name: str | None) -> Language:
    """The language a system locale (e.g. 'ko_KR', 'ja_JP') plays in; English for any other."""
    lowered = (locale_name or '').lower()
    return next((language for language in LANGUAGES if lowered.startswith(language.system_locales)), ENGLISH)
