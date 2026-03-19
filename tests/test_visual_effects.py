import os
import unittest
from unittest.mock import patch, MagicMock, call

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from src.visual_effects import draw_transparent_color, flash_transparent_color


class TestDrawTransparentColor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((100, 100))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_draw_transparent_color_no_blit(self):
        # When no_blit=True, should NOT call screen.blit
        mock_screen = MagicMock()
        mock_screen.get_width.return_value = 100
        mock_screen.get_height.return_value = 100
        draw_transparent_color((255, 0, 0), mock_screen, 128, no_blit=True)
        mock_screen.blit.assert_not_called()

    def test_draw_transparent_color_with_blit(self):
        # When no_blit=False, should call screen.blit
        mock_screen = MagicMock()
        mock_screen.get_width.return_value = 100
        mock_screen.get_height.return_value = 100
        draw_transparent_color((255, 0, 0), mock_screen, 128, no_blit=False)
        mock_screen.blit.assert_called_once()

    def test_draw_transparent_color_blit_position(self):
        mock_screen = MagicMock()
        mock_screen.get_width.return_value = 200
        mock_screen.get_height.return_value = 150
        draw_transparent_color((0, 255, 0), mock_screen, 64, no_blit=False)
        # Should blit at (0, 0)
        args = mock_screen.blit.call_args
        self.assertEqual(args[0][1], (0, 0))


class TestFade(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((100, 100))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_fade_out_no_blit_no_wait(self):
        from src.visual_effects import fade
        config = {'NO_BLIT': True, 'NO_WAIT': True}
        mock_screen = MagicMock()
        mock_screen.get_width.return_value = 100
        mock_screen.get_height.return_value = 100
        with patch('src.visual_effects.display') as mock_display:
            # Should not raise
            fade(fade_out=True, screen=mock_screen, config=config)

    def test_fade_in_no_blit_no_wait(self):
        from src.visual_effects import fade
        config = {'NO_BLIT': True, 'NO_WAIT': True}
        mock_screen = MagicMock()
        mock_screen.get_width.return_value = 100
        mock_screen.get_height.return_value = 100
        mock_screen.copy.return_value = MagicMock()
        with patch('src.visual_effects.display') as mock_display:
            fade(fade_out=False, screen=mock_screen, config=config)

    def test_fade_in_with_draw_callback(self):
        from src.visual_effects import fade
        config = {'NO_BLIT': True, 'NO_WAIT': True}
        mock_screen = MagicMock()
        mock_screen.get_width.return_value = 100
        mock_screen.get_height.return_value = 100
        mock_callback = MagicMock()
        with patch('src.visual_effects.display') as mock_display:
            fade(fade_out=False, screen=mock_screen, config=config, draw_callback=mock_callback)
        # Callback should have been called at least once
        self.assertGreater(mock_callback.call_count, 0)

    def test_fade_in_without_callback_blits_background(self):
        from src.visual_effects import fade
        config = {'NO_BLIT': True, 'NO_WAIT': True}
        mock_screen = MagicMock()
        mock_screen.get_width.return_value = 100
        mock_screen.get_height.return_value = 100
        mock_background = MagicMock()
        mock_screen.copy.return_value = mock_background
        with patch('src.visual_effects.display') as mock_display:
            fade(fade_out=False, screen=mock_screen, config=config)
        # Background should be blitted since NO_BLIT is True but we're checking screen.blit
        # The blit call with background happens regardless of NO_BLIT
        mock_screen.blit.assert_called()


class TestFlashTransparentColor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((100, 100))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_flash_returns_quickly_with_mock_calculation(self):
        mock_screen = MagicMock()
        mock_screen.get_width.return_value = 100
        mock_screen.get_height.return_value = 100
        mock_calc = MagicMock()
        # Make the while loop exit immediately (frames >= 3 from the start)
        mock_calc.convert_to_frames_since_start_time.return_value = 10

        with patch('src.visual_effects.display') as mock_display:
            flash_transparent_color((255, 0, 0), mock_screen, mock_calc, no_blit=True)

        # draw_transparent_color should have been called once
        # (since no_blit=True, screen.blit won't actually be called)

    def test_flash_calls_display_flip(self):
        mock_screen = MagicMock()
        mock_screen.get_width.return_value = 100
        mock_screen.get_height.return_value = 100
        mock_calc = MagicMock()
        mock_calc.convert_to_frames_since_start_time.side_effect = [0, 1, 2, 10]

        with patch('src.visual_effects.display') as mock_display:
            flash_transparent_color((255, 0, 0), mock_screen, mock_calc, no_blit=True)
            mock_display.flip.assert_called()

    def test_flash_with_custom_transparency(self):
        mock_screen = MagicMock()
        mock_screen.get_width.return_value = 100
        mock_screen.get_height.return_value = 100
        mock_calc = MagicMock()
        mock_calc.convert_to_frames_since_start_time.return_value = 10

        with patch('src.visual_effects.display'):
            # Should not raise with custom transparency value
            flash_transparent_color((0, 255, 0), mock_screen, mock_calc, transparency=64, no_blit=True)


if __name__ == '__main__':
    unittest.main()
