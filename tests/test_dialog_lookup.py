from unittest import TestCase
from unittest.mock import patch

import pygame

from src.config.test_config import test_config
from src.game import Game


class TestDialogLookup(TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        with patch('src.game.SCALED'):
            self.dialog_lookup = Game(test_config).cmd_menu.dialog_lookup

    def test_inn_costs_match_nes(self):
        # NES InnCostTbl (Bank00): Kol 20, Brecconary 6, Garinham 25, Cantlin 100, Rimuldar 55
        expected = {'Brecconary': 6, 'Garinham': 25, 'Kol': 20, 'Rimuldar': 55, 'Cantlin': 100}
        found = {}
        for town, characters in self.dialog_lookup.lookup_table.items():
            for character in characters.values():
                dialog = character.get('dialog') if isinstance(character, dict) else None
                for entry in dialog if isinstance(dialog, tuple) else ():
                    if getattr(getattr(entry, 'func', None), '__name__', '') == 'check_stay_at_inn':
                        found.setdefault(town, set()).add(entry.args[0])
        self.assertEqual(found, {town: {cost} for town, cost in expected.items()})

    def test_mashing_accept_at_the_inn_stays_and_pays_once(self):
        # Issue #97: mashing the accept key restarted the stay and charged for it again
        from pygame import KEYDOWN, K_RETURN
        from pygame.event import Event
        player = self.dialog_lookup.player
        player.gold = 100
        mashed = [Event(KEYDOWN, key=K_RETURN, unicode='\r') for _ in range(3)]
        with patch('data.text.dialog.get', side_effect=[mashed]), \
                patch.object(self.dialog_lookup.command_menu, 'show_line_in_dialog_box'), \
                patch.object(self.dialog_lookup.command_menu, 'show_text_in_dialog_box'), \
                patch.object(self.dialog_lookup.command_menu, 'window_drop_down_effect'), \
                patch('data.text.dialog_lookup_table.fade'):
            self.dialog_lookup.check_stay_at_inn(6)
        self.assertEqual(player.gold, 94)
