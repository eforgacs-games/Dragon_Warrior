import json
import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

import pygame

from src.config.test_config import test_config
from src.game import Game
from src.maps import CharlockB1, CharlockB2, CharlockB3, map_lookup

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

THRONE = CharlockB1.THRONE_COORDINATES
HIDDEN_STAIRS = CharlockB1.HIDDEN_STAIRCASE_COORDINATES
BARRIER_VALUE = 8
STAIR_DOWN_VALUE = 6
STAIR_UP_VALUE = 7


class TestCharlockHiddenStairs(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()
        cls.screen = pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.game.player.name = "Edward"

    def go_to(self, map_name, coordinates):
        self.game.change_map(map_lookup[map_name](self.game.config), destination_coordinates=coordinates)
        # The hero's row and column normally follow its rect on the next frame
        self.game.player.row, self.game.player.column = coordinates

    def where(self):
        tile_size = self.game.tile_size
        rect = self.game.player.rect
        return self.game.current_map.identifier, (rect.y // tile_size, rect.x // tile_size)

    def search(self):
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text:
            self.game.cmd_menu.search()
        return show_text.call_args.args[0]

    def tile_at(self, coordinates):
        return self.game.current_map.layout[coordinates[0]][coordinates[1]]

    def test_stairs_are_hidden_behind_a_force_field(self):
        charlock = CharlockB1(self.game.config)
        self.assertEqual(charlock.layout[HIDDEN_STAIRS[0]][HIDDEN_STAIRS[1]], BARRIER_VALUE)
        self.assertNotIn(HIDDEN_STAIRS, charlock.staircases)

    def test_searching_behind_the_throne_reveals_the_stairs(self):
        self.go_to('CharlockB1', HIDDEN_STAIRS)
        self.assertEqual(self.search(), ["Edward searched the ground all about.",
                                         "Edward discovers the Secret Passage."])
        self.assertTrue(self.game.story_flags.charlock_stairs_revealed)
        self.assertEqual(self.tile_at(HIDDEN_STAIRS), STAIR_DOWN_VALUE)
        self.assertEqual(self.game.player.current_tile, 'BRICK_STAIR_DOWN')
        self.assertEqual(self.game.current_map.staircases[HIDDEN_STAIRS]['map'], 'CharlockB2')
        # NES: once found, searching there again finds nothing
        self.assertEqual(self.search(), ["Edward searched the ground all about.", "But there found nothing."])

    def test_searching_on_the_throne_only_hints(self):
        self.go_to('CharlockB1', THRONE)
        self.assertEqual(self.search(), ["Edward searched the ground all about.",
                                         "Feel the wind blowing from behind the throne."])
        self.assertFalse(self.game.story_flags.charlock_stairs_revealed)
        self.assertEqual(self.tile_at(HIDDEN_STAIRS), BARRIER_VALUE)

    def test_searching_elsewhere_finds_nothing(self):
        for coordinates in ((HIDDEN_STAIRS[0], HIDDEN_STAIRS[1] - 1), (HIDDEN_STAIRS[0] + 1, HIDDEN_STAIRS[1]),
                            (25, 17)):
            with self.subTest(coordinates=coordinates):
                self.go_to('CharlockB1', coordinates)
                self.assertEqual(self.search(), ["Edward searched the ground all about.",
                                                 "But there found nothing."])
                self.assertFalse(self.game.story_flags.charlock_stairs_revealed)
                self.assertEqual(self.tile_at(HIDDEN_STAIRS), BARRIER_VALUE)
                self.assertNotIn(HIDDEN_STAIRS, self.game.current_map.staircases)

    def test_same_tile_on_another_map_finds_nothing(self):
        self.go_to('CharlockB2', HIDDEN_STAIRS)
        self.assertEqual(self.search(), ["Edward searched the ground all about.", "But there found nothing."])
        self.assertFalse(self.game.story_flags.charlock_stairs_revealed)

    def test_revealed_stairs_lead_to_charlock_b2(self):
        self.go_to('CharlockB1', HIDDEN_STAIRS)
        self.search()
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box'):
            self.game.cmd_menu.stairs()
        # NES MapEntryTbl: DL castle GF(10,1) -> DL castle SL1(9,0)
        self.assertEqual(self.where(), ('CharlockB2', (3, 12)))
        self.assertEqual(self.tile_at((3, 12)), STAIR_UP_VALUE)

    def test_stairs_command_does_nothing_before_reveal(self):
        self.go_to('CharlockB1', HIDDEN_STAIRS)
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text:
            self.game.cmd_menu.stairs()
        self.assertEqual(show_text.call_args.args[0], "There are no stairs here.")
        self.assertEqual(self.game.current_map.identifier, 'CharlockB1')

    def test_stairs_stay_revealed_after_leaving_and_returning(self):
        self.go_to('CharlockB1', HIDDEN_STAIRS)
        self.search()
        self.go_to('Alefgard', (10, 10))
        self.go_to('CharlockB1', (25, 17))
        self.assertEqual(self.tile_at(HIDDEN_STAIRS), STAIR_DOWN_VALUE)
        self.assertIn(HIDDEN_STAIRS, self.game.current_map.staircases)

    def test_climbing_back_up_arrives_on_the_revealed_stairs(self):
        self.go_to('CharlockB1', HIDDEN_STAIRS)
        self.search()
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box'):
            self.game.cmd_menu.stairs()
        self.game.player.row, self.game.player.column = (3, 12)
        self.game.player.current_tile = 'BRICK_STAIR_UP'
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box'):
            self.game.cmd_menu.stairs()
        self.assertEqual(self.where(), ('CharlockB1', HIDDEN_STAIRS))
        self.assertEqual(self.tile_at(HIDDEN_STAIRS), STAIR_DOWN_VALUE)

    def test_save_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.game.directories.save_dir = tmp_dir
            self.game.cmd_menu.directories.save_dir = tmp_dir
            self.game.player.adventure_log = 1
            self.game.story_flags.charlock_stairs_revealed = True
            self.game.cmd_menu.save()
            with open(os.path.join(tmp_dir, 'save_slot_1.json')) as save_file:
                saved = json.load(save_file)
        self.assertTrue(saved['StoryFlags']['charlock_stairs_revealed'])

        with patch('src.game.SCALED'):
            loaded_game = Game(test_config)
        saved['CurrentMap'], saved['PlayerRow'], saved['PlayerColumn'] = 'CharlockB1', 25, 17
        loaded_game.load_game(saved)
        self.assertTrue(loaded_game.story_flags.charlock_stairs_revealed)
        self.assertEqual(loaded_game.current_map.layout[HIDDEN_STAIRS[0]][HIDDEN_STAIRS[1]], STAIR_DOWN_VALUE)
        self.assertIn(HIDDEN_STAIRS, loaded_game.current_map.staircases)

    def test_old_save_without_the_flag_still_loads(self):
        self.game.story_flags.charlock_stairs_revealed = True
        save = {"Name": "Erdrick", "Experience": 0, "Gold": 0, "Inventory": [],
                "CurrentMap": "CharlockB1", "PlayerRow": 25, "PlayerColumn": 17}
        self.game.load_game(save)
        self.assertFalse(self.game.story_flags.charlock_stairs_revealed)
        self.assertEqual(self.tile_at(HIDDEN_STAIRS), BARRIER_VALUE)
        self.assertNotIn(HIDDEN_STAIRS, self.game.current_map.staircases)

    def test_old_save_with_the_flat_flag_still_loads(self):
        save = {"Name": "Erdrick", "Experience": 0, "Gold": 0, "Inventory": [], "CharlockStairsRevealed": True,
                "CurrentMap": "CharlockB1", "PlayerRow": 25, "PlayerColumn": 17}
        with patch('src.game.SCALED'):
            loaded_game = Game(test_config)
        loaded_game.load_game(save)
        self.assertTrue(loaded_game.story_flags.charlock_stairs_revealed)
        self.assertEqual(loaded_game.current_map.layout[HIDDEN_STAIRS[0]][HIDDEN_STAIRS[1]], STAIR_DOWN_VALUE)

    def test_staircase_links_are_symmetric_and_land_on_stairs(self):
        # The staircases between Charlock's ground floor and first two basements follow NES MapEntryTbl/MapTargetTbl,
        # and every one of them lands on a staircase that leads straight back.
        maps = {cls.__name__: cls(self.game.config) for cls in (CharlockB1, CharlockB2, CharlockB3)}
        maps['CharlockB1'].reveal_hidden_staircase()
        for map_name in ('CharlockB1', 'CharlockB2'):
            current = maps[map_name]
            for coordinates, staircase in current.staircases.items():
                if staircase['map'] not in maps:
                    continue  # Overworld exits and CharlockB3's own basements are out of scope here
                with self.subTest(map=map_name, coordinates=coordinates):
                    self.assertIn(current.layout[coordinates[0]][coordinates[1]], (STAIR_DOWN_VALUE, STAIR_UP_VALUE))
                    target = maps[staircase['map']]
                    destination = staircase['destination_coordinates']
                    self.assertIn(target.layout[destination[0]][destination[1]], (STAIR_DOWN_VALUE, STAIR_UP_VALUE))
                    self.assertEqual(target.staircases[destination],
                                     {**target.staircases[destination], 'map': map_name,
                                      'destination_coordinates': coordinates})
