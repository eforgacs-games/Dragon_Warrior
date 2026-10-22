import os
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame
from pygame import KEYDOWN, K_ESCAPE, K_RETURN

from src.color import RED, WHITE, is_low_hp, window_color
from src.config.test_config import test_config
from src.game import Game
from src.maps import map_lookup
from src.windows import SHOP_INVENTORY_WINDOW

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


class TestLowHPThreshold(TestCase):
    """NES ChkLowHPPal/ChkLowHP: HP is low when HP <= DisplayedMaxHP / 4 (rounded down) + 1."""

    def test_threshold(self):
        for max_hp, highest_low_hp in ((15, 4), (16, 5), (3, 1), (100, 26), (255, 64)):
            with self.subTest(max_hp=max_hp):
                self.assertTrue(is_low_hp(highest_low_hp, max_hp))
                self.assertFalse(is_low_hp(highest_low_hp + 1, max_hp))
                self.assertTrue(is_low_hp(0, max_hp))
                self.assertFalse(is_low_hp(max_hp, max_hp))

    def test_window_color(self):
        self.assertEqual(window_color(4, 15), RED)
        self.assertEqual(window_color(5, 15), WHITE)


class TestLowHPWindowColor(TestCase):

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
            self.game = Game(test_config)
        self.player = self.game.player
        self.player.name = "Edward"
        self.player.max_hp = 15
        self.player.current_hp = 15
        self.game.load_window_palette()
        pygame.event.clear()

    @property
    def cmd_menu(self):
        return self.game.cmd_menu

    def set_hp(self, hp):
        self.player.current_hp = hp
        self.game.load_window_palette()

    def assert_command_window_color(self, color):
        """Every COMMAND entry, selected or not, and the selection arrow are in the window color."""
        self.assertEqual(self.cmd_menu.rendered_color, color)
        widgets = self.cmd_menu.menu.get_widgets()
        self.assertEqual(len(widgets), 8)
        for widget in widgets:
            font = widget.get_font_info()
            self.assertEqual(tuple(font['color'])[:3], color)
            self.assertEqual(tuple(font['selected_color'])[:3], color)
            self.assertEqual(tuple(widget.get_selection_effect().color)[:3], color)
        selected = self.cmd_menu.menu.get_selected_widget()
        self.assertEqual(tuple(selected.get_font_color_status())[:3], color)

    # The COMMAND window (pygame-menu)

    def test_command_window_white_at_normal_hp(self):
        self.assertEqual(self.game.color, WHITE)
        self.assert_command_window_color(WHITE)

    def test_command_window_selected_entry_red_at_low_hp(self):
        self.set_hp(4)
        self.assertEqual(self.game.color, RED)
        self.assert_command_window_color(RED)
        # moving the cursor keeps it red
        self.cmd_menu.menu.enable()
        self.cmd_menu.menu.update([pygame.event.Event(KEYDOWN, key=pygame.K_DOWN)])
        self.assert_command_window_color(RED)
        self.set_hp(15)
        self.assert_command_window_color(WHITE)

    def test_command_window_built_at_low_hp_is_red(self):
        # changing maps builds a new COMMAND window, in the color for the current HP
        self.player.current_hp = 2
        self.game.change_map(map_lookup['Brecconary'](self.game.config), destination_coordinates=(23, 10))
        self.assertEqual(self.game.color, RED)
        self.assert_command_window_color(RED)

    def test_command_window_background_and_border_redrawn(self):
        with patch.object(self.cmd_menu.graphics, 'set_window_background') as set_window_background:
            self.set_hp(3)
        self.assertEqual([c.args[2] for c in set_window_background.call_args_list], [RED, RED])
        with patch.object(self.cmd_menu.graphics, 'set_window_background') as set_window_background:
            self.set_hp(3)
        set_window_background.assert_not_called()  # nothing changed, nothing redrawn

    # The other windows read the same color when they're drawn

    def test_windows_opened_from_the_command_window_follow_the_color(self):
        self.set_hp(1)
        self.assertEqual(self.cmd_menu.color, RED)
        self.assertEqual(self.cmd_menu.dialog_lookup.color, RED)
        self.set_hp(15)
        self.assertEqual(self.cmd_menu.color, WHITE)
        self.assertEqual(self.cmd_menu.dialog_lookup.color, WHITE)

    def item_list_colors(self, menu_name):
        pygame.event.post(pygame.event.Event(KEYDOWN, key=K_ESCAPE))
        with patch.object(self.cmd_menu.graphics, 'blink_arrow') as blink_arrow, \
                patch.object(self.cmd_menu.graphics, 'create_window') as create_window, \
                patch('src.menu.draw_text') as draw_text, patch('src.menu.display'):
            self.cmd_menu.display_item_menu(menu_name)
        return ({c.kwargs['color'] for c in blink_arrow.call_args_list},
                {c.args[6] for c in create_window.call_args_list},
                {c.kwargs['color'] for c in draw_text.call_args_list})

    def test_spell_and_item_lists(self):
        self.player.spells = ['HEAL', 'HURT']
        self.player.inventory = ['Herb', 'Torch']
        for hp, color in ((15, WHITE), (4, RED)):
            self.set_hp(hp)
            for menu_name in ('spells', 'inventory'):
                with self.subTest(hp=hp, menu=menu_name):
                    cursor, window, text = self.item_list_colors(menu_name)
                    self.assertEqual(cursor, {color})
                    self.assertEqual(window, {color})
                    self.assertEqual(text, {color})

    def test_yes_no_prompt(self):
        for hp, color in ((15, WHITE), (4, RED)):
            self.set_hp(hp)
            pygame.event.post(pygame.event.Event(KEYDOWN, key=K_RETURN))
            with patch.object(self.cmd_menu.graphics, 'create_window') as create_window:
                self.cmd_menu.prompt_yes_no()
            self.assertEqual({c.kwargs['color'] for c in create_window.call_args_list}, {color})

    def test_shop_cursor(self):
        dialog_lookup = self.cmd_menu.dialog_lookup
        for hp, color in ((15, WHITE), (4, RED)):
            self.set_hp(hp)
            pygame.event.post(pygame.event.Event(KEYDOWN, key=K_ESCAPE))
            with patch.object(self.cmd_menu, 'window_drop_down_effect'), \
                    patch('data.text.dialog_lookup_table.draw_text') as draw_text:
                dialog_lookup.select_in_window(SHOP_INVENTORY_WINDOW, 2, lambda: None, 2)
            self.assertEqual(draw_text.call_args.args[5], color)

    def test_battle_command_window(self):
        battle_ctrl = self.game.battle_ctrl
        for hp, color in ((15, WHITE), (4, RED)):
            self.set_hp(hp)
            with patch.object(battle_ctrl.graphics, 'blink_switch') as blink_switch, \
                    patch('src.battle_controller.event.get', return_value=[]):
                battle_ctrl.handle_battle_prompts(False, MagicMock())
            self.assertEqual(blink_switch.call_args.kwargs['color'], color)

    # When the color changes (NES: when the background palettes are loaded, and ChkLowHP after a step)

    def test_damage_turns_windows_red_at_once(self):
        with patch.object(self.cmd_menu, 'show_line_in_dialog_box'):
            self.game.receive_damage(10)
        self.assertEqual(self.player.current_hp, 5)
        self.assertEqual(self.game.color, WHITE)
        with patch.object(self.cmd_menu, 'show_line_in_dialog_box'):
            self.game.receive_damage(1)
        self.assertEqual(self.game.color, RED)
        self.assert_command_window_color(RED)

    def test_swamp_damage_turns_windows_red(self):
        self.player.current_hp = 6
        with patch('src.game.flash_transparent_color'), patch.object(self.game.drawer, 'draw_all'):
            self.game.damage_step(damage_amount=2)
        self.assertEqual(self.game.color, RED)

    def test_healing_turns_windows_white(self):
        for heal in ('heal', 'herb', 'healmore'):
            with self.subTest(heal=heal):
                self.set_hp(1)
                self.assertEqual(self.game.color, RED)
                self.player.inventory = ['Herb']
                with patch.object(self.cmd_menu, 'show_text_in_dialog_box'), \
                        patch.object(self.cmd_menu, 'show_line_in_dialog_box'):
                    getattr(self.cmd_menu, heal)()
                self.assertGreater(self.player.current_hp, 4)
                self.assertEqual(self.game.color, WHITE)
                self.assert_command_window_color(WHITE)

    def test_step_only_clears_red(self):
        # NES ChkLowHP: a step turns the windows white if HP isn't low, but never turns them red
        self.set_hp(2)
        self.player.current_hp = 10
        self.game.count_step()
        self.assertEqual(self.game.color, WHITE)
        self.player.current_hp = 2
        self.game.count_step()
        self.assertEqual(self.game.color, WHITE)

    def test_level_up_waits_for_the_next_palette_load(self):
        # NES: a level up raises the max HP (LoadStats) but loads no palette; HP 5 of 15 isn't low, of 24 it is
        self.set_hp(5)
        self.player.max_hp = 24
        self.game.get_events()
        self.assertEqual(self.game.color, WHITE)
        self.game.change_map(map_lookup['Brecconary'](self.game.config), destination_coordinates=(23, 10))
        self.assertEqual(self.game.color, RED)

    def test_inn_wakes_up_to_white_windows(self):
        self.game.change_map(map_lookup['Brecconary'](self.game.config), destination_coordinates=(23, 10))
        self.set_hp(2)
        self.player.gold = 100
        cmd_menu = self.cmd_menu
        colors = []

        def record(*_args, **_kwargs):
            colors.append((cmd_menu.color, cmd_menu.dialog_lookup.color, self.game.color))

        with patch.object(cmd_menu, 'show_line_in_dialog_box', side_effect=record), \
                patch.object(cmd_menu, 'show_text_in_dialog_box', side_effect=record), \
                patch('data.text.dialog_lookup_table.fade'):
            cmd_menu.dialog_lookup.inn_sleep(6)
        # "Good night." is said before the fade out, at the old HP; the innkeeper's next lines come after the fade in
        self.assertEqual(colors, [(RED, RED, RED), (WHITE, WHITE, WHITE)])
        self.assert_command_window_color(WHITE)

    def test_death_and_revival(self):
        with patch.object(self.cmd_menu, 'show_line_in_dialog_box'):
            self.game.receive_damage(15)
        self.assertEqual(self.game.color, RED)
        self.player.is_dead = True
        self.game.set_post_death_attributes()
        self.assertEqual(self.player.current_hp, self.player.max_hp)
        self.assertEqual(self.game.color, WHITE)
        self.assert_command_window_color(WHITE)

    def test_cursed_revival_at_1_hp_is_red(self):
        # NES StartAtThroneRoom: 1 HP is set before the throne room fades in, so the king's words are in red windows
        self.player.wearing_cursed_belt = True
        self.player.current_hp = 0
        self.player.is_dead = True
        colors = []
        with patch('src.menu.CommandMenu.show_text_in_dialog_box',
                   side_effect=lambda *a, **k: colors.append(self.game.color)), \
                patch.object(self.game, 'leave_tantegel'):
            self.game.set_post_death_attributes()
        self.assertEqual(self.player.current_hp, 1)
        self.assertEqual(colors, [RED])
        self.assert_command_window_color(RED)
