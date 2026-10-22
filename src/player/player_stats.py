"""The hero's stats per level and how the name changes them.

NES source: LoadStats (Bank03, $F050), SetBaseStats (Bank01, $99B4), BaseStatsTbl (Bank01, $A0CD), ReduceStat
(Bank03, $F10C) and LevelUpTbl (Bank03, $F35B), from the nmikstas/dragon-warrior-disassembly.

LoadStats works the stats out from scratch every time it runs (at the start, after every fight, on loading):

1. The level is the highest LevelUpTbl entry the experience reaches (GetLevelLoop).
2. SetBaseStats copies strength, agility, max HP and max MP for that level out of BaseStatsTbl.
3. NameAddLoop adds up the tile values of the first four name characters (DispName0-DispName3) in 8 bits.
4. Bits 0-1 of the sum are StatPenalty, bits 2-3 (shifted down) are StatBonus, 0-3.
5. Bit 0 clear: strength is reduced. Bit 0 set: max MP is reduced, but only if it isn't 0 (levels 1 and 2 have
   no MP, so they get neither the cut nor the bonus).
   Bit 1 clear: agility is reduced. Bit 1 set: max HP is reduced.
6. ReduceStat: stat * 9 / 10 (16-bit WordMultiply, then WordDivide, which drops the remainder) + StatBonus.

So two stats always grow at the full rate ("fast") and the other two at 90% plus a 0-3 head start ("slow"). Only
the low four bits of the sum matter, so a name falls into one of 16 groups: 4 growth patterns x 4 bonuses.
"""
import unicodedata
from typing import Literal, TypedDict, cast

from src.spells import Spell

# NES text tile values of the characters on the name entry screen (WndProcessChar, SymbolConvTbl, Bank01).
# A-Z: index + TXT_UPR_A ($24). a-z: index - $17, giving $0A-$23. Symbols come from SymbolConvTbl.
NAME_CHARACTER_VALUES: dict[str, int] = {
    **{chr(ord('A') + i): 0x24 + i for i in range(26)},
    **{chr(ord('a') + i): 0x0A + i for i in range(26)},
    '-': 0x49,  # TXT_DASH
    "'": 0x40,  # TXT_APOS
    '!': 0x4C,  # TXT_EXCLAIM
    '?': 0x4B,  # TXT_QUESTION
    '(': 0x4F,  # TXT_OPN_PAREN
    ')': 0x4E,  # TXT_CLS_PAREN
    ' ': 0x60,  # TXT_BLANK1
    ',': 0x48,  # TXT_COMMA
    '.': 0x47,  # TXT_PERIOD
    # Not on the name entry screen, but in the font: the digits are tiles $00-$09.
    **{str(digit): digit for digit in range(10)},
}
# InitNameWindow fills the name buffer with TL_BLANK_TILE2 ($60) first, so a name shorter than four characters
# is padded with blanks.
BLANK_TILE = 0x60
NAME_STAT_LETTERS = 4  # NameAddLoop: LDX #$04 ... ADC $B4,X adds DispName3..DispName0


def name_character_value(character: str) -> int:
    """The NES tile value of one name character.

    The NES can only enter the characters in NAME_CHARACTER_VALUES. For anything else (lowercase/uppercase letters
    with accents, Korean, ...) this game uses:
    - a letter with accents counts as the plain letter (NFKD, then drop the combining marks), so "É" is "E";
    - any other character counts as the low byte of its Unicode code point, so different names (Korean ones too)
      still spread across all 16 groups and always give the same stats.
    """
    if character in NAME_CHARACTER_VALUES:
        return NAME_CHARACTER_VALUES[character]
    base = ''.join(c for c in unicodedata.normalize('NFKD', character) if not unicodedata.combining(c))
    if len(base) == 1 and base in NAME_CHARACTER_VALUES:
        return NAME_CHARACTER_VALUES[base]
    return ord(character) & 0xFF


