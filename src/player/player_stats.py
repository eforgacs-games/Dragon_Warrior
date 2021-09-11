from math import floor

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

# may not need this anymore
initial_stats_chart = {
    # keys are remainders after calculating using the letter_calculations chart
    # probably best to use https://www.woodus.com/den/games/web/dwsim/calc.htm to calculate initial stats for each name on the side
    # example names commented on side
    0: {"max_hp": 15, "max_mp": 0, "strength": 3, "agility": 3, "attack": 3, "defense": 1, "growth": "A"},  # "ma", "Steve"
    1: {"max_hp": 15, "max_mp": 0, "strength": 4, "agility": 3, "attack": 4, "defense": 1, "growth": "B"},  # "na", "Eva"
    2: {"max_hp": 13, "max_mp": 0, "strength": 3, "agility": 4, "attack": 3, "defense": 2, "growth": "C"},  # "Im"
    3: {"max_hp": 13, "max_mp": 0, "strength": 4, "agility": 4, "attack": 4, "defense": 2, "growth": "D"},  # "Va",
    4: {"max_hp": 15, "max_mp": 0, "strength": 4, "agility": 4, "attack": 4, "defense": 2, "growth": "A"},  # "Ga", "Eddie", "Justin", "Lawrence"
    5: {"max_hp": 15, "max_mp": 0, "strength": 4, "agility": 4, "attack": 4, "defense": 2, "growth": "B"},  # "Ed", "Joey"
    6: {"max_hp": 14, "max_mp": 0, "strength": 4, "agility": 4, "attack": 4, "defense": 2, "growth": "C"},  # "TED", "Walter"
    7: {"max_hp": 14, "max_mp": 0, "strength": 4, "agility": 4, "attack": 4, "defense": 2, "growth": "D"},  # "Uno", "Eon"
    8: {"max_hp": 15, "max_mp": 0, "strength": 5, "agility": 5, "attack": 5, "defense": 2, "growth": "A"},  # "gooo"
    9: {"max_hp": 15, "max_mp": 0, "strength": 4, "agility": 5, "attack": 4, "defense": 2, "growth": "B"},  # "La", "Sejin"
    10: {"max_hp": 15, "max_mp": 0, "strength": 5, "agility": 4, "attack": 5, "defense": 2, "growth": "C"},  # "Wam", "Stephen"
    11: {"max_hp": 15, "max_mp": 0, "strength": 4, "agility": 4, "attack": 4, "defense": 2, "growth": "D"},  # "Gan", "James", "Jason"
    12: {"max_hp": 15, "max_mp": 0, "strength": 6, "agility": 6, "attack": 6, "defense": 3, "growth": "A"},  # "Gao"
    13: {"max_hp": 15, "max_mp": 0, "strength": 4, "agility": 6, "attack": 4, "defense": 3, "growth": "B"},  # "Gap", "Jacquie", "Gina"
    14: {"max_hp": 16, "max_mp": 0, "strength": 6, "agility": 4, "attack": 6, "defense": 2, "growth": "C"},  # "Wall"
    15: {"max_hp": 16, "max_mp": 0, "strength": 4, "agility": 4, "attack": 4, "defense": 2, "growth": "D"}  # "Name", "Larry", "Edward", "ED", "Joseph"
}

growth_rates = {
    "A": {"strength": 1, "agility": 2, "HP": 1, "MP": 2},
    "B": {"strength": 2, "agility": 1, "HP": 2, "MP": 1},
    "C": {"strength": 1, "agility": 1, "HP": 2, "MP": 2},
    "D": {"strength": 2, "agility": 2, "HP": 1, "MP": 1},
}


def get_remainder(name):
    total = get_total_name_score(name)
    remainder = total % 16
    return remainder


def get_total_name_score(name):
    """Gets name score based on the first four characters of the name."""
    name = name[0:4]
    total = 0
    for letter in name:
        for score, letters in letter_calculations.items():
            if letter in letters:
                total += score
                break
    return total


