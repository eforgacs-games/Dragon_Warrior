"""The options overlay (src/options_overlay.py): SELECT or Tab on the map, this game's own settings changed in play,
in pages, with the NES / MODERN / CUSTOM preset (#409); the switches for the conveniences that act on a key (#437);
and the STAIRS setting (AUTO_STAIRS), which has no key of its own."""
import os
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from pygame import K_DOWN, K_ESCAPE, K_F2, K_LEFT, K_PAGEDOWN, K_PAGEUP, K_RETURN, K_RIGHT, K_TAB, K_UP, K_i, K_j, \
    K_k, K_u, KEYDOWN
from pygame.event import Event

from src.config.test_config import test_config
from src.display_filters import SCALING_PIXEL_PERFECT, SCALING_SMOOTH
from src.map_layouts import GRASS_STAIR_DOWN
from src.maps import STAIR_DIRECTIONS, map_lookup
from src.options_overlay import FIXED_ROWS, MOST_ROWS, OPTION_PAGES, OPTION_ROWS, OPTIONS_WINDOW, PRESET_CUSTOM, \
    PRESET_MODERN, PRESET_NES, PRESET_ROWS, OptionsOverlay, current_preset, options_layout, overlay_texts, \
    preset_values
from src.options_screen import CLASSIC, MODERN, SWITCHES, options_from_config
from src.visual_effects import FADE_STYLE_NES, FADE_STYLE_SMOOTH
from src.waiting import MENU_SPEED_FOLLOW as FOLLOW, MENU_SPEED_NORMAL as NORMAL
from tests import helpers
from tests.test_character_redraw import draw_frame

# Frames with nothing pressed after each press, like tests/test_options_screen.py
GAP = 2


def key(pressed_key):
    return Event(KEYDOWN, key=pressed_key, mod=0)


def presses(*keys):
    """event.get's results for the overlay's loop, which reads it once a frame: each press, then GAP frames of none."""
    results = []
    for pressed_key in keys:
        results += [[]] * GAP + [[key(pressed_key)]]
    return results


# new_game's settings: the first value of every row (the order the rows cycle in), whatever base_config says
DEFAULTS = {row.config_key: row.values[0] for row in OPTION_ROWS}
OWN_KEYS = tuple(DEFAULTS)


def new_game(**overrides):
    # A copy of test_config, so the settings these tests change don't leak into other tests
    return helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True, **DEFAULTS,
                             **overrides})


def own_settings(config):
    return {config_key: config[config_key] for config_key in OWN_KEYS}


def row_named(label):
    return next(row for row in OPTION_ROWS if row.label == label)


def page_of(label):
    return next(number for number, page in enumerate(OPTION_PAGES) if label in [row.label for row in page.rows])


def down_to(label):
    """The presses that go to the row's page (START turns the page) and move the cursor from PRESET to the row."""
    page = page_of(label)
    rows = [row.label for row in OPTION_PAGES[page].rows]
    return (K_i,) * page + (K_DOWN,) * (FIXED_ROWS + rows.index(label))


def page_texts(config, page=0):
    return [text.text for text in options_layout(config, page).texts]


class OverlayTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()

    def setUp(self):
        self.game = self.make_game()
        self.config = self.game.game_state.config
        # One NES frame of game time per pass of the overlay's loop, whatever the machine's speed
        clock = [0]

        def next_frame(frames=1, *_args, **_kwargs):
            clock[0] += round(frames * 1000 / 60)
        patch('src.cursor.get_ticks', lambda: clock[0]).start()
        patch('src.selection.wait_frames', side_effect=next_frame).start()
        self.addCleanup(patch.stopall)

    def make_game(self):
        return new_game()

    def run_overlay(self, *keys):
        """Run the overlay with these key presses; returns how many times the menu button sound played."""
        with patch('src.selection.event.get', side_effect=presses(*keys)), \
                patch.object(self.game.sound, 'play_sound') as play_sound:
            OptionsOverlay(self.game).run()
        return [call.args[0] for call in play_sound.call_args_list].count(self.game.directories.menu_button_sfx)


