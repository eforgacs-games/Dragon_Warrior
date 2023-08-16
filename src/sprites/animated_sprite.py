from src.direction import Direction
from src.sprites.base_sprite import BaseSprite


class AnimatedSprite(BaseSprite):
    def __init__(self, center_point, direction_value, images, identifier):
        self.identifier = identifier
        self.current_frame = 0
        self.frame_count = 0
        self.frame_delay = 2
        self.direction_value = direction_value
        self.images_map = {}
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

    def animate(self):
        max_frame = 1
        self.frame_count += 1
        if self.frame_count % 15 == 0:
            if self.frame_count > self.frame_delay:
                self.frame_count = 0
                self.current_frame += 1
            if self.current_frame > max_frame:
                self.current_frame = 0
        if self.direction_value in self.images_map.keys():
            # have gotten an IndexError: list index out of range here
            self.image = self.images_map[self.direction_value][self.current_frame]
        self.dirty = 1

    def pause(self):
        self.dirty = 1
