from unittest import TestCase

from src.player import get_remainder


class Test(TestCase):

    def test_get_remainder(self):
        """Names are from https://gamefaqs.gamespot.com/boards/563408-dragon-warrior/72498979"""
        high_12 = (
            "!",
            "J"
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
        for name in high_12:
            self.assertEqual(12, get_remainder(name))
        for name in high_strength_hp_13:
            self.assertEqual(13, get_remainder(name))
        for name in high_strength_agility_15:
            self.assertEqual(15, get_remainder(name))