class TestOpening(OverlayTestCase):

    def press(self, pressed_key):
        self.game.handle_keypresses(key(pressed_key))

    def test_select_or_tab_opens_it_on_the_map(self):
        for pressed_key in (K_u, K_TAB):
            with self.subTest(key=pygame.key.name(pressed_key)), patch.object(self.game, 'open_options') as open_options:
                self.press(pressed_key)
            open_options.assert_called_once()
            self.assertFalse(self.game.options_requested)

    def test_it_waits_for_the_heros_step(self):
        # Like START (PausePrepLoop): mid-step it waits, and no new step starts meanwhile
        self.game.player.is_moving = True
        with patch.object(self.game, 'open_options') as open_options:
            self.press(K_u)
            open_options.assert_not_called()
            self.assertTrue(self.game.movement.freeze_pending)
            self.game.player.is_moving = False
            self.game.movement.resolve_pending_freezes()
        open_options.assert_called_once()

    def test_not_while_a_window_is_open_or_the_game_is_paused(self):
        for attribute, owner in (('launch_signaled', self.game.cmd_menu), ('paused', self.game),
                                 ('cmd_menu_requested', self.game), ('pause_requested', self.game)):
            with self.subTest(attribute), patch.object(owner, attribute, True), \
                    patch.object(self.game, 'open_options') as open_options:
                self.press(K_u)
                open_options.assert_not_called()
                self.assertFalse(self.game.options_requested)

    def test_not_while_the_command_window_is_up(self):
        self.game.cmd_menu.menu.enable()
        self.addCleanup(self.game.cmd_menu.menu.disable)
        with patch.object(self.game, 'open_options') as open_options:
            self.press(K_TAB)
        open_options.assert_not_called()

    def test_start_while_it_is_pending_pauses_instead(self):
        self.game.player.is_moving = True
        with patch.object(self.game, 'open_options') as open_options:
            self.press(K_u)
            self.press(pygame.K_i)
            self.game.player.is_moving = False
            self.game.movement.resolve_pending_freezes()
        open_options.assert_not_called()
        self.assertTrue(self.game.paused)

    def test_a_while_it_is_pending_does_not_open_the_command_window_after(self):
        self.game.player.is_moving = True
        with patch.object(self.game, 'open_options'):
            self.press(K_u)
            self.press(K_k)
        self.assertFalse(self.game.cmd_menu_requested)

    def test_select_opens_and_closes_it(self):
        with patch('src.selection.event.get', side_effect=presses(K_u)), \
                patch('src.options_overlay.OptionsOverlay.close', autospec=True) as close:
            self.press(K_u)
        close.assert_called_once()

    def test_time_stops_while_it_is_open(self):
        # The overlay's loop is the only one running: no map frame, no NPC step, no draw of the map
        schedule = self.game.movement.npc_schedule
        before = (schedule.frame_counter, self.game.tiles_moved_since_spawn, self.game.repel_timer,
                  [character.rect.copy() for character in self.game.current_map.roaming_characters])
        with patch.object(self.game, 'map_frame') as map_frame, \
                patch.object(self.game.drawer, 'draw_all') as draw_all, \
                patch('src.selection.event.get', side_effect=presses(K_DOWN, K_RIGHT, K_UP, K_u)):
            self.press(K_u)
        map_frame.assert_not_called()
        draw_all.assert_not_called()
        self.assertEqual(before, (schedule.frame_counter, self.game.tiles_moved_since_spawn, self.game.repel_timer,
                                  [character.rect.copy() for character in self.game.current_map.roaming_characters]))


