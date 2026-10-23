import unittest
from unittest.mock import patch, MagicMock

import pygame

from src.visual_effects import (
    NES_PALETTE, NES_RED, SWAMP_FLASH_FRAMES, draw_transparent_color, enemy_fade_in, enemy_hit_flash, enemy_spell_flash,
    fade_surface, flash_transparent_color, force_field_flash, nes_color_index, nes_faded_color, player_hit_shake,
    rainbow_bridge_flash, rainbow_flash_colors, silhouette_surface,
)


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
        with patch('src.visual_effects.display'):
            # Should not raise
            fade(fade_out=True, screen=mock_screen, config=config)

    def test_fade_in_no_blit_no_wait(self):
        from src.visual_effects import fade
        config = {'NO_BLIT': True, 'NO_WAIT': True}
        mock_screen = MagicMock()
        mock_screen.get_width.return_value = 100
        mock_screen.get_height.return_value = 100
        mock_screen.copy.return_value = MagicMock()
        with patch('src.visual_effects.display'):
            fade(fade_out=False, screen=mock_screen, config=config)

    def test_fade_in_with_draw_callback(self):
        from src.visual_effects import fade
        config = {'NO_BLIT': True, 'NO_WAIT': True}
        mock_screen = MagicMock()
        mock_screen.get_width.return_value = 100
        mock_screen.get_height.return_value = 100
        mock_callback = MagicMock()
        with patch('src.visual_effects.display'):
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
        with patch('src.visual_effects.display'):
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

    def test_flash_shows_the_tint_for_three_frames(self):
        mock_screen = MagicMock()
        mock_screen.get_width.return_value = 100
        mock_screen.get_height.return_value = 100
        with patch('src.visual_effects.display') as mock_display, patch('src.visual_effects.wait') as mock_wait:
            flash_transparent_color((255, 0, 0), mock_screen, {'NO_BLIT': True, 'NO_WAIT': False})
        mock_display.flip.assert_called_once()
        mock_wait.assert_called_once_with(round(SWAMP_FLASH_FRAMES * 1000 / 60), {'NO_BLIT': True, 'NO_WAIT': False})
        self.assertEqual(SWAMP_FLASH_FRAMES, 3)

    def test_flash_with_custom_transparency(self):
        mock_screen = MagicMock()
        mock_screen.get_width.return_value = 100
        mock_screen.get_height.return_value = 100
        with patch('src.visual_effects.display'), patch('src.visual_effects.wait'):
            # Should not raise with custom transparency value
            flash_transparent_color((0, 255, 0), mock_screen, {'NO_BLIT': True}, transparency=64)

    def test_flash_follows_no_wait(self):
        mock_screen = MagicMock()
        mock_screen.get_width.return_value = 100
        mock_screen.get_height.return_value = 100
        with patch('src.visual_effects.display'), patch('src.waiting.time.wait') as sleep:
            flash_transparent_color((255, 0, 0), mock_screen, {'NO_BLIT': True, 'NO_WAIT': True})
        sleep.assert_not_called()


class NesPaletteTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((100, 100))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    @staticmethod
    def sprite(*colors):
        """A 1-pixel-high sprite: one pixel per color, then a transparent pixel."""
        surface = pygame.Surface((len(colors) + 1, 1), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))
        for x, color in enumerate(colors):
            surface.set_at((x, 0), color)
        return surface

    @staticmethod
    def record_flips(screen, *points):
        """Patch display.flip to record the screen color at each point whenever a frame is shown."""
        shown = []

        def flip():
            shown.append(tuple(tuple(screen.get_at(point))[:3] for point in points))

        return patch('src.visual_effects.display', flip=flip), shown


