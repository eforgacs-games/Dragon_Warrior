import json
import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

import pygame

from src.config.test_config import test_config
from src.constants import THRONE_ROOM_DOOR_COORDINATES
from src.direction import Direction
from src.map_layouts import BRICK, DOOR
from src.maps import map_lookup
from tests.helpers import new_game

# The door to the Tantegel cellar (NES TantGFDat 18, 6), and the tile below it
CELLAR_DOOR = (13, 25)
BELOW_CELLAR_DOOR = (14, 25)


class TestOpenDoorHistory(TestCase):
    """NES DoorXPos/DoorYPos: CheckDoor/UseKey (Bank03 LDC42-LDCE0) record each door opened, GetBlockID (Bank00
    ChkDoorBlock, LAD45) reads a recorded door as brick, and InitMapData (ChkOverworldMap, LAF2B-LAF3A) and
    MainGameEngine (LCA0F) clear the history."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()
        pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        self.game = new_game()
        self.game.player.name = "Erdrick"

    def go_to(self, map_name, coordinates):
        self.game.change_map(map_lookup[map_name](self.game.config), destination_coordinates=coordinates)
        self.game.player.row, self.game.player.column = coordinates

    def door(self, standing_at, facing=Direction.UP.value):
        """Use DOOR standing at standing_at, facing the given way. Returns the lines shown."""
        player = self.game.player
        player.row, player.column = standing_at
        player.direction_value = facing
        row, column = standing_at
        player.next_coordinates = {Direction.UP.value: (row - 1, column), Direction.DOWN.value: (row + 1, column),
                                   Direction.LEFT.value: (row, column - 1),
                                   Direction.RIGHT.value: (row, column + 1)}[facing]
        next_row, next_column = player.next_coordinates
        player.next_tile_id = self.game.current_map.get_tile_by_value(
            self.game.current_map.layout[next_row][next_column])
        with patch('src.menu.CommandMenu.show_text_in_dialog_box') as show_text:
            self.game.cmd_menu.door()
        return [call.args[0] for call in show_text.call_args_list]

    def tile(self, coordinates):
        row, column = coordinates
        return self.game.current_map.layout[row][column]

    def open_cellar_door(self):
        self.go_to('TantegelCourtyard', BELOW_CELLAR_DOOR)
        self.game.player.inventory = ['Magic Key', 'Magic Key']
        self.door(BELOW_CELLAR_DOOR)
        self.assertEqual(self.tile(CELLAR_DOOR), BRICK)
        self.assertEqual(self.game.player.inventory, ['Magic Key'])

    def test_door_locks_again_after_the_overworld(self):
        # NES ChkOverworldMap: entering the overworld clears the door history
        self.open_cellar_door()
        self.go_to('Alefgard', (50, 50))
        self.go_to('TantegelCourtyard', BELOW_CELLAR_DOOR)
        self.assertEqual(self.tile(CELLAR_DOOR), DOOR)

    def test_door_stays_open_between_other_maps(self):
        # Only the overworld clears the history: the courtyard -> cellar -> courtyard keeps the door open
        self.open_cellar_door()
        self.go_to('TantegelCellar', (4, 1))
        self.go_to('TantegelCourtyard', BELOW_CELLAR_DOOR)
        self.assertEqual(self.tile(CELLAR_DOOR), BRICK)

    def test_an_opened_door_can_be_opened_again_after_the_overworld(self):
        # Every visit costs another key
        self.open_cellar_door()
        self.go_to('Alefgard', (50, 50))
        self.go_to('TantegelCourtyard', BELOW_CELLAR_DOOR)
        self.door(BELOW_CELLAR_DOOR)
        self.assertEqual(self.tile(CELLAR_DOOR), BRICK)
        self.assertEqual(self.game.player.inventory, [])

    def test_full_history_takes_the_key_but_opens_nothing(self):
        # NES UseKey (DoorCheckLoop, LDCA8-LDCB7): DEC InventoryKeys first; with no free slot, ResumeGamePlay
        self.go_to('TantegelCourtyard', BELOW_CELLAR_DOOR)
        for slot in range(8):
            self.assertTrue(self.game.door_history.record('Cantlin', (slot, slot)))
        self.game.player.inventory = ['Magic Key']
        with patch.object(self.game.cmd_menu.sound, 'play_sound') as play_sound:
            lines = self.door(BELOW_CELLAR_DOOR)
        self.assertEqual(lines, [])
        play_sound.assert_not_called()
        self.assertEqual(self.game.player.inventory, [])
        self.assertEqual(self.tile(CELLAR_DOOR), DOOR)

    def test_continued_game_has_its_doors_locked(self):
        # NES MainGameEngine clears the door history; it isn't saved
        self.open_cellar_door()
        self.game.load_game(self.saved_game())
        self.assertEqual(self.game.current_map.identifier, 'TantegelCourtyard')
        self.assertEqual(self.tile(CELLAR_DOOR), DOOR)

    def saved_game(self) -> dict:
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.game.cmd_menu.directories.save_dir = tmp_dir
            self.game.player.adventure_log = 1
            self.game.cmd_menu.save()
            with open(os.path.join(tmp_dir, 'save_slot_1.json')) as save_file:
                return json.load(save_file)

    def test_throne_room_door_stays_open_after_the_overworld(self):
        # NES ChkLeftThRoom: with F_LEFT_THROOM set, entering the throne room writes its door into history slot 7
        self.go_to('TantegelCourtyard', BELOW_CELLAR_DOOR)
        self.go_to('Alefgard', (50, 50))
        self.go_to('TantegelThroneRoom', (12, 14))
        self.assertTrue(self.game.story_flags.left_throne_room)
        self.assertEqual(self.tile(THRONE_ROOM_DOOR_COORDINATES), BRICK)
        self.assertEqual(self.game.door_history.slots[7], ('TantegelThroneRoom', THRONE_ROOM_DOOR_COORDINATES))
