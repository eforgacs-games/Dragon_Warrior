import os
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from src.config.test_config import test_config
from src.direction import Direction
from src.game import Game
from src.maps import map_lookup
from tests.test_shop_dialog import npc_identifiers

# The NPCs outside the towns and Tantegel. (map, graphic, NES X, NES Y, facing, dialog byte), from the Bank00 tables
# DLBFStatTbl, RainStatTbl and RnbwStatTbl (their mobile tables are empty). Gwaelin isn't in an NPC table: she's
# block $6 of SwampCaveDat, which DoTalkResults (Bank03) treats as her.
NPCS = (
    ('CharlockB8', 'DRAGONLORD', 16, 24, Direction.DOWN, 0x70),
    ('StaffOfRainCave', 'WISE_MAN', 4, 4, Direction.RIGHT, 0x6C),
    ('MagicTemple', 'WISE_MAN', 4, 5, Direction.LEFT, 0x6D),
    ('SwampCave', 'PRINCESS_GWAELIN', 5, 18, Direction.DOWN, None),
)

# NES coordinates (X, Y) -> this map's (row, column)
OFFSETS = {
    'CharlockB8': lambda x, y: (y + 4, x + 6),
    'StaffOfRainCave': lambda x, y: (y + 2, x + 2),
    'MagicTemple': lambda x, y: (y + 2, x + 2),
    'SwampCave': lambda x, y: (y + 6, x + 4),
}

# Maps with no NES NPC table: LoadMap (ChkMapDungeon, Bank00) only loads NPCs for MAP_TANTCSTL_GF to MAP_RAINBOW
MAPS_WITHOUT_NPCS = (
    'Hauksness', 'CharlockB1', 'CharlockB2', 'CharlockB3', 'CharlockB4', 'CharlockB5', 'CharlockB6',
    'CharlockB7Wide', 'CharlockB7Narrow', 'ErdricksCaveB1', 'ErdricksCaveB2', 'GarinsGraveB1', 'GarinsGraveB2',
    'GarinsGraveB3', 'GarinsGraveB4', 'MountainCaveB1', 'MountainCaveB2',
)


class TestOtherNPCsDialog(TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.dialog_lookup = self.game.cmd_menu.dialog_lookup

    def load(self, map_name):
        game_map = map_lookup[map_name](test_config)
        game_map.load_map(self.game.player, None, test_config['TILE_SIZE'])
        return game_map

    def test_every_nes_npc_is_on_the_map(self):
        for map_name in OFFSETS:
            expected = {OFFSETS[map_name](x, y): graphic for name, graphic, x, y, _, _ in NPCS if name == map_name}
            self.assertEqual(map_lookup[map_name](test_config).npc_coordinates, expected, map_name)

    def test_maps_without_nes_npcs(self):
        for map_name in MAPS_WITHOUT_NPCS:
            game_map = self.load(map_name)
            self.assertEqual(game_map.npc_coordinates, {}, map_name)
            self.assertNotIn(map_name, self.dialog_lookup.lookup_table)

    def test_every_npc_has_dialog(self):
        for map_name in OFFSETS:
            identifiers = npc_identifiers(map_lookup[map_name](test_config))
            self.assertEqual(set(identifiers.values()), set(self.dialog_lookup.lookup_table[map_name]), map_name)

    def test_no_npc_roams(self):
        for map_name in OFFSETS:
            game_map = self.load(map_name)
            self.assertEqual(game_map.roaming_character_list, [], map_name)
            self.assertEqual(game_map.roaming_characters, [], map_name)

    def test_facing(self):
        # The DD bits of each table entry. Gwaelin's block has only the one picture.
        for map_name, graphic, x, y, facing, _ in NPCS:
            game_map = self.load(map_name)
            identifier = npc_identifiers(game_map)[OFFSETS[map_name](x, y)]
            self.assertEqual(game_map.characters[identifier]['character'].direction_value, facing.value, map_name)

    def test_gwaelin_rescue_dialog(self):
        # NES DoGwaelinRescue: TextBlock12 entry 5, then the PrincessRescueLoop prompt
        self.assertEqual(self.dialog_lookup.lookup_table['SwampCave']['PRINCESS_GWAELIN']['dialog'], (
            f"Thou art brave indeed to rescue me, {self.game.player.name}.",
            "I am Gwaelin, daughter of Lorik.",
            self.dialog_lookup.take_to_castle_confirmation_prompt,
        ))

    def test_dragonlord_dialog(self):
        # NES DoDrgnLrdDialog: TextBlock13 entry 7, TextBlock11 entry 4, TextBlock13 entry 8 and the yes/no window
        self.assertEqual(self.dialog_lookup.lookup_table['CharlockB8']['DRAGONLORD']['dialog'], (
            f"Welcome, {self.game.player.name}.\nI am the Dragonlord--King of Kings.",
            "I have been waiting long for one such as thee.",
            "I give thee now a chance to share this world and to rule half of it if thou will now stand beside me.",
            self.dialog_lookup.dragonlord_offer_prompt,
        ))

    def test_shrine_guardians(self):
        self.assertEqual(self.dialog_lookup.lookup_table['StaffOfRainCave']['WISE_MAN']['dialog'],
                         (self.dialog_lookup.staff_of_rain_guardian,))
        self.assertEqual(self.dialog_lookup.lookup_table['MagicTemple']['WISE_MAN']['dialog'],
                         (self.dialog_lookup.magic_temple_rainbow_drop_exchange,))

    def test_bw_screen_flash(self):
        # NES BWScreenFlash: 8 flashes of 3 greyscale frames, each after 2 frames in color
        self.dialog_lookup.config = dict(test_config, NO_BLIT=False)
        with patch('data.text.dialog_lookup_table.greyscale_screen') as greyscale:
            self.dialog_lookup.bw_screen_flash()
        self.assertEqual(greyscale.call_count, 8)
        for call in greyscale.call_args_list:
            self.assertEqual(call.kwargs['frames'], 3)

    def test_rainbow_drop_shrine_without_token_flashes_black_and_white(self):
        self.game.player.inventory = ['Staff of Rain', 'Stones of Sunlight']
        self.game.change_map(map_lookup['MagicTemple'](test_config), destination_coordinates=(6, 2))
        self.game.player.row, self.game.player.column = 6, 2
        with patch.object(self.game.cmd_menu.dialog_lookup, 'bw_screen_flash') as flash, \
                patch('src.menu.CommandMenu.show_line_in_dialog_box',
                      side_effect=lambda line, *args, **kwargs: line() if callable(line) else None), \
                patch('src.menu.CommandMenu.window_drop_down_effect'), \
                patch('src.menu.CommandMenu.window_drop_up_effect'):
            self.game.cmd_menu.launch_dialog('WISE_MAN', self.game.current_map)
        flash.assert_called_once()
        self.assertEqual(self.game.current_map.identifier, 'Alefgard')
