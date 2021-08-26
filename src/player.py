from random import randint

from src.sprites.animated_sprite import AnimatedSprite
from src.common import Direction

# TODO: Fix ranges to not be random integers, and instead based on the character's name.

experience_chart = {
    1: {'exp': 0, 'strength': randint(3, 6), 'agility': randint(3, 6), 'max_hp': randint(13, 16), 'max_mp': 0, 'spell': None},
    2: {'exp': 7, 'strength': 1, 'agility': 0, 'max_hp': randint(6, 7), 'max_mp': 0, 'spell': None},
    3: {'exp': 23, 'strength': 2, 'agility': 2, 'max_hp': 2, 'max_mp': randint(4, 7), 'spell': "Heal"},
    4: {'exp': 47, 'strength': 0, 'agility': 2, 'max_hp': randint(6, 7), 'max_mp': randint(10, 11), 'spell': "Hurt"},
    5: {'exp': 110, 'strength': randint(4, 5), 'agility': 2, 'max_hp': 4, 'max_mp': 4, 'spell': None},
    6: {'exp': 220, 'strength': 4, 'agility': 0, 'max_hp': 3, 'max_mp': randint(3, 4), 'spell': None},
    7: {'exp': 450, 'strength': 2, 'agility': randint(6, 7), 'max_hp': 2, 'max_mp': 2, 'spell': "Sleep"},
    8: {'exp': 800, 'strength': randint(3, 4), 'agility': 3, 'max_hp': randint(5, 6), 'max_mp': 3, 'spell': None},
    9: {'exp': 1300, 'strength': 8, 'agility': randint(1, 2), 'max_hp': 4, 'max_mp': randint(6, 7), 'spell': "Radiant"},
    10: {'exp': 2000, 'strength': randint(4, 5), 'agility': randint(8, 9), 'max_hp': randint(3, 4), 'max_mp': 4, 'spell': "Stopspell"},
    11: {'exp': 2900, 'strength': 5, 'agility': 4, 'max_hp': randint(7, 8), 'max_mp': randint(9, 10), 'spell': None},
    12: {'exp': 4000, 'strength': randint(7, 8), 'agility': 5, 'max_hp': 1, 'max_mp': randint(7, 8), 'spell': "Outside"},
    13: {'exp': 5500, 'strength': randint(3, 4), 'agility': randint(7, 8), 'max_hp': 7, 'max_mp': randint(5, 6), 'spell': "Return"},
    14: {'exp': 7500, 'strength': 8, 'agility': randint(6, 7), 'max_hp': randint(7, 8), 'max_mp': 6, 'spell': None},
    15: {'exp': 10000, 'strength': randint(7, 8), 'agility': randint(8, 9), 'max_hp': randint(7, 8), 'max_mp': randint(1, 2), 'spell': "Repel"},
    16: {'exp': 13000, 'strength': randint(3, 4), 'agility': 6, 'max_hp': randint(5, 6), 'max_mp': randint(21, 23), 'spell': None},
    17: {'exp': 16000, 'strength': 0, 'agility': randint(7, 8), 'max_hp': 8, 'max_mp': 5, 'spell': "Healmore"},
    18: {'exp': 19000, 'strength': randint(12, 13), 'agility': randint(5, 6), 'max_hp': randint(13, 15), 'max_mp': randint(7, 8), 'spell': None},
    19: {'exp': 22000, 'strength': 2, 'agility': 2, 'max_hp': randint(14, 15), 'max_mp': randint(6, 7), 'spell': "Hurtmore"},
    20: {'exp': 26000, 'strength': randint(4, 5), 'agility': 2, 'max_hp': randint(7, 8), 'max_mp': randint(12, 13), 'spell': None},
    21: {'exp': 30000, 'strength': 3, 'agility': 2, 'max_hp': randint(10, 11), 'max_mp': randint(6, 7), 'spell': None},
    22: {'exp': 34000, 'strength': 2, 'agility': 0, 'max_hp': randint(8, 9), 'max_mp': randint(10, 11), 'spell': None},
    23: {'exp': 38000, 'strength': 2, 'agility': randint(3, 4), 'max_hp': randint(6, 7), 'max_mp': randint(6, 7), 'spell': None},
    24: {'exp': 42000, 'strength': randint(3, 4), 'agility': 4, 'max_hp': 5, 'max_mp': randint(7, 8), 'spell': None},
    25: {'exp': 46000, 'strength': randint(9, 10), 'agility': 2, 'max_hp': randint(3, 4), 'max_mp': 0, 'spell': None},
    26: {'exp': 50000, 'strength': 4, 'agility': randint(4, 5), 'max_hp': 6, 'max_mp': 7, 'spell': None},
    27: {'exp': 54000, 'strength': randint(7, 8), 'agility': 2, 'max_hp': randint(8, 9), 'max_mp': randint(6, 7), 'spell': None},
    28: {'exp': 58000, 'strength': 5, 'agility': randint(7, 8), 'max_hp': randint(5, 6), 'max_mp': 5, 'spell': None},
    29: {'exp': 62000, 'strength': randint(4, 5), 'agility': 5, 'max_hp': 5, 'max_mp': randint(9, 10), 'spell': None},
    30: {'exp': 65535, 'strength': 5, 'agility': randint(9, 10), 'max_hp': randint(9, 10), 'max_mp': randint(9, 10), 'spell': None}
}


class Player(AnimatedSprite):

    def __init__(self, center_point, images, direction=Direction.DOWN.value):
        AnimatedSprite.__init__(self, center_point, direction, images, identifier='HERO')
        self.is_moving = False
        self.current_coordinates = None
        self.next_coordinates = None
        self.name = 'Eddie'
        self.experience = 1400
        # hovering status window stats
        self.level = 0
        for level in experience_chart:
            if experience_chart[level]['exp'] <= self.experience:
                self.level = level
            else:
                break

        self.gold = 0
        self.points_to_next_level = None
        if experience_chart.get(self.level + 1):
            self.points_to_next_level = experience_chart[self.level + 1]['exp'] - self.experience
        self.agility = 0
        self.strength = 22
        self.maximum_hp = 44
        self.maximum_mp = 29
        self.attack_power = 37
        self.defense_power = 20
        self.weapon = "Hand Axe"
        self.armor = "Chain Mail"
        self.shield = "Small Shield"
        self.spells = []
        for i in range(1, self.level):
            if experience_chart[i].get('spell'):
                self.spells.append(experience_chart[i]['spell'])
        self.inventory = []

