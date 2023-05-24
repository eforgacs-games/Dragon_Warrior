from src.common import Direction, get_next_tile_identifier
from src.items import weapons, armor, shields
from src.player.player_stats import levels_list, apply_transformation_to_levels_list
from src.sprites.animated_sprite import AnimatedSprite


class Player(AnimatedSprite):

    def __init__(self, center_point, images, current_map, direction_value=Direction.DOWN.value):
        AnimatedSprite.__init__(self, center_point, direction_value, images, identifier='HERO')

        # map/collision-related attributes
        self.row, self.column = current_map.get_initial_character_location('HERO')
        self.next_tile_checked = False
        self.is_moving = False
        self.next_coordinates = None
        self.next_next_coordinates = None
        self.current_tile = None
        self.next_tile_id = get_next_tile_identifier(self.column, self.row, self.direction_value, current_map)
        self.next_next_tile_id = get_next_tile_identifier(self.column, self.row, self.direction_value, current_map, offset=2)
        self.bumped = False
        self.last_bump_time = None
        self.received_environment_damage = False

        self.adventure_log = 0

        # character attributes
        self.name = "Player"
        # status menu
        self.strength = 0
        self.agility = 0
        self.max_hp = 0
        self.max_mp = 0
        self.weapon = ""
        self.armor = ""
        self.shield = ""

        # set name-based initial stats and growth stats

        self.set_initial_stats()
        self.attack_power = self.strength
        self.defense_power = self.agility

        # set power based on equipment
        self.update_attack_power()
        self.update_defense_power()

        # hovering status window stats
        self.level = 0
        self.current_hp = self.max_hp
        self.current_mp = self.max_mp
        self.gold = 0
        self.total_experience = 0
        self.is_dead = False

        self.level = self.get_level_by_experience()

        self.points_to_next_level = self.get_points_to_next_level()

        self.spells = []
        self.inventory = []

    def update_attack_power(self):
        if weapons.get(self.weapon):
            self.attack_power = self.strength + weapons[self.weapon]['offense']
        else:
            self.attack_power = self.strength

    def update_defense_power(self):
        if armor.get(self.armor):
            if shields.get(self.shield):
                self.defense_power = self.agility + armor[self.armor]['defense'] + shields[self.shield]['defense']
            else:
                self.defense_power = self.agility + armor[self.armor]['defense']
        else:
            if shields.get(self.shield):
                self.defense_power = self.agility + shields[self.shield]['defense']
            else:
                self.defense_power = self.agility

    def get_points_to_next_level(self):
        if levels_list.get(self.level + 1):
            return levels_list[self.level + 1]['exp'] - self.total_experience
        else:
            return 0

    def get_level_by_experience(self):
        for level in reversed(levels_list):
            if self.total_experience >= levels_list[level]['total_exp']:
                return level

    def set_initial_stats(self):
        apply_transformation_to_levels_list(self.name)
        self.set_stats_by_level(1)

    def update_stats_to_current_level(self):
        self.set_stats_by_level(self.level)

    def set_stats_by_level(self, level):
        self.strength = levels_list[level]['strength']
        self.agility = levels_list[level]['agility']
        self.max_hp = levels_list[level]['max_hp']
        self.max_mp = levels_list[level]['max_mp']
        for i in range(1, level + 1):
            if levels_list[i].get('spell'):
                if levels_list[i]['spell'] not in self.spells:
                    self.spells.append(levels_list[i]['spell'])

    def update_stats_by_level(self):
        self.strength = levels_list[self.level]['strength']
        self.agility = levels_list[self.level]['agility']
        self.max_hp = levels_list[self.level]['max_hp']
        self.max_mp = levels_list[self.level]['max_mp']

    def restore_hp(self):
        self.current_hp = self.max_hp

    def restore_mp(self):
        self.current_mp = self.max_mp
