from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame
from pygame import KEYDOWN, K_ESCAPE, K_RETURN

from src.color import BLACK, LOW_HP_RED, WHITE, is_low_hp, window_color
from src.config.test_config import test_config
from src.cursor import IN_DOWN
from src.maps_functions import PAL0_COLOR1_LOW_HP
from src.visual_effects import NES_PALETTE, NES_RED
from src.maps import map_lookup
from src.windows import SHOP_INVENTORY_WINDOW
from tests.helpers import new_game


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
        self.assertEqual(window_color(4, 15), LOW_HP_RED)
        self.assertEqual(window_color(5, 15), WHITE)

    def test_low_hp_red_is_nes_26(self):
        # AddPalByte's ChkLowHPPal: LDA #$26, the same red for the windows and the map's palette 0 tiles
        self.assertEqual(LOW_HP_RED, NES_PALETTE[0x26])
        self.assertEqual(LOW_HP_RED, PAL0_COLOR1_LOW_HP)
        # not RedFlashPal's $16, the damage flash
        self.assertNotEqual(LOW_HP_RED, NES_RED)


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
        self.game = new_game()
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
        """The whole COMMAND window, its border, title, every entry and the cursor, is in the window color: drawn, it
        has no other color but black (on the NES they are all tiles in background palette 0, AddPalByte)."""
        with patch.dict(self.game.game_state.config, NO_BLIT=False):
            rect = self.cmd_menu.draw_command_window()
        window = pygame.image.tobytes(self.game.screen.subsurface(rect), 'RGB')
        colors = {tuple(window[i:i + 3]) for i in range(0, len(window), 3)}
        self.assertEqual(colors, {BLACK, color})

    # The COMMAND window

    def test_command_window_white_at_normal_hp(self):
        self.assertEqual(self.game.color, WHITE)
        self.assert_command_window_color(WHITE)

    def test_command_window_selected_entry_red_at_low_hp(self):
        self.set_hp(4)
        self.assertEqual(self.game.color, LOW_HP_RED)
        self.assert_command_window_color(LOW_HP_RED)
        # moving the cursor keeps it red
        self.cmd_menu.menu.enable()
        self.cmd_menu.menu.process_input(IN_DOWN)
        self.assertEqual(1, self.cmd_menu.menu.selected)
        self.assert_command_window_color(LOW_HP_RED)
        self.set_hp(15)
        self.assert_command_window_color(WHITE)

    def test_command_window_built_at_low_hp_is_red(self):
        # changing maps builds a new COMMAND window, in the color for the current HP
        self.player.current_hp = 2
        self.game.change_map(map_lookup['Brecconary'](self.game.config), destination_coordinates=(23, 10))
        self.assertEqual(self.game.color, LOW_HP_RED)
        self.assert_command_window_color(LOW_HP_RED)

    def test_open_command_window_changes_color_with_hp(self):
        # Nothing is kept drawn in an old color: the next time the open window is drawn, it is in the new one
        self.cmd_menu.menu.enable()
        self.assert_command_window_color(WHITE)
        self.set_hp(3)
        self.assert_command_window_color(LOW_HP_RED)
        self.set_hp(15)
        self.assert_command_window_color(WHITE)

    def test_window_background_white_turns_low_hp_red(self):
        graphics = self.cmd_menu.graphics
        path = self.game.directories.COMMAND_MENU_BACKGROUND_PATH
        colors = {}
        for color in (WHITE, LOW_HP_RED):
            window = pygame.Surface((64, 64))
            with patch.dict(graphics.config, NO_BLIT=False):
                graphics.set_window_background(window, path, color)
            colors[color] = {tuple(window.get_at((x, y)))[:3] for x in range(64) for y in range(64)}
        # the image's border is near white, (255, 254, 255), which set_window_background matches as white
        self.assertEqual(colors[WHITE], {(0, 0, 0), (255, 254, 255)})
        self.assertEqual(colors[LOW_HP_RED], {(0, 0, 0), LOW_HP_RED})

    def test_bad_ending_window_color(self):
        # NES ChooseDrgnLrd loads BadEndBGPal ($16 at $3F01) with PrepBGPalLoad, so ChkLowHPPal still makes it $26
        # when HP is low (ZeroStats leaves HitPoints alone)
        dialog_lookup = self.cmd_menu.dialog_lookup
        for hp, color in ((15, NES_RED), (4, LOW_HP_RED)):
            with self.subTest(hp=hp):
                self.player.current_hp = hp
                with patch.object(self.cmd_menu, 'show_line_in_dialog_box'), \
                        patch.object(self.game.drawer, 'draw_hovering_stats_window') as stats_window, \
                        patch('data.text.dialog_lookup_table.display'):
                    dialog_lookup.show_bad_ending_palette('')
                self.assertEqual(self.game.color, color)
                self.assertEqual(stats_window.call_args.args[2], color)
                self.assertEqual(self.game.current_map.low_hp_palette, color == LOW_HP_RED)

    # The other windows read the same color when they're drawn

    def test_windows_opened_from_the_command_window_follow_the_color(self):
        self.set_hp(1)
        self.assertEqual(self.cmd_menu.color, LOW_HP_RED)
        self.assertEqual(self.cmd_menu.dialog_lookup.color, LOW_HP_RED)
        self.set_hp(15)
        self.assertEqual(self.cmd_menu.color, WHITE)
        self.assertEqual(self.cmd_menu.dialog_lookup.color, WHITE)

    def item_list_colors(self, menu_name):
        pygame.event.post(pygame.event.Event(KEYDOWN, key=K_ESCAPE))
        with patch('src.menu.draw_cursor_tile') as draw_cursor_tile, \
                patch('src.menu.draw_window') as draw_window, \
                patch('src.menu.draw_text') as draw_text, patch('src.menu.display'), \
                patch.dict(self.game.game_state.config, NO_BLIT=False):
            self.cmd_menu.display_item_menu(menu_name)
        return ({c.args[4] for c in draw_cursor_tile.call_args_list},
                {c.args[2] for c in draw_window.call_args_list},
                {c.kwargs['color'] for c in draw_text.call_args_list})

    def test_spell_and_item_lists(self):
        self.player.spells = ['HEAL', 'HURT']
        self.player.inventory = ['Herb', 'Torch']
        for hp, color in ((15, WHITE), (4, LOW_HP_RED)):
            self.set_hp(hp)
            for menu_name in ('spells', 'inventory'):
                with self.subTest(hp=hp, menu=menu_name):
                    cursor, window, text = self.item_list_colors(menu_name)
                    self.assertEqual(cursor, {color})
                    self.assertEqual(window, {color})
                    self.assertEqual(text, {color})

    def test_yes_no_prompt(self):
        for hp, color in ((15, WHITE), (4, LOW_HP_RED)):
            self.set_hp(hp)
            pygame.event.post(pygame.event.Event(KEYDOWN, key=K_RETURN))
            with patch('src.translated_window.draw_window') as draw_window, patch('src.menu.display'), \
                    patch.dict(self.game.game_state.config, NO_BLIT=False):
                self.cmd_menu.prompt_yes_no()
            # The border, the text and the cursor are all in the window color (see tests/test_generated_windows.py)
            self.assertEqual({c.args[2] for c in draw_window.call_args_list}, {color})

    def test_shop_cursor(self):
        dialog_lookup = self.cmd_menu.dialog_lookup
        for hp, color in ((15, WHITE), (4, LOW_HP_RED)):
            self.set_hp(hp)
            pygame.event.post(pygame.event.Event(KEYDOWN, key=K_ESCAPE))
            with patch.object(self.cmd_menu, 'window_drop_down_effect'), \
                    patch('src.menu.draw_cursor_tile') as draw_cursor_tile, \
                    patch('data.text.dialog_lookup_table.display'), \
                    patch.dict(self.game.game_state.config, NO_BLIT=False):
                dialog_lookup.select_in_window(SHOP_INVENTORY_WINDOW, 2, lambda: None, 2)
            self.assertEqual({c.args[4] for c in draw_cursor_tile.call_args_list}, {color})

    def test_battle_command_window(self):
        battle_ctrl = self.game.battle_ctrl
        for hp, color in ((15, WHITE), (4, LOW_HP_RED)):
            self.set_hp(hp)
            with patch('src.translated_window.draw_window') as draw_window, \
                    patch('src.battle_controller.display'), \
                    patch('src.battle_controller.event.get', return_value=[]), \
                    patch.dict(self.game.game_state.config, NO_BLIT=False):
                battle_ctrl.handle_battle_prompts(False, MagicMock())
            # The border, the text and the cursor are all in the window color (see tests/test_generated_windows.py)
            self.assertEqual(draw_window.call_args.args[2], color)

    # When the color changes (NES: when the background palettes are loaded, and ChkLowHP after a step)

    def test_damage_turns_windows_red_at_once(self):
        with patch.object(self.cmd_menu, 'show_line_in_dialog_box'):
            self.game.receive_damage(10)
        self.assertEqual(self.player.current_hp, 5)
        self.assertEqual(self.game.color, WHITE)
        with patch.object(self.cmd_menu, 'show_line_in_dialog_box'):
            self.game.receive_damage(1)
        self.assertEqual(self.game.color, LOW_HP_RED)
        self.assert_command_window_color(LOW_HP_RED)

    def test_swamp_damage_turns_windows_red(self):
        self.player.current_hp = 6
        with patch('src.game.flash_transparent_color'), patch.object(self.game.drawer, 'draw_all'):
            self.game.damage_step(damage_amount=2)
        self.assertEqual(self.game.color, LOW_HP_RED)

    def test_healing_turns_windows_white(self):
        for heal in ('heal', 'herb', 'healmore'):
            with self.subTest(heal=heal):
                self.set_hp(1)
                self.assertEqual(self.game.color, LOW_HP_RED)
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
        self.assertEqual(self.game.color, LOW_HP_RED)

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
                patch('data.text.dialog_lookup_table.screen_fade'):
            cmd_menu.dialog_lookup.inn_sleep(6)
        # "Good night." is said before the fade out, at the old HP; the innkeeper's next lines come after the fade in
        self.assertEqual(colors, [(LOW_HP_RED, LOW_HP_RED, LOW_HP_RED), (WHITE, WHITE, WHITE)])
        self.assert_command_window_color(WHITE)

    def test_death_and_revival(self):
        with patch.object(self.cmd_menu, 'show_line_in_dialog_box'):
            self.game.receive_damage(15)
        self.assertEqual(self.game.color, LOW_HP_RED)
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
        self.assertEqual(colors, [LOW_HP_RED])
        self.assert_command_window_color(LOW_HP_RED)
