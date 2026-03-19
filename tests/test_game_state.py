import unittest

from src.game_state import GameState


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

    def test_radiant_start_defaults_none(self):
        self.assertIsNone(self.game_state.radiant_start)

    def test_tiles_moved_total_defaults_zero(self):
        self.assertEqual(self.game_state.tiles_moved_total, 0)

    def test_radiant_active_defaults_false(self):
        self.assertFalse(self.game_state.radiant_active)

    def test_game_loaded_from_save_defaults_false(self):
        self.assertFalse(self.game_state.game_loaded_from_save)

    def test_music_enabled_from_config_true(self):
        self.assertTrue(self.game_state.music_enabled)

    def test_music_enabled_from_config_false(self):
        gs = GameState({'MUSIC_ENABLED': False})
        self.assertFalse(gs.music_enabled)

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


if __name__ == '__main__':
    unittest.main()
