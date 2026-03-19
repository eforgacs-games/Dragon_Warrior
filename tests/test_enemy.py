import unittest

from src.enemy import (
    Enemy, Slime, RedSlime, MetalSlime, Drakee, Magidrakee, Drakeema,
    Ghost, Poltergeist, Specter, Magician, Warlock, Wizard,
    Scorpion, MetalScorpion, RogueScorpion, Druin, Druinlord,
    Droll, Drollmagi, Skeleton, Wraith, WraithKnight, DemonKnight,
    Wolf, Wolflord, Werewolf, Goldman, Golem, Stoneman,
    Wyvern, Magiwyvern, Starwyvern, Knight, AxeKnight, ArmoredKnight,
    GreenDragon, BlueDragon, RedDragon, Dragonlord, Dragonlord2,
    enemy_groups
)


class TestEnemyBase(unittest.TestCase):

    def setUp(self):
        self.enemy = Enemy(
            hp=10, attack=5, defense=3, speed=15, xp=2, gold=3,
            spells=None, sleep_resist=0.0, stopspell_resist=0.5,
            hurt_resist=0.0, dodge=1 / 64
        )

    def test_hp_initialized(self):
        self.assertEqual(self.enemy.hp, 10)
        self.assertEqual(self.enemy.max_hp, 10)

    def test_attack_initialized(self):
        self.assertEqual(self.enemy.attack, 5)

    def test_defense_initialized(self):
        self.assertEqual(self.enemy.defense, 3)

    def test_speed_initialized(self):
        self.assertEqual(self.enemy.speed, 15)

    def test_xp_initialized(self):
        self.assertEqual(self.enemy.xp, 2)

    def test_gold_initialized(self):
        self.assertEqual(self.enemy.gold, 3)

    def test_spells_none(self):
        self.assertIsNone(self.enemy.spells)

    def test_name_defaults_empty(self):
        self.assertEqual(self.enemy.name, '')

    def test_not_asleep_initially(self):
        self.assertFalse(self.enemy.is_asleep)

    def test_pattern_defaults_empty(self):
        self.assertEqual(self.enemy.pattern, [])

    def test_get_current_hp(self):
        self.assertEqual(self.enemy.get_current_hp(), 10)

    def test_get_current_hp_after_change(self):
        self.enemy.hp = 7
        self.assertEqual(self.enemy.get_current_hp(), 7)

    def test_refresh_pattern(self):
        self.enemy.pattern = ['ATTACK', 'ATTACK']
        self.enemy.refresh_pattern()
        self.assertEqual(self.enemy.pattern, [])

    def test_resist_values_stored(self):
        self.assertAlmostEqual(self.enemy.sleep_resist, 0.0)
        self.assertAlmostEqual(self.enemy.stopspell_resist, 0.5)
        self.assertAlmostEqual(self.enemy.hurt_resist, 0.0)

    def test_dodge_stored(self):
        self.assertAlmostEqual(self.enemy.dodge, 1 / 64)


class TestSlime(unittest.TestCase):

    def setUp(self):
        self.enemy = Slime()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Slime')

    def test_hp(self):
        self.assertEqual(self.enemy.hp, 3)

    def test_attack(self):
        self.assertEqual(self.enemy.attack, 5)

    def test_defense(self):
        self.assertEqual(self.enemy.defense, 3)

    def test_xp(self):
        self.assertEqual(self.enemy.xp, 1)

    def test_gold(self):
        self.assertEqual(self.enemy.gold, 1)

    def test_no_spells(self):
        self.assertIsNone(self.enemy.spells)

    def test_pattern_empty(self):
        self.assertEqual(self.enemy.pattern, [])


class TestRedSlime(unittest.TestCase):

    def setUp(self):
        self.enemy = RedSlime()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Red Slime')

    def test_stronger_than_slime(self):
        slime = Slime()
        self.assertGreater(self.enemy.attack, slime.attack)

    def test_more_xp_than_slime(self):
        slime = Slime()
        self.assertGreaterEqual(self.enemy.xp, slime.xp)


class TestMetalSlime(unittest.TestCase):

    def setUp(self):
        self.enemy = MetalSlime()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Metal Slime')

    def test_very_high_defense(self):
        self.assertEqual(self.enemy.defense, 225)

    def test_very_high_speed(self):
        self.assertEqual(self.enemy.speed, 255)

    def test_high_xp(self):
        self.assertEqual(self.enemy.xp, 115)

    def test_has_hurt_spell(self):
        self.assertIn("HURT", self.enemy.spells)

    def test_pattern_includes_hurt(self):
        self.assertIn("ATTACK", self.enemy.pattern)
        pattern_spells = [p[1] for p in self.enemy.pattern if isinstance(p, tuple)]
        self.assertIn("HURT", pattern_spells)


