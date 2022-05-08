from src.common import Direction
from src.items import weapons
from src.player.player_stats import levels_list, apply_transformation_to_levels_list
from src.sprites.animated_sprite import AnimatedSprite


class Player(AnimatedSprite):

    def __init__(self, center_point, images, direction=Direction.DOWN.value):
        AnimatedSprite.__init__(self, center_point, direction, images, identifier='HERO')

        # map/collision-related attributes
        self.is_moving = False
        self.coordinates = None
        self.next_coordinates = None
        self.next_next_coordinates = None
        self.current_tile = None
        self.next_tile_id = None
        self.next_next_tile_id = None
        self.bumped = False
        self.last_bump_time = None

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
        apply_transformation_to_levels_list(self.name)
        self.strength = levels_list[1]["strength"]
        self.agility = levels_list[1]["agility"]
        self.max_hp = levels_list[1]["max_hp"]
        self.max_mp = levels_list[1]["max_mp"]
        self.agility = levels_list[1]["agility"]
