from unittest import TestCase

from src.player.player_stats import get_remainder, apply_transformation_to_experience_chart, levels_list


class Test(TestCase):
    def setUp(self) -> None:
        self.mock_levels_list = {
            1: {'exp': 0, 'strength': 0, 'agility': 0, 'max_hp': 0, 'max_mp': 0, 'spell': None},
            2: {'exp': 7, 'strength': 1, 'agility': 0, 'max_hp': 7, 'max_mp': 0, 'spell': None},
            3: {'exp': 23, 'strength': 3, 'agility': 2, 'max_hp': 2, 'max_mp': 5, 'spell': "Heal"},
            4: {'exp': 47, 'strength': 3, 'agility': 2, 'max_hp': 7, 'max_mp': 11, 'spell': "Hurt"},
            5: {'exp': 110, 'strength': 7, 'agility': 2, 'max_hp': 4, 'max_mp': 4, 'spell': None},
            6: {'exp': 220, 'strength': 11, 'agility': 0, 'max_hp': 3, 'max_mp': 4, 'spell': None},
            7: {'exp': 450, 'strength': 13, 'agility': 7, 'max_hp': 2, 'max_mp': 2, 'spell': "Sleep"},
            8: {'exp': 800, 'strength': 16, 'agility': 3, 'max_hp': 6, 'max_mp': 3, 'spell': None},
            9: {'exp': 1300, 'strength': 24, 'agility': 2, 'max_hp': 4, 'max_mp': 7, 'spell': "Radiant"},
            10: {'exp': 2000, 'strength': 28, 'agility': 9, 'max_hp': 4, 'max_mp': 4, 'spell': "Stopspell"},
            11: {'exp': 2900, 'strength': 33, 'agility': 4, 'max_hp': 8, 'max_mp': 10, 'spell': None},
            12: {'exp': 4000, 'strength': 40, 'agility': 5, 'max_hp': 1, 'max_mp': 8, 'spell': "Outside"},
            13: {'exp': 5500, 'strength': 43, 'agility': 8, 'max_hp': 7, 'max_mp': 6, 'spell': "Return"},
            14: {'exp': 7500, 'strength': 51, 'agility': 7, 'max_hp': 8, 'max_mp': 6, 'spell': None},
            15: {'exp': 10000, 'strength': 58, 'agility': 9, 'max_hp': 8, 'max_mp': 2, 'spell': "Repel"},
            16: {'exp': 13000, 'strength': 61, 'agility': 6, 'max_hp': 6, 'max_mp': 23, 'spell': None},
            17: {'exp': 16000, 'strength': 61, 'agility': 8, 'max_hp': 8, 'max_mp': 5, 'spell': "Healmore"},
            18: {'exp': 19000, 'strength': 73, 'agility': 6, 'max_hp': 15, 'max_mp': 8, 'spell': None},
            19: {'exp': 22000, 'strength': 75, 'agility': 2, 'max_hp': 15, 'max_mp': 7, 'spell': "Hurtmore"},
            20: {'exp': 26000, 'strength': 79, 'agility': 2, 'max_hp': 8, 'max_mp': 13, 'spell': None},
            21: {'exp': 30000, 'strength': 82, 'agility': 2, 'max_hp': 11, 'max_mp': 7, 'spell': None},
            22: {'exp': 34000, 'strength': 84, 'agility': 0, 'max_hp': 9, 'max_mp': 11, 'spell': None},
            23: {'exp': 38000, 'strength': 86, 'agility': 4, 'max_hp': 7, 'max_mp': 7, 'spell': None},
            24: {'exp': 42000, 'strength': 89, 'agility': 4, 'max_hp': 5, 'max_mp': 8, 'spell': None},
            25: {'exp': 46000, 'strength': 98, 'agility': 2, 'max_hp': 4, 'max_mp': 0, 'spell': None},
            26: {'exp': 50000, 'strength': 102, 'agility': 5, 'max_hp': 6, 'max_mp': 7, 'spell': None},
            27: {'exp': 54000, 'strength': 109, 'agility': 2, 'max_hp': 9, 'max_mp': 7, 'spell': None},
            28: {'exp': 58000, 'strength': 114, 'agility': 8, 'max_hp': 6, 'max_mp': 5, 'spell': None},
            29: {'exp': 62000, 'strength': 118, 'agility': 5, 'max_hp': 5, 'max_mp': 10, 'spell': None},
            30: {'exp': 65535, 'strength': 123, 'agility': 10, 'max_hp': 10, 'max_mp': 10, 'spell': None}
        }
        self.mock_levels_list_0 = {
            1: {'exp': 0, 'total_exp': 0, 'strength': 4 - 1, 'agility': 4 - 1, 'max_hp': 15, 'max_mp': 0, 'spell': None},
            2: {'exp': 7, 'total_exp': 7, 'strength': 5 - 1, 'agility': 4 - 1, 'max_hp': 22, 'max_mp': 0, 'spell': None},
            3: {'exp': 16, 'total_exp': 23, 'strength': 7 - 1, 'agility': 6 - 1, 'max_hp': 24, 'max_mp': 5, 'spell': "HEAL"},
            4: {'exp': 24, 'total_exp': 47, 'strength': 7 - 1, 'agility': 8 - 1, 'max_hp': 31, 'max_mp': 16, 'spell': "HURT"},
            5: {'exp': 63, 'total_exp': 110, 'strength': 12 - 2, 'agility': 10 - 1, 'max_hp': 35, 'max_mp': 20, 'spell': None},
            6: {'exp': 110, 'total_exp': 220, 'strength': 16 - 2, 'agility': 10 - 1, 'max_hp': 38, 'max_mp': 24, 'spell': None},
            7: {'exp': 230, 'total_exp': 450, 'strength': 18 - 2, 'agility': 17 - 2, 'max_hp': 40, 'max_mp': 26, 'spell': "SLEEP"},
            8: {'exp': 350, 'total_exp': 800, 'strength': 22 - 3, 'agility': 20 - 2, 'max_hp': 46, 'max_mp': 29, 'spell': None},
            9: {'exp': 500, 'total_exp': 1300, 'strength': 30 - 3, 'agility': 22 - 3, 'max_hp': 50, 'max_mp': 36, 'spell': "RADIANT"},
            10: {'exp': 700, 'total_exp': 2000, 'strength': 35 - 4, 'agility': 31 - 4, 'max_hp': 54, 'max_mp': 40, 'spell': "STOPSPELL"},
            11: {'exp': 900, 'total_exp': 2900, 'strength': 40 - 4, 'agility': 35 - 4, 'max_hp': 62, 'max_mp': 50, 'spell': None},
            12: {'exp': 1100, 'total_exp': 4000, 'strength': 48 - 5, 'agility': 40 - 4, 'max_hp': 63, 'max_mp': 58, 'spell': "OUTSIDE"},
            13: {'exp': 1500, 'total_exp': 5500, 'strength': 52 - 6, 'agility': 48 - 5, 'max_hp': 70, 'max_mp': 64, 'spell': "RETURN"},
            14: {'exp': 2000, 'total_exp': 7500, 'strength': 60 - 6, 'agility': 55 - 6, 'max_hp': 78, 'max_mp': 70, 'spell': None},
            15: {'exp': 2500, 'total_exp': 10000, 'strength': 68 - 7, 'agility': 64 - 7, 'max_hp': 86, 'max_mp': 72, 'spell': "REPEL"},
            16: {'exp': 3000, 'total_exp': 13000, 'strength': 72 - 8, 'agility': 70 - 7, 'max_hp': 92, 'max_mp': 95, 'spell': None},
            17: {'exp': 3000, 'total_exp': 16000, 'strength': 72 - 8, 'agility': 78 - 8, 'max_hp': 100, 'max_mp': 100, 'spell': "HEALMORE"},
            18: {'exp': 3000, 'total_exp': 19000, 'strength': 85 - 9, 'agility': 84 - 9, 'max_hp': 115, 'max_mp': 108, 'spell': None},
            19: {'exp': 3000, 'total_exp': 22000, 'strength': 87 - 9, 'agility': 86 - 9, 'max_hp': 130, 'max_mp': 115, 'spell': "HURTMORE"},
            20: {'exp': 4000, 'total_exp': 26000, 'strength': 92 - 10, 'agility': 88 - 9, 'max_hp': 138, 'max_mp': 128, 'spell': None},
            21: {'exp': 4000, 'total_exp': 30000, 'strength': 95 - 10, 'agility': 90 - 9, 'max_hp': 149, 'max_mp': 135, 'spell': None},
            22: {'exp': 4000, 'total_exp': 34000, 'strength': 97 - 10, 'agility': 90 - 9, 'max_hp': 158, 'max_mp': 146, 'spell': None},
            23: {'exp': 4000, 'total_exp': 38000, 'strength': 99 - 10, 'agility': 94 - 10, 'max_hp': 165, 'max_mp': 153, 'spell': None},
            24: {'exp': 4000, 'total_exp': 42000, 'strength': 103 - 11, 'agility': 98 - 10, 'max_hp': 170, 'max_mp': 161, 'spell': None},
            25: {'exp': 4000, 'total_exp': 46000, 'strength': 113 - 12, 'agility': 100 - 10, 'max_hp': 174, 'max_mp': 161, 'spell': None},
            26: {'exp': 4000, 'total_exp': 50000, 'strength': 117 - 12, 'agility': 105 - 11, 'max_hp': 180, 'max_mp': 168, 'spell': None},
            27: {'exp': 4000, 'total_exp': 54000, 'strength': 125 - 13, 'agility': 107 - 11, 'max_hp': 189, 'max_mp': 175, 'spell': None},
            28: {'exp': 4000, 'total_exp': 58000, 'strength': 130 - 13, 'agility': 115 - 12, 'max_hp': 195, 'max_mp': 180, 'spell': None},
            29: {'exp': 4000, 'total_exp': 62000, 'strength': 135 - 14, 'agility': 120 - 12, 'max_hp': 200, 'max_mp': 190, 'spell': None},
            30: {'exp': 3535, 'total_exp': 65535, 'strength': 140 - 14, 'agility': 130 - 13, 'max_hp': 210, 'max_mp': 200, 'spell': None},
        }

    def test_get_remainder(self):
        """Names are from https://gamefaqs.gamespot.com/boards/563408-dragon-warrior/72498979"""
        high_12 = (
            "!",
        )
        high_strength_hp_13 = (
            # growth type "B"
            "Jacquie",
            "Gina",

            "J",
            "NAME",
            "LUIGI",
            "Zelda",
            "KEFKA",
            "EDGAR",
            "Rocky",
            "Sabin",
            "Arthus",
            "Ceres",
            "Edea",
            "Kane",
            "Yang",
            "Hassan",
            "Rocky"
        )
        high_strength_agility_15 = (
            # growth type "D"
            "Edward",
            "ED",
            "Larry",
            "Joseph",

            "L",
            "Name",
            "Luigi",
            "Mara",
            "Cristo",
            "Esturk",
            "CLOUD",
            "Kefka",
            "Edgar",
            "Gwen",
            "Aeris",
            "Aramis",
            "Milon",
            "Pacman",
            "Zemus"
        )
        self.assertEqual(0, get_remainder("Steve"))
        self.assertEqual(1, get_remainder("Eva"))
        self.assertEqual(2, get_remainder("Im"))
        self.assertEqual(3, get_remainder("Va"))
        self.assertEqual(4, get_remainder("Eddie"))
        self.assertEqual(5, get_remainder("Ed"))
        self.assertEqual(6, get_remainder("Walter"))
        self.assertEqual(7, get_remainder("Eon"))
        self.assertEqual(8, get_remainder("gooo"))
        self.assertEqual(9, get_remainder("Sejin"))
        self.assertEqual(10, get_remainder("Stephen"))
        self.assertEqual(11, get_remainder("James"))
        self.assertEqual(12, get_remainder("Gao"))
        self.assertEqual(13, get_remainder("Jacquie"))
        self.assertEqual(14, get_remainder("Wall"))
        self.assertEqual(15, get_remainder("Edward"))
        for name in high_12:
            self.assertEqual(12, get_remainder(name))
        for name in high_strength_hp_13:
            self.assertEqual(13, get_remainder(name))
        for name in high_strength_agility_15:
            self.assertEqual(15, get_remainder(name))

    def test_apply_transformation_to_experience_chart_0(self):
        """Strength and Agility penalized.
        Example name: Steve
        """
        apply_transformation_to_experience_chart(0)
        self.assertEqual(self.mock_levels_list_0, levels_list)

    def test_apply_transformation_to_experience_chart_1(self):
        """Agility and Maximum MP penalized.
        Example name: Eva
        """
        apply_transformation_to_experience_chart(1)
        self.assertEqual(self.mock_levels_list, levels_list)

    def test_apply_transformation_to_experience_chart_2(self):
        """Strength and Maximum HP penalized.
        Example name: Im
        """
        apply_transformation_to_experience_chart(2)
        self.assertEqual(self.mock_levels_list, levels_list)

    def test_apply_transformation_to_experience_chart_3(self):
        """Strength and Maximum HP penalized.
        Example name: Im
        """
        apply_transformation_to_experience_chart(3)
        self.assertEqual(self.mock_levels_list, levels_list)

    def test_apply_transformation_to_experience_chart_4(self):
        """Strength and Agility penalized.
        Example name: Eddie
        """
        apply_transformation_to_experience_chart(4)
        self.assertEqual(self.mock_levels_list, levels_list)

    def test_apply_transformation_to_experience_chart_5(self):
        """Agility and Maximum MP penalized.
        Example name: Ed
        """
        apply_transformation_to_experience_chart(5)
        self.assertEqual(self.mock_levels_list, levels_list)

    def test_apply_transformation_to_experience_chart_6(self):
        """Strength and Maximum HP penalized.
        Example name: Walter
        """
        apply_transformation_to_experience_chart(6)
        self.assertEqual(self.mock_levels_list, levels_list)

    def test_apply_transformation_to_experience_chart_7(self):
        """Maximum HP and Maximum MP penalized.
        Example name: Uno
        """
        apply_transformation_to_experience_chart(7)
        self.assertEqual(self.mock_levels_list, levels_list)

    def test_apply_transformation_to_experience_chart_8(self):
        """Maximum HP and Maximum MP penalized.
        Example name: gooo
        """
        apply_transformation_to_experience_chart(8)
        self.assertEqual(self.mock_levels_list, levels_list)

    def test_apply_transformation_to_experience_chart_9(self):
        """Strength and Agility penalized.
        Example name: Sejin
        """
        apply_transformation_to_experience_chart(9)
        self.assertEqual(self.mock_levels_list, levels_list)

    def test_apply_transformation_to_experience_chart_10(self):
        """Strength and Maximum HP penalized.
        Example name: Stephen
        """
        apply_transformation_to_experience_chart(10)
        self.assertEqual(self.mock_levels_list, levels_list)

    def test_apply_transformation_to_experience_chart_11(self):
        """Maximum HP and Maximum MP penalized.
        Example name: James
        """
        apply_transformation_to_experience_chart(11)
        self.assertEqual(self.mock_levels_list, levels_list)

    def test_apply_transformation_to_experience_chart_12(self):
        """Strength and Agility penalized.
        Example name: Gao
        """
        apply_transformation_to_experience_chart(12)
        self.assertEqual(self.mock_levels_list, levels_list)

    def test_apply_transformation_to_experience_chart_13(self):
        """Agility and Maximum MP penalized.
        Example name: Jacquie / Gina
        """
        apply_transformation_to_experience_chart(13)
        self.assertEqual(self.mock_levels_list, levels_list)

    def test_apply_transformation_to_experience_chart_14(self):
        """Strength and Maximum HP penalized.
        Example name: Wall
        """
        apply_transformation_to_experience_chart(14)
        self.assertEqual(self.mock_levels_list, levels_list)

    def test_apply_transformation_to_experience_chart_15(self):
        """Maximum HP and Maximum MP penalized.
        Example name: Edward / Larry / Joseph
        """
        apply_transformation_to_experience_chart(15)
        self.assertEqual(self.mock_levels_list, levels_list)