def get_name_tiles(name: str) -> tuple[int, ...]:
    """DispName0-DispName3: the first four characters of the name, padded with blank tiles."""
    tiles = [name_character_value(character) for character in name[:NAME_STAT_LETTERS]]
    return tuple(tiles + [BLANK_TILE] * (NAME_STAT_LETTERS - len(tiles)))


# BaseStatsTbl (Bank01, $A0CD) and LevelUpTbl (Bank03, $F35B), plus the spell learned at each level.
# These are the base values: never change them, use get_stats_for_level for a named hero.
levels_list: dict[int, dict[str, int | Spell | None]] = {
    1: {'total_exp': 0, 'strength': 4, 'agility': 4, 'max_hp': 15, 'max_mp': 0, 'spell': None},
    2: {'total_exp': 7, 'strength': 5, 'agility': 4, 'max_hp': 22, 'max_mp': 0, 'spell': None},
    3: {'total_exp': 23, 'strength': 7, 'agility': 6, 'max_hp': 24, 'max_mp': 5, 'spell': Spell.HEAL},
    4: {'total_exp': 47, 'strength': 7, 'agility': 8, 'max_hp': 31, 'max_mp': 16, 'spell': Spell.HURT},
    5: {'total_exp': 110, 'strength': 12, 'agility': 10, 'max_hp': 35, 'max_mp': 20, 'spell': None},
    6: {'total_exp': 220, 'strength': 16, 'agility': 10, 'max_hp': 38, 'max_mp': 24, 'spell': None},
    7: {'total_exp': 450, 'strength': 18, 'agility': 17, 'max_hp': 40, 'max_mp': 26, 'spell': Spell.SLEEP},
    8: {'total_exp': 800, 'strength': 22, 'agility': 20, 'max_hp': 46, 'max_mp': 29, 'spell': None},
    9: {'total_exp': 1300, 'strength': 30, 'agility': 22, 'max_hp': 50, 'max_mp': 36, 'spell': Spell.RADIANT},
    10: {'total_exp': 2000, 'strength': 35, 'agility': 31, 'max_hp': 54, 'max_mp': 40, 'spell': Spell.STOPSPELL},
    11: {'total_exp': 2900, 'strength': 40, 'agility': 35, 'max_hp': 62, 'max_mp': 50, 'spell': None},
    12: {'total_exp': 4000, 'strength': 48, 'agility': 40, 'max_hp': 63, 'max_mp': 58, 'spell': Spell.OUTSIDE},
    13: {'total_exp': 5500, 'strength': 52, 'agility': 48, 'max_hp': 70, 'max_mp': 64, 'spell': Spell.RETURN},
    14: {'total_exp': 7500, 'strength': 60, 'agility': 55, 'max_hp': 78, 'max_mp': 70, 'spell': None},
    15: {'total_exp': 10000, 'strength': 68, 'agility': 64, 'max_hp': 86, 'max_mp': 72, 'spell': Spell.REPEL},
    16: {'total_exp': 13000, 'strength': 72, 'agility': 70, 'max_hp': 92, 'max_mp': 95, 'spell': None},
    17: {'total_exp': 16000, 'strength': 72, 'agility': 78, 'max_hp': 100, 'max_mp': 100, 'spell': Spell.HEALMORE},
    18: {'total_exp': 19000, 'strength': 85, 'agility': 84, 'max_hp': 115, 'max_mp': 108, 'spell': None},
    19: {'total_exp': 22000, 'strength': 87, 'agility': 86, 'max_hp': 130, 'max_mp': 115, 'spell': Spell.HURTMORE},
    20: {'total_exp': 26000, 'strength': 92, 'agility': 88, 'max_hp': 138, 'max_mp': 128, 'spell': None},
    21: {'total_exp': 30000, 'strength': 95, 'agility': 90, 'max_hp': 149, 'max_mp': 135, 'spell': None},
    22: {'total_exp': 34000, 'strength': 97, 'agility': 90, 'max_hp': 158, 'max_mp': 146, 'spell': None},
    23: {'total_exp': 38000, 'strength': 99, 'agility': 94, 'max_hp': 165, 'max_mp': 153, 'spell': None},
    24: {'total_exp': 42000, 'strength': 103, 'agility': 98, 'max_hp': 170, 'max_mp': 161, 'spell': None},
    25: {'total_exp': 46000, 'strength': 113, 'agility': 100, 'max_hp': 174, 'max_mp': 161, 'spell': None},
    26: {'total_exp': 50000, 'strength': 117, 'agility': 105, 'max_hp': 180, 'max_mp': 168, 'spell': None},
    27: {'total_exp': 54000, 'strength': 125, 'agility': 107, 'max_hp': 189, 'max_mp': 175, 'spell': None},
    28: {'total_exp': 58000, 'strength': 130, 'agility': 115, 'max_hp': 195, 'max_mp': 180, 'spell': None},
    29: {'total_exp': 62000, 'strength': 135, 'agility': 120, 'max_hp': 200, 'max_mp': 190, 'spell': None},
    30: {'total_exp': 65535, 'strength': 140, 'agility': 130, 'max_hp': 210, 'max_mp': 200, 'spell': None},
}


