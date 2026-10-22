import json
from collections import defaultdict
import os
import tempfile
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame
from pygame import RESIZABLE, SCALED
from pygame.imageext import load_extended
from pygame.sprite import LayeredDirty
from pygame.transform import scale

from data.text.dialog_lookup_table import DialogLookup
from data.text.intro_lookup_table import ControlInfo
from src.calculation import get_tile_id_by_coordinates
from src.camera import Camera
from src.common import A_OR_START_KEYS
from src.config.test_config import test_config
from src.direction import Direction
from src.drawer import replace_characters_with_underlying_tiles, convert_numeric_tile_list_to_unique_tile_values, \
    set_to_save_prompt
from src.game import Game
from src.game_functions import get_next_coordinates
from src.map_layouts import MapLayouts
from src.maps import TantegelThroneRoom, TantegelCourtyard, Alefgard
from src.maps_functions import parse_animated_sprite_sheet
from src.menu import CommandMenu
from src.music_player import MusicPlayer
from src.player.player import Player
from src.sprites.roaming_character import RoamingCharacter
from src.waiting import game_speed, reset_game_speed
from tests.mock_map import MockMap

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


def pressed_keys(pressed_key):
    """A stand-in for pygame.key.get_pressed() with one key held. pygame 2 key codes like K_UP are over a billion,
    so this maps codes to states instead of allocating an array that large (4 GB per call)."""
    return defaultdict(int, {pressed_key: 1})


def setup_roaming_character(row, column, direction):
    test_roaming_character = RoamingCharacter(None, direction, None, 'ROAMING_GUARD')
    test_roaming_character.rect = MagicMock()
    test_roaming_character.row = row
    test_roaming_character.column = column
    return test_roaming_character


