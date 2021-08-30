from unittest import TestCase

import src.player
from src.player import get_remainder, apply_transformation_to_experience_chart_strength, experience_chart


class Test(TestCase):
    def setUp(self) -> None:
        self.mock_experience_chart = {
            # the stat rates are represented as the total additional points given after the initial status endowments
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
        self.mock_experience_chart_with_strength_change = {
            # the stat rates are represented as the total additional points given after the initial status endowments
            1: {'exp': 0, 'strength': 0, 'agility': 0, 'max_hp': 0, 'max_mp': 0, 'spell': None},
            2: {'exp': 7, 'strength': 1, 'agility': 0, 'max_hp': 7, 'max_mp': 0, 'spell': None},
            3: {'exp': 23, 'strength': 3, 'agility': 2, 'max_hp': 2, 'max_mp': 5, 'spell': "Heal"},
            4: {'exp': 47, 'strength': 3, 'agility': 2, 'max_hp': 7, 'max_mp': 11, 'spell': "Hurt"},
            5: {'exp': 110, 'strength': 8, 'agility': 2, 'max_hp': 4, 'max_mp': 4, 'spell': None},
            6: {'exp': 220, 'strength': 12, 'agility': 0, 'max_hp': 3, 'max_mp': 4, 'spell': None},
            7: {'exp': 450, 'strength': 14, 'agility': 7, 'max_hp': 2, 'max_mp': 2, 'spell': "Sleep"},
            8: {'exp': 800, 'strength': 18, 'agility': 3, 'max_hp': 6, 'max_mp': 3, 'spell': None},
            9: {'exp': 1300, 'strength': 26, 'agility': 2, 'max_hp': 4, 'max_mp': 7, 'spell': "Radiant"},
            10: {'exp': 2000, 'strength': 31, 'agility': 9, 'max_hp': 4, 'max_mp': 4, 'spell': "Stopspell"},
            11: {'exp': 2900, 'strength': 36, 'agility': 4, 'max_hp': 8, 'max_mp': 10, 'spell': None},
            12: {'exp': 4000, 'strength': 44, 'agility': 5, 'max_hp': 1, 'max_mp': 8, 'spell': "Outside"},
            13: {'exp': 5500, 'strength': 48, 'agility': 8, 'max_hp': 7, 'max_mp': 6, 'spell': "Return"},
            14: {'exp': 7500, 'strength': 56, 'agility': 7, 'max_hp': 8, 'max_mp': 6, 'spell': None},
            15: {'exp': 10000, 'strength': 64, 'agility': 9, 'max_hp': 8, 'max_mp': 2, 'spell': "Repel"},
            16: {'exp': 13000, 'strength': 68, 'agility': 6, 'max_hp': 6, 'max_mp': 23, 'spell': None},
            17: {'exp': 16000, 'strength': 68, 'agility': 8, 'max_hp': 8, 'max_mp': 5, 'spell': "Healmore"},
            18: {'exp': 19000, 'strength': 81, 'agility': 6, 'max_hp': 15, 'max_mp': 8, 'spell': None},
            19: {'exp': 22000, 'strength': 83, 'agility': 2, 'max_hp': 15, 'max_mp': 7, 'spell': "Hurtmore"},
            20: {'exp': 26000, 'strength': 88, 'agility': 2, 'max_hp': 8, 'max_mp': 13, 'spell': None},
            21: {'exp': 30000, 'strength': 91, 'agility': 2, 'max_hp': 11, 'max_mp': 7, 'spell': None},
            22: {'exp': 34000, 'strength': 93, 'agility': 0, 'max_hp': 9, 'max_mp': 11, 'spell': None},
            23: {'exp': 38000, 'strength': 95, 'agility': 4, 'max_hp': 7, 'max_mp': 7, 'spell': None},
            24: {'exp': 42000, 'strength': 99, 'agility': 4, 'max_hp': 5, 'max_mp': 8, 'spell': None},
            25: {'exp': 46000, 'strength': 109, 'agility': 2, 'max_hp': 4, 'max_mp': 0, 'spell': None},
            26: {'exp': 50000, 'strength': 113, 'agility': 5, 'max_hp': 6, 'max_mp': 7, 'spell': None},
            27: {'exp': 54000, 'strength': 121, 'agility': 2, 'max_hp': 9, 'max_mp': 7, 'spell': None},
            28: {'exp': 58000, 'strength': 126, 'agility': 8, 'max_hp': 6, 'max_mp': 5, 'spell': None},
            29: {'exp': 62000, 'strength': 131, 'agility': 5, 'max_hp': 5, 'max_mp': 10, 'spell': None},
            30: {'exp': 65535, 'strength': 136, 'agility': 10, 'max_hp': 10, 'max_mp': 10, 'spell': None}
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

    def test_apply_transformation_to_experience_chart_strength_with_change1(self):

        apply_transformation_to_experience_chart_strength("A")
        self.assertEqual(self.mock_experience_chart_with_strength_change, experience_chart)

    def test_apply_transformation_to_experience_chart_strength_no_change_1(self):

        apply_transformation_to_experience_chart_strength("B")
        self.assertEqual(self.mock_experience_chart, experience_chart)

    def test_apply_transformation_to_experience_chart_strength_with_change2(self):
        apply_transformation_to_experience_chart_strength("C")
        self.assertEqual(self.mock_experience_chart_with_strength_change, experience_chart)

    def test_apply_transformation_to_experience_chart_strength_no_change_2(self):
        apply_transformation_to_experience_chart_strength("D")
        self.assertEqual(self.mock_experience_chart, experience_chart)
