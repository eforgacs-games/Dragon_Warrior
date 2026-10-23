"""The title menu's CHANGE MESSAGE SPEED options (src/options_screen.py) and the Classic / Modern dialog styles."""
import json
import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import K_DOWN, K_LEFT, K_RETURN, K_RIGHT, K_j, KEYDOWN, QUIT
from pygame.event import Event

from src.config.test_config import test_config
from src.dialog_box import DIALOG_ROWS, frames_per_character
from src.game import BACK_TO_TITLE_MENU, Game
from src.options_screen import CLASSIC, DEFAULT_DIALOG_STYLE, DEFAULT_MESSAGE_SPEED, DEFAULT_OPTIONS, \
    DIALOG_STYLE_OPTIONS, DIALOG_STYLE_SAVE_KEY, MESSAGE_SPEED_NAMES, MESSAGE_SPEED_OPTIONS, MESSAGE_SPEED_SAVE_KEY, \
    MODERN, NPCS_MAKE_WAY_OPTIONS, NPCS_MAKE_WAY_SAVE_KEY, Options, OptionsScreen, dialog_style_from_save, \
    message_speed_from_save, npcs_make_way_from_save
from src.windows import MESSAGE_SPEED_WINDOW
from tests import helpers
from tests.mock_map import MockMap

ENTER = Event(KEYDOWN, key=K_RETURN)  # A
DOWN = Event(KEYDOWN, key=K_DOWN)
LEFT = Event(KEYDOWN, key=K_LEFT)
RIGHT = Event(KEYDOWN, key=K_RIGHT)
B = Event(KEYDOWN, key=K_j)
# Frames with nothing pressed after each press: a window reads one button per press (SelectionButtons), and the next
# one only once the last has been let go (WndBtnRetrig), so these leave time for that, and for a window to open
GAP = 4


def presses(*keys):
    """event.get's results for the selection loop, which reads it once a frame: each press, then GAP frames of none."""
    results = []
    for key in keys:
        results += [[]] * GAP + [[key]]
    return results


def new_game(**overrides) -> Game:
    # A copy of test_config, so the settings these tests change don't leak into other tests
    config = {**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True, 'TEXT_SPEED': 'Fast',
              'DIALOG_STYLE': CLASSIC, 'NPCS_MAKE_WAY': True, **overrides}
    return helpers.new_game(config)


def settings(config):
    return config['TEXT_SPEED'], config['DIALOG_STYLE'], config['NPCS_MAKE_WAY']


class OptionsTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()
        pygame.display.set_mode((800, 600))

    def setUp(self):
        self.game = new_game()
        self.config = self.game.game_state.config
        # One NES frame of game time per pass of the selection loop (its WaitForNMI), whatever the machine's speed:
        # the cursor and SelectionButtons count frames from the game clock, so on a slow or fast run the scripted
        # presses (presses(), one event.get per frame) would otherwise land on different frames
        clock = [0]

        def next_frame(frames=1, *_args, **_kwargs):
            clock[0] += round(frames * 1000 / 60)
        patch('src.cursor.get_ticks', lambda: clock[0]).start()
        patch('src.selection.wait_frames', side_effect=next_frame).start()
        self.addCleanup(patch.stopall)