class TestGame(TestCase):

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
        self.game.cmd_menu.dialog_lookup = DialogLookup(self.game.cmd_menu, self.game.game_state.config)
        self.game.current_map = MockMap(self.game.config)
        unarmed_hero_sheet = load_extended(self.game.directories.UNARMED_HERO_PATH)
        self.game.player = Player((0, 0), parse_animated_sprite_sheet(
            scale(unarmed_hero_sheet, (
                unarmed_hero_sheet.get_width() * self.game.config['SCALE'],
                unarmed_hero_sheet.get_height() * self.game.config['SCALE'])),
            self.game.game_state.config), self.game.current_map, god_mode=self.game.game_state.config['GOD_MODE'])
        tile_size = self.game.game_state.config['TILE_SIZE']
        self.camera = Camera((self.game.player.rect.y // tile_size, self.game.player.rect.x // tile_size),
                             self.game.current_map, self.screen, tile_size)

    def test_get_initial_camera_position(self):
        self.assertEqual((288.0, 256.0), self.camera.pos)
        self.game.current_map.staircases = {
            (10, 13): {'map': 'TantegelThroneRoom', 'destination_coordinates': (14, 18)}}
        # self.game.change_map(TantegelThroneRoom())
        # self.assertEqual((-160.0, -96.0), self.camera.pos)
        # self.game.change_map(TantegelCourtyard())
        # self.assertEqual((-192.0, -224.0), self.camera.pos)

    #     self.game.current_map.layout = [[1, 0],
    #                                     [34, 2]]
    #     initial_hero_location = self.game.current_map.get_initial_character_location('HERO')
    #     self.assertEqual(self.camera.set_camera_position(initial_hero_location), (-16, 0))
    #     self.game.current_map.layout = [[1, 34],
    #                                     [0, 2]]
    #     initial_hero_location = self.game.current_map.get_initial_character_location('HERO')
    #     self.assertEqual(self.camera.set_camera_position(initial_hero_location), (0, -7))
    #     self.game.current_map.layout = [[1, 0],
    #                                     [2, 34]]
    #     initial_hero_location = self.game.current_map.get_initial_character_location('HERO')
    #     self.assertEqual(self.camera.set_camera_position(initial_hero_location), (-16, -7))

    def test_load_game_restores_worn_items(self):
        save = {"Name": "Erdrick", "Experience": 0, "Gold": 0, "Inventory": ["Dragon's Scale"],
                "Armor": "Clothes", "WearingDragonScale": True, "WearingFightersRing": True}
        self.game.load_game(save)
        self.assertTrue(self.game.player.wearing_dragon_scale)
        self.assertTrue(self.game.player.wearing_fighters_ring)
        self.assertEqual(self.game.player.defense_power, self.game.player.agility // 2 + 2 + 2)

    def stats(self):
        player = self.game.player
        return player.strength, player.agility, player.max_hp, player.max_mp

    def test_load_game_works_the_stats_out_from_the_name_and_experience(self):
        """NES LoadStats runs after LoadSavedData: only the name and experience are needed. Erdrick at level 20 cuts
        max HP and max MP and adds 2 (tests/test_player_stats.py)."""
        self.game.load_game({"Name": "Erdrick", "Experience": 26000, "Gold": 0, "Inventory": []})
        self.assertEqual(20, self.game.player.level)
        self.assertEqual((92, 88, 126, 117), self.stats())
        # a second load with another name doesn't keep anything from the first one
        self.game.load_game({"Name": "Steve", "Experience": 26000, "Gold": 0, "Inventory": []})
        self.assertEqual((82, 79, 138, 128), self.stats())
        self.game.load_game({"Name": "Erdrick", "Experience": 26000, "Gold": 0, "Inventory": []})
        self.assertEqual((92, 88, 126, 117), self.stats())

    def test_save_and_load_keep_the_name_based_stats(self):
        player = self.game.cmd_menu.player = self.game.player
        player.name, player.total_experience = "Gina", 2000
        player.level = player.get_level_by_experience()
        player.update_stats_to_current_level()
        self.assertEqual((35, 30, 54, 39), self.stats())
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.game.directories.save_dir = tmp_dir
            self.game.cmd_menu.directories.save_dir = tmp_dir
            player.adventure_log = 1
            self.game.cmd_menu.save()
            with open(os.path.join(tmp_dir, 'save_slot_1.json')) as save_file:
                saved = json.load(save_file)
        player.name, player.total_experience = "Steve", 0
        player.level = player.get_level_by_experience()
        player.update_stats_to_current_level()
        self.game.load_game(saved)
        self.assertEqual(("Gina", 10), (player.name, player.level))
        self.assertEqual((35, 30, 54, 39), self.stats())

    def test_points_to_next_level(self):
        """GetExpRemaining: the next level's LevelUpTbl entry minus the experience."""
        player = self.game.player
        player.total_experience = 30
        player.level = player.get_level_by_experience()
        self.assertEqual(47 - 30, player.points_to_next_level)
        player.total_experience = 65535
        player.level = player.get_level_by_experience()
        self.assertEqual(0, player.points_to_next_level)

    def test_hero_underlying_tile(self):
        self.assertEqual('BRICK', self.game.current_map.hero_underlying_tile())

    # def test_hero_underlying_tile_not_implemented(self):
    #     self.assertRaises(NotImplementedError, self.game.current_map.hero_underlying_tile)

    def test_every_enemy_turn_with_real_player(self):
        # Mocked players hide missing attributes (e.g. is_stopspelled), so run every enemy's turn against the
        # real Player: first exactly as the game creates it, then asleep and stopspelled.
        from src.battle import Battle
        from src.enemy_lookup import enemy_string_lookup

        def take_turns(roll):
            for name in enemy_string_lookup:
                with self.subTest(enemy=name, roll=roll):
                    self.game.player.current_hp = self.game.player.max_hp
                    battle = Battle(self.game.config, name, self.game.current_map)
                    with patch('src.battle_controller.random.randint', side_effect=lambda a, b: roll if b == 99 else a), \
                            patch('src.battle_controller.random.random', return_value=0.99), \
                            patch('src.battle_controller.wait'), patch.object(self.game, 'drawer'), \
                            patch.object(self.game.cmd_menu, 'show_line_in_dialog_box'):
                        self.game.battle_ctrl.enemy_move(battle)

        for roll in (0, 99):
            take_turns(roll)
        self.game.player.is_asleep = True
        self.game.player.is_stopspelled = True
        take_turns(0)

    def go_to(self, map_name, coordinates):
        from src.maps import map_lookup
        self.game.change_map(map_lookup[map_name](self.game.config), destination_coordinates=coordinates)

    def where(self):
        # The hero's row and column follow its rect on the next frame, so read the rect directly
        tile_size = self.game.tile_size
        rect = self.game.player.rect
        return self.game.current_map.identifier, (rect.y // tile_size, rect.x // tile_size)

    def test_outside_leaves_caves(self):
        for map_name, start, expected in (
                ('ErdricksCaveB2', (10, 9), ('Alefgard', (19, 36))),
                ('SwampCave', (6, 4), ('Alefgard', (51, 112))),
                ('MountainCaveB2', (1, 1), ('Alefgard', (64, 37))),
                ('CharlockB8', (33, 16), ('Alefgard', (55, 56))),
                ('GarinsGraveB3', (2, 19), ('Garinham', (0, 28)))):
            with self.subTest(map=map_name):
                self.go_to(map_name, start)
                self.game.cmd_menu.outside()
                self.assertEqual(self.where(), expected)
                self.assertEqual(self.game.player.direction_value, Direction.DOWN.value)
                # the hero stands on the destination's own tile (e.g. the cave entrance), not a staircase
                row, column = expected[1]
                self.assertEqual(self.game.current_map.character_key['HERO']['underlying_tile'],
                                 self.game.current_map.get_tile_by_value(self.game.current_map.layout[row][column]))

    def test_outside_does_nothing_outside_caves(self):
        self.go_to('Brecconary', (7, 23))
        with patch('src.menu.CommandMenu.show_text_in_dialog_box') as show_text:
            self.game.cmd_menu.outside()
        self.assertEqual(self.where(), ('Brecconary', (7, 23)))
        self.assertEqual(show_text.call_args.args[0], 'But nothing happened.')

    def test_return_warps_next_to_tantegel(self):
        self.go_to('Brecconary', (7, 23))
        self.game.cmd_menu.return_()
        self.assertEqual(self.where(), ('Alefgard', (50, 50)))

    def test_return_fails_in_dungeons(self):
        for map_name, start in (('SwampCave', (6, 4)), ('CharlockB8', (33, 16))):
            with self.subTest(map=map_name):
                self.go_to(map_name, start)
                with patch('src.menu.CommandMenu.show_text_in_dialog_box') as show_text:
                    self.game.cmd_menu.return_()
                self.assertEqual(self.where(), (map_name, start))
                self.assertEqual(show_text.call_args.args[0], 'But nothing happened.')

    def test_wings_are_used_up(self):
        self.game.player.inventory = ['Wings', 'Wings']
        self.go_to('Garinham', (11, 29))
        with patch('src.menu.CommandMenu.show_text_in_dialog_box'):
            self.game.cmd_menu.wings()
        self.assertEqual(self.where(), ('Alefgard', (50, 50)))
        self.assertEqual(self.game.player.inventory, ['Wings'])

    def test_wings_cannot_be_used_in_dungeons(self):
        self.game.player.inventory = ['Wings']
        self.go_to('ErdricksCaveB1', (3, 3))
        with patch('src.menu.CommandMenu.show_text_in_dialog_box') as show_text:
            self.game.cmd_menu.wings()
        self.assertEqual(self.where(), ('ErdricksCaveB1', (3, 3)))
        self.assertEqual(self.game.player.inventory, ['Wings'])
        self.assertEqual(show_text.call_args.args[0], 'The Wings of the Wyvern cannot be used here.')

    def test_load_game_on_another_map(self):
        # Used to raise KeyError: change_map looked up a staircase at the player's position
        save = {"Name": "Erdrick", "Experience": 100, "Gold": 50, "Inventory": [],
                "CurrentMap": "Brecconary", "PlayerRow": 10, "PlayerColumn": 10}
        self.game.load_game(save)
        self.assertEqual(self.where(), ('Brecconary', (10, 10)))

    def stand_on(self, map_name, coordinates):
        self.go_to(map_name, coordinates)
        # The game loop syncs row and column with the hero's rect on the next frame
        self.game.player.row, self.game.player.column = coordinates

    def use_rainbow_drop(self):
        with patch('src.menu.CommandMenu.show_text_in_dialog_box') as show_text:
            self.game.cmd_menu.rainbow_drop()
        return [c.args[0] for c in show_text.call_args_list]

    def bridge_tile(self):
        # NES overworld (64, 49)
        return get_tile_id_by_coordinates(72, 56, self.game.current_map)

    def test_rainbow_drop_builds_the_rainbow_bridge(self):
        self.game.player.inventory = ['Rainbow Drop']
        self.stand_on('Alefgard', (56, 73))  # NES overworld (65, 49), the tile east of the bridge
        self.assertEqual(self.bridge_tile(), 'WATER')
        self.assertEqual(self.use_rainbow_drop(), [f'{self.game.player.name} held the Rainbow Drop toward the sky.'])
        self.assertTrue(self.game.story_flags.rainbow_bridge_built)
        self.assertEqual(self.bridge_tile(), 'BRIDGE')
        self.assertFalse(self.game.is_impassable(self.bridge_tile()))
        # NES ChkDrop never removes the Rainbow Drop
        self.assertEqual(self.game.player.inventory, ['Rainbow Drop'])

    def test_rainbow_drop_does_nothing_elsewhere(self):
        self.game.player.inventory = ['Rainbow Drop']
        for map_name, coordinates in (('Alefgard', (56, 74)), ('Alefgard', (50, 50)), ('Brecconary', (7, 23))):
            with self.subTest(map=map_name, coordinates=coordinates):
                self.stand_on(map_name, coordinates)
                self.assertEqual(self.use_rainbow_drop()[-1], 'But no rainbow appeared here.')
                self.assertFalse(self.game.story_flags.rainbow_bridge_built)
                self.assertEqual(self.game.player.inventory, ['Rainbow Drop'])
        self.go_to('Alefgard', (56, 74))
        self.assertEqual(self.bridge_tile(), 'WATER')

    def test_rainbow_drop_only_builds_the_bridge_once(self):
        self.stand_on('Alefgard', (56, 73))
        self.use_rainbow_drop()
        self.assertEqual(self.use_rainbow_drop()[-1], 'But no rainbow appeared here.')
        self.assertEqual(self.bridge_tile(), 'BRIDGE')

    def test_rainbow_bridge_survives_leaving_the_overworld(self):
        self.stand_on('Alefgard', (56, 73))
        self.use_rainbow_drop()
        self.go_to('Brecconary', (7, 23))
        self.go_to('Alefgard', (50, 50))
        self.assertEqual(self.bridge_tile(), 'BRIDGE')
        # The flag alone rebuilds it, even from freshly decoded map layouts
        self.game.layouts = MapLayouts()
        self.go_to('Brecconary', (7, 23))
        self.go_to('Alefgard', (50, 50))
        self.assertEqual(self.bridge_tile(), 'BRIDGE')

    def test_rainbow_bridge_save_round_trip(self):
        self.stand_on('Alefgard', (56, 73))
        self.use_rainbow_drop()
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.game.cmd_menu.directories.save_dir = tmp_dir
            self.game.player.adventure_log = 1
            self.game.cmd_menu.save()
            with open(os.path.join(tmp_dir, 'save_slot_1.json')) as save_file:
                save = json.load(save_file)
        self.assertTrue(save['StoryFlags']['rainbow_bridge_built'])

        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.assertFalse(self.game.story_flags.rainbow_bridge_built)
        self.game.load_game(save)
        self.assertTrue(self.game.story_flags.rainbow_bridge_built)
        self.assertEqual(self.where(), ('Alefgard', (56, 73)))
        self.assertEqual(self.bridge_tile(), 'BRIDGE')

    def test_load_game_without_rainbow_bridge_key(self):
        save = {"Name": "Erdrick", "Experience": 0, "Gold": 0, "Inventory": [],
                "CurrentMap": "Alefgard", "PlayerRow": 56, "PlayerColumn": 73}
        self.game.story_flags.rainbow_bridge_built = True
        self.game.load_game(save)
        self.assertFalse(self.game.story_flags.rainbow_bridge_built)

    def walk(self, steps):
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text:
            for _ in range(steps):
                self.game.count_step()
        return [c.args[0] for c in show_text.call_args_list]

    def test_repel_lasts_127_steps(self):
        self.game.repel_timer = 255
        self.assertEqual(self.walk(126), [])
        self.assertTrue(self.game.repel_timer)
        self.assertEqual(self.walk(1), ['REPEL has lost its effect.'])
        self.assertEqual(self.game.repel_timer, 0)
        self.assertEqual(self.walk(5), [])

    def test_fairy_water_lasts_127_steps(self):
        self.game.repel_timer = 254
        self.assertEqual(self.walk(126), [])
        self.assertEqual(self.walk(1), ['The Fairy Water has lost its effect.'])

    def test_radiant_light_shrinks_as_the_hero_walks(self):
        # NES GameEngineLoop counts RadiantTimer down once per step
        self.go_to('ErdricksCaveB1', (0, 0))
        self.game.game_state.cast_radiant()
        light = []
        for _ in range(201):
            self.walk(1)
            light.append(self.game.game_state.light_diameter)
        self.assertEqual(light, [7] * 79 + [5] * 60 + [3] * 60 + [1] * 2)

    def test_light_lasts_between_dungeon_floors_but_not_outside(self):
        # NES InitMapData only resets LightDiameter and RadiantTimer on maps that aren't dungeons
        self.go_to('ErdricksCaveB1', (0, 0))
        self.game.game_state.cast_radiant()
        self.walk(10)
        self.go_to('ErdricksCaveB2', (10, 9))
        self.assertEqual(self.game.game_state.light_diameter, 7)
        self.assertEqual(self.game.game_state.radiant_timer, 0x50 - 10)
        self.game.cmd_menu.outside()
        self.assertEqual(self.game.current_map.identifier, 'Alefgard')
        self.assertEqual(self.game.game_state.light_diameter, 1)
        self.assertEqual(self.game.game_state.lit_diameter, 1)
        self.assertEqual(self.game.game_state.radiant_timer, 0)

    def die(self, in_battle):
        self.game.battle_ctrl.launch_battle = in_battle
        self.game.player.current_hp = 0
        self.game.player.gold = 101
        with patch.object(self.game.battle_ctrl, 'draw_command_window') as command_window, \
                patch.object(self.game, 'drawer') as drawer, \
                patch.object(self.game, 'music_player'), patch('src.game.display'), \
                patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text:
            self.game.handle_death()
        return command_window, drawer, show_text

    def test_death_in_battle(self):
        command_window, drawer, show_text = self.die(in_battle=True)
        command_window.assert_called_once_with(True)
        drawer.draw_all_tiles_in_current_map.assert_not_called()
        self.assertFalse(self.game.battle_ctrl.launch_battle)
        show_text.assert_called_once_with("Thou art dead.", disable_sound=True, advance_keys=A_OR_START_KEYS)
        self.assertEqual(self.game.current_map.identifier, 'TantegelThroneRoom')
        self.assertEqual(self.game.player.current_hp, self.game.player.max_hp)
        self.assertEqual(self.game.player.gold, 50)

    def test_death_outside_battle(self):
        # e.g. from swamp or barrier damage
        command_window, drawer, show_text = self.die(in_battle=False)
        command_window.assert_not_called()
        drawer.draw_all_tiles_in_current_map.assert_called_once()
        show_text.assert_called_once_with("Thou art dead.", disable_sound=True, advance_keys=A_OR_START_KEYS)

    def test_get_tile_by_coordinates(self):
        self.assertEqual('BRICK', get_tile_id_by_coordinates(0, 0, self.game.current_map))
        self.assertEqual('ROOF', get_tile_id_by_coordinates(1, 0, self.game.current_map))
        self.assertEqual('WALL', get_tile_id_by_coordinates(0, 1, self.game.current_map))
        self.assertEqual('WOOD', get_tile_id_by_coordinates(1, 1, self.game.current_map))

    def test_roaming_character_stays_on_the_map(self):
        # NES ChkNPCMapLimit (Bank00): an NPC on the map's edge can't step off it
        test_roaming_character = setup_roaming_character(row=2, column=2, direction=Direction.DOWN.value)
        test_roaming_character.rect.y = 0
        self.game.move_medially(test_roaming_character)
        self.assertEqual(0, test_roaming_character.rect.y)
        test_roaming_character.direction_value = Direction.RIGHT.value
        test_roaming_character.rect.x = 0
        self.game.move_laterally(test_roaming_character)
        self.assertEqual(0, test_roaming_character.rect.x)

    def test_move_roaming_character_medially(self):
        test_roaming_character = setup_roaming_character(row=1, column=2, direction=Direction.UP.value)
        test_roaming_character.rect.y = 0
        self.game.move_medially(test_roaming_character)
        self.assertEqual(-2, test_roaming_character.rect.y)
        test_roaming_character.direction_value = Direction.DOWN.value
        self.game.move_medially(test_roaming_character)
        self.assertEqual(0, test_roaming_character.rect.y)

    def test_move_roaming_character_laterally(self):
        test_roaming_character = setup_roaming_character(row=2, column=1, direction=Direction.LEFT.value)
        test_roaming_character.rect.x = 0
        self.game.move_laterally(test_roaming_character)
        self.assertEqual(-2, test_roaming_character.rect.x)
        test_roaming_character.direction_value = Direction.RIGHT.value
        self.game.move_laterally(test_roaming_character)
        self.assertEqual(0, test_roaming_character.rect.x)

    def test_roaming_character_blocked_by_object(self):
        test_roaming_character = setup_roaming_character(row=2, column=0, direction=Direction.UP.value)
        test_roaming_character.rect.y = 0
        self.game.move_medially(test_roaming_character)
        self.assertEqual(0, test_roaming_character.rect.y)

    # TODO(ELF): Write tests that test the test_roaming_character.row / column update correctly after moving/not moving

    @patch('src.menu.CommandMenu.show_text_in_dialog_box')
    def test_handle_fps_changes(self, mock_show_text_in_dialog_box):
        """Keys 1 to 4 set the game speed to 1x, 2x, 4x or 8x: the main loop runs at 60 FPS times the speed."""
        self.addCleanup(reset_game_speed)
        for key_code, speed, label in ((pygame.K_2, 2, '2x'), (pygame.K_3, 4, '4x'),
                                       (pygame.K_4, 8, '8x'), (pygame.K_1, 1, 'normal')):
            with self.subTest(speed=speed):
                self.game.handle_fps_changes(pygame.event.Event(pygame.KEYDOWN, key=key_code))
                self.assertEqual(speed, game_speed())
                self.assertEqual(60 * speed, self.game.fps)
                self.assertEqual(f"Game set to {label} speed.\n({60 * speed} FPS)",
                                 mock_show_text_in_dialog_box.call_args.args[0])

    def test_handle_start_button(self):
        self.assertFalse(self.game.paused)
        keydown_event = pygame.event.Event(pygame.KEYDOWN, unicode="i", key=pygame.K_i, mod=pygame.KMOD_NONE)
        self.game.handle_start_button(keydown_event)
        self.assertTrue(self.game.paused)
        keydown_event = pygame.event.Event(pygame.KEYDOWN, unicode="i", key=pygame.K_i, mod=pygame.KMOD_NONE)
        self.game.handle_start_button(keydown_event)
        self.assertFalse(self.game.paused)

    def test_handle_a_button(self):
        # B closes the COMMAND window from inside it (CommandMenu.select_command; see tests/test_command_window.py)
        self.assertFalse(self.game.cmd_menu.launch_signaled)
        keydown_event = pygame.event.Event(pygame.KEYDOWN, unicode="k", key=pygame.K_k, mod=pygame.KMOD_NONE)
        self.game.handle_a_button(keydown_event)
        self.assertTrue(self.game.cmd_menu.launch_signaled)

    def test_replace_characters_with_underlying_tiles(self):
        self.game.current_map.character_key['HERO']['underlying_tile'] = 'BRICK'
        self.assertEqual(['BRICK'],
                         replace_characters_with_underlying_tiles(['HERO'], self.game.current_map.character_key))

    def test_convert_numeric_tile_list_to_unique_tile_values(self):
        self.assertEqual(['WALL',
                          'WOOD',
                          'BRICK',
                          'TREASURE_BOX',
                          'DOOR',
                          'BRICK_STAIR_DOWN',
                          'BRICK_STAIR_UP',
                          'BARRIER',
                          'WEAPON_SIGN'],
                         convert_numeric_tile_list_to_unique_tile_values(self.game.current_map,
                                                                         [1, 2, 3, 4, 5, 6, 7, 8, 9]))

    @patch('pygame.mixer.music')
    def test_handle_menu_launch(self, mock_music):
        self.game.cmd_menu.launch_signaled = True
        self.game.drawer.handle_menu_launch(self.game.screen, self.game.cmd_menu, self.game.cmd_menu)
        self.assertTrue(self.game.cmd_menu.menu.is_enabled())
        self.game.drawer.handle_menu_launch(self.game.screen, self.game.cmd_menu, self.game.cmd_menu)

    def test_change_map(self):
        self.game.player.row = 10
        self.game.player.column = 13
        self.game.current_map.staircases = {
            (10, 13): {'map': 'TantegelThroneRoom', 'destination_coordinates': (14, 18)}}
        self.game.change_map(TantegelThroneRoom(self.game.config))
        self.assertEqual('MockMap', self.game.last_map.identifier)
        self.assertEqual('TantegelThroneRoom', self.game.current_map.identifier)
        self.game.player.row = 14
        self.game.player.column = 18
        self.game.last_map = TantegelThroneRoom(self.game.config)
        self.game.change_map(TantegelCourtyard(self.game.config))
        self.assertTrue(self.game.story_flags.left_throne_room)
        self.game.music_enabled = False
        self.game.player.row = 14
        self.game.player.column = 14
        self.game.change_map(TantegelThroneRoom(self.game.config))

    def test_change_map_maintain_inventory_and_gold(self):
        self.game.player.row = 10
        self.game.player.column = 13
        self.game.player.gold = 120
        self.game.player.inventory = ['Torch']
        self.game.current_map.staircases = {
            (10, 13): {'map': 'TantegelThroneRoom', 'destination_coordinates': (14, 18)}}
        self.game.change_map(TantegelThroneRoom(self.game.config))
        self.assertEqual(120, self.game.player.gold)
        self.assertEqual(['Torch'], self.game.player.inventory)

    def test_king_lorik_initial_dialog(self):
        self.assertEqual((
            "Descendant of Erdrick, listen now to my words.",
            "It is told that in ages past Erdrick fought demons with a Ball of Light.",
            "Then came the Dragonlord who stole the precious globe and hid it in the darkness.",
            "Now, Edward, thou must help us recover the Ball of Light and restore peace to our land.",
            "The Dragonlord must be defeated.",
            "Take now whatever thou may find in these Treasure Chests to aid thee in thy quest.",
            "Then speak with the guards, for they have much knowledge that may aid thee.",
            "May the light shine upon thee, Edward."
        ), self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'])

    def test_king_lorik_post_initial_dialog(self):
        self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['is_initial_dialog'] = False
        self.game.drawer.set_to_post_initial_dialog(self.game.cmd_menu)
        self.assertEqual("When thou art finished preparing for thy departure, please see me.\nI shall wait.",
                         self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'])

    def test_wise_man_tantegel_courtyard_dialog(self):
        self.assertEqual("Edward's coming was foretold by legend. May the light shine upon "
                         'this brave warrior.',
                         self.game.cmd_menu.dialog_lookup.lookup_table['TantegelCourtyard']['WISE_MAN']['dialog'][0])

    # gives an IndexError: list index out of range because the constants for K_UP, etc. are huge
    # def test_move_player_directions(self):
    #     self.assertEqual(Direction.UP.value, self.game.player.direction_value)
    #     pygame.key.get_pressed = create_key_mock(pygame.K_s)
    #     self.game.move_player(pygame.key.get_pressed())
    #     self.assertEqual(Direction.DOWN.value, self.game.player.direction_value)

    def test_run_automatic_initial_dialog(self):
        self.assertTrue(self.game.game_state.is_initial_dialog)
        self.game.drawer.run_automatic_initial_dialog(self.game.events, self.game.skip_text, self.game.cmd_menu)
        self.assertFalse(self.game.game_state.enable_movement)
        # TODO(ELF): Need to enable the following checks:
        # self.assertFalse(self.game.is_initial_dialog)
        # self.assertTrue(self.game.game_state.automatic_initial_dialog_run)

    def test_set_to_save_prompt(self):
        self.game.player.name = "Edward"
        self.assertEqual((
            "Descendant of Erdrick, listen now to my words.",
            "It is told that in ages past Erdrick fought demons with a Ball of Light.",
            "Then came the Dragonlord who stole the precious globe and hid it in the darkness.",
            f"Now, {self.game.player.name}, thou must help us recover the Ball of Light and restore peace to our land.",
            "The Dragonlord must be defeated.",
            "Take now whatever thou may find in these Treasure Chests to aid thee in thy quest.",
            "Then speak with the guards, for they have much knowledge that may aid thee.",
            f"May the light shine upon thee, {self.game.player.name}."
        ), self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'])
        set_to_save_prompt(self.game.cmd_menu)
        self.assertEqual((
            f"I am greatly pleased that thou hast returned, {self.game.player.name}.",
            f"Before reaching thy next level of experience thou must gain {self.game.player.points_to_next_level} Points.",
            # "Will thou tell me now of thy deeds so they won't be forgotten?",
            # if yes:
            # "Thy deeds have been recorded on the Imperial Scrolls of Honor.",
            # "Dost thou wish to continue thy quest?",
            # if yes:
            # f"Goodbye now, {self.game.player.name}.\n'Take care and tempt not the Fates.",
            # if no:
            # "Rest then for awhile."
        ), (self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][0],
            self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][1],
            # self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][2],
            # self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][3],
            # self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][4],
            ))

    @patch('src.menu.CommandMenu.show_text_line_in_dialog_box')
    @patch('src.menu.CommandMenu.window_drop_up_effect')
    @patch('src.menu.CommandMenu.window_drop_down_effect')
    @patch('src.visual_effects.fade')
    def test_travelers_inn(self, mock_show_text_line_in_dialog_box, mock_window_drop_up_effect,
                           mock_window_drop_down_effect, mock_fade):
        self.game.current_map = Alefgard(self.game.config)
        self.game.player.row, self.game.player.column = 48, 56
        # organically switch maps to Brecconary, as though entering from Alefgard
        for staircase_location, staircase_dict in self.game.current_map.staircases.items():
            self.game.process_staircase_warps(staircase_location, staircase_dict)
        self.game.player.current_hp = 1
        self.game.player.current_mp = 1
        self.game.player.direction_value = Direction.RIGHT.value
        self.game.current_map.load_map(self.game.player, (23, 10), self.game.tile_size)
        self.assertEqual('Brecconary', self.game.current_map.identifier)
        self.assertTrue('MERCHANT_2' in self.game.current_map.characters)
        self.assertTrue(self.game.current_map.characters['MERCHANT_2']['coordinates'] == (29, 20))
        self.assertEqual((23, 10), self.game.current_map.destination_coordinates)
        self.assertEqual((23, 10), self.game.current_map.initial_coordinates)
        self.game.cmd_menu.skip_text = True
        self.game.player.gold = 10
        self.game.player.row, self.game.player.column = 29, 18
        self.game.player.next_next_coordinates = get_next_coordinates(18, 29, self.game.player.direction_value,
                                                                      offset_from_character=2)
        self.assertEqual((29, 20), self.game.player.next_next_coordinates)
        self.assertEqual('BRICK', get_tile_id_by_coordinates(self.game.player.next_next_coordinates[1],
                                                             self.game.player.next_next_coordinates[0],
                                                             self.game.current_map))
        self.game.player.next_tile_id = self.game.calculation.get_next_tile_identifier(self.game.player.column,
                                                                                       self.game.player.row,
                                                                                       self.game.player.direction_value,
                                                                                       self.game.current_map)
        self.assertEqual('WOOD', self.game.player.next_tile_id)
        self.game.player.next_coordinates = get_next_coordinates(self.game.player.column, self.game.player.row,
                                                                 direction=self.game.player.direction_value)
        self.assertEqual((29, 19), self.game.player.next_coordinates)
        self.game.cmd_menu.talk()
        self.assertEqual(self.game.player.max_hp, self.game.player.current_hp)
        self.assertEqual(self.game.player.max_mp, self.game.player.current_mp)
        # checking that it won't work if you don't have enough gold
        self.assertEqual(4, self.game.player.gold)
        self.game.player.current_hp = 2
        self.game.player.current_mp = 3
        self.game.cmd_menu.talk()
        self.assertEqual(2, self.game.player.current_hp)
        self.assertEqual(3, self.game.player.current_mp)
        self.assertEqual(4, self.game.player.gold)

    def test_unlaunch_menu(self):
        self.game.cmd_menu.menu.enable()
        with patch.object(CommandMenu, 'window_drop_up_effect', return_value=None) as mock_window_drop_up_effect:
            self.assertFalse(self.game.cmd_menu.launch_signaled)
            self.game.unlaunch_menu(self.game.cmd_menu)
            self.assertTrue(self.game.game_state.enable_animate)
            self.assertTrue(self.game.game_state.enable_roaming)
            self.assertTrue(self.game.game_state.enable_movement)
            self.assertFalse(self.game.cmd_menu.menu.is_enabled())
        mock_window_drop_up_effect.assert_called_with(6, 1, 8, 5)

    @patch('src.menu.CommandMenu.show_text_in_dialog_box')
    def test_handle_initial_dialog(self, mock_show_text_in_dialog_box):
        self.game.initial_dialog_enabled = True
        self.game.skip_text = True
        self.game.current_map.identifier = 'TantegelThroneRoom'
        self.assertEqual(('Descendant of Erdrick, listen now to my words.',
                          'It is told that in ages past Erdrick fought demons with a Ball of Light.',
                          'Then came the Dragonlord who stole the precious globe and hid it in the '
                          'darkness.',
                          'Now, Edward, thou must help us recover the Ball of Light and restore peace '
                          'to our land.',
                          'The Dragonlord must be defeated.',
                          'Take now whatever thou may find in these Treasure Chests to aid thee in thy '
                          'quest.',
                          'Then speak with the guards, for they have much knowledge that may aid thee.',
                          'May the light shine upon thee, Edward.'),
                         self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'])
        self.game.drawer.handle_initial_dialog(self.game.initial_dialog_enabled, self.game.cmd_menu, self.game.events,
                                               self.game.skip_text, self.game.story_flags.left_throne_room)
        self.assertFalse(self.game.drawer.display_hovering_stats)
        self.assertFalse(self.game.cmd_menu.launch_signaled)
        self.assertTrue(self.game.game_state.automatic_initial_dialog_run)
        self.assertEqual('When thou art finished preparing for thy departure, please see me.\nI shall wait.',
                         self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'])
        self.game.story_flags.left_throne_room = True
        self.game.drawer.handle_initial_dialog(self.game.initial_dialog_enabled, self.game.cmd_menu, self.game.events,
                                               self.game.skip_text, self.game.story_flags.left_throne_room)
        self.assertFalse(self.game.game_state.is_initial_dialog)
        self.assertEqual(('I am greatly pleased that thou hast returned, Edward.',
                          'Before reaching thy next level of experience thou must gain 7 Points.',
                          # "Will thou tell me now of thy deeds so they won't be forgotten?",
                          # 'Thy deeds have been recorded on the Imperial Scrolls of Honor.',
                          # 'Dost thou wish to continue thy quest?',
                          # "Goodbye now, Edward.\n'Take care and tempt not the Fates."),
                          ),
                         (
                         self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][0],
                         self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][1],
                         # self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][2],
                         # self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][3],
                         # self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][4],
                         # self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']['dialog'][5]
                         ))
        self.assertFalse(self.game.game_state.is_initial_dialog)

    def test_drop_down_hovering_stats_window(self):
        with patch.object(CommandMenu, 'window_drop_down_effect', return_value=None) as mock_window_drop_down_effect:
            self.game.cmd_menu.window_drop_down_effect(1, 2, 4, 6)
            self.game.hovering_stats_displayed = True
            self.assertTrue(self.game.hovering_stats_displayed)
        mock_window_drop_down_effect.assert_called_with(1, 2, 4, 6)

    # select button doesn't do anything (for now). Commenting it out to keep the unit tests fast.

    # def test_handle_select_button(self):
    #     pygame.key.get_pressed = create_key_mock_u(pygame.K_u)
    #     self.game.handle_select_button(pygame.key.get_pressed())

    def test_handle_help_button(self):
        with patch.object(CommandMenu, 'show_text_in_dialog_box', return_value=None) as mock_show_text_in_dialog_box:
            keydown_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1, mod=pygame.KMOD_NONE)
            self.game.handle_help_button(keydown_event)
        # a tuple, so the dialog box shows one page at a time and waits for the A button between them
        mock_show_text_in_dialog_box.assert_called_once_with(ControlInfo(test_config).help_pages)

    def test_handle_help_button_ignores_other_keys(self):
        with patch.object(CommandMenu, 'show_text_in_dialog_box', return_value=None) as mock_show_text_in_dialog_box:
            self.game.handle_help_button(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F2, mod=pygame.KMOD_NONE))
        mock_show_text_in_dialog_box.assert_not_called()

    # def test_handle_keypresses(self):
    #     pygame.key.get_pressed = create_f1_key_mock(pygame.K_k)
    #     self.game.handle_keypresses(pygame.key.get_pressed())
    #     pygame.key.get_pressed = create_f1_key_mock(pygame.K_j)
    #     self.game.handle_keypresses(pygame.key.get_pressed())

    def test_get_events(self):
        self.game.get_events()
        # this is a weird value for the player current tile (wraps to layout[-1][-1])
        self.assertEqual('BRICK', self.game.player.current_tile)
        self.assertEqual((0, -1), self.game.player.next_coordinates)
        self.assertEqual((1, -1), self.game.player.next_next_coordinates)
        self.game.game_state.enable_roaming = True
        self.game.player.row = 10
        self.game.player.column = 13
        self.game.current_map.staircases = {
            (10, 13): {'map': 'TantegelThroneRoom', 'destination_coordinates': (14, 18)}}
        self.game.change_map(TantegelThroneRoom(self.game.config))
        self.game.get_events()

    def test_draw_all(self):
        self.game.drawer.draw_all(self.game.screen, self.game.loop_count, self.game.big_map, self.game.current_map,
                                  self.game.player, self.game.cmd_menu, self.game.foreground_rects,
                                  self.game.game_state.enable_animate, self.game.camera, self.game.initial_dialog_enabled,
                                  self.game.events, self.game.skip_text, self.game.story_flags.left_throne_room,
                                  self.game.game_state, self.game.color)
        self.assertTrue(self.game.drawer.not_moving_time_start)

    # def test_handle_sprite_drawing_and_animation(self):
    #     self.game.handle_sprite_drawing_and_animation()

    def test_move_roaming_characters(self):
        # test with no roaming characters
        self.game.move_roaming_characters()
        self.game.player.row = 10
        self.game.player.column = 13
        self.game.current_map.staircases = {
            (10, 13): {'map': 'TantegelThroneRoom', 'destination_coordinates': (14, 18)}}
        self.game.change_map(TantegelThroneRoom(self.game.config))
        self.game.current_map.load_map(self.game.player, (14, 18), self.game.game_state.config["TILE_SIZE"])
        # test with moving characters before they're moving
        for roaming_character in self.game.current_map.roaming_characters:
            self.assertFalse(roaming_character.is_moving)
        # The first frame on a map is the first pair's decision frame (NES InitMapData: NPCUpdateCntr = 0)
        guard = self.game.current_map.roaming_characters[0]
        start = guard.rect.topleft
        with patch('src.game.random.choice', return_value=Direction.DOWN.value):
            self.game.do_sprites()
        self.assertTrue(guard.is_moving)
        self.assertEqual(Direction.DOWN.value, guard.direction_value)
        # test with moving characters once they're moving: 1 NES pixel a frame, 16 frames a step
        for _ in range(15):
            self.game.do_sprites()
        self.assertFalse(guard.is_moving)
        self.assertEqual((start[0], start[1] + self.game.tile_size), guard.rect.topleft)

    def test_move_and_handle_sides_collision(self):
        self.game.player.rect.x = -1
        self.game.move_and_handle_sides_collision(-1, 1)
        self.assertEqual(0, self.game.player.rect.x)
        self.game.player.rect.y = -1
        self.game.move_and_handle_sides_collision(1, -1)
        self.assertEqual(0, self.game.player.rect.y)
        self.game.player.rect.x = 65
        self.game.move_and_handle_sides_collision(65, 1)
        self.assertEqual(64, self.game.player.rect.x)
        self.game.player.rect.y = 65
        self.game.move_and_handle_sides_collision(1, 65)
        self.assertEqual(64, self.game.player.rect.y)

    def test_move_player_up(self):
        """Test moving the player up."""
        keys = pressed_keys(pygame.K_w)
        self.game.current_map.player_sprites = LayeredDirty(self.game.player)
        self.assertEqual(self.game.player.rect.y, -16)
        self.game.move_player(keys)
        # I'm not sure why this is -18, need to investigate
        self.assertEqual(self.game.player.rect.y, -18)
        self.assertEqual(Direction.UP.value, self.game.player.direction_value)

    def test_move_player_left(self):
        """Test moving the player left."""
        keys = pressed_keys(pygame.K_a)
        self.game.current_map.player_sprites = LayeredDirty(self.game.player)
        initial_x = self.game.player.rect.x
        self.game.move_player(keys)
        self.assertEqual(initial_x + 16, self.game.player.rect.x)
        self.assertEqual(Direction.LEFT.value, self.game.player.direction_value)

    def test_move_player_down(self):
        """Test moving the player down.
        The player should not move if there is an impassable object in the way."""
        keys = pressed_keys(pygame.K_s)
        self.game.current_map.player_sprites = LayeredDirty(self.game.player)
        self.assertEqual(self.game.player.rect.y, -16)
        self.game.move_player(keys)
        # impassable object in way of player
        self.assertEqual(self.game.player.rect.y, -16)
        self.assertEqual(Direction.DOWN.value, self.game.player.direction_value)

    def test_move_player_right(self):
        """Test moving the player right."""
        keys = pressed_keys(pygame.K_d)
        self.game.current_map.player_sprites = LayeredDirty(self.game.player)
        initial_x = self.game.player.rect.x
        self.game.move_player(keys)
        self.assertEqual(self.game.player.rect.x, initial_x + 16)
        self.assertEqual(Direction.RIGHT.value, self.game.player.direction_value)

    @patch('src.game.Game.set_screen')
    def test_flags_fullscreen_disabled(self, mock_set_screen):
        self.game.fullscreen_enabled = False
        self.game.__init__(test_config)
        self.assertEqual(RESIZABLE | SCALED, self.game.flags)

    @patch('src.game.Game.set_screen')
    def test_flags_fullscreen_enabled(self, mock_set_screen):
        self.game.fullscreen_enabled = True
        self.game.__init__(test_config)
        # seems like an integer overflow happens if we try:
        # self.assertEqual(FULLSCREEN | SCALED, self.game.flags)
        self.assertEqual(528, self.game.flags)

    @patch('src.game.Game.set_screen')
    @patch.object(MusicPlayer, "load_and_play_music")
    def test_splash_screen_enabled_load_and_play_music(self, mock_load_and_play_music, mock_set_screen):
        splash_config = {**test_config, "SPLASH_SCREEN_ENABLED": True}
        self.game.__init__(splash_config)
        mock_load_and_play_music.assert_called_once_with(self.game.directories.intro_overture)

    # @patch('src.config')
    # def test_splash_screen_disabled_load_and_play_music(self, mocked_config):
    #     # self.game.splash_screen_enabled = False
    #     with patch.object(Game, 'load_and_play_music') as mock_method:
    #         self.game.__init__()
    #     mock_method.assert_called_once_with(self.game.current_map.music_file_path)

    # this test fails in GitHub Actions

    # def test_show_main_menu_screen(self):
    #     mocked_return = MagicMock()
    #     mocked_return.type = KEYDOWN
    #     mocked_return.key = K_RETURN
    #     with patch.object(event, 'get', return_value=[mocked_return]) as mock_method:
    #         self.game.show_main_menu_screen(self.game.screen)

    def test_change_message_speed_leaves_no_wait_alone(self):
        # it used to flip NO_WAIT; now it picks a log and its speed (tests/test_options_screen.py)
        original = self.game.game_state.config['NO_WAIT']
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.game.directories.save_dir = tmp_dir
            self.game.save_dir_contents = []
            self.game.change_message_speed()
        self.assertEqual(original, self.game.game_state.config['NO_WAIT'])

    def test_continue_quest_shows_the_saved_name_on_the_log(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.game.directories.save_dir = tmp_dir
            with open(os.path.join(tmp_dir, 'save_slot_1.json'), 'w') as f:
                json.dump({'Name': 'Ed'}, f)
            self.game.save_dir_contents = os.listdir(tmp_dir)
            with patch.object(self.game.game_functions, 'main_menu_selection', return_value=0) as mock_selection, \
                    patch.object(self.game, 'load_game'), patch.object(self.game, 'music_player'), \
                    patch('src.map_manager.screen_fade'), patch('src.game.CommandMenu'):
                self.game.continue_quest()
            overlay = mock_selection.call_args.kwargs['overlay']
            self.assertEqual('Ed  ', overlay.texts[0].text)
            self.assertEqual((24, 14), (overlay.texts[0].column, overlay.texts[0].row))

    def test_erase_quest_removes_save_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.game.directories.save_dir = tmp_dir
            save_path = os.path.join(tmp_dir, 'save_slot_1.json')
            with open(save_path, 'w') as f:
                json.dump({'Name': 'Hero'}, f)
            with patch.object(self.game.game_functions, 'main_menu_selection', return_value=0):
                self.game.erase_quest()
            self.assertFalse(os.path.exists(save_path))

    def test_erase_quest_missing_file_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.game.directories.save_dir = tmp_dir
            with patch.object(self.game.game_functions, 'main_menu_selection', return_value=0):
                self.game.erase_quest()  # should not raise

    def test_copy_quest_copies_save_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.game.directories.save_dir = tmp_dir
            src_path = os.path.join(tmp_dir, 'save_slot_1.json')
            dst_path = os.path.join(tmp_dir, 'save_slot_2.json')
            with open(src_path, 'w') as f:
                json.dump({'Name': 'Hero'}, f)
            # first call = pick src slot (0 → slot 1), second = pick dst slot (1 → slot 2)
            with patch.object(self.game.game_functions, 'main_menu_selection', side_effect=[0, 1]):
                self.game.copy_quest()
            self.assertTrue(os.path.exists(dst_path))
            with open(dst_path) as f:
                self.assertEqual({'Name': 'Hero'}, json.load(f))

    def test_copy_quest_same_slot_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.game.directories.save_dir = tmp_dir
            src_path = os.path.join(tmp_dir, 'save_slot_1.json')
            with open(src_path, 'w') as f:
                json.dump({'Name': 'Hero'}, f)
            with patch.object(self.game.game_functions, 'main_menu_selection', side_effect=[0, 0]):
                self.game.copy_quest()
            # only one file should exist (no copy made to same slot)
            self.assertEqual(['save_slot_1.json'], os.listdir(tmp_dir))

    # this test fails in GitHub Actions

    # @mock.patch.object(menu_functions, "select_name", return_value="ed")
    # def test_show_main_menu_screen(self, mock_select_name):
    #     mocked_return = MagicMock()
    #     mocked_return.type = KEYDOWN
    #     mocked_return.key = K_RETURN
    #     with patch.object(event, 'get', return_value=[mocked_return]) as mock_method:
    #         self.game.show_main_menu_screen(self.game.screen)
    #     self.assertEqual(1, self.game.player.adventure_log)
    #     self.assertEqual('ed', self.game.player.name)
    #
    #     self.assertEqual(1, self.game.player.level)

    # self.assertEqual(1, self.game.player.strength)
    # self.assertEqual(1, self.game.player.agility)
    # self.assertEqual(15, self.game.player.max_hp)
    # self.assertEqual(0, self.game.player.max_mp)
