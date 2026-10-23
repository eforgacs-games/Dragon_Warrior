"""Per-step damage, healing and map changes against the NES (#233): Bank00 ChkSpecialLoc and Bank03
CheckForTriggers/MovementUpdates/CheckBlockDmg."""
from unittest import TestCase
from unittest.mock import patch

import pygame

from src.color import LOW_HP_RED, WHITE
from src.config.test_config import test_config
from src.maps import map_lookup
from src.maps_functions import get_center_point
from tests.helpers import new_game

# Maps whose edges lead out to the overworld (create_town_gates)
MAPS_WITH_GATES = ('TantegelCourtyard', 'CharlockB1', 'Brecconary', 'Garinham', 'Kol', 'Rimuldar', 'Hauksness',
                   'Cantlin')


class StepTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()
        pygame.display.set_mode((800, 600))

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        self.game = new_game()
        self.player = self.game.player
        self.player.max_hp = 100
        self.player.current_hp = 50
        self.player.armor = "Full Plate"

    def go_to(self, map_name, coordinates):
        self.game.change_map(map_lookup[map_name](self.game.config), destination_coordinates=coordinates)

    def end_step_on(self, coordinates):
        """The hero's sprite has just finished a step onto coordinates; its row and column are still the old ones."""
        row, column = coordinates
        self.player.rect.center = get_center_point(column, row, self.game.tile_size)
        self.player.is_moving = False


class TestBlockDamage(StepTestCase):
    """NES ChkOtherBlocks/NextBlockCheck (LCDC6) and the force field (LCE1F)."""

    def environment_damage(self, tile):
        self.player.is_moving = False
        self.player.received_environment_damage = False
        self.player.current_tile = tile
        hp = self.player.current_hp
        with patch.object(self.game, 'drawer'), patch('src.game.display'), patch('src.game.force_field_flash'), \
                patch('src.game.flash_transparent_color'), patch.object(self.game.sound, 'play_sound'):
            self.game.handle_environment_damage()
        return hp - self.player.current_hp

    def test_erdricks_armor_stops_swamp_and_force_field_damage(self):
        # NES: AND #AR_ARMOR / CMP #AR_ERDK_ARMR before the swamp (LCDCC) and the force field (LCE23) damage
        self.player.armor = "Erdrick's Armor"
        self.assertEqual(self.environment_damage('MARSH'), 0)
        self.assertEqual(self.environment_damage('BARRIER'), 0)

    def test_other_armor_does_not(self):
        for armor in ("Magic Armor", "Full Plate", None):
            with self.subTest(armor=armor):
                self.player.armor, self.player.current_hp = armor, 50
                self.assertEqual(self.environment_damage('MARSH'), 2)
                self.assertEqual(self.environment_damage('BARRIER'), 15)

    def test_the_dragons_scale_does_not_stop_block_damage(self):
        # NES: only the armor bits of EqippedItems are checked; the Dragon's Scale only adds 2 defense (LoadStats)
        self.player.wearing_dragon_scale = True
        self.assertEqual(self.environment_damage('MARSH'), 2)
        self.assertEqual(self.environment_damage('BARRIER'), 15)

    def test_a_force_field_that_leaves_hp_low_does_not_turn_the_windows_red(self):
        # NES LCE34-LCE44: LoadRegBGPal is called during the flashes, before the 15 HP are taken, and not after
        self.player.current_hp = 40
        self.game.load_window_palette()
        self.environment_damage('BARRIER')
        self.assertEqual(self.player.current_hp, 25)  # low: 25 <= 100 / 4 + 1
        self.assertEqual(self.game.color, WHITE)

    def test_a_force_field_keeps_low_hp_windows_red(self):
        self.player.current_hp = 20
        self.game.load_window_palette()
        self.environment_damage('BARRIER')
        self.assertEqual(self.game.color, LOW_HP_RED)

    def test_a_swamp_that_leaves_hp_low_turns_the_windows_red(self):
        # NES DoSwampDamage: STA HitPoints, then LoadRegBGPal (LCDED)
        self.player.current_hp = 28
        self.game.load_window_palette()
        self.environment_damage('MARSH')
        self.assertEqual(self.game.color, LOW_HP_RED)


