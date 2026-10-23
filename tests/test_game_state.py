import unittest

from src.game_state import GameState, LIGHT_REDRAW_FRAMES


class TestGameStateInitialization(unittest.TestCase):

    def setUp(self):
        self.config = {'MUSIC_ENABLED': True}
        self.game_state = GameState(self.config)

    def test_enable_movement_defaults_true(self):
        self.assertTrue(self.game_state.enable_movement)

    def test_enable_animate_defaults_true(self):
        self.assertTrue(self.game_state.enable_animate)

    def test_enable_roaming_defaults_true(self):
        self.assertTrue(self.game_state.enable_roaming)

    def test_is_initial_dialog_defaults_true(self):
        self.assertTrue(self.game_state.is_initial_dialog)

    def test_is_post_death_dialog_defaults_false(self):
        self.assertFalse(self.game_state.is_post_death_dialog)

    def test_automatic_initial_dialog_run_defaults_false(self):
        self.assertFalse(self.game_state.automatic_initial_dialog_run)

    def test_tiles_moved_total_defaults_zero(self):
        self.assertEqual(self.game_state.tiles_moved_total, 0)

    def test_light_defaults_to_the_minimum(self):
        self.assertEqual(self.game_state.light_diameter, 1)
        self.assertEqual(self.game_state.lit_diameter, 1)
        self.assertEqual(self.game_state.radiant_timer, 0)
        self.assertEqual(self.game_state.pending_light_redraws, [])

    def test_config_stored(self):
        self.assertEqual(self.game_state.config, self.config)


class TestGameStatePauseUnpause(unittest.TestCase):

    def setUp(self):
        self.game_state = GameState({'MUSIC_ENABLED': True})

    def test_pause_all_movement_disables_movement(self):
        self.game_state.pause_all_movement()
        self.assertFalse(self.game_state.enable_movement)

    def test_pause_all_movement_disables_animate(self):
        self.game_state.pause_all_movement()
        self.assertFalse(self.game_state.enable_animate)

    def test_pause_all_movement_disables_roaming(self):
        self.game_state.pause_all_movement()
        self.assertFalse(self.game_state.enable_roaming)

    def test_unpause_all_movement_enables_movement(self):
        self.game_state.pause_all_movement()
        self.game_state.unpause_all_movement()
        self.assertTrue(self.game_state.enable_movement)

    def test_unpause_all_movement_enables_animate(self):
        self.game_state.pause_all_movement()
        self.game_state.unpause_all_movement()
        self.assertTrue(self.game_state.enable_animate)

    def test_unpause_all_movement_enables_roaming(self):
        self.game_state.pause_all_movement()
        self.game_state.unpause_all_movement()
        self.assertTrue(self.game_state.enable_roaming)

    def test_unpause_without_pause_keeps_all_enabled(self):
        self.game_state.unpause_all_movement()
        self.assertTrue(self.game_state.enable_movement)
        self.assertTrue(self.game_state.enable_animate)
        self.assertTrue(self.game_state.enable_roaming)

    def test_multiple_pause_calls(self):
        self.game_state.pause_all_movement()
        self.game_state.pause_all_movement()
        self.assertFalse(self.game_state.enable_movement)

    def test_pause_then_unpause_cycle(self):
        for _ in range(3):
            self.game_state.pause_all_movement()
            self.assertFalse(self.game_state.enable_movement)
            self.game_state.unpause_all_movement()
            self.assertTrue(self.game_state.enable_movement)

    def test_manual_flag_modification(self):
        self.game_state.enable_movement = False
        self.assertFalse(self.game_state.enable_movement)
        self.assertTrue(self.game_state.enable_animate)  # untouched


