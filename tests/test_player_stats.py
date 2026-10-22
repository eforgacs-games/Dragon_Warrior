"""Name-based stats, checked against the NES algorithm (LoadStats, Bank03 $F050; see src/player/player_stats.py).

How the expected numbers were worked out by hand from the disassembly:

1. Add up the NES tile values of the first four name characters in 8 bits (NameAddLoop). Upper case is $24 (A)
   to $3D (Z), lower case $0A (a) to $23 (z). The blank, $60, pads names shorter than four.
2. Bits 0-1 of the sum: bit 0 clear cuts strength, set cuts max MP; bit 1 clear cuts agility, set cuts max HP.
   Bits 2-3 are the bonus, 0-3.
3. Each cut stat is BaseStatsTbl * 9 // 10 + bonus (ReduceStat). A max MP of 0 (levels 1-2) is left alone.

The four names below cover the four growth patterns, each with a different bonus:

  Steve   = S $36 + t $1D + e $0E + v $1F = $80 -> %00: strength, agility cut; bonus 0
  Deez    = D $27 + e $0E + e $0E + z $23 = $66 -> %10: strength, max HP cut;  bonus 1 (the disassembly's example)
  Erdrick = E $28 + r $1B + d $0D + r $1B = $6B -> %11: max HP, max MP cut;    bonus 2
  Gina    = G $2A + i $12 + n $17 + a $0A = $5D -> %01: agility, max MP cut;   bonus 3

For example, Erdrick at level 30: BaseStatsTbl has 140, 130, 210, 200, so max HP = 210 * 9 // 10 + 2 = 191 and
max MP = 200 * 9 // 10 + 2 = 182, giving (140, 130, 191, 182).
The same rules also reproduce, at every level, the 16 tables from https://guides.gamercorner.net/dw/name-stats/
that an older version of this file held (Steve, Eva, Im, Va, Eddie, Ed, Walter, Uno, gooo, Sejin, Stephen, James,
Gao, Jacquie, Wall, Edward).
"""
import os
from unittest import TestCase

from src.player import player_stats
from src.player.player_stats import (BLANK_TILE, determine_penalized_stats, get_base_stats, get_bonus,
                                     get_level_by_experience, get_name_tiles, get_stats_for_level,
                                     get_total_name_score, levels_list, name_character_value, reduce_stat)

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