class TestMapExits(StepTestCase):
    """NES ChkSpecialLoc (Bank00, LB219): a step off the map's edge goes to CheckMapExit, before CheckForTriggers."""

    def test_every_town_gate_is_off_the_nes_map(self):
        for map_name in MAPS_WITH_GATES:
            current_map = map_lookup[map_name](test_config)
            gates = [cell for cell, staircase in current_map.staircases.items() if staircase['map'] == 'Alefgard']
            with self.subTest(map_name):
                self.assertTrue(gates)
                for row, column in gates:
                    self.assertTrue(current_map.is_map_exit(row, column), (row, column))
                    self.assertTrue(current_map.is_step_warp(row, column), (row, column))
                self.assertFalse(current_map.is_map_exit(*current_map.initial_coordinates))

    def test_overworld_entrances_are_taken_on_the_step_and_stairs_are_not(self):
        # NES CheckBlockDmg: BLK_TOWN, BLK_CAVE and BLK_CASTLE go to CalcNextMap; stairs need STAIRS (CheckStairs).
        # The overworld shrine stairs (GRASS_STAIR_DOWN) are BLK_STAIR_DN (WrldBlkConvTbl index $0C)
        alefgard = map_lookup['Alefgard'](test_config)
        for row, column in alefgard.staircases:
            is_stairs = alefgard.get_tile_by_value(alefgard.layout[row][column]) == 'GRASS_STAIR_DOWN'
            self.assertEqual(alefgard.is_step_warp(row, column), not is_stairs, (row, column))
        for map_name in ('GarinsGraveB2', 'CharlockB2', 'TantegelThroneRoom'):
            current_map = map_lookup[map_name](test_config)
            for row, column in current_map.staircases:
                self.assertFalse(current_map.is_step_warp(row, column), (map_name, row, column))

    def test_a_step_off_the_map_does_not_heal(self):
        self.player.armor = "Erdrick's Armor"
        self.go_to('Garinham', (15, 9))
        self.end_step_on((15, 8))  # the west gate
        self.game.count_step()
        self.assertEqual(self.player.current_hp, 50)
        self.end_step_on((15, 10))
        self.game.count_step()
        self.assertEqual(self.player.current_hp, 51)

    def test_a_step_off_the_map_skips_movement_updates(self):
        self.go_to('Garinham', (15, 9))
        self.end_step_on((15, 8))
        with patch.object(self.game, 'movement_updates') as movement_updates:
            self.game.count_step()
        movement_updates.assert_not_called()

    def test_leaving_charlock_through_its_swamp_does_no_damage_and_starts_no_fight(self):
        # The tiles just outside Charlock's ground floor are swamp here; on the NES the step leaves the map first
        self.go_to('CharlockB1', (25, 17))
        self.end_step_on((26, 17))
        self.assertEqual(self.game.current_map.get_tile_by_value(self.game.current_map.layout[26][17]), 'MARSH')
        self.game.tiles_moved_since_spawn += 1
        with patch.dict(test_config, FORCE_BATTLE=True), \
                patch.object(self.game.battle_ctrl, 'run_battle') as run_battle, \
                patch.object(self.game, 'damage_step') as damage_step:
            self.game.handle_battles()
        run_battle.assert_not_called()
        damage_step.assert_not_called()

    def test_inside_charlock_the_swamp_still_hurts(self):
        self.go_to('CharlockB1', (25, 17))
        self.assertFalse(self.game.current_map.is_map_exit(25, 17))


class TestStepWarps(StepTestCase):
    """The warp check after a step (MapManager.handle_warps)."""

    def warp_after_steps(self, map_name, arrival, cell, steps):
        self.go_to(map_name, arrival)
        self.game.tiles_moved_since_spawn = steps
        self.player.row, self.player.column = cell
        with patch.object(self.game.map_mgr, 'process_warp') as process_warp:
            self.game.handle_warps()
        return process_warp.called

    def test_a_town_gate_is_taken_on_the_first_step(self):
        # NES ChkSpecialLoc -> CheckMapExit on any step off the edge. Before, Garinham's, Kol's and Tantegel's gates
        # needed three steps on the map, so stepping straight back out walked past the gate.
        self.assertTrue(self.warp_after_steps('Garinham', (15, 9), (15, 8), 1))
        self.assertTrue(self.warp_after_steps('Kol', (8, 20), (7, 20), 1))

    def test_an_overworld_entrance_is_taken_on_the_step_onto_it(self):
        alefgard = map_lookup['Alefgard'](test_config)
        entrance = next(iter(alefgard.staircases))
        row, column = entrance
        self.assertTrue(self.warp_after_steps('Alefgard', (row, column + 1), entrance, 1))

    def test_nothing_is_taken_before_a_step(self):
        self.assertFalse(self.warp_after_steps('Garinham', (15, 8), (15, 8), 0))

    def test_stairs_still_wait_for_a_few_steps(self):
        # Unchanged: this project takes stairs by stepping onto them (the NES only by STAIRS), after a few steps
        self.assertFalse(self.warp_after_steps('Garinham', (2, 28), (1, 28), 1))
        self.assertTrue(self.warp_after_steps('Garinham', (2, 28), (1, 28), 3))
