"""The widescreen view (src/view.py, #411): VIEW NES (4:3) or WIDE.

In the WIDE view the display is wider and the game's screen is the NES-sized area in its middle, so everything drawn
on the screen (the windows above all) is where the NES view has it, and the 4:3 middle of every wide frame is the NES
frame byte for byte. The map goes on to the left and right, with the map's border block beyond its edges; the
darkness, the fades and the flashes cover the whole width."""
import hashlib
import os
import tempfile
import random
from collections import defaultdict
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import K_F11, K_LEFT, K_RIGHT, KEYDOWN, Rect, Surface
from pygame.event import Event

from src import zoom
from src.config.test_config import test_config
from src.display_filters import SCALING_PIXEL_PERFECT, presentation_rect
from src.frame_recorder import recording
from src.game import Game
from src.settings import load_settings
from src.maps import map_lookup
from src.options_overlay import OptionsOverlay
from src.view import NES_WIDTH, VIEW_NES, VIEW_WIDE, full_screen, screen_origin_x, view_width, wide_aspect, \
    wide_view, wide_width
from src.visual_effects import cut_to_black, nes_palette_fade
from tests.test_character_redraw import draw_frame

SCALE = test_config['SCALE']
TILE = test_config['TILE_SIZE']
WIDE_16_9 = 426  # NES pixels across


def make_game(start_map: str, view: str = VIEW_WIDE, **overrides) -> Game:
    config = {**test_config, 'START_MAP': start_map, 'NO_BLIT': False, 'NO_WAIT': True, 'RENDER_TEXT': False,
              'VIEW': view, **overrides}
    with patch('src.game.SCALED', 0), patch('src.view.wide_aspect', return_value=16 / 9):
        game = Game(config)
    game.game_state.enable_animate = True
    return game


def surface_bytes(surface: Surface) -> bytes:
    return pygame.image.tobytes(surface, 'RGB')


def middle(game: Game) -> bytes:
    """The 4:3 middle of the whole picture."""
    return surface_bytes(full_screen(game.screen).subsurface(Rect(screen_origin_x(game.screen), 0, 512, 480)))