class TestMessageSpeedRules(TestCase):

    def test_nes_speeds_in_window_order(self):
        # MessageSpeed: #$00-fast, #$01-normal, #$02-slow; MsgSpeedDat lists FAST, NORMAL, SLOW
        self.assertEqual(('Fast', 'Normal', 'Slow'), MESSAGE_SPEED_NAMES)
        self.assertEqual(('FAST', 'NORMAL', 'SLOW'), MESSAGE_SPEED_OPTIONS.labels)

    def test_frames_per_character(self):
        # TextToPPU: LDX MessageSpeed / WaitForNMI / DEX / BPL, MessageSpeed + 1 frames
        self.assertEqual([1, 2, 3], [frames_per_character(speed) for speed in MESSAGE_SPEED_NAMES])

    def test_message_speed_window_layout(self):
        # MsgSpeedDat: 7 blocks high, 18 tiles wide, Y = 7, X = 4; cursor home Y = 8, X = 6; one entry per 2 rows
        self.assertEqual(MESSAGE_SPEED_WINDOW, MESSAGE_SPEED_OPTIONS.window)
        self.assertEqual([8, 10, 12], [MESSAGE_SPEED_OPTIONS.entry_row(index) for index in range(3)])
        self.assertEqual(6, MESSAGE_SPEED_OPTIONS.cursor_column)
        # the dialog style window sits directly above it, and the NPCS MAKE WAY window above that, all the same width
        style_window, npcs_window = DIALOG_STYLE_OPTIONS.window, NPCS_MAKE_WAY_OPTIONS.window
        self.assertEqual(MESSAGE_SPEED_WINDOW.y, style_window.y + style_window.height)
        self.assertEqual(style_window.y, npcs_window.y + npcs_window.height)
        self.assertEqual(0, npcs_window.y)
        for window in (style_window, npcs_window):
            self.assertEqual((MESSAGE_SPEED_WINDOW.x, MESSAGE_SPEED_WINDOW.width), (window.x, window.width))
        self.assertEqual('CLASSIC (NES)', DIALOG_STYLE_OPTIONS.labels[0])
        self.assertEqual(('ON', 'OFF (NES)'), NPCS_MAKE_WAY_OPTIONS.labels)

    def test_npcs_make_way_entries_side_by_side(self):
        # both on row 3, the cursor in the tile before each, and the text ending inside the right border (column 17)
        self.assertEqual([3, 3], [NPCS_MAKE_WAY_OPTIONS.entry_row(index) for index in range(2)])
        self.assertEqual([2, 7], [NPCS_MAKE_WAY_OPTIONS.entry_cursor_column(index) for index in range(2)])
        last = NPCS_MAKE_WAY_OPTIONS.entry_text_column(1) + len(NPCS_MAKE_WAY_OPTIONS.labels[1])
        self.assertLessEqual(last, NPCS_MAKE_WAY_OPTIONS.window.width * 2 - 1)

    def test_defaults(self):
        # NewQuest: LDA #MSG_NORMAL; Classic (the NES dialog window) is the default style; NPCs make way by default
        self.assertEqual(('Normal', CLASSIC), (DEFAULT_MESSAGE_SPEED, DEFAULT_DIALOG_STYLE))
        self.assertEqual(Options('Normal', CLASSIC, True), DEFAULT_OPTIONS)

    def test_old_saves_load_with_the_defaults(self):
        self.assertEqual('Normal', message_speed_from_save({'Name': 'Ed'}))
        self.assertEqual(CLASSIC, dialog_style_from_save({'Name': 'Ed'}))
        self.assertTrue(npcs_make_way_from_save({'Name': 'Ed'}))
        self.assertEqual('Normal', message_speed_from_save({MESSAGE_SPEED_SAVE_KEY: 'Warp'}))
        self.assertEqual('Slow', message_speed_from_save({MESSAGE_SPEED_SAVE_KEY: 'Slow'}))
        self.assertEqual(MODERN, dialog_style_from_save({DIALOG_STYLE_SAVE_KEY: MODERN}))
        self.assertFalse(npcs_make_way_from_save({NPCS_MAKE_WAY_SAVE_KEY: False}))
        self.assertTrue(npcs_make_way_from_save({NPCS_MAKE_WAY_SAVE_KEY: 'no'}))