class TestMagidrakee(unittest.TestCase):

    def setUp(self):
        self.enemy = Magidrakee()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Magidrakee')

    def test_has_hurt_spell(self):
        self.assertIn("HURT", self.enemy.spells)

    def test_pattern_has_hurt(self):
        pattern_spells = [p[1] for p in self.enemy.pattern if isinstance(p, tuple)]
        self.assertIn("HURT", pattern_spells)


class TestDrakeema(unittest.TestCase):

    def setUp(self):
        self.enemy = Drakeema()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Drakeema')

    def test_has_heal_and_hurt(self):
        self.assertIn("HEAL", self.enemy.spells)
        self.assertIn("HURT", self.enemy.spells)

    def test_pattern_has_heal_and_hurt(self):
        pattern_spells = [p[1] for p in self.enemy.pattern if isinstance(p, tuple)]
        self.assertIn("HEAL", pattern_spells)
        self.assertIn("HURT", pattern_spells)


class TestSpecter(unittest.TestCase):

    def setUp(self):
        self.enemy = Specter()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Specter')

    def test_has_sleep_and_hurt(self):
        self.assertIn("HURT", self.enemy.spells)
        self.assertIn("SLEEP", self.enemy.spells)

    def test_pattern_has_sleep_and_hurt(self):
        pattern_spells = [p[1] for p in self.enemy.pattern if isinstance(p, tuple)]
        self.assertIn("SLEEP", pattern_spells)
        self.assertIn("HURT", pattern_spells)


class TestMagician(unittest.TestCase):

    def setUp(self):
        self.enemy = Magician()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Magician')

    def test_has_hurt_spell(self):
        self.assertIn("HURT", self.enemy.spells)

    def test_pattern_attacks(self):
        self.assertIn("ATTACK", self.enemy.pattern)


class TestWarlock(unittest.TestCase):

    def setUp(self):
        self.enemy = Warlock()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Warlock')

    def test_has_hurt_and_sleep(self):
        self.assertIn("HURT", self.enemy.spells)
        self.assertIn("SLEEP", self.enemy.spells)


class TestWizard(unittest.TestCase):

    def setUp(self):
        self.enemy = Wizard()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Wizard')

    def test_has_hurtmore(self):
        self.assertIn("HURTMORE", self.enemy.spells)

    def test_high_stats(self):
        self.assertEqual(self.enemy.attack, 80)
        self.assertEqual(self.enemy.defense, 70)


class TestDruinlord(unittest.TestCase):

    def setUp(self):
        self.enemy = Druinlord()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Druinlord')

    def test_pattern_has_heal(self):
        pattern_spells = [p[1] for p in self.enemy.pattern if isinstance(p, tuple)]
        self.assertIn("HEAL", pattern_spells)

    def test_heal_conditional_on_low_hp(self):
        # Druinlord should heal when HP < max/4
        self.enemy.hp = 1  # Very low HP
        self.enemy.refresh_pattern()
        heal_entry = [p for p in self.enemy.pattern if isinstance(p, tuple) and p[1] == 'HEAL']
        self.assertTrue(len(heal_entry) > 0)


class TestDrollmagi(unittest.TestCase):

    def setUp(self):
        self.enemy = Drollmagi()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Drollmagi')

    def test_has_stopspell(self):
        self.assertIn("STOPSPELL", self.enemy.spells)

    def test_pattern_has_stopspell(self):
        pattern_spells = [p[1] for p in self.enemy.pattern if isinstance(p, tuple)]
        self.assertIn("STOPSPELL", pattern_spells)


class TestWraith(unittest.TestCase):

    def setUp(self):
        self.enemy = Wraith()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Wraith')

    def test_has_heal(self):
        self.assertIn("HEAL", self.enemy.spells)


class TestWraithKnight(unittest.TestCase):

    def setUp(self):
        self.enemy = WraithKnight()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Wraith Knight')

    def test_pattern_has_heal(self):
        pattern_spells = [p[1] for p in self.enemy.pattern if isinstance(p, tuple)]
        self.assertIn("HEAL", pattern_spells)


class TestDemonKnight(unittest.TestCase):

    def setUp(self):
        self.enemy = DemonKnight()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Demon Knight')

    def test_very_high_resistances(self):
        self.assertAlmostEqual(self.enemy.sleep_resist, 15 / 16)
        self.assertAlmostEqual(self.enemy.stopspell_resist, 15 / 16)
        self.assertAlmostEqual(self.enemy.hurt_resist, 15 / 16)


