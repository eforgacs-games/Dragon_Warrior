from src.sprites.animated_sprite import AnimatedSprite


class RoamingCharacter(AnimatedSprite):
    def __init__(self, center_point, direction_value, images, identifier):
        super().__init__(center_point, direction_value, images, identifier)
        self.column = None
        self.row = None
        self.is_moving = False
        self.previous_previous_tile = None
        self.previous_tile = None
        self.current_tile = None
        self.next_tile_id = None
        self.next_next_tile_id = None
        self.next_tile_checked = False
        self.last_rect = None
        # NPCS_MAKE_WAY: turns of its own to stand still for, after stepping out of the hero's way (Game.make_way)
        self.turns_to_rest = 0
