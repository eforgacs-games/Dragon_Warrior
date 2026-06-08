import logging
import sys
from unittest import TestCase

from src.map_layouts import MapLayouts


class TestMapLayouts(TestCase):

    def setUp(self) -> None:
        self.map_layouts = MapLayouts()

    def test_no_character_ids_in_layouts(self):
        """Character IDs (33-42) must not appear in any map layout; characters are placed via npc_coordinates."""
        for map_name, map_layout in self.map_layouts.map_layout_lookup.items():
            log = logging.getLogger("TestLog")
            log.debug(f"Testing map: {map_name}")
            for row_idx, row in enumerate(map_layout):
                for col_idx, val in enumerate(row):
                    self.assertLessEqual(
                        val, 32,
                        msg=f"Map '{map_name}' has character ID {val} at ({row_idx}, {col_idx})"
                    )


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
