from unittest import TestCase, mock
from unittest.mock import MagicMock

import pygame

from src.config.test_config import test_config
from src.movement import MovementController


class TestSound(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_bump(self):
        """NES DirectionBlocked plays SFX_WALL_BUMP on every blocked step; how often is up to
        MovementController.move_player."""
        character = MagicMock()
        character.identifier = 'HERO'
        character.current_tile = 'BRICK'
        character.bumped = False
        movement = MovementController(MagicMock(config=test_config))
        with mock.patch.object(movement.sound, 'play_sound') as play_sound:
            for bumps in range(1, 3):
                movement.bump(character)
                self.assertTrue(character.bumped)
                self.assertEqual(bumps, play_sound.call_count)
