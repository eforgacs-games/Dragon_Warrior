"""Table-driven check of every enemy against the NES enemy data (nmikstas dragon-warrior-disassembly).

EN_STAT_TBL is the first 8 bytes of each 16-byte row of Bank01 EnStatTbl ($9E4B-$A0CA), in enemy-number order
($00 Slime to $27 Dragonlord's true form). The other 8 bytes of each row are unused. The columns are:

    Att  Def  HP  Spel  Agi  Mdef  Exp  Gld

How the NES reads them (Bank03):
- HP: ModEnHitPoints starts the fight on HP - (HP * rand(0-255) / 256) / 4, except for the Dragonlord's true
  form, which always starts on full HP.
- Spel (EnSpell), read by DoEnemyAttack: bits 7-6 pick the upper spell (SLEEP, STOPSPELL, HEAL, HEALMORE) and
  bits 5-4 its chance in quarters; bits 3-2 pick the lower spell (HURT, HURTMORE, fire 1, fire 2) and bits
  1-0 its chance in quarters. The upper spell is tried first. HEAL and HEALMORE are only cast at or below
  1/4 of base HP.
- Agi (EnBaseAgi): upper nibble = SLEEP resistance, lower nibble = STOPSPELL resistance (ChkSpellFail, n/16).
- Mdef (EnBaseMDef): upper nibble = HURT/HURTMORE resistance (n/16); lower nibble = dodge chance (n/64).
- Exp is given as-is; Gld is multiplied by (192 + rand(0-63)) / 256 (CalcPlyrGold).
"""
import unittest
from unittest.mock import patch

from src.battle import Battle, randomize_enemy_gold, randomize_enemy_hp
from src.enemy import enemy_groups
from src.enemy_lookup import enemy_repel_lookup, enemy_string_lookup
from src.enemy_spells import enemy_spell_lookup
from src.spells import Spell

