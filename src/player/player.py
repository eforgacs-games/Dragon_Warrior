from src.common import Direction
from src.items import weapons
from src.player.player_stats import levels_list, get_remainder, get_initial_stats
from src.sprites.animated_sprite import AnimatedSprite


class Player(AnimatedSprite):

    def __init__(self, center_point, images, direction=Direction.DOWN.value):
        AnimatedSprite.__init__(self, center_point, direction, images, identifier='HERO', dialog=None)

        # map/collision-related attributes
        self.is_moving = False
        self.coordinates = None
        self.next_coordinates = None

        # character attributes
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
            if levels_list[i].get('spell'):
                self.spells.append(levels_list[i]['spell'])
        self.inventory = []

    def update_attack_power(self):
        if weapons.get(self.weapon):
            self.attack_power = weapons[self.weapon]['offense']

    def get_points_to_next_level(self):
        if levels_list.get(self.level + 1):
            return levels_list[self.level + 1]['exp'] - self.experience
        else:
            return 0

    def set_level_by_experience(self):
        for level in levels_list:
            if levels_list[level]['exp'] <= self.experience:
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
