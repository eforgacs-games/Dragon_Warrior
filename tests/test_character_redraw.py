"""Regression tests for #98: animating characters mustn't leave a "residue" of old frames on the map.

The map is drawn once onto Drawer.background, and after that draw_all only redraws the tiles under and around the
characters before drawing them again. If the tile under a character isn't redrawn, each new animation frame is drawn
over the old one, and the old frame shows through the new one's transparent pixels. These tests render real frames
headless and compare the background around each on-screen character with a clean redraw of the same frame.
"""
import inspect
import os
from unittest import TestCase
from unittest.mock import patch

import pygame

from src.config.test_config import test_config
from src.game import Game

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

FRAMES = 60  # characters change animation frame every ANIMATION_CYCLE_TICKS (15) frames


def make_game(start_map: str) -> Game:
    config = dict(test_config, START_MAP=start_map, NO_BLIT=False, NO_WAIT=True, RENDER_TEXT=False)
    with patch('src.game.SCALED', 0):
        game = Game(config)
    game.game_state.enable_animate = True
    return game


def draw_frame(game: Game) -> None:
    """Draw one frame the way Game.main does."""
    arguments = {'screen': game.screen, 'loop_count': game.loop_count, 'big_map': game.big_map,
                 'current_map': game.current_map, 'player': game.player, 'cmd_menu': game.cmd_menu,
                 'foreground_rects': game.foreground_rects, 'enable_animate': game.game_state.enable_animate,
                 'camera': game.camera, 'initial_dialog_enabled': False, 'events': [], 'skip_text': game.skip_text,
                 'left_throne_room': True, 'game_state': game.game_state, 'color': game.color}
    parameters = inspect.signature(game.drawer.draw_all).parameters
    game.drawer.draw_all(**{name: arguments[name] if name in arguments else getattr(game, name)
                            for name in parameters})
    game.loop_count += 1


def find_residue(game: Game, before_drawing=None) -> dict:
    """Draw FRAMES frames and return {character identifier: frame number} for every character that had other pixels
    around it than a clean redraw of the map and characters would have."""
    tile_size = game.game_state.config['TILE_SIZE']
    residue: dict = {}
    for frame in range(1, FRAMES + 1):
        if before_drawing:
            before_drawing(frame)
        # draw_all draws each character, then moves its animation on to the next image
        drawn = {identifier: (character_dict['character'].image, character_dict['character'].rect.copy())
                 for identifier, character_dict in game.current_map.characters.items()}
        draw_frame(game)
        background = game.drawer.background
        clean = background.copy()
        game.drawer.draw_all_tiles_in_current_map(game.current_map, clean)
        for image, rect in drawn.values():
            clean.blit(image, rect)
        on_screen = pygame.Rect(-game.camera.pos[0], -game.camera.pos[1], game.screen.get_width(),
                                game.screen.get_height())
        for identifier, (_, rect) in drawn.items():
            area = rect.inflate(tile_size * 2, tile_size * 2).clip(on_screen).clip(background.get_rect())
            if not area.width or not area.height:
                continue
            if pygame.image.tobytes(background.subsurface(area), 'RGB') != \
                    pygame.image.tobytes(clean.subsurface(area), 'RGB'):
                residue.setdefault(identifier, frame)
    return residue


class TestCharacterRedraw(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_fixed_characters_leave_no_residue(self):
        # The issue's example: the MAN standing on the trees just inside Brecconary's west gate
        game = make_game('Brecconary')
        man = game.current_map.characters['MAN_2']['character']
        self.assertEqual((21, 11), (man.row, man.column))
        self.assertEqual({}, find_residue(game))

    def test_fixed_characters_on_other_tiles_leave_no_residue(self):
        # Garinham's and Kol's NPCs stand on sand, trees and grass as well as brick
        for start_map in ('Garinham', 'Kol', 'TantegelThroneRoom'):
            with self.subTest(start_map=start_map):
                self.assertEqual({}, find_residue(make_game(start_map)))

    def test_roaming_characters_leave_no_residue(self):
        game = make_game('TantegelCourtyard')
        roaming_characters = game.current_map.roaming_characters
        self.assertTrue(roaming_characters)
        start_positions = [character.rect.topleft for character in roaming_characters]
        clock = [0]

        def roam(_frame):
            clock[0] += 100  # roaming characters pick a new step every second
            game.move_roaming_characters()
            game.update_roaming_character_positions()

        with patch('src.game.get_ticks', lambda: clock[0]):
            residue = find_residue(game, before_drawing=roam)
        self.assertNotEqual(start_positions, [character.rect.topleft for character in roaming_characters])
        self.assertEqual({}, residue)

    def test_residue_is_detected_when_the_tile_under_a_character_is_not_redrawn(self):
        # The bug in #98: the tile under the MAN wasn't among the tiles redrawn each frame
        game = make_game('Brecconary')
        with patch('src.drawer.get_fixed_character_underlying_tiles', return_value=[]):
            residue = find_residue(game)
        self.assertIn('MAN_2', residue)