#   name               Att   Def   HP    Spel  Agi   Mdef  Exp   Gld      EnStatTbl label
EN_STAT_TBL = [
    ('Slime',          0x05, 0x03, 0x03, 0x00, 0x0F, 0x01, 0x01, 0x02),  # L9E4B
    ('Red Slime',      0x07, 0x03, 0x04, 0x00, 0x0F, 0x01, 0x01, 0x03),  # L9E5B
    ('Drakee',         0x09, 0x06, 0x06, 0x00, 0x0F, 0x01, 0x02, 0x03),  # L9E6B
    ('Ghost',          0x0B, 0x08, 0x07, 0x00, 0x0F, 0x04, 0x03, 0x05),  # L9E7B
    ('Magician',       0x0B, 0x0C, 0x0D, 0x02, 0x00, 0x01, 0x04, 0x0C),  # L9E8B
    ('Magidrakee',     0x0E, 0x0E, 0x0F, 0x02, 0x00, 0x01, 0x05, 0x0C),  # L9E9B
    ('Scorpion',       0x12, 0x10, 0x14, 0x00, 0x0F, 0x01, 0x06, 0x10),  # L9EAB
    ('Druin',          0x14, 0x12, 0x16, 0x00, 0x0F, 0x02, 0x07, 0x10),  # L9EBB
    ('Poltergeist',    0x12, 0x14, 0x17, 0x03, 0x00, 0x06, 0x08, 0x12),  # L9ECB
    ('Droll',          0x18, 0x18, 0x19, 0x00, 0x0E, 0x02, 0x0A, 0x19),  # L9EDB
    ('Drakeema',       0x16, 0x1A, 0x14, 0x92, 0x20, 0x06, 0x0B, 0x14),  # L9EEB
    ('Skeleton',       0x1C, 0x16, 0x1E, 0x00, 0x0F, 0x04, 0x0B, 0x1E),  # L9EFB
    ('Warlock',        0x1C, 0x16, 0x1E, 0x12, 0x31, 0x02, 0x0D, 0x23),  # L9F0B
    ('Metal Scorpion', 0x24, 0x2A, 0x16, 0x00, 0x0F, 0x02, 0x0E, 0x28),  # L9F1B
    ('Wolf',           0x28, 0x1E, 0x22, 0x00, 0x1F, 0x02, 0x10, 0x32),  # L9F2B
    ('Wraith',         0x2C, 0x22, 0x24, 0x90, 0x70, 0x04, 0x11, 0x3C),  # L9F3B
    ('Metal Slime',    0x0A, 0xFF, 0x04, 0x03, 0xFF, 0xF1, 0x73, 0x06),  # L9F4B
    ('Specter',        0x28, 0x26, 0x24, 0x13, 0x31, 0x04, 0x12, 0x46),  # L9F5B
    ('Wolflord',       0x32, 0x24, 0x26, 0x60, 0x47, 0x02, 0x14, 0x50),  # L9F6B
    ('Druinlord',      0x2F, 0x28, 0x23, 0xB1, 0xF0, 0x04, 0x14, 0x55),  # L9F7B
    ('Drollmagi',      0x34, 0x32, 0x26, 0x60, 0x22, 0x01, 0x16, 0x5A),  # L9F8B
    ('Wyvern',         0x38, 0x30, 0x2A, 0x00, 0x4F, 0x02, 0x18, 0x64),  # L9F9B
    ('Rogue Scorpion', 0x3C, 0x5A, 0x23, 0x00, 0x7F, 0x02, 0x1A, 0x6E),  # L9FAB
    ('Wraith Knight',  0x44, 0x38, 0x2E, 0xB0, 0x50, 0x34, 0x1C, 0x78),  # L9FBB
    ('Golem',          0x78, 0x3C, 0x46, 0x00, 0xFF, 0xF0, 0x05, 0x0A),  # L9FCB
    ('Goldman',        0x30, 0x28, 0x32, 0x00, 0xDF, 0x01, 0x06, 0xC8),  # L9FDB
    ('Knight',         0x4C, 0x4E, 0x37, 0x60, 0x67, 0x01, 0x21, 0x82),  # L9FEB
    ('Magiwyvern',     0x4E, 0x44, 0x3A, 0x20, 0x20, 0x02, 0x22, 0x8C),  # L9FFB
    ('Demon Knight',   0x4F, 0x40, 0x32, 0x00, 0xFF, 0xFF, 0x25, 0x96),  # LA00B
    ('Werewolf',       0x56, 0x46, 0x3C, 0x00, 0x7F, 0x07, 0x28, 0x9B),  # LA01B
    ('Green Dragon',   0x58, 0x4A, 0x41, 0x09, 0x7F, 0x22, 0x2D, 0xA0),  # LA02B
    ('Starwyvern',     0x56, 0x50, 0x41, 0xF9, 0x80, 0x12, 0x2B, 0xA0),  # LA03B
    ('Wizard',         0x50, 0x46, 0x41, 0x06, 0xF7, 0xF2, 0x32, 0xA5),  # LA04B
    ('Axe Knight',     0x5E, 0x52, 0x46, 0x10, 0xF3, 0x11, 0x36, 0xA5),  # LA05B
    ('Blue Dragon',    0x62, 0x54, 0x46, 0x09, 0xFF, 0x72, 0x3C, 0x96),  # LA06B
    ('Stoneman',       0x64, 0x28, 0xA0, 0x00, 0x2F, 0x71, 0x41, 0x8C),  # LA07B
    ('Armored Knight', 0x69, 0x56, 0x5A, 0xF5, 0xF7, 0x12, 0x46, 0x8C),  # LA08B
    ('Red Dragon',     0x78, 0x5A, 0x64, 0x19, 0xF7, 0xF2, 0x64, 0x8C),  # LA09B
    ('Dragonlord',     0x5A, 0x4B, 0x64, 0x57, 0xFF, 0xF0, 0x00, 0x00),  # LA0AB
    ('Dragonlord 2',   0x8C, 0xC8, 0x82, 0x0E, 0xFF, 0xF0, 0x00, 0x00),  # LA0BB
]