class TestRows(OverlayTestCase):

    def test_pages(self):
        self.assertEqual([("LOOK & SOUND", [("MESSAGE SPEED", 'TEXT_SPEED', ("FAST", "NORMAL", "SLOW")),
                                            ("DIALOG STYLE", 'DIALOG_STYLE', ("CLASSIC (NES)", "MODERN")),
                                            ("FADE STYLE", 'FADE_STYLE', ("NES", "SMOOTH")),
                                            ("MUSIC", 'ORCHESTRA_MUSIC_ENABLED', ("ORCHESTRA", "NES")),
                                            ("LANGUAGE", 'LANGUAGE', ("ENGLISH", "한국어")),
                                            ("SCANLINES", 'SCANLINES', ("OFF", "ON")),
                                            ("SCALING", 'SCALING', ("SMOOTH", "PIXEL PERFECT")),
                                            ("STATUS WINDOW", 'STATUS_WINDOW', ("NES", "ALWAYS")),
                                            ("SHOP PREVIEW", 'SHOP_PREVIEW', ("OFF (NES)", "ON"))]),
                          ("GAMEPLAY", [("NPCS MAKE WAY", 'NPCS_MAKE_WAY', ("ON", "OFF (NES)")),
                                        ("STAIRS", 'AUTO_STAIRS', ("STEP ON", "NES")),
                                        ("QUICK ACTION", 'QUICK_ACTION', ("OFF (NES)", "ON")),
                                        ("ENCOUNTERS", 'ENCOUNTERS', ("NES", "HALF", "OFF")),
                                        ("EXP/GOLD", 'EXP_GOLD', ("x1 (NES)", "x2", "x4"))]),
                          ("CONTROLS", [("GAME SPEED", 'GAME_SPEED_KEYS', ("OFF (NES)", "ON")),
                                        ("SAVE STATES", 'SAVE_STATES', ("OFF (NES)", "ON")),
                                        ("REWIND", 'REWIND', ("OFF (NES)", "ON")),
                                        ("AUTO-GRIND", 'AUTO_GRIND', ("OFF (NES)", "ON")),
                                        ("GRIND STOP", 'AUTO_GRIND_STOP', ("RED HP", "HALF HP", "3/4 HP")),
                                        ("MENU SPEED", 'MENU_SPEED', ("NORMAL", "FOLLOW GAME")),
                                        ("CHEATS", 'CHEAT_KEYS', ("OFF (NES)", "ON")),
                                        ("RUN BUTTON", 'RUN_BUTTON', ("OFF (NES)", "ON"))])],
                         [(page.title, [(row.label, row.config_key, row.value_labels) for row in page.rows])
                          for page in OPTION_PAGES])

    def test_every_page_starts_with_preset_and_page(self):
        for number in range(len(OPTION_PAGES)):
            with self.subTest(page=number):
                layout = options_layout(self.config, number)
                self.assertEqual(OPTION_PAGES[number].title, layout.title.text)
                self.assertEqual(["PRESET", "CUSTOM", "PAGE", f"{number + 1}/3"], page_texts(self.config, number)[:4])
                self.assertEqual(FIXED_ROWS + len(OPTION_PAGES[number].rows), len(layout.cursor_tiles))

    def test_window_shows_the_current_values(self):
        self.assertEqual(["PRESET", "CUSTOM", "PAGE", "1/3", "MESSAGE SPEED", "FAST", "DIALOG STYLE", "CLASSIC (NES)",
                          "FADE STYLE", "NES", "MUSIC", "ORCHESTRA", "LANGUAGE", "ENGLISH", "SCANLINES", "OFF",
                          "SCALING", "SMOOTH", "STATUS WINDOW", "NES", "SHOP PREVIEW", "OFF (NES)"],
                         page_texts(self.config))
        self.assertEqual(["PRESET", "CUSTOM", "PAGE", "2/3", "NPCS MAKE WAY", "ON", "STAIRS", "STEP ON",
                          "QUICK ACTION", "OFF (NES)", "ENCOUNTERS", "NES", "EXP/GOLD", "x1 (NES)"],
                         page_texts(self.config, 1))
        self.config.update(TEXT_SPEED='Slow', DIALOG_STYLE=MODERN, NPCS_MAKE_WAY=False, FADE_STYLE=FADE_STYLE_SMOOTH,
                           AUTO_STAIRS=False, AUTO_GRIND_STOP='ThreeQuartersHP', CHEAT_KEYS=True, REWIND=True,
                           STATUS_WINDOW='Always', ENCOUNTERS='Half', EXP_GOLD=4, RUN_BUTTON=True)
        self.assertEqual(["PRESET", "CUSTOM", "PAGE", "1/3", "MESSAGE SPEED", "SLOW", "DIALOG STYLE", "MODERN",
                          "FADE STYLE", "SMOOTH", "MUSIC", "ORCHESTRA", "LANGUAGE", "ENGLISH", "SCANLINES", "OFF",
                          "SCALING", "SMOOTH", "STATUS WINDOW", "ALWAYS", "SHOP PREVIEW", "OFF (NES)"],
                         page_texts(self.config))
        self.assertEqual(["PRESET", "CUSTOM", "PAGE", "2/3", "NPCS MAKE WAY", "OFF (NES)", "STAIRS", "NES",
                          "QUICK ACTION", "OFF (NES)", "ENCOUNTERS", "HALF", "EXP/GOLD", "x4"],
                         page_texts(self.config, 1))
        self.assertEqual(["PRESET", "CUSTOM", "PAGE", "3/3", "GAME SPEED", "OFF (NES)", "SAVE STATES", "OFF (NES)",
                          "REWIND", "ON", "AUTO-GRIND", "OFF (NES)", "GRIND STOP", "3/4 HP", "MENU SPEED", "NORMAL",
                          "CHEATS", "ON", "RUN BUTTON", "ON"], page_texts(self.config, 2))

    def test_the_window_is_the_same_size_on_every_page_and_fits_the_screen(self):
        self.assertEqual(MOST_ROWS + 2, OPTIONS_WINDOW.height)
        self.assertLessEqual(OPTIONS_WINDOW.y + OPTIONS_WINDOW.height, 15)  # 240 / 16 blocks high
        for number in range(len(OPTION_PAGES)):
            self.assertEqual(OPTIONS_WINDOW, options_layout(self.config, number).window)

    def test_every_text_fits_the_window(self):
        # window_tiles raises ValueError for text outside the window
        from src.window_renderer import window_tiles
        for choice in range(3):
            for row in OPTION_ROWS:
                self.config[row.config_key] = row.values[choice % len(row.values)]
            # 한국어 is drawn in the Korean font (src/translated_window.py), not in NES tiles: see
            # tests/test_korean_windows.py
            self.config['LANGUAGE'] = 'English'
            for number in range(len(OPTION_PAGES)):
                window_tiles(options_layout(self.config, number))

    def test_each_text_is_in_the_catalog(self):
        texts = overlay_texts()
        for number in range(len(OPTION_PAGES)):
            layout = options_layout(self.config, number)
            for text in (layout.title, *layout.texts):
                if '/' not in text.text or text.text == "3/4 HP":  # the page number isn't translated
                    self.assertIn(text.text, texts)

    def test_each_row_changes_its_setting_with_a_sound(self):
        for row in OPTION_ROWS:
            with self.subTest(row.label):
                self.config.update(DEFAULTS)
                presses_to_row = down_to(row.label)
                # each page turn has the menu button sound too
                self.assertEqual(presses_to_row.count(K_i) + 1, self.run_overlay(*presses_to_row, K_RIGHT, K_u))
                expected = {**DEFAULTS, row.config_key: row.values[1]}
                self.assertEqual(expected, own_settings(self.config))
                # what the next save keeps (CommandMenu.save)
                self.assertEqual(options_from_config(expected), options_from_config(self.config))

    def test_grind_stop_goes_round_all_three(self):
        settings = []
        for _ in range(3):
            self.run_overlay(*down_to("GRIND STOP"), K_RIGHT, K_u)
            settings.append(self.config['AUTO_GRIND_STOP'])
        self.assertEqual(['HalfHP', 'ThreeQuartersHP', 'RedHP'], settings)
        self.run_overlay(*down_to("GRIND STOP"), K_LEFT, K_u)
        self.assertEqual('ThreeQuartersHP', self.config['AUTO_GRIND_STOP'])

    def test_message_speed_goes_round_all_three(self):
        speeds = []
        for _ in range(3):
            self.run_overlay(*down_to("MESSAGE SPEED"), K_RIGHT, K_u)
            speeds.append(self.config['TEXT_SPEED'])
        self.assertEqual(['Normal', 'Slow', 'Fast'], speeds)
        self.run_overlay(*down_to("MESSAGE SPEED"), K_LEFT, K_u)
        self.assertEqual('Slow', self.config['TEXT_SPEED'])

    def test_left_right_and_a_all_change_the_value(self):
        for change in (K_LEFT, K_RIGHT, K_k, K_RETURN):
            with self.subTest(key=pygame.key.name(change)):
                self.config['AUTO_STAIRS'] = True
                self.run_overlay(*down_to("STAIRS"), change, K_u)
                self.assertFalse(self.config['AUTO_STAIRS'])
        # and back again
        self.assertEqual(3, self.run_overlay(*down_to("STAIRS"), K_RIGHT, K_LEFT, K_u))
        self.assertFalse(self.config['AUTO_STAIRS'])

    def test_cursor_stops_at_the_edges(self):
        # up from PRESET stays on it (right there: CUSTOM to NES); down past the last row stays on the last (SHOP
        # PREVIEW, which right turns from OFF to ON)
        self.run_overlay(K_UP, K_RIGHT, *(K_DOWN,) * (MOST_ROWS + 1), K_RIGHT, K_u)
        self.assertEqual({**DEFAULTS, **preset_values(PRESET_NES), 'SHOP_PREVIEW': True},
                         own_settings(self.config))

    def test_b_esc_select_and_tab_close_it(self):
        for close in (K_j, K_ESCAPE, K_u, K_TAB):
            with self.subTest(key=pygame.key.name(close)):
                self.assertEqual(0, self.run_overlay(close))
                self.assertEqual(DEFAULTS, own_settings(self.config))

    def test_the_change_applies_at_once(self):
        # the game reads the config it's in: the next stairs step, NPC bump, dialog and fade use it
        self.run_overlay(*down_to("STAIRS"), K_RIGHT, K_u)
        self.assertFalse(self.game.auto_stairs)
        self.assertIs(self.game.config, self.config)

    def test_saved_and_loaded_with_the_adventure_log(self):
        import json
        import tempfile
        for row in OPTION_ROWS:
            self.run_overlay(*down_to(row.label), K_RIGHT, K_u)
        changed = own_settings(self.config)
        self.assertEqual({row.config_key: row.values[1] for row in OPTION_ROWS}, changed)
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.game.cmd_menu.directories.save_dir = tmp_dir
            self.game.player.adventure_log = 2
            self.game.cmd_menu.save()
            with open(os.path.join(tmp_dir, 'save_slot_2.json')) as save_file:
                save = json.load(save_file)
        self.assertLessEqual({switch.save_key for switch in SWITCHES}, set(save))
        loaded = new_game()
        with patch.object(loaded.map_mgr, 'change_map'):
            loaded.load_game(save)
        # the language and the display filters are the player's, kept in the global settings (src/settings.py)
        self.assertEqual({**changed, 'LANGUAGE': 'English', 'SCANLINES': False, 'SCALING': 'Smooth'},
                         own_settings(loaded.game_state.config))
        # The language is the player's, kept in the global settings (src/settings.py), not the adventure's
        self.assertEqual(('Korean', True, SCALING_PIXEL_PERFECT),
                         (self.config['LANGUAGE'], self.config['SCANLINES'], self.config['SCALING']))
        self.assertEqual(('English', False, SCALING_SMOOTH), (loaded.game_state.config['LANGUAGE'],
                                                              loaded.game_state.config['SCANLINES'],
                                                              loaded.game_state.config['SCALING']))


