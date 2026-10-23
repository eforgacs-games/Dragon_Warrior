"""Nothing reads the joypad while RADIANT's light grows (issue #307).

NES DoSpell (Bank03, SPL_RADIANT): LightIncreaseLoop grows the light 2 blocks at a time, redrawing the screen with
PostMoveUpdate each time (LIGHT_REDRAW_FRAMES frames), and only returns once the light is 7 blocks wide: about 24
frames in which the joypad isn't read and the NPCs stay stopped. UseTorch's one redraw works the same way.

The light is advanced by Drawer.handle_darkness, a frame per draw; these tests draw (advance the light) once per frame.
"""
from unittest.mock import patch

from pygame import K_DOWN, K_RIGHT, K_UP, K_LEFT, K_i, K_k

from src.game_state import LIGHT_REDRAW_FRAMES
from src.maps import ErdricksCaveB1
from tests.test_freeze_movement import FreezeTestCase, keydown

RADIANT_GROWTH_FRAMES = 3 * LIGHT_REDRAW_FRAMES  # 1 -> 3 -> 5 -> 7 blocks


class TestLightGrowthFreeze(FreezeTestCase):

    def setUp(self):
        super().setUp()
        self.game.change_map(ErdricksCaveB1(self.game.config), destination_coordinates=(3, 3))
        self.assertTrue(self.game.current_map.is_dark)
        self.player = self.game.player
        self.addCleanup(patch.stopall)
        patch.dict(self.game.game_state.config, NO_BATTLES=True, ENABLE_DARKNESS=True).start()
        patch.object(self.game.movement.sound, 'play_sound').start()
        self.game.movement.frame_counter = 0
        self.direction = self.open_direction()

    def open_direction(self):
        """A direction the hero can walk in from the start."""
        for direction in (K_DOWN, K_RIGHT, K_UP, K_LEFT):
            start = self.player.rect.topleft
            self.game.movement.frame_counter = 0
            self.frame(held=(direction,))
            moved = self.player.rect.topleft != start
            self.frames(32)  # finish the step, or the bump
            if moved:
                self.game.change_map(ErdricksCaveB1(self.game.config), destination_coordinates=(3, 3))
                return direction
        self.fail('The hero is walled in')

    def frame(self, *events, held=()):
        super().frame(*events, held=held)
        self.game.game_state.update_lit_diameter(hero_is_stepping=False)  # what drawing the frame does

    def test_radiant_grows_the_light_for_24_frames(self):
        self.assertEqual(24, RADIANT_GROWTH_FRAMES)
        self.game.game_state.cast_radiant()
        self.assertTrue(self.game.movement.light_growing)
        self.frames(RADIANT_GROWTH_FRAMES - 1)
        self.assertTrue(self.game.movement.light_growing)
        self.frame()
        self.assertFalse(self.game.movement.light_growing)
        self.assertEqual(7, self.game.game_state.lit_diameter)

    def test_the_hero_does_not_move_while_the_light_grows(self):
        self.game.movement.frame_counter = 5  # would step on the 11th frame if the joypad were read
        self.game.game_state.cast_radiant()
        start = self.player.rect.topleft
        self.frames(RADIANT_GROWTH_FRAMES, held=(self.direction,))
        self.assertEqual(start, self.player.rect.topleft)
        self.assertFalse(self.player.is_moving)
        # FrameCounter starts again from 0 (JoypadCheckLoop), so the held direction steps on the next frame
        self.frame(held=(self.direction,))
        self.assertNotEqual(start, self.player.rect.topleft)

    def test_a_and_start_are_ignored_while_the_light_grows(self):
        self.game.game_state.cast_radiant()
        self.frame(keydown(K_k))
        self.frame(keydown(K_i))
        self.frames(RADIANT_GROWTH_FRAMES)
        self.assertFalse(self.game.cmd_menu_requested)
        self.assertFalse(self.game.pause_requested)
        self.assertFalse(self.game.paused)
        self.assertFalse(self.game.cmd_menu.menu.is_enabled())

    def test_a_torch_freezes_for_its_one_redraw(self):
        self.game.game_state.use_torch()
        start = self.player.rect.topleft
        self.frames(LIGHT_REDRAW_FRAMES, held=(self.direction,))
        self.assertEqual(start, self.player.rect.topleft)
        self.frame(held=(self.direction,))
        self.assertNotEqual(start, self.player.rect.topleft)

    def test_no_freeze_without_darkness(self):
        # With ENABLE_DARKNESS off nothing draws the light, so it must not hold the hero up
        self.game.game_state.config['ENABLE_DARKNESS'] = False
        self.game.game_state.cast_radiant()
        self.assertFalse(self.game.movement.light_growing)
