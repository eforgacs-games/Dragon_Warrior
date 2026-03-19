import unittest

from src.enemy_spells import enemy_spell_lookup


class TestEnemySpellLookup(unittest.TestCase):

    def test_all_expected_spells_present(self):
        expected = {"HURT", "HURTMORE", "SLEEP", "STOPSPELL", "HEAL", "HEALMORE", "FIREBREATH", "FIREBREATH2"}
        self.assertEqual(set(enemy_spell_lookup.keys()), expected)

    def test_hurt_range(self):
        min_dmg, max_dmg = enemy_spell_lookup["HURT"]
        self.assertEqual(min_dmg, 3)
        self.assertEqual(max_dmg, 10)

    def test_hurtmore_range(self):
        min_dmg, max_dmg = enemy_spell_lookup["HURTMORE"]
        self.assertEqual(min_dmg, 30)
        self.assertEqual(max_dmg, 45)

    def test_sleep_is_zero_damage(self):
        min_dmg, max_dmg = enemy_spell_lookup["SLEEP"]
        self.assertEqual(min_dmg, 0)
        self.assertEqual(max_dmg, 0)

    def test_stopspell_is_zero_damage(self):
        min_dmg, max_dmg = enemy_spell_lookup["STOPSPELL"]
        self.assertEqual(min_dmg, 0)
        self.assertEqual(max_dmg, 0)

    def test_heal_range(self):
        min_hp, max_hp = enemy_spell_lookup["HEAL"]
        self.assertEqual(min_hp, 20)
        self.assertEqual(max_hp, 27)

    def test_healmore_range(self):
        min_hp, max_hp = enemy_spell_lookup["HEALMORE"]
        self.assertEqual(min_hp, 85)
        self.assertEqual(max_hp, 100)

    def test_firebreath_range(self):
        min_dmg, max_dmg = enemy_spell_lookup["FIREBREATH"]
        self.assertEqual(min_dmg, 16)
        self.assertEqual(max_dmg, 23)

    def test_firebreath2_range(self):
        min_dmg, max_dmg = enemy_spell_lookup["FIREBREATH2"]
        self.assertEqual(min_dmg, 65)
        self.assertEqual(max_dmg, 72)

    def test_all_ranges_have_valid_min_max(self):
        for spell, (min_dmg, max_dmg) in enemy_spell_lookup.items():
            with self.subTest(spell=spell):
                self.assertGreaterEqual(min_dmg, 0, f"{spell} min should be non-negative")
                self.assertGreaterEqual(max_dmg, min_dmg, f"{spell} max should be >= min")

    def test_healmore_heals_more_than_heal(self):
        heal_min, heal_max = enemy_spell_lookup["HEAL"]
        healmore_min, healmore_max = enemy_spell_lookup["HEALMORE"]
        self.assertGreater(healmore_min, heal_max)

    def test_hurtmore_deals_more_than_hurt(self):
        hurt_min, hurt_max = enemy_spell_lookup["HURT"]
        hurtmore_min, hurtmore_max = enemy_spell_lookup["HURTMORE"]
        self.assertGreater(hurtmore_min, hurt_max)

    def test_firebreath2_deals_more_than_firebreath(self):
        fb_min, fb_max = enemy_spell_lookup["FIREBREATH"]
        fb2_min, fb2_max = enemy_spell_lookup["FIREBREATH2"]
        self.assertGreater(fb2_min, fb_max)

    def test_lookup_returns_tuples(self):
        for spell, value in enemy_spell_lookup.items():
            with self.subTest(spell=spell):
                self.assertIsInstance(value, tuple)
                self.assertEqual(len(value), 2)


if __name__ == '__main__':
    unittest.main()
