import unittest

from src.enemy import (
    Slime, RedSlime, MetalSlime, Drakee, Magidrakee, Drakeema,
    Ghost, Poltergeist, Specter, Magician, Warlock, Wizard,
    Scorpion, MetalScorpion, RogueScorpion, Druin, Druinlord,
    Droll, Drollmagi, Skeleton, Wraith, WraithKnight, DemonKnight,
    Wolf, Wolflord, Werewolf, Goldman, Golem, Stoneman,
    Wyvern, Magiwyvern, Starwyvern, Knight, AxeKnight, ArmoredKnight,
    GreenDragon, BlueDragon, RedDragon, Dragonlord, Dragonlord2
)
from src.enemy_lookup import (
    enemy_string_lookup, enemy_image_position_lookup, enemy_territory_map
)


class TestEnemyStringLookup(unittest.TestCase):

    def test_slime_lookup(self):
        self.assertIs(enemy_string_lookup['Slime'], Slime)

    def test_red_slime_lookup(self):
        self.assertIs(enemy_string_lookup['Red Slime'], RedSlime)

    def test_metal_slime_lookup(self):
        self.assertIs(enemy_string_lookup['Metal Slime'], MetalSlime)

    def test_dragonlord_lookup(self):
        self.assertIs(enemy_string_lookup['Dragonlord'], Dragonlord)

    def test_dragonlord2_lookup(self):
        self.assertIs(enemy_string_lookup['Dragonlord 2'], Dragonlord2)

    def test_all_expected_enemies_in_lookup(self):
        expected = [
            'Slime', 'Red Slime', 'Metal Slime', 'Drakee', 'Magidrakee', 'Drakeema',
            'Ghost', 'Poltergeist', 'Specter', 'Magician', 'Warlock', 'Wizard',
            'Scorpion', 'Metal Scorpion', 'Rogue Scorpion', 'Druin', 'Druinlord',
            'Droll', 'Drollmagi', 'Skeleton', 'Wraith', 'Wraith Knight', 'Demon Knight',
            'Wolf', 'Wolflord', 'Werewolf', 'Goldman', 'Golem', 'Stoneman',
            'Wyvern', 'Magiwyvern', 'Starwyvern', 'Knight', 'Axe Knight', 'Armored Knight',
            'Green Dragon', 'Blue Dragon', 'Red Dragon', 'Dragonlord', 'Dragonlord 2'
        ]
        for name in expected:
            with self.subTest(name=name):
                self.assertIn(name, enemy_string_lookup)

    def test_lookup_produces_instantiable_classes(self):
        for name, EnemyClass in enemy_string_lookup.items():
            with self.subTest(name=name):
                instance = EnemyClass()
                self.assertEqual(instance.name, name)

    def test_lookup_values_are_classes(self):
        for name, value in enemy_string_lookup.items():
            with self.subTest(name=name):
                self.assertTrue(callable(value))


class TestEnemyImagePositionLookup(unittest.TestCase):

    def test_slime_has_position(self):
        self.assertIn('Slime', enemy_image_position_lookup)

    def test_dragonlord2_has_position(self):
        self.assertIn('Dragonlord 2', enemy_image_position_lookup)

    def test_all_string_lookup_enemies_have_image_position(self):
        for name in enemy_string_lookup.keys():
            with self.subTest(name=name):
                self.assertIn(name, enemy_image_position_lookup)

    def test_positions_are_tuples_of_two_floats(self):
        for name, pos in enemy_image_position_lookup.items():
            with self.subTest(name=name):
                self.assertIsInstance(pos, tuple)
                self.assertEqual(len(pos), 2)
                for val in pos:
                    self.assertIsInstance(val, (int, float))

    def test_slime_position(self):
        self.assertEqual(enemy_image_position_lookup['Slime'], (8, 7))

    def test_dragonlord_position(self):
        self.assertEqual(enemy_image_position_lookup['Dragonlord'], (7.5, 6))


class TestEnemyTerritoryMap(unittest.TestCase):

    def test_origin_has_enemies(self):
        self.assertIn((0, 0), enemy_territory_map)

    def test_swamp_cave_special_zone(self):
        self.assertIn((-1, -1), enemy_territory_map)

    def test_garins_grave_special_zones(self):
        self.assertIn((-2, -2), enemy_territory_map)
        self.assertIn((-3, -3), enemy_territory_map)
        self.assertIn((-4, -4), enemy_territory_map)
        self.assertIn((-5, -5), enemy_territory_map)

    def test_territory_values_are_tuples(self):
        for key, enemies in enemy_territory_map.items():
            with self.subTest(key=key):
                self.assertIsInstance(enemies, tuple)

    def test_territory_enemies_are_non_empty(self):
        for key, enemies in enemy_territory_map.items():
            with self.subTest(key=key):
                self.assertGreater(len(enemies), 0)

    def test_swamp_cave_contains_druin(self):
        self.assertIn('Druin', enemy_territory_map[(-1, -1)])

    def test_garins_grave_b1_contains_expected_enemies(self):
        b1 = enemy_territory_map[(-2, -2)]
        self.assertIn('Skeleton', b1)
        self.assertIn('Warlock', b1)

    def test_grid_coordinates_present(self):
        for row in range(8):
            for col in range(8):
                with self.subTest(coord=(row, col)):
                    self.assertIn((row, col), enemy_territory_map)

    def test_territory_enemy_names_are_strings(self):
        for key, enemies in enemy_territory_map.items():
            for enemy_name in enemies:
                with self.subTest(key=key, enemy=enemy_name):
                    self.assertIsInstance(enemy_name, str)


if __name__ == '__main__':
    unittest.main()
