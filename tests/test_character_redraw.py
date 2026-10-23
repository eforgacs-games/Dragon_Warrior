"""Regression tests for #98: animating characters mustn't leave a "residue" of old frames on the map.

The map is drawn once onto Drawer.background, and after that draw_all only redraws the tiles under and around the
characters before drawing them again. If the tile under a character isn't redrawn, each new animation frame is drawn
over the old one, and the old frame shows through the new one's transparent pixels. These tests render real frames
headless and compare the background around each on-screen character with a clean redraw of the same frame.
"""
import inspect
import random
from collections import defaultdict
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import K_DOWN, K_LEFT, K_RIGHT, K_UP

from src.config.test_config import test_config
from src.direction import Direction
from src.game import Game
from src.game_functions import set_character_position

FRAMES = 60  # characters change animation frame every 16 frames (NES CharLeftRight)


def make_game(start_map: str, scale: int = test_config['SCALE']) -> Game:
    config = dict(test_config, START_MAP=start_map, NO_BLIT=False, NO_WAIT=True, RENDER_TEXT=False, SCALE=scale,
                  TILE_SIZE=16 * scale)
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
        else:
            game.movement.npc_schedule.count_frame()  # the walking animation moves on every 16 frames
            game.movement.npc_schedule.start_sprites()
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


def characters_to_draw(game: Game) -> list:
    """(image, rect) of each character draw_all is about to draw: all but the NPCs hidden by a roof (#90)."""
    current_map = game.current_map
    return [(character_dict['character'].image, character_dict['character'].rect.copy())
            for identifier, character_dict in current_map.characters.items()
            if identifier == 'HERO' or not current_map.is_hidden_by_cover(character_dict['character'].row,
                                                                           character_dict['character'].column)]


def visible_area_matches_a_clean_redraw(game: Game, drawn) -> bool:
    """Whether everything on screen (the part of the background the camera shows) is what a clean redraw of the map
    and the characters, as drawn, would show."""
    background = game.drawer.background
    clean = background.copy()
    game.drawer.draw_all_tiles_in_current_map(game.current_map, clean)
    for image, rect in drawn:
        clean.blit(image, rect)
    on_screen = pygame.Rect(-game.camera.pos[0], -game.camera.pos[1], game.screen.get_width(),
                            game.screen.get_height()).clip(background.get_rect())
    return pygame.image.tobytes(background.subsurface(on_screen), 'RGB') == \
        pygame.image.tobytes(clean.subsurface(on_screen), 'RGB')


def walk_and_find_ghosts(game: Game, npc_identifier: str, npc_direction: Direction, npc_steps: int, hero_waits: int,
                         hero_steps: int) -> list:
    """Have the roaming NPCs take npc_steps steps in npc_direction, one after another, and walk the hero right (the
    camera scrolling with him) for hero_steps blocks, starting hero_waits frames in. Returns the frames on which
    anything on screen differed from a clean redraw."""
    npc = game.current_map.characters[npc_identifier]['character']
    held_keys = defaultdict(int)
    npc_slot = game.current_map.roaming_characters.index(npc)
    steps_started = 0
    ghost_frames = []
    hero_start_x = game.player.rect.x
    frame = 0
    with patch('src.movement.random.choice', return_value=npc_direction.value), \
            patch('src.movement.key.get_pressed', return_value=held_keys):
        while frame < 300 and (steps_started < npc_steps or npc.is_moving or game.player.is_moving or
                               game.player.rect.x < hero_start_x + hero_steps * game.tile_size):
            frame += 1
            held_keys[K_RIGHT] = int(hero_waits < frame and
                                     game.player.rect.x <= hero_start_x + (hero_steps - 1) * game.tile_size)
            game.movement.handle_player_movement()
            if not game.player.is_moving:
                set_character_position(game.player, game.tile_size)
            if not npc.is_moving and steps_started < npc_steps:
                game.movement.npc_schedule.give_turn_to(npc_slot)  # her next step starts now
                steps_started += 1
            game.movement.do_sprites()
            drawn = characters_to_draw(game)
            draw_frame(game)
            if not visible_area_matches_a_clean_redraw(game, drawn):
                ghost_frames.append(frame)
    assert game.player.rect.x == hero_start_x + hero_steps * game.tile_size, 'the hero should have walked'
    assert npc.last_rect is not None and npc.rect != npc.last_rect, 'the NPC should have walked'
    return ghost_frames


