"""The display filters (src/display_filters.py): SCANLINES and SCALING in the options overlay, kept with the global
settings; where the picture goes in windows of every size; and the scanlines are only ever drawn on the window, never
on the game's own screen surface."""
import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from pygame import K_DOWN, K_RIGHT, K_u, KEYDOWN, RESIZABLE, SCALED, Rect
from pygame._sdl2.video import Renderer, Window
from pygame.event import Event

from src import display_filters
from src.config.test_config import test_config
from src.display_filters import PRESENTER, SCALING_PIXEL_PERFECT, SCALING_SMOOTH, presentation_rect
from src.options_overlay import FIXED_ROWS, OPTION_PAGES, OptionsOverlay, options_layout
from src.settings import Settings, load_settings, save_settings
from src.waiting import reset_game_speed, set_speed_listener
from src.zoom import set_zoom_listener
from tests import helpers

SCREEN = (512, 480)  # NES_RES * SCALE
GAP = 2


def presses(*keys):
    results = []
    for pressed_key in keys:
        results += [[]] * GAP + [[Event(KEYDOWN, key=pressed_key, mod=0)]]
    return results


class TestPresentationRect(TestCase):
    """Where the 512x480 screen surface goes in the window."""

    def test_pixel_perfect_whole_nes_multiples_centred(self):
        cases = {
            (512, 480): Rect(0, 0, 512, 480),  # 2x, the window's normal size
            (768, 720): Rect(0, 0, 768, 720),  # 3x: each NES pixel 3x3 window pixels
            (1000, 900): Rect(116, 90, 768, 720),  # 3x with black borders
            (1920, 1080): Rect(448, 60, 1024, 960),  # 4x, a 1080p screen
            (2560, 1440): Rect(512, 0, 1536, 1440),  # 6x
            (3840, 2160): Rect(768, 0, 2304, 2160),  # 9x, a 4K screen
        }
        for window, expected in cases.items():
            with self.subTest(window=window):
                for fullscreen in (False, True):
                    self.assertEqual(expected, presentation_rect(window, SCREEN, SCALING_PIXEL_PERFECT, fullscreen))

    def test_pixel_perfect_factor_is_whole(self):
        for width in range(256, 4000, 37):
            for height in range(240, 2400, 53):
                rect = presentation_rect((width, height), SCREEN, SCALING_PIXEL_PERFECT, False)
                factor = rect.width // 256
                self.assertEqual((256 * factor, 240 * factor), rect.size)
                self.assertTrue(Rect(0, 0, width, height).contains(rect))
                # the biggest that fits
                self.assertTrue(256 * (factor + 1) > width or 240 * (factor + 1) > height)
                # centred
                self.assertLessEqual(abs((width - rect.right) - rect.left), 1)
                self.assertLessEqual(abs((height - rect.bottom) - rect.top), 1)

    def test_a_window_smaller_than_the_nes_screen_still_shows_it_at_1x(self):
        self.assertEqual((256, 240), presentation_rect((200, 200), SCREEN, SCALING_PIXEL_PERFECT, False).size)

    def test_smooth_is_what_pygames_scaled_does(self):
        # in a window, whole multiples of the 512x480 surface (pygame turns on SDL's integer scaling there)
        self.assertEqual(Rect(128, 120, 512, 480), presentation_rect((768, 720), SCREEN, SCALING_SMOOTH, False))
        self.assertEqual(Rect(0, 0, 1024, 960), presentation_rect((1024, 960), SCREEN, SCALING_SMOOTH, False))
        # in fullscreen, stretched to fit, keeping the shape
        self.assertEqual(Rect(448, 0, 1024, 960), presentation_rect((1920, 960), SCREEN, SCALING_SMOOTH, True))
        self.assertEqual(Rect(256, 0, 1536, 1440), presentation_rect((2048, 1440), SCREEN, SCALING_SMOOTH, True))
        stretched = presentation_rect((2560, 1600), SCREEN, SCALING_SMOOTH, True)
        self.assertEqual((1706, 1600), stretched.size)
        # a window smaller than the surface: shrunk to fit
        self.assertEqual((384, 360), presentation_rect((384, 360), SCREEN, SCALING_SMOOTH, False).size)


class TestScanlineRects(TestCase):

    def test_lower_half_of_each_nes_line_in_window_pixels(self):
        for factor, dark in ((1, ()), (2, (1,)), (3, (2,)), (4, (2, 3)), (5, (3, 4))):
            with self.subTest(factor=factor):
                rects = display_filters.scanline_rects(10, 20, 256 * factor, 240 * factor)
                rows = {row - 20 for x, y, width, height in rects for row in range(y, y + height)}
                self.assertEqual({line * factor + offset for line in range(240) for offset in dark}, rows)
                self.assertTrue(all((x, width) == (10, 256 * factor) for x, _, width, _ in rects))

    def test_a_stretched_picture_still_gets_240_lines(self):
        rects = display_filters.scanline_rects(0, 0, 1706, 1600)
        self.assertEqual(240, len(rects))
        self.assertLessEqual(rects[-1][1] + rects[-1][3], 1600)


