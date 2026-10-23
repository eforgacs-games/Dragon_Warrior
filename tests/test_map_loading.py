"""The map loading shortcuts of #431 draw exactly what the long way did.

- load_map makes each type's tiles at once (DragonWarriorMap.map_all_floor_tiles) instead of block by block: the same
  tiles, with the same images and rects, in the same order in each group;
- the main loop's first frame after a map change doesn't draw every tile again, as the frame the fade-in started from
  has just drawn them all (Drawer.drawn_in_full), unless something about the tiles changed in between;
- a map change keeps the biggest map surface it lets go of (Alefgard's) and uses it again (SpareMapSurface).
Each test compares the picture with the one drawn the old way, byte for byte.
"""
import hashlib
import random
from collections import defaultdict
from contextlib import nullcontext
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import K_LEFT, K_RIGHT, Surface

from src.color import LOW_HP_RED, WHITE
from src.drawer import Drawer, SpareMapSurface, map_surface
from src.maps import map_lookup
from tests.test_character_redraw import draw_frame, make_game


def screen_bytes(surface: Surface) -> bytes:
    return pygame.image.tobytes(surface, 'RGB')


def tiles_of(current_map) -> dict:
    """Each tile type's tiles: their rects and their images' pixels, in their groups' order (each map makes its own
    tile images, so two loads of a map have equal images, not the same ones)."""
    pixels: dict[int, bytes] = {}

    def image_bytes(image: Surface) -> bytes:
        if id(image) not in pixels:
            pixels[id(image)] = screen_bytes(image)
        return pixels[id(image)]
    return {name: [(tuple(tile.rect), image_bytes(tile.image)) for tile in tile_dict['group']]
            for name, tile_dict in current_map.floor_tile_key.items() if tile_dict.get('group')}