class TestOptionsScreen(OptionsTestCase):

    def choose(self, events, speed='Normal', style=CLASSIC, make_way=True):
        options_screen = OptionsScreen(self.game.screen, self.config)
        with patch('src.selection.event.get', side_effect=presses(*events)):
            return options_screen.choose_options(Options(speed, style, make_way))

    def test_cursor_starts_on_the_current_settings(self):
        # LA93E: WndRow = MessageSpeed
        self.assertEqual(Options('Fast', MODERN, False), self.choose([ENTER, ENTER, ENTER], 'Fast', MODERN, False))
        self.assertEqual(Options('Slow', CLASSIC, True), self.choose([ENTER, ENTER, ENTER], 'Slow'))

    def test_choose_speed_then_style_then_npcs(self):
        self.assertEqual(Options('Slow', MODERN, False), self.choose([DOWN, ENTER, DOWN, ENTER, RIGHT, ENTER]))

    def test_cursor_stops_at_the_edges(self):
        self.assertEqual(Options('Slow', MODERN, False),
                         self.choose([DOWN, DOWN, DOWN, ENTER, DOWN, DOWN, ENTER, RIGHT, RIGHT, ENTER], 'Fast'))
        self.assertEqual(Options('Normal', CLASSIC, True), self.choose([ENTER, ENTER, LEFT, ENTER]))

    def test_npcs_make_way_moves_left_and_right_only(self):
        # a one-row window: up and down do nothing (WndUpPressed/WndDownPressed stop on its only row)
        self.assertEqual(Options('Normal', CLASSIC, True), self.choose([ENTER, ENTER, DOWN, ENTER]))
        self.assertEqual(Options('Normal', CLASSIC, True), self.choose([ENTER, ENTER, RIGHT, LEFT, ENTER]))

    def test_left_and_right_do_nothing_in_the_speed_window(self):
        self.assertEqual(Options('Normal', CLASSIC, True), self.choose([RIGHT, ENTER, ENTER, ENTER]))

    def test_b_in_the_speed_window_cancels(self):
        self.assertIsNone(self.choose([DOWN, B]))

    def test_b_goes_back_a_window(self):
        # FAST, then B: the speed window again, still on FAST
        self.assertEqual(Options('Normal', CLASSIC, True), self.choose([ENTER, B, DOWN, ENTER, ENTER, ENTER], 'Fast'))
        # B in the NPCS MAKE WAY window: back to the dialog style
        self.assertEqual(Options('Normal', MODERN, False),
                         self.choose([ENTER, ENTER, B, DOWN, ENTER, RIGHT, ENTER]))

    def test_quit_in_the_options_screen(self):
        with patch('src.waiting.pygame_quit'), self.assertRaises(SystemExit):
            self.choose([Event(QUIT)])


