"""The hero's block (row and column) on arriving on a map, and in a snapshot taken then (the autosave written on
entering a town, src/autosave.py): a stale block from the last map made CONTINUE AUTOSAVE crash (IndexError in
DragonWarriorMap.has_floor_tile)."""
import json
from unittest import TestCase
from unittest.mock import patch

import pygame

from src.config.test_config import test_config
from src.maps import map_lookup
from src.save_state import StateError, decode_snapshot, hero_block, restore_snapshot, take_snapshot
from src.title_menu import BACK_TO_TITLE_MENU
from tests import helpers

COURTYARD_BLOCK = (36, 18)  # Tantegel's courtyard, where the hero arrives from the overworld's (50, 51)


class HeroBlockTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.addCleanup(patch.stopall)
        self.game = helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True})
        self.tile = self.game.tile_size

    def arrive_in_the_courtyard(self):
        self.game.player.row, self.game.player.column = 50, 51  # where the hero was on the overworld
        with patch('src.map_manager.screen_fade'), patch.object(self.game.music_player, 'load_and_play_music'):
            self.game.change_map(map_lookup['TantegelCourtyard'](self.game.config),
                                 destination_coordinates=COURTYARD_BLOCK)


class TestArriving(HeroBlockTestCase):

    def test_the_block_is_the_new_maps_at_once(self):
        self.arrive_in_the_courtyard()
        self.assertEqual(COURTYARD_BLOCK, (self.game.player.row, self.game.player.column))

    def test_a_snapshot_taken_then_loads(self):
        self.arrive_in_the_courtyard()
        snapshot = json.loads(json.dumps(take_snapshot(self.game)))
        self.assertEqual(list(COURTYARD_BLOCK), [snapshot['hero']['row'], snapshot['hero']['column']])
        restore_snapshot(self.game, snapshot)
        self.assertEqual(COURTYARD_BLOCK, (self.game.player.row, self.game.player.column))


class TestAnOldAutosave(HeroBlockTestCase):
    """One written before the fix: the courtyard, with the overworld's block."""

    def stale_snapshot(self):
        self.arrive_in_the_courtyard()
        snapshot = json.loads(json.dumps(take_snapshot(self.game)))
        snapshot['hero']['row'], snapshot['hero']['column'] = 50, 51
        return snapshot

    def test_loads_on_the_block_of_its_position(self):
        restore_snapshot(self.game, self.stale_snapshot())
        self.assertEqual('TantegelCourtyard', self.game.current_map.identifier)
        self.assertEqual(COURTYARD_BLOCK, (self.game.player.row, self.game.player.column))

    def test_continue_autosave_loads_it(self):
        with patch('src.title_menu.read_autosave', return_value=self.stale_snapshot()):
            self.assertIsNone(self.game.title_menu.continue_autosave())

    def test_off_the_map_mid_step_is_refused_not_a_crash(self):
        snapshot = self.stale_snapshot()
        snapshot['hero']['is_moving'] = True
        self.assertRaises(StateError, restore_snapshot, self.game, snapshot)
        with patch('src.title_menu.read_autosave', return_value=snapshot):
            self.assertIs(BACK_TO_TITLE_MENU, self.game.title_menu.continue_autosave())

    def test_without_the_tile_size_the_saved_block(self):
        snapshot = self.stale_snapshot()
        snapshot['hero']['row'], snapshot['hero']['column'] = 30, 10
        self.assertEqual((30, 10), (decode_snapshot(snapshot)['hero']['row'],
                                    decode_snapshot(snapshot)['hero']['column']))


class TestHeroBlock(TestCase):

    LAYOUT = [[0] * 4 for _ in range(3)]

    def test_from_the_position_when_on_a_block(self):
        hero = {'row': 9, 'column': 9, 'rect': [64, 32], 'is_moving': False}
        self.assertEqual((1, 2), hero_block(hero, self.LAYOUT, 32))

    def test_in_a_step_the_saved_block(self):
        hero = {'row': 1, 'column': 1, 'rect': [40, 32], 'is_moving': True}
        self.assertEqual((1, 1), hero_block(hero, self.LAYOUT, 32))

    def test_off_the_map(self):
        hero = {'row': 1, 'column': 7, 'rect': [40, 32], 'is_moving': True}
        self.assertRaises(ValueError, hero_block, hero, self.LAYOUT, 32)
