import unittest

from unittest.mock import patch

from src.items import weapons, armor, shields, treasure, roll_treasure_gold, TreasureChestHistory
from src.map_layouts import MapLayouts, TREASURE_BOX, BRICK
from src.maps import map_lookup


class TestWeapons(unittest.TestCase):

    def test_bamboo_pole_exists(self):
        self.assertIn('Bamboo Pole', weapons)

    def test_club_exists(self):
        self.assertIn('Club', weapons)

    def test_copper_sword_exists(self):
        self.assertIn('Copper Sword', weapons)

    def test_hand_axe_exists(self):
        self.assertIn('Hand Axe', weapons)

    def test_broad_sword_exists(self):
        self.assertIn('Broad Sword', weapons)

    def test_flame_sword_exists(self):
        self.assertIn('Flame Sword', weapons)

    def test_erdricks_sword_with_apostrophe_exists(self):
        self.assertIn("Erdrick's Sword", weapons)

    def test_erdricks_sword_without_apostrophe_exists(self):
        self.assertIn("Erdricks Sword", weapons)

    def test_all_weapons_have_offense(self):
        for name, data in weapons.items():
            with self.subTest(weapon=name):
                self.assertIn('offense', data)
                self.assertGreater(data['offense'], 0)

    def test_all_weapons_have_cost(self):
        for name, data in weapons.items():
            with self.subTest(weapon=name):
                self.assertIn('cost', data)
                self.assertGreater(data['cost'], 0)

    def test_bamboo_pole_stats(self):
        self.assertEqual(weapons['Bamboo Pole']['offense'], 2)
        self.assertEqual(weapons['Bamboo Pole']['cost'], 10)

    def test_copper_sword_stats(self):
        self.assertEqual(weapons['Copper Sword']['offense'], 10)
        self.assertEqual(weapons['Copper Sword']['cost'], 180)

    def test_erdricks_sword_strongest(self):
        offenses = [weapons[w]['offense'] for w in weapons]
        self.assertEqual(weapons["Erdrick's Sword"]['offense'], max(offenses))

    def test_weapon_offense_increases_with_tier(self):
        tier_weapons = ['Bamboo Pole', 'Club', 'Copper Sword', 'Hand Axe', 'Broad Sword']
        offenses = [weapons[w]['offense'] for w in tier_weapons]
        self.assertEqual(offenses, sorted(offenses))

    def test_bamboo_pole_sold_in_brecconary(self):
        self.assertIn('Brecconary', weapons['Bamboo Pole']['found'])

    def test_erdricks_sword_found_in_dragonlord_castle(self):
        self.assertIn("Dragonlord's Castle", weapons["Erdrick's Sword"]['found'])

    def test_erdricks_both_versions_same_offense(self):
        self.assertEqual(weapons["Erdrick's Sword"]['offense'], weapons["Erdricks Sword"]['offense'])


class TestArmor(unittest.TestCase):

    def test_clothes_exist(self):
        self.assertIn('Clothes', armor)

    def test_leather_armor_exists(self):
        self.assertIn('Leather Armor', armor)

    def test_chain_mail_exists(self):
        self.assertIn('Chain Mail', armor)

    def test_half_plate_exists(self):
        self.assertIn('Half Plate', armor)

    def test_full_plate_exists(self):
        self.assertIn('Full Plate', armor)

    def test_magic_armor_exists(self):
        self.assertIn('Magic Armor', armor)

    def test_erdricks_armor_exists(self):
        self.assertIn("Erdrick's Armor", armor)

    def test_all_armor_have_defense(self):
        for name, data in armor.items():
            with self.subTest(armor=name):
                self.assertIn('defense', data)
                self.assertGreater(data['defense'], 0)

    def test_clothes_stats(self):
        self.assertEqual(armor['Clothes']['defense'], 2)
        self.assertEqual(armor['Clothes']['cost'], 20)

    def test_erdricks_armor_strongest(self):
        # Erdrick's Armor defense is 28 and doesn't have 'sold' key
        self.assertEqual(armor["Erdrick's Armor"]['defense'], 28)

    def test_armor_defense_increases_with_tier(self):
        tier_armor = ['Clothes', 'Leather Armor', 'Chain Mail', 'Half Plate', 'Full Plate']
        defenses = [armor[a]['defense'] for a in tier_armor]
        self.assertEqual(defenses, sorted(defenses))

    def test_erdricks_armor_has_low_cost(self):
        # Erdrick's Armor has a nominal cost of 2 (it's effectively found, not purchased)
        self.assertEqual(armor["Erdrick's Armor"]['cost'], 2)