class TestNesColors(NesPaletteTestCase):

    def test_white_is_color_30(self):
        self.assertEqual(nes_color_index((252, 252, 252)), 0x30)

    def test_fade_subtracts_one_brightness_row_per_10(self):
        # AddPalByte: $30 - $30 = $00 (dark grey), $27 - $10 = $17
        self.assertEqual(nes_faded_color((252, 252, 252), 0x30), NES_PALETTE[0x00])
        self.assertEqual(nes_faded_color(NES_PALETTE[0x27], 0x10), NES_PALETTE[0x17])

    def test_fade_below_zero_is_black(self):
        self.assertEqual(nes_faded_color(NES_PALETTE[0x15], 0x20), (0, 0, 0))
        self.assertEqual(nes_faded_color((0, 0, 0), 0x10), (0, 0, 0))

    def test_unknown_color_uses_nearest(self):
        self.assertEqual(nes_color_index((250, 250, 250)), 0x30)

    def test_fade_surface_keeps_transparency(self):
        faded = fade_surface(self.sprite(NES_PALETTE[0x30]), 0x30)
        self.assertEqual(tuple(faded.get_at((0, 0)))[:3], NES_PALETTE[0x00])
        self.assertEqual(faded.get_at((1, 0)).a, 0)

    def test_silhouette_is_red_and_keeps_shape(self):
        red = silhouette_surface(self.sprite((0, 0, 0), NES_PALETTE[0x30]), NES_RED)
        self.assertEqual(tuple(red.get_at((0, 0)))[:3], NES_RED)
        self.assertEqual(tuple(red.get_at((1, 0)))[:3], NES_RED)
        self.assertEqual(red.get_at((2, 0)).a, 0)

    def test_silhouette_keep_black(self):
        red = silhouette_surface(self.sprite((0, 0, 0), NES_PALETTE[0x30]), NES_RED, keep_black=True)
        self.assertEqual(tuple(red.get_at((0, 0)))[:3], (0, 0, 0))
        self.assertEqual(tuple(red.get_at((1, 0)))[:3], NES_RED)


class TestEnemyFadeIn(NesPaletteTestCase):
    config = {'NO_WAIT': True, 'NO_BLIT': False}

    def test_fades_in_twice_from_a_black_shadow(self):
        screen = pygame.Surface((10, 10))
        recorder, shown = self.record_flips(screen, (2, 2))
        with recorder:
            enemy_fade_in(screen, self.sprite(NES_PALETTE[0x30]), (2, 2), self.config)
        steps = [NES_PALETTE[0x00], NES_PALETTE[0x10], NES_PALETTE[0x20], NES_PALETTE[0x30]]
        self.assertEqual([color for (color,) in shown], [(0, 0, 0)] + steps * 2 + [NES_PALETTE[0x30]])

    def test_final_form_fades_in_four_times(self):
        screen = pygame.Surface((10, 10))
        recorder, shown = self.record_flips(screen, (0, 0))
        with recorder:
            enemy_fade_in(screen, self.sprite(NES_PALETTE[0x30]), (0, 0), self.config, repeats=4)
        self.assertEqual(len(shown), 1 + 4 * 4 + 1)

    @patch('src.visual_effects.wait')
    def test_each_step_lasts_four_frames(self, mock_wait):
        with patch('src.visual_effects.display'):
            enemy_fade_in(pygame.Surface((10, 10)), self.sprite(NES_PALETTE[0x30]), (0, 0),
                          {'NO_WAIT': False, 'NO_BLIT': False})
        self.assertEqual([c.args[0] for c in mock_wait.call_args_list], [67] * 9)  # 4 frames at 60 FPS

    def test_no_blit_draws_nothing(self):
        screen = MagicMock()
        with patch('src.visual_effects.display'):
            enemy_fade_in(screen, self.sprite(NES_PALETTE[0x30]), (0, 0), {'NO_WAIT': True, 'NO_BLIT': True})
        screen.blit.assert_not_called()