class TestDungeonLight(unittest.TestCase):
    """NES LightDiameter/RadiantTimer: DoSpell (SPL_RADIANT), UseTorch and GameEngineLoop in Bank03, InitMapData in
    Bank00."""

    def setUp(self):
        self.game_state = GameState({'MUSIC_ENABLED': True})

    def walk(self, steps):
        for _ in range(steps):
            self.game_state.tick_radiant_timer()

    def redraw(self, frames, hero_is_stepping=False):
        """Run the screen for some frames and return the frames (0-based) on which SFX_RADIANT played."""
        return [frame for frame in range(frames) if self.game_state.update_lit_diameter(hero_is_stepping)]

    def test_radiant_grows_the_light_to_7_blocks(self):
        self.game_state.cast_radiant()
        self.assertEqual(self.game_state.light_diameter, 7)
        self.assertEqual(self.game_state.radiant_timer, 0x50)
        self.assertEqual(self.game_state.pending_light_redraws, [3, 5, 7])

    def test_radiant_light_expands_2_blocks_at_a_time(self):
        self.game_state.cast_radiant()
        lit = []
        for _ in range(LIGHT_REDRAW_FRAMES * 3 + 2):
            self.game_state.update_lit_diameter(hero_is_stepping=False)
            lit.append(self.game_state.lit_diameter)
        # Each PostMoveUpdate shows its light on its last frame
        self.assertEqual(lit, [1] * (LIGHT_REDRAW_FRAMES - 1) + [3] * LIGHT_REDRAW_FRAMES + [5] * LIGHT_REDRAW_FRAMES
                         + [7] * 3)
        self.assertEqual(self.game_state.pending_light_redraws, [])

    def test_radiant_plays_its_sound_for_each_expansion(self):
        self.game_state.cast_radiant()
        self.assertEqual(self.redraw(LIGHT_REDRAW_FRAMES * 4), [0, LIGHT_REDRAW_FRAMES, LIGHT_REDRAW_FRAMES * 2])

    def test_radiant_lasts_80_steps_then_shrinks_every_60_steps(self):
        self.game_state.cast_radiant()
        diameters = []
        for _ in range(250):
            self.game_state.tick_radiant_timer()
            diameters.append(self.game_state.light_diameter)
        self.assertEqual(diameters, [7] * 79 + [5] * 60 + [3] * 60 + [1] * 51)

    def test_the_radiant_timer_stops_at_the_minimum_light(self):
        self.game_state.cast_radiant()
        self.walk(80 + 60 + 60)  # down to 1, with the timer reloaded once more
        self.assertEqual(self.game_state.light_diameter, 1)
        self.assertEqual(self.game_state.radiant_timer, 0x3C)
        self.walk(60)
        self.assertEqual(self.game_state.radiant_timer, 0)
        self.walk(100)
        self.assertEqual(self.game_state.light_diameter, 1)
        self.assertEqual(self.game_state.radiant_timer, 0)

    def test_shrinking_light_is_drawn_on_the_next_step(self):
        self.game_state.cast_radiant()
        self.redraw(LIGHT_REDRAW_FRAMES * 3)
        self.walk(80)
        self.assertEqual(self.game_state.light_diameter, 5)
        # The NES only redraws the dungeon when the hero moves, so the 7 block light stays up until then
        self.assertEqual(self.redraw(10), [])
        self.assertEqual(self.game_state.lit_diameter, 7)
        self.assertEqual(self.redraw(1, hero_is_stepping=True), [])
        self.assertEqual(self.game_state.lit_diameter, 5)

    def test_radiant_cast_again_restarts_the_timer(self):
        self.game_state.cast_radiant()
        self.redraw(LIGHT_REDRAW_FRAMES * 3)
        self.walk(50)
        self.game_state.cast_radiant()
        self.assertEqual(self.game_state.radiant_timer, 0x50)
        # LightIncreaseLoop exits at once when the light is already at 7: no redraw and no sound
        self.assertEqual(self.game_state.pending_light_redraws, [])
        self.assertEqual(self.redraw(LIGHT_REDRAW_FRAMES), [])

    def test_radiant_cast_while_shrinking_grows_back_to_7(self):
        self.game_state.cast_radiant()
        self.redraw(LIGHT_REDRAW_FRAMES * 3)
        self.walk(80 + 60)
        self.assertEqual(self.game_state.light_diameter, 3)
        self.game_state.cast_radiant()
        self.assertEqual(self.game_state.pending_light_redraws, [5, 7])
        self.assertEqual(self.game_state.radiant_timer, 0x50)

    def test_torch_lights_3_blocks_for_good(self):
        self.game_state.use_torch()
        self.assertEqual(self.game_state.light_diameter, 3)
        self.assertEqual(self.game_state.radiant_timer, 0)
        self.assertEqual(self.redraw(LIGHT_REDRAW_FRAMES), [0])
        self.assertEqual(self.game_state.lit_diameter, 3)
        self.walk(1000)
        self.assertEqual(self.game_state.light_diameter, 3)

    def test_radiant_after_a_torch_grows_from_3_and_shrinks_to_1(self):
        self.game_state.use_torch()
        self.redraw(LIGHT_REDRAW_FRAMES)
        self.game_state.cast_radiant()
        self.assertEqual(self.game_state.pending_light_redraws, [5, 7])
        self.assertEqual(self.redraw(LIGHT_REDRAW_FRAMES * 2), [0, LIGHT_REDRAW_FRAMES])
        self.walk(80 + 60 + 60)
        # The torch's light doesn't come back once RADIANT wears off
        self.assertEqual(self.game_state.light_diameter, 1)

    def test_torch_during_radiant_cuts_the_light_to_3(self):
        self.game_state.cast_radiant()
        self.redraw(LIGHT_REDRAW_FRAMES * 3)
        self.walk(10)
        self.game_state.use_torch()
        self.assertEqual(self.game_state.radiant_timer, 0)
        self.assertEqual(self.game_state.light_diameter, 3)
        self.redraw(LIGHT_REDRAW_FRAMES)
        self.assertEqual(self.game_state.lit_diameter, 3)
        self.walk(500)
        self.assertEqual(self.game_state.light_diameter, 3)

    def test_torch_during_the_radiant_expansion_replaces_it(self):
        self.game_state.cast_radiant()
        self.redraw(LIGHT_REDRAW_FRAMES + 2)
        self.game_state.use_torch()
        self.assertEqual(self.game_state.pending_light_redraws, [3])
        self.redraw(LIGHT_REDRAW_FRAMES * 3)
        self.assertEqual(self.game_state.lit_diameter, 3)

    def test_a_step_during_the_expansion_does_not_skip_it(self):
        self.game_state.cast_radiant()
        self.redraw(1, hero_is_stepping=True)
        self.assertEqual(self.game_state.lit_diameter, 1)

    def test_leaving_the_dungeon_puts_out_the_light(self):
        self.game_state.cast_radiant()
        self.redraw(LIGHT_REDRAW_FRAMES)
        self.game_state.reset_light()
        self.assertEqual(self.game_state.light_diameter, 1)
        self.assertEqual(self.game_state.lit_diameter, 1)
        self.assertEqual(self.game_state.radiant_timer, 0)
        self.assertEqual(self.game_state.pending_light_redraws, [])


if __name__ == '__main__':
    unittest.main()
