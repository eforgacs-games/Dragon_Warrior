import os
from unittest import TestCase
from unittest.mock import patch

from src.config import test_config
from src.game import Game
from tests.mock_map import MockMap

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


class Test(TestCase):

    def setUp(self) -> None:
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.game.current_map = MockMap(self.game.config)

    def test_bump_and_reset(self):
        self.assertEqual('BRICK', self.game.player.next_tile_id)
        self.assertEqual('GUARD', self.game.player.next_next_tile_id)
        self.game.movement.bump_and_reset(self.game.player, 'TREES', 'GRASS')
        self.assertEqual('TREES', self.game.player.next_tile_id)
        self.assertEqual('GRASS', self.game.player.next_next_tile_id)
