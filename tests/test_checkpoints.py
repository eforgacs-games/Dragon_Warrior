"""
Every playtest checkpoint in data/checkpoints/ loads through the real load path (Game.load_checkpoint, which uses
Game.load_game) into the state it promises, and the story can go on from there: each test takes the next story step
with the same stand-ins as the headless story run. If a checkpoint goes stale after a code change, these fail.
"""
import json
import os
from dataclasses import fields
from unittest.mock import patch

import pygame

import tests.test_story_run as story_run  # imported as a module so pytest doesn't collect TestStoryRun twice
from src.checkpoints import CHECKPOINT_HERO_NAME, CHECKPOINT_NAMES, CHECKPOINT_SAVE_DIR, CHECKPOINTS_DIR, \
    LOCALIZED_HERO_NAMES, checkpoint_hero_name, read_checkpoint
from src.config.test_config import test_config
from src.constants import ENDING_TRIGGER_COORDINATES, GWAELIN_SWAMP_CAVE_COORDINATES, \
    GWAELIN_THRONE_ROOM_COORDINATES, RAINBOW_BRIDGE_COORDINATES, RAINBOW_DROP_COORDINATES, RETURN_DESTINATION
from src.debug_tools import ADD_GOLD, EQUIP_ERDRICK, REFILL, DebugTools
from src.ending import CREDITS
from src.items import INVENTORY_SLOTS, UNSLOTTED_ITEMS, armor, shields, weapons
from src.maps import CharlockB1
from src.player.player_stats import get_total_name_score, levels_list
from src.story_flags import StoryFlags

UP, DOWN, LEFT, RIGHT = story_run.UP, story_run.DOWN, story_run.LEFT, story_run.RIGHT
KEY_ITEMS = ("Silver Harp", "Stones of Sunlight", "Staff of Rain", "Erdrick's Token", "Rainbow Drop", "Gwaelin's Love")

# What each checkpoint promises: map, (row, column), facing, the story flags that are set, and the key items carried.
EXPECTED = {
    'throne_room': ('TantegelThroneRoom', (10, 13), None, set(), set()),
    'garins_grave': ('Garinham', (1, 28), UP, {'left_throne_room'}, {'Stones of Sunlight'}),
    'swamp_cave': ('Alefgard', (56, 110), RIGHT, {'left_throne_room'}, {'Stones of Sunlight', 'Silver Harp'}),
    'rainbow_drop_shrine': ('MagicTemple', (7, 5), RIGHT,
                            {'left_throne_room', 'gwaelin_returned', 'green_dragon_defeated'},
                            {'Stones of Sunlight', 'Staff of Rain', "Erdrick's Token", "Gwaelin's Love"}),
    'rainbow_bridge': ('Alefgard', RAINBOW_DROP_COORDINATES, LEFT,
                       {'left_throne_room', 'gwaelin_returned', 'green_dragon_defeated'},
                       {'Rainbow Drop', "Erdrick's Token", "Gwaelin's Love"}),
    'charlock_throne': ('CharlockB1', CharlockB1.THRONE_COORDINATES, UP,
                        {'left_throne_room', 'gwaelin_returned', 'green_dragon_defeated', 'rainbow_bridge_built',
                         'golem_defeated'},
                        {'Rainbow Drop', "Erdrick's Token", "Gwaelin's Love"}),
    'dragonlord': ('CharlockB8', (28, 23), LEFT,
                   {'left_throne_room', 'gwaelin_returned', 'green_dragon_defeated', 'rainbow_bridge_built',
                    'golem_defeated', 'charlock_stairs_revealed'},
                   {'Rainbow Drop', "Erdrick's Token", "Gwaelin's Love"}),
    'ending_gwaelin_returned': ('Alefgard', RETURN_DESTINATION[1], RIGHT,
                                {'left_throne_room', 'gwaelin_returned', 'green_dragon_defeated',
                                 'rainbow_bridge_built', 'golem_defeated', 'charlock_stairs_revealed',
                                 'dragonlord_defeated'},
                                {'Rainbow Drop', "Erdrick's Token", "Gwaelin's Love"}),
    'ending_carrying_gwaelin': ('Alefgard', RETURN_DESTINATION[1], RIGHT,
                                {'left_throne_room', 'carrying_gwaelin', 'green_dragon_defeated',
                                 'rainbow_bridge_built', 'golem_defeated', 'charlock_stairs_revealed',
                                 'dragonlord_defeated'},
                                {'Rainbow Drop', "Erdrick's Token"}),
}