class TestShields(unittest.TestCase):

    def test_small_shield_exists(self):
        self.assertIn('Small Shield', shields)

    def test_large_shield_exists(self):
        self.assertIn('Large Shield', shields)

    def test_silver_shield_exists(self):
        self.assertIn('Silver Shield', shields)

    def test_all_shields_have_defense(self):
        for name, data in shields.items():
            with self.subTest(shield=name):
                self.assertIn('defense', data)
                self.assertGreater(data['defense'], 0)

    def test_all_shields_have_cost(self):
        for name, data in shields.items():
            with self.subTest(shield=name):
                self.assertIn('cost', data)
                self.assertGreater(data['cost'], 0)

    def test_small_shield_stats(self):
        self.assertEqual(shields['Small Shield']['defense'], 4)
        self.assertEqual(shields['Small Shield']['cost'], 90)

    def test_large_shield_stats(self):
        self.assertEqual(shields['Large Shield']['defense'], 10)
        self.assertEqual(shields['Large Shield']['cost'], 800)

    def test_silver_shield_strongest(self):
        defenses = [shields[s]['defense'] for s in shields]
        self.assertEqual(shields['Silver Shield']['defense'], max(defenses))

    def test_silver_shield_most_expensive(self):
        costs = [shields[s]['cost'] for s in shields]
        self.assertEqual(shields['Silver Shield']['cost'], max(costs))

    def test_shield_defense_increases_with_tier(self):
        tier_shields = ['Small Shield', 'Large Shield', 'Silver Shield']
        defenses = [shields[s]['defense'] for s in tier_shields]
        self.assertEqual(defenses, sorted(defenses))


class TestTreasure(unittest.TestCase):

    def test_tantegel_throne_room_exists(self):
        self.assertIn('TantegelThroneRoom', treasure)

    def test_erdricks_cave_b2_exists(self):
        self.assertIn('ErdricksCaveB2', treasure)

    def test_tantegel_cellar_exists(self):
        self.assertIn('TantegelCellar', treasure)

    def test_garins_grave_b1_exists(self):
        self.assertIn('GarinsGraveB1', treasure)

    def test_garins_grave_b3_exists(self):
        self.assertIn('GarinsGraveB3', treasure)

    def test_mountain_cave_b2_exists(self):
        self.assertIn('MountainCaveB2', treasure)

    def test_staff_of_rain_cave_exists(self):
        self.assertIn('StaffOfRainCave', treasure)

    def test_all_treasure_has_item_field(self):
        for location, chests in treasure.items():
            for pos, data in chests.items():
                with self.subTest(location=location, pos=pos):
                    self.assertIn('item', data)

    def test_tantegel_magic_key(self):
        self.assertEqual(treasure['TantegelThroneRoom'][(7, 16)]['item'], 'Magic Key')

    def test_tantegel_torch(self):
        self.assertEqual(treasure['TantegelThroneRoom'][(10, 15)]['item'], 'Torch')

    def test_tantegel_gold_amount(self):
        gold_chest = treasure['TantegelThroneRoom'][(10, 14)]
        self.assertEqual(gold_chest['item'], 'GOLD')
        self.assertEqual(gold_chest['gold'], (120, 0))

    def test_tantegel_cellar_stones_of_sunlight(self):
        self.assertEqual(treasure['TantegelCellar'][(6, 5)]['item'], 'Stones of Sunlight')

    def test_erdricks_cave_tablet(self):
        self.assertEqual(treasure['ErdricksCaveB2'][(4, 10)]['item'], 'Tablet')

    def test_garins_grave_b3_cursed_belt(self):
        self.assertEqual(treasure['GarinsGraveB3'][(2, 2)]['item'], 'Cursed Belt')

    def test_garins_grave_b3_silver_harp(self):
        self.assertEqual(treasure['GarinsGraveB3'][(7, 14)]['item'], 'Silver Harp')

    def test_mountain_cave_fighters_ring(self):
        self.assertEqual(treasure['MountainCaveB2'][(3, 3)]['item'], "Fighter's Ring")

    def test_staff_of_rain_cave(self):
        self.assertEqual(treasure['StaffOfRainCave'][(6, 5)]['item'], 'Staff of Rain')

    def test_garins_grave_random_gold_in_range(self):
        # NES TRSR_GLD1: 5 + (random AND $0F), rolled when the chest is opened
        gold_chest = treasure['GarinsGraveB1'][(1, 13)]
        self.assertEqual(gold_chest['item'], 'GOLD')
        with patch('src.items.random.randint', return_value=0):
            self.assertEqual(roll_treasure_gold(gold_chest['gold']), 5)
        with patch('src.items.random.randint', return_value=255):
            self.assertEqual(roll_treasure_gold(gold_chest['gold']), 20)

    def test_gold_ranges_match_nes(self):
        # NES GetTrsrGold ranges: GLD1 5-20, GLD2 6-13, GLD3 10-17, GLD4 500-755, GLD5 120
        ranges = set()
        for chests in treasure.values():
            for data in chests.values():
                if data['item'] == 'GOLD':
                    base, bits = data['gold']
                    ranges.add((base, base + bits))
        self.assertEqual(ranges, {(5, 20), (6, 13), (10, 17), (500, 755), (120, 120)})

    def test_every_nes_chest_is_listed(self):
        # NES TreasureTbl has 31 entries ($7C bytes / 4)
        self.assertEqual(sum(len(chests) for chests in treasure.values()), 31)

    def test_charlock_has_erdricks_sword(self):
        self.assertEqual(treasure['CharlockB3'][(8, 8)]['item'], "Erdrick's Sword")

    def test_every_chest_is_on_a_treasure_box_tile(self):
        layouts = MapLayouts()
        for map_name, chests in treasure.items():
            self.assertIn(map_name, map_lookup)
            for (row, column) in chests:
                with self.subTest(map_name=map_name, coordinates=(row, column)):
                    self.assertEqual(layouts.map_layout_lookup[map_name][row][column], TREASURE_BOX)


