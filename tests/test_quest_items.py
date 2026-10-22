import os
from collections import deque
from unittest import TestCase
from unittest.mock import patch

import pygame

from src.config.test_config import test_config
from src.constants import SILVER_HARP_ENEMIES
from src.enemy_lookup import enemy_string_lookup
from src.game import Game
from src.items import treasure
from src.maps import map_lookup

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

NO_BUSINESS = "Thou hast no business here.\nGo away."


class TestQuestItems(TestCase):
    """The Silver Harp -> Staff of Rain, Stones of Sunlight -> Rainbow Drop chain (NES Bank03 RainStaffDialog,
    WzdGuardDialog, RnbwDrpDialog, ChkHarp, ChkStaff, ChkStones)."""

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
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.game.player.name = "Edward"

    def go_to(self, map_name, coordinates=None):
        self.game.change_map(map_lookup[map_name](self.game.config), destination_coordinates=coordinates)
        if coordinates:
            self.game.player.row, self.game.player.column = coordinates

    def talk_to(self, character):
        """Run the NPC's dialog the way CommandMenu.launch_dialog does and return the lines shown."""
        lines = []

        def show_line(line, *args, **kwargs):
            if callable(line):
                line()
            else:
                lines.append(line)

        with patch('src.menu.CommandMenu.show_line_in_dialog_box', side_effect=show_line), \
                patch('src.menu.CommandMenu.window_drop_down_effect'), \
                patch('src.menu.CommandMenu.window_drop_up_effect'):
            self.game.cmd_menu.launch_dialog(character, self.game.current_map)
        return lines

    def use_item(self, item_function):
        with patch('src.menu.CommandMenu.show_text_in_dialog_box') as show_text, patch('src.music_player.mixer'), \
                patch.object(self.game.battle_ctrl, 'queue_scripted_battle') as start_battle:
            item_function()
        return [c.args[0] for c in show_text.call_args_list], start_battle

    def reachable(self, start, target):
        """Flood fill over passable tiles, treating fixed NPCs and other staircases as walls."""
        current_map = self.game.current_map
        npcs = {(c.row, c.column) for c in current_map.fixed_characters}
        seen, queue = {start}, deque([start])
        while queue:
            row, column = queue.popleft()
            if (row, column) == target:
                return True
            for next_row, next_column in ((row - 1, column), (row + 1, column), (row, column - 1), (row, column + 1)):
                if not (0 <= next_row < len(current_map.layout) and 0 <= next_column < len(current_map.layout[0])):
                    continue
                tile = current_map.get_tile_by_value(current_map.layout[next_row][next_column])
                blocked = tile in current_map.impassable_tiles or (next_row, next_column) in npcs or (
                    (next_row, next_column) in current_map.staircases and (next_row, next_column) != target)
                if not blocked and (next_row, next_column) not in seen:
                    seen.add((next_row, next_column))
                    queue.append((next_row, next_column))
        return False

    # Silver Harp

    def test_silver_harp_summons_a_monster_on_the_overworld(self):
        self.game.player.inventory = ['Silver Harp']
        self.go_to('Alefgard', (50, 50))
        self.game.repel_timer = 200  # InitFight is called directly, so repel doesn't apply
        lines, start_battle = self.use_item(self.game.cmd_menu.silver_harp)
        self.assertEqual(lines, ["Edward played a sweet melody on the harp."])
        start_battle.assert_called_once()
        self.assertIn(start_battle.call_args.args[0], SILVER_HARP_ENEMIES)
        self.assertEqual(self.game.player.inventory, ['Silver Harp'])

    def test_silver_harp_enemies_match_nes(self):
        # NES HarpRNGLoop: enemy #0-4 or #6
        self.assertEqual(SILVER_HARP_ENEMIES, ('Slime', 'Red Slime', 'Drakee', 'Ghost', 'Magician', 'Scorpion'))
        for enemy in SILVER_HARP_ENEMIES:
            self.assertIn(enemy, enemy_string_lookup)

    def test_silver_harp_does_nothing_off_the_overworld(self):
        self.game.player.inventory = ['Silver Harp']
        for map_name, coordinates in (('Brecconary', (7, 23)), ('GarinsGraveB3', (7, 14))):
            with self.subTest(map=map_name):
                self.go_to(map_name, coordinates)
                lines, start_battle = self.use_item(self.game.cmd_menu.silver_harp)
                self.assertEqual(lines, ["Edward played a sweet melody on the harp.", "But nothing happened."])
                start_battle.assert_not_called()
                self.assertEqual(self.game.player.inventory, ['Silver Harp'])

    def test_random_encounters_are_still_repelled(self):
        self.go_to('Alefgard', (50, 50))
        self.game.repel_timer = 200
        with patch.object(self.game.battle_ctrl, 'queue_scripted_battle') as start_battle, \
                patch.object(self.game.battle_ctrl, 'is_repelled', return_value=True):
            self.game.battle_ctrl.run_battle(['Slime'])
        start_battle.assert_not_called()

    # Staff of Rain and Stones of Sunlight

    def test_staff_and_stones_do_nothing_when_used(self):
        self.game.player.inventory = ['Staff of Rain', 'Stones of Sunlight']
        for function, item in ((self.game.cmd_menu.staff_of_rain, 'Staff of Rain'),
                               (self.game.cmd_menu.stones_of_sunlight, 'Stones of Sunlight')):
            with self.subTest(item=item):
                lines, _ = self.use_item(function)
                self.assertEqual(lines, [f"Edward held the {item} tightly.\nBut nothing happened."])
        self.assertEqual(self.game.player.inventory, ['Staff of Rain', 'Stones of Sunlight'])

    # Staff of Rain shrine

    def test_staff_of_rain_chest_matches_nes(self):
        # NES TreasureTbl: MAP_RAIN at 3,4 (this map is padded by 2 tiles)
        self.assertEqual(treasure['StaffOfRainCave'], {(6, 5): {'item': 'Staff of Rain'}})

    def test_staff_of_rain_guardian_without_the_harp(self):
        self.go_to('StaffOfRainCave', (6, 7))
        self.assertEqual(self.talk_to('WISE_MAN'), [
            "Thy bravery must be proven.",
            "Thus, I propose a test.",
            "There is a Silver Harp that beckons to the creatures of the Dragonlord.",
            "Bring this to me and I will reward thee with the Staff of Rain."])
        self.assertIn('WISE_MAN', self.game.current_map.characters)
        self.assertFalse(self.reachable((11, 6), (6, 5)))

    def test_staff_of_rain_guardian_takes_the_harp(self):
        self.game.player.inventory = ['Silver Harp', 'Herb']
        self.go_to('StaffOfRainCave', (6, 7))
        self.assertFalse(self.reachable((11, 6), (6, 5)))
        self.assertEqual(self.talk_to('WISE_MAN'), [
            "Thou hast brought the harp. Good.",
            "I have been waiting long for one such as thee.",
            "Take the Treasure Chest."])
        self.assertEqual(self.game.player.inventory, ['Herb'])
        self.assertNotIn('WISE_MAN', self.game.current_map.characters)
        self.assertEqual(self.game.current_map.fixed_characters, [])
        self.assertTrue(self.reachable((11, 6), (6, 5)))
        # He's back the next time the shrine is entered
        self.go_to('StaffOfRainCave', (6, 7))
        self.assertIn('WISE_MAN', self.game.current_map.characters)

    def test_staff_of_rain_guardian_with_staff_or_drop(self):
        for inventory in (['Silver Harp', 'Staff of Rain'], ['Silver Harp', 'Rainbow Drop']):
            with self.subTest(inventory=inventory):
                self.game.player.inventory = list(inventory)
                self.go_to('StaffOfRainCave', (6, 7))
                self.assertEqual(self.talk_to('WISE_MAN'), [NO_BUSINESS])
                self.assertEqual(self.game.player.inventory, inventory)
                self.assertIn('WISE_MAN', self.game.current_map.characters)

    # Stones of Sunlight

    def test_stones_of_sunlight_chest_matches_nes(self):
        # NES TreasureTbl: MAP_TANTCSTL_SL at 4,5 (this map is padded by 1 tile)
        self.assertEqual(treasure['TantegelCellar'], {(6, 5): {'item': 'Stones of Sunlight'}})

    def test_tantegel_cellar_needs_a_magic_key(self):
        # NES TantGFDat: the stairs down are in the south-east corner (29, 29), and the only way there is through the
        # door at (18, 6). Here that's the stairs at (36, 36) and the door at (13, 25).
        self.go_to('TantegelCourtyard', (14, 25))
        self.assertEqual(self.game.current_map.staircases[(36, 36)]['map'], 'TantegelCellar')
        self.assertFalse(self.reachable((14, 14), (36, 36)))
        self.game.player.inventory = ['Magic Key']
        self.game.player.next_tile_id = 'DOOR'
        self.game.player.next_coordinates = (13, 25)
        with patch('src.menu.CommandMenu.show_text_in_dialog_box'):
            self.game.cmd_menu.door()
        self.assertEqual(self.game.player.inventory, [])
        self.assertTrue(self.reachable((14, 14), (36, 36)))
        self.go_to('TantegelCellar', (4, 1))
        self.assertTrue(self.reachable((4, 1), (6, 5)))

    def test_tantegel_cellar_guardian(self):
        self.go_to('TantegelCellar', (4, 1))
        self.assertEqual(self.talk_to('WISE_MAN'),
                         ["I have been waiting long for one such as thee.", "Take the Treasure Chest."])
        for inventory in (['Stones of Sunlight'], ['Rainbow Drop']):
            with self.subTest(inventory=inventory):
                self.game.player.inventory = list(inventory)
                self.assertEqual(self.talk_to('WISE_MAN'), [NO_BUSINESS])

    # Rainbow Drop shrine

    def test_rainbow_drop_exchange(self):
        self.game.player.inventory = ["Erdrick's Token", 'Staff of Rain', 'Herb', 'Stones of Sunlight']
        self.go_to('MagicTemple', (6, 2))
        with patch('data.text.dialog_lookup_table.greyscale_screen') as greyscale:
            self.assertEqual(self.talk_to('WISE_MAN'),
                             ["Now the sun and rain shall meet and the Rainbow Drop passes to thy keeping."])
        greyscale.assert_called_once()
        self.assertEqual(greyscale.call_args.kwargs['frames'], 30)
        self.assertEqual(self.game.player.inventory, ['Rainbow Drop', "Erdrick's Token", 'Herb'])
        self.assertEqual(self.talk_to('WISE_MAN'), [NO_BUSINESS])

    def test_rainbow_drop_exchange_without_both_items(self):
        for inventory in (["Erdrick's Token"], ["Erdrick's Token", 'Staff of Rain'],
                          ["Erdrick's Token", 'Stones of Sunlight']):
            with self.subTest(inventory=inventory):
                self.game.player.inventory = list(inventory)
                self.go_to('MagicTemple', (6, 2))
                self.assertEqual(self.talk_to('WISE_MAN'), [
                    "When the sun and rain meet, a Rainbow Bridge shall appear.", "Thou may go and search."])
                self.assertEqual(self.game.player.inventory, inventory)
                self.assertEqual(self.game.current_map.identifier, 'MagicTemple')

    def test_rainbow_drop_exchange_needs_erdricks_token(self):
        self.game.player.inventory = ['Staff of Rain', 'Stones of Sunlight']
        self.go_to('MagicTemple', (6, 2))
        self.assertEqual(self.talk_to('WISE_MAN'), [
            "In thy task thou hast failed. Alas, I fear thou art not the one Erdrick predicted would save us.",
            "Go now!"])
        self.assertEqual(self.game.player.inventory, ['Staff of Rain', 'Stones of Sunlight'])
        self.assertEqual(self.game.current_map.identifier, 'Alefgard')
