from src.sprites.animated_sprite import AnimatedSprite


class FixedCharacter(AnimatedSprite):
    def __init__(self, center_point, direction, images, identifier):
        super().__init__(center_point, direction, images, identifier)
        self.column = None
        self.row = None