def get_bonus(name_score):
    return (name_score // 4) % 4


def stat_calc(bonus, base):
    return floor(base * .9) + bonus


def determine_penalized_stats(name_score):
    # TODO: Make this actually map using the binary values.
    stats_to_penalize = name_score % 4
    if stats_to_penalize == 0:
        return ['strength', 'agility']
    elif stats_to_penalize == 1:
        return ['max_mp', 'agility']
    elif stats_to_penalize == 2:
        return ['strength', 'max_hp']
    elif stats_to_penalize == 3:
        return ['max_hp', 'max_mp']
    elif stats_to_penalize == 4:
        return ['strength', 'agility']
    else:
        print("Unable to determine stats to penalize.")


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


def apply_max_mp_transformation_1():
    levels_list[3]['max_mp'] -= 1
    for i in range(4, 6):
        levels_list[i]['max_mp'] -= 2
    for i in range(6, 9):
        levels_list[i]['max_mp'] -= 3
    for i in range(9, 11):
        levels_list[i]['max_mp'] -= 4
    levels_list[11]['max_mp'] -= 5
    levels_list[12]['max_mp'] -= 6
    for i in range(13, 15):
        levels_list[i]['max_mp'] -= 7
    levels_list[15]['max_mp'] -= 8
    for i in range(16, 18):
        levels_list[i]['max_mp'] -= 10
    levels_list[18]['max_mp'] -= 11
    levels_list[19]['max_mp'] -= 12
    levels_list[20]['max_mp'] -= 13
    levels_list[21]['max_mp'] -= 14
    levels_list[22]['max_mp'] -= 15
    levels_list[23]['max_mp'] -= 16
    for i in range(24, 27):
        levels_list[i]['max_mp'] -= 17
    for i in range(27, 29):
        levels_list[i]['max_mp'] -= 18
    levels_list[29]['max_mp'] -= 19
    levels_list[30]['max_mp'] -= 20


def apply_strength_transformation_0():
    for i in range(1, 5):
        levels_list[i]['strength'] -= 1
    for i in range(5, 8):
        levels_list[i]['strength'] -= 2
    for i in range(8, 10):
        levels_list[i]['strength'] -= 3
    for i in range(10, 12):
        levels_list[i]['strength'] -= 4
    levels_list[12]['strength'] -= 5
    for i in range(13, 15):
        levels_list[i]['strength'] -= 6
    levels_list[15]['strength'] -= 7
    for i in range(16, 18):
        levels_list[i]['strength'] -= 8
    for i in range(18, 20):
        levels_list[i]['strength'] -= 9
    for i in range(20, 24):
        levels_list[i]['strength'] -= 10
    levels_list[24]['strength'] -= 11
    for i in range(25, 27):
        levels_list[i]['strength'] -= 12
    for i in range(27, 29):
        levels_list[i]['strength'] -= 13
    for i in range(29, 31):
        levels_list[i]['strength'] -= 14


def apply_agility_transformation_0_1():
    for i in range(1, 7):
        levels_list[i]['agility'] -= 1
    for i in range(7, 9):
        levels_list[i]['agility'] -= 2
    levels_list[9]['agility'] -= 3
    for i in range(10, 13):
        levels_list[i]['agility'] -= 4
    levels_list[13]['agility'] -= 5
    levels_list[14]['agility'] -= 6
    for i in range(15, 17):
        levels_list[i]['agility'] -= 7
    levels_list[17]['agility'] -= 8
    for i in range(18, 23):
        levels_list[i]['agility'] -= 9
    for i in range(23, 26):
        levels_list[i]['agility'] -= 10
    for i in range(26, 28):
        levels_list[i]['agility'] -= 11
    for i in range(28, 30):
        levels_list[i]['agility'] -= 12
    levels_list[30]['agility'] -= 13


def get_initial_stats(remainder):
    return initial_stats_chart[remainder]
