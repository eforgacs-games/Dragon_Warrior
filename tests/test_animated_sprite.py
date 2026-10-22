from unittest import TestCase
from unittest.mock import MagicMock

from src.direction import Direction
from src.config.test_config import test_config
from src.maps_functions import parse_animated_sprite_sheet
from src.sprites.animated_sprite import AnimatedSprite


class TestAnimatedSprite(TestCase):
    def setUp(self) -> None:
        mock = MagicMock()
        mock.get_size = MagicMock(return_value=(128, 0))
        self.mock_images = parse_animated_sprite_sheet(mock, test_config)
        self.anim_sprite = AnimatedSprite(center_point=None, direction_value=None, images=self.mock_images, identifier='Mock')

    def test_initialized_values(self):
        self.assertEqual(self.anim_sprite.identifier, 'Mock')
        self.assertEqual(self.mock_images[Direction.DOWN.value], self.anim_sprite.images_map[Direction.DOWN.value])
        self.assertEqual(self.mock_images[Direction.LEFT.value], self.anim_sprite.images_map[Direction.LEFT.value])
        self.assertEqual(self.mock_images[Direction.UP.value], self.anim_sprite.images_map[Direction.UP.value])
        self.assertEqual(self.mock_images[Direction.RIGHT.value], self.anim_sprite.images_map[Direction.RIGHT.value])
        self.assertEqual(self.anim_sprite.current_frame, AnimatedSprite.walk_frame)
        self.assertIsNone(self.anim_sprite.direction_value)

    def test_directional_values(self):
        self.assertEqual(self.mock_images[0], self.mock_images[Direction.DOWN.value])
        self.assertEqual(self.mock_images[1], self.mock_images[Direction.LEFT.value])
        self.assertEqual(self.mock_images[2], self.mock_images[Direction.UP.value])
        self.assertEqual(self.mock_images[3], self.mock_images[Direction.RIGHT.value])

    def test_animate_shows_the_shared_walking_frame(self):
        # NES CharLeftRight: one walking frame for every character
        self.addCleanup(setattr, AnimatedSprite, 'walk_frame', AnimatedSprite.walk_frame)
        self.anim_sprite.direction_value = Direction.LEFT.value
        other = AnimatedSprite(center_point=None, direction_value=Direction.UP.value, images=self.mock_images,
                               identifier='Other')
        for walk_frame in (1, 0, 1):
            AnimatedSprite.walk_frame = walk_frame
            self.anim_sprite.animate()
            other.animate()
            self.assertEqual(walk_frame, self.anim_sprite.current_frame)
            self.assertEqual(walk_frame, other.current_frame)
            self.assertEqual(self.anim_sprite.images_map[Direction.LEFT.value][walk_frame], self.anim_sprite.image)

    def test_animate_down_direction(self):
        self.anim_sprite.direction_value = Direction.DOWN.value
        self.anim_sprite.animate()
        self.assertEqual(self.anim_sprite.image, self.anim_sprite.images_map[0][self.anim_sprite.current_frame])

    def test_animate_left_direction(self):
        self.anim_sprite.direction_value = Direction.LEFT.value
        self.anim_sprite.animate()
        sprite = self.anim_sprite
        self.assertEqual(sprite.image, sprite.images_map[sprite.direction_value][sprite.current_frame])

    def test_animate_up_direction(self):
        self.anim_sprite.direction_value = Direction.UP.value
        self.anim_sprite.animate()
        sprite = self.anim_sprite
        self.assertEqual(sprite.image, sprite.images_map[sprite.direction_value][sprite.current_frame])

    def test_animate_right_direction(self):
        self.anim_sprite.direction_value = Direction.RIGHT.value
        self.anim_sprite.animate()
        sprite = self.anim_sprite
        self.assertEqual(sprite.image, sprite.images_map[sprite.direction_value][sprite.current_frame])