# (strength, agility, max HP, max MP) for levels 1-30
STEVE = (
    (3, 3, 15, 0),  # 1
    (4, 3, 22, 0),  # 2
    (6, 5, 24, 5),  # 3
    (6, 7, 31, 16),  # 4
    (10, 9, 35, 20),  # 5
    (14, 9, 38, 24),  # 6
    (16, 15, 40, 26),  # 7
    (19, 18, 46, 29),  # 8
    (27, 19, 50, 36),  # 9
    (31, 27, 54, 40),  # 10
    (36, 31, 62, 50),  # 11
    (43, 36, 63, 58),  # 12
    (46, 43, 70, 64),  # 13
    (54, 49, 78, 70),  # 14
    (61, 57, 86, 72),  # 15
    (64, 63, 92, 95),  # 16
    (64, 70, 100, 100),  # 17
    (76, 75, 115, 108),  # 18
    (78, 77, 130, 115),  # 19
    (82, 79, 138, 128),  # 20
    (85, 81, 149, 135),  # 21
    (87, 81, 158, 146),  # 22
    (89, 84, 165, 153),  # 23
    (92, 88, 170, 161),  # 24
    (101, 90, 174, 161),  # 25
    (105, 94, 180, 168),  # 26
    (112, 96, 189, 175),  # 27
    (117, 103, 195, 180),  # 28
    (121, 108, 200, 190),  # 29
    (126, 117, 210, 200),  # 30
)
DEEZ = (
    (4, 4, 14, 0),  # 1
    (5, 4, 20, 0),  # 2
    (7, 6, 22, 5),  # 3
    (7, 8, 28, 16),  # 4
    (11, 10, 32, 20),  # 5
    (15, 10, 35, 24),  # 6
    (17, 17, 37, 26),  # 7
    (20, 20, 42, 29),  # 8
    (28, 22, 46, 36),  # 9
    (32, 31, 49, 40),  # 10
    (37, 35, 56, 50),  # 11
    (44, 40, 57, 58),  # 12
    (47, 48, 64, 64),  # 13
    (55, 55, 71, 70),  # 14
    (62, 64, 78, 72),  # 15
    (65, 70, 83, 95),  # 16
    (65, 78, 91, 100),  # 17
    (77, 84, 104, 108),  # 18
    (79, 86, 118, 115),  # 19
    (83, 88, 125, 128),  # 20
    (86, 90, 135, 135),  # 21
    (88, 90, 143, 146),  # 22
    (90, 94, 149, 153),  # 23
    (93, 98, 154, 161),  # 24
    (102, 100, 157, 161),  # 25
    (106, 105, 163, 168),  # 26
    (113, 107, 171, 175),  # 27
    (118, 115, 176, 180),  # 28
    (122, 120, 181, 190),  # 29
    (127, 130, 190, 200),  # 30
)
ERDRICK = (
    (4, 4, 15, 0),  # 1
    (5, 4, 21, 0),  # 2
    (7, 6, 23, 6),  # 3
    (7, 8, 29, 16),  # 4
    (12, 10, 33, 20),  # 5
    (16, 10, 36, 23),  # 6
    (18, 17, 38, 25),  # 7
    (22, 20, 43, 28),  # 8
    (30, 22, 47, 34),  # 9
    (35, 31, 50, 38),  # 10
    (40, 35, 57, 47),  # 11
    (48, 40, 58, 54),  # 12
    (52, 48, 65, 59),  # 13
    (60, 55, 72, 65),  # 14
    (68, 64, 79, 66),  # 15
    (72, 70, 84, 87),  # 16
    (72, 78, 92, 92),  # 17
    (85, 84, 105, 99),  # 18
    (87, 86, 119, 105),  # 19
    (92, 88, 126, 117),  # 20
    (95, 90, 136, 123),  # 21
    (97, 90, 144, 133),  # 22
    (99, 94, 150, 139),  # 23
    (103, 98, 155, 146),  # 24
    (113, 100, 158, 146),  # 25
    (117, 105, 164, 153),  # 26
    (125, 107, 172, 159),  # 27
    (130, 115, 177, 164),  # 28
    (135, 120, 182, 173),  # 29
    (140, 130, 191, 182),  # 30
)
GINA = (
    (4, 6, 15, 0),  # 1
    (5, 6, 22, 0),  # 2
    (7, 8, 24, 7),  # 3
    (7, 10, 31, 17),  # 4
    (12, 12, 35, 21),  # 5
    (16, 12, 38, 24),  # 6
    (18, 18, 40, 26),  # 7
    (22, 21, 46, 29),  # 8
    (30, 22, 50, 35),  # 9
    (35, 30, 54, 39),  # 10
    (40, 34, 62, 48),  # 11
    (48, 39, 63, 55),  # 12
    (52, 46, 70, 60),  # 13
    (60, 52, 78, 66),  # 14
    (68, 60, 86, 67),  # 15
    (72, 66, 92, 88),  # 16
    (72, 73, 100, 93),  # 17
    (85, 78, 115, 100),  # 18
    (87, 80, 130, 106),  # 19
    (92, 82, 138, 118),  # 20
    (95, 84, 149, 124),  # 21
    (97, 84, 158, 134),  # 22
    (99, 87, 165, 140),  # 23
    (103, 91, 170, 147),  # 24
    (113, 93, 174, 147),  # 25
    (117, 97, 180, 154),  # 26
    (125, 99, 189, 160),  # 27
    (130, 106, 195, 165),  # 28
    (135, 111, 200, 174),  # 29
    (140, 120, 210, 183),  # 30
)
EXPECTED = {'Steve': STEVE, 'Deez': DEEZ, 'Erdrick': ERDRICK, 'Gina': GINA}