def set_exp():
    for level_int, level_dict in levels_list.items():
        if level_int == 1:
            level_dict['exp'] = 0
        else:
            level_dict['exp'] = level_dict['total_exp'] - levels_list[level_int - 1]['total_exp']


set_exp()


class LevelStats(TypedDict):
    strength: int
    agility: int
    max_hp: int
    max_mp: int


def get_total_name_score(name: str) -> int:
    """NameAddLoop (LF089): the 8-bit sum (CLC, ADC per character, so the carry is dropped) of DispName0-3."""
    return sum(get_name_tiles(name)) & 0xFF


def get_bonus(name_score: int) -> int:
    """LF096: StatBonus is bits 2 and 3 of the name sum (LSR, LSR, AND #$03)."""
    return (name_score >> 2) & 0x03


StatName = Literal['strength', 'agility', 'max_hp', 'max_mp']


def determine_penalized_stats(name_score: int) -> tuple[StatName, StatName]:
    """LF092 StatPenalty = sum AND #$03, then (LF09E-LF0CB):
    bit 1 clear: agility, set: max_hp (ChkAgiPenalty);
    bit 0 clear: strength, set: max_mp (LF0A1, BCS MaxMPPenalty)."""
    return ('max_hp' if name_score & 0x02 else 'agility'), ('max_mp' if name_score & 0x01 else 'strength')


def reduce_stat(stat: int, bonus: int) -> int:
    """ReduceStat (LF10C): stat * 9 / 10, rounded down by WordDivide, plus StatBonus. Every value fits in a byte."""
    return stat * 9 // 10 + bonus


def get_base_stats(level: int) -> LevelStats:
    """SetBaseStats (L99B4): the BaseStatsTbl row for the level, before the name is applied."""
    row = levels_list[level]
    return LevelStats(strength=cast(int, row['strength']), agility=cast(int, row['agility']),
                      max_hp=cast(int, row['max_hp']), max_mp=cast(int, row['max_mp']))


def get_stats_for_level(name: str, level: int) -> LevelStats:
    """LoadStats (LF050) for a hero with this name at this level: BaseStatsTbl, then the name's penalties."""
    stats = get_base_stats(level)
    name_score = get_total_name_score(name)
    bonus = get_bonus(name_score)
    for stat in determine_penalized_stats(name_score):
        if stat == 'max_mp' and stats['max_mp'] == 0:
            continue  # LF0AF: BEQ ChkAgiPenalty, no MP to reduce and no bonus either
        stats[stat] = reduce_stat(stats[stat], bonus)
    return stats


def get_level_by_experience(total_experience: int) -> int:
    """GetLevelLoop (LF056): count down from level 30 to the first LevelUpTbl entry the experience reaches."""
    for level in reversed(levels_list):
        if total_experience >= cast(int, levels_list[level]['total_exp']):
            return level
    return 1
