"""How many times the menu button sound (SFX_MENU_BTN) plays for SPELL and ITEM, in the field and in a fight.

NES WndAPressed (Bank01, LA9B7) plays it once each time an entry of a selection window is chosen, and nothing else
in these sequences plays it (Bank03 PlyrSpell, ChkPlyrItem and NCCmdSelected don't): choosing SPELL or ITEM in the
COMMAND window (or the battle command window) is one, and choosing a spell or an item from its window is another.
"""
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import KEYDOWN, K_RETURN
from pygame.event import Event

from src.battle import Battle
from src.battle_controller import BATTLE_MENU_OPTIONS
from src.config.test_config import test_config
from src.cursor import IN_A
from src.sound import Sound
from src.spells import Spell
from tests.helpers import new_game


def accept() -> Event:
    return Event(KEYDOWN, key=K_RETURN, mod=0, unicode='\r')


class TestMenuSoundCount(TestCase):

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
        self.game = new_game()
        self.game.game_state.is_initial_dialog = False
        self.cmd_menu = self.game.cmd_menu
        self.player = self.game.player
        self.player.spells = [Spell.HEAL]
        self.player.current_mp = self.player.max_mp = 10
        self.player.inventory = ['Torch']
        self.addCleanup(patch.stopall)
        # Every Sound (the menu's, the battle's, the battle controller's) is counted
        self.played = patch.object(Sound, 'play_sound', autospec=True).start()
        for stub in ('show_line_in_dialog_box', 'show_text_in_dialog_box', 'show_popup_window', 'heal', 'torch',
                     'use_item_in_battle', 'window_drop_down_effect', 'window_drop_up_effect'):
            patch.object(self.cmd_menu, stub).start()
        # The spell or item window: A chooses the first entry
        patch('src.selection.event.get', return_value=[accept()]).start()

    def menu_sounds(self) -> int:
        menu_sound = self.cmd_menu.directories.menu_button_sfx
        return sum(1 for c in self.played.call_args_list if c.args[1] == menu_sound)

    def choose_in_battle(self, command: str) -> None:
        """Choose a command in the battle command window (WndAPressed), then run it as handle_battle_prompts does."""
        controller = self.game.battle_ctrl
        battle = Battle(self.game.config, 'Slime', self.game.current_map)
        self.cmd_menu.current_battle = battle
        self.addCleanup(setattr, self.cmd_menu, 'current_battle', None)
        controller.battle_menu_row, controller.battle_menu_column = next(
            (row, column) for row, options in enumerate(BATTLE_MENU_OPTIONS)
            for column, option in enumerate(options) if option == command)
        self.assertEqual(command, controller.process_command_input(IN_A))
        if command == 'Spell':
            battle.battle_spell(self.cmd_menu, self.player, battle)
        else:
            self.cmd_menu.display_item_menu('inventory')

    def test_battle_spell_then_a_spell(self):
        self.choose_in_battle('Spell')
        self.cmd_menu.heal.assert_called_once()
        self.assertEqual(2, self.menu_sounds())

    def test_battle_item_then_an_item(self):
        self.choose_in_battle('Item')
        self.cmd_menu.use_item_in_battle.assert_called_once_with('Torch')
        self.assertEqual(2, self.menu_sounds())

    def test_field_spell_then_a_spell(self):
        self.cmd_menu.choose_command(self.cmd_menu.spell)
        self.cmd_menu.heal.assert_called_once()
        self.assertEqual(2, self.menu_sounds())

    def test_field_item_then_an_item(self):
        self.cmd_menu.choose_command(self.cmd_menu.item)
        self.cmd_menu.torch.assert_called_once()
        self.assertEqual(2, self.menu_sounds())
