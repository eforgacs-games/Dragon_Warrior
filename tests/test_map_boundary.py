"""NES BoundsChkEnd (Bank00 LABDF): every block off the map is the map's boundary block (MapDatTbl), so the NES never
shows black past a map's edge (#377)."""
import os
import unittest
from collections import Counter

import pygame
from pygame import Rect

from src.color import BLACK
from src.maps import MAP_BOUNDARY_TILES, map_lookup
from tests.test_character_redraw import draw_frame, make_game

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


def edge_tiles(current_map) -> Counter:
    layout = current_map.layout
    edge = layout[0] + layout[-1] + [row[0] for row in layout] + [row[-1] for row in layout]
    return Counter(current_map.get_tile_by_value(value) for value in edge)


class TestMapBoundary(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((512, 480))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.game = make_game('Garinham')
        self.tile_size = self.game.game_state.config['TILE_SIZE']

    def go_to(self, map_name, coordinates):
        self.game.map_mgr.change_map(map_lookup[map_name](self.game.config), destination_coordinates=coordinates)
        draw_frame(self.game)

    def map_rect(self) -> Rect:
        current_map = self.game.current_map
        x, y = self.game.camera.pos
        return Rect(int(x), int(y), current_map.width, current_map.height)

    def test_the_layouts_are_padded_with_the_boundary_block(self):
        # MAP_BOUNDARY_TILES is MapDatTbl's boundary byte for each map; the layouts' own padding agrees with it
        for map_name in ('Alefgard', 'Brecconary', 'Cantlin', 'CharlockB1', 'CharlockB8', 'Garinham', 'Hauksness',
                         'Kol', 'MagicTemple', 'Rimuldar', 'StaffOfRainCave', 'TantegelCellar', 'TantegelCourtyard',
                         'TantegelThroneRoom', 'SwampCave', 'GarinsGraveB1', 'CharlockB2'):
            with self.subTest(map_name=map_name):
                current_map = map_lookup[map_name](self.game.config)
                self.assertEqual(edge_tiles(current_map).most_common(1)[0][0], current_map.boundary_tile)
        self.assertEqual(map_lookup['TantegelCellar'](self.game.config).boundary_tile, 'WALL')  # $10, stone
        self.assertEqual(MAP_BOUNDARY_TILES['Cantlin'], 'BRICK')

    def test_garinham_shows_grass_past_its_top_edge(self):
        # Garinham's layout has only one row above the NES map: standing on its top row used to show black above
        self.go_to('Garinham', (1, 18))
        screen, current_map = self.game.screen, self.game.current_map
        map_rect = self.map_rect()
        self.assertGreater(map_rect.top, 0)
        grass = current_map.floor_tile_image(current_map.floor_tile_key['GRASS']['val'])
        for row_top in range(map_rect.top - self.tile_size, -self.tile_size, -self.tile_size):
            for column_left in range(map_rect.left, screen.get_width(), self.tile_size):
                area = Rect(column_left, row_top, self.tile_size, self.tile_size).clip(screen.get_rect())
                if not area.width or not area.height:
                    continue
                block = screen.subsurface(area)
                expected = grass.subsurface(Rect(area.x - column_left, area.y - row_top, area.width, area.height))
                self.assertEqual(pygame.image.tobytes(block, 'RGB'), pygame.image.tobytes(expected, 'RGB'),
                                 (row_top, column_left))

    def test_the_map_itself_is_drawn_as_before(self):
        # Only the blocks off the layout change: on the map, the screen is the background, as it always was
        for map_name, coordinates in (('Garinham', (1, 18)), ('Cantlin', (10, 2)), ('TantegelCellar', (2, 2)),
                                      ('Alefgard', (50, 51))):
            with self.subTest(map_name=map_name):
                self.go_to(map_name, coordinates)
                screen = self.game.screen
                on_screen = self.map_rect().clip(screen.get_rect())
                self.assertEqual(pygame.image.tobytes(screen.subsurface(on_screen), 'RGB'),
                                 pygame.image.tobytes(self.game.drawer.background.subsurface(
                                     on_screen.move(-self.map_rect().x, -self.map_rect().y)), 'RGB'))

    def test_off_the_map_is_blank_from_under_a_roof(self):
        # HasCoverData: blocks off the map are never covered, so from under cover ChkCoveredArea blanks them
        self.go_to('Garinham', (1, 18))
        current_map = self.game.current_map
        current_map.covered_area = frozenset({(1, 18)})
        draw_frame(self.game)
        self.assertTrue(current_map.player_under_cover)
        draw_frame(self.game)
        above = Rect(0, 0, self.game.screen.get_width(), self.map_rect().top)
        colors = {self.game.screen.get_at((x, y))[:3] for x in range(0, above.width, 7) for y in range(above.height)}
        self.assertEqual(colors, {BLACK})


if __name__ == '__main__':
    unittest.main()