def open_scaled_window():
    """A SCALED window, as the game opens it (under SDL's dummy driver it has a software renderer). The display is
    restarted first: the dummy driver can't open a SCALED window over another one (see tests/test_zoom.py)."""
    PRESENTER.release()
    pygame.display.quit()
    pygame.display.init()
    return pygame.display.set_mode(SCREEN, RESIZABLE | SCALED)


class PresenterTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.screen = open_scaled_window()
        self.addCleanup(PRESENTER.configure, False, SCALING_SMOOTH)
        # a picture with every NES line (2 lines of the surface, as the game draws them) different
        for y in range(SCREEN[1]):
            pygame.draw.line(self.screen, (200, (y // 2 * 7) % 256, 100), (0, y), (SCREEN[0] - 1, y))

    @classmethod
    def tearDownClass(cls):
        PRESENTER.release()
        pygame.display.quit()
        pygame.display.init()

    def shown(self):
        """What the window shows: read back from its renderer."""
        return Renderer.from_window(Window.from_display_module()).to_surface()


class TestPresenter(PresenterTestCase):

    def test_off_changes_nothing(self):
        real_flip, real_update = pygame.display.flip, pygame.display.update
        PRESENTER.configure(False, SCALING_SMOOTH)
        self.assertIs(real_flip, pygame.display.flip)
        self.assertIs(real_update, pygame.display.update)
        self.assertFalse(PRESENTER.active)

    def test_on_and_off_again(self):
        real_flip, real_update = pygame.display.flip, pygame.display.update
        PRESENTER.configure(True, SCALING_SMOOTH)
        self.assertIsNot(real_flip, pygame.display.flip)
        PRESENTER.configure(True, SCALING_PIXEL_PERFECT)  # changing filters doesn't wrap it twice
        PRESENTER.configure(False, SCALING_PIXEL_PERFECT)
        PRESENTER.configure(False, SCALING_SMOOTH)
        self.assertIs(real_flip, pygame.display.flip)
        self.assertIs(real_update, pygame.display.update)
        # pygame's own flip works again, over the logical size it set
        pygame.display.flip()
        self.assertEqual(SCREEN, tuple(Renderer.from_window(Window.from_display_module()).logical_size))

    def test_scanlines_never_touch_the_game_surface(self):
        before = pygame.image.tobytes(self.screen, 'RGB')
        PRESENTER.configure(True, SCALING_SMOOTH)
        pygame.display.flip()
        pygame.display.update(Rect(0, 0, 10, 10))
        self.assertEqual(before, pygame.image.tobytes(self.screen, 'RGB'))

    def test_scanlines_darken_the_lower_half_of_each_nes_line(self):
        PRESENTER.configure(True, SCALING_SMOOTH)
        pygame.display.flip()
        shown = self.shown()
        self.assertEqual(SCREEN, shown.get_size())
        for y in range(0, 40, 2):  # each NES line is 2 window pixels here
            with self.subTest(y=y):
                self.assertEqual(self.screen.get_at((5, y)), shown.get_at((5, y)))
                darker, original = shown.get_at((5, y + 1)), self.screen.get_at((5, y + 1))
                self.assertLess(darker.r, original.r)
                self.assertAlmostEqual(original.r * (255 - display_filters.SCANLINE_ALPHA) / 255, darker.r, delta=2)

    def test_without_filters_the_window_shows_the_surface(self):
        PRESENTER.configure(True, SCALING_SMOOTH)
        PRESENTER.configure(False, SCALING_SMOOTH)
        pygame.display.flip()
        self.assertEqual(pygame.image.tobytes(self.screen, 'RGB'), pygame.image.tobytes(self.shown(), 'RGB'))

    def test_pixel_perfect_with_black_borders(self):
        Window.from_display_module().size = (1000, 900)
        pygame.event.pump()
        PRESENTER.configure(False, SCALING_PIXEL_PERFECT)
        pygame.display.flip()
        shown = self.shown()
        self.assertEqual((1000, 900), shown.get_size())
        picture = Rect(116, 90, 768, 720)  # 3x
        self.assertEqual((0, 0, 0), tuple(shown.get_at((picture.left - 1, 450)))[:3])
        self.assertEqual((0, 0, 0), tuple(shown.get_at((500, picture.top - 1)))[:3])
        self.assertEqual((0, 0, 0), tuple(shown.get_at((picture.right, 450)))[:3])
        # each NES pixel (2x2 of the surface) is 3x3 window pixels
        for nes_y in range(0, 20):
            for window_y in range(picture.top + nes_y * 3, picture.top + nes_y * 3 + 3):
                self.assertEqual(self.screen.get_at((4, nes_y * 2)), shown.get_at((picture.left + 6, window_y)))

    def test_a_window_without_a_renderer_presents_as_always(self):
        # Under the dummy driver a window opened without SCALED has no renderer: the filters do nothing
        PRESENTER.release()
        with patch('src.display_filters.Renderer') as renderer:
            renderer.from_window.side_effect = pygame.error("no renderer")
            PRESENTER.configure(True, SCALING_PIXEL_PERFECT)
            with patch.object(PRESENTER, '_previous_flip') as previous_flip:
                pygame.display.flip()
            previous_flip.assert_called_once()

    def test_a_frame_recorder_on_top(self):
        from src.frame_recorder import FrameRecorder
        PRESENTER.configure(True, SCALING_SMOOTH)
        with FrameRecorder() as recorder:
            pygame.display.flip()
        # it recorded the game's own picture, without scanlines, and the window showed it with them
        self.assertEqual(1, len(recorder))
        self.assertEqual(pygame.image.tobytes(self.screen, 'RGB'), pygame.image.tobytes(recorder[0].surface(), 'RGB'))
        self.assertNotEqual(pygame.image.tobytes(self.screen, 'RGB'), pygame.image.tobytes(self.shown(), 'RGB'))
        self.assertIs(PRESENTER._flip, pygame.display.flip)


class TestOverlayRows(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.path = os.path.join(temp_dir.name, 'settings.json')
        self.addCleanup(set_zoom_listener, None)
        self.addCleanup(set_speed_listener, None)
        self.addCleanup(reset_game_speed)
        self.addCleanup(PRESENTER.configure, False, SCALING_SMOOTH)
        patch('src.selection.wait_frames').start()
        self.addCleanup(patch.stopall)

    def new_game(self):
        return helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True,
                                 'LANGUAGE': 'English', 'SETTINGS_PATH': self.path})

    def run_overlay(self, game, *keys):
        with patch('src.selection.event.get', side_effect=presses(*keys)):
            OptionsOverlay(game).run()

    def down_to(self, label):
        # the rows are on the first page (LOOK & SOUND), under PRESET and PAGE
        return (K_DOWN,) * (FIXED_ROWS + [row.label for row in OPTION_PAGES[0].rows].index(label))

    def test_off_by_default(self):
        game = self.new_game()
        texts = [text.text for text in options_layout(game.config).texts]
        self.assertEqual(["SCANLINES", "OFF", "SCALING", "SMOOTH"], texts[-4:])
        self.assertFalse(PRESENTER.active)

    def test_scanlines_row(self):
        game = self.new_game()
        self.run_overlay(game, *self.down_to("SCANLINES"), K_RIGHT, K_u)
        self.assertTrue(game.config['SCANLINES'])
        self.assertTrue(PRESENTER.scanlines)
        self.assertTrue(load_settings(self.path).scanlines)
        self.run_overlay(game, *self.down_to("SCANLINES"), K_RIGHT, K_u)
        self.assertFalse(PRESENTER.active)
        self.assertEqual(Settings(), load_settings(self.path))

    def test_scaling_row(self):
        game = self.new_game()
        self.run_overlay(game, *self.down_to("SCALING"), K_RIGHT, K_u)
        self.assertEqual(SCALING_PIXEL_PERFECT, game.config['SCALING'])
        self.assertEqual(SCALING_PIXEL_PERFECT, PRESENTER.scaling)
        self.assertEqual(SCALING_PIXEL_PERFECT, load_settings(self.path).scaling)
        texts = [text.text for text in options_layout(game.config).texts]
        self.assertEqual(["SCALING", "PIXEL PERFECT"], texts[-2:])

    def test_saved_filters_are_on_at_start(self):
        save_settings(self.path, Settings(scanlines=True, scaling=SCALING_PIXEL_PERFECT))
        game = self.new_game()
        self.assertEqual((True, SCALING_PIXEL_PERFECT), (game.config['SCANLINES'], game.config['SCALING']))
        self.assertEqual((True, SCALING_PIXEL_PERFECT), (PRESENTER.scanlines, PRESENTER.scaling))

    def test_a_new_game_without_them_turns_them_off(self):
        PRESENTER.configure(True, SCALING_PIXEL_PERFECT)
        self.new_game()
        self.assertFalse(PRESENTER.active)