def walk_hero_and_find_ghosts(game: Game, walk: list) -> list:
    """Walk the hero (the camera scrolling with him) the given (key, blocks) legs, with the NPCs standing still. Returns
    the frames on which anything on screen differed from a clean redraw."""
    held_keys = defaultdict(int)
    ghost_frames = []
    frame = 0
    with patch('src.game.get_ticks', return_value=0), \
            patch('src.movement.key.get_pressed', return_value=held_keys):
        for walk_key, blocks in walk:
            held_keys.clear()
            held_keys[walk_key] = 1
            for _ in range(blocks * game.tile_size // game.movement.speed + 1):
                frame += 1
                game.movement.handle_player_movement()
                drawn = characters_to_draw(game)
                draw_frame(game)
                if not visible_area_matches_a_clean_redraw(game, drawn):
                    ghost_frames.append(frame)
            held_keys.clear()
            while game.player.is_moving:
                game.movement.handle_player_movement()
            set_character_position(game.player, game.tile_size)
    return ghost_frames


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

        def roam(_frame):
            game.movement.do_sprites()

        residue = find_residue(game, before_drawing=roam)
        self.assertNotEqual(start_positions, [character.rect.topleft for character in roaming_characters])
        self.assertEqual({}, residue)

    def test_residue_is_detected_when_the_tile_under_a_character_is_not_redrawn(self):
        # The bug in #98: the tile under the MAN wasn't among the tiles redrawn each frame. Brecconary's roaming NPCs
        # (#223) stand on every other tile type, so the tiles around them are left out too.
        game = make_game('Brecconary')
        with patch('src.drawer.get_fixed_character_underlying_tiles', return_value=[]), \
                patch('src.drawer.Drawer.get_all_roaming_character_surrounding_tiles', return_value=[]):
            residue = find_residue(game)
        self.assertIn('MAN_2', residue)

    def test_npcs_off_screen_leave_no_ghosts_when_the_camera_scrolls_to_them(self):
        # Garinham's WOMAN_2 starts five blocks right of the screen. Steps she took off screen used to leave her old
        # frames on the background: the tiles under roaming NPCs were only redrawn within two blocks of the screen,
        # so the hero walking right then scrolled ghosts of her into view at the right edge. She (and the other
        # roaming NPCs) walk down before the hero sets off, or left (toward him) while he walks right.
        for scale in (1, 2):
            for npc_direction, hero_waits in ((Direction.DOWN, 50), (Direction.LEFT, 0)):
                with self.subTest(scale=scale, npc_direction=npc_direction.name, hero_waits=hero_waits):
                    game = make_game('Garinham', scale)
                    self.assertEqual(16 * scale, game.tile_size)
                    woman = game.current_map.characters['WOMAN_2']['character']
                    self.assertEqual(((15, 9), (13, 21)), ((game.player.row, game.player.column),
                                                           (woman.row, woman.column)))
                    self.assertEqual([], walk_and_find_ghosts(game, 'WOMAN_2', npc_direction, 2, hero_waits,
                                                              hero_steps=6))

    def test_the_hero_leaves_no_trail_in_any_direction(self):
        # The blocks redrawn around the walking hero were 2.04 blocks square from a block up and left of him, which
        # Rect cut to 2 at SCALE 1, so walking up or left left the bottom or right edge of his last frame behind.
        for scale in (1, 2):
            with self.subTest(scale=scale):
                game = make_game('Garinham', scale)
                start = (game.player.row, game.player.column)
                self.assertEqual([], walk_hero_and_find_ghosts(game, [(K_RIGHT, 3), (K_UP, 1), (K_DOWN, 1),
                                                                      (K_LEFT, 3)]))
                self.assertEqual(start, (game.player.row, game.player.column))

    def test_every_block_has_only_the_map_tile(self):
        # Each NPC also got its "underlying" tile (BRICK, or a per-map override) on top of the map's own
        # tile there, e.g. Brecconary's MAN_3 got GRASS on brick. The block (or a roaming NPC's starting block, once
        # it walked away) then showed one or the other, depending on which tile types were being redrawn.
        for start_map in ('Brecconary', 'Garinham', 'Kol', 'Cantlin', 'Rimuldar', 'TantegelCourtyard',
                          'TantegelThroneRoom'):
            with self.subTest(start_map=start_map):
                game = make_game(start_map)
                tile_size = game.tile_size
                layout = game.current_map.layout
                wrong_tiles = [(tile, sprite.rect.y // tile_size, sprite.rect.x // tile_size)
                               for tile, tile_dict in game.current_map.floor_tile_key.items() if tile_dict.get('group')
                               for sprite in tile_dict['group']
                               if game.current_map.get_tile_by_value(layout[sprite.rect.y // tile_size][
                                   sprite.rect.x // tile_size]) != tile]
                self.assertEqual([], wrong_tiles)


def find_ghosts_drawing_every(game: Game, frames_per_draw: int, frames: int, held_key: int | None = None) -> list:
    """Run frames on the map (the hero, holding held_key, and the roaming NPCs) and draw only every frames_per_draw-th
    one, as the main loop does when drawing can't keep up with the game speed (Game.run_due_frames). Returns the draws
    on which anything on screen differed from a clean redraw."""
    held_keys = defaultdict(int)
    if held_key is not None:
        held_keys[held_key] = 1
    ghost_frames = []
    with patch('src.movement.random', random.Random(1)), patch('src.movement.key.get_pressed', return_value=held_keys):
        for frame in range(1, frames + 1):
            game.movement.handle_player_movement()
            if not game.player.is_moving:
                set_character_position(game.player, game.tile_size)
            game.movement.do_sprites()
            if frame % frames_per_draw == 0:
                drawn = characters_to_draw(game)
                draw_frame(game)
                if not visible_area_matches_a_clean_redraw(game, drawn):
                    ghost_frames.append(frame)
    return ghost_frames


class TestSkippedDraws(TestCase):
    """At a high game speed the main loop may run up to 8 frames between two draws (Game.run_due_frames): the tiles
    redrawn around the characters still cover everywhere they were drawn last."""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_the_walking_hero_leaves_no_trail(self):
        for frames_per_draw in (2, 3, 5, 8):
            with self.subTest(frames_per_draw=frames_per_draw):
                game = make_game('Garinham')
                start_column = game.player.column
                self.assertEqual([], find_ghosts_drawing_every(game, frames_per_draw, 4 * 16, K_RIGHT))
                self.assertGreater(game.player.column, start_column + 2)

    def test_roaming_npcs_leave_no_ghosts(self):
        for frames_per_draw in (2, 3, 5, 8):
            with self.subTest(frames_per_draw=frames_per_draw):
                game = make_game('TantegelCourtyard')
                npcs = game.current_map.roaming_characters
                start_positions = [npc.rect.topleft for npc in npcs]
                self.assertEqual([], find_ghosts_drawing_every(game, frames_per_draw, 3 * 80))
                self.assertNotEqual(start_positions, [npc.rect.topleft for npc in npcs])
