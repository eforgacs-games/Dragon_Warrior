from unittest import TestCase

from src.config.test_config import test_config
from tests.mock_map import MockMap
from tests.helpers import new_game


class Test(TestCase):

    def setUp(self) -> None:
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        self.game = new_game()
        self.game.current_map = MockMap(self.game.config)

    def test_bump_and_reset(self):
        self.assertEqual('BRICK', self.game.player.next_tile_id)
        self.assertEqual('BRICK', self.game.player.next_next_tile_id)
        self.game.movement.bump_and_reset(self.game.player, 'TREES', 'GRASS')
        self.assertEqual('TREES', self.game.player.next_tile_id)
        self.assertEqual('GRASS', self.game.player.next_next_tile_id)
