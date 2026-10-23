from unittest import TestCase

import pygame

from src.config.test_config import test_config
from src.direction import Direction
from src.map_layouts import MapLayouts
from src.maps import STAIR_DIRECTIONS, map_lookup
from tests.helpers import new_game


class TestStairsFacing(TestCase):
    """NES CheckStairs (Bank03): StairUpFound (LD9E0) always leaves the hero facing left, and StairDownFound ->
    CalcNextMap -> StairsFaceRight (LD97F) facing right."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()
        pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        self.game = new_game()

    def take_stairs(self, map_name, location):
        """Stand on the stairs at location and take them; returns the hero's facing on the new map."""
        self.game.change_map(map_lookup[map_name](self.game.config), destination_coordinates=location)
        self.game.player.row, self.game.player.column = location
        self.game.map_mgr.process_warp(self.game.current_map.staircases[location])
        return self.game.player.direction_value

    def stairs(self, direction):
        for map_name in MapLayouts().map_layout_lookup:
            current_map = map_lookup[map_name](self.game.config)
            for (row, column) in current_map.staircases:
                if 0 <= row < len(current_map.layout) and 0 <= column < len(current_map.layout[0]) and \
                        STAIR_DIRECTIONS.get(current_map.layout[row][column]) == direction:
                    yield map_name, (row, column)

    def test_going_up_any_stairs_faces_left(self):
        stairs = list(self.stairs('up'))
        self.assertGreater(len(stairs), 20)
        for map_name, location in stairs:
            with self.subTest(map_name=map_name, location=location):
                self.assertEqual(self.take_stairs(map_name, location), Direction.LEFT.value)

    def test_going_down_any_stairs_faces_right(self):
        stairs = list(self.stairs('down'))
        self.assertGreater(len(stairs), 20)
        for map_name, location in stairs:
            with self.subTest(map_name=map_name, location=location):
                self.assertEqual(self.take_stairs(map_name, location), Direction.RIGHT.value)