class TestEnemyHitFlash(NesPaletteTestCase):

    def test_flashes_red_five_times_then_restores(self):
        screen = pygame.Surface((10, 10))
        recorder, shown = self.record_flips(screen, (0, 0))
        with recorder:
            enemy_hit_flash(screen, self.sprite(NES_PALETTE[0x30]), (0, 0), {'NO_WAIT': True, 'NO_BLIT': False})
        self.assertEqual([color for (color,) in shown], [NES_PALETTE[0x30], NES_RED] * 5 + [NES_PALETTE[0x30]])

    @patch('src.visual_effects.wait')
    def test_three_frames_normal_two_frames_red(self, mock_wait):
        with patch('src.visual_effects.display'):
            enemy_hit_flash(pygame.Surface((10, 10)), self.sprite(NES_PALETTE[0x30]), (0, 0),
                            {'NO_WAIT': False, 'NO_BLIT': False})
        self.assertEqual([c.args[0] for c in mock_wait.call_args_list], [50, 33] * 5)


class TestEnemySpellFlash(NesPaletteTestCase):
    """NES EnCastSpell (LEC03-LEC0D): PaletteFlash with SplFlshBGPal, every color $10."""

    def test_flashes_grey_five_times_then_restores(self):
        screen = pygame.Surface((10, 10))
        recorder, shown = self.record_flips(screen, (0, 0))
        with recorder:
            enemy_spell_flash(screen, self.sprite(NES_PALETTE[0x16]), (0, 0), {'NO_WAIT': True, 'NO_BLIT': False})
        self.assertEqual([color for (color,) in shown],
                         [NES_PALETTE[0x16], NES_PALETTE[0x10]] * 5 + [NES_PALETTE[0x16]])

    @patch('src.visual_effects.wait')
    def test_same_timing_as_the_hit_flash(self, mock_wait):
        with patch('src.visual_effects.display'):
            enemy_spell_flash(pygame.Surface((10, 10)), self.sprite(NES_PALETTE[0x30]), (0, 0),
                              {'NO_WAIT': False, 'NO_BLIT': False})
        self.assertEqual([c.args[0] for c in mock_wait.call_args_list], [50, 33] * 5)


class TestForceFieldFlash(NesPaletteTestCase):
    """NES force field damage (Bank03, LCE30): three red flashes, 2 frames as before then 2 frames red each."""

    def test_flashes_red_three_times_then_restores(self):
        screen = pygame.Surface((10, 10))
        screen.fill(NES_PALETTE[0x30])
        recorder, shown = self.record_flips(screen, (0, 0))
        with recorder:
            force_field_flash(NES_RED, screen, {'NO_WAIT': True, 'NO_BLIT': False}, transparency=255)
        self.assertEqual([color for (color,) in shown], [NES_PALETTE[0x30], NES_RED] * 3 + [NES_PALETTE[0x30]])

    @patch('src.visual_effects.wait')
    def test_two_frames_normal_two_frames_red(self, mock_wait):
        with patch('src.visual_effects.display'):
            force_field_flash(NES_RED, pygame.Surface((10, 10)), {'NO_WAIT': False, 'NO_BLIT': False})
        self.assertEqual([c.args[0] for c in mock_wait.call_args_list], [33, 33] * 3)  # 12 frames in all


class TestRainbowBridgeFlash(NesPaletteTestCase):
    """NES ChkDrop (LDEC5-LDEFB): $3F03, the overworld's water blue ($11), goes through $21-$2C four times and then
    back to $11, a write every 5 frames."""

    def test_the_colors(self):
        cycle = list(range(0x21, 0x2D))
        self.assertEqual(12, len(cycle))
        self.assertEqual(cycle * 4 + [0x11], rainbow_flash_colors())

    def test_only_the_water_blue_changes_and_the_screen_ends_as_it_was(self):
        screen = pygame.Surface((10, 10))
        screen.fill(NES_PALETTE[0x29])  # grass green
        screen.set_at((5, 5), NES_PALETTE[0x11])  # water
        screen.set_at((6, 6), NES_PALETTE[0x12])  # the hero's blue (RegSPPal), not $11
        recorder, shown = self.record_flips(screen, (5, 5), (0, 0), (6, 6))
        with recorder:
            rainbow_bridge_flash(screen, {'NO_WAIT': True, 'NO_BLIT': False})
        self.assertEqual([NES_PALETTE[color] for color in rainbow_flash_colors()], [water for water, _, _ in shown])
        self.assertEqual({(NES_PALETTE[0x29], NES_PALETTE[0x12])}, {(grass, hero) for _, grass, hero in shown})
        self.assertEqual(NES_PALETTE[0x11], tuple(screen.get_at((5, 5)))[:3])

    def test_five_frames_before_each_color(self):
        with patch('src.visual_effects.display'), patch('src.visual_effects.wait_frames') as wait_frames:
            rainbow_bridge_flash(pygame.Surface((10, 10)), {'NO_WAIT': False, 'NO_BLIT': False})
        self.assertEqual([5] * 49, [c.args[0] for c in wait_frames.call_args_list])  # 245 frames in all


