from src.animated_sprite import AnimatedSprite
from src.common import Direction


class Player(AnimatedSprite):

    def __init__(self, center_point, images, direction=Direction.DOWN.value):
        AnimatedSprite.__init__(self, center_point, direction, images, identifier='HERO')
        self.is_moving = False
        self.name = 'Eddie'
        self.points_to_next_level = 0
        self.strength = 22
        self.maximum_hp = 44
        self.maximum_mp = 29
        self.attack_power = 37
        self.defense_power = 20
        self.weapon = "Hand Axe"
        self.armor = "Chain Mail"
        self.shield = "Small Shield"