class TestTitleMenuFlow(OptionsTestCase):

    def setUp(self):
        super().setUp()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.game.directories.save_dir = self.tmp_dir.name
        old_save = {'Experience': 0, 'Inventory': []}  # a save from before the settings were kept
        self.saves = {1: {**old_save, 'Name': 'Erdrick', 'Gold': 120},
                      2: {**old_save, 'Name': 'Loto', 'Gold': 5, MESSAGE_SPEED_SAVE_KEY: 'Fast'}}
        for slot, save in self.saves.items():
            with open(self.save_path(slot), 'w') as save_file:
                json.dump(save, save_file)

    def save_path(self, slot):
        return os.path.join(self.tmp_dir.name, f'save_slot_{slot}.json')

    def read(self, slot):
        with open(self.save_path(slot)) as save_file:
            return json.load(save_file)

    def run_title_menu(self, events, then=2):
        """Choose CHANGE MESSAGE SPEED (1) on the title menu, play the events, then choose `then` (BEGIN A NEW QUEST)."""
        with patch.object(self.game.game_functions, 'main_menu_selection', side_effect=[1, then]) as title_menu, \
                patch.object(self.game, 'begin_new_quest') as begin_new_quest, \
                patch('src.selection.event.get', side_effect=presses(*events)):
            self.game.show_main_menu_screen(self.game.screen)
        return title_menu, begin_new_quest

    def test_choose_a_log_then_its_speed_dialog_style_and_npcs(self):
        self.config['TEXT_SPEED'] = 'Fast'
        # log 2, then SLOW (from FAST, its saved speed), then MODERN, then OFF
        title_menu, begin_new_quest = self.run_title_menu([DOWN, ENTER, DOWN, DOWN, ENTER, DOWN, ENTER, RIGHT, ENTER])
        self.assertEqual({**self.saves[2], MESSAGE_SPEED_SAVE_KEY: 'Slow', DIALOG_STYLE_SAVE_KEY: MODERN,
                          NPCS_MAKE_WAY_SAVE_KEY: False}, self.read(2))
        self.assertEqual(self.saves[1], self.read(1))
        # ChngMsgSpeed -> WndBackToMain: the title menu again
        self.assertEqual(2, title_menu.call_count)
        begin_new_quest.assert_called_once()
        # the settings are the log's, not the running game's until that log is continued
        self.assertEqual(('Fast', CLASSIC, True), settings(self.config))

    def test_b_in_the_log_window_goes_back_to_the_title_menu(self):
        title_menu, _ = self.run_title_menu([B])
        self.assertEqual(self.saves[1], self.read(1))
        self.assertEqual(2, title_menu.call_count)

    def test_b_in_the_speed_window_saves_nothing(self):
        title_menu, _ = self.run_title_menu([ENTER, DOWN, B])
        self.assertEqual(self.saves[1], self.read(1))
        self.assertEqual(2, title_menu.call_count)

    def test_change_message_speed_lists_the_used_logs(self):
        self.game.save_dir_contents = self.game.save_files()
        with patch.object(OptionsScreen, 'choose_log', return_value=None) as choose_log:
            self.assertIs(BACK_TO_TITLE_MENU, self.game.change_message_speed())
        self.assertEqual([(1, 'Erdrick'), (2, 'Loto')], choose_log.call_args.args[0])

    def test_continuing_the_log_uses_its_settings(self):
        self.run_title_menu([ENTER, DOWN, DOWN, ENTER, DOWN, ENTER, RIGHT, ENTER])
        with patch.object(self.game.map_mgr, 'change_map'):
            self.game.load_game(self.read(1))
        self.assertEqual(('Slow', MODERN, False), settings(self.config))


class TestNewQuestOptions(OptionsTestCase):

    def test_new_quest_uses_the_chosen_options(self):
        self.config['TEXT_SPEED'], self.config['NPCS_MAKE_WAY'] = 'Fast', False
        with patch('src.selection.event.get', side_effect=presses(DOWN, ENTER, DOWN, ENTER, RIGHT, ENTER)):
            self.game.choose_new_quest_options()
        # the cursors start on NORMAL (NewQuest: LDA #MSG_NORMAL), CLASSIC and ON, whatever the last game used
        self.assertEqual(('Slow', MODERN, False), settings(self.config))

    def test_new_quest_keeps_npcs_making_way_by_default(self):
        self.config['NPCS_MAKE_WAY'] = False
        with patch('src.selection.event.get', side_effect=presses(ENTER, ENTER, ENTER)):
            self.game.choose_new_quest_options()
        self.assertEqual(('Normal', CLASSIC, True), settings(self.config))

    def test_new_quest_without_a_choice_uses_the_defaults(self):
        self.config['TEXT_SPEED'], self.config['DIALOG_STYLE'], self.config['NPCS_MAKE_WAY'] = 'Fast', MODERN, False
        with patch('src.selection.event.get', side_effect=presses(B)):
            self.game.choose_new_quest_options()
        self.assertEqual(('Normal', CLASSIC, True), settings(self.config))

    def test_begin_new_quest_shows_the_options_after_the_name(self):
        calls = []
        with patch.object(self.game, 'select_adventure_log', side_effect=lambda screen: calls.append('log')), \
                patch('src.game.NameSelection') as name_selection, \
                patch.object(self.game, 'choose_new_quest_options', side_effect=lambda: calls.append('options')), \
                patch('src.map_manager.screen_fade'), patch.object(self.game, 'music_player'), patch('src.game.CommandMenu'):
            name_selection.return_value.select_name.side_effect = lambda *args: calls.append('name') or 'Ed'
            self.game.begin_new_quest()
        self.assertEqual(['log', 'name', 'options'], calls)