class TestPages(OverlayTestCase):

    def shown_pages(self, *keys):
        """The page shown after each press (and before the first)."""
        overlay = OptionsOverlay(self.game)
        pages = []
        with patch.object(OptionsOverlay, 'draw', autospec=True,
                          side_effect=lambda shown, *_args: pages.append((shown.page, shown.index))), \
                patch('src.selection.event.get', side_effect=presses(*keys, K_u)), \
                patch.object(self.game.sound, 'play_sound'):
            overlay.run()
        return pages

    def last_page(self, *keys):
        overlay = OptionsOverlay(self.game)
        with patch('src.selection.event.get', side_effect=presses(*keys, K_u)), \
                patch.object(self.game.sound, 'play_sound'):
            overlay.run()
        return overlay.page, overlay.index

    def test_page_row_turns_the_page_both_ways_going_round(self):
        self.assertEqual((1, 1), self.last_page(K_DOWN, K_RIGHT))
        self.assertEqual((2, 1), self.last_page(K_DOWN, K_RIGHT, K_k))
        self.assertEqual((0, 1), self.last_page(K_DOWN, K_RIGHT, K_RIGHT, K_RIGHT))
        self.assertEqual((2, 1), self.last_page(K_DOWN, K_LEFT))

    def test_start_and_page_down_turn_to_the_next_page_and_page_up_to_the_previous_from_any_row(self):
        self.assertEqual((1, 3), self.last_page(K_DOWN, K_DOWN, K_DOWN, K_i))
        self.assertEqual((1, 0), self.last_page(K_PAGEDOWN))
        self.assertEqual((2, 0), self.last_page(K_PAGEUP))

    def test_the_cursor_goes_to_a_shorter_pages_last_row(self):
        # the CONTROLS page's last row (CHEATS) is lower than any row of the GAMEPLAY page
        last = FIXED_ROWS + len(OPTION_PAGES[2].rows) - 1
        self.assertEqual((1, FIXED_ROWS + len(OPTION_PAGES[1].rows) - 1),
                         self.last_page(K_i, K_i, *(K_DOWN,) * last, K_PAGEUP))

    def test_each_page_is_drawn(self):
        pages = {page for page, _index in self.shown_pages(K_i, K_i)}
        self.assertEqual({0, 1, 2}, pages)

    def test_turning_the_page_changes_no_setting(self):
        self.assertEqual(3, self.run_overlay(K_DOWN, K_RIGHT, K_i, K_PAGEUP, K_u))
        self.assertEqual(DEFAULTS, own_settings(self.config))