def load_block_by_block(current_map, player, coordinates, tile_size):
    """load_map as it was: map_floor_tiles for each block, row by row."""
    def map_all_floor_tiles(size):
        for row in range(len(current_map.layout)):
            for column in range(len(current_map.layout[row])):
                current_map.center_pt = (column * size + size // 2, row * size + size // 2)
                current_map.map_floor_tiles(column, row)
    with patch.object(current_map, 'map_all_floor_tiles', map_all_floor_tiles):
        current_map.load_map(player, coordinates, tile_size)


class DisplayTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((512, 480))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()


class TestLoadMap(DisplayTestCase):

    def test_makes_the_tiles_the_block_by_block_way_made(self):
        game = make_game('TantegelThroneRoom')
        for map_name in ('Alefgard', 'TantegelCourtyard', 'Brecconary', 'Garinham', 'SwampCave', 'CharlockB1',
                         'TantegelThroneRoom'):
            with self.subTest(map_name=map_name):
                loaded = {}
                for way in ('at once', 'block by block'):
                    current_map = map_lookup[map_name](game.config)
                    current_map.layout = game.layouts.map_layout_lookup[map_name]
                    coordinates = current_map.initial_coordinates
                    if way == 'at once':
                        current_map.load_map(game.player, coordinates, game.tile_size)
                    else:
                        load_block_by_block(current_map, game.player, coordinates, game.tile_size)
                    loaded[way] = (tiles_of(current_map), current_map.center_pt)
                self.assertEqual(loaded['block by block'], loaded['at once'])

    def test_low_hp_tiles_get_their_red_images(self):
        game = make_game('TantegelThroneRoom')
        for low_hp in (False, True):
            loaded = []
            for way in ('at once', 'block by block'):
                current_map = map_lookup['Alefgard'](game.config)
                current_map.layout = game.layouts.map_layout_lookup['Alefgard']
                current_map.set_low_hp_palette(low_hp)
                if way == 'at once':
                    current_map.load_map(game.player, (50, 47), game.tile_size)
                else:
                    load_block_by_block(current_map, game.player, (50, 47), game.tile_size)
                loaded.append(tiles_of(current_map))
            self.assertEqual(loaded[0], loaded[1])


def entering_frames(full_redraw: bool, between=None, map_name='Alefgard', coordinates=(50, 47)) -> list[bytes]:
    """The screens and backgrounds of a change_map from the Swamp Cave and the 40 main loop frames after it, the hero
    walking left then right. With full_redraw, the main loop's first frame draws every tile again, as it used to."""
    random.seed(431)
    game = make_game('SwampCave')
    frames = []

    def fade(*_args, **_kwargs):
        frames.append(hashlib.sha256(screen_bytes(game.screen) + screen_bytes(game.drawer.background)).digest())
    with patch('src.map_manager.screen_fade', side_effect=fade), patch('src.map_manager.cut_to_black'):
        next_map = map_lookup[map_name](game.config)
        game.map_mgr.change_map(next_map, destination_coordinates=coordinates or next_map.initial_coordinates)
    if between:
        between(game)
    held_keys: defaultdict = defaultdict(int)
    with patch.object(Drawer, 'drawn_in_full', return_value=False) if full_redraw else nullcontext(), \
            patch('src.game.get_ticks', return_value=0), patch('src.movement.key.get_pressed', return_value=held_keys):
        for frame in range(40):
            held_keys.clear()
            held_keys[K_LEFT if frame < 20 else K_RIGHT] = 1
            if frame:
                game.movement.handle_player_movement()
                game.movement.sprites_frame()
            draw_frame(game)
            frames.append(hashlib.sha256(screen_bytes(game.screen) + screen_bytes(game.drawer.background)).digest())
    return frames


class TestFirstFrameAfterAMapChange(DisplayTestCase):

    def test_frames_are_drawn_as_when_the_first_frame_drew_every_tile_again(self):
        for map_name, coordinates in (('Alefgard', (50, 47)), ('Brecconary', None), ('TantegelCourtyard', None)):
            with self.subTest(map_name=map_name):
                self.assertEqual(entering_frames(True, map_name=map_name, coordinates=coordinates),
                                 entering_frames(False, map_name=map_name, coordinates=coordinates))

    def test_a_palette_change_in_between_draws_every_tile_again(self):
        def low_hp(game):
            game.set_window_color(LOW_HP_RED)  # loop_count 1: set_window_color leaves the redraw to the first frame
        self.assertEqual(entering_frames(True, low_hp), entering_frames(False, low_hp))
        self.assertNotEqual(entering_frames(False), entering_frames(False, low_hp))

    def test_the_first_frame_after_entering_alefgard_draws_no_tile_types_in_full(self):
        game = make_game('SwampCave')
        with patch('src.map_manager.screen_fade'), patch('src.map_manager.cut_to_black'):
            game.map_mgr.change_map(map_lookup['Alefgard'](game.config), destination_coordinates=(50, 47))
        self.assertEqual(1, game.loop_count)
        with patch.object(Drawer, 'draw_all_tiles_in_current_map') as draw_all_tiles:
            draw_frame(game)
        draw_all_tiles.assert_not_called()

    def test_a_tile_added_in_between_draws_every_tile_again(self):
        game = make_game('SwampCave')
        with patch('src.map_manager.screen_fade'), patch('src.map_manager.cut_to_black'):
            game.map_mgr.change_map(map_lookup['Alefgard'](game.config), destination_coordinates=(50, 47))
        game.current_map.add_tile(game.current_map.floor_tile_key['GRASS'], (16, 16))
        self.assertFalse(game.drawer.drawn_in_full(game.current_map, game.big_map))
        game.set_window_color(WHITE)
        with patch.object(Drawer, 'draw_all_tiles_in_current_map') as draw_all_tiles:
            draw_frame(game)
        draw_all_tiles.assert_called_once()


class TestSpareMapSurface(DisplayTestCase):

    def test_going_back_to_alefgard_uses_its_surface_again(self):
        game = make_game('Alefgard')
        alefgard_surface = game.big_map
        with patch('src.map_manager.screen_fade'), patch('src.map_manager.cut_to_black'):
            brecconary = map_lookup['Brecconary'](game.config)
            game.map_mgr.change_map(brecconary, destination_coordinates=brecconary.initial_coordinates)
            self.assertIsNot(alefgard_surface, game.big_map)
            self.assertIs(alefgard_surface, game.map_mgr.spare_map_surface.surface)
            with patch('src.drawer.map_surface', wraps=map_surface) as make_surface:
                game.map_mgr.change_map(map_lookup['Alefgard'](game.config), destination_coordinates=(50, 47))
        make_surface.assert_not_called()
        self.assertIs(alefgard_surface, game.big_map)

    def test_a_kept_surface_is_black_like_a_new_one(self):
        spare = SpareMapSurface()
        used = map_surface(64, 48)
        used.fill(WHITE)
        spare.give_back(used)
        taken = spare.take(64, 48)
        self.assertIs(used, taken)
        self.assertEqual(screen_bytes(map_surface(64, 48)), screen_bytes(taken))
        self.assertIsNone(spare.surface)

    def test_keeps_the_biggest(self):
        spare = SpareMapSurface()
        big, small = map_surface(64, 64), map_surface(32, 32)
        spare.give_back(big)
        spare.give_back(small)
        self.assertIs(big, spare.surface)
        self.assertIsNot(big, spare.take(32, 32))  # another size: a new surface, and the big one still kept
        self.assertIs(big, spare.surface)
        spare.give_back(None)
        self.assertIs(big, spare.surface)

    def test_a_surface_in_another_format_is_not_used(self):
        spare = SpareMapSurface()
        other_format = Surface((64, 64), pygame.SRCALPHA, 32)
        spare.give_back(other_format)
        taken = spare.take(64, 64)
        self.assertIsNot(other_format, taken)
        self.assertEqual(screen_bytes(map_surface(64, 64)), screen_bytes(taken))