def walk(game: Game, frames: int = 40, before_frame=None) -> list[bytes]:
    """The pictures of the hero walking left then right (the 4:3 middle of each, and a hash of the whole)."""
    random.seed(411)
    held_keys: defaultdict = defaultdict(int)
    pictures = []
    with patch('src.game.get_ticks', return_value=0), patch('src.movement.key.get_pressed', return_value=held_keys):
        for frame in range(frames):
            held_keys.clear()
            held_keys[K_LEFT if frame < frames // 2 else K_RIGHT] = 1
            game.movement.handle_player_movement()
            game.movement.sprites_frame()
            draw_frame(game)
            if before_frame:
                before_frame(game)
            pictures.append(middle(game))
    return pictures


class DisplayTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()


class TestWidth(TestCase):

    def test_16_9_and_16_10(self):
        self.assertEqual(426, wide_width(16 / 9))
        self.assertEqual(384, wide_width(16 / 10))
        self.assertEqual(NES_WIDTH, wide_width(1.0))

    def test_the_desktop_gives_the_shape(self):
        self.assertAlmostEqual(16 / 9, wide_aspect([(1920, 1080)]))
        self.assertAlmostEqual(16 / 10, wide_aspect([(2560, 1600)]))
        self.assertAlmostEqual(4 / 3, wide_aspect([(1024, 768)]))
        self.assertAlmostEqual(16 / 9, wide_aspect([(3440, 1440)]))  # 21:9: 16:9 at most
        self.assertAlmostEqual(16 / 9, wide_aspect([(1080, 1920)]))  # no wider than the NES view: 16:9
        self.assertAlmostEqual(16 / 9, wide_aspect([]))

    def test_nes_view_is_the_nes_width(self):
        self.assertEqual(NES_WIDTH, view_width({'VIEW': VIEW_NES}, 16 / 9))
        self.assertEqual(NES_WIDTH, view_width({}, 16 / 9))
        self.assertEqual(WIDE_16_9, view_width({'VIEW': VIEW_WIDE}, 16 / 9))


class TestPixelPerfect(TestCase):

    def test_whole_multiples_of_the_wide_picture(self):
        # PIXEL PERFECT (src/display_filters.py) scales the WIDE surface by whole multiples of its own NES size
        self.assertEqual(Rect(0, 0, WIDE_16_9 * 4, 960), presentation_rect(
            (WIDE_16_9 * 4, 1080), (WIDE_16_9 * SCALE, 480), SCALING_PIXEL_PERFECT, True).move(0, -60))
        self.assertEqual((WIDE_16_9 * 2, 480), presentation_rect((1000, 700), (WIDE_16_9 * SCALE, 480),
                                                                  SCALING_PIXEL_PERFECT, False).size)
        self.assertEqual((768, 720), presentation_rect((1000, 900), (512, 480), SCALING_PIXEL_PERFECT, False).size)


class TestScreen(DisplayTestCase):

    def test_nes_view_draws_on_the_display_itself(self):
        game = make_game('TantegelThroneRoom', VIEW_NES)
        self.assertIs(pygame.display.get_surface(), game.screen)
        self.assertIsNone(wide_view())
        self.assertIs(game.screen, full_screen(game.screen))

    def test_wide_screen_is_the_middle_of_the_display(self):
        game = make_game('TantegelThroneRoom')
        display_surface = pygame.display.get_surface()
        self.assertEqual((WIDE_16_9 * SCALE, 480), display_surface.get_size())
        self.assertEqual((512, 480), game.screen.get_size())
        self.assertIs(display_surface, game.screen.get_parent())
        self.assertEqual(((WIDE_16_9 - NES_WIDTH) // 2 * SCALE, 0), game.screen.get_offset())
        self.assertIs(display_surface, full_screen(game.screen))
        self.assertIs(game.screen, game.cmd_menu.screen)

    def test_the_view_option_changes_the_window(self):
        game = make_game('Brecconary', VIEW_NES)
        game.game_state.config['VIEW'] = VIEW_WIDE
        with patch('src.view.wide_aspect', return_value=16 / 9):
            game.set_view()
        self.assertEqual(WIDE_16_9 * SCALE, pygame.display.get_surface().get_width())
        self.assertIs(game.screen, game.cmd_menu.screen)
        self.assertIs(game.screen, game.camera.screen)
        draw_frame(game)
        self.assertNotEqual(surface_bytes(Surface((12, 480))), surface_bytes(
            pygame.display.get_surface().subsurface(Rect(0, 0, 12, 480))), "the map on the left")
        game.game_state.config['VIEW'] = VIEW_NES
        game.set_view()
        self.assertEqual(512, pygame.display.get_surface().get_width())
        self.assertIs(pygame.display.get_surface(), game.screen)

    def test_the_view_row_is_a_global_setting(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'settings.json')
            game = make_game('Brecconary', VIEW_NES, SETTINGS_PATH=path)
            game.game_state.config['VIEW'] = VIEW_WIDE
            game.apply_option('VIEW')
            self.assertEqual(VIEW_WIDE, load_settings(path).view)
            again = make_game('Brecconary', VIEW_NES, SETTINGS_PATH=path)
            self.assertEqual(VIEW_WIDE, again.game_state.config['VIEW'])
            self.assertEqual(WIDE_16_9 * SCALE, pygame.display.get_surface().get_width())

    def test_the_overlay_sets_the_view_when_it_closes(self):
        game = make_game('Brecconary', VIEW_NES)

        def choose_wide(overlay):
            overlay.config['VIEW'] = VIEW_WIDE
        with patch.object(OptionsOverlay, 'run', choose_wide), patch('src.view.wide_aspect', return_value=16 / 9):
            game.open_options()
        self.assertEqual(WIDE_16_9 * SCALE, pygame.display.get_surface().get_width())

    def test_fullscreen_toggle_keeps_the_view(self):
        # F11 makes the window again (the flags patched out: the dummy driver has no fullscreen SCALED renderer, and
        # its plain fullscreen is the desktop's size): the screen is made again on the new display surface, in the view
        # it had
        game = make_game('Brecconary')
        for _ in range(2):
            with patch('src.view.wide_aspect', return_value=16 / 9), patch('src.game.SCALED', 0), \
                    patch('src.game.FULLSCREEN', 0), patch.object(game, 'draw_temporary_text'):
                game.handle_fullscreen_toggle(Event(KEYDOWN, key=K_F11, mod=0))
            self.assertEqual((WIDE_16_9 * SCALE, 480), pygame.display.get_surface().get_size())
            self.assertIs(pygame.display.get_surface(), game.screen.get_parent())
            self.assertIs(game.screen, game.cmd_menu.screen)
            self.assertIs(game.screen, game.camera.screen)
        draw_frame(game)
        self.assertEqual(middle(game), surface_bytes(game.screen))

    def test_zoom_steps_are_whole_multiples_of_the_wide_picture(self):
        pygame.display.set_mode((WIDE_16_9 * SCALE, 480))
        self.assertEqual(WIDE_16_9, zoom.nes_width())
        pygame.display.set_mode((512, 480))
        self.assertEqual(NES_WIDTH, zoom.nes_width())


class TestWideFrames(DisplayTestCase):

    def test_the_middle_is_the_nes_frame(self):
        for map_name in ('Brecconary', 'Alefgard', 'TantegelCourtyard', 'SwampCave'):
            with self.subTest(map_name=map_name):
                nes = walk(make_game(map_name, VIEW_NES))
                wide = walk(make_game(map_name))
                self.assertEqual(nes, wide)

    def test_windows_stay_in_the_middle(self):
        # The pop-up stats window and the COMMAND window, drawn as in the NES view
        def windows(game):
            game.drawer.draw_hovering_stats_window(game.screen, game.player)
            game.cmd_menu.draw_command_window()
        # The COMMAND cursor blinks on the menu clock (src/cursor.py), not the game clock walk stops: stopped too, so
        # both walks draw it at the same point of its blink however long they take
        with patch('src.cursor.get_ticks', return_value=0):
            self.assertEqual(walk(make_game('Brecconary', VIEW_NES), 4, windows),
                             walk(make_game('Brecconary'), 4, windows))

    def test_the_sides_show_the_map(self):
        game = make_game('Alefgard')
        draw_frame(game)
        whole = full_screen(game.screen)
        x, y = int(game.camera.pos[0]) + screen_origin_x(game.screen), int(game.camera.pos[1])
        expected = Surface(whole.get_size())
        expected.blit(game.drawer.background, (x, y))
        for side in (Rect(0, 0, screen_origin_x(game.screen), 480),
                     Rect(screen_origin_x(game.screen) + 512, 0, screen_origin_x(game.screen), 480)):
            self.assertEqual(surface_bytes(expected.subsurface(side)), surface_bytes(whole.subsurface(side)))
        # the hero's half block right of the middle of the whole picture, as in the NES view
        hero = game.player.rect.move(x, y)
        self.assertEqual(whole.get_width() // 2, hero.left)

    def test_the_border_block_is_off_the_map(self):
        for map_name, coordinates in (('Alefgard', (10, 10)), ('Brecconary', None), ('Garinham', None)):
            with self.subTest(map_name=map_name):
                game = make_game(map_name, ENABLE_DARKNESS=False)
                if coordinates:
                    with patch('src.map_manager.screen_fade'):
                        game.map_mgr.change_map(map_lookup[map_name](game.config), destination_coordinates=coordinates)
                draw_frame(game)
                whole = full_screen(game.screen)
                x, y = int(game.camera.pos[0]) + screen_origin_x(game.screen), int(game.camera.pos[1])
                current_map = game.current_map
                border = surface_bytes(current_map.floor_tile_image(
                    current_map.floor_tile_key[current_map.boundary_tile]['val']))
                off_map = [Rect(column, row, TILE, TILE)
                           for column in range(x % TILE - TILE, whole.get_width(), TILE)
                           for row in range(y % TILE - TILE, whole.get_height(), TILE)
                           if not game.drawer.background.get_rect(topleft=(x, y)).colliderect(
                               Rect(column, row, TILE, TILE))
                           and whole.get_rect().contains(Rect(column, row, TILE, TILE))]
                self.assertTrue(off_map, "some of the view is off the map")
                for block in off_map:
                    self.assertEqual(border, surface_bytes(whole.subsurface(block)))

    def test_darkness_covers_the_sides(self):
        game = make_game('SwampCave')
        draw_frame(game)
        whole = full_screen(game.screen)
        origin_x = screen_origin_x(game.screen)
        black = surface_bytes(Surface((origin_x, 480)))
        self.assertEqual(black, surface_bytes(whole.subsurface(Rect(0, 0, origin_x, 480))))
        self.assertEqual(black, surface_bytes(whole.subsurface(Rect(origin_x + 512, 0, origin_x, 480))))


class TestWholePictureEffects(DisplayTestCase):

    def test_cut_to_black_and_fade_out_cover_the_whole_width(self):
        for effect in (lambda game: cut_to_black(game.screen, game.game_state.config),
                       lambda game: nes_palette_fade(True, game.screen, game.game_state.config)):
            game = make_game('Alefgard')
            draw_frame(game)
            effect(game)
            whole = full_screen(game.screen)
            self.assertEqual(surface_bytes(Surface(whole.get_size())), surface_bytes(whole))

    def test_the_overlay_darkens_the_whole_width_and_puts_it_back(self):
        game = make_game('Alefgard')
        draw_frame(game)
        whole = full_screen(game.screen)
        before = surface_bytes(whole)
        corner = whole.get_at((2, 2))
        shown = []

        def capture(*_args, **_kwargs):
            shown.append((whole.get_at((2, 2)), middle(game)))
        overlay = OptionsOverlay(game)
        with patch('src.options_overlay.display.update', side_effect=capture):
            overlay.draw(whole.copy(), 0, True)
            overlay.close(pygame.image.frombytes(before, whole.get_size(), 'RGB'))
        self.assertLess(sum(shown[0][0][:3]), sum(corner[:3]))
        self.assertEqual(before, surface_bytes(whole))
        # the window over the middle is the NES view's
        nes = make_game('Alefgard', VIEW_NES)
        nes.game_state.config['VIEW'] = VIEW_WIDE  # the VIEW row's value, without changing the view
        draw_frame(nes)
        nes_overlay = OptionsOverlay(nes)
        with patch('src.options_overlay.display.update'):
            nes_overlay.draw(nes.screen.copy(), 0, True)
        self.assertEqual(surface_bytes(nes.screen), shown[0][1])

    def test_the_frame_recorder_records_the_whole_width(self):
        game = make_game('Alefgard')
        draw_frame(game)
        with recording() as frames:
            pygame.display.flip()
        self.assertEqual((WIDE_16_9 * SCALE, 480), frames[0].size)
        self.assertEqual(hashlib.sha256(surface_bytes(full_screen(game.screen))).digest(),
                         hashlib.sha256(frames[0].pixels()).digest())