class TestPreset(OverlayTestCase):

    def test_the_presets(self):
        self.assertEqual({'DIALOG_STYLE': CLASSIC, 'FADE_STYLE': FADE_STYLE_NES, 'ORCHESTRA_MUSIC_ENABLED': False,
                          'STATUS_WINDOW': 'NES', 'NPCS_MAKE_WAY': False, 'AUTO_STAIRS': False, 'QUICK_ACTION': False,
                          'ENCOUNTERS': 'NES', 'EXP_GOLD': 1, 'GAME_SPEED_KEYS': False, 'SAVE_STATES': False,
                          'REWIND': False, 'AUTO_GRIND': False, 'AUTO_GRIND_STOP': 'RedHP', 'MENU_SPEED': NORMAL,
                          'CHEAT_KEYS': False, 'RUN_BUTTON': False, 'SHOP_PREVIEW': False}, preset_values(PRESET_NES))
        # MODERN: every convenience but the cheats; the number of fights and what they give stay the NES's
        self.assertEqual({'DIALOG_STYLE': CLASSIC, 'FADE_STYLE': FADE_STYLE_NES, 'ORCHESTRA_MUSIC_ENABLED': True,
                          'STATUS_WINDOW': 'Always', 'NPCS_MAKE_WAY': True, 'AUTO_STAIRS': True, 'QUICK_ACTION': True,
                          'ENCOUNTERS': 'NES', 'EXP_GOLD': 1, 'GAME_SPEED_KEYS': True, 'SAVE_STATES': True,
                          'REWIND': True, 'AUTO_GRIND': True, 'AUTO_GRIND_STOP': 'RedHP', 'MENU_SPEED': NORMAL,
                          'CHEAT_KEYS': False, 'RUN_BUTTON': True, 'SHOP_PREVIEW': True}, preset_values(PRESET_MODERN))
        # the message speed is the NES's own setting, and the language the player's: no preset changes them
        self.assertNotIn('TEXT_SPEED', [row.config_key for row in PRESET_ROWS])
        for config_key in ('LANGUAGE', 'SCANLINES', 'SCALING'):
            self.assertNotIn(config_key, [row.config_key for row in PRESET_ROWS])

    def test_menu_speed_is_normal_in_both_presets_so_follow_game_is_custom(self):
        # the NES has only 1x, so NORMAL is as faithful as FOLLOW GAME: both presets keep the menus at NORMAL
        self.config.update(preset_values(PRESET_MODERN))
        self.assertEqual(PRESET_MODERN, current_preset(self.config))
        self.config['MENU_SPEED'] = FOLLOW
        self.assertEqual(PRESET_CUSTOM, current_preset(self.config))

    def test_a_new_quest_keeps_what_the_game_already_had(self):
        # The conveniences there before the switches start on, as they always did; a new quest is CUSTOM, and the NES
        # preset switches them all off
        from src.options_screen import DEFAULT_OPTIONS, apply_options
        config = {}
        apply_options(config, DEFAULT_OPTIONS)
        nes = preset_values(PRESET_NES)
        differences = {config_key for config_key, value in nes.items() if config[config_key] != value}
        self.assertEqual({'ORCHESTRA_MUSIC_ENABLED', 'AUTO_STAIRS', 'NPCS_MAKE_WAY', 'QUICK_ACTION', 'GAME_SPEED_KEYS',
                          'SAVE_STATES', 'REWIND', 'AUTO_GRIND', 'CHEAT_KEYS', 'SHOP_PREVIEW'}, differences)
        self.assertEqual(PRESET_CUSTOM, current_preset(config))

    def test_an_older_save_loads_with_them_on(self):
        from src.options_screen import options_from_save
        options = options_from_save({'Name': 'Ed'})
        self.assertEqual((True, True, True, True, True, True, True),
                         (options.orchestra_music, options.game_speed_keys, options.save_states, options.rewind,
                          options.auto_grind, options.cheat_keys, options.quick_action))

    def test_preset_sets_every_row_at_once(self):
        self.assertEqual(1, self.run_overlay(K_RIGHT, K_u))  # CUSTOM -> NES (the first)
        self.assertEqual(PRESET_NES, current_preset(self.config))
        self.assertEqual({**DEFAULTS, **preset_values(PRESET_NES)}, own_settings(self.config))
        self.run_overlay(K_RIGHT, K_u)
        self.assertEqual(PRESET_MODERN, current_preset(self.config))
        self.assertEqual({**DEFAULTS, **preset_values(PRESET_MODERN)}, own_settings(self.config))
        self.assertEqual('Fast', self.config['TEXT_SPEED'])

    def test_a_row_that_differs_shows_custom(self):
        self.config.update(preset_values(PRESET_NES))
        self.assertEqual(["PRESET", "NES"], page_texts(self.config)[:2])
        self.run_overlay(*down_to("REWIND"), K_RIGHT, K_u)
        self.assertEqual(PRESET_CUSTOM, current_preset(self.config))
        self.assertEqual(["PRESET", "CUSTOM"], page_texts(self.config, 2)[:2])
        # and changing it back to the preset's value shows the preset again
        self.run_overlay(*down_to("REWIND"), K_RIGHT, K_u)
        self.assertEqual(["PRESET", "NES"], page_texts(self.config)[:2])

    def test_preset_goes_back_to_the_last_custom_values(self):
        custom = own_settings(self.config)  # DEFAULTS: neither preset
        # CUSTOM -> NES -> MODERN -> CUSTOM, all in one go
        self.run_overlay(K_RIGHT, K_RIGHT, K_RIGHT, K_u)
        self.assertEqual(custom, own_settings(self.config))
        # and left goes the other way round: CUSTOM -> MODERN
        self.run_overlay(K_LEFT, K_u)
        self.assertEqual(PRESET_MODERN, current_preset(self.config))

    def test_without_custom_values_the_preset_goes_between_nes_and_modern(self):
        self.config.update(preset_values(PRESET_NES))
        self.run_overlay(K_RIGHT, K_RIGHT, K_u)
        self.assertEqual(PRESET_NES, current_preset(self.config))

    def test_a_row_changed_in_the_same_run_is_the_custom_values_to_go_back_to(self):
        self.config.update(preset_values(PRESET_NES))
        self.run_overlay(*down_to("STAIRS"), K_RIGHT, *(K_UP,) * 10, K_RIGHT, K_RIGHT, K_RIGHT, K_u)
        self.assertEqual({**preset_values(PRESET_NES), 'AUTO_STAIRS': True},
                         {config_key: self.config[config_key] for config_key in preset_values(PRESET_NES)})

    def test_presets_switch_the_music_and_the_speed_keys_at_once(self):
        with patch.object(self.game, 'apply_option', wraps=self.game.apply_option) as apply_option:
            self.run_overlay(K_RIGHT, K_RIGHT, K_u)  # CUSTOM -> NES -> MODERN
        applied = {call.args[0] for call in apply_option.call_args_list}
        self.assertIn('ORCHESTRA_MUSIC_ENABLED', applied)
        self.assertIn('GAME_SPEED_KEYS', applied)
        from src.waiting import speed_keys_enabled
        self.assertTrue(speed_keys_enabled())


