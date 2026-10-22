from src.direction import Direction
from src.sprites.base_sprite import BaseSprite


class AnimatedSprite(BaseSprite):
    # NES CharLeftRight bit 3 (DoSprites, Bank00): the walking frame (which leg is forward), one for every character
    # on the map, hero and NPCs alike. NPCSchedule.start_frame swaps it every 16 frames.
    walk_frame = 0

    def __init__(self, center_point, direction_value, images, identifier):
        self.identifier = identifier
        self.current_frame = AnimatedSprite.walk_frame
        self.direction_value = direction_value
        self.images_map = {}
        # (column, row) tiles a character holds while taking a step, so nobody else can move onto either. The NES
        # checks a move once, when it starts, against everyone's position and the tile they're moving to.
        self.step_origin: tuple | None = None
        self.step_destination: tuple | None = None
        self.set_images(images)
        if center_point is not None and images is not None:
            super().__init__(center_point, images[0][0])

    def set_images(self, images):
        if images is not None:
            down_images = images[0]
            left_images = images[1]
            up_images = images[2]
            right_images = images[3]
            self.images_map = {
                Direction.DOWN.value: down_images,
                Direction.LEFT.value: left_images,
                Direction.UP.value: up_images,
                Direction.RIGHT.value: right_images
            }

    def show_facing(self):
        """Show the current animation frame for the way the character faces now. __init__ always starts on the
        first image (facing down), and the frame drawn before animate() runs would otherwise show that."""
        if self.direction_value in self.images_map:
            self.image = self.images_map[self.direction_value][self.current_frame]
            self.dirty = 1

    def animate(self):
        """Show the shared walking frame (NES GetPlayerAnim and the NPC sprite code both read CharLeftRight), so every
        character swaps legs on the same frame."""
        self.current_frame = AnimatedSprite.walk_frame
        if self.direction_value in self.images_map.keys():
            self.image = self.images_map[self.direction_value][self.current_frame]
        self.dirty = 1

    def pause(self):
        self.dirty = 1
