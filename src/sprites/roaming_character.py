from src.sprites.animated_sprite import AnimatedSprite


class RoamingCharacter(AnimatedSprite):
    def __init__(self, center_point, direction_value, images, identifier):
        super().__init__(center_point, direction_value, images, identifier)
        self.last_roaming_clock_check = None
        self.column = None
        self.row = None
        self.is_moving = False
        self.previous_previous_tile = None
        self.previous_tile = None
        self.current_tile = None
        self.next_tile_id = None
        self.next_tile_checked = False