class TestSwitches(OverlayTestCase):
    """The conveniences that act on a key (#409, #437): off, their keys do nothing."""

    def press(self, pressed_key):
        self.game.handle_keypresses(key(pressed_key))

    def set_switch(self, label, on):
        if self.config[row_named(label).config_key] != on:
            self.run_overlay(*down_to(label), K_RIGHT, K_u)
        self.assertEqual(on, self.config[row_named(label).config_key])

    def test_game_speed(self):
        from src.waiting import game_speed, handle_speed_key, reset_game_speed
        self.addCleanup(reset_game_speed)
        self.set_switch("GAME SPEED", False)
        with patch.object(self.game, 'draw_temporary_text') as draw_temporary_text:
            self.press(pygame.K_3)
        draw_temporary_text.assert_not_called()
        self.assertEqual(1, game_speed())
        # in the other loops too, where the key is still taken out (so it's never "any key")
        self.assertTrue(handle_speed_key(key(pygame.K_4)))
        self.assertEqual(1, game_speed())
        self.set_switch("GAME SPEED", True)
        with patch.object(self.game, 'draw_temporary_text'):
            self.press(pygame.K_3)
        self.assertEqual(4, game_speed())
        # switching it off goes back to normal speed
        self.set_switch("GAME SPEED", False)
        self.assertEqual(1, game_speed())

    def test_auto_grind(self):
        self.set_switch("AUTO-GRIND", False)
        self.press(pygame.K_g)
        self.assertFalse(self.game.auto_grind_requested)
        self.set_switch("AUTO-GRIND", True)
        with patch.object(self.game, 'start_auto_grind') as start_auto_grind:
            self.press(pygame.K_g)
        start_auto_grind.assert_called_once()

    def test_cheats(self):
        self.set_switch("CHEATS", False)
        with patch.object(self.game, 'draw_temporary_text') as draw_temporary_text:
            self.press(pygame.K_F4)
            self.press(pygame.K_F9)
        draw_temporary_text.assert_not_called()
        self.assertEqual((False, False), (self.game.auto_battle, self.game.invulnerable))
        self.set_switch("CHEATS", True)
        with patch.object(self.game, 'draw_temporary_text'):
            self.press(pygame.K_F4)
            self.press(pygame.K_F9)
        self.assertEqual((True, True), (self.game.auto_battle, self.game.invulnerable))
        # switching them off switches both off
        self.set_switch("CHEATS", False)
        self.assertEqual((False, False), (self.game.auto_battle, self.game.invulnerable))

    def test_quick_action(self):
        self.game.player.current_tile = 'TREASURE_BOX'
        self.set_switch("QUICK ACTION", True)
        with patch.object(self.game.cmd_menu, 'take') as take, patch.object(self.game.drawer,
                                                                             'draw_hovering_stats_window'):
            self.press(K_RETURN)
        take.assert_called_once()
        self.assertFalse(self.game.cmd_menu_requested)
        # off, Enter is the A button on the map, as everywhere else: it opens the COMMAND window
        self.set_switch("QUICK ACTION", False)
        with patch.object(self.game.cmd_menu, 'take') as take, \
                patch.object(self.game.movement, 'resolve_pending_freezes'):
            self.press(K_RETURN)
        take.assert_not_called()
        self.assertTrue(self.game.cmd_menu_requested)

    def test_music(self):
        directories = self.game.directories
        self.assertTrue(self.config['ORCHESTRA_MUSIC_ENABLED'])
        self.assertIn('orchestra', self.game.current_map.music_file_path)
        with patch.object(self.game.music_player, 'load_and_play_music') as load_and_play_music:
            self.set_switch("MUSIC", False)
        # the map's music starts again, from the NES set, and every music path after it is from that set
        load_and_play_music.assert_called_once_with(directories.tantegel_castle_throne_room_music)
        self.assertIn(os.path.join('music', 'NES'), self.game.current_map.music_file_path)
        self.assertIn(os.path.join('music', 'NES'), self.game.battle_ctrl.directories.overworld_music)
        self.assertIn(os.path.join('music', 'NES'), map_lookup['Alefgard'](self.config).music_file_path)
        with patch.object(self.game.music_player, 'load_and_play_music'):
            self.set_switch("MUSIC", True)
        self.assertIn('orchestra', self.game.current_map.music_file_path)

    def test_save_states_and_rewind_have_switches(self):
        for label in ("SAVE STATES", "REWIND"):
            with self.subTest(label):
                self.set_switch(label, True)
                self.set_switch(label, False)

    def test_new_game_follows_the_switches_in_the_config(self):
        from src.waiting import reset_game_speed, speed_keys_enabled
        self.addCleanup(reset_game_speed)
        self.assertFalse(speed_keys_enabled())
        new_game(GAME_SPEED_KEYS=True)
        self.assertTrue(speed_keys_enabled())

    def test_loading_a_log_applies_its_switches(self):
        from src.waiting import reset_game_speed, speed_keys_enabled
        self.addCleanup(reset_game_speed)
        self.game.invulnerable = True
        save = {'Name': 'Ed', 'Experience': 0, 'Gold': 0, 'Inventory': [], 'GameSpeedKeys': True, 'CheatKeys': False}
        with patch.object(self.game.map_mgr, 'change_map'):
            self.game.load_game(save)
        self.assertTrue(speed_keys_enabled())
        self.assertFalse(self.game.invulnerable)


