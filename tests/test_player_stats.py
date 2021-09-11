from unittest import TestCase

from src.player.player_stats import get_remainder, apply_transformation_to_levels_list, levels_list, get_total_name_score, get_bonus


class Test(TestCase):
    def setUp(self) -> None:
        self.levels_list = {
            1: {'exp': 0, 'total_exp': 0, 'strength': 4, 'agility': 4, 'max_hp': 15, 'max_mp': 0, 'spell': None},
            2: {'exp': 7, 'total_exp': 7, 'strength': 5, 'agility': 4, 'max_hp': 22, 'max_mp': 0, 'spell': None},
            3: {'exp': 16, 'total_exp': 23, 'strength': 7, 'agility': 6, 'max_hp': 24, 'max_mp': 5, 'spell': "HEAL"},
            4: {'exp': 24, 'total_exp': 47, 'strength': 7, 'agility': 8, 'max_hp': 31, 'max_mp': 16, 'spell': "HURT"},
            5: {'exp': 63, 'total_exp': 110, 'strength': 12, 'agility': 10, 'max_hp': 35, 'max_mp': 20, 'spell': None},
            6: {'exp': 110, 'total_exp': 220, 'strength': 16, 'agility': 10, 'max_hp': 38, 'max_mp': 24, 'spell': None},
            7: {'exp': 230, 'total_exp': 450, 'strength': 18, 'agility': 17, 'max_hp': 40, 'max_mp': 26, 'spell': "SLEEP"},
            8: {'exp': 350, 'total_exp': 800, 'strength': 22, 'agility': 20, 'max_hp': 46, 'max_mp': 29, 'spell': None},
            9: {'exp': 500, 'total_exp': 1300, 'strength': 30, 'agility': 22, 'max_hp': 50, 'max_mp': 36, 'spell': "RADIANT"},
            10: {'exp': 700, 'total_exp': 2000, 'strength': 35, 'agility': 31, 'max_hp': 54, 'max_mp': 40, 'spell': "STOPSPELL"},
            11: {'exp': 900, 'total_exp': 2900, 'strength': 40, 'agility': 35, 'max_hp': 62, 'max_mp': 50, 'spell': None},
            12: {'exp': 1100, 'total_exp': 4000, 'strength': 48, 'agility': 40, 'max_hp': 63, 'max_mp': 58, 'spell': "OUTSIDE"},
            13: {'exp': 1500, 'total_exp': 5500, 'strength': 52, 'agility': 48, 'max_hp': 70, 'max_mp': 64, 'spell': "RETURN"},
            14: {'exp': 2000, 'total_exp': 7500, 'strength': 60, 'agility': 55, 'max_hp': 78, 'max_mp': 70, 'spell': None},
            15: {'exp': 2500, 'total_exp': 10000, 'strength': 68, 'agility': 64, 'max_hp': 86, 'max_mp': 72, 'spell': "REPEL"},
            16: {'exp': 3000, 'total_exp': 13000, 'strength': 72, 'agility': 70, 'max_hp': 92, 'max_mp': 95, 'spell': None},
            17: {'exp': 3000, 'total_exp': 16000, 'strength': 72, 'agility': 78, 'max_hp': 100, 'max_mp': 100, 'spell': "HEALMORE"},
            18: {'exp': 3000, 'total_exp': 19000, 'strength': 85, 'agility': 84, 'max_hp': 115, 'max_mp': 108, 'spell': None},
            19: {'exp': 3000, 'total_exp': 22000, 'strength': 87, 'agility': 86, 'max_hp': 130, 'max_mp': 115, 'spell': "HURTMORE"},
            20: {'exp': 4000, 'total_exp': 26000, 'strength': 92, 'agility': 88, 'max_hp': 138, 'max_mp': 128, 'spell': None},
            21: {'exp': 4000, 'total_exp': 30000, 'strength': 95, 'agility': 90, 'max_hp': 149, 'max_mp': 135, 'spell': None},
            22: {'exp': 4000, 'total_exp': 34000, 'strength': 97, 'agility': 90, 'max_hp': 158, 'max_mp': 146, 'spell': None},
            23: {'exp': 4000, 'total_exp': 38000, 'strength': 99, 'agility': 94, 'max_hp': 165, 'max_mp': 153, 'spell': None},
            24: {'exp': 4000, 'total_exp': 42000, 'strength': 103, 'agility': 98, 'max_hp': 170, 'max_mp': 161, 'spell': None},
            25: {'exp': 4000, 'total_exp': 46000, 'strength': 113, 'agility': 100, 'max_hp': 174, 'max_mp': 161, 'spell': None},
            26: {'exp': 4000, 'total_exp': 50000, 'strength': 117, 'agility': 105, 'max_hp': 180, 'max_mp': 168, 'spell': None},
            27: {'exp': 4000, 'total_exp': 54000, 'strength': 125, 'agility': 107, 'max_hp': 189, 'max_mp': 175, 'spell': None},
            28: {'exp': 4000, 'total_exp': 58000, 'strength': 130, 'agility': 115, 'max_hp': 195, 'max_mp': 180, 'spell': None},
            29: {'exp': 4000, 'total_exp': 62000, 'strength': 135, 'agility': 120, 'max_hp': 200, 'max_mp': 190, 'spell': None},
            30: {'exp': 3535, 'total_exp': 65535, 'strength': 140, 'agility': 130, 'max_hp': 210, 'max_mp': 200, 'spell': None},
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
        self.mock_levels_list_1 = {
            1: {'exp': 0, 'total_exp': 0, 'strength': 4, 'agility': 4 - 1, 'max_hp': 15, 'max_mp': 0, 'spell': None},
            2: {'exp': 7, 'total_exp': 7, 'strength': 5, 'agility': 4 - 1, 'max_hp': 22, 'max_mp': 0, 'spell': None},
            3: {'exp': 16, 'total_exp': 23, 'strength': 7, 'agility': 6 - 1, 'max_hp': 24, 'max_mp': 5 - 1, 'spell': "HEAL"},
            4: {'exp': 24, 'total_exp': 47, 'strength': 7, 'agility': 8 - 1, 'max_hp': 31, 'max_mp': 16 - 2, 'spell': "HURT"},
            5: {'exp': 63, 'total_exp': 110, 'strength': 12, 'agility': 10 - 1, 'max_hp': 35, 'max_mp': 20 - 2, 'spell': None},
            6: {'exp': 110, 'total_exp': 220, 'strength': 16, 'agility': 10 - 1, 'max_hp': 38, 'max_mp': 24 - 3, 'spell': None},
            7: {'exp': 230, 'total_exp': 450, 'strength': 18, 'agility': 17 - 2, 'max_hp': 40, 'max_mp': 26 - 3, 'spell': "SLEEP"},
            8: {'exp': 350, 'total_exp': 800, 'strength': 22, 'agility': 20 - 2, 'max_hp': 46, 'max_mp': 29 - 3, 'spell': None},
            9: {'exp': 500, 'total_exp': 1300, 'strength': 30, 'agility': 22 - 3, 'max_hp': 50, 'max_mp': 36 - 4, 'spell': "RADIANT"},
            10: {'exp': 700, 'total_exp': 2000, 'strength': 35, 'agility': 31 - 4, 'max_hp': 54, 'max_mp': 40 - 4, 'spell': "STOPSPELL"},
            11: {'exp': 900, 'total_exp': 2900, 'strength': 40, 'agility': 35 - 4, 'max_hp': 62, 'max_mp': 50 - 5, 'spell': None},
            12: {'exp': 1100, 'total_exp': 4000, 'strength': 48, 'agility': 40 - 4, 'max_hp': 63, 'max_mp': 58 - 6, 'spell': "OUTSIDE"},
            13: {'exp': 1500, 'total_exp': 5500, 'strength': 52, 'agility': 48 - 5, 'max_hp': 70, 'max_mp': 64 - 7, 'spell': "RETURN"},
            14: {'exp': 2000, 'total_exp': 7500, 'strength': 60, 'agility': 55 - 6, 'max_hp': 78, 'max_mp': 70 - 7, 'spell': None},
            15: {'exp': 2500, 'total_exp': 10000, 'strength': 68, 'agility': 64 - 7, 'max_hp': 86, 'max_mp': 72 - 8, 'spell': "REPEL"},
            16: {'exp': 3000, 'total_exp': 13000, 'strength': 72, 'agility': 70 - 7, 'max_hp': 92, 'max_mp': 95 - 10, 'spell': None},
            17: {'exp': 3000, 'total_exp': 16000, 'strength': 72, 'agility': 78 - 8, 'max_hp': 100, 'max_mp': 100 - 10, 'spell': "HEALMORE"},
            18: {'exp': 3000, 'total_exp': 19000, 'strength': 85, 'agility': 84 - 9, 'max_hp': 115, 'max_mp': 108 - 11, 'spell': None},
            19: {'exp': 3000, 'total_exp': 22000, 'strength': 87, 'agility': 86 - 9, 'max_hp': 130, 'max_mp': 115 - 12, 'spell': "HURTMORE"},
            20: {'exp': 4000, 'total_exp': 26000, 'strength': 92, 'agility': 88 - 9, 'max_hp': 138, 'max_mp': 128 - 13, 'spell': None},
            21: {'exp': 4000, 'total_exp': 30000, 'strength': 95, 'agility': 90 - 9, 'max_hp': 149, 'max_mp': 135 - 14, 'spell': None},
            22: {'exp': 4000, 'total_exp': 34000, 'strength': 97, 'agility': 90 - 9, 'max_hp': 158, 'max_mp': 146 - 15, 'spell': None},
            23: {'exp': 4000, 'total_exp': 38000, 'strength': 99, 'agility': 94 - 10, 'max_hp': 165, 'max_mp': 153 - 16, 'spell': None},
            24: {'exp': 4000, 'total_exp': 42000, 'strength': 103, 'agility': 98 - 10, 'max_hp': 170, 'max_mp': 161 - 17, 'spell': None},
            25: {'exp': 4000, 'total_exp': 46000, 'strength': 113, 'agility': 100 - 10, 'max_hp': 174, 'max_mp': 161 - 17, 'spell': None},
            26: {'exp': 4000, 'total_exp': 50000, 'strength': 117, 'agility': 105 - 11, 'max_hp': 180, 'max_mp': 168 - 17, 'spell': None},
            27: {'exp': 4000, 'total_exp': 54000, 'strength': 125, 'agility': 107 - 11, 'max_hp': 189, 'max_mp': 175 - 18, 'spell': None},
            28: {'exp': 4000, 'total_exp': 58000, 'strength': 130, 'agility': 115 - 12, 'max_hp': 195, 'max_mp': 180 - 18, 'spell': None},
            29: {'exp': 4000, 'total_exp': 62000, 'strength': 135, 'agility': 120 - 12, 'max_hp': 200, 'max_mp': 190 - 19, 'spell': None},
            30: {'exp': 3535, 'total_exp': 65535, 'strength': 140, 'agility': 130 - 13, 'max_hp': 210, 'max_mp': 200 - 20, 'spell': None},
        }
        self.mock_levels_list_2 = {
            1: {'exp': 0, 'total_exp': 0, 'strength': 4 - 1, 'agility': 4, 'max_hp': 15 - 2, 'max_mp': 0, 'spell': None},
            2: {'exp': 7, 'total_exp': 7, 'strength': 5 - 1, 'agility': 4, 'max_hp': 22 - 3, 'max_mp': 0, 'spell': None},
            3: {'exp': 16, 'total_exp': 23, 'strength': 7 - 1, 'agility': 6, 'max_hp': 24 - 3, 'max_mp': 5, 'spell': "HEAL"},
            4: {'exp': 24, 'total_exp': 47, 'strength': 7 - 1, 'agility': 8, 'max_hp': 31 - 4, 'max_mp': 16, 'spell': "HURT"},
            5: {'exp': 63, 'total_exp': 110, 'strength': 12 - 2, 'agility': 10, 'max_hp': 35 - 4, 'max_mp': 20, 'spell': None},
            6: {'exp': 110, 'total_exp': 220, 'strength': 16 - 2, 'agility': 10, 'max_hp': 38 - 4, 'max_mp': 24, 'spell': None},
            7: {'exp': 230, 'total_exp': 450, 'strength': 18 - 2, 'agility': 17, 'max_hp': 40 - 4, 'max_mp': 26, 'spell': "SLEEP"},
            8: {'exp': 350, 'total_exp': 800, 'strength': 22 - 3, 'agility': 20, 'max_hp': 46 - 5, 'max_mp': 29, 'spell': None},
            9: {'exp': 500, 'total_exp': 1300, 'strength': 30 - 3, 'agility': 22, 'max_hp': 50 - 5, 'max_mp': 36, 'spell': "RADIANT"},
            10: {'exp': 700, 'total_exp': 2000, 'strength': 35 - 4, 'agility': 31, 'max_hp': 54 - 6, 'max_mp': 40, 'spell': "STOPSPELL"},
            11: {'exp': 900, 'total_exp': 2900, 'strength': 40 - 4, 'agility': 35, 'max_hp': 62 - 7, 'max_mp': 50, 'spell': None},
            12: {'exp': 1100, 'total_exp': 4000, 'strength': 48 - 5, 'agility': 40, 'max_hp': 63 - 7, 'max_mp': 58, 'spell': "OUTSIDE"},
            13: {'exp': 1500, 'total_exp': 5500, 'strength': 52 - 6, 'agility': 48, 'max_hp': 70 - 7, 'max_mp': 64, 'spell': "RETURN"},
            14: {'exp': 2000, 'total_exp': 7500, 'strength': 60 - 6, 'agility': 55, 'max_hp': 78 - 8, 'max_mp': 70, 'spell': None},
            15: {'exp': 2500, 'total_exp': 10000, 'strength': 68 - 7, 'agility': 64, 'max_hp': 86 - 9, 'max_mp': 72, 'spell': "REPEL"},
            16: {'exp': 3000, 'total_exp': 13000, 'strength': 72 - 8, 'agility': 70, 'max_hp': 92 - 10, 'max_mp': 95, 'spell': None},
            17: {'exp': 3000, 'total_exp': 16000, 'strength': 72 - 8, 'agility': 78, 'max_hp': 100 - 10, 'max_mp': 100, 'spell': "HEALMORE"},
            18: {'exp': 3000, 'total_exp': 19000, 'strength': 85 - 9, 'agility': 84, 'max_hp': 115 - 12, 'max_mp': 108, 'spell': None},
            19: {'exp': 3000, 'total_exp': 22000, 'strength': 87 - 9, 'agility': 86, 'max_hp': 130 - 13, 'max_mp': 115, 'spell': "HURTMORE"},
            20: {'exp': 4000, 'total_exp': 26000, 'strength': 92 - 10, 'agility': 88, 'max_hp': 138 - 14, 'max_mp': 128, 'spell': None},
            21: {'exp': 4000, 'total_exp': 30000, 'strength': 95 - 10, 'agility': 90, 'max_hp': 149 - 15, 'max_mp': 135, 'spell': None},
            22: {'exp': 4000, 'total_exp': 34000, 'strength': 97 - 10, 'agility': 90, 'max_hp': 158 - 16, 'max_mp': 146, 'spell': None},
            23: {'exp': 4000, 'total_exp': 38000, 'strength': 99 - 10, 'agility': 94, 'max_hp': 165 - 17, 'max_mp': 153, 'spell': None},
            24: {'exp': 4000, 'total_exp': 42000, 'strength': 103 - 11, 'agility': 98, 'max_hp': 170 - 17, 'max_mp': 161, 'spell': None},
            25: {'exp': 4000, 'total_exp': 46000, 'strength': 113 - 12, 'agility': 100, 'max_hp': 174 - 18, 'max_mp': 161, 'spell': None},
            26: {'exp': 4000, 'total_exp': 50000, 'strength': 117 - 12, 'agility': 105, 'max_hp': 180 - 18, 'max_mp': 168, 'spell': None},
            27: {'exp': 4000, 'total_exp': 54000, 'strength': 125 - 13, 'agility': 107, 'max_hp': 189 - 19, 'max_mp': 175, 'spell': None},
            28: {'exp': 4000, 'total_exp': 58000, 'strength': 130 - 13, 'agility': 115, 'max_hp': 195 - 20, 'max_mp': 180, 'spell': None},
            29: {'exp': 4000, 'total_exp': 62000, 'strength': 135 - 14, 'agility': 120, 'max_hp': 200 - 20, 'max_mp': 190, 'spell': None},
            30: {'exp': 3535, 'total_exp': 65535, 'strength': 140 - 14, 'agility': 130, 'max_hp': 210 - 21, 'max_mp': 200, 'spell': None},

        }
        self.mock_levels_list_3 = {
            1: {'exp': 0, 'total_exp': 0, 'strength': 4, 'agility': 4, 'max_hp': 15 - 2, 'max_mp': 0, 'spell': None},
            2: {'exp': 7, 'total_exp': 7, 'strength': 5, 'agility': 4, 'max_hp': 22 - 3, 'max_mp': 0, 'spell': None},
            3: {'exp': 16, 'total_exp': 23, 'strength': 7, 'agility': 6, 'max_hp': 24 - 3, 'max_mp': 5 - 1, 'spell': "HEAL"},
            4: {'exp': 24, 'total_exp': 47, 'strength': 7, 'agility': 8, 'max_hp': 31 - 4, 'max_mp': 16 - 2, 'spell': "HURT"},
            5: {'exp': 63, 'total_exp': 110, 'strength': 12, 'agility': 10, 'max_hp': 35 - 4, 'max_mp': 20 - 2, 'spell': None},
            6: {'exp': 110, 'total_exp': 220, 'strength': 16, 'agility': 10, 'max_hp': 38 - 4, 'max_mp': 24 - 3, 'spell': None},
            7: {'exp': 230, 'total_exp': 450, 'strength': 18, 'agility': 17, 'max_hp': 40 - 4, 'max_mp': 26 - 3, 'spell': "SLEEP"},
            8: {'exp': 350, 'total_exp': 800, 'strength': 22, 'agility': 20, 'max_hp': 46 - 5, 'max_mp': 29 - 3, 'spell': None},
            9: {'exp': 500, 'total_exp': 1300, 'strength': 30, 'agility': 22, 'max_hp': 50 - 5, 'max_mp': 36 - 4, 'spell': "RADIANT"},
            10: {'exp': 700, 'total_exp': 2000, 'strength': 35, 'agility': 31, 'max_hp': 54 - 6, 'max_mp': 40 - 4, 'spell': "STOPSPELL"},
            11: {'exp': 900, 'total_exp': 2900, 'strength': 40, 'agility': 35, 'max_hp': 62 - 7, 'max_mp': 50 - 5, 'spell': None},
            12: {'exp': 1100, 'total_exp': 4000, 'strength': 48, 'agility': 40, 'max_hp': 63 - 7, 'max_mp': 58 - 6, 'spell': "OUTSIDE"},
            13: {'exp': 1500, 'total_exp': 5500, 'strength': 52, 'agility': 48, 'max_hp': 70 - 7, 'max_mp': 64 - 7, 'spell': "RETURN"},
            14: {'exp': 2000, 'total_exp': 7500, 'strength': 60, 'agility': 55, 'max_hp': 78 - 8, 'max_mp': 70 - 7, 'spell': None},
            15: {'exp': 2500, 'total_exp': 10000, 'strength': 68, 'agility': 64, 'max_hp': 86 - 9, 'max_mp': 72 - 8, 'spell': "REPEL"},
            16: {'exp': 3000, 'total_exp': 13000, 'strength': 72, 'agility': 70, 'max_hp': 92 - 10, 'max_mp': 95 - 10, 'spell': None},
            17: {'exp': 3000, 'total_exp': 16000, 'strength': 72, 'agility': 78, 'max_hp': 100 - 10, 'max_mp': 100 - 10, 'spell': "HEALMORE"},
            18: {'exp': 3000, 'total_exp': 19000, 'strength': 85, 'agility': 84, 'max_hp': 115 - 12, 'max_mp': 108 - 11, 'spell': None},
            19: {'exp': 3000, 'total_exp': 22000, 'strength': 87, 'agility': 86, 'max_hp': 130 - 13, 'max_mp': 115 - 12, 'spell': "HURTMORE"},
            20: {'exp': 4000, 'total_exp': 26000, 'strength': 92, 'agility': 88, 'max_hp': 138 - 14, 'max_mp': 128 - 13, 'spell': None},
            21: {'exp': 4000, 'total_exp': 30000, 'strength': 95, 'agility': 90, 'max_hp': 149 - 15, 'max_mp': 135 - 14, 'spell': None},
            22: {'exp': 4000, 'total_exp': 34000, 'strength': 97, 'agility': 90, 'max_hp': 158 - 16, 'max_mp': 146 - 15, 'spell': None},
            23: {'exp': 4000, 'total_exp': 38000, 'strength': 99, 'agility': 94, 'max_hp': 165 - 17, 'max_mp': 153 - 16, 'spell': None},
            24: {'exp': 4000, 'total_exp': 42000, 'strength': 103, 'agility': 98, 'max_hp': 170 - 17, 'max_mp': 161 - 17, 'spell': None},
            25: {'exp': 4000, 'total_exp': 46000, 'strength': 113, 'agility': 100, 'max_hp': 174 - 18, 'max_mp': 161 - 17, 'spell': None},
            26: {'exp': 4000, 'total_exp': 50000, 'strength': 117, 'agility': 105, 'max_hp': 180 - 18, 'max_mp': 168 - 17, 'spell': None},
            27: {'exp': 4000, 'total_exp': 54000, 'strength': 125, 'agility': 107, 'max_hp': 189 - 19, 'max_mp': 175 - 18, 'spell': None},
            28: {'exp': 4000, 'total_exp': 58000, 'strength': 130, 'agility': 115, 'max_hp': 195 - 20, 'max_mp': 180 - 18, 'spell': None},
            29: {'exp': 4000, 'total_exp': 62000, 'strength': 135, 'agility': 120, 'max_hp': 200 - 20, 'max_mp': 190 - 19, 'spell': None},
            30: {'exp': 3535, 'total_exp': 65535, 'strength': 140, 'agility': 130, 'max_hp': 210 - 21, 'max_mp': 200 - 20, 'spell': None},

        }
        self.mock_levels_list_4 = {
            1: {'exp': 0, 'total_exp': 0, 'strength': 4, 'agility': 4, 'max_hp': 15, 'max_mp': 0, 'spell': None},
            2: {'exp': 7, 'total_exp': 7, 'strength': 5, 'agility': 4, 'max_hp': 22, 'max_mp': 0, 'spell': None},
            3: {'exp': 16, 'total_exp': 23, 'strength': 7, 'agility': 6, 'max_hp': 24, 'max_mp': 5, 'spell': "HEAL"},
            4: {'exp': 24, 'total_exp': 47, 'strength': 7, 'agility': 8, 'max_hp': 31, 'max_mp': 16, 'spell': "HURT"},
            5: {'exp': 63, 'total_exp': 110, 'strength': 12 - 1, 'agility': 10, 'max_hp': 35, 'max_mp': 20, 'spell': None},
            6: {'exp': 110, 'total_exp': 220, 'strength': 16 - 1, 'agility': 10, 'max_hp': 38, 'max_mp': 24, 'spell': None},
            7: {'exp': 230, 'total_exp': 450, 'strength': 18 - 1, 'agility': 17 - 1, 'max_hp': 40, 'max_mp': 26, 'spell': "SLEEP"},
            8: {'exp': 350, 'total_exp': 800, 'strength': 22 - 2, 'agility': 20 - 1, 'max_hp': 46, 'max_mp': 29, 'spell': None},
            9: {'exp': 500, 'total_exp': 1300, 'strength': 30 - 2, 'agility': 22 - 2, 'max_hp': 50, 'max_mp': 36, 'spell': "RADIANT"},
            10: {'exp': 700, 'total_exp': 2000, 'strength': 35 - 3, 'agility': 31 - 3, 'max_hp': 54, 'max_mp': 40, 'spell': "STOPSPELL"},
            11: {'exp': 900, 'total_exp': 2900, 'strength': 40 - 3, 'agility': 35 - 3, 'max_hp': 62, 'max_mp': 50, 'spell': None},
            12: {'exp': 1100, 'total_exp': 4000, 'strength': 48 - 4, 'agility': 40 - 3, 'max_hp': 63, 'max_mp': 58, 'spell': "OUTSIDE"},
            13: {'exp': 1500, 'total_exp': 5500, 'strength': 52 - 5, 'agility': 48 - 4, 'max_hp': 70, 'max_mp': 64, 'spell': "RETURN"},
            14: {'exp': 2000, 'total_exp': 7500, 'strength': 60 - 5, 'agility': 55 - 5, 'max_hp': 78, 'max_mp': 70, 'spell': None},
            15: {'exp': 2500, 'total_exp': 10000, 'strength': 68 - 6, 'agility': 64 - 6, 'max_hp': 86, 'max_mp': 72, 'spell': "REPEL"},
            16: {'exp': 3000, 'total_exp': 13000, 'strength': 72 - 7, 'agility': 70 - 6, 'max_hp': 92, 'max_mp': 95, 'spell': None},
            17: {'exp': 3000, 'total_exp': 16000, 'strength': 72 - 7, 'agility': 78 - 7, 'max_hp': 100, 'max_mp': 100, 'spell': "HEALMORE"},
            18: {'exp': 3000, 'total_exp': 19000, 'strength': 85 - 8, 'agility': 84 - 8, 'max_hp': 115, 'max_mp': 108, 'spell': None},
            19: {'exp': 3000, 'total_exp': 22000, 'strength': 87 - 8, 'agility': 86 - 8, 'max_hp': 130, 'max_mp': 115, 'spell': "HURTMORE"},
            20: {'exp': 4000, 'total_exp': 26000, 'strength': 92 - 9, 'agility': 88 - 8, 'max_hp': 138, 'max_mp': 128, 'spell': None},
            21: {'exp': 4000, 'total_exp': 30000, 'strength': 95 - 9, 'agility': 90 - 8, 'max_hp': 149, 'max_mp': 135, 'spell': None},
            22: {'exp': 4000, 'total_exp': 34000, 'strength': 97 - 9, 'agility': 90 - 8, 'max_hp': 158, 'max_mp': 146, 'spell': None},
            23: {'exp': 4000, 'total_exp': 38000, 'strength': 99 - 9, 'agility': 94 - 9, 'max_hp': 165, 'max_mp': 153, 'spell': None},
            24: {'exp': 4000, 'total_exp': 42000, 'strength': 103 - 10, 'agility': 98 - 9, 'max_hp': 170, 'max_mp': 161, 'spell': None},
            25: {'exp': 4000, 'total_exp': 46000, 'strength': 113 - 11, 'agility': 100 - 9, 'max_hp': 174, 'max_mp': 161, 'spell': None},
            26: {'exp': 4000, 'total_exp': 50000, 'strength': 117 - 11, 'agility': 105 - 10, 'max_hp': 180, 'max_mp': 168, 'spell': None},
            27: {'exp': 4000, 'total_exp': 54000, 'strength': 125 - 12, 'agility': 107 - 10, 'max_hp': 189, 'max_mp': 175, 'spell': None},
            28: {'exp': 4000, 'total_exp': 58000, 'strength': 130 - 12, 'agility': 115 - 11, 'max_hp': 195, 'max_mp': 180, 'spell': None},
            29: {'exp': 4000, 'total_exp': 62000, 'strength': 135 - 13, 'agility': 120 - 11, 'max_hp': 200, 'max_mp': 190, 'spell': None},
            30: {'exp': 3535, 'total_exp': 65535, 'strength': 140 - 13, 'agility': 130 - 12, 'max_hp': 210, 'max_mp': 200, 'spell': None},

        }
        self.mock_levels_list_5 = {
            1: {'exp': 0, 'total_exp': 0, 'strength': 4, 'agility': 4, 'max_hp': 15, 'max_mp': 0, 'spell': None},
            2: {'exp': 7, 'total_exp': 7, 'strength': 5, 'agility': 4, 'max_hp': 22, 'max_mp': 0, 'spell': None},
            3: {'exp': 16, 'total_exp': 23, 'strength': 7, 'agility': 6, 'max_hp': 24, 'max_mp': 5, 'spell': "HEAL"},
            4: {'exp': 24, 'total_exp': 47, 'strength': 7, 'agility': 8, 'max_hp': 31, 'max_mp': 16 - 1, 'spell': "HURT"},
            5: {'exp': 63, 'total_exp': 110, 'strength': 12, 'agility': 10, 'max_hp': 35, 'max_mp': 20 - 1, 'spell': None},
            6: {'exp': 110, 'total_exp': 220, 'strength': 16, 'agility': 10, 'max_hp': 38, 'max_mp': 24 - 2, 'spell': None},
            7: {'exp': 230, 'total_exp': 450, 'strength': 18, 'agility': 17 - 1, 'max_hp': 40, 'max_mp': 26 - 2, 'spell': "SLEEP"},
            8: {'exp': 350, 'total_exp': 800, 'strength': 22, 'agility': 20 - 1, 'max_hp': 46, 'max_mp': 29 - 2, 'spell': None},
            9: {'exp': 500, 'total_exp': 1300, 'strength': 30, 'agility': 22 - 2, 'max_hp': 50, 'max_mp': 36 - 3, 'spell': "RADIANT"},
            10: {'exp': 700, 'total_exp': 2000, 'strength': 35, 'agility': 31 - 3, 'max_hp': 54, 'max_mp': 40 - 3, 'spell': "STOPSPELL"},
            11: {'exp': 900, 'total_exp': 2900, 'strength': 40, 'agility': 35 - 3, 'max_hp': 62, 'max_mp': 50 - 4, 'spell': None},
            12: {'exp': 1100, 'total_exp': 4000, 'strength': 48, 'agility': 40 - 3, 'max_hp': 63, 'max_mp': 58 - 5, 'spell': "OUTSIDE"},
            13: {'exp': 1500, 'total_exp': 5500, 'strength': 52, 'agility': 48 - 4, 'max_hp': 70, 'max_mp': 64 - 6, 'spell': "RETURN"},
            14: {'exp': 2000, 'total_exp': 7500, 'strength': 60, 'agility': 55 - 5, 'max_hp': 78, 'max_mp': 70 - 6, 'spell': None},
            15: {'exp': 2500, 'total_exp': 10000, 'strength': 68, 'agility': 64 - 6, 'max_hp': 86, 'max_mp': 72 - 7, 'spell': "REPEL"},
            16: {'exp': 3000, 'total_exp': 13000, 'strength': 72, 'agility': 70 - 6, 'max_hp': 92, 'max_mp': 95 - 9, 'spell': None},
            17: {'exp': 3000, 'total_exp': 16000, 'strength': 72, 'agility': 78 - 7, 'max_hp': 100, 'max_mp': 100 - 9, 'spell': "HEALMORE"},
            18: {'exp': 3000, 'total_exp': 19000, 'strength': 85, 'agility': 84 - 8, 'max_hp': 115, 'max_mp': 108 - 10, 'spell': None},
            19: {'exp': 3000, 'total_exp': 22000, 'strength': 87, 'agility': 86 - 8, 'max_hp': 130, 'max_mp': 115 - 11, 'spell': "HURTMORE"},
            20: {'exp': 4000, 'total_exp': 26000, 'strength': 92, 'agility': 88 - 8, 'max_hp': 138, 'max_mp': 128 - 12, 'spell': None},
            21: {'exp': 4000, 'total_exp': 30000, 'strength': 95, 'agility': 90 - 8, 'max_hp': 149, 'max_mp': 135 - 13, 'spell': None},
            22: {'exp': 4000, 'total_exp': 34000, 'strength': 97, 'agility': 90 - 8, 'max_hp': 158, 'max_mp': 146 - 14, 'spell': None},
            23: {'exp': 4000, 'total_exp': 38000, 'strength': 99, 'agility': 94 - 9, 'max_hp': 165, 'max_mp': 153 - 15, 'spell': None},
            24: {'exp': 4000, 'total_exp': 42000, 'strength': 103, 'agility': 98 - 9, 'max_hp': 170, 'max_mp': 161 - 16, 'spell': None},
            25: {'exp': 4000, 'total_exp': 46000, 'strength': 113, 'agility': 100 - 9, 'max_hp': 174, 'max_mp': 161 - 16, 'spell': None},
            26: {'exp': 4000, 'total_exp': 50000, 'strength': 117, 'agility': 105 - 10, 'max_hp': 180, 'max_mp': 168 - 16, 'spell': None},
            27: {'exp': 4000, 'total_exp': 54000, 'strength': 125, 'agility': 107 - 10, 'max_hp': 189, 'max_mp': 175 - 17, 'spell': None},
            28: {'exp': 4000, 'total_exp': 58000, 'strength': 130, 'agility': 115 - 11, 'max_hp': 195, 'max_mp': 180 - 17, 'spell': None},
            29: {'exp': 4000, 'total_exp': 62000, 'strength': 135, 'agility': 120 - 11, 'max_hp': 200, 'max_mp': 190 - 18, 'spell': None},
            30: {'exp': 3535, 'total_exp': 65535, 'strength': 140, 'agility': 130 - 12, 'max_hp': 210, 'max_mp': 200 - 19, 'spell': None},

        }
        self.mock_levels_list_6 = {
            1: {'exp': 0, 'total_exp': 0, 'strength': 4, 'agility': 4, 'max_hp': 15 - 1, 'max_mp': 0, 'spell': None},
            2: {'exp': 7, 'total_exp': 7, 'strength': 5, 'agility': 4, 'max_hp': 22 - 2, 'max_mp': 0, 'spell': None},
            3: {'exp': 16, 'total_exp': 23, 'strength': 7, 'agility': 6, 'max_hp': 24 - 2, 'max_mp': 5, 'spell': "HEAL"},
            4: {'exp': 24, 'total_exp': 47, 'strength': 7, 'agility': 8, 'max_hp': 31 - 3, 'max_mp': 16, 'spell': "HURT"},
            5: {'exp': 63, 'total_exp': 110, 'strength': 12 - 1, 'agility': 10, 'max_hp': 35 - 3, 'max_mp': 20, 'spell': None},
            6: {'exp': 110, 'total_exp': 220, 'strength': 16 - 1, 'agility': 10, 'max_hp': 38 - 3, 'max_mp': 24, 'spell': None},
            7: {'exp': 230, 'total_exp': 450, 'strength': 18 - 1, 'agility': 17, 'max_hp': 40 - 3, 'max_mp': 26, 'spell': "SLEEP"},
            8: {'exp': 350, 'total_exp': 800, 'strength': 22 - 2, 'agility': 20, 'max_hp': 46 - 4, 'max_mp': 29, 'spell': None},
            9: {'exp': 500, 'total_exp': 1300, 'strength': 30 - 2, 'agility': 22, 'max_hp': 50 - 4, 'max_mp': 36, 'spell': "RADIANT"},
            10: {'exp': 700, 'total_exp': 2000, 'strength': 35 - 3, 'agility': 31, 'max_hp': 54 - 5, 'max_mp': 40, 'spell': "STOPSPELL"},
            11: {'exp': 900, 'total_exp': 2900, 'strength': 40 - 3, 'agility': 35, 'max_hp': 62 - 6, 'max_mp': 50, 'spell': None},
            12: {'exp': 1100, 'total_exp': 4000, 'strength': 48 - 4, 'agility': 40, 'max_hp': 63 - 6, 'max_mp': 58, 'spell': "OUTSIDE"},
            13: {'exp': 1500, 'total_exp': 5500, 'strength': 52 - 5, 'agility': 48, 'max_hp': 70 - 6, 'max_mp': 64, 'spell': "RETURN"},
            14: {'exp': 2000, 'total_exp': 7500, 'strength': 60 - 5, 'agility': 55, 'max_hp': 78 - 7, 'max_mp': 70, 'spell': None},
            15: {'exp': 2500, 'total_exp': 10000, 'strength': 68 - 6, 'agility': 64, 'max_hp': 86 - 8, 'max_mp': 72, 'spell': "REPEL"},
            16: {'exp': 3000, 'total_exp': 13000, 'strength': 72 - 7, 'agility': 70, 'max_hp': 92 - 9, 'max_mp': 95, 'spell': None},
            17: {'exp': 3000, 'total_exp': 16000, 'strength': 72 - 7, 'agility': 78, 'max_hp': 100 - 9, 'max_mp': 100, 'spell': "HEALMORE"},
            18: {'exp': 3000, 'total_exp': 19000, 'strength': 85 - 8, 'agility': 84, 'max_hp': 115 - 11, 'max_mp': 108, 'spell': None},
            19: {'exp': 3000, 'total_exp': 22000, 'strength': 87 - 8, 'agility': 86, 'max_hp': 130 - 12, 'max_mp': 115, 'spell': "HURTMORE"},
            20: {'exp': 4000, 'total_exp': 26000, 'strength': 92 - 9, 'agility': 88, 'max_hp': 138 - 13, 'max_mp': 128, 'spell': None},
            21: {'exp': 4000, 'total_exp': 30000, 'strength': 95 - 9, 'agility': 90, 'max_hp': 149 - 14, 'max_mp': 135, 'spell': None},
            22: {'exp': 4000, 'total_exp': 34000, 'strength': 97 - 9, 'agility': 90, 'max_hp': 158 - 15, 'max_mp': 146, 'spell': None},
            23: {'exp': 4000, 'total_exp': 38000, 'strength': 99 - 9, 'agility': 94, 'max_hp': 165 - 16, 'max_mp': 153, 'spell': None},
            24: {'exp': 4000, 'total_exp': 42000, 'strength': 103 - 10, 'agility': 98, 'max_hp': 170 - 16, 'max_mp': 161, 'spell': None},
            25: {'exp': 4000, 'total_exp': 46000, 'strength': 113 - 11, 'agility': 100, 'max_hp': 174 - 17, 'max_mp': 161, 'spell': None},
            26: {'exp': 4000, 'total_exp': 50000, 'strength': 117 - 11, 'agility': 105, 'max_hp': 180 - 17, 'max_mp': 168, 'spell': None},
            27: {'exp': 4000, 'total_exp': 54000, 'strength': 125 - 12, 'agility': 107, 'max_hp': 189 - 18, 'max_mp': 175, 'spell': None},
            28: {'exp': 4000, 'total_exp': 58000, 'strength': 130 - 12, 'agility': 115, 'max_hp': 195 - 19, 'max_mp': 180, 'spell': None},
            29: {'exp': 4000, 'total_exp': 62000, 'strength': 135 - 13, 'agility': 120, 'max_hp': 200 - 19, 'max_mp': 190, 'spell': None},
            30: {'exp': 3535, 'total_exp': 65535, 'strength': 140 - 13, 'agility': 130, 'max_hp': 210 - 20, 'max_mp': 200, 'spell': None},

        }
        self.mock_levels_list_7 = {
            1: {'exp': 0, 'total_exp': 0, 'strength': 4, 'agility': 4, 'max_hp': 15 - 1, 'max_mp': 0, 'spell': None},
            2: {'exp': 7, 'total_exp': 7, 'strength': 5, 'agility': 4, 'max_hp': 22 - 2, 'max_mp': 0, 'spell': None},
            3: {'exp': 16, 'total_exp': 23, 'strength': 7, 'agility': 6, 'max_hp': 24 - 2, 'max_mp': 5, 'spell': "HEAL"},
            4: {'exp': 24, 'total_exp': 47, 'strength': 7, 'agility': 8, 'max_hp': 31 - 3, 'max_mp': 16 - 1, 'spell': "HURT"},
            5: {'exp': 63, 'total_exp': 110, 'strength': 12, 'agility': 10, 'max_hp': 35 - 3, 'max_mp': 20 - 1, 'spell': None},
            6: {'exp': 110, 'total_exp': 220, 'strength': 16, 'agility': 10, 'max_hp': 38 - 3, 'max_mp': 24 - 2, 'spell': None},
            7: {'exp': 230, 'total_exp': 450, 'strength': 18, 'agility': 17, 'max_hp': 40 - 3, 'max_mp': 26 - 2, 'spell': "SLEEP"},
            8: {'exp': 350, 'total_exp': 800, 'strength': 22, 'agility': 20, 'max_hp': 46 - 4, 'max_mp': 29 - 2, 'spell': None},
            9: {'exp': 500, 'total_exp': 1300, 'strength': 30, 'agility': 22, 'max_hp': 50 - 4, 'max_mp': 36 - 3, 'spell': "RADIANT"},
            10: {'exp': 700, 'total_exp': 2000, 'strength': 35, 'agility': 31, 'max_hp': 54 - 5, 'max_mp': 40 - 3, 'spell': "STOPSPELL"},
            11: {'exp': 900, 'total_exp': 2900, 'strength': 40, 'agility': 35, 'max_hp': 62 - 6, 'max_mp': 50 - 4, 'spell': None},
            12: {'exp': 1100, 'total_exp': 4000, 'strength': 48, 'agility': 40, 'max_hp': 63 - 6, 'max_mp': 58 - 5, 'spell': "OUTSIDE"},
            13: {'exp': 1500, 'total_exp': 5500, 'strength': 52, 'agility': 48, 'max_hp': 70 - 6, 'max_mp': 64 - 6, 'spell': "RETURN"},
            14: {'exp': 2000, 'total_exp': 7500, 'strength': 60, 'agility': 55, 'max_hp': 78 - 7, 'max_mp': 70 - 6, 'spell': None},
            15: {'exp': 2500, 'total_exp': 10000, 'strength': 68, 'agility': 64, 'max_hp': 86 - 8, 'max_mp': 72 - 7, 'spell': "REPEL"},
            16: {'exp': 3000, 'total_exp': 13000, 'strength': 72, 'agility': 70, 'max_hp': 92 - 9, 'max_mp': 95 - 9, 'spell': None},
            17: {'exp': 3000, 'total_exp': 16000, 'strength': 72, 'agility': 78, 'max_hp': 100 - 9, 'max_mp': 100 - 9, 'spell': "HEALMORE"},
            18: {'exp': 3000, 'total_exp': 19000, 'strength': 85, 'agility': 84, 'max_hp': 115 - 11, 'max_mp': 108 - 10, 'spell': None},
            19: {'exp': 3000, 'total_exp': 22000, 'strength': 87, 'agility': 86, 'max_hp': 130 - 12, 'max_mp': 115 - 11, 'spell': "HURTMORE"},
            20: {'exp': 4000, 'total_exp': 26000, 'strength': 92, 'agility': 88, 'max_hp': 138 - 13, 'max_mp': 128 - 12, 'spell': None},
            21: {'exp': 4000, 'total_exp': 30000, 'strength': 95, 'agility': 90, 'max_hp': 149 - 14, 'max_mp': 135 - 13, 'spell': None},
            22: {'exp': 4000, 'total_exp': 34000, 'strength': 97, 'agility': 90, 'max_hp': 158 - 15, 'max_mp': 146 - 14, 'spell': None},
            23: {'exp': 4000, 'total_exp': 38000, 'strength': 99, 'agility': 94, 'max_hp': 165 - 16, 'max_mp': 153 - 15, 'spell': None},
            24: {'exp': 4000, 'total_exp': 42000, 'strength': 103, 'agility': 98, 'max_hp': 170 - 16, 'max_mp': 161 - 16, 'spell': None},
            25: {'exp': 4000, 'total_exp': 46000, 'strength': 113, 'agility': 100, 'max_hp': 174 - 17, 'max_mp': 161 - 16, 'spell': None},
            26: {'exp': 4000, 'total_exp': 50000, 'strength': 117, 'agility': 105, 'max_hp': 180 - 17, 'max_mp': 168 - 16, 'spell': None},
            27: {'exp': 4000, 'total_exp': 54000, 'strength': 125, 'agility': 107, 'max_hp': 189 - 18, 'max_mp': 175 - 17, 'spell': None},
            28: {'exp': 4000, 'total_exp': 58000, 'strength': 130, 'agility': 115, 'max_hp': 195 - 19, 'max_mp': 180 - 17, 'spell': None},
            29: {'exp': 4000, 'total_exp': 62000, 'strength': 135, 'agility': 120, 'max_hp': 200 - 19, 'max_mp': 190 - 18, 'spell': None},
            30: {'exp': 3535, 'total_exp': 65535, 'strength': 140, 'agility': 130, 'max_hp': 210 - 20, 'max_mp': 200 - 19, 'spell': None},

        }
        self.mock_levels_list_8 = {
            1: {'exp': 0, 'total_exp': 0, 'strength': 4 + 1, 'agility': 4 + 1, 'max_hp': 15, 'max_mp': 0, 'spell': None},
            2: {'exp': 7, 'total_exp': 7, 'strength': 5 + 1, 'agility': 4 + 1, 'max_hp': 22, 'max_mp': 0, 'spell': None},
            3: {'exp': 16, 'total_exp': 23, 'strength': 7 + 1, 'agility': 6 + 1, 'max_hp': 24, 'max_mp': 5, 'spell': "HEAL"},
            4: {'exp': 24, 'total_exp': 47, 'strength': 7 + 1, 'agility': 8 + 1, 'max_hp': 31, 'max_mp': 16, 'spell': "HURT"},
            5: {'exp': 63, 'total_exp': 110, 'strength': 12, 'agility': 10 + 1, 'max_hp': 35, 'max_mp': 20, 'spell': None},
            6: {'exp': 110, 'total_exp': 220, 'strength': 16, 'agility': 10 + 1, 'max_hp': 38, 'max_mp': 24, 'spell': None},
            7: {'exp': 230, 'total_exp': 450, 'strength': 18, 'agility': 17, 'max_hp': 40, 'max_mp': 26, 'spell': "SLEEP"},
            8: {'exp': 350, 'total_exp': 800, 'strength': 22 - 1, 'agility': 20, 'max_hp': 46, 'max_mp': 29, 'spell': None},
            9: {'exp': 500, 'total_exp': 1300, 'strength': 30 - 1, 'agility': 22 - 1, 'max_hp': 50, 'max_mp': 36, 'spell': "RADIANT"},
            10: {'exp': 700, 'total_exp': 2000, 'strength': 35 - 2, 'agility': 31 - 2, 'max_hp': 54, 'max_mp': 40, 'spell': "STOPSPELL"},
            11: {'exp': 900, 'total_exp': 2900, 'strength': 40 - 2, 'agility': 35 - 2, 'max_hp': 62, 'max_mp': 50, 'spell': None},
            12: {'exp': 1100, 'total_exp': 4000, 'strength': 48 - 3, 'agility': 40 - 2, 'max_hp': 63, 'max_mp': 58, 'spell': "OUTSIDE"},
            13: {'exp': 1500, 'total_exp': 5500, 'strength': 52 - 4, 'agility': 48 - 3, 'max_hp': 70, 'max_mp': 64, 'spell': "RETURN"},
            14: {'exp': 2000, 'total_exp': 7500, 'strength': 60 - 4, 'agility': 55 - 4, 'max_hp': 78, 'max_mp': 70, 'spell': None},
            15: {'exp': 2500, 'total_exp': 10000, 'strength': 68 - 5, 'agility': 64 - 5, 'max_hp': 86, 'max_mp': 72, 'spell': "REPEL"},
            16: {'exp': 3000, 'total_exp': 13000, 'strength': 72 - 6, 'agility': 70 - 5, 'max_hp': 92, 'max_mp': 95, 'spell': None},
            17: {'exp': 3000, 'total_exp': 16000, 'strength': 72 - 6, 'agility': 78 - 6, 'max_hp': 100, 'max_mp': 100, 'spell': "HEALMORE"},
            18: {'exp': 3000, 'total_exp': 19000, 'strength': 85 - 7, 'agility': 84 - 7, 'max_hp': 115, 'max_mp': 108, 'spell': None},
            19: {'exp': 3000, 'total_exp': 22000, 'strength': 87 - 7, 'agility': 86 - 7, 'max_hp': 130, 'max_mp': 115, 'spell': "HURTMORE"},
            20: {'exp': 4000, 'total_exp': 26000, 'strength': 92 - 8, 'agility': 88 - 7, 'max_hp': 138, 'max_mp': 128, 'spell': None},
            21: {'exp': 4000, 'total_exp': 30000, 'strength': 95 - 8, 'agility': 90 - 7, 'max_hp': 149, 'max_mp': 135, 'spell': None},
            22: {'exp': 4000, 'total_exp': 34000, 'strength': 97 - 8, 'agility': 90 - 7, 'max_hp': 158, 'max_mp': 146, 'spell': None},
            23: {'exp': 4000, 'total_exp': 38000, 'strength': 99 - 8, 'agility': 94 - 8, 'max_hp': 165, 'max_mp': 153, 'spell': None},
            24: {'exp': 4000, 'total_exp': 42000, 'strength': 103 - 9, 'agility': 98 - 8, 'max_hp': 170, 'max_mp': 161, 'spell': None},
            25: {'exp': 4000, 'total_exp': 46000, 'strength': 113 - 10, 'agility': 100 - 8, 'max_hp': 174, 'max_mp': 161, 'spell': None},
            26: {'exp': 4000, 'total_exp': 50000, 'strength': 117 - 10, 'agility': 105 - 9, 'max_hp': 180, 'max_mp': 168, 'spell': None},
            27: {'exp': 4000, 'total_exp': 54000, 'strength': 125 - 11, 'agility': 107 - 9, 'max_hp': 189, 'max_mp': 175, 'spell': None},
            28: {'exp': 4000, 'total_exp': 58000, 'strength': 130 - 11, 'agility': 115 - 10, 'max_hp': 195, 'max_mp': 180, 'spell': None},
            29: {'exp': 4000, 'total_exp': 62000, 'strength': 135 - 12, 'agility': 120 - 10, 'max_hp': 200, 'max_mp': 190, 'spell': None},
            30: {'exp': 3535, 'total_exp': 65535, 'strength': 140 - 12, 'agility': 130 - 11, 'max_hp': 210, 'max_mp': 200, 'spell': None},

        }
        self.mock_levels_list_9 = {
            1: {'exp': 0, 'total_exp': 0, 'strength': 4, 'agility': 4 + 1, 'max_hp': 15, 'max_mp': 0, 'spell': None},
            2: {'exp': 7, 'total_exp': 7, 'strength': 5, 'agility': 4 + 1, 'max_hp': 22, 'max_mp': 0, 'spell': None},
            3: {'exp': 16, 'total_exp': 23, 'strength': 7, 'agility': 6 + 1, 'max_hp': 24, 'max_mp': 5 + 1, 'spell': "HEAL"},
            4: {'exp': 24, 'total_exp': 47, 'strength': 7, 'agility': 8 + 1, 'max_hp': 31, 'max_mp': 16, 'spell': "HURT"},
            5: {'exp': 63, 'total_exp': 110, 'strength': 12, 'agility': 10 + 1, 'max_hp': 35, 'max_mp': 20, 'spell': None},
            6: {'exp': 110, 'total_exp': 220, 'strength': 16, 'agility': 10 + 1, 'max_hp': 38, 'max_mp': 24 - 1, 'spell': None},
            7: {'exp': 230, 'total_exp': 450, 'strength': 18, 'agility': 17, 'max_hp': 40, 'max_mp': 26 - 1, 'spell': "SLEEP"},
            8: {'exp': 350, 'total_exp': 800, 'strength': 22, 'agility': 20, 'max_hp': 46, 'max_mp': 29 - 1, 'spell': None},
            9: {'exp': 500, 'total_exp': 1300, 'strength': 30, 'agility': 22 - 1, 'max_hp': 50, 'max_mp': 36 - 2, 'spell': "RADIANT"},
            10: {'exp': 700, 'total_exp': 2000, 'strength': 35, 'agility': 31 - 2, 'max_hp': 54, 'max_mp': 40 - 2, 'spell': "STOPSPELL"},
            11: {'exp': 900, 'total_exp': 2900, 'strength': 40, 'agility': 35 - 2, 'max_hp': 62, 'max_mp': 50 - 3, 'spell': None},
            12: {'exp': 1100, 'total_exp': 4000, 'strength': 48, 'agility': 40 - 2, 'max_hp': 63, 'max_mp': 58 - 4, 'spell': "OUTSIDE"},
            13: {'exp': 1500, 'total_exp': 5500, 'strength': 52, 'agility': 48 - 3, 'max_hp': 70, 'max_mp': 64 - 5, 'spell': "RETURN"},
            14: {'exp': 2000, 'total_exp': 7500, 'strength': 60, 'agility': 55 - 4, 'max_hp': 78, 'max_mp': 70 - 5, 'spell': None},
            15: {'exp': 2500, 'total_exp': 10000, 'strength': 68, 'agility': 64 - 5, 'max_hp': 86, 'max_mp': 72 - 6, 'spell': "REPEL"},
            16: {'exp': 3000, 'total_exp': 13000, 'strength': 72, 'agility': 70 - 5, 'max_hp': 92, 'max_mp': 95 - 8, 'spell': None},
            17: {'exp': 3000, 'total_exp': 16000, 'strength': 72, 'agility': 78 - 6, 'max_hp': 100, 'max_mp': 100 - 8, 'spell': "HEALMORE"},
            18: {'exp': 3000, 'total_exp': 19000, 'strength': 85, 'agility': 84 - 7, 'max_hp': 115, 'max_mp': 108 - 9, 'spell': None},
            19: {'exp': 3000, 'total_exp': 22000, 'strength': 87, 'agility': 86 - 7, 'max_hp': 130, 'max_mp': 115 - 10, 'spell': "HURTMORE"},
            20: {'exp': 4000, 'total_exp': 26000, 'strength': 92, 'agility': 88 - 7, 'max_hp': 138, 'max_mp': 128 - 11, 'spell': None},
            21: {'exp': 4000, 'total_exp': 30000, 'strength': 95, 'agility': 90 - 7, 'max_hp': 149, 'max_mp': 135 - 12, 'spell': None},
            22: {'exp': 4000, 'total_exp': 34000, 'strength': 97, 'agility': 90 - 7, 'max_hp': 158, 'max_mp': 146 - 13, 'spell': None},
            23: {'exp': 4000, 'total_exp': 38000, 'strength': 99, 'agility': 94 - 8, 'max_hp': 165, 'max_mp': 153 - 14, 'spell': None},
            24: {'exp': 4000, 'total_exp': 42000, 'strength': 103, 'agility': 98 - 8, 'max_hp': 170, 'max_mp': 161 - 15, 'spell': None},
            25: {'exp': 4000, 'total_exp': 46000, 'strength': 113, 'agility': 100 - 8, 'max_hp': 174, 'max_mp': 161 - 15, 'spell': None},
            26: {'exp': 4000, 'total_exp': 50000, 'strength': 117, 'agility': 105 - 9, 'max_hp': 180, 'max_mp': 168 - 15, 'spell': None},
            27: {'exp': 4000, 'total_exp': 54000, 'strength': 125, 'agility': 107 - 9, 'max_hp': 189, 'max_mp': 175 - 16, 'spell': None},
            28: {'exp': 4000, 'total_exp': 58000, 'strength': 130, 'agility': 115 - 10, 'max_hp': 195, 'max_mp': 180 - 16, 'spell': None},
            29: {'exp': 4000, 'total_exp': 62000, 'strength': 135, 'agility': 120 - 10, 'max_hp': 200, 'max_mp': 190 - 17, 'spell': None},
            30: {'exp': 3535, 'total_exp': 65535, 'strength': 140, 'agility': 130 - 11, 'max_hp': 210, 'max_mp': 200 - 18, 'spell': None},

        }
        self.mock_levels_list_10 = {
            1: {'exp': 0, 'total_exp': 0, 'strength': 4 + 1, 'agility': 4, 'max_hp': 15, 'max_mp': 0, 'spell': None},
            2: {'exp': 7, 'total_exp': 7, 'strength': 5 + 1, 'agility': 4, 'max_hp': 22 - 1, 'max_mp': 0, 'spell': None},
            3: {'exp': 16, 'total_exp': 23, 'strength': 7 + 1, 'agility': 6, 'max_hp': 24 - 1, 'max_mp': 5, 'spell': "HEAL"},
            4: {'exp': 24, 'total_exp': 47, 'strength': 7 + 1, 'agility': 8, 'max_hp': 31 - 2, 'max_mp': 16, 'spell': "HURT"},
            5: {'exp': 63, 'total_exp': 110, 'strength': 12, 'agility': 10, 'max_hp': 35 - 2, 'max_mp': 20, 'spell': None},
            6: {'exp': 110, 'total_exp': 220, 'strength': 16, 'agility': 10, 'max_hp': 38 - 2, 'max_mp': 24, 'spell': None},
            7: {'exp': 230, 'total_exp': 450, 'strength': 18, 'agility': 17, 'max_hp': 40 - 2, 'max_mp': 26, 'spell': "SLEEP"},
            8: {'exp': 350, 'total_exp': 800, 'strength': 22 - 1, 'agility': 20, 'max_hp': 46 - 3, 'max_mp': 29, 'spell': None},
            9: {'exp': 500, 'total_exp': 1300, 'strength': 30 - 1, 'agility': 22, 'max_hp': 50 - 3, 'max_mp': 36, 'spell': "RADIANT"},
            10: {'exp': 700, 'total_exp': 2000, 'strength': 35 - 2, 'agility': 31, 'max_hp': 54 - 4, 'max_mp': 40, 'spell': "STOPSPELL"},
            11: {'exp': 900, 'total_exp': 2900, 'strength': 40 - 2, 'agility': 35, 'max_hp': 62 - 5, 'max_mp': 50, 'spell': None},
            12: {'exp': 1100, 'total_exp': 4000, 'strength': 48 - 3, 'agility': 40, 'max_hp': 63 - 5, 'max_mp': 58, 'spell': "OUTSIDE"},
            13: {'exp': 1500, 'total_exp': 5500, 'strength': 52 - 4, 'agility': 48, 'max_hp': 70 - 5, 'max_mp': 64, 'spell': "RETURN"},
            14: {'exp': 2000, 'total_exp': 7500, 'strength': 60 - 4, 'agility': 55, 'max_hp': 78 - 6, 'max_mp': 70, 'spell': None},
            15: {'exp': 2500, 'total_exp': 10000, 'strength': 68 - 5, 'agility': 64, 'max_hp': 86 - 7, 'max_mp': 72, 'spell': "REPEL"},
            16: {'exp': 3000, 'total_exp': 13000, 'strength': 72 - 6, 'agility': 70, 'max_hp': 92 - 8, 'max_mp': 95, 'spell': None},
            17: {'exp': 3000, 'total_exp': 16000, 'strength': 72 - 6, 'agility': 78, 'max_hp': 100 - 8, 'max_mp': 100, 'spell': "HEALMORE"},
            18: {'exp': 3000, 'total_exp': 19000, 'strength': 85 - 7, 'agility': 84, 'max_hp': 115 - 10, 'max_mp': 108, 'spell': None},
            19: {'exp': 3000, 'total_exp': 22000, 'strength': 87 - 7, 'agility': 86, 'max_hp': 130 - 11, 'max_mp': 115, 'spell': "HURTMORE"},
            20: {'exp': 4000, 'total_exp': 26000, 'strength': 92 - 8, 'agility': 88, 'max_hp': 138 - 12, 'max_mp': 128, 'spell': None},
            21: {'exp': 4000, 'total_exp': 30000, 'strength': 95 - 8, 'agility': 90, 'max_hp': 149 - 13, 'max_mp': 135, 'spell': None},
            22: {'exp': 4000, 'total_exp': 34000, 'strength': 97 - 8, 'agility': 90, 'max_hp': 158 - 14, 'max_mp': 146, 'spell': None},
            23: {'exp': 4000, 'total_exp': 38000, 'strength': 99 - 8, 'agility': 94, 'max_hp': 165 - 15, 'max_mp': 153, 'spell': None},
            24: {'exp': 4000, 'total_exp': 42000, 'strength': 103 - 9, 'agility': 98, 'max_hp': 170 - 15, 'max_mp': 161, 'spell': None},
            25: {'exp': 4000, 'total_exp': 46000, 'strength': 113 - 10, 'agility': 100, 'max_hp': 174 - 16, 'max_mp': 161, 'spell': None},
            26: {'exp': 4000, 'total_exp': 50000, 'strength': 117 - 10, 'agility': 105, 'max_hp': 180 - 16, 'max_mp': 168, 'spell': None},
            27: {'exp': 4000, 'total_exp': 54000, 'strength': 125 - 11, 'agility': 107, 'max_hp': 189 - 17, 'max_mp': 175, 'spell': None},
            28: {'exp': 4000, 'total_exp': 58000, 'strength': 130 - 11, 'agility': 115, 'max_hp': 195 - 18, 'max_mp': 180, 'spell': None},
            29: {'exp': 4000, 'total_exp': 62000, 'strength': 135 - 12, 'agility': 120, 'max_hp': 200 - 18, 'max_mp': 190, 'spell': None},
            30: {'exp': 3535, 'total_exp': 65535, 'strength': 140 - 12, 'agility': 130, 'max_hp': 210 - 19, 'max_mp': 200, 'spell': None},

        }
        self.mock_levels_list_11 = {
            1: {'exp': 0, 'total_exp': 0, 'strength': 4, 'agility': 4, 'max_hp': 15, 'max_mp': 0, 'spell': None},
            2: {'exp': 7, 'total_exp': 7, 'strength': 5, 'agility': 4, 'max_hp': 22 - 1, 'max_mp': 0, 'spell': None},
            3: {'exp': 16, 'total_exp': 23, 'strength': 7, 'agility': 6, 'max_hp': 24 - 1, 'max_mp': 5 + 1, 'spell': "HEAL"},
            4: {'exp': 24, 'total_exp': 47, 'strength': 7, 'agility': 8, 'max_hp': 31 - 2, 'max_mp': 16, 'spell': "HURT"},
            5: {'exp': 63, 'total_exp': 110, 'strength': 12, 'agility': 10, 'max_hp': 35 - 2, 'max_mp': 20, 'spell': None},
            6: {'exp': 110, 'total_exp': 220, 'strength': 16, 'agility': 10, 'max_hp': 38 - 2, 'max_mp': 24 - 1, 'spell': None},
            7: {'exp': 230, 'total_exp': 450, 'strength': 18, 'agility': 17, 'max_hp': 40 - 2, 'max_mp': 26 - 1, 'spell': "SLEEP"},
            8: {'exp': 350, 'total_exp': 800, 'strength': 22, 'agility': 20, 'max_hp': 46 - 3, 'max_mp': 29 - 1, 'spell': None},
            9: {'exp': 500, 'total_exp': 1300, 'strength': 30, 'agility': 22, 'max_hp': 50 - 3, 'max_mp': 36 - 2, 'spell': "RADIANT"},
            10: {'exp': 700, 'total_exp': 2000, 'strength': 35, 'agility': 31, 'max_hp': 54 - 4, 'max_mp': 40 - 2, 'spell': "STOPSPELL"},
            11: {'exp': 900, 'total_exp': 2900, 'strength': 40, 'agility': 35, 'max_hp': 62 - 5, 'max_mp': 50 - 3, 'spell': None},
            12: {'exp': 1100, 'total_exp': 4000, 'strength': 48, 'agility': 40, 'max_hp': 63 - 5, 'max_mp': 58 - 4, 'spell': "OUTSIDE"},
            13: {'exp': 1500, 'total_exp': 5500, 'strength': 52, 'agility': 48, 'max_hp': 70 - 5, 'max_mp': 64 - 5, 'spell': "RETURN"},
            14: {'exp': 2000, 'total_exp': 7500, 'strength': 60, 'agility': 55, 'max_hp': 78 - 6, 'max_mp': 70 - 5, 'spell': None},
            15: {'exp': 2500, 'total_exp': 10000, 'strength': 68, 'agility': 64, 'max_hp': 86 - 7, 'max_mp': 72 - 6, 'spell': "REPEL"},
            16: {'exp': 3000, 'total_exp': 13000, 'strength': 72, 'agility': 70, 'max_hp': 92 - 8, 'max_mp': 95 - 8, 'spell': None},
            17: {'exp': 3000, 'total_exp': 16000, 'strength': 72, 'agility': 78, 'max_hp': 100 - 8, 'max_mp': 100 - 8, 'spell': "HEALMORE"},
            18: {'exp': 3000, 'total_exp': 19000, 'strength': 85, 'agility': 84, 'max_hp': 115 - 10, 'max_mp': 108 - 9, 'spell': None},
            19: {'exp': 3000, 'total_exp': 22000, 'strength': 87, 'agility': 86, 'max_hp': 130 - 11, 'max_mp': 115 - 10, 'spell': "HURTMORE"},
            20: {'exp': 4000, 'total_exp': 26000, 'strength': 92, 'agility': 88, 'max_hp': 138 - 12, 'max_mp': 128 - 11, 'spell': None},
            21: {'exp': 4000, 'total_exp': 30000, 'strength': 95, 'agility': 90, 'max_hp': 149 - 13, 'max_mp': 135 - 12, 'spell': None},
            22: {'exp': 4000, 'total_exp': 34000, 'strength': 97, 'agility': 90, 'max_hp': 158 - 14, 'max_mp': 146 - 13, 'spell': None},
            23: {'exp': 4000, 'total_exp': 38000, 'strength': 99, 'agility': 94, 'max_hp': 165 - 15, 'max_mp': 153 - 14, 'spell': None},
            24: {'exp': 4000, 'total_exp': 42000, 'strength': 103, 'agility': 98, 'max_hp': 170 - 15, 'max_mp': 161 - 15, 'spell': None},
            25: {'exp': 4000, 'total_exp': 46000, 'strength': 113, 'agility': 100, 'max_hp': 174 - 16, 'max_mp': 161 - 15, 'spell': None},
            26: {'exp': 4000, 'total_exp': 50000, 'strength': 117, 'agility': 105, 'max_hp': 180 - 16, 'max_mp': 168 - 15, 'spell': None},
            27: {'exp': 4000, 'total_exp': 54000, 'strength': 125, 'agility': 107, 'max_hp': 189 - 17, 'max_mp': 175 - 16, 'spell': None},
            28: {'exp': 4000, 'total_exp': 58000, 'strength': 130, 'agility': 115, 'max_hp': 195 - 18, 'max_mp': 180 - 16, 'spell': None},
            29: {'exp': 4000, 'total_exp': 62000, 'strength': 135, 'agility': 120, 'max_hp': 200 - 18, 'max_mp': 190 - 17, 'spell': None},
            30: {'exp': 3535, 'total_exp': 65535, 'strength': 140, 'agility': 130, 'max_hp': 210 - 19, 'max_mp': 200 - 18, 'spell': None},

        }
        self.mock_levels_list_12 = {
            1: {'exp': 0, 'total_exp': 0, 'strength': 4 + 2, 'agility': 4 + 2, 'max_hp': 15, 'max_mp': 0, 'spell': None},
            2: {'exp': 7, 'total_exp': 7, 'strength': 5 + 2, 'agility': 4 + 2, 'max_hp': 22, 'max_mp': 0, 'spell': None},
            3: {'exp': 16, 'total_exp': 23, 'strength': 7 + 2, 'agility': 6 + 2, 'max_hp': 24, 'max_mp': 5, 'spell': "HEAL"},
            4: {'exp': 24, 'total_exp': 47, 'strength': 7 + 2, 'agility': 8 + 2, 'max_hp': 31, 'max_mp': 16, 'spell': "HURT"},
            5: {'exp': 63, 'total_exp': 110, 'strength': 12 + 1, 'agility': 10 + 2, 'max_hp': 35, 'max_mp': 20, 'spell': None},
            6: {'exp': 110, 'total_exp': 220, 'strength': 16 + 1, 'agility': 10 + 2, 'max_hp': 38, 'max_mp': 24, 'spell': None},
            7: {'exp': 230, 'total_exp': 450, 'strength': 18 + 1, 'agility': 17 + 1, 'max_hp': 40, 'max_mp': 26, 'spell': "SLEEP"},
            8: {'exp': 350, 'total_exp': 800, 'strength': 22, 'agility': 20 + 1, 'max_hp': 46, 'max_mp': 29, 'spell': None},
            9: {'exp': 500, 'total_exp': 1300, 'strength': 30, 'agility': 22, 'max_hp': 50, 'max_mp': 36, 'spell': "RADIANT"},
            10: {'exp': 700, 'total_exp': 2000, 'strength': 35 - 1, 'agility': 31 - 1, 'max_hp': 54, 'max_mp': 40, 'spell': "STOPSPELL"},
            11: {'exp': 900, 'total_exp': 2900, 'strength': 40 - 1, 'agility': 35 - 1, 'max_hp': 62, 'max_mp': 50, 'spell': None},
            12: {'exp': 1100, 'total_exp': 4000, 'strength': 48 - 2, 'agility': 40 - 1, 'max_hp': 63, 'max_mp': 58, 'spell': "OUTSIDE"},
            13: {'exp': 1500, 'total_exp': 5500, 'strength': 52 - 3, 'agility': 48 - 2, 'max_hp': 70, 'max_mp': 64, 'spell': "RETURN"},
            14: {'exp': 2000, 'total_exp': 7500, 'strength': 60 - 3, 'agility': 55 - 3, 'max_hp': 78, 'max_mp': 70, 'spell': None},
            15: {'exp': 2500, 'total_exp': 10000, 'strength': 68 - 4, 'agility': 64 - 4, 'max_hp': 86, 'max_mp': 72, 'spell': "REPEL"},
            16: {'exp': 3000, 'total_exp': 13000, 'strength': 72 - 5, 'agility': 70 - 4, 'max_hp': 92, 'max_mp': 95, 'spell': None},
            17: {'exp': 3000, 'total_exp': 16000, 'strength': 72 - 5, 'agility': 78 - 5, 'max_hp': 100, 'max_mp': 100, 'spell': "HEALMORE"},
            18: {'exp': 3000, 'total_exp': 19000, 'strength': 85 - 6, 'agility': 84 - 6, 'max_hp': 115, 'max_mp': 108, 'spell': None},
            19: {'exp': 3000, 'total_exp': 22000, 'strength': 87 - 6, 'agility': 86 - 6, 'max_hp': 130, 'max_mp': 115, 'spell': "HURTMORE"},
            20: {'exp': 4000, 'total_exp': 26000, 'strength': 92 - 7, 'agility': 88 - 6, 'max_hp': 138, 'max_mp': 128, 'spell': None},
            21: {'exp': 4000, 'total_exp': 30000, 'strength': 95 - 7, 'agility': 90 - 6, 'max_hp': 149, 'max_mp': 135, 'spell': None},
            22: {'exp': 4000, 'total_exp': 34000, 'strength': 97 - 7, 'agility': 90 - 6, 'max_hp': 158, 'max_mp': 146, 'spell': None},
            23: {'exp': 4000, 'total_exp': 38000, 'strength': 99 - 7, 'agility': 94 - 7, 'max_hp': 165, 'max_mp': 153, 'spell': None},
            24: {'exp': 4000, 'total_exp': 42000, 'strength': 103 - 8, 'agility': 98 - 7, 'max_hp': 170, 'max_mp': 161, 'spell': None},
            25: {'exp': 4000, 'total_exp': 46000, 'strength': 113 - 9, 'agility': 100 - 7, 'max_hp': 174, 'max_mp': 161, 'spell': None},
            26: {'exp': 4000, 'total_exp': 50000, 'strength': 117 - 9, 'agility': 105 - 8, 'max_hp': 180, 'max_mp': 168, 'spell': None},
            27: {'exp': 4000, 'total_exp': 54000, 'strength': 125 - 10, 'agility': 107 - 8, 'max_hp': 189, 'max_mp': 175, 'spell': None},
            28: {'exp': 4000, 'total_exp': 58000, 'strength': 130 - 10, 'agility': 115 - 9, 'max_hp': 195, 'max_mp': 180, 'spell': None},
            29: {'exp': 4000, 'total_exp': 62000, 'strength': 135 - 11, 'agility': 120 - 9, 'max_hp': 200, 'max_mp': 190, 'spell': None},
            30: {'exp': 3535, 'total_exp': 65535, 'strength': 140 - 11, 'agility': 130 - 10, 'max_hp': 210, 'max_mp': 200, 'spell': None},

        }
        self.mock_levels_list_13 = {
            1: {'exp': 0, 'total_exp': 0, 'strength': 4, 'agility': 4 + 2, 'max_hp': 15, 'max_mp': 0, 'spell': None},
            2: {'exp': 7, 'total_exp': 7, 'strength': 5, 'agility': 4 + 2, 'max_hp': 22, 'max_mp': 0, 'spell': None},
            3: {'exp': 16, 'total_exp': 23, 'strength': 7, 'agility': 6 + 2, 'max_hp': 24, 'max_mp': 5 + 2, 'spell': "HEAL"},
            4: {'exp': 24, 'total_exp': 47, 'strength': 7, 'agility': 8 + 2, 'max_hp': 31, 'max_mp': 16 + 1, 'spell': "HURT"},
            5: {'exp': 63, 'total_exp': 110, 'strength': 12, 'agility': 10 + 2, 'max_hp': 35, 'max_mp': 20 + 1, 'spell': None},
            6: {'exp': 110, 'total_exp': 220, 'strength': 16, 'agility': 10 + 2, 'max_hp': 38, 'max_mp': 24, 'spell': None},
            7: {'exp': 230, 'total_exp': 450, 'strength': 18, 'agility': 17 + 1, 'max_hp': 40, 'max_mp': 26, 'spell': "SLEEP"},
            8: {'exp': 350, 'total_exp': 800, 'strength': 22, 'agility': 20 + 1, 'max_hp': 46, 'max_mp': 29, 'spell': None},
            9: {'exp': 500, 'total_exp': 1300, 'strength': 30, 'agility': 22, 'max_hp': 50, 'max_mp': 36 - 1, 'spell': "RADIANT"},
            10: {'exp': 700, 'total_exp': 2000, 'strength': 35, 'agility': 31 - 1, 'max_hp': 54, 'max_mp': 40 - 1, 'spell': "STOPSPELL"},
            11: {'exp': 900, 'total_exp': 2900, 'strength': 40, 'agility': 35 - 1, 'max_hp': 62, 'max_mp': 50 - 2, 'spell': None},
            12: {'exp': 1100, 'total_exp': 4000, 'strength': 48, 'agility': 40 - 1, 'max_hp': 63, 'max_mp': 58 - 3, 'spell': "OUTSIDE"},
            13: {'exp': 1500, 'total_exp': 5500, 'strength': 52, 'agility': 48 - 2, 'max_hp': 70, 'max_mp': 64 - 4, 'spell': "RETURN"},
            14: {'exp': 2000, 'total_exp': 7500, 'strength': 60, 'agility': 55 - 3, 'max_hp': 78, 'max_mp': 70 - 4, 'spell': None},
            15: {'exp': 2500, 'total_exp': 10000, 'strength': 68, 'agility': 64 - 4, 'max_hp': 86, 'max_mp': 72 - 5, 'spell': "REPEL"},
            16: {'exp': 3000, 'total_exp': 13000, 'strength': 72, 'agility': 70 - 4, 'max_hp': 92, 'max_mp': 95 - 7, 'spell': None},
            17: {'exp': 3000, 'total_exp': 16000, 'strength': 72, 'agility': 78 - 5, 'max_hp': 100, 'max_mp': 100 - 7, 'spell': "HEALMORE"},
            18: {'exp': 3000, 'total_exp': 19000, 'strength': 85, 'agility': 84 - 6, 'max_hp': 115, 'max_mp': 108 - 8, 'spell': None},
            19: {'exp': 3000, 'total_exp': 22000, 'strength': 87, 'agility': 86 - 6, 'max_hp': 130, 'max_mp': 115 - 9, 'spell': "HURTMORE"},
            20: {'exp': 4000, 'total_exp': 26000, 'strength': 92, 'agility': 88 - 6, 'max_hp': 138, 'max_mp': 128 - 10, 'spell': None},
            21: {'exp': 4000, 'total_exp': 30000, 'strength': 95, 'agility': 90 - 6, 'max_hp': 149, 'max_mp': 135 - 11, 'spell': None},
            22: {'exp': 4000, 'total_exp': 34000, 'strength': 97, 'agility': 90 - 6, 'max_hp': 158, 'max_mp': 146 - 12, 'spell': None},
            23: {'exp': 4000, 'total_exp': 38000, 'strength': 99, 'agility': 94 - 7, 'max_hp': 165, 'max_mp': 153 - 13, 'spell': None},
            24: {'exp': 4000, 'total_exp': 42000, 'strength': 103, 'agility': 98 - 7, 'max_hp': 170, 'max_mp': 161 - 14, 'spell': None},
            25: {'exp': 4000, 'total_exp': 46000, 'strength': 113, 'agility': 100 - 7, 'max_hp': 174, 'max_mp': 161 - 14, 'spell': None},
            26: {'exp': 4000, 'total_exp': 50000, 'strength': 117, 'agility': 105 - 8, 'max_hp': 180, 'max_mp': 168 - 14, 'spell': None},
            27: {'exp': 4000, 'total_exp': 54000, 'strength': 125, 'agility': 107 - 8, 'max_hp': 189, 'max_mp': 175 - 15, 'spell': None},
            28: {'exp': 4000, 'total_exp': 58000, 'strength': 130, 'agility': 115 - 9, 'max_hp': 195, 'max_mp': 180 - 15, 'spell': None},
            29: {'exp': 4000, 'total_exp': 62000, 'strength': 135, 'agility': 120 - 9, 'max_hp': 200, 'max_mp': 190 - 16, 'spell': None},
            30: {'exp': 3535, 'total_exp': 65535, 'strength': 140, 'agility': 130 - 10, 'max_hp': 210, 'max_mp': 200 - 17, 'spell': None},

        }
        self.mock_levels_list_14 = {
            1: {'exp': 0, 'total_exp': 0, 'strength': 4 + 2, 'agility': 4, 'max_hp': 15 + 1, 'max_mp': 0, 'spell': None},
            2: {'exp': 7, 'total_exp': 7, 'strength': 5 + 2, 'agility': 4, 'max_hp': 22, 'max_mp': 0, 'spell': None},
            3: {'exp': 16, 'total_exp': 23, 'strength': 7 + 2, 'agility': 6, 'max_hp': 24, 'max_mp': 5, 'spell': "HEAL"},
            4: {'exp': 24, 'total_exp': 47, 'strength': 7 + 2, 'agility': 8, 'max_hp': 31 - 1, 'max_mp': 16, 'spell': "HURT"},
            5: {'exp': 63, 'total_exp': 110, 'strength': 12 + 1, 'agility': 10, 'max_hp': 35 - 1, 'max_mp': 20, 'spell': None},
            6: {'exp': 110, 'total_exp': 220, 'strength': 16 + 1, 'agility': 10, 'max_hp': 38 - 1, 'max_mp': 24, 'spell': None},
            7: {'exp': 230, 'total_exp': 450, 'strength': 18 + 1, 'agility': 17, 'max_hp': 40 - 1, 'max_mp': 26, 'spell': "SLEEP"},
            8: {'exp': 350, 'total_exp': 800, 'strength': 22, 'agility': 20, 'max_hp': 46 - 2, 'max_mp': 29, 'spell': None},
            9: {'exp': 500, 'total_exp': 1300, 'strength': 30, 'agility': 22, 'max_hp': 50 - 2, 'max_mp': 36, 'spell': "RADIANT"},
            10: {'exp': 700, 'total_exp': 2000, 'strength': 35 - 1, 'agility': 31, 'max_hp': 54 - 3, 'max_mp': 40, 'spell': "STOPSPELL"},
            11: {'exp': 900, 'total_exp': 2900, 'strength': 40 - 1, 'agility': 35, 'max_hp': 62 - 4, 'max_mp': 50, 'spell': None},
            12: {'exp': 1100, 'total_exp': 4000, 'strength': 48 - 2, 'agility': 40, 'max_hp': 63 - 4, 'max_mp': 58, 'spell': "OUTSIDE"},
            13: {'exp': 1500, 'total_exp': 5500, 'strength': 52 - 3, 'agility': 48, 'max_hp': 70 - 4, 'max_mp': 64, 'spell': "RETURN"},
            14: {'exp': 2000, 'total_exp': 7500, 'strength': 60 - 3, 'agility': 55, 'max_hp': 78 - 5, 'max_mp': 70, 'spell': None},
            15: {'exp': 2500, 'total_exp': 10000, 'strength': 68 - 4, 'agility': 64, 'max_hp': 86 - 6, 'max_mp': 72, 'spell': "REPEL"},
            16: {'exp': 3000, 'total_exp': 13000, 'strength': 72 - 5, 'agility': 70, 'max_hp': 92 - 7, 'max_mp': 95, 'spell': None},
            17: {'exp': 3000, 'total_exp': 16000, 'strength': 72 - 5, 'agility': 78, 'max_hp': 100 - 7, 'max_mp': 100, 'spell': "HEALMORE"},
            18: {'exp': 3000, 'total_exp': 19000, 'strength': 85 - 6, 'agility': 84, 'max_hp': 115 - 9, 'max_mp': 108, 'spell': None},
            19: {'exp': 3000, 'total_exp': 22000, 'strength': 87 - 6, 'agility': 86, 'max_hp': 130 - 10, 'max_mp': 115, 'spell': "HURTMORE"},
            20: {'exp': 4000, 'total_exp': 26000, 'strength': 92 - 7, 'agility': 88, 'max_hp': 138 - 11, 'max_mp': 128, 'spell': None},
            21: {'exp': 4000, 'total_exp': 30000, 'strength': 95 - 7, 'agility': 90, 'max_hp': 149 - 12, 'max_mp': 135, 'spell': None},
            22: {'exp': 4000, 'total_exp': 34000, 'strength': 97 - 7, 'agility': 90, 'max_hp': 158 - 13, 'max_mp': 146, 'spell': None},
            23: {'exp': 4000, 'total_exp': 38000, 'strength': 99 - 7, 'agility': 94, 'max_hp': 165 - 14, 'max_mp': 153, 'spell': None},
            24: {'exp': 4000, 'total_exp': 42000, 'strength': 103 - 8, 'agility': 98, 'max_hp': 170 - 14, 'max_mp': 161, 'spell': None},
            25: {'exp': 4000, 'total_exp': 46000, 'strength': 113 - 9, 'agility': 100, 'max_hp': 174 - 15, 'max_mp': 161, 'spell': None},
            26: {'exp': 4000, 'total_exp': 50000, 'strength': 117 - 9, 'agility': 105, 'max_hp': 180 - 15, 'max_mp': 168, 'spell': None},
            27: {'exp': 4000, 'total_exp': 54000, 'strength': 125 - 10, 'agility': 107, 'max_hp': 189 - 16, 'max_mp': 175, 'spell': None},
            28: {'exp': 4000, 'total_exp': 58000, 'strength': 130 - 10, 'agility': 115, 'max_hp': 195 - 17, 'max_mp': 180, 'spell': None},
            29: {'exp': 4000, 'total_exp': 62000, 'strength': 135 - 11, 'agility': 120, 'max_hp': 200 - 17, 'max_mp': 190, 'spell': None},
            30: {'exp': 3535, 'total_exp': 65535, 'strength': 140 - 11, 'agility': 130, 'max_hp': 210 - 18, 'max_mp': 200, 'spell': None},

        }
        self.mock_levels_list_15 = {
            1: {'exp': 0, 'total_exp': 0, 'strength': 4, 'agility': 4, 'max_hp': 15 + 1, 'max_mp': 0, 'spell': None},
            2: {'exp': 7, 'total_exp': 7, 'strength': 5, 'agility': 4, 'max_hp': 22, 'max_mp': 0, 'spell': None},
            3: {'exp': 16, 'total_exp': 23, 'strength': 7, 'agility': 6, 'max_hp': 24, 'max_mp': 5 + 2, 'spell': "HEAL"},
            4: {'exp': 24, 'total_exp': 47, 'strength': 7, 'agility': 8, 'max_hp': 31 - 1, 'max_mp': 16 + 1, 'spell': "HURT"},
            5: {'exp': 63, 'total_exp': 110, 'strength': 12, 'agility': 10, 'max_hp': 35 - 1, 'max_mp': 20 + 1, 'spell': None},
            6: {'exp': 110, 'total_exp': 220, 'strength': 16, 'agility': 10, 'max_hp': 38 - 1, 'max_mp': 24, 'spell': None},
            7: {'exp': 230, 'total_exp': 450, 'strength': 18, 'agility': 17, 'max_hp': 40 - 1, 'max_mp': 26, 'spell': "SLEEP"},
            8: {'exp': 350, 'total_exp': 800, 'strength': 22, 'agility': 20, 'max_hp': 46 - 2, 'max_mp': 29, 'spell': None},
            9: {'exp': 500, 'total_exp': 1300, 'strength': 30, 'agility': 22, 'max_hp': 50 - 2, 'max_mp': 36 - 1, 'spell': "RADIANT"},
            10: {'exp': 700, 'total_exp': 2000, 'strength': 35, 'agility': 31, 'max_hp': 54 - 3, 'max_mp': 40 - 1, 'spell': "STOPSPELL"},
            11: {'exp': 900, 'total_exp': 2900, 'strength': 40, 'agility': 35, 'max_hp': 62 - 4, 'max_mp': 50 - 2, 'spell': None},
            12: {'exp': 1100, 'total_exp': 4000, 'strength': 48, 'agility': 40, 'max_hp': 63 - 4, 'max_mp': 58 - 3, 'spell': "OUTSIDE"},
            13: {'exp': 1500, 'total_exp': 5500, 'strength': 52, 'agility': 48, 'max_hp': 70 - 4, 'max_mp': 64 - 4, 'spell': "RETURN"},
            14: {'exp': 2000, 'total_exp': 7500, 'strength': 60, 'agility': 55, 'max_hp': 78 - 5, 'max_mp': 70 - 4, 'spell': None},
            15: {'exp': 2500, 'total_exp': 10000, 'strength': 68, 'agility': 64, 'max_hp': 86 - 6, 'max_mp': 72 - 5, 'spell': "REPEL"},
            16: {'exp': 3000, 'total_exp': 13000, 'strength': 72, 'agility': 70, 'max_hp': 92 - 7, 'max_mp': 95 - 7, 'spell': None},
            17: {'exp': 3000, 'total_exp': 16000, 'strength': 72, 'agility': 78, 'max_hp': 100 - 7, 'max_mp': 100 - 7, 'spell': "HEALMORE"},
            18: {'exp': 3000, 'total_exp': 19000, 'strength': 85, 'agility': 84, 'max_hp': 115 - 9, 'max_mp': 108 - 8, 'spell': None},
            19: {'exp': 3000, 'total_exp': 22000, 'strength': 87, 'agility': 86, 'max_hp': 130 - 10, 'max_mp': 115 - 9, 'spell': "HURTMORE"},
            20: {'exp': 4000, 'total_exp': 26000, 'strength': 92, 'agility': 88, 'max_hp': 138 - 11, 'max_mp': 128 - 10, 'spell': None},
            21: {'exp': 4000, 'total_exp': 30000, 'strength': 95, 'agility': 90, 'max_hp': 149 - 12, 'max_mp': 135 - 11, 'spell': None},
            22: {'exp': 4000, 'total_exp': 34000, 'strength': 97, 'agility': 90, 'max_hp': 158 - 13, 'max_mp': 146 - 12, 'spell': None},
            23: {'exp': 4000, 'total_exp': 38000, 'strength': 99, 'agility': 94, 'max_hp': 165 - 14, 'max_mp': 153 - 13, 'spell': None},
            24: {'exp': 4000, 'total_exp': 42000, 'strength': 103, 'agility': 98, 'max_hp': 170 - 14, 'max_mp': 161 - 14, 'spell': None},
            25: {'exp': 4000, 'total_exp': 46000, 'strength': 113, 'agility': 100, 'max_hp': 174 - 15, 'max_mp': 161 - 14, 'spell': None},
            26: {'exp': 4000, 'total_exp': 50000, 'strength': 117, 'agility': 105, 'max_hp': 180 - 15, 'max_mp': 168 - 14, 'spell': None},
            27: {'exp': 4000, 'total_exp': 54000, 'strength': 125, 'agility': 107, 'max_hp': 189 - 16, 'max_mp': 175 - 15, 'spell': None},
            28: {'exp': 4000, 'total_exp': 58000, 'strength': 130, 'agility': 115, 'max_hp': 195 - 17, 'max_mp': 180 - 15, 'spell': None},
            29: {'exp': 4000, 'total_exp': 62000, 'strength': 135, 'agility': 120, 'max_hp': 200 - 17, 'max_mp': 190 - 16, 'spell': None},
            30: {'exp': 3535, 'total_exp': 65535, 'strength': 140, 'agility': 130, 'max_hp': 210 - 18, 'max_mp': 200 - 17, 'spell': None},

        }

    def test_get_total_name_score(self):
        self.assertEqual(31, get_total_name_score("Edward"))
        self.assertEqual(36, get_total_name_score("Eddie"))
        self.assertEqual(43, get_total_name_score("James"))

    def test_get_bonus(self):
        self.assertEqual(0, get_bonus(33))
        self.assertEqual(1, get_bonus(52))
        self.assertEqual(2, get_bonus(43))
        self.assertEqual(3, get_bonus(31))

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

    def test_apply_transformation_to_levels_list_0(self):
        """Strength and Agility penalized.
        Example name: Steve
        """
        apply_transformation_to_levels_list("Steve")
        self.assertEqual(self.mock_levels_list_0, levels_list)

    def test_apply_transformation_to_levels_list_1(self):
        """Agility and Maximum MP penalized.
        Example name: Eva
        """
        apply_transformation_to_levels_list("Eva")
        self.assertEqual(self.mock_levels_list_1, levels_list)

    def test_apply_transformation_to_levels_list_2(self):
        """Strength and Maximum HP penalized.
        Example name: Im
        """
        apply_transformation_to_levels_list("Im")
        self.assertEqual(self.mock_levels_list_2, levels_list)

    def test_apply_transformation_to_levels_list_3(self):
        """Strength and Maximum HP penalized.
        Example name: Va
        """
        apply_transformation_to_levels_list("Va")
        self.assertEqual(self.mock_levels_list_3, levels_list)

    def test_apply_transformation_to_levels_list_4(self):
        """Strength and Agility penalized.
        Example name: Eddie
        """
        apply_transformation_to_levels_list("Eddie")
        self.assertEqual(self.mock_levels_list_4, levels_list)

    def test_apply_transformation_to_levels_list_5(self):
        """Agility and Maximum MP penalized.
        Example name: Ed
        """
        apply_transformation_to_levels_list("Ed")
        self.assertEqual(self.mock_levels_list_5, levels_list)

    def test_apply_transformation_to_levels_list_6(self):
        """Strength and Maximum HP penalized.
        Example name: Walter
        """
        apply_transformation_to_levels_list("Walter")
        self.assertEqual(self.mock_levels_list_6, levels_list)

    def test_apply_transformation_to_levels_list_7(self):
        """Maximum HP and Maximum MP penalized.
        Example name: Uno
        """
        apply_transformation_to_levels_list("Uno")
        self.assertEqual(self.mock_levels_list_7, levels_list)

    def test_apply_transformation_to_levels_list_8(self):
        """Maximum HP and Maximum MP penalized.
        Example name: gooo
        """
        apply_transformation_to_levels_list("gooo")
        self.assertEqual(self.mock_levels_list_8, levels_list)

    def test_apply_transformation_to_levels_list_9(self):
        """Strength and Agility penalized.
        Example name: Sejin
        """
        apply_transformation_to_levels_list("Sejin")
        self.assertEqual(self.mock_levels_list_9, levels_list)

    def test_apply_transformation_to_levels_list_10(self):
        """Strength and Maximum HP penalized.
        Example name: Stephen
        """
        apply_transformation_to_levels_list("Stephen")
        self.assertEqual(self.mock_levels_list_10, levels_list)

    def test_apply_transformation_to_levels_list_11(self):
        """Maximum HP and Maximum MP penalized.
        Example name: James
        """
        apply_transformation_to_levels_list("James")
        self.assertEqual(self.mock_levels_list_11, levels_list)

    def test_apply_transformation_to_levels_list_12(self):
        """Strength and Agility penalized.
        Example name: Gao
        """
        apply_transformation_to_levels_list("Gao")
        self.assertEqual(self.mock_levels_list_12, levels_list)

    def test_apply_transformation_to_levels_list_13(self):
        """Agility and Maximum MP penalized.
        Example name: Jacquie / Gina
        """
        apply_transformation_to_levels_list("Jacquie")
        self.assertEqual(self.mock_levels_list_13, levels_list)

    def test_apply_transformation_to_levels_list_14(self):
        """Strength and Maximum HP penalized.
        Example name: Wall
        """
        apply_transformation_to_levels_list("Wall")
        self.assertEqual(self.mock_levels_list_14, levels_list)

    def test_apply_transformation_to_levels_list_15(self):
        """Maximum HP and Maximum MP penalized.
        Example name: Edward / Larry / Joseph
        """
        apply_transformation_to_levels_list("Edward")
        self.assertEqual(self.mock_levels_list_15, levels_list)