class TestSaveRoundTrip(OptionsTestCase):

    def save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.game.cmd_menu.directories.save_dir = tmp_dir
            self.game.player.adventure_log = 3
            self.game.cmd_menu.save()
            with open(os.path.join(tmp_dir, 'save_slot_3.json')) as save_file:
                save = json.load(save_file)
        loaded = new_game(NPCS_MAKE_WAY=not self.config['NPCS_MAKE_WAY'])
        with patch.object(loaded.map_mgr, 'change_map'):
            loaded.load_game(save)
        return save, loaded.game_state.config

    def test_round_trip(self):
        for speed in MESSAGE_SPEED_NAMES:
            for style in (CLASSIC, MODERN):
                for make_way in (True, False):
                    self.config['TEXT_SPEED'], self.config['DIALOG_STYLE'] = speed, style
                    self.config['NPCS_MAKE_WAY'] = make_way
                    save, loaded_config = self.save_and_load()
                    self.assertEqual((speed, style, make_way), (save[MESSAGE_SPEED_SAVE_KEY],
                                                                save[DIALOG_STYLE_SAVE_KEY],
                                                                save[NPCS_MAKE_WAY_SAVE_KEY]))
                    self.assertEqual((speed, style, make_way), settings(loaded_config))

    def test_old_save_loads_with_the_defaults(self):
        self.config['TEXT_SPEED'], self.config['DIALOG_STYLE'], self.config['NPCS_MAKE_WAY'] = 'Fast', MODERN, False
        with patch.object(self.game.map_mgr, 'change_map'):
            self.game.load_game({'Name': 'Ed', 'Experience': 0, 'Gold': 0, 'Inventory': []})
        self.assertEqual(('Normal', CLASSIC, True), settings(self.config))

    def test_loaded_setting_reaches_the_npcs(self):
        # Game.ask_npc_to_make_way reads Game.config, the same dict the options are applied to
        with patch.object(self.game.map_mgr, 'change_map'):
            self.game.load_game({'Name': 'Ed', 'Experience': 0, 'Gold': 0, 'Inventory': [],
                                 NPCS_MAKE_WAY_SAVE_KEY: False})
        self.assertFalse(self.game.config['NPCS_MAKE_WAY'])