class TestCheckpoints(story_run.TestStoryRun):
    test_the_game_can_be_finished = None  # the whole run is in test_story_run.py

    def setUp(self):
        super().setUp()
        # load_checkpoint points saving away from src/saves; don't let that leak into other tests
        self.addCleanup(test_config.__setitem__, 'SAVE_DIR', test_config['SAVE_DIR'])

    def load(self, name):
        self.game.load_checkpoint(name)
        self.settle()  # what the first frame does

    def check(self, name):
        """Load the checkpoint and check it against EXPECTED and its own save file."""
        self.load(name)
        game, player = self.game, self.player
        map_name, coordinates, facing, flags, key_items = EXPECTED[name]
        save = read_checkpoint(name)
        self.assertEqual(self.where, (map_name, coordinates), name)
        if facing is not None:
            self.assertEqual(player.direction_value, facing, name)
        self.assertEqual({flag.name for flag in fields(StoryFlags) if getattr(game.story_flags, flag.name)}, flags,
                         name)
        self.assertEqual({item for item in player.inventory if item in KEY_ITEMS}, key_items, name)
        self.assertEqual(player.inventory, save['Inventory'], name)
        self.assertEqual(player.level, player.get_level_by_experience(), name)
        self.assertEqual(player.current_hp, player.max_hp, name)
        self.assertEqual(player.current_mp, player.max_mp, name)
        self.assertEqual(sorted(player.spells), sorted(str(levels_list[level]['spell']) for level in range(
            1, player.level + 1) if levels_list[level]['spell']), f"{name}: spells don't match the level")
        for slot, table in ((player.weapon, weapons), (player.armor, armor), (player.shield, shields)):
            self.assertTrue(slot == '' or slot in table, f"{name}: unknown equipment {slot!r}")
        slotted = [item for item in player.inventory if item not in UNSLOTTED_ITEMS]
        self.assertLessEqual(len(slotted), INVENTORY_SLOTS, name)
        self.assertNotIn(self.tile(coordinates), game.current_map.impassable_tiles, f"{name}: hero stands in a wall")
        self.assertEqual(game.config['SAVE_DIR'], CHECKPOINT_SAVE_DIR)
        return save

    # The set of checkpoints

    def test_every_checkpoint_file_is_listed_and_checked(self):
        files = sorted(file_name.removesuffix('.json') for file_name in os.listdir(CHECKPOINTS_DIR))
        self.assertEqual(files, sorted(CHECKPOINT_NAMES))
        self.assertEqual(set(EXPECTED), set(CHECKPOINT_NAMES))
        for name in CHECKPOINT_NAMES:
            with open(os.path.join(CHECKPOINTS_DIR, f'{name}.json')) as checkpoint_file:
                save = json.load(checkpoint_file)
            # Only save-file keys, plus Facing (src/checkpoints.py)
            self.assertLessEqual(set(save) - {'Facing'}, {
                'Name', 'Experience', 'Gold', 'CurrentHP', 'CurrentMP', 'Weapon', 'Armor', 'Shield',
                'WearingDragonScale', 'WearingFightersRing', 'WearingCursedBelt', 'WearingDeathNecklace', 'Inventory',
                'Spells', 'CurrentMap', 'PlayerRow', 'PlayerColumn', 'StoryFlags'}, name)
            self.assertEqual(set(save['StoryFlags']), {flag.name for flag in fields(StoryFlags)}, name)

    def test_every_checkpoint_names_the_hero_arthur(self):
        # Not Erdrick: that's the hero's ancestor (로토 in Korean)
        for name in CHECKPOINT_NAMES:
            self.assertEqual(read_checkpoint(name)['Name'], CHECKPOINT_HERO_NAME, name)
        self.assertEqual(CHECKPOINT_HERO_NAME, 'Arthur')

    def test_the_checkpoint_names_give_the_strongest_name_stats(self):
        # NES LoadStats: a first-four-tile sum ending in $D keeps full strength and HP and adds the +3 bonus
        self.assertEqual(get_total_name_score(CHECKPOINT_HERO_NAME) & 0x0F, 0x0D)
        # Korean names count each character as the low byte of its code point, padded to four with blank tiles ($60)
        korean_name = LOCALIZED_HERO_NAMES['Korean']
        korean_tiles = [ord(character) & 0xFF for character in korean_name[:4]] + [0x60] * (4 - len(korean_name))
        self.assertEqual(sum(korean_tiles) & 0x0F, 0x0D)

    def test_the_hero_is_named_arthur_in_english(self):
        with patch.dict(self.game.config, {'LANGUAGE': 'English'}):
            for name in CHECKPOINT_NAMES:
                with self.subTest(name):
                    self.game.load_checkpoint(name)
                    self.assertEqual(self.player.name, 'Arthur')

    def test_the_hero_is_named_geomgaek_in_korean(self):
        with patch.dict(self.game.config, {'LANGUAGE': 'Korean'}):
            for name in CHECKPOINT_NAMES:
                with self.subTest(name):
                    self.game.load_checkpoint(name)
                    self.assertEqual(self.player.name, '검객')

    def test_a_real_save_keeps_its_name_in_korean(self):
        # Only checkpoints are renamed: a name the player typed is never translated, even if it is "Arthur"
        for typed_name in ('Arthur', 'Erdrick', '용사'):
            with self.subTest(typed_name), patch.dict(self.game.config, {'LANGUAGE': 'Korean'}):
                self.game.load_game({**read_checkpoint('throne_room'), 'Name': typed_name})
                self.assertEqual(self.player.name, typed_name)

    def test_checkpoint_hero_name(self):
        self.assertEqual(checkpoint_hero_name('Arthur', 'English'), 'Arthur')
        self.assertEqual(checkpoint_hero_name('Arthur', 'Korean'), '검객')
        self.assertEqual(checkpoint_hero_name('Eddie', 'Korean'), 'Eddie')

    def test_saving_from_a_checkpoint_goes_to_the_checkpoint_save_folder(self):
        self.load('throne_room')
        self.assertEqual(self.cmd_menu.directories.save_dir, CHECKPOINT_SAVE_DIR)

    # Each checkpoint, then the next step of the story from it

    def test_throne_room(self):
        self.check('throne_room')
        self.assertEqual(self.player.inventory, [])
        self.take((10, 14))
        self.assertGreater(self.player.gold, 0)  # the chests are still there

    def test_garins_grave(self):
        self.check('garins_grave')
        self.take_stairs((0, 28))
        self.assertEqual(self.where, ('GarinsGraveB1', (12, 7)))

    def test_swamp_cave(self):
        self.check('swamp_cave')
        self.assertIn('Magic Key', self.player.inventory)  # for the door in front of Gwaelin
        self.walk_onto((56, 112))  # the south entrance, two steps east
        self.assertEqual(self.where, ('SwampCave', (35, 4)))
        self.assertIn('PRINCESS_GWAELIN', self.game.current_map.characters)
        self.assertEqual(self.game.current_map.characters['PRINCESS_GWAELIN']['coordinates'],
                         GWAELIN_SWAMP_CAVE_COORDINATES)

    def test_rainbow_drop_shrine(self):
        self.check('rainbow_drop_shrine')
        self.settle(RIGHT)
        self.cmd_menu.talk()
        self.assertIn('Rainbow Drop', self.player.inventory)
        self.assertNotIn('Staff of Rain', self.player.inventory)

    def test_rainbow_bridge(self):
        self.check('rainbow_bridge')
        self.assertEqual(self.tile(RAINBOW_BRIDGE_COORDINATES), 'WATER')
        self.cmd_menu.rainbow_drop()
        self.assertEqual(self.tile(RAINBOW_BRIDGE_COORDINATES), 'BRIDGE')

    def test_charlock_throne(self):
        self.check('charlock_throne')
        self.cmd_menu.search()
        self.assertIn("Feel the wind blowing from behind the throne.", self.shown_text)
        self.search(CharlockB1.HIDDEN_STAIRCASE_COORDINATES)
        self.assertEqual(self.tile(CharlockB1.HIDDEN_STAIRCASE_COORDINATES), 'BRICK_STAIR_DOWN')

    def test_dragonlord(self):
        self.check('dragonlord')
        self.assertEqual((self.player.weapon, self.player.armor), ("Erdrick's Sword", "Erdrick's Armor"))
        self.settle(LEFT)
        self.cmd_menu.talk()
        self.assertIn("Thou art a fool!", self.shown_text)
        self.assertEqual(self.game.battle_ctrl.pending_scripted_battle, 'Dragonlord')

    def roll_ending(self):
        self.walk_onto((50, 51))
        self.assertEqual(self.where, ('TantegelCourtyard', (36, 18)))
        self.stand_at(ENDING_TRIGGER_COORDINATES[0], UP)
        credit_screens: list = []
        with patch.object(self.game.ending, 'show_credit_screen', side_effect=credit_screens.append), \
                patch('src.ending.fade'), \
                patch('src.ending.event.get', return_value=[pygame.event.Event(pygame.QUIT)]), \
                patch('src.ending.pygame_quit'), \
                self.assertRaises(SystemExit):
            self.game.ending.check_for_end_game_trigger()
        self.assertEqual(credit_screens, list(CREDITS))
        self.assertTrue(self.game.story_flags.carrying_gwaelin)

    def test_ending_gwaelin_returned(self):
        self.check('ending_gwaelin_returned')
        self.travel_to('TantegelThroneRoom', (10, 13))
        self.assertEqual(self.game.current_map.characters['PRINCESS_GWAELIN']['coordinates'],
                         GWAELIN_THRONE_ROOM_COORDINATES)
        self.travel_to('Alefgard', RETURN_DESTINATION[1])
        self.roll_ending()
        self.assertIn("Please, wait.", ''.join(self.shown_text))

    def test_ending_carrying_gwaelin(self):
        self.check('ending_carrying_gwaelin')
        self.roll_ending()
        self.assertIn("May I travel as thy companion?", self.prompts)


