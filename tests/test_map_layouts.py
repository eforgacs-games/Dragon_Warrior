import logging
import sys
from unittest import TestCase

from src.map_layouts import MapLayouts


class TestMapLayouts(TestCase):

    def setUp(self) -> None:
        self.map_layouts = MapLayouts()

    def test_player_in_every_map(self):
        for map_name, map_layout in self.map_layouts.map_layout_lookup.items():
            log = logging.getLogger("TestLog")
            log.debug(f"Testing map: {map_name}")
            self.assertTrue(any(33 in row for row in map_layout))


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