class TestDialogStyles(OptionsTestCase):

    def setUp(self):
        super().setUp()
        self.game.current_map = MockMap(self.game.config)
        self.game.current_map.load_map(self.game.player, (0, 0), self.config["TILE_SIZE"])
        self.cmd_menu = self.game.cmd_menu

    def lines_after_each_message(self, style, messages, **kwargs):
        self.config['DIALOG_STYLE'] = style
        seen = []
        original = self.cmd_menu.wait_for_dialog_key

        def record(*args, **record_kwargs):
            seen.append(self.cmd_menu.dialog_buffer.visible_lines)
            original(*args, **record_kwargs)

        with patch.object(self.cmd_menu, 'wait_for_dialog_key', side_effect=record):
            self.cmd_menu.show_text_in_dialog_box(messages, skip_text=True, **kwargs)
        return seen

    def test_classic_scrolls_on_below(self):
        seen = self.lines_after_each_message(CLASSIC, ("Welcome to Tantegel Castle.", "Thou hast a key.", "Goodbye."),
                                             add_quotes=True)
        self.assertEqual([['`Welcome to Tantegel', ' Castle.’'],
                          ['`Welcome to Tantegel', ' Castle.’', '`Thou hast a key.’'],
                          ['`Welcome to Tantegel', ' Castle.’', '`Thou hast a key.’', '`Goodbye.’']], seen)

    def test_modern_replaces_each_message(self):
        seen = self.lines_after_each_message(MODERN, ("Welcome to Tantegel Castle.", "Thou hast a key.", "Goodbye."),
                                             add_quotes=True)
        self.assertEqual([['`Welcome to Tantegel', ' Castle.’'], ['`Thou hast a key.’'], ['`Goodbye.’']], seen)

    def test_modern_battle_lines_replace_each_other(self):
        self.config['DIALOG_STYLE'] = MODERN
        self.cmd_menu.show_line_in_battle_dialog_box("A Slime draws near!\nCommand?\n")
        self.assertEqual(['A Slime draws near!', 'Command?'], self.cmd_menu.dialog_buffer.visible_lines)
        for _ in range(9):
            self.cmd_menu.show_line_in_dialog_box("Erdrick attacks!\n", add_quotes=False, skip_text=True,
                                                  hide_arrow=True, disable_sound=True)
        self.assertEqual(['Erdrick attacks!'], self.cmd_menu.dialog_buffer.visible_lines)

    def test_modern_arrow_is_at_the_bottom(self):
        self.config['DIALOG_STYLE'] = MODERN
        rows = []
        with patch.object(self.cmd_menu, 'dialog_cell_rect', side_effect=lambda row, *args: rows.append(row)), \
                patch.object(self.cmd_menu, 'draw_dialog_text'):
            self.cmd_menu.draw_dialog_arrow(True)
        self.assertEqual([DIALOG_ROWS - 1], rows)

    def beeps(self, style, text):
        self.config['DIALOG_STYLE'] = style
        with patch.object(self.cmd_menu.sound, 'play_sfx') as play_sfx:
            self.cmd_menu.show_line_in_dialog_box(text, skip_text=True, hide_arrow=True)
        return [call.args[0] for call in play_sfx.call_args_list]

    def test_modern_beeps_like_classic(self):
        classic = self.beeps(CLASSIC, "Welcome to Tantegel Castle.")
        self.assertEqual(13, len(classic))
        self.assertEqual(classic, self.beeps(MODERN, "Welcome to Tantegel Castle."))

    def test_message_speed_applies_in_both_styles(self):
        self.config['NO_WAIT'] = False
        for style in (CLASSIC, MODERN):
            self.config['DIALOG_STYLE'] = style
            for speed, frames in (('Fast', 1), ('Normal', 2), ('Slow', 3)):
                self.config['TEXT_SPEED'] = speed
                with patch.object(self.cmd_menu, 'wait_dialog_frames') as wait_frames:
                    self.cmd_menu.show_line_in_dialog_box("Hi there.", skip_text=True, hide_arrow=True)
                self.assertEqual(10 * frames, sum(call.args[0] for call in wait_frames.call_args_list), (style, speed))
                self.cmd_menu.dialog_buffer.clear()

    def test_modern_waits_go_through_the_game_wait(self):
        # src.waiting.wait is where QUIT is checked during a wait (#267) and where the game speed applies (#279)
        self.config['NO_WAIT'] = False
        self.config['DIALOG_STYLE'] = MODERN
        self.config['TEXT_SPEED'] = 'Slow'
        with patch('src.menu.wait') as wait:
            self.cmd_menu.show_line_in_dialog_box("Hi.", skip_text=True, hide_arrow=True)
        self.assertTrue(wait.called)

    def test_quit_while_modern_text_prints(self):
        self.config['NO_WAIT'] = False
        self.config['DIALOG_STYLE'] = MODERN
        pygame.event.clear()
        pygame.event.post(Event(QUIT))
        with patch('src.waiting.pygame_quit'), self.assertRaises(SystemExit):
            self.cmd_menu.show_line_in_dialog_box("Hello there.", skip_text=True, hide_arrow=True)

    def test_quit_while_modern_dialog_waits_for_a_key(self):
        self.config['DIALOG_STYLE'] = MODERN
        with patch('src.menu.event.get', return_value=[Event(QUIT)]), patch('src.waiting.pygame_quit'), \
                self.assertRaises(SystemExit):
            self.cmd_menu.show_line_in_dialog_box("Hello.")
