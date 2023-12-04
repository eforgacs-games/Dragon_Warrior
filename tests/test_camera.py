import os
from unittest import TestCase
from unittest.mock import patch

from src.config.test_config import test_config
from src.game import Game

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


class TestCamera(TestCase):
    def setUp(self) -> None:
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.game.camera_pos = 0, 0
        self.center_pt = 0, 0

    def test_set_pos(self):
        self.game.camera.set_pos((1, 2))
        self.assertEqual(1, self.game.camera.x)
        self.assertEqual(2, self.game.camera.y)