class TestGolem(unittest.TestCase):

    def setUp(self):
        self.enemy = Golem()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Golem')

    def test_no_dodge(self):
        self.assertAlmostEqual(self.enemy.dodge, 0.0)

    def test_no_spells(self):
        self.assertIsNone(self.enemy.spells)


class TestGoldman(unittest.TestCase):

    def setUp(self):
        self.enemy = Goldman()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Goldman')

    def test_high_gold_reward(self):
        self.assertEqual(self.enemy.gold, 200)

    def test_low_xp(self):
        self.assertEqual(self.enemy.xp, 6)


class TestStoneman(unittest.TestCase):

    def setUp(self):
        self.enemy = Stoneman()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Stoneman')

    def test_very_high_hp(self):
        self.assertEqual(self.enemy.hp, 160)


class TestWyvern(unittest.TestCase):

    def setUp(self):
        self.enemy = Wyvern()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Wyvern')

    def test_no_spells(self):
        self.assertIsNone(self.enemy.spells)


class TestMagiwyvern(unittest.TestCase):

    def setUp(self):
        self.enemy = Magiwyvern()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Magiwyvern')

    def test_has_sleep(self):
        self.assertIn("SLEEP", self.enemy.spells)

    def test_pattern_has_sleep(self):
        pattern_spells = [p[1] for p in self.enemy.pattern if isinstance(p, tuple)]
        self.assertIn("SLEEP", pattern_spells)


class TestStarwyvern(unittest.TestCase):

    def setUp(self):
        self.enemy = Starwyvern()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Starwyvern')

    def test_has_healmore_and_firebreath(self):
        self.assertIn("HEALMORE", self.enemy.spells)
        self.assertIn("FIREBREATH", self.enemy.spells)

    def test_pattern_has_firebreath(self):
        self.assertIn("FIREBREATH", self.enemy.pattern)


class TestKnight(unittest.TestCase):

    def setUp(self):
        self.enemy = Knight()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Knight')

    def test_has_stopspell(self):
        self.assertIn("STOPSPELL", self.enemy.spells)


class TestAxeKnight(unittest.TestCase):

    def setUp(self):
        self.enemy = AxeKnight()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Axe Knight')

    def test_has_sleep_and_stopspell(self):
        self.assertIn("SLEEP", self.enemy.spells)
        self.assertIn("STOPSPELL", self.enemy.spells)


class TestArmoredKnight(unittest.TestCase):

    def setUp(self):
        self.enemy = ArmoredKnight()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Armored Knight')

    def test_has_healmore_and_hurtmore(self):
        self.assertIn("HEALMORE", self.enemy.spells)
        self.assertIn("HURTMORE", self.enemy.spells)


class TestGreenDragon(unittest.TestCase):

    def setUp(self):
        self.enemy = GreenDragon()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Green Dragon')

    def test_has_firebreath(self):
        self.assertIn("FIREBREATH", self.enemy.spells)

    def test_pattern_has_firebreath(self):
        pattern_spells = [p[1] for p in self.enemy.pattern if isinstance(p, tuple)]
        self.assertIn("FIREBREATH", pattern_spells)


class TestBlueDragon(unittest.TestCase):

    def setUp(self):
        self.enemy = BlueDragon()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Blue Dragon')

    def test_max_speed(self):
        self.assertEqual(self.enemy.speed, 255)


class TestRedDragon(unittest.TestCase):

    def setUp(self):
        self.enemy = RedDragon()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Red Dragon')

    def test_has_sleep_and_firebreath(self):
        self.assertIn("SLEEP", self.enemy.spells)
        self.assertIn("FIREBREATH", self.enemy.spells)

    def test_high_hp(self):
        self.assertEqual(self.enemy.hp, 100)


class TestDragonlord(unittest.TestCase):

    def setUp(self):
        self.enemy = Dragonlord()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Dragonlord')

    def test_no_xp_or_gold(self):
        self.assertEqual(self.enemy.xp, 0)
        self.assertEqual(self.enemy.gold, 0)

    def test_has_stopspell_and_hurtmore(self):
        self.assertIn("STOPSPELL", self.enemy.spells)
        self.assertIn("HURTMORE", self.enemy.spells)

    def test_pattern_has_stopspell_and_hurtmore(self):
        pattern_spells = [p[1] for p in self.enemy.pattern if isinstance(p, tuple)]
        self.assertIn("STOPSPELL", pattern_spells)
        self.assertIn("HURTMORE", pattern_spells)


