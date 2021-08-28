from unittest import TestCase

from src.player import get_remainder


class Test(TestCase):

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
