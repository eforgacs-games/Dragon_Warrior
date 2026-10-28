import json
import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

import pygame

from src.config.test_config import test_config
from src.constants import GWAELIN_SWAMP_CAVE_COORDINATES, GWAELIN_THRONE_ROOM_COORDINATES, \
    THRONE_ROOM_DOOR_COORDINATES
from src.game import Game
from src.items import treasure
from src.map_layouts import BRICK, DOOR, TREASURE_BOX
from src.maps import map_lookup
from src.story_flags import StoryFlags, story_bits
from tests.helpers import new_game

FLAG_NAMES = list(story_bits())
THRONE_ROOM_CHESTS = list(treasure['TantegelThroneRoom'])


class TestSaveStoryProgress(TestCase):
    """CommandMenu.save and Game.load_game, per NES SaveData/LoadSavedData and the continue routines (Bank03)."""

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
        self.game = new_game()
        self.game.player.name = "Erdrick"

    def save(self, game: Game | None = None) -> dict:
        game = game or self.game
        with tempfile.TemporaryDirectory() as tmp_dir:
            game.cmd_menu.directories.save_dir = tmp_dir
            game.player.adventure_log = 1
            game.cmd_menu.save()
            with open(os.path.join(tmp_dir, 'save_slot_1.json')) as save_file:
                return json.load(save_file)

    @staticmethod
    def load(save: dict) -> Game:
        loaded_game = new_game()
        loaded_game.load_game(save)
        return loaded_game

    def go_to(self, map_name, coordinates):
        self.game.change_map(map_lookup[map_name](self.game.config), destination_coordinates=coordinates)

    def throne_room_chest_tiles(self, game: Game):
        return [game.current_map.layout[row][column] for row, column in THRONE_ROOM_CHESTS]

    # Round trips

    def test_every_story_flag_round_trips(self):
        for name in FLAG_NAMES:
            setattr(self.game.story_flags, name, True)
        save = self.save()
        self.assertEqual(save['StoryFlags'], {**{name: True for name in FLAG_NAMES}, 'heard_goals': {}})
        self.assertNotIn('RainbowBridgeBuilt', save)
        self.assertNotIn('CharlockStairsRevealed', save)
        self.assertEqual(self.load(save).story_flags, StoryFlags(**{name: True for name in FLAG_NAMES}))

    def test_each_story_flag_round_trips_alone(self):
        # Saved in the throne room, where loading leaves F_LEFT_THROOM as it was
        for name in FLAG_NAMES:
            with self.subTest(flag=name):
                self.game.story_flags = StoryFlags(**{name: True})
                self.assertEqual(self.load(self.save()).story_flags, StoryFlags(**{name: True}))

    def test_cleared_flags_round_trip(self):
        self.assertEqual(self.load(self.save()).story_flags, StoryFlags())

    def test_worn_items_round_trip(self):
        # NES ModsnSpells bits 4-7 are saved with the rest of the byte
        player = self.game.player
        player.inventory = ["Dragon's Scale", "Fighter's Ring", "Cursed Belt", "Death Necklace"]
        player.wearing_dragon_scale = player.wearing_fighters_ring = True
        player.wearing_cursed_belt = player.wearing_death_necklace = True
        loaded = self.load(self.save()).player
        self.assertTrue(loaded.wearing_dragon_scale)
        self.assertTrue(loaded.wearing_fighters_ring)
        self.assertTrue(loaded.wearing_cursed_belt)
        self.assertTrue(loaded.wearing_death_necklace)
        self.assertTrue(loaded.is_wearing_cursed_item("Cursed Belt"))

    def test_empty_inventory_slots_round_trip(self):
        # NES SaveData keeps the inventory bytes as they are, emptied slots included
        player = self.game.player
        player.inventory = ['Torch', 'Wings', 'Herb', 'Fairy Water']
        player.inventory.remove('Wings')
        save = self.save()
        self.assertEqual(save['Inventory'], ['Torch', None, 'Herb', 'Fairy Water'])
        loaded = self.load(save).player
        self.assertEqual(loaded.inventory, ['Torch', 'Herb', 'Fairy Water'])
        loaded.inventory.append('Silver Harp')
        self.assertEqual(loaded.inventory, ['Torch', 'Silver Harp', 'Herb', 'Fairy Water'])

    # What the NES doesn't save

    def test_chest_history_and_repel_timer_are_not_saved(self):
        self.go_to('GarinsGraveB1', (1, 11))
        self.game.chest_history.record('GarinsGraveB1', (1, 12))
        self.game.repel_timer = 200
        save = self.save()
        self.assertFalse({'ChestHistory', 'RepelTimer'} & set(save))
        loaded_game = self.load(save)
        self.assertFalse(loaded_game.chest_history.is_opened('GarinsGraveB1', (1, 12)))
        self.assertEqual(loaded_game.repel_timer, 0)

    def test_loading_clears_the_chest_history_and_repel_timer(self):
        # NES MainGameEngine clears TrsrXPos, StartAtThroneRoom clears RepelTimer
        save = self.save()
        self.game.chest_history.record('GarinsGraveB1', (1, 12))
        self.game.repel_timer = 200
        self.game.load_game(save)
        self.assertFalse(self.game.chest_history.is_opened('GarinsGraveB1', (1, 12)))
        self.assertEqual(self.game.repel_timer, 0)

    # NES continue behavior

    def test_throne_room_chests_are_gone_on_continue_after_leaving(self):
        # NES InitMapData: with F_LEFT_THROOM set, the throne room chests are read as taken
        self.game.story_flags.left_throne_room = True
        loaded_game = self.load(self.save())
        self.assertEqual(loaded_game.current_map.identifier, 'TantegelThroneRoom')
        self.assertEqual(self.throne_room_chest_tiles(loaded_game), [BRICK] * 3)

    def test_throne_room_chests_stay_before_leaving(self):
        loaded_game = self.load(self.save())
        self.assertEqual(self.throne_room_chest_tiles(loaded_game), [TREASURE_BOX] * 3)

    def test_throne_room_door_is_open_on_continue_after_leaving(self):
        # NES InitMapData (ChkLeftThRoom): F_LEFT_THROOM removes the throne room door with its chests, so a continued
        # game doesn't start behind a locked door with no key
        self.game.story_flags.left_throne_room = True
        loaded_game = self.load(self.save())
        row, column = THRONE_ROOM_DOOR_COORDINATES
        self.assertEqual(loaded_game.current_map.layout[row][column], BRICK)

    def test_throne_room_door_stays_before_leaving(self):
        loaded_game = self.load(self.save())
        row, column = THRONE_ROOM_DOOR_COORDINATES
        self.assertEqual(loaded_game.current_map.layout[row][column], DOOR)

    def test_cursed_hero_continues_with_1_hp(self):
        # NES StartAtThroneRoom (LCB6B): ModsnSpells AND IS_CURSED sets HitPoints to 1; MP is left alone
        for curse in ('wearing_cursed_belt', 'wearing_death_necklace'):
            with self.subTest(curse=curse):
                self.game.player.wearing_cursed_belt = self.game.player.wearing_death_necklace = False
                setattr(self.game.player, curse, True)
                self.game.player.current_hp, self.game.player.current_mp = 12, 3
                loaded = self.load(self.save()).player
                self.assertEqual(loaded.current_hp, 1)
                self.assertEqual(loaded.current_mp, 3)

    def test_uncursed_hero_continues_with_saved_hp(self):
        # The start status saved with the game is always "don't restore" by the time King Lorik can save it
        self.game.player.current_hp, self.game.player.current_mp = 12, 3
        loaded = self.load(self.save()).player
        self.assertEqual((loaded.current_hp, loaded.current_mp), (12, 3))

    def test_dying_also_clears_the_repel_timer(self):
        # NES DeathText goes through the same StartAtThroneRoom as a continue
        self.game.repel_timer = 200
        self.game.player.is_dead = True
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box'):
            self.game.set_post_death_attributes()
        self.assertEqual(self.game.repel_timer, 0)

    def test_dying_refills_hp_and_mp(self):
        # NES DeathText: ThisStrtStat = STRT_FULL_HP, so StartAtThroneRoom (LCB78-LCB87) sets both HitPoints and
        # MagicPoints to their maximums
        player = self.game.player
        player.max_hp, player.max_mp = 30, 20
        player.current_hp, player.current_mp = 0, 4
        player.is_dead = True
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box'):
            self.game.set_post_death_attributes()
        self.assertEqual((player.current_hp, player.current_mp), (30, 20))

    def test_dying_cursed_leaves_mp_alone(self):
        # NES StartAtThroneRoom (LCB6B-LCB75): a cursed hero gets HitPoints = 1 and skips the MP step
        player = self.game.player
        player.wearing_cursed_belt = True
        player.max_hp, player.max_mp = 30, 20
        player.current_hp, player.current_mp = 0, 4
        player.is_dead = True
        with patch('src.menu.CommandMenu.show_text_in_dialog_box'), patch.object(self.game, 'leave_tantegel'):
            self.game.set_post_death_attributes()
        self.assertEqual((player.current_hp, player.current_mp), (1, 4))

    def test_continue_while_carrying_gwaelin(self):
        # The NES saves PlayerFlags whole, so F_GOT_GWAELIN comes back: she's still in the hero's arms, gone from the
        # Swamp Cave, and King Lorik's first words are his thanks for her return.
        self.game.story_flags.carrying_gwaelin = True
        loaded_game = self.load(self.save())
        self.assertTrue(loaded_game.story_flags.carrying_gwaelin)
        self.assertTrue(loaded_game.story_flags.gwaelin_rescued)
        loaded_game.cmd_menu.set_king_lorik_dialog(left_throne_room=True)
        king_lorik = loaded_game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']
        self.assertEqual(king_lorik['dialog'], king_lorik['carrying_princess_dialog'])
        loaded_game.change_map(map_lookup['SwampCave'](loaded_game.config), destination_coordinates=(6, 4))
        self.assertNotIn(GWAELIN_SWAMP_CAVE_COORDINATES, loaded_game.current_map.npc_coordinates)

    def test_continue_after_returning_gwaelin(self):
        self.game.story_flags.gwaelin_returned = True
        loaded_game = self.load(self.save())
        self.assertEqual(loaded_game.current_map.identifier, 'TantegelThroneRoom')
        self.assertEqual(loaded_game.current_map.npc_coordinates.get(GWAELIN_THRONE_ROOM_COORDINATES),
                         'PRINCESS_GWAELIN')
        self.assertIn('PRINCESS_GWAELIN', loaded_game.current_map.characters)

    def test_king_greets_a_returning_hero(self):
        # NES MainGameEngine (LCA1D): F_LEFT_THROOM picks "I am glad thou hast returned" over the opening speech
        king_lorik = self.game.cmd_menu.dialog_lookup.lookup_table['TantegelThroneRoom']['KING_LORIK']
        for left_throne_room, expected in ((False, king_lorik['dialog']), (True, king_lorik['load_from_save_dialog'])):
            with self.subTest(left_throne_room=left_throne_room):
                self.game.story_flags.left_throne_room = left_throne_room
                self.game.game_state.automatic_initial_dialog_run = False
                with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text:
                    self.game.drawer.run_automatic_initial_dialog([], True, self.game.cmd_menu)
                self.assertEqual(show_text.call_args.args[0], expected)

    # Old saves

    def test_old_save_without_any_flags(self):
        save = {"Name": "Erdrick", "Experience": 0, "Gold": 0, "Inventory": [],
                "CurrentMap": "TantegelThroneRoom", "PlayerRow": 10, "PlayerColumn": 13}
        loaded_game = self.load(save)
        # Old saves could only be made with King Lorik after leaving the throne room
        self.assertEqual(loaded_game.story_flags, StoryFlags(left_throne_room=True))
        self.assertFalse(loaded_game.player.wearing_cursed_belt)
        self.assertFalse(loaded_game.player.wearing_death_necklace)
        self.assertEqual(self.throne_room_chest_tiles(loaded_game), [BRICK] * 3)

    def test_old_save_with_flat_keys(self):
        save = {"Name": "Erdrick", "Experience": 0, "Gold": 0, "Inventory": [],
                "RainbowBridgeBuilt": True, "CharlockStairsRevealed": True}
        flags = self.load(save).story_flags
        self.assertEqual(flags, StoryFlags(rainbow_bridge_built=True, charlock_stairs_revealed=True,
                                           left_throne_room=True))

    def test_old_save_works_out_flags_from_the_inventory(self):
        save = {"Name": "Erdrick", "Experience": 0, "Gold": 0, "Inventory": ["Gwaelin's Love", "Death Necklace"]}
        flags = self.load(save).story_flags
        self.assertTrue(flags.gwaelin_returned)
        self.assertTrue(flags.death_necklace_found)
        self.assertFalse(flags.carrying_gwaelin)

    def test_new_save_flags_win_over_flat_keys_and_inventory(self):
        save = {"Name": "Erdrick", "Experience": 0, "Gold": 0, "Inventory": ["Gwaelin's Love"],
                "RainbowBridgeBuilt": True, "StoryFlags": {"rainbow_bridge_built": False, "unknown_flag": True}}
        self.assertEqual(StoryFlags.from_save(save), StoryFlags())

    # Bad ending

    def test_bad_ending_clears_every_flag(self):
        # NES ZeroStats zeroes ModsnSpells, PlayerFlags and StoryFlags
        for name in FLAG_NAMES:
            setattr(self.game.story_flags, name, True)
        self.game.player.wearing_cursed_belt = self.game.player.wearing_dragon_scale = True
        self.game.cmd_menu.dialog_lookup.zero_stats_for_bad_ending()
        self.assertEqual(self.game.story_flags, StoryFlags())
        self.assertFalse(self.game.player.is_cursed)
        self.assertFalse(self.game.player.wearing_dragon_scale)