# BaseStatsTbl (Bank01, $A0CD): strength, agility, max HP, max MP, copied from its .byte rows
BASE_STATS_TBL = (
    (0x04, 0x04, 0x0F, 0x00), (0x05, 0x04, 0x16, 0x00), (0x07, 0x06, 0x18, 0x05), (0x07, 0x08, 0x1F, 0x10),
    (0x0C, 0x0A, 0x23, 0x14), (0x10, 0x0A, 0x26, 0x18), (0x12, 0x11, 0x28, 0x1A), (0x16, 0x14, 0x2E, 0x1D),
    (0x1E, 0x16, 0x32, 0x24), (0x23, 0x1F, 0x36, 0x28), (0x28, 0x23, 0x3E, 0x32), (0x30, 0x28, 0x3F, 0x3A),
    (0x34, 0x30, 0x46, 0x40), (0x3C, 0x37, 0x4E, 0x46), (0x44, 0x40, 0x56, 0x48), (0x48, 0x46, 0x5C, 0x5F),
    (0x48, 0x4E, 0x64, 0x64), (0x55, 0x54, 0x73, 0x6C), (0x57, 0x56, 0x82, 0x73), (0x5C, 0x58, 0x8A, 0x80),
    (0x5F, 0x5A, 0x95, 0x87), (0x61, 0x5A, 0x9E, 0x92), (0x63, 0x5E, 0xA5, 0x99), (0x67, 0x62, 0xAA, 0xA1),
    (0x71, 0x64, 0xAE, 0xA1), (0x75, 0x69, 0xB4, 0xA8), (0x7D, 0x6B, 0xBD, 0xAF), (0x82, 0x73, 0xC3, 0xB4),
    (0x87, 0x78, 0xC8, 0xBE), (0x8C, 0x82, 0xD2, 0xC8),
)
# LevelUpTbl (Bank03, $F35B)
LEVEL_UP_TBL = (0, 7, 23, 47, 110, 220, 450, 800, 1300, 2000, 2900, 4000, 5500, 7500, 10000, 13000, 16000, 19000,
                22000, 26000, 30000, 34000, 38000, 42000, 46000, 50000, 54000, 58000, 62000, 65535)


def as_tuple(stats):
    return stats['strength'], stats['agility'], stats['max_hp'], stats['max_mp']


class TestTables(TestCase):

    def test_base_stats_match_base_stats_tbl(self):
        for level in range(1, 31):
            self.assertEqual(BASE_STATS_TBL[level - 1], as_tuple(get_base_stats(level)), level)

    def test_level_thresholds_match_level_up_tbl(self):
        for level in range(1, 31):
            self.assertEqual(LEVEL_UP_TBL[level - 1], levels_list[level]['total_exp'], level)

    def test_set_exp_is_the_gap_to_the_previous_level(self):
        self.assertEqual(0, levels_list[1]['exp'])
        self.assertEqual(16, levels_list[3]['exp'])
        self.assertEqual(3535, levels_list[30]['exp'])

    def test_get_level_by_experience(self):
        """GetLevelLoop: the highest LevelUpTbl entry the experience reaches."""
        self.assertEqual(1, get_level_by_experience(0))
        self.assertEqual(1, get_level_by_experience(6))
        self.assertEqual(2, get_level_by_experience(7))
        self.assertEqual(9, get_level_by_experience(1999))
        self.assertEqual(29, get_level_by_experience(65534))
        self.assertEqual(30, get_level_by_experience(65535))


