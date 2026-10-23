from unittest import TestCase
from unittest.mock import patch

import pygame

from src.config.test_config import test_config
from tests.helpers import new_game


class TestMovementUpdates(TestCase):
    """NES CheckForTriggers/MovementUpdates (Bank03): the checks made after every completed step."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()
        cls.screen = pygame.display.set_mode((800, 600))

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        self.game = new_game()
        self.player = self.game.player
        self.player.max_hp = 100
        self.player.current_hp = 50

    def steps(self, count):
        for _ in range(count):
            self.game.count_step()

    # MovmtIncHP

    def test_erdricks_armor_heals_1_hp_every_step(self):
        self.player.armor = "Erdrick's Armor"
        self.steps(3)
        self.assertEqual(self.player.current_hp, 53)

    def test_magic_armor_heals_1_hp_every_4th_step(self):
        self.player.armor = "Magic Armor"
        self.steps(3)
        self.assertEqual(self.player.current_hp, 50)
        self.steps(1)
        self.assertEqual(self.player.current_hp, 51)
        self.steps(4)
        self.assertEqual(self.player.current_hp, 52)

    def test_magic_armor_step_count_only_counts_steps_in_magic_armor(self):
        # NES: MjArmrHP is only incremented while Magic Armor is worn
        self.player.armor = "Magic Armor"
        self.steps(3)
        self.player.armor = "Full Plate"
        self.steps(5)
        self.player.armor = "Magic Armor"
        self.steps(1)
        self.assertEqual(self.player.current_hp, 51)

    def test_other_armor_does_not_heal(self):
        self.player.armor = "Full Plate"
        self.steps(8)
        self.assertEqual(self.player.current_hp, 50)

    def test_armor_heal_is_capped_at_max_hp(self):
        self.player.armor = "Erdrick's Armor"
        self.player.current_hp = 99
        self.steps(3)
        self.assertEqual(self.player.current_hp, 100)

    # Dragonlord dead: CheckForTriggers skips MovementUpdates

    def test_armor_does_not_heal_after_the_dragonlord_is_dead(self):
        self.game.story_flags.dragonlord_defeated = True
        for armor in ("Erdrick's Armor", "Magic Armor"):
            self.player.armor = armor
            self.steps(8)
            self.assertEqual(self.player.current_hp, 50, armor)

    def test_movement_updates_are_skipped_after_the_dragonlord_is_dead(self):
        self.game.story_flags.dragonlord_defeated = True
        with patch.object(self.game, 'movement_updates') as movement_updates:
            self.game.count_step()
        movement_updates.assert_not_called()

    def test_movement_updates_run_while_the_dragonlord_is_alive(self):
        with patch.object(self.game, 'movement_updates') as movement_updates:
            self.game.count_step()
        movement_updates.assert_called_once()

    def test_repel_timer_still_ticks_after_the_dragonlord_is_dead(self):
        # NES CheckRepelTimer is in GameEngineLoop, outside CheckForTriggers
        self.game.story_flags.dragonlord_defeated = True
        self.game.repel_timer = 9
        self.game.count_step()
        self.assertEqual(self.game.repel_timer, 7)

    # CheckBlockDmg/ChkOtherBlocks: its own F_DGNLRD_DEAD check ends swamp and barrier damage

    def environment_damage(self, tile):
        self.player.armor = "Full Plate"
        self.player.is_moving = False
        self.player.received_environment_damage = False
        self.player.current_tile = tile
        with patch.object(self.game, 'drawer'), patch('src.game.display'), \
                patch('src.game.flash_transparent_color'), patch.object(self.game.sound, 'play_sound'):
            self.game.handle_environment_damage()
        return 50 - self.player.current_hp

    def test_swamp_and_barrier_hurt_while_the_dragonlord_is_alive(self):
        self.assertEqual(self.environment_damage('MARSH'), 2)
        self.player.current_hp = 50
        self.assertEqual(self.environment_damage('BARRIER'), 15)

    def test_swamp_and_barrier_damage_stop_at_zero_hp(self):
        self.player.current_hp = 1
        self.environment_damage('BARRIER')
        self.assertEqual(self.player.current_hp, 0)

    def test_swamp_and_barrier_do_not_hurt_after_the_dragonlord_is_dead(self):
        self.game.story_flags.dragonlord_defeated = True
        self.assertEqual(self.environment_damage('MARSH'), 0)
        self.assertEqual(self.environment_damage('BARRIER'), 0)
