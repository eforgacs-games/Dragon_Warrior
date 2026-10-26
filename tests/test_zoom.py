"""The window zoom (src/zoom.py): Ctrl +, Ctrl -, Ctrl 0 and Ctrl with the mouse wheel change the window's size in whole
multiples of the NES's 256x240, between SCALE and what fits on the desktop, and change nothing else: the screen surface
the game draws on, TILE_SIZE and the game's state stay the same, and every other key is left for the game."""
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import K_0, K_1, K_EQUALS, K_KP_MINUS, K_KP_PLUS, K_MINUS, K_k, KEYDOWN, KMOD_CTRL, KMOD_LCTRL, \
    KMOD_NONE, MOUSEWHEEL, RESIZABLE, SCALED
from pygame.event import Event

from src import zoom
from src.config.test_config import test_config
from src.display_window import display_window
from src.selection import frame_events
from src.waiting import game_speed, get_events, reset_game_speed
from tests.helpers import new_game

# A 1920x1080 desktop: 1080 - 64 (DESKTOP_MARGIN) fits 4 x 240, so the zoom goes from SCALE (2x, the screen surface's
# size, which a SCALED window can't go below) to 4x
DESKTOP = [(1920, 1080)]
SCALE = test_config['SCALE']
LOGICAL_SIZE = (test_config['NES_RES'][0] * SCALE, test_config['NES_RES'][1] * SCALE)


# The WIDE view's screen (src/view.py): 426x240 NES pixels, 16:9
WIDE_NES_WIDTH = 426
WIDE_LOGICAL_SIZE = (WIDE_NES_WIDTH * SCALE, LOGICAL_SIZE[1])


def open_window(size=LOGICAL_SIZE):
    """Open the game's window the way Game does (SCALED, at its normal size). Under SDL's dummy driver a SCALED window
    can't be opened again over another one (no renderer), so the display is restarted first."""
    pygame.display.quit()
    pygame.display.init()
    return pygame.display.set_mode(size, RESIZABLE | SCALED)


def ctrl_key(key_code, mod=KMOD_LCTRL):
    return Event(KEYDOWN, key=key_code, mod=mod)


def wheel(y):
    return Event(MOUSEWHEEL, x=0, y=y, flipped=False)


class ZoomTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.quit()
        pygame.init()
        cls.make_game()
        open_window()
        zoom.remember_default_zoom()

    @classmethod
    def make_game(cls):
        """Subclasses that need a Game make it here, before the SCALED window is opened: under the dummy driver,
        opening a window without SCALED over a SCALED one crashes."""

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        desktop = patch('src.zoom.display.get_desktop_sizes', return_value=DESKTOP)
        desktop.start()
        self.addCleanup(desktop.stop)
        # a test may have opened the window again (leaving fullscreen)
        self.screen = pygame.display.get_surface()
        zoom.reset_zoom()

    def window_size(self):
        return pygame.display.get_window_size()

    def zoomed(self, level):
        return 256 * level, 240 * level


