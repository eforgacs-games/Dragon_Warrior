from src.common import Direction
from src.items import weapons
from src.sprites.animated_sprite import AnimatedSprite

# TODO: Fix ranges to not be random integers, and instead based on the character's name.


experience_chart = {
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

initial_stats_chart = {
    # keys are remainders after calculating using the letter_calculations chart
    # example names commented on side
    0: {"strength": 3, "agility": 3, "max_hp": 15, "max_mp": 5, "growth": "A"},  # "ma", "Steve"
    1: {"strength": 4, "agility": 3, "max_hp": 15, "max_mp": 4, "growth": "B"},  # "na", "Eva"
    2: {"strength": 3, "agility": 4, "max_hp": 13, "max_mp": 5, "growth": "C"},  # "Im"
    3: {"strength": 4, "agility": 4, "max_hp": 13, "max_mp": 4, "growth": "D"},  # "Va",
    4: {"strength": 4, "agility": 4, "max_hp": 15, "max_mp": 5, "growth": "A"},  # "Ga", "Eddie", "Justin", "Lawrence"
    5: {"strength": 4, "agility": 4, "max_hp": 15, "max_mp": 5, "growth": "B"},  # "Ed", "Joey"
    6: {"strength": 4, "agility": 4, "max_hp": 14, "max_mp": 5, "growth": "C"},  # "TED", "Walter"
    7: {"strength": 4, "agility": 4, "max_hp": 14, "max_mp": 5, "growth": "D"},  # "Uno", "Eon"
    8: {"strength": 5, "agility": 5, "max_hp": 15, "max_mp": 5, "growth": "A"},  # "gooo"
    9: {"strength": 4, "agility": 5, "max_hp": 15, "max_mp": 6, "growth": "B"},  # "La", "Sejin"
    10: {"strength": 5, "agility": 4, "max_hp": 15, "max_mp": 5, "growth": "C"},  # "Wam", "Stephen"
    11: {"strength": 4, "agility": 4, "max_hp": 15, "max_mp": 6, "growth": "D"},  # "Gan", "James", "Jason"
    12: {"strength": 6, "agility": 6, "max_hp": 15, "max_mp": 5, "growth": "A"},  # "Gao"
    13: {"strength": 4, "agility": 6, "max_hp": 15, "max_mp": 7, "growth": "B"},  # "Gap", "Jacquie", "Gina"
    14: {"strength": 6, "agility": 4, "max_hp": 16, "max_mp": 5, "growth": "C"},  # "Wall"
    15: {"strength": 4, "agility": 4, "max_hp": 16, "max_mp": 7, "growth": "D"}  # "Name", "Larry", "Edward", "ED", "Joseph"
}

growth_rates = {
    "A": {"strength": 1, "agility": 2, "HP": 1, "MP": 2},
    "B": {"strength": 2, "agility": 1, "HP": 2, "MP": 1},
    "C": {"strength": 1, "agility": 1, "HP": 2, "MP": 2},
    "D": {"strength": 2, "agility": 2, "HP": 1, "MP": 1},
}


def get_remainder(name):
    name = name[0:4]
    total = 0
    for letter in name:
        for score, letters in letter_calculations.items():
            if letter in letters:
                total += score
                break
    remainder = total % 16
    return remainder


def apply_transformation_to_experience_chart_strength(growth_rate_type):
    growth_rate = growth_rates[growth_rate_type]['strength']
    if growth_rate == 1:
        # Strength growth rate 1:
        experience_chart[1]['strength'] += 0
        experience_chart[2]['strength'] += 0
        experience_chart[3]['strength'] += 0
        experience_chart[4]['strength'] += 0  # 4 zeros
        experience_chart[5]['strength'] += 1
        experience_chart[6]['strength'] += 1
        experience_chart[7]['strength'] += 1  # 3 ones
        experience_chart[8]['strength'] += 2
        experience_chart[9]['strength'] += 2  # 2 twos
        experience_chart[10]['strength'] += 3
        experience_chart[11]['strength'] += 3  # 2 threes
        experience_chart[12]['strength'] += 4  # 1 four
        experience_chart[13]['strength'] += 5
        experience_chart[14]['strength'] += 5  # 2 fives
        experience_chart[15]['strength'] += 6  # 1 six
        experience_chart[16]['strength'] += 7
        experience_chart[17]['strength'] += 7  # 2 sevens
        experience_chart[18]['strength'] += 8
        experience_chart[19]['strength'] += 8  # 2 eights
        experience_chart[20]['strength'] += 9
        experience_chart[21]['strength'] += 9
        experience_chart[22]['strength'] += 9
        experience_chart[23]['strength'] += 9  # 4 nines
        experience_chart[24]['strength'] += 10  # 1 ten
        experience_chart[25]['strength'] += 11
        experience_chart[26]['strength'] += 11  # 2 elevens
        experience_chart[27]['strength'] += 12
        experience_chart[28]['strength'] += 12  # 2 twelves
        experience_chart[29]['strength'] += 13
        experience_chart[30]['strength'] += 13  # 2 thirteens
    elif growth_rate == 2:
        pass
    else:
        print("Unknown strength growth rate.")


def get_initial_stats(remainder):
    return initial_stats_chart[remainder]


class Player(AnimatedSprite):

    def __init__(self, center_point, images, direction=Direction.DOWN.value):
        AnimatedSprite.__init__(self, center_point, direction, images, identifier='HERO')
        self.is_moving = False
        self.current_coordinates = None
        self.next_coordinates = None
        self.name = 'Edward'
        # pre-set attributes
        self.growth = ""
        # status menu
        self.strength = 0
        self.agility = 0
        self.max_hp = 0
        self.max_mp = 0
        self.attack_power = 0
        self.defense_power = 0
        self.weapon = ""
        self.armor = ""
        self.shield = ""

        # set name-based initial stats and growth stats

        self.set_initial_stats()

        # set attack power based on weapon

        self.update_attack_power()

        # hovering status window stats
        self.level = 0
        self.current_hp = self.max_hp
        self.current_mp = self.max_mp
        self.gold = 0
        self.experience = 0

        self.level = self.set_level_by_experience()

        self.points_to_next_level = self.get_points_to_next_level()

        self.spells = []
        for i in range(1, self.level):
            if experience_chart[i].get('spell'):
                self.spells.append(experience_chart[i]['spell'])
        self.inventory = []

    def update_attack_power(self):
        if weapons.get(self.weapon):
            self.attack_power = weapons[self.weapon]['offense']

    def get_points_to_next_level(self):
        if experience_chart.get(self.level + 1):
            return experience_chart[self.level + 1]['exp'] - self.experience
        else:
            return 0

    def set_level_by_experience(self):
        for level in experience_chart:
            if experience_chart[level]['exp'] <= self.experience:
                return level
            return

    def set_initial_stats(self):
        remainder = get_remainder(self.name)
        initial_stats_row = get_initial_stats(remainder)
        self.strength = initial_stats_row["strength"]
        self.agility = initial_stats_row["agility"]
        self.max_hp = initial_stats_row["max_hp"]
        self.max_mp = initial_stats_row["max_mp"]
        self.growth = initial_stats_row["growth"]
        self.agility = initial_stats_row["agility"]
        self.agility = initial_stats_row["agility"]