class TestDragonlord2(unittest.TestCase):

    def setUp(self):
        self.enemy = Dragonlord2()

    def test_name(self):
        self.assertEqual(self.enemy.name, 'Dragonlord 2')

    def test_very_high_defense(self):
        self.assertEqual(self.enemy.defense, 200)

    def test_has_firebreath2(self):
        self.assertIn("FIREBREATH2", self.enemy.spells)

    def test_no_xp_or_gold(self):
        self.assertEqual(self.enemy.xp, 0)
        self.assertEqual(self.enemy.gold, 0)

    def test_pattern_has_firebreath2(self):
        pattern_spells = [p[1] for p in self.enemy.pattern if isinstance(p, tuple)]
        self.assertIn("FIREBREATH2", pattern_spells)


class TestEnemyGroups(unittest.TestCase):

    def test_all_four_groups_exist(self):
        self.assertIn(1, enemy_groups)
        self.assertIn(2, enemy_groups)
        self.assertIn(3, enemy_groups)
        self.assertIn(4, enemy_groups)

    def test_group_1_contains_slime(self):
        self.assertIn('Slime', enemy_groups[1])

    def test_group_1_contains_metal_slime(self):
        self.assertIn('MetalSlime', enemy_groups[1])

    def test_group_4_contains_dragonlord(self):
        self.assertIn('Dragonlord', enemy_groups[4])

    def test_group_4_contains_dragonlord2(self):
        self.assertIn('Dragonlord2', enemy_groups[4])

    def test_groups_non_empty(self):
        for group_id, group in enemy_groups.items():
            with self.subTest(group_id=group_id):
                self.assertTrue(len(group) > 0)


class TestEnemyStatsConsistency(unittest.TestCase):
    """Test that all enemies have valid stat ranges."""

    ALL_ENEMIES = [
        Slime, RedSlime, MetalSlime, Drakee, Magidrakee, Drakeema,
        Ghost, Poltergeist, Specter, Magician, Warlock, Wizard,
        Scorpion, MetalScorpion, RogueScorpion, Druin, Druinlord,
        Droll, Drollmagi, Skeleton, Wraith, WraithKnight, DemonKnight,
        Wolf, Wolflord, Werewolf, Goldman, Golem, Stoneman,
        Wyvern, Magiwyvern, Starwyvern, Knight, AxeKnight, ArmoredKnight,
        GreenDragon, BlueDragon, RedDragon, Dragonlord, Dragonlord2
    ]

    def test_all_enemies_have_positive_hp(self):
        for EnemyClass in self.ALL_ENEMIES:
            with self.subTest(enemy=EnemyClass.__name__):
                enemy = EnemyClass()
                self.assertGreater(enemy.hp, 0)

    def test_all_enemies_have_positive_attack(self):
        for EnemyClass in self.ALL_ENEMIES:
            with self.subTest(enemy=EnemyClass.__name__):
                enemy = EnemyClass()
                self.assertGreater(enemy.attack, 0)

    def test_all_enemies_have_names(self):
        for EnemyClass in self.ALL_ENEMIES:
            with self.subTest(enemy=EnemyClass.__name__):
                enemy = EnemyClass()
                self.assertNotEqual(enemy.name, '')

    def test_all_enemies_max_hp_equals_initial_hp(self):
        for EnemyClass in self.ALL_ENEMIES:
            with self.subTest(enemy=EnemyClass.__name__):
                enemy = EnemyClass()
                self.assertEqual(enemy.hp, enemy.max_hp)

    def test_all_enemies_not_asleep_initially(self):
        for EnemyClass in self.ALL_ENEMIES:
            with self.subTest(enemy=EnemyClass.__name__):
                enemy = EnemyClass()
                self.assertFalse(enemy.is_asleep)

    def test_all_enemies_valid_resist_values(self):
        for EnemyClass in self.ALL_ENEMIES:
            with self.subTest(enemy=EnemyClass.__name__):
                enemy = EnemyClass()
                self.assertGreaterEqual(enemy.sleep_resist, 0)
                self.assertLessEqual(enemy.sleep_resist, 1)
                self.assertGreaterEqual(enemy.stopspell_resist, 0)
                self.assertLessEqual(enemy.stopspell_resist, 1)
                self.assertGreaterEqual(enemy.hurt_resist, 0)
                self.assertLessEqual(enemy.hurt_resist, 1)

    def test_all_enemies_valid_dodge_values(self):
        for EnemyClass in self.ALL_ENEMIES:
            with self.subTest(enemy=EnemyClass.__name__):
                enemy = EnemyClass()
                self.assertGreaterEqual(enemy.dodge, 0)
                self.assertLessEqual(enemy.dodge, 1)


if __name__ == '__main__':
    unittest.main()