class TestZoomKeys(ZoomTestCase):

    def test_the_window_opens_at_the_default_zoom(self):
        self.assertEqual(self.zoomed(test_config['SCALE']), self.window_size())
        self.assertEqual(test_config['SCALE'], zoom.default_zoom())

    def test_ctrl_plus_zooms_in_one_step(self):
        for key_code in (K_EQUALS, K_KP_PLUS):
            with self.subTest(key=key_code):
                zoom.reset_zoom()
                self.assertTrue(zoom.handle_zoom_event(ctrl_key(key_code)))
                self.assertEqual(self.zoomed(3), self.window_size())

    def test_ctrl_minus_zooms_out_one_step(self):
        for key_code in (K_MINUS, K_KP_MINUS):
            with self.subTest(key=key_code):
                zoom.set_zoom(4)
                self.assertTrue(zoom.handle_zoom_event(ctrl_key(key_code)))
                self.assertEqual(self.zoomed(3), self.window_size())

    def test_ctrl_wheel_zooms(self):
        with patch('src.zoom.key.get_mods', return_value=KMOD_LCTRL):
            self.assertTrue(zoom.handle_zoom_event(wheel(1)))
            self.assertEqual(self.zoomed(3), self.window_size())
            self.assertTrue(zoom.handle_zoom_event(wheel(1)))
            self.assertEqual(self.zoomed(4), self.window_size())
            self.assertTrue(zoom.handle_zoom_event(wheel(-1)))
            self.assertEqual(self.zoomed(3), self.window_size())

    def test_the_wheel_without_ctrl_does_nothing(self):
        with patch('src.zoom.key.get_mods', return_value=KMOD_NONE):
            self.assertFalse(zoom.handle_zoom_event(wheel(1)))
        self.assertEqual(self.zoomed(SCALE), self.window_size())

    def test_each_change_is_told_to_the_listener(self):
        # The game saves the zoom with its global settings (src/settings.py) through this
        told = []
        zoom.set_zoom_listener(told.append)
        self.addCleanup(zoom.set_zoom_listener, None)
        zoom.handle_zoom_event(ctrl_key(K_EQUALS))
        zoom.set_zoom(3)  # no change: nothing told
        zoom.reset_zoom()
        self.assertEqual([3, SCALE], told)

    def test_zoom_stays_within_bounds(self):
        for _ in range(10):
            zoom.handle_zoom_event(ctrl_key(K_EQUALS))
        self.assertEqual(self.zoomed(4), self.window_size())
        self.assertFalse(zoom.zoom_in())
        for _ in range(10):
            zoom.handle_zoom_event(ctrl_key(K_MINUS))
        self.assertEqual(self.zoomed(SCALE), self.window_size())
        self.assertFalse(zoom.zoom_out())
        self.assertFalse(zoom.set_zoom(1))  # never smaller than the screen surface
        self.assertEqual(self.zoomed(SCALE), self.window_size())

    def test_max_zoom_follows_the_desktop(self):
        with patch('src.zoom.display.get_desktop_sizes', return_value=[(2560, 1440)]):
            self.assertEqual(5, zoom.max_zoom())
        with patch('src.zoom.display.get_desktop_sizes', return_value=[(1920, 1080), (2560, 1440)]):
            self.assertEqual(5, zoom.max_zoom())  # the biggest monitor
        with patch('src.zoom.display.get_desktop_sizes', return_value=[(200, 200)]):
            # too small a desktop: still the window's own size
            self.assertEqual(SCALE, zoom.max_zoom())
            self.assertFalse(zoom.zoom_in())

    def test_ctrl_0_resets_the_zoom(self):
        zoom.handle_zoom_event(ctrl_key(K_EQUALS))
        zoom.handle_zoom_event(ctrl_key(K_EQUALS))
        self.assertEqual(self.zoomed(4), self.window_size())
        self.assertTrue(zoom.handle_zoom_event(ctrl_key(K_0)))
        self.assertEqual(self.zoomed(SCALE), self.window_size())

    def test_a_dragged_window_steps_to_the_next_whole_zoom(self):
        display_window().size = (900, 840)  # 3.5x
        zoom.zoom_in()
        self.assertEqual(self.zoomed(4), self.window_size())
        display_window().size = (900, 840)
        zoom.zoom_out()
        self.assertEqual(self.zoomed(3), self.window_size())

    def test_a_window_dragged_to_a_new_size_saves_the_nearest_zoom(self):
        # Dragging the window's edge (#430): the window stays as dragged, SCALED stretching the screen to it, and the
        # nearest whole zoom goes to the listener (the global settings), for the next launch
        zooms = []
        zoom.set_zoom_listener(zooms.append)
        self.addCleanup(zoom.set_zoom_listener, None)
        window = display_window()
        for size, expected in (((900, 840), 4), ((800, 730), 3), ((300, 280), SCALE), ((5000, 4000), 4)):
            with self.subTest(size=size):
                window.size = size
                actual = self.window_size()
                for resize_event in (Event(pygame.VIDEORESIZE, w=size[0], h=size[1], size=size),
                                     Event(pygame.WINDOWSIZECHANGED, x=size[0], y=size[1])):
                    self.assertFalse(zoom.handle_zoom_event(resize_event))  # left for the loop
                self.assertEqual([expected, expected], zooms[-2:])
                self.assertEqual(actual, self.window_size())  # not snapped to a whole zoom

    def test_a_resize_in_fullscreen_saves_nothing(self):
        zooms = []
        zoom.set_zoom_listener(zooms.append)
        self.addCleanup(zoom.set_zoom_listener, None)
        with patch('src.zoom.is_fullscreen', return_value=True):
            zoom.handle_zoom_event(Event(pygame.VIDEORESIZE, w=1920, h=1080, size=(1920, 1080)))
        self.assertEqual([], zooms)

    def test_the_screen_surface_is_unchanged(self):
        zoom.handle_zoom_event(ctrl_key(K_EQUALS))
        self.assertIs(self.screen, pygame.display.get_surface())
        self.assertEqual(LOGICAL_SIZE, pygame.display.get_surface().get_size())

    def test_other_keys_are_left_alone(self):
        for current_event in (ctrl_key(K_k), ctrl_key(K_1), Event(KEYDOWN, key=K_EQUALS, mod=KMOD_NONE),
                              Event(KEYDOWN, key=K_MINUS, mod=KMOD_NONE), Event(KEYDOWN, key=K_0, mod=KMOD_NONE)):
            with self.subTest(event=current_event):
                self.assertFalse(zoom.handle_zoom_event(current_event))
                self.assertEqual(self.zoomed(SCALE), self.window_size())

    def test_no_zoom_in_fullscreen(self):
        with patch('src.zoom.is_fullscreen', return_value=True):
            self.assertTrue(zoom.handle_zoom_event(ctrl_key(K_EQUALS)))
        self.assertEqual(self.zoomed(SCALE), self.window_size())

    def test_leaving_fullscreen_restores_the_zoomed_window(self):
        zoom.zoom_in()
        zoom.remember_windowed_size()
        open_window()  # what F11 does on the way back to a window
        self.assertEqual(self.zoomed(SCALE), self.window_size())
        zoom.restore_windowed_size()
        self.assertEqual(self.zoomed(3), self.window_size())


    def test_a_saved_zoom_for_a_game_opened_in_fullscreen_is_wide_in_the_wide_view(self):
        self.addCleanup(open_window)
        open_window(WIDE_LOGICAL_SIZE)
        zoom.set_windowed_zoom(3)
        zoom.restore_windowed_size()
        self.assertEqual((WIDE_NES_WIDTH * 3, 240 * 3), self.window_size())

    def test_a_view_changed_in_fullscreen_keeps_the_zoom(self):
        # 3x in the NES view, then fullscreen, then VIEW: WIDE (Game.set_view makes the window again, still fullscreen),
        # then back to a window: 3x of the wide picture
        self.addCleanup(open_window)
        zoom.zoom_in()
        zoom.remember_windowed_size()
        open_window(WIDE_LOGICAL_SIZE)
        zoom.restore_windowed_size()
        self.assertEqual((WIDE_NES_WIDTH * 3, 240 * 3), self.window_size())