class TestDebugTools(story_run.TestStoryRun):
    """The F5-F7 debug keys (dev config only)."""
    test_the_game_can_be_finished = None

    def setUp(self):
        super().setUp()
        self.addCleanup(test_config.__setitem__, 'SAVE_DIR', test_config['SAVE_DIR'])
        self.tools = DebugTools(self.game)

    def test_off_without_the_dev_config(self):
        self.assertIsNone(self.game.debug_tools)  # test_config, like prod_config, has DEBUG_KEYS off
        with patch.object(DebugTools, 'pick') as pick:
            self.game.handle_keypresses(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F5, unicode=''))
        pick.assert_not_called()

    def test_every_map_can_be_warped_to(self):
        for map_name in self.tools.warp_maps:
            with self.subTest(map_name):
                self.tools.warp(map_name)
                self.settle()
                self.assertEqual(self.where, (map_name, self.tools.entrance(map_name)))
                self.assertNotIn(self.player.current_tile, self.game.current_map.impassable_tiles)
                self.assertNotEqual(self.player.current_tile, 'WALL')

    def test_warp_lands_at_the_overworld_entrance(self):
        self.assertEqual(self.tools.entrance('Garinham'), (14, 9))
        self.assertEqual(self.tools.entrance('Rimuldar'), (22, 37))
        self.assertEqual(self.tools.entrance('Alefgard'), RETURN_DESTINATION[1])

    def test_give(self):
        player = self.player
        player.current_hp = 1
        self.tools.give(REFILL)
        self.assertEqual(player.current_hp, player.max_hp)
        gold = player.gold
        self.tools.give(ADD_GOLD)
        self.assertEqual(player.gold, gold + 1000)
        self.tools.give("Give Rainbow Drop")
        self.tools.give("Give Rainbow Drop")
        self.assertEqual(player.inventory.count('Rainbow Drop'), 1)
        for _ in range(8):
            self.tools.give("Give Magic Key")
        self.assertEqual(player.inventory.count('Magic Key'), 6)
        self.tools.give(EQUIP_ERDRICK)
        self.assertEqual(player.weapon, "Erdrick's Sword")
        self.tools.set_level(20)
        self.assertEqual((player.level, player.get_level_by_experience()), (20, 20))
        self.assertIn('HURTMORE', player.spells)

    def test_pick_filters_by_typing(self):
        keys = [pygame.event.Event(pygame.KEYDOWN, key=0, unicode=letter) for letter in 'char']
        keys += [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN, unicode=''),
                 pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode='\r')]
        with patch('src.debug_tools.event.get', side_effect=[keys]), patch('src.debug_tools.display.flip'):
            self.assertEqual(self.tools.pick("Warp to", self.tools.warp_maps), 'CharlockB2')
        with patch('src.debug_tools.event.get',
                   side_effect=[[pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode='\x1b')]]), \
                patch('src.debug_tools.display.flip'):
            self.assertIsNone(self.tools.pick("Warp to", self.tools.warp_maps))

    def test_checkpoint_menu_loads_the_checkpoint(self):
        with patch.object(DebugTools, 'pick', return_value='dragonlord'):
            self.tools.checkpoint_menu()
        self.assertEqual(self.game.current_map.identifier, 'CharlockB8')