# Bank03 RepelTbl ($F4FA), indexed by enemy number.
REPEL_TBL = [
    0x05, 0x07, 0x09, 0x0B, 0x0B, 0x0E, 0x12, 0x14, 0x12, 0x18, 0x16, 0x1C, 0x1C, 0x24, 0x28, 0x2C,
    0x0A, 0x28, 0x32, 0x2F, 0x34, 0x38, 0x3C, 0x44, 0x78, 0x30, 0x4C, 0x4E, 0x4F, 0x56, 0x58, 0x56,
    0x50, 0x5E, 0x62, 0x64, 0x69, 0x78, 0x5A, 0x8C,
]

# DoEnemyAttack: EnSpell bits 7-6 and 3-2.
UPPER_SPELLS = (Spell.SLEEP, Spell.STOPSPELL, Spell.HEAL, Spell.HEALMORE)
LOWER_SPELLS = (Spell.HURT, Spell.HURTMORE, Spell.FIREBREATH, Spell.FIREBREATH2)

# TryRun: enemy numbers at or above EN_DROLLMAGI ($14), EN_GDRAGON ($1E) and EN_STONEMAN ($23).
EN_DROLLMAGI, EN_GDRAGON, EN_STONEMAN = 0x14, 0x1E, 0x23


def decode_spell_byte(spell_byte):
    """The (chance %, spell) pairs DoEnemyAttack tries, in order, for an EnSpell byte."""
    upper_chance = (spell_byte >> 4) & 0x03
    lower_chance = spell_byte & 0x03
    attempts = []
    if upper_chance:
        attempts.append((upper_chance * 25, UPPER_SPELLS[spell_byte >> 6]))
    if lower_chance:
        attempts.append((lower_chance * 25, LOWER_SPELLS[(spell_byte >> 2) & 0x03]))
    return attempts


def spell_attempts(enemy):
    return [(entry[0], entry[1]) for entry in enemy.pattern if isinstance(entry, tuple)]


