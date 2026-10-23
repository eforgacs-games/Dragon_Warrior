from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame

from src.config.test_config import test_config
from src.game import Game
from src.items import armor, hidden_items
from src.map_layouts import MapLayouts
from tests.mock_map import MockMap


class TestHiddenItems(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()
        cls.screen = pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self) -> None:
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.game.current_map = MockMap(self.game.config)
        self.game.current_map.load_map(self.game.player, (0, 0), self.game.game_state.config["TILE_SIZE"])
        self.cmd_menu = self.game.cmd_menu
        self.player = self.game.player

    def search_at(self, map_identifier, row, column):
        """Search on the given tile and return the lines shown."""
        self.cmd_menu.current_map = MagicMock(identifier=map_identifier)
        self.player.row, self.player.column = row, column
        self.player.current_tile = 'GRASS'
        with patch.object(self.cmd_menu, 'show_text_in_dialog_box') as show_text:
            self.cmd_menu.search()
        return show_text.call_args.args[0]

    def test_nothing_found_elsewhere(self):
        self.assertEqual(self.search_at('Kol', 14, 20),
                         [f"{self.player.name} searched the ground all about.", "But there found nothing."])

    def test_treasure_box_is_reported(self):
        self.cmd_menu.current_map = MagicMock(identifier='Kol')
        self.player.current_tile = 'TREASURE_BOX'
        with patch.object(self.cmd_menu, 'show_text_in_dialog_box') as show_text:
            self.cmd_menu.search()
        self.assertEqual(show_text.call_args.args[0][1], "There is a treasure box.")

    def test_erdricks_token_found_once(self):
        # NES overworld (83, 113), i.e. 40 east and 70 south of Tantegel
        self.assertEqual(self.cmd_menu.calculation.get_distance_from_tantegel(91, 120), (40, 70))
        self.assertEqual(self.search_at('Alefgard', 120, 91)[1],
                         f"{self.player.name} discovers the Erdrick's Token.")
        self.assertEqual(self.player.inventory, ["Erdrick's Token"])
        self.assertEqual(self.search_at('Alefgard', 120, 91)[1], "But there found nothing.")
        self.assertEqual(self.player.inventory, ["Erdrick's Token"])

    def test_fairy_flute_found_once(self):
        self.assertEqual(self.search_at('Kol', 14, 19)[1], f"{self.player.name} discovers the Fairy Flute.")
        self.assertEqual(self.player.inventory, ['Fairy Flute'])
        self.assertEqual(self.search_at('Kol', 14, 19)[1], "But there found nothing.")
        self.assertEqual(self.player.inventory, ['Fairy Flute'])

    def test_erdricks_armor_is_equipped_not_carried(self):
        self.player.armor = 'Full Plate'
        self.player.update_defense_power()
        defense_before = self.player.defense_power
        self.assertEqual(self.search_at('Hauksness', 20, 27)[1],
                         f"{self.player.name} discovers the Erdrick's Armor.")
        self.assertEqual(self.player.armor, "Erdrick's Armor")
        self.assertNotIn("Erdrick's Armor", self.player.inventory)
        self.assertEqual(self.player.defense_power,
                         defense_before - armor['Full Plate']['defense'] + armor["Erdrick's Armor"]['defense'])
        self.assertEqual(self.search_at('Hauksness', 20, 27)[1], "But there found nothing.")

    def test_hidden_items_are_inside_their_maps(self):
        # Kol and Hauksness are padded: NES (X, Y) is (row Y + 8, column X + 10) in Kol and (Y + 8, X + 9) in
        # Hauksness. The flute spot is a tree in the NES KolDat (row 6, X 9 = $8).
        layouts = MapLayouts().map_layout_lookup
        self.assertEqual(layouts['Kol'][14][19], 14)  # TREES
        self.assertEqual(layouts['Kol'][9][11], 3)  # BRICK under the wizard the NES places at Kol (1, 1)
        self.assertEqual(layouts['Hauksness'][20][28], 1)  # WALL: stone at NES Hauksness (19, 12), next to the armor
        for map_name, items in hidden_items.items():
            for row, column in items:
                self.assertLess(row, len(layouts[map_name]))
                self.assertLess(column, len(layouts[map_name][0]))

    def test_fairy_flute_in_item_menu(self):
        self.player.inventory = ['Fairy Flute']
        with patch.object(self.cmd_menu, 'fairy_flute') as fairy_flute, \
                patch.object(pygame.event, 'get',
                             return_value=[MagicMock(type=pygame.KEYDOWN, key=pygame.K_RETURN)]):
            self.cmd_menu.display_item_menu('inventory')
        fairy_flute.assert_called_once()

    def play_flute(self):
        with patch('src.music_player.mixer'), \
                patch.object(self.cmd_menu, 'show_line_in_dialog_box') as show_line, \
                patch.object(self.cmd_menu, 'show_text_in_dialog_box') as show_text:
            self.cmd_menu.fairy_flute()
        return [c.args[0] for c in show_line.call_args_list + show_text.call_args_list]

    def test_fairy_flute_outside_battle(self):
        self.assertEqual(self.play_flute(),
                         [f"{self.player.name} blew the Fairies' Flute.", "But nothing happened."])

    def test_fairy_flute_puts_golem_to_sleep(self):
        from src.enemy import Golem
        golem = Golem()
        battle = MagicMock(no_op=False)
        battle.enemy = golem
        self.cmd_menu.current_battle = battle
        self.assertEqual(self.play_flute(), [f"{self.player.name} blew the Fairies' Flute.",
                                             "Quietly Golem closes his eyes and settles into sleep.",
                                             "The Golem is asleep."])
        self.assertTrue(golem.is_asleep)
        self.assertTrue(battle.no_op)

    def test_fairy_flute_does_nothing_to_other_enemies(self):
        from src.enemy import Slime
        slime = Slime()
        battle = MagicMock(no_op=False)
        battle.enemy = slime
        self.cmd_menu.current_battle = battle
        self.assertEqual(self.play_flute(),
                         [f"{self.player.name} blew the Fairies' Flute.", "But nothing happened."])
        self.assertFalse(slime.is_asleep)
        self.assertFalse(battle.no_op)
