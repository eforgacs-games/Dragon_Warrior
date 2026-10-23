"""The options overlay (src/options_overlay.py): SELECT or Tab on the map, this game's own settings changed in play,
and the STAIRS setting (AUTO_STAIRS) it shares with F2."""
import os
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from pygame import K_DOWN, K_ESCAPE, K_F2, K_LEFT, K_RETURN, K_RIGHT, K_TAB, K_UP, K_j, K_k, K_u, KEYDOWN
from pygame.event import Event

from src.config.test_config import test_config
from src.map_layouts import GRASS_STAIR_DOWN
from src.maps import STAIR_DIRECTIONS, map_lookup
from src.options_overlay import OPTION_ROWS, OPTIONS_TITLE, OptionsOverlay, options_layout
from src.options_screen import CLASSIC, MODERN, options_from_config
from src.visual_effects import FADE_STYLE_NES, FADE_STYLE_SMOOTH
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


def new_game(**overrides):
    # A copy of test_config, so the settings these tests change don't leak into other tests
    return helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True,
                             'DIALOG_STYLE': CLASSIC, 'NPCS_MAKE_WAY': True, 'FADE_STYLE': FADE_STYLE_NES,
                             'AUTO_STAIRS': True, **overrides})


def own_settings(config):
    return config['DIALOG_STYLE'], config['NPCS_MAKE_WAY'], config['FADE_STYLE'], config['AUTO_STAIRS']


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

    def test_rows(self):
        self.assertEqual("OPTIONS", OPTIONS_TITLE.text)
        self.assertEqual([("DIALOG STYLE", 'DIALOG_STYLE', ("CLASSIC (NES)", "MODERN")),
                          ("NPCS MAKE WAY", 'NPCS_MAKE_WAY', ("ON", "OFF (NES)")),
                          ("FADE STYLE", 'FADE_STYLE', ("NES", "SMOOTH")),
                          ("STAIRS", 'AUTO_STAIRS', ("STEP ON", "NES"))],
                         [(row.label, row.config_key, row.value_labels) for row in OPTION_ROWS])

    def test_window_shows_the_current_values(self):
        texts = [text.text for text in options_layout(self.config).texts]
        self.assertEqual(["DIALOG STYLE", "CLASSIC (NES)", "NPCS MAKE WAY", "ON", "FADE STYLE", "NES", "STAIRS",
                          "STEP ON"], texts)
        self.config.update(DIALOG_STYLE=MODERN, NPCS_MAKE_WAY=False, FADE_STYLE=FADE_STYLE_SMOOTH, AUTO_STAIRS=False)
        texts = [text.text for text in options_layout(self.config).texts]
        self.assertEqual(["DIALOG STYLE", "MODERN", "NPCS MAKE WAY", "OFF (NES)", "FADE STYLE", "SMOOTH", "STAIRS",
                          "NES"], texts)

    def test_every_text_fits_the_window(self):
        # window_tiles raises ValueError for text outside the window
        from src.window_renderer import window_tiles
        for values in ((CLASSIC, True, FADE_STYLE_NES, True), (MODERN, False, FADE_STYLE_SMOOTH, False)):
            self.config.update(zip(('DIALOG_STYLE', 'NPCS_MAKE_WAY', 'FADE_STYLE', 'AUTO_STAIRS'), values))
            window_tiles(options_layout(self.config))

    def test_each_row_changes_its_setting_with_a_sound(self):
        cases = ((K_RIGHT, (MODERN, True, FADE_STYLE_NES, True)),
                 (K_DOWN, K_RIGHT, (CLASSIC, False, FADE_STYLE_NES, True)),
                 (K_DOWN, K_DOWN, K_RIGHT, (CLASSIC, True, FADE_STYLE_SMOOTH, True)),
                 (K_DOWN, K_DOWN, K_DOWN, K_RIGHT, (CLASSIC, True, FADE_STYLE_NES, False)))
        for *keys, expected in cases:
            with self.subTest(expected=expected):
                self.config.update(DIALOG_STYLE=CLASSIC, NPCS_MAKE_WAY=True, FADE_STYLE=FADE_STYLE_NES,
                                   AUTO_STAIRS=True)
                self.assertEqual(1, self.run_overlay(*keys, K_u))
                self.assertEqual(expected, own_settings(self.config))
                # what the next save keeps (CommandMenu.save)
                options = options_from_config(self.config)
                self.assertEqual(expected, (options.dialog_style, options.npcs_make_way, options.fade_style,
                                            options.auto_stairs))

    def test_left_right_and_a_all_change_the_value(self):
        for change in (K_LEFT, K_RIGHT, K_k, K_RETURN):
            with self.subTest(key=pygame.key.name(change)):
                self.config['AUTO_STAIRS'] = True
                self.run_overlay(K_DOWN, K_DOWN, K_DOWN, change, K_u)
                self.assertFalse(self.config['AUTO_STAIRS'])
        # and back again
        self.assertEqual(2, self.run_overlay(K_DOWN, K_DOWN, K_DOWN, K_RIGHT, K_LEFT, K_u))
        self.assertFalse(self.config['AUTO_STAIRS'])

    def test_cursor_stops_at_the_edges(self):
        self.run_overlay(K_UP, K_RIGHT, K_DOWN, K_DOWN, K_DOWN, K_DOWN, K_DOWN, K_RIGHT, K_u)
        self.assertEqual((MODERN, True, FADE_STYLE_NES, False), own_settings(self.config))

    def test_b_esc_select_and_tab_close_it(self):
        for close in (K_j, K_ESCAPE, K_u, K_TAB):
            with self.subTest(key=pygame.key.name(close)):
                self.assertEqual(0, self.run_overlay(close))
                self.assertEqual((CLASSIC, True, FADE_STYLE_NES, True), own_settings(self.config))

    def test_the_change_applies_at_once(self):
        # the game reads the config it's in: the next stairs step, NPC bump, dialog and fade use it
        self.run_overlay(K_DOWN, K_DOWN, K_DOWN, K_RIGHT, K_u)
        self.assertFalse(self.game.auto_stairs)
        self.assertIs(self.game.config, self.config)

    def test_saved_and_loaded_with_the_adventure_log(self):
        import json
        import tempfile
        self.run_overlay(K_RIGHT, K_DOWN, K_RIGHT, K_DOWN, K_RIGHT, K_DOWN, K_RIGHT, K_u)
        changed = own_settings(self.config)
        self.assertEqual((MODERN, False, FADE_STYLE_SMOOTH, False), changed)
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.game.cmd_menu.directories.save_dir = tmp_dir
            self.game.player.adventure_log = 2
            self.game.cmd_menu.save()
            with open(os.path.join(tmp_dir, 'save_slot_2.json')) as save_file:
                save = json.load(save_file)
        loaded = new_game()
        with patch.object(loaded.map_mgr, 'change_map'):
            loaded.load_game(save)
        self.assertEqual(changed, own_settings(loaded.game_state.config))


