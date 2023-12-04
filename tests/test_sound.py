from unittest import TestCase, mock
from unittest.mock import MagicMock

from pygame import time
from pygame.time import get_ticks

from src.config.test_config import test_config
from src.movement import Movement


class TestSound(TestCase):

    @mock.patch.object(time, "get_ticks", return_value=300)
    def test_bump(self, mock_get_ticks):
        character = MagicMock()
        character.identifier = 'HERO'
        character.last_bump_time = get_ticks()
        character.bumped = False
        movement = Movement(test_config)
        for i in range(2):
            movement.bump(character)
            self.assertTrue(character.bumped)
            # will reset the character.last_bump_time
            character.last_bump_time = 10
            movement.bump(character)
            self.assertEqual(300, character.last_bump_time)