class TestZoomInEveryLoop(ZoomTestCase):
    """The menus, dialogs and battles read the queue through get_events or frame_events: the zoom keys work there and
    are taken out, so no window reads them as a key, while the other keys stay."""

    def setUp(self):
        super().setUp()
        reset_game_speed()
        self.addCleanup(reset_game_speed)

    def test_get_events_zooms_and_takes_the_keys_out(self):
        for read_events in (get_events, frame_events):
            with self.subTest(loop=read_events.__name__):
                zoom.reset_zoom()
                pygame.event.clear()
                pygame.event.post(ctrl_key(K_EQUALS))
                pygame.event.post(Event(KEYDOWN, key=K_k, mod=KMOD_NONE))
                pygame.event.post(Event(KEYDOWN, key=pygame.K_2, mod=KMOD_NONE))
                keys = [current_event.key for current_event in read_events() if current_event.type == KEYDOWN]
                self.assertEqual([K_k], keys)
                self.assertEqual(self.zoomed(3), self.window_size())
                self.assertEqual(2, game_speed())  # the speed keys still work alongside
                reset_game_speed()


class TestZoomOnTheMap(ZoomTestCase):

    @classmethod
    def make_game(cls):
        pygame.mixer.init()
        pygame.display.set_mode((800, 600))  # the way tests/test_game.py makes its Game
        test_config['NO_WAIT'] = True
        cls.game = new_game()

    def setUp(self):
        super().setUp()
        self.game.screen = self.screen

    def test_zoom_keys_on_the_map_change_only_the_window(self):
        tile_size = self.game.game_state.config['TILE_SIZE']
        player_position = (self.game.player.column, self.game.player.row, self.game.player.direction_value)
        with patch.object(self.game, 'handle_keypresses') as handle_keypresses:
            pygame.event.clear()
            pygame.event.post(ctrl_key(K_KP_PLUS, mod=KMOD_CTRL))
            self.game.read_events()
        handle_keypresses.assert_not_called()  # the game never sees the key
        self.assertEqual(self.zoomed(3), self.window_size())
        self.assertEqual(tile_size, self.game.game_state.config['TILE_SIZE'])
        self.assertEqual(16 * test_config['SCALE'], self.game.tile_size)
        self.assertEqual(LOGICAL_SIZE, self.game.screen.get_size())
        self.assertEqual(player_position,
                         (self.game.player.column, self.game.player.row, self.game.player.direction_value))
        self.assertEqual(1, game_speed())

    def test_other_keys_on_the_map_still_reach_the_game(self):
        with patch.object(self.game, 'handle_keypresses') as handle_keypresses:
            pygame.event.clear()
            pygame.event.post(Event(KEYDOWN, key=K_k, mod=KMOD_NONE))
            self.game.read_events()
        handle_keypresses.assert_called_once()
        self.assertEqual(self.zoomed(SCALE), self.window_size())

    def test_f11_back_to_a_window_keeps_the_zoom(self):
        zoom.zoom_in()
        with patch('src.game.set_mode', return_value=self.game.screen) as set_mode, \
                patch.object(self.game, 'draw_temporary_text'), \
                patch('src.zoom.is_fullscreen', return_value=False):
            self.game.fullscreen_enabled = False
            self.game.handle_fullscreen_toggle(Event(KEYDOWN, key=pygame.K_F11, mod=KMOD_NONE))  # to fullscreen
            open_window()  # the window opens at its first size again
            self.game.handle_fullscreen_toggle(Event(KEYDOWN, key=pygame.K_F11, mod=KMOD_NONE))  # back
        self.assertEqual(2, set_mode.call_count)
        self.assertEqual(self.zoomed(3), self.window_size())