class TestF2(OverlayTestCase):

    def test_f2_toggles_the_stairs_setting(self):
        with patch.object(self.game, 'draw_temporary_text') as draw_temporary_text:
            self.game.handle_keypresses(key(K_F2))
            self.assertFalse(self.game.auto_stairs)
            self.assertFalse(self.config['AUTO_STAIRS'])
            self.assertEqual("NES", options_layout(self.config).texts[-1].text)
            self.assertFalse(options_from_config(self.config).auto_stairs)
            draw_temporary_text.assert_called_with("Stairs: NES (STAIRS command)")
            self.game.handle_keypresses(key(K_F2))
            self.assertTrue(self.config['AUTO_STAIRS'])
            draw_temporary_text.assert_called_with("Stairs: STEP ON")

    def test_the_overlay_and_f2_change_the_same_setting(self):
        self.run_overlay(K_DOWN, K_DOWN, K_DOWN, K_RIGHT, K_u)
        with patch.object(self.game, 'draw_temporary_text'):
            self.game.handle_keypresses(key(K_F2))
        self.assertTrue(self.game.auto_stairs)


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

    def test_nes_steps_into_the_overworld_shrines(self):
        # GRASS_STAIR_DOWN, the overworld shrine entrances, are cave blocks on the NES (src/encounters.py
        # MAP_CHANGE_TILES), so they're stepped into whatever STAIRS is set to
        self.config['AUTO_STAIRS'] = False
        alefgard = map_lookup['Alefgard'](self.game.config)
        shrine = next(location for location in alefgard.staircases
                      if alefgard.layout[location[0]][location[1]] == GRASS_STAIR_DOWN)
        self.stand_on('Alefgard', shrine)
        self.warps().assert_called_once()


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