class TestNameValues(TestCase):

    def test_nes_name_entry_alphabet(self):
        """WndProcessChar: A-Z are index + TXT_UPR_A, a-z are index - $17, the rest come from SymbolConvTbl.
        The values match the list in the comment above ReduceStat."""
        self.assertEqual(0x24, name_character_value('A'))
        self.assertEqual(0x3D, name_character_value('Z'))
        self.assertEqual(0x0A, name_character_value('a'))
        self.assertEqual(0x23, name_character_value('z'))
        for character, value in (('-', 0x49), ("'", 0x40), ('!', 0x4C), ('?', 0x4B), ('(', 0x4F), (')', 0x4E),
                                 (' ', 0x60), (',', 0x48), ('.', 0x47)):
            self.assertEqual(value, name_character_value(character), character)

    def test_digits_are_their_font_tiles(self):
        self.assertEqual(0, name_character_value('0'))
        self.assertEqual(9, name_character_value('9'))

    def test_accented_letters_count_as_the_plain_letter(self):
        self.assertEqual(name_character_value('E'), name_character_value('É'))
        self.assertEqual(name_character_value('n'), name_character_value('ñ'))
        self.assertEqual(get_stats_for_level('Eva', 20), get_stats_for_level('Éva', 20))

    def test_other_characters_use_the_low_byte_of_the_code_point(self):
        self.assertEqual(0xA9, name_character_value('용'))  # U+C6A9
        self.assertEqual(0xAC, name_character_value('사'))  # U+C0AC
        # 용사 = $A9 + $AC + $60 + $60 = $215 -> $15 = %0101: agility and max MP cut, bonus 1
        self.assertEqual(0x15, get_total_name_score('용사'))
        self.assertEqual((140, 118, 210, 181), as_tuple(get_stats_for_level('용사', 30)))

    def test_only_the_first_four_characters_count(self):
        self.assertEqual(get_name_tiles('Erdrick'), get_name_tiles('Erdr'))
        self.assertEqual(get_stats_for_level('Erdrick', 30), get_stats_for_level('Erdr', 30))

    def test_short_names_are_padded_with_blanks(self):
        """InitNameWindow fills the name buffer with TL_BLANK_TILE2 ($60)."""
        self.assertEqual((0x24, BLANK_TILE, BLANK_TILE, BLANK_TILE), get_name_tiles('A'))
        self.assertEqual(get_name_tiles('A   '), get_name_tiles('A'))
        self.assertEqual(0x80, get_total_name_score(''))

    def test_name_sum_is_eight_bits(self):
        """NameAddLoop adds with ADC, so the carry out of bit 7 is lost."""
        self.assertEqual(0xA7, get_total_name_score('JAKE'))  # $2D+$24+$2E+$28, the disassembly's example
        self.assertEqual(0x66, get_total_name_score('Deez'))  # the disassembly's other example
        self.assertEqual(0x5F, get_total_name_score('Edward'))
        self.assertEqual(0x03, get_total_name_score('Va'))  # $39 + $0A + $60 + $60 = $103