class TestPlayerHitShake(NesPaletteTestCase):
    config = {'NO_WAIT': True, 'NO_BLIT': False, 'SCALE': 2}

    @staticmethod
    def make_screen():
        """A screen where the red channel encodes the column and the blue channel the row."""
        screen = pygame.Surface((20, 20))
        for x in range(20):
            for y in range(20):
                screen.set_at((x, y), (x * 10 + 5, 1, y * 10 + 5))
        return screen

    def test_shakes_x_then_y_by_two_nes_pixels_and_resets(self):
        screen = self.make_screen()
        recorder, shown = self.record_flips(screen, (5, 5))
        with recorder:
            player_hit_shake(screen, self.config)
        normal, x_moved, y_moved = (55, 1, 55), (95, 1, 55), (55, 1, 95)  # 2 NES pixels * SCALE 2 = 4 pixels
        expected = []
        for moved in (x_moved, y_moved) * 4:
            expected += [(normal,), (moved,)]
        self.assertEqual(shown, expected + [(normal,)])
        self.assertEqual(tuple(screen.get_at((5, 5)))[:3], normal)

    def test_deathblow_flashes_background_red_but_not_the_enemy(self):
        screen = self.make_screen()
        screen.set_at((15, 15), (0, 0, 0))
        enemy = self.sprite(NES_PALETTE[0x30])
        background = pygame.Surface((20, 20))
        background.fill((0, 0, 200))
        recorder, shown = self.record_flips(screen, (5, 5), (2, 2), (11, 15))
        with recorder:
            player_hit_shake(screen, self.config, deathblow=True, enemy=(enemy, (2, 2)),
                             background=(background, (0, 0)))
        moved_frames = shown[1:16:2]
        self.assertTrue(all(frame[0] == NES_RED for frame in moved_frames))
        self.assertTrue(all(frame[1] == NES_PALETTE[0x30] for frame in moved_frames))  # the enemy doesn't move
        self.assertEqual(moved_frames[0][2], (0, 0, 0))  # black stays black (x 15 shown at x 11)
        self.assertEqual(shown[-1][0], (55, 1, 55))

    def test_hit_without_deathblow_has_no_red(self):
        screen = self.make_screen()
        recorder, shown = self.record_flips(screen, (5, 5))
        with recorder:
            player_hit_shake(screen, self.config)
        self.assertNotIn((NES_RED,), shown)

    @patch('src.visual_effects.wait')
    def test_final_form_does_not_shake_but_takes_the_same_time(self, mock_wait):
        screen = MagicMock()
        with patch('src.visual_effects.display') as mock_display:
            player_hit_shake(screen, {'NO_WAIT': False, 'NO_BLIT': False}, shake=False)
            player_hit_shake(screen, {'NO_WAIT': False, 'NO_BLIT': False}, deathblow=True, shake=False)
        screen.blit.assert_not_called()
        mock_display.flip.assert_not_called()
        self.assertEqual([c.args[0] for c in mock_wait.call_args_list], [533, 400])  # 32 and 24 frames

    @patch('src.visual_effects.wait')
    def test_shake_timing(self, mock_wait):
        with patch('src.visual_effects.display'):
            player_hit_shake(self.make_screen(), {'NO_WAIT': False, 'NO_BLIT': False, 'SCALE': 2})
        self.assertEqual([c.args[0] for c in mock_wait.call_args_list], [33] * 16)


if __name__ == '__main__':
    unittest.main()