class TestTreasureChestHistory(unittest.TestCase):

    def test_record_and_clear_on_overworld(self):
        history = TreasureChestHistory()
        self.assertTrue(history.record('GarinsGraveB1', (1, 12)))
        self.assertTrue(history.is_opened('GarinsGraveB1', (1, 12)))
        history.enter_map('GarinsGraveB2')
        self.assertTrue(history.is_opened('GarinsGraveB1', (1, 12)))
        # NES InitMapData: entering the overworld clears the history, so chests refill
        history.enter_map('Alefgard')
        self.assertFalse(history.is_opened('GarinsGraveB1', (1, 12)))

    def test_only_eight_slots(self):
        history = TreasureChestHistory()
        for column in range(8):
            self.assertTrue(history.record('CharlockB8', (0, column)))
        self.assertFalse(history.record('CharlockB8', (1, 0)))
        self.assertFalse(history.is_opened('CharlockB8', (1, 0)))

    def test_throne_room_chests_gone_after_leaving(self):
        history = TreasureChestHistory()
        history.enter_map('TantegelThroneRoom')
        self.assertFalse(history.is_opened('TantegelThroneRoom', (10, 14)))
        history.enter_map('TantegelCourtyard')
        history.enter_map('Alefgard')
        history.enter_map('TantegelCourtyard')
        history.enter_map('TantegelThroneRoom')
        for coordinates in treasure['TantegelThroneRoom']:
            self.assertTrue(history.is_opened('TantegelThroneRoom', coordinates))

    def test_apply_to_layout(self):
        history = TreasureChestHistory()
        layout = MapLayouts().map_layout_lookup['GarinsGraveB1']
        history.record('GarinsGraveB1', (1, 13))
        layout[1][12] = BRICK
        history.apply_to_layout('GarinsGraveB1', layout, TREASURE_BOX, BRICK)
        self.assertEqual(layout[1][12], TREASURE_BOX)
        self.assertEqual(layout[1][13], BRICK)

    def test_treasure_positions_are_tuples(self):
        for location, chests in treasure.items():
            for pos in chests.keys():
                with self.subTest(location=location, pos=pos):
                    self.assertIsInstance(pos, tuple)
                    self.assertEqual(len(pos), 2)


if __name__ == '__main__':
    unittest.main()