class TestDevOnly(TestCase):
    """#437: the frame recorder (F8) and the debug keys (F5-F7) are only in dev builds (dev_config's DEBUG_KEYS)."""

    def test_prod_has_no_debug_keys(self):
        from src.config.dev_config import dev_config
        from src.config.prod_config import prod_config
        self.assertFalse(prod_config['DEBUG_KEYS'])
        self.assertTrue(dev_config['DEBUG_KEYS'])

    def test_prod_starts_with_every_key_convenience_as_it_was(self):
        # on: the speed keys, save states, rewind, auto-grind, F4/F9 and the Enter shortcut worked before the switches
        from src.config.prod_config import prod_config
        for switch in SWITCHES:
            if switch.config_key in ('ENCOUNTERS', 'EXP_GOLD', 'RUN_BUTTON', 'STATUS_WINDOW'):
                # new options: the NES's
                self.assertIn(switch.default, (False, 'NES', 1), switch.config_key)
            else:
                self.assertTrue(prod_config[switch.config_key], switch.config_key)
            self.assertEqual(switch.default, prod_config[switch.config_key], switch.config_key)

    def test_a_game_without_debug_keys_has_no_debug_tools(self):
        pygame.init()
        game = new_game(DEBUG_KEYS=False)
        self.assertIsNone(game.debug_tools)


class TestStairsHasNoKey(OverlayTestCase):

    def test_f2_no_longer_toggles_the_stairs_setting(self):
        """F2 was the STAIRS key; it's kept for the save states now, so STAIRS is only in the overlay."""
        with patch.object(self.game, 'draw_temporary_text') as draw_temporary_text:
            self.game.handle_keypresses(key(K_F2))
        self.assertTrue(self.game.auto_stairs)
        draw_temporary_text.assert_not_called()

    def test_the_overlay_changes_the_stairs_setting(self):
        self.run_overlay(*down_to("STAIRS"), K_RIGHT, K_u)
        self.assertFalse(self.game.auto_stairs)
        self.assertFalse(options_from_config(self.config).auto_stairs)
        texts = page_texts(self.config, page_of("STAIRS"))
        self.assertEqual("NES", texts[texts.index("STAIRS") + 1])


