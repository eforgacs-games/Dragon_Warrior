from math import floor

# probably best to use https://www.woodus.com/den/games/web/dwsim/calc.htm to calculate initial stats for each name on the side
# example names:
# 0: "ma", "Steve"
# 1: "na", "Eva"
# 2: "Im"
# 3: "Va",
# 4: "Ga", "Eddie", "Justin", "Lawrence"
# 5: "Ed", "Joey"
# 6: "TED", "Walter"
# 7: "Uno", "Eon"
# 8: "gooo"
# 9: "La", "Sejin"
# 10: "Wam", "Stephen"
# 11: "Gan", "James", "Jason"
# 12: "Gao"
# 13: "Gap", "Jacquie", "Gina"
# 14: "Wall"
# 15: "Name", "Larry", "Edward", "ED", "Joseph"

letter_calculations = {
    0: (" ", "g", "w", "M", "'"),
    1: ("h", "x", "N"),
    2: ("i", "y", "O"),
    3: ("j", "z", "P"),
    4: ("k", "A", "Q"),
    5: ("l", "B", "R"),
    6: ("m", "C", "S"),
    7: ("n", "D", "T", "."),
    8: ("o", "E", "U", ","),
    9: ("p", "F", "V", "-"),
    10: ("a", "q", "G", "W"),
    11: ("b", "r", "H", "X", "?"),
    12: ("c", "s", "I", "Y", "!"),
    13: ("d", "t", "J", "Z"),
    14: ("e", "u", "K", ")"),
    15: ("f", "v", "L", "("),
}

levels_list = {
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


def get_total_name_score(name: str) -> int:
    """Gets name score based on the first four characters of the name."""
    name = name[0:4]
    total = 0
    for letter in name:
        for score, letters in letter_calculations.items():
            if letter in letters:
                total += score
                break
    return total


def get_bonus(name_score: int) -> int:
    return (name_score // 4) % 4


def stat_calc(bonus: int, base: int) -> int:
    return floor(base * .9) + bonus


def determine_penalized_stats(name_score: int) -> list:
    """Determine the stats to penalize based on the last four bits of the binary representation of the name score.
    if second to last bit is 0, agility is penalized.
    if second to last bit is 1, max_hp is penalized.
    if last bit is 0, strength is penalized.
    if last bit is 1, max_mp is penalized.
    """
    stats_to_penalize = name_score % 4
    num_bits = 2
    bits = [(stats_to_penalize >> bit) & 1 for bit in range(num_bits - 1, -1, -1)]
    chart_of_stats_to_penalize = ('agility', 'max_hp'), ('strength', 'max_mp')
    return [chart_of_stats_to_penalize[i][bits[i]] for i in range(len(bits))]


def apply_transformation_to_levels_list(name: str):
    # basing this on https://guides.gamercorner.net/dw/name-stats/
    total_name_score = get_total_name_score(name)
    bonus = get_bonus(total_name_score)
    penalized_stats = determine_penalized_stats(total_name_score)
    for i in range(1, len(levels_list) + 1):
        for stat in penalized_stats:
            if stat == 'max_mp' and i <= 2:
                continue
            levels_list[i][stat] = stat_calc(bonus, levels_list[i][stat])