class TestEnemyStatTable(unittest.TestCase):

    def test_table_covers_every_enemy(self):
        self.assertEqual(len(EN_STAT_TBL), 40)
        self.assertEqual({row[0] for row in EN_STAT_TBL}, set(enemy_string_lookup))

    def test_stats_match_en_stat_tbl(self):
        for name, att, defense, hp, _spel, agi, mdef, exp, gold in EN_STAT_TBL:
            enemy = enemy_string_lookup[name]()
            with self.subTest(enemy=name):
                self.assertEqual(enemy.name, name)
                self.assertEqual(enemy.max_hp, hp)
                self.assertEqual(enemy.hp, hp)
                self.assertEqual(enemy.attack, att)
                self.assertEqual(enemy.defense, defense)
                self.assertEqual(enemy.speed, agi)
                self.assertEqual(enemy.xp, exp)
                self.assertEqual(enemy.gold, gold)

    def test_resistances_match_agi_and_mdef_nibbles(self):
        for name, _att, _def, _hp, _spel, agi, mdef, _exp, _gold in EN_STAT_TBL:
            enemy = enemy_string_lookup[name]()
            with self.subTest(enemy=name):
                self.assertEqual(enemy.sleep_resist, (agi >> 4) / 16)
                self.assertEqual(enemy.stopspell_resist, (agi & 0x0F) / 16)
                self.assertEqual(enemy.hurt_resist, (mdef >> 4) / 16)
                self.assertEqual(enemy.dodge, (mdef & 0x0F) / 64)

    def test_spells_match_spell_byte(self):
        for name, _att, _def, _hp, spel, *_ in EN_STAT_TBL:
            enemy = enemy_string_lookup[name]()
            expected = decode_spell_byte(spel)
            with self.subTest(enemy=name, spell_byte=f'${spel:02X}'):
                self.assertEqual(enemy.spells, tuple(spell for _, spell in expected) or None)

    def test_pattern_matches_spell_byte(self):
        """At 1 HP every HEAL/HEALMORE condition is met, so the whole pattern is visible."""
        for name, _att, _def, _hp, spel, *_ in EN_STAT_TBL:
            enemy = enemy_string_lookup[name]()
            enemy.hp = 1
            enemy.refresh_pattern()
            expected = decode_spell_byte(spel)
            with self.subTest(enemy=name, spell_byte=f'${spel:02X}'):
                self.assertEqual(spell_attempts(enemy), expected)
                if expected:
                    self.assertEqual(enemy.pattern[-1], Spell.ATTACK)
                    self.assertTrue(all(entry[2] for entry in enemy.pattern if isinstance(entry, tuple)))
                else:
                    self.assertEqual(enemy.pattern, [])

    def test_heal_only_at_or_below_quarter_base_hp(self):
        """DoEnemyAttack: HEAL/HEALMORE need EnBaseHP / 4 >= EnCurntHP; other spells have no HP condition."""
        for name, _att, _def, hp, *_ in EN_STAT_TBL:
            enemy = enemy_string_lookup[name]()
            for current_hp, can_heal in ((hp // 4, True), (hp // 4 + 1, False)):
                enemy.hp = current_hp
                enemy.refresh_pattern()
                for chance, spell, condition in (entry for entry in enemy.pattern if isinstance(entry, tuple)):
                    with self.subTest(enemy=name, spell=spell, hp=current_hp):
                        self.assertEqual(condition, can_heal if spell in (Spell.HEAL, Spell.HEALMORE) else True)

    def test_hp_randomization_matches_mod_en_hit_points(self):
        for name, _att, _def, hp, *_ in EN_STAT_TBL:
            enemy = enemy_string_lookup[name]()
            for roll in range(256):
                # ModEnHitPoints: upper byte of HP * rand, divided by 4, subtracted from HP
                expected = hp if name == 'Dragonlord 2' else hp - (((hp * roll) >> 8) >> 2)
                with patch('src.battle.random.randint', return_value=roll):
                    self.assertEqual(randomize_enemy_hp(enemy), expected, (name, roll))

    def test_gold_randomization_matches_calc_plyr_gold(self):
        for name, *_, gold in EN_STAT_TBL:
            for roll in range(64):
                # CalcPlyrGold: upper byte of EnBaseGld * (rand & $3F + $C0)
                expected = (gold * (roll + 0xC0)) >> 8
                with patch('src.battle.random.randint', return_value=roll):
                    self.assertEqual(randomize_enemy_gold(gold), expected, (name, roll))

    def test_repel_values_match_repel_tbl(self):
        for number, (name, *_) in enumerate(EN_STAT_TBL):
            with self.subTest(enemy=name):
                self.assertEqual(enemy_repel_lookup[name], REPEL_TBL[number])

    def test_run_groups_match_try_run(self):
        for number, (name, *_) in enumerate(EN_STAT_TBL):
            if number >= EN_STONEMAN:
                group = 4
            elif number >= EN_GDRAGON:
                group = 3
            elif number >= EN_DROLLMAGI:
                group = 2
            else:
                group = 1
            with self.subTest(enemy=name):
                self.assertIn(name, enemy_groups[group])
                self.assertEqual(Battle.get_group_factor(name), group)

    def test_enemy_spell_ranges(self):
        """EnCastHurt, EnCastHurtmore, EnCastHeal, EnCastHealmore, EnCastFire1 and EnCastFire2."""
        self.assertEqual(enemy_spell_lookup[Spell.HURT], (3, 3 + 7))          # (rand & 7) + 3
        self.assertEqual(enemy_spell_lookup[Spell.HURTMORE], (30, 30 + 15))   # (rand & $0F) + $1E
        self.assertEqual(enemy_spell_lookup[Spell.HEAL], (20, 20 + 7))        # (rand & 7) + $14
        self.assertEqual(enemy_spell_lookup[Spell.HEALMORE], (85, 85 + 15))   # (rand & $0F) + $55
        self.assertEqual(enemy_spell_lookup[Spell.FIREBREATH], (16, 16 + 7))  # (rand & 7) | $10
        self.assertEqual(enemy_spell_lookup[Spell.FIREBREATH2], (65, 65 + 7))  # (rand & 7) + $41


if __name__ == '__main__':
    unittest.main()