class TestStairs(OverlayTestCase):
    """STAIRS: STEP ON takes stairs by stepping onto them, NES only with the STAIRS command (Bank03 CheckStairs)."""

    GRAVE_STAIRS = (3, 12)  # Garin's Grave B2's stairs up

    def stand_on(self, map_name, coordinates):
        self.game.change_map(map_lookup[map_name](self.game.config), destination_coordinates=coordinates)
        self.game.player.row, self.game.player.column = coordinates
        self.game.tiles_moved_since_spawn = 5  # past a new map's wait for stairs

    def warps(self):
        with patch.object(self.game.map_mgr, 'process_warp') as process_warp:
            self.game.handle_warps()
        return process_warp

    def test_step_on_takes_the_stairs(self):
        self.stand_on('GarinsGraveB2', self.GRAVE_STAIRS)
        self.warps().assert_called_once_with(self.game.current_map.staircases[self.GRAVE_STAIRS])

    def test_nes_does_not_take_stairs_stepped_onto(self):
        self.config['AUTO_STAIRS'] = False
        self.stand_on('GarinsGraveB2', self.GRAVE_STAIRS)
        self.warps().assert_not_called()
        self.warps().assert_not_called()  # nor standing on them, frame after frame

    def test_stairs_command_takes_them_in_both_modes(self):
        for auto_stairs in (True, False):
            with self.subTest(auto_stairs=auto_stairs):
                self.config['AUTO_STAIRS'] = auto_stairs
                self.stand_on('GarinsGraveB2', self.GRAVE_STAIRS)
                self.game.player.current_tile = 'BRICK_STAIR_UP'
                destination = self.game.current_map.staircases[self.GRAVE_STAIRS]['map']
                with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text:
                    self.game.cmd_menu.stairs()
                show_text.assert_not_called()
                self.assertEqual(destination, self.game.current_map.identifier)

    def test_nes_still_steps_into_towns_and_out_of_them(self):
        # NES CheckBlockDmg: a town, castle or cave block changes maps when stepped onto (CalcNextMap), and so does
        # walking off a town's edge (CheckMapExit); only stair blocks wait for the STAIRS command
        self.config['AUTO_STAIRS'] = False
        alefgard = map_lookup['Alefgard'](self.game.config)
        entrance = next(location for location in alefgard.staircases
                        if alefgard.layout[location[0]][location[1]] not in STAIR_DIRECTIONS)
        brecconary = map_lookup['Brecconary'](self.game.config)
        gate = next(location for location, staircase in brecconary.staircases.items() if staircase['map'] == 'Alefgard')
        for map_name, location in (('Alefgard', entrance), ('Brecconary', gate)):
            with self.subTest(map_name):
                self.stand_on(map_name, location)
                self.warps().assert_called_once()

    def shrine_stairs(self):
        alefgard = map_lookup['Alefgard'](self.game.config)
        return next(location for location in alefgard.staircases
                    if alefgard.layout[location[0]][location[1]] == GRASS_STAIR_DOWN)

    def test_nes_does_not_step_into_the_overworld_shrines(self):
        # GRASS_STAIR_DOWN, the overworld shrine entrances, are BLK_STAIR_DN on the NES (Bank00 WrldBlkConvTbl
        # index $0C), and CheckBlockDmg only changes maps for town, cave and castle blocks, so they wait for STAIRS
        self.config['AUTO_STAIRS'] = False
        self.stand_on('Alefgard', self.shrine_stairs())
        self.warps().assert_not_called()

    def test_step_on_steps_into_the_overworld_shrines(self):
        self.stand_on('Alefgard', self.shrine_stairs())
        self.warps().assert_called_once()

    def test_stairs_command_takes_the_overworld_shrines(self):
        self.config['AUTO_STAIRS'] = False
        shrine = self.shrine_stairs()
        self.stand_on('Alefgard', shrine)
        self.game.player.current_tile = 'GRASS_STAIR_DOWN'
        destination = self.game.current_map.staircases[shrine]['map']
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box') as show_text:
            self.game.cmd_menu.stairs()
        show_text.assert_not_called()
        self.assertEqual(destination, self.game.current_map.identifier)


class TestNoGhosting(OverlayTestCase):
    """Closing the overlay puts the map frame back exactly (tests/test_character_redraw.py draws real frames)."""

    def make_game(self):
        with patch('src.game.SCALED', 0):
            game = new_game(NO_BLIT=False, START_MAP='TantegelCourtyard')
        game.game_state.enable_animate = True
        return game

    def test_closing_restores_the_map_frame(self):
        draw_frame(self.game)
        pygame.display.flip()
        before = pygame.image.tobytes(self.game.screen, 'RGB')
        shown = []
        real_update = pygame.display.update

        def update(*args, **kwargs):
            shown.append(pygame.image.tobytes(self.game.screen, 'RGB'))
            return real_update(*args, **kwargs)

        with patch('src.options_overlay.display.update', side_effect=update):
            self.run_overlay(K_DOWN, K_RIGHT, K_UP, K_u)
        # while it was open, the screen was darkened with the window over it, and the change was shown
        self.assertTrue(shown)
        self.assertNotIn(before, shown[:-1])
        self.assertGreater(len(set(shown[:-1])), 1)
        # closed: exactly the frame it opened over, which is what was shown last
        self.assertEqual(before, pygame.image.tobytes(self.game.screen, 'RGB'))
        self.assertEqual(before, shown[-1])

    def test_overlay_darkens_the_map_behind_the_window(self):
        draw_frame(self.game)
        corner = self.game.screen.get_at((2, self.game.screen.get_height() - 3))
        frames = []
        with patch('src.options_overlay.display.update',
                   side_effect=lambda *args: frames.append(self.game.screen.get_at((2, self.game.screen.get_height()
                                                                                    - 3)))):
            self.run_overlay(K_u)
        darkened = frames[0]
        self.assertTrue(all(dark <= light for dark, light in zip(darkened[:3], corner[:3])))
        if any(corner[:3]):
            self.assertLess(sum(darkened[:3]), sum(corner[:3]))