class TestNameStats(TestCase):

    def test_get_bonus(self):
        self.assertEqual(0, get_bonus(0x80))
        self.assertEqual(1, get_bonus(0x66))
        self.assertEqual(2, get_bonus(0x6B))
        self.assertEqual(3, get_bonus(0x5D))
        self.assertEqual(3, get_bonus(0xFF))

    def test_determine_penalized_stats(self):
        self.assertEqual(('agility', 'strength'), determine_penalized_stats(0b00))
        self.assertEqual(('agility', 'max_mp'), determine_penalized_stats(0b01))
        self.assertEqual(('max_hp', 'strength'), determine_penalized_stats(0b10))
        self.assertEqual(('max_hp', 'max_mp'), determine_penalized_stats(0b11))
        self.assertEqual(('agility', 'strength'), determine_penalized_stats(0b100))

    def test_reduce_stat_rounds_down(self):
        self.assertEqual(4, reduce_stat(5, 0))  # 45 / 10
        self.assertEqual(7, reduce_stat(8, 0))  # 72 / 10
        self.assertEqual(192, reduce_stat(210, 3))

    def test_four_growth_patterns_every_level(self):
        for name, expected in EXPECTED.items():
            for level in range(1, 31):
                self.assertEqual(expected[level - 1], as_tuple(get_stats_for_level(name, level)), f'{name} {level}')

    def test_full_rate_stats_are_the_base_table(self):
        """The two stats the name doesn't cut are exactly BaseStatsTbl."""
        for level in range(1, 31):
            strength, agility, max_hp, max_mp = BASE_STATS_TBL[level - 1]
            self.assertEqual((max_hp, max_mp), STEVE[level - 1][2:])
            self.assertEqual((agility, max_mp), DEEZ[level - 1][1::2])
            self.assertEqual((strength, agility), ERDRICK[level - 1][:2])
            self.assertEqual((strength, max_hp), GINA[level - 1][::2])

    def test_no_mp_means_no_cut_and_no_bonus(self):
        """LF0AF: with max MP 0 (levels 1 and 2) the MP cut and its bonus are skipped."""
        self.assertEqual(0, get_stats_for_level('Gina', 1)['max_mp'])
        self.assertEqual(0, get_stats_for_level('Gina', 2)['max_mp'])
        self.assertEqual(5 * 9 // 10 + 3, get_stats_for_level('Gina', 3)['max_mp'])

    def test_all_sixteen_groups_at_level_30(self):
        """One name for each value of the low four bits of the sum."""
        for name, expected in (
                ('Steve', (126, 117, 210, 200)),  # $80
                ('Eva', (140, 117, 210, 180)),  # $B1
                ('Im', (126, 130, 189, 200)),  # $02
                ('Va', (140, 130, 189, 180)),  # $03
                ('Eddie', (127, 118, 210, 200)),  # $54
                ('Ed', (140, 118, 210, 181)),  # $F5
                ('Walter', (127, 130, 190, 200)),  # $76
                ('Uno', (140, 130, 190, 181)),  # $C7
                ('gooo', (128, 119, 210, 200)),  # $58
                ('Sejin', (140, 119, 210, 182)),  # $69
                ('Stephen', (128, 130, 191, 200)),  # $7A
                ('James', (140, 130, 191, 182)),  # $5B
                ('Gao', (129, 120, 210, 200)),  # $AC
                ('Gina', (140, 120, 210, 183)),  # $5D
                ('Wall', (129, 130, 192, 200)),  # $6E
                ('Edward', (140, 130, 192, 183)),  # $5F
        ):
            self.assertEqual(expected, as_tuple(get_stats_for_level(name, 30)), name)

    def test_level_up_stat_changes(self):
        """ChkStrengthUp-ChkMPUp report the new stats minus the old ones."""
        def gains(name, old_level, new_level):
            old, new = as_tuple(get_stats_for_level(name, old_level)), as_tuple(get_stats_for_level(name, new_level))
            return tuple(after - before for before, after in zip(old, new))
        self.assertEqual((1, 0, 7, 0), gains('Steve', 1, 2))  # strength 4 * 9 // 10 = 3 -> 5 * 9 // 10 = 4
        self.assertEqual((2, 2, 2, 7), gains('Gina', 2, 3))  # MP 0 -> 5 * 9 // 10 + 3 = 7
        self.assertEqual((0, 2, 6, 11), gains('Deez', 3, 4))  # HP 24 * 9 // 10 + 1 = 22 -> 31 * 9 // 10 + 1 = 28
        self.assertEqual((9, 2, 7, 7), gains('Erdrick', 4, 6))  # two levels at once

    def test_base_table_is_never_changed(self):
        before = {level: dict(row) for level, row in levels_list.items()}
        for name in EXPECTED:
            for level in range(1, 31):
                get_stats_for_level(name, level)
        self.assertEqual(before, player_stats.levels_list)
