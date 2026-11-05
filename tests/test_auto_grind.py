"""Auto-grind (src/auto_grind.py): G on the map, driven by the virtual joypad (src/virtual_joypad.py). Not NES."""
import os
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from pygame import K_2, K_DOWN, K_F2, K_LCTRL, K_RIGHT, K_UP, K_g, K_j, K_k, KEYDOWN, KMOD_CTRL, KMOD_LCTRL
from pygame.event import Event

from data.text.dialog_lookup_table import DialogLookup
from src.auto_grind import ALL_DIRECTION_KEYS, GRIND_STOP_DANGER, GRIND_STOP_HALF_HP, GRIND_STOP_RED_HP, \
    GRIND_STOP_THREE_QUARTERS_HP, UNSAFE_TILES, AutoGrind, StopReason, at_grind_stop_hp
from src.battle import Battle
from src.battle_controller import BattleController, BattleOutcome
from src.config.test_config import test_config
from src.controls import Binding, Controls, reset_controls, set_controls
from src.direction import Direction
from src.enemy_lookup import enemy_string_lookup
from src.game_options import AUTO_HEAL_KEEP_ONE, AUTO_HEAL_OFF, AUTO_HEAL_ON
from src.grind_route import Exit, Leg
from src.grind_safety import worst_enemy_damage, worst_group_damage
from src.inn_trip import ATTEMPTS, COMMAND_STAIRS, STUCK_FRAMES, TripResult
from src.maps import map_lookup
from src.maps_functions import get_center_point
from src.random_streams import seed_all
from src.spells import Spell
from src.virtual_joypad import is_virtual
from src.waiting import MAP_CONTEXT, WINDOW_CONTEXT, game_speed, poll_virtual_joypad, set_game_speed, \
    virtual_joypad
from tests import helpers

# Grass by Tantegel Castle, whose gate is at (50, 51): the hero faces down, to (51, 44), more grass
GRASS = (50, 44)


def key(pressed_key, mod=0):
    return Event(KEYDOWN, key=pressed_key, mod=mod, unicode='', scancode=0)


def queued_keydowns():
    events = pygame.event.get(KEYDOWN)
    for current_event in events:
        pygame.event.post(current_event)
    return events


class Done(Exception):
    """Ends a headless run from inside the game's loops."""


class GrindTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()

    def setUp(self):
        pygame.event.clear()
        self.game = self.new_game()
        self.grind = self.game.auto_grind
        self.player = self.game.player
        self.addCleanup(self.cleanup)
        self.temporary_text = patch.object(self.game, 'draw_temporary_text').start()
        self.sound = patch.object(self.game.sound, 'play_sound').start()
        self.go_to('Alefgard', GRASS)

    def cleanup(self):
        self.grind.joypad.disconnect()
        patch.stopall()
        set_game_speed(1)
        pygame.event.clear()

    def new_game(self, **overrides):
        # A copy of test_config, so nothing these tests change leaks into other tests
        return helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True,
                                 'AUTO_GRIND_STOP': GRIND_STOP_RED_HP, 'AUTO_GRIND': True, 'GAME_SPEED_KEYS': True,
                                 **overrides})

    def go_to(self, map_name, coordinates, direction=Direction.DOWN.value):
        self.game.change_map(map_lookup[map_name](self.game.config), destination_coordinates=coordinates,
                             direction=direction)
        self.player.direction_value = direction

    def stand_on(self, coordinates):
        row, column = coordinates
        self.player.rect.center = get_center_point(column, row, self.game.tile_size)
        self.player.row, self.player.column = coordinates

    def start(self):
        self.assertTrue(self.grind.start())
        self.temporary_text.reset_mock()
        self.sound.reset_mock()


class TestThreshold(TestCase):

    def test_red_hp_is_the_nes_low_hp(self):
        # NES ChkLowHPPal: HP <= max HP / 4 + 1, where the windows turn red
        self.assertTrue(at_grind_stop_hp(26, 100, GRIND_STOP_RED_HP))
        self.assertFalse(at_grind_stop_hp(27, 100, GRIND_STOP_RED_HP))
        self.assertTrue(at_grind_stop_hp(4, 15, GRIND_STOP_RED_HP))
        self.assertFalse(at_grind_stop_hp(5, 15, GRIND_STOP_RED_HP))

    def test_half_and_three_quarters(self):
        self.assertTrue(at_grind_stop_hp(50, 100, GRIND_STOP_HALF_HP))
        self.assertFalse(at_grind_stop_hp(51, 100, GRIND_STOP_HALF_HP))
        self.assertTrue(at_grind_stop_hp(7, 15, GRIND_STOP_HALF_HP))
        self.assertTrue(at_grind_stop_hp(75, 100, GRIND_STOP_THREE_QUARTERS_HP))
        self.assertFalse(at_grind_stop_hp(76, 100, GRIND_STOP_THREE_QUARTERS_HP))
        self.assertTrue(at_grind_stop_hp(11, 15, GRIND_STOP_THREE_QUARTERS_HP))
        self.assertFalse(at_grind_stop_hp(12, 15, GRIND_STOP_THREE_QUARTERS_HP))

    def test_anything_else_is_red_hp(self):
        self.assertEqual(at_grind_stop_hp(26, 100, None), at_grind_stop_hp(26, 100, GRIND_STOP_RED_HP))


class TestStarting(GrindTestCase):

    def test_g_on_the_map_starts_it(self):
        self.game.handle_keypresses(key(K_g))
        for _ in range(32):  # once the hero and the NPCs are between steps (resolve_pending_freezes)
            if self.grind.active:
                break
            self.game.map_frame()
        self.assertTrue(self.grind.active)
        self.assertIs(self.grind.joypad, virtual_joypad())
        self.temporary_text.assert_called_with("Auto-grind on\n(G or any key to stop)")
        self.assertEqual((GRASS, (51, 44)), (self.grind.origin, self.grind.partner))

    def test_a_key_bound_with_a_modifier_needs_the_modifier(self):
        # AUTO GRIND on Ctrl+F2: plain F2 (LOAD 2) doesn't start it
        controls = Controls.defaults()
        self.assertTrue(controls.bind_key('AUTO_GRIND', 0, Binding(K_F2, KMOD_CTRL)))
        set_controls(controls)
        self.addCleanup(reset_controls)
        self.game.hotkeys.press_auto_grind(key(K_F2))
        self.assertFalse(self.game.auto_grind_requested or self.grind.active)
        self.game.hotkeys.press_auto_grind(key(K_F2, KMOD_LCTRL))
        self.assertTrue(self.game.auto_grind_requested or self.grind.active)

    def test_not_while_paused_or_a_window_is_open(self):
        self.game.paused = True
        self.game.handle_keypresses(key(K_g))
        self.assertFalse(self.game.auto_grind_requested)
        self.game.paused = False
        self.game.cmd_menu.launch_signaled = True
        self.game.handle_keypresses(key(K_g))
        self.assertFalse(self.game.auto_grind_requested)

    def test_not_in_towns_or_castles(self):
        for map_name in ('Brecconary', 'TantegelCourtyard', 'TantegelThroneRoom'):
            with self.subTest(map_name):
                current_map = map_lookup[map_name](self.game.config)
                self.go_to(map_name, current_map.initial_coordinates)
                self.temporary_text.reset_mock()
                self.assertFalse(self.grind.start())
                self.assertFalse(self.grind.active)
                self.temporary_text.assert_called_once_with("Auto-grind: no fights here")

    def test_not_with_battles_turned_off(self):
        # dev_config's NO_BATTLES: no step can start a fight, so there's nothing to grind
        self.game.game_state.config['NO_BATTLES'] = True
        self.addCleanup(self.game.game_state.config.__setitem__, 'NO_BATTLES', False)
        self.assertFalse(self.grind.start())
        self.assertFalse(self.grind.active)
        self.temporary_text.assert_called_once_with("Auto-grind: battles are off (NO_BATTLES)")

    def test_not_once_the_dragonlord_is_dead(self):
        self.game.story_flags.dragonlord_defeated = True
        self.assertFalse(self.grind.start())
        self.temporary_text.assert_called_once_with("Auto-grind: no fights here")

    def test_in_a_dungeon(self):
        current_map = map_lookup['GarinsGraveB1'](self.game.config)
        self.go_to('GarinsGraveB1', current_map.initial_coordinates)
        self.stand_on(self.grind.hero_cell())
        partner = self.grind.safe_partner(self.grind.hero_cell())
        self.assertEqual(partner is not None, self.grind.start())

    def test_not_with_no_safe_tile(self):
        with patch.object(AutoGrind, 'safe_tile', side_effect=lambda cell, check_characters=True: cell == GRASS):
            self.assertFalse(self.grind.start())
        self.assertFalse(self.grind.active)
        self.temporary_text.assert_called_once_with("Auto-grind: no safe tile to walk to")

    def test_not_with_hp_already_low(self):
        self.player.current_hp = self.player.max_hp // 4 + 1
        self.assertFalse(self.grind.start())
        self.temporary_text.assert_called_once_with("Auto-grind: HP is already low")


class TestSafeTiles(GrindTestCase):

    def assert_safe(self, cell):
        current_map = self.game.current_map
        row, column = cell
        tile = current_map.get_tile_by_value(current_map.layout[row][column])
        self.assertNotIn(tile, current_map.impassable_tiles)
        self.assertNotIn(tile, UNSAFE_TILES)
        self.assertNotIn(cell, current_map.staircases)
        self.assertFalse(current_map.is_step_warp(row, column))
        self.assertFalse(current_map.is_map_exit(row, column))

    def test_the_partner_is_always_safe(self):
        # Around Tantegel: grass, trees, hills, mountains, the castle, water and the swamp to the south-east
        current_map = self.game.current_map
        found = 0
        for row in range(38, 62):
            for column in range(38, 62):
                partner = self.grind.safe_partner((row, column))
                if partner is None:
                    continue
                found += 1
                with self.subTest(origin=(row, column), partner=partner):
                    self.assert_safe((row, column))
                    self.assert_safe(partner)
                    self.assertEqual(1, abs(partner[0] - row) + abs(partner[1] - column))
        self.assertGreater(found, 100)
        self.assertIsNone(self.grind.safe_partner((50, 51)))  # the castle itself
        self.assertFalse(self.grind.safe_tile((50, 51)))
        self.assertFalse(self.grind.safe_tile((55, 55)))  # swamp
        self.assertEqual('MARSH', current_map.get_tile_by_value(current_map.layout[55][55]))

    def test_swamp_force_field_and_stairs_are_unsafe(self):
        current_map = self.game.current_map
        for tile in ('MARSH', 'BARRIER', 'BRICK_STAIR_DOWN', 'GRASS_STAIR_DOWN'):
            with self.subTest(tile):
                with patch.object(current_map, 'get_tile_by_value', return_value=tile):
                    self.assertFalse(self.grind.safe_tile((51, 44)))
        self.assertTrue(self.grind.safe_tile((51, 44)))

    def test_looks_the_way_the_hero_faces_first(self):
        self.player.direction_value = Direction.UP.value
        self.assertEqual((49, 44), self.grind.safe_partner(GRASS))
        self.player.direction_value = Direction.LEFT.value
        self.assertEqual((50, 43), self.grind.safe_partner(GRASS))

    def test_not_onto_someone(self):
        someone = Mock(row=51, column=44, step_origin=None, step_destination=None)
        with patch.object(self.game.current_map, 'fixed_characters', [someone]):
            self.assertFalse(self.grind.safe_tile((51, 44)))
            self.assertNotEqual((51, 44), self.grind.safe_partner(GRASS))
        walking = Mock(row=52, column=44, step_origin=(52, 44), step_destination=(51, 44))
        with patch.object(self.game.current_map, 'roaming_characters', [walking]):
            self.assertFalse(self.grind.safe_tile((51, 44)))


class TestPacing(GrindTestCase):

    def test_holds_the_direction_to_the_other_tile(self):
        self.start()
        joypad = self.grind.joypad
        self.grind.update(joypad, MAP_CONTEXT)
        self.assertEqual({K_DOWN}, joypad.held)
        self.stand_on((51, 44))
        self.grind.update(joypad, MAP_CONTEXT)
        self.assertEqual({K_UP}, joypad.held)

    def test_walks_back_and_forth_through_the_movement_code(self):
        self.start()
        self.game.config['NO_BATTLES'] = True  # only once it's walking (it won't start with it): no fight interrupts
        cells = []
        real_count_step = self.game.step_triggers.count_step

        def count_step():
            cells.append(self.grind.hero_cell())
            real_count_step()
        clock = helpers.fake_game_clock()
        with patch.object(self.game.step_triggers, 'count_step', side_effect=count_step):
            for _ in range(1000):  # 6 steps of 16 frames, and the turns between them
                if len(cells) >= 6:
                    break
                clock.advance_frames()
                self.game.run_due_frames()
        self.assertEqual([(51, 44), GRASS] * 3, cells[:6])
        self.assertTrue(self.grind.active)

    def test_a_map_change_stops_it(self):
        self.start()
        self.go_to('Brecconary', map_lookup['Brecconary'](self.game.config).initial_coordinates)
        poll_virtual_joypad(MAP_CONTEXT)
        self.assertFalse(self.grind.active)
        self.assertEqual(StopReason.INTERRUPTED, self.grind.last_stop)
        self.assertEqual("Auto-grind stopped", self.grind.pending_message)


class TestVirtualJoypad(GrindTestCase):

    def test_taps_a_in_windows(self):
        self.start()
        poll_virtual_joypad(WINDOW_CONTEXT)
        self.assertIn(K_k, self.grind.joypad.held)
        presses = [current_event for current_event in queued_keydowns() if current_event.key == K_k]
        self.assertEqual(1, len(presses))
        self.assertTrue(is_virtual(presses[0]))

    def test_its_presses_never_reach_the_map(self):
        self.start()
        poll_virtual_joypad(WINDOW_CONTEXT)
        poll_virtual_joypad(MAP_CONTEXT)
        self.assertEqual([], [current_event for current_event in queued_keydowns() if current_event.key == K_k])
        self.assertNotIn(K_k, self.grind.joypad.held)

    def test_stopping_lets_go_and_drops_unread_presses(self):
        self.start()
        poll_virtual_joypad(WINDOW_CONTEXT)
        self.grind.stop(StopReason.HP_LOW)
        self.assertIsNone(virtual_joypad())
        self.assertEqual(set(), self.grind.joypad.held)
        self.assertEqual([], [current_event for current_event in queued_keydowns() if is_virtual(current_event)])


class TestKeys(GrindTestCase):

    def test_any_key_stops_it_and_is_used_up(self):
        for pressed_key in (K_k, K_g, K_UP, pygame.K_i, pygame.K_F4):
            with self.subTest(key=pygame.key.name(pressed_key)):
                pygame.event.clear()
                self.start()
                pygame.event.post(key(pressed_key))
                poll_virtual_joypad(WINDOW_CONTEXT)
                self.assertFalse(self.grind.active)
                self.assertEqual(StopReason.KEY, self.grind.last_stop)
                self.assertEqual([], [e for e in queued_keydowns() if e.key == pressed_key])
                self.sound.assert_called_once_with(self.game.directories.menu_button_sfx)
                self.assertEqual("Auto-grind stopped", self.grind.pending_message)
                self.grind.pending_message = None

    def test_g_on_the_map_stops_it(self):
        self.start()
        pygame.event.post(key(K_g))
        self.game.read_events()
        self.assertFalse(self.grind.active)
        self.assertFalse(self.game.auto_grind_requested)  # G doesn't start it again
        self.game.map_frame()
        self.temporary_text.assert_called_once_with("Auto-grind stopped")

    def test_the_speed_keys_do_not_stop_it(self):
        self.start()
        pygame.event.post(key(K_2))
        self.game.read_events()
        self.assertTrue(self.grind.active)
        self.assertEqual(2, game_speed())

    def test_the_zoom_keys_do_not_stop_it(self):
        self.start()
        pygame.event.post(key(K_LCTRL, mod=KMOD_CTRL))
        pygame.event.post(key(pygame.K_EQUALS, mod=KMOD_CTRL))
        poll_virtual_joypad(WINDOW_CONTEXT)
        self.assertTrue(self.grind.active)

    def test_a_key_pressed_as_the_battle_command_window_opens_still_stops_it(self):
        self.start()
        pygame.event.post(key(pygame.K_j))
        with patch.object(self.game.cmd_menu, 'window_drop_down_effect'), \
                patch.object(self.game.cmd_menu, 'covered_area'):
            self.game.battle_ctrl.open_command_window()
        self.assertFalse(self.grind.active)


class TestStops(GrindTestCase):

    def setUp(self):
        super().setUp()
        self.battle_line = patch.object(self.game.cmd_menu, 'show_line_in_dialog_box').start()
        self.start()

    def in_battle(self):
        self.game.cmd_menu.current_battle = MagicMock()

    def assert_stopped(self, reason, message=None):
        self.assertFalse(self.grind.active)
        self.assertEqual(reason, self.grind.last_stop)
        self.sound.assert_called_once_with(self.game.directories.menu_button_sfx)
        if message is not None:
            self.battle_line.assert_called_once_with(message + '\n', add_quotes=False, hide_arrow=True,
                                                     disable_sound=True, skip_text=True)

    def test_hp_low_at_the_start_of_a_turn(self):
        self.in_battle()
        self.grind.player_turn_starts()
        self.assertTrue(self.grind.active)
        self.player.current_hp = self.player.max_hp // 4 + 1
        self.grind.player_turn_starts()
        self.assert_stopped(StopReason.HP_LOW, "Auto-grind stopped: HP low")

    def test_a_safety_stop_turns_auto_battle_off(self):
        # Auto-battle (F4) would otherwise repeat the last command as soon as auto-grind lets go of the fight
        for reason, stop in ((StopReason.HP_LOW, self.lower_hp_at_turn_start),
                             (StopReason.ASLEEP, self.fall_asleep_at_turn_start),
                             (StopReason.STOPSPELL, self.grind.stopspell_hit),
                             (StopReason.SCRIPTED_FIGHT, self.grind.scripted_fight_starts)):
            with self.subTest(reason=reason):
                self.player.current_hp, self.player.is_asleep = self.player.max_hp, False
                self.game.cmd_menu.current_battle = None
                if not self.grind.active:
                    self.start()
                self.in_battle()
                self.game.auto_battle = True
                stop()
                self.assertEqual(reason, self.grind.last_stop)
                self.assertFalse(self.game.auto_battle)

    def test_a_key_leaves_auto_battle_on(self):
        self.in_battle()
        self.game.auto_battle = True
        self.grind.stop(StopReason.KEY)
        self.assertTrue(self.game.auto_battle)

    def lower_hp_at_turn_start(self):
        self.player.current_hp = self.player.max_hp // 4 + 1
        self.grind.player_turn_starts()

    def fall_asleep_at_turn_start(self):
        self.player.is_asleep = True
        self.grind.player_turn_starts()

    def test_the_threshold_is_the_option(self):
        self.in_battle()
        self.player.max_hp, self.player.current_hp = 100, 60
        self.game.config['AUTO_GRIND_STOP'] = GRIND_STOP_HALF_HP
        self.grind.player_turn_starts()
        self.assertTrue(self.grind.active)
        self.game.config['AUTO_GRIND_STOP'] = GRIND_STOP_THREE_QUARTERS_HP
        self.grind.player_turn_starts()
        self.assert_stopped(StopReason.HP_LOW)

    def test_asleep_at_the_start_of_a_turn(self):
        self.in_battle()
        self.player.is_asleep = True
        self.grind.player_turn_starts()
        self.assert_stopped(StopReason.ASLEEP, "Auto-grind stopped: asleep")

    def test_stopspell(self):
        self.in_battle()
        self.grind.stopspell_hit()
        self.assert_stopped(StopReason.STOPSPELL, "Auto-grind stopped: STOPSPELL")

    def test_scripted_fight(self):
        self.in_battle()
        self.grind.scripted_fight_starts()
        self.assert_stopped(StopReason.SCRIPTED_FIGHT, "Auto-grind stopped: special fight")

    def test_level_up_says_so_back_on_the_map(self):
        self.in_battle()
        self.grind.level_up()
        self.assert_stopped(StopReason.LEVEL_UP)
        self.battle_line.assert_not_called()
        self.game.cmd_menu.current_battle = None
        self.game.map_frame()
        self.temporary_text.assert_called_once_with("Auto-grind stopped: level up\n(G to go on)")

    def test_a_key_mid_fight_says_so_at_the_next_turn(self):
        self.in_battle()
        pygame.event.post(key(K_k))
        poll_virtual_joypad(WINDOW_CONTEXT)
        self.battle_line.assert_not_called()
        self.grind.player_turn_starts()
        self.battle_line.assert_called_once()
        self.assertEqual("Auto-grind stopped\n", self.battle_line.call_args.args[0])

    def test_after_a_step(self):
        self.game.step_triggers.count_step()
        self.assertTrue(self.grind.active)
        self.player.current_hp = self.player.max_hp // 4 + 1
        self.game.step_triggers.count_step()
        self.assert_stopped(StopReason.HP_LOW)
        self.temporary_text.assert_called_once_with("Auto-grind stopped: HP low")

    def test_after_a_fight(self):
        def fight(_enemies):
            self.player.current_hp = 1
            return BattleOutcome.VICTORY
        self.game.config['FORCE_BATTLE'] = True
        with patch.object(self.game.battle_ctrl, 'run_battle', side_effect=fight):
            self.game.field_encounters.roll_for_fight(44, 50, 'GRASS')
        self.assert_stopped(StopReason.HP_LOW)
        self.temporary_text.assert_called_once_with("Auto-grind stopped: HP low")

    def test_a_death_stops_it_silently(self):
        def fight(_enemies):
            self.player.current_hp = 0
            return BattleOutcome.DEFEAT
        self.game.config['FORCE_BATTLE'] = True
        with patch.object(self.game.battle_ctrl, 'run_battle', side_effect=fight):
            self.game.field_encounters.roll_for_fight(44, 50, 'GRASS')
        self.assertFalse(self.grind.active)
        self.assertEqual(StopReason.DEATH, self.grind.last_stop)
        self.sound.assert_not_called()
        self.temporary_text.assert_not_called()


def battle_game(grinding):
    game = MagicMock()
    game._ = lambda s: s
    game.config = {"MUSIC_ENABLED": False}
    game.game_state.config = {"TILE_SIZE": 32}
    game.auto_grind.active = grinding
    player = game.player
    player.name = "Erdrick"
    player.armor = "Clothes"
    player.is_asleep = False
    player.is_dead = False
    player.is_stopspelled = False
    player.current_hp = 15
    return game


class TestBattleHooks(TestCase):
    """Where the battle code calls auto-grind."""

    def test_every_player_turn_starts_with_the_check(self):
        game = battle_game(grinding=True)
        controller = BattleController(game)
        battle = Mock(turn=0, last_turn=0, no_op=False)
        battle.enemy.hp = 3
        with patch.object(controller, 'open_command_window',
                          side_effect=lambda: setattr(controller, 'command_window_open', True)), \
                patch.object(controller, 'draw_command_window'), patch('src.battle_controller.next_frame'), \
                patch('src.battle_controller.frame_events', return_value=[]), \
                patch('src.battle_controller.held_joypad_buttons', return_value=0):
            controller.handle_battle_prompts(False, battle)
            game.auto_grind.player_turn_starts.assert_called_once()
            controller.handle_battle_prompts(False, battle)  # the same turn's window, a frame later
            game.auto_grind.player_turn_starts.assert_called_once()
        game.player.is_asleep = True
        with patch.object(controller, 'sleeping_player_turn'), patch.object(controller, 'enemy_move', return_value=False):
            controller.handle_battle_prompts(False, battle)
        self.assertEqual(2, game.auto_grind.player_turn_starts.call_count)

    def test_f3_auto_battle_is_ignored_while_grinding(self):
        for grinding in (True, False):
            with self.subTest(grinding=grinding):
                game = battle_game(grinding)
                game.auto_battle = True
                controller = BattleController(game)
                controller.last_battle_action = 'Run'
                battle = Mock()
                battle.enemy.hp = 3
                with patch.object(controller, 'open_command_window'), \
                        patch.object(controller, 'draw_command_window'), \
                        patch('src.battle_controller.next_frame'), \
                        patch('src.battle_controller.frame_events', return_value=[]), \
                        patch('src.battle_controller.held_joypad_buttons', return_value=0), \
                        patch('src.battle_controller.time'), \
                        patch.object(controller, 'remove_command_window'), \
                        patch.object(controller, 'enemy_move', return_value=False):
                    controller.handle_battle_prompts(False, battle)
                # Auto-battle would have repeated RUN at once; auto-grind waits for its A on FIGHT
                self.assertEqual(not grinding, battle.battle_run.called)

    def test_stopspell_that_works(self):
        for works in (True, False):
            with self.subTest(works=works):
                game = battle_game(grinding=True)
                controller = BattleController(game)
                enemy = Mock(is_stopspelled=False)
                enemy.name = 'Magician'
                with patch('src.battle_controller.coin_flip', return_value=works), \
                        patch('src.battle_controller.hero_random.randint', return_value=0):
                    controller.execute_enemy_pattern(Mock(), (100, Spell.STOPSPELL, True), 0, enemy)
                self.assertEqual(works, game.auto_grind.stopspell_hit.called)

    @patch('src.battle_controller.display')
    @patch('src.battle_controller.Battle')
    def test_scripted_fights_and_the_dragonlord(self, mock_battle_class, _display):
        for enemy_name, scripted, expected in (('Golem', True, True), ('Slime', False, False),
                                               ('Dragonlord 2', False, True)):
            with self.subTest(enemy_name):
                game = battle_game(grinding=True)
                controller = BattleController(game)
                battle = Mock()
                battle.enemy = Mock(hp=10)
                battle.enemy.name = enemy_name
                mock_battle_class.return_value = battle
                with patch.object(controller, 'start_fight', return_value=True), \
                        patch.object(controller, 'reload_map_after_running_from_final_form'):
                    if scripted:
                        controller.start_scripted_battle(enemy_name)
                    else:
                        controller.fight_enemy(enemy_name)
                self.assertEqual(expected, game.auto_grind.scripted_fight_starts.called)
                self.assertFalse(controller.scripted_fight)

    def test_a_level_up_stops_it_before_the_promotion(self):
        battle = MagicMock()
        cmd_menu = MagicMock()
        order = []
        cmd_menu.game.auto_grind.level_up.side_effect = lambda: order.append('stop')
        cmd_menu.wait_for_button.side_effect = lambda **_kwargs: order.append('wait')
        player = MagicMock(level=1, total_experience=7)
        Battle.check_player_level_up(battle, cmd_menu, player)
        # stopped before TB16E1's leading WAIT, and before ExitFight's press after the stat lines (#381)
        self.assertEqual(['stop', 'wait', 'wait'], order)
        cmd_menu.reset_mock()
        player = MagicMock(level=2, total_experience=7)
        Battle.check_player_level_up(battle, cmd_menu, player)
        cmd_menu.game.auto_grind.level_up.assert_not_called()


class HeadlessTestCase(GrindTestCase):
    """The real game loop, near Tantegel, with the real messages and windows."""
    experience = 23  # level 3: several fights before HP is low, and none of them a level up

    def setUp(self):
        super().setUp()
        self.temporary_text.stop()  # the real messages, through the dialog code
        patch.stopall()
        self.sound = patch.object(self.game.sound, 'play_sound').start()
        player = self.player
        player.total_experience = self.experience
        player.level = player.get_level_by_experience()
        player.set_stats_by_level(player.level)
        player.update_attack_power()
        player.update_defense_power()
        player.current_hp = player.max_hp
        player.current_mp = player.max_mp

    def run_main_loop(self, passes: int) -> None:
        """Passes of the main loop, one NES frame each on a fake game clock: the same frames, steps and fights on any
        machine. The map is drawn too (NO_BLIT draws nothing to the screen): the drawer opens the COMMAND window."""
        clock = helpers.fake_game_clock()
        game = self.game
        for _ in range(passes):
            clock.advance_frames()
            game.run_due_frames()
            game.drawer.draw_all(game, game.movement.sprites_animate)
            game.loop_count += 1


class TestHeadlessGrind(HeadlessTestCase):
    """G, then nothing until auto-grind hands the game back."""

    def test_fights_until_hp_is_low_and_hands_over_the_command_window(self):
        seed_all(1)
        # Game time, one NES frame per pass of the main loop: the same frames, steps and fights on any machine
        clock = helpers.fake_game_clock()
        cells, fights, stops = set(), [], []
        game = self.game
        real_count_step, real_fight, real_open = game.step_triggers.count_step, game.battle_ctrl.fight_enemy, \
            game.battle_ctrl.open_command_window

        def count_step():
            cells.add(self.grind.hero_cell())
            real_count_step()

        def fight_enemy(enemy_name):
            fights.append(enemy_name)
            return real_fight(enemy_name)

        def open_command_window():
            real_open()
            if not self.grind.active:
                stops.append(self.grind.last_stop)
                raise Done

        pygame.event.post(key(K_g))
        with patch.object(game.step_triggers, 'count_step', side_effect=count_step), \
                patch.object(game.battle_ctrl, 'fight_enemy', side_effect=fight_enemy), \
                patch.object(game.battle_ctrl, 'open_command_window', side_effect=open_command_window):
            with self.assertRaises(Done):
                for _ in range(100_000):
                    clock.advance_frames()
                    game.run_due_frames()  # the main loop, without drawing the map (NO_BLIT draws nothing anyway)
        self.assertGreaterEqual(len(fights), 3)
        self.assertEqual([StopReason.HP_LOW], stops)
        self.assertLessEqual(self.player.current_hp, self.player.max_hp // 4 + 1)
        self.assertGreater(self.player.current_hp, 0)
        # mid-fight, with the battle's command window open for the player, on FIGHT
        self.assertIsNotNone(game.cmd_menu.current_battle)
        self.assertTrue(game.battle_ctrl.command_window_open)
        self.assertEqual((0, 0), (game.battle_ctrl.battle_menu_row, game.battle_ctrl.battle_menu_column))
        self.assertEqual({GRASS, (51, 44)}, cells)
        self.assertEqual(set(), ALL_DIRECTION_KEYS & self.grind.joypad.held)
        self.assertIsNone(virtual_joypad())


class TestHeadlessAutoHeal(HeadlessTestCase):
    """AUTO-HEAL in the real game loop: HP low, the hero casts HEAL through the windows and grinds on, until there's
    no MP left for another. Level 3: HEAL, and the MP for one (5)."""

    def new_game(self, **overrides):
        return super().new_game(AUTO_HEAL=AUTO_HEAL_ON, **overrides)

    def run_until_stopped(self, seed):
        seed_all(seed)
        game = self.game
        heals, stops = [], []
        real_heal, real_open = game.cmd_menu.heal, game.battle_ctrl.open_command_window

        def heal():
            heals.append(game.cmd_menu.current_battle is not None)  # whether in a fight
            real_heal()

        def open_command_window():
            real_open()
            if not self.grind.active:
                stops.append(self.grind.last_stop)
                raise Done

        pygame.event.post(key(K_g))
        with patch.object(game.cmd_menu, 'heal', side_effect=heal), \
                patch.object(game.battle_ctrl, 'open_command_window', side_effect=open_command_window):
            with self.assertRaises(Done):
                self.run_main_loop(200_000)
        return heals, stops

    def test_heals_then_stops_when_the_mp_is_gone(self):
        heals, stops = self.run_until_stopped(seed=1)
        self.assertEqual([True], heals)  # one HEAL, at the start of a turn in a fight: SPELL, then HEAL
        self.assertEqual([StopReason.MP_LOW], stops)
        self.assertEqual(1, self.player.current_mp)  # 5 - HEAL's 4
        self.assertLessEqual(self.player.current_hp, self.player.max_hp // 4 + 1)
        self.assertGreater(self.player.current_hp, 0)

    def test_keep_one_heal_stops_without_casting_it(self):
        self.game.game_state.config['AUTO_HEAL'] = AUTO_HEAL_KEEP_ONE
        heals, stops = self.run_until_stopped(seed=1)
        self.assertEqual([], heals)  # 5 MP - 4 would leave less than one HEAL
        self.assertEqual([StopReason.MP_LOW], stops)
        self.assertEqual(5, self.player.current_mp)


class TestAutoHealOnTheMap(HeadlessTestCase):
    """HP low on the map: A, SPELL in the COMMAND window, HEAL in the SPELL window, through the real windows."""
    experience = 47  # level 4: HEAL and HURT, 16 MP

    def new_game(self, **overrides):
        return super().new_game(AUTO_HEAL=AUTO_HEAL_ON, **overrides)

    def test_starting_with_hp_low_heals_first_and_grinds_on(self):
        player = self.player
        player.current_hp = 3
        self.assertTrue(self.grind.start())
        self.assertEqual(Spell.HEAL, self.grind.heal_spell)
        heals = []
        real_heal = self.game.cmd_menu.heal

        def heal():
            heals.append(player.current_hp)
            real_heal()

        with patch.object(self.game.cmd_menu, 'heal', side_effect=heal), \
                patch.object(self.game.battle_ctrl, 'fight_enemy', side_effect=Done):
            with self.assertRaises(Done):  # back to pacing: the first fight
                self.run_main_loop(20_000)
        # HEAL until out of the red (31 max HP: 8 and below), each from the map's windows
        self.assertGreaterEqual(len(heals), 1)
        self.assertGreater(player.current_hp, player.max_hp // 4 + 1)
        self.assertEqual(player.max_mp - 4 * len(heals), player.current_mp)
        self.assertTrue(self.grind.active)
        self.assertIsNone(self.grind.heal_spell)
        self.assertFalse(self.game.cmd_menu.menu.is_enabled())

    def test_without_auto_heal_it_does_not_start(self):
        self.game.game_state.config['AUTO_HEAL'] = AUTO_HEAL_OFF
        self.player.current_hp = 3
        with patch.object(self.game, 'draw_temporary_text') as text:
            self.assertFalse(self.grind.start())
        text.assert_called_once_with("Auto-grind: HP is already low")


class TestDanger(GrindTestCase):

    def setUp(self):
        super().setUp()
        self.game.game_state.config['AUTO_GRIND_STOP'] = GRIND_STOP_DANGER

    def test_on_the_map_twice_the_worst_hit_of_the_zone(self):
        player = self.player
        worst = worst_group_damage(self.grind.enemies_here(), player.defense_power, player.armor)
        self.assertEqual({'Slime', 'Red Slime'}, self.grind.enemies_here())  # by Tantegel
        self.assertEqual(2 * worst, self.grind.hp_line(in_fight=False))

    def test_in_a_fight_the_enemy_s_worst_hit(self):
        battle = MagicMock()
        battle.enemy = enemy_string_lookup['Magician']()
        self.game.cmd_menu.current_battle = battle
        player = self.player
        self.assertEqual(worst_enemy_damage(battle.enemy, player.defense_power, player.armor),
                         self.grind.hp_line(in_fight=True))


class TestGInAFight(GrindTestCase):

    def setUp(self):
        super().setUp()
        self.game.cmd_menu.current_battle = MagicMock()

    def test_g_at_the_command_window_starts_it(self):
        self.assertTrue(self.game.battle_ctrl.press_auto_grind(key(K_g)))
        self.assertTrue(self.grind.active)
        self.assertEqual((GRASS, (51, 44)), (self.grind.origin, self.grind.partner))

    def test_not_in_a_scripted_fight(self):
        self.game.battle_ctrl.special_fight = True
        with patch.object(self.game.cmd_menu, 'show_line_in_dialog_box') as line:
            self.assertTrue(self.game.battle_ctrl.press_auto_grind(key(K_g)))
        self.assertFalse(self.grind.active)
        line.assert_called_once()

    def test_other_keys_and_the_option_off(self):
        self.assertFalse(self.game.battle_ctrl.press_auto_grind(key(K_k)))
        self.game.game_state.config['AUTO_GRIND'] = False
        self.assertFalse(self.game.battle_ctrl.press_auto_grind(key(K_g)))
        self.assertFalse(self.grind.active)


class TestHealSteering(GrindTestCase):
    """heal_key: the key that takes each window one step closer to the healing spell."""

    def setUp(self):
        super().setUp()
        self.player.spells = [Spell.HEAL, Spell.HURT, Spell.SLEEP, Spell.RADIANT, Spell.STOPSPELL, Spell.OUTSIDE,
                              Spell.RETURN, Spell.REPEL, Spell.HEALMORE]
        self.grind.heal_spell = Spell.HEALMORE

    def test_the_spell_window(self):
        cmd_menu = self.game.cmd_menu
        cmd_menu.item_menu_selection = ('spells', 0)
        self.assertEqual(K_DOWN, self.grind.heal_key())
        cmd_menu.item_menu_selection = ('spells', 9)  # past it (a bigger list): back up
        self.assertEqual(K_UP, self.grind.heal_key())
        cmd_menu.item_menu_selection = ('spells', 8)
        self.assertEqual(K_k, self.grind.heal_key())
        self.assertIsNone(self.grind.heal_spell)  # chosen

    def test_the_item_window_is_backed_out_of(self):
        self.game.cmd_menu.item_menu_selection = ('inventory', 0)
        self.assertEqual(K_j, self.grind.heal_key())
        self.assertEqual(Spell.HEALMORE, self.grind.heal_spell)

    def test_the_battle_command_window(self):
        battle_ctrl = self.game.battle_ctrl
        self.game.cmd_menu.current_battle = MagicMock()
        battle_ctrl.command_window_open = False
        self.assertEqual(K_k, self.grind.heal_key())  # a battle line waiting for a press
        battle_ctrl.command_window_open = True
        for cell, expected in (((0, 0), K_RIGHT), ((1, 0), K_UP), ((1, 1), K_UP), ((0, 1), K_k)):
            battle_ctrl.battle_menu_row, battle_ctrl.battle_menu_column = cell
            with self.subTest(cell=cell):
                self.assertEqual(expected, self.grind.heal_key())

    def test_the_command_window_on_the_map(self):
        cmd_menu = self.game.cmd_menu
        self.assertEqual(K_k, self.grind.heal_key())  # opens it
        cmd_menu.launch_signaled = True
        self.assertIsNone(self.grind.heal_key())  # on its way
        cmd_menu.menu.enable()
        for selected, expected in ((0, K_RIGHT), (5, K_UP), (4, K_k)):  # TALK, ITEM, SPELL
            cmd_menu.menu.selected = selected
            with self.subTest(selected=selected):
                self.assertEqual(expected, self.grind.heal_key())


class TestHeadlessInnTrip(HeadlessTestCase):
    """AUTO-INN in the real game loop, near Tantegel: level 2, no spells, 100 gold. HP low on the map: to Brecconary,
    a night at the inn, and back to the tile auto-grind started on."""
    experience = 7  # level 2: 22 HP, no HEAL

    def new_game(self, **overrides):
        return super().new_game(AUTO_INN=True, AUTO_GRIND_STOP=GRIND_STOP_DANGER, **overrides)

    def test_to_the_inn_and_back(self):
        seed_all(2)
        game, player, grind = self.game, self.player, self.grind
        player.gold = 100
        maps, nights = [], []
        real_change_map, real_back_home = game.map_mgr.change_map, grind.back_home
        real_sleep = DialogLookup.inn_sleep

        def change_map(*args, **kwargs):
            real_change_map(*args, **kwargs)
            maps.append(game.current_map.identifier)

        def inn_sleep(dialog_lookup, cost):
            nights.append((cost, player.current_hp))
            real_sleep(dialog_lookup, cost)

        def back_home():
            real_back_home()
            raise Done

        pygame.event.post(key(K_g))
        with patch.object(game.map_mgr, 'change_map', side_effect=change_map), \
                patch.object(DialogLookup, 'inn_sleep', autospec=True, side_effect=inn_sleep), \
                patch.object(grind, 'back_home', side_effect=back_home):
            with self.assertRaises(Done):
                self.run_main_loop(20_000)
        self.assertEqual(['Brecconary', 'Alefgard'], maps)
        self.assertEqual(1, len(nights))
        cost, hp_at_the_inn = nights[0]
        self.assertEqual(6, cost)
        self.assertLess(hp_at_the_inn, player.max_hp)
        # back where it started, with full HP and MP and 6 gold less than it had at the inn (the fights pay on the way)
        self.assertEqual(GRASS, grind.hero_cell())
        self.assertEqual(player.max_hp, player.current_hp)
        self.assertTrue(grind.active)
        self.assertIsNone(grind.trip)
        self.assertEqual((GRASS, (51, 44)), (grind.origin, grind.partner))


class TestAutoInn(GrindTestCase):

    def new_game(self, **overrides):
        return super().new_game(AUTO_INN=True, **overrides)

    def setUp(self):
        super().setUp()
        self.player.gold = 100

    def test_hp_low_on_the_map_starts_a_trip(self):
        self.start()
        self.player.current_hp = 1
        self.grind.after_step()
        self.assertTrue(self.grind.active)
        self.assertIsNotNone(self.grind.trip)
        self.temporary_text.assert_called_with("Auto-grind: off to the inn")

    def test_without_auto_inn_it_stops(self):
        self.game.game_state.config['AUTO_INN'] = False
        self.start()
        self.player.current_hp = 1
        self.grind.after_step()
        self.assertFalse(self.grind.active)
        self.assertEqual(StopReason.HP_LOW, self.grind.last_stop)

    def test_no_inn_it_can_pay_for(self):
        self.player.gold = 5
        self.start()
        self.player.current_hp = 1
        self.grind.after_step()
        self.assertFalse(self.grind.active)
        self.assertEqual(StopReason.HP_LOW, self.grind.last_stop)

    def test_starting_with_hp_low_goes_to_the_inn_first(self):
        self.player.current_hp = 1
        self.assertTrue(self.grind.start())
        self.assertIsNotNone(self.grind.trip)
        self.assertEqual((GRASS, (51, 44)), (self.grind.origin, self.grind.partner))

    def test_out_of_mp_for_a_heal_goes_while_hp_is_good(self):
        self.game.game_state.config['AUTO_HEAL'] = AUTO_HEAL_KEEP_ONE
        self.player.spells = [Spell.HEAL]
        self.player.current_mp = 7  # one HEAL kept for the way: none to spend
        self.start()
        self.grind.after_fight()
        self.assertIsNotNone(self.grind.trip)
        # on the way, the HEAL kept is spent
        self.player.current_hp = 1
        self.assertEqual(Spell.HEAL, self.grind.heal_choice(in_fight=False))

    def test_out_of_mp_with_no_inn_grinds_on(self):
        self.player.gold = 0
        self.game.game_state.config['AUTO_HEAL'] = AUTO_HEAL_ON
        self.player.spells = [Spell.HEAL]
        self.player.current_mp = 3
        self.start()
        self.grind.after_fight()
        self.assertTrue(self.grind.active)
        self.assertIsNone(self.grind.trip)
        self.assertTrue(self.grind.no_inn_for_mp)  # and it doesn't look again every fight

    def test_in_a_fight_it_fights_on_while_the_enemy_cannot_kill(self):
        self.start()
        battle = MagicMock()
        battle.enemy = enemy_string_lookup['Slime']()
        self.game.cmd_menu.current_battle = battle
        player = self.player
        worst = worst_enemy_damage(battle.enemy, player.defense_power, player.armor)
        with patch.object(self.game.cmd_menu, 'show_line_in_dialog_box'):
            player.current_hp = worst + 1
            self.grind.heal_or_stop(in_fight=True)
            self.assertTrue(self.grind.active)
            player.current_hp = worst
            self.grind.heal_or_stop(in_fight=True)
        self.assertFalse(self.grind.active)
        self.assertEqual(StopReason.HP_LOW, self.grind.last_stop)

    def test_on_the_way_in_a_town_it_walks_on(self):
        self.player.current_hp = 1
        self.assertTrue(self.grind.start())
        self.go_to('Brecconary', (23, 10))
        self.grind.heal_or_stop(in_fight=False)
        self.assertTrue(self.grind.active)


class TestInnTripSteps(GrindTestCase):
    """The trip's steps on their own (src/inn_trip.py): stairs, someone in the way, a command that does nothing."""

    def new_game(self, **overrides):
        return super().new_game(AUTO_INN=True, **overrides)

    def setUp(self):
        super().setUp()
        self.player.gold = 100
        self.player.current_hp = 1
        self.assertTrue(self.grind.start())
        self.trip = self.grind.trip
        self.joypad = self.grind.joypad

    def test_stairs_at_the_end_of_the_leg_are_taken_with_the_stairs_command(self):
        cell = self.grind.hero_cell()
        self.trip.leg = Leg([cell], exit=Exit.STAIRS)
        self.trip.leg_map = self.game.current_map.identifier
        self.assertEqual(TripResult.WALKING, self.trip.drive(self.joypad))
        self.assertEqual(COMMAND_STAIRS, self.trip.command)
        # down the stairs: the next map's leg is worked out afresh
        self.trip.leg_map = 'ErdricksCaveB1'
        self.assertEqual(TripResult.WALKING, self.trip.drive(self.joypad))
        self.assertIsNone(self.trip.command)
        self.assertIsNone(self.trip.leg)

    def test_a_command_that_keeps_doing_nothing_loses_the_way(self):
        self.trip.start_command(COMMAND_STAIRS)
        results = []
        for _ in range(ATTEMPTS + 1):
            self.trip.command_chosen = True  # chosen in the COMMAND window, which has closed again, and nothing came of it
            results.append(self.trip.drive(self.joypad))
        self.assertEqual([TripResult.WALKING] * ATTEMPTS + [TripResult.LOST], results)

    def test_someone_in_the_way_is_gone_round(self):
        self.assertIsNotNone(self.trip.leg)
        self.trip.drive(self.joypad)  # the first step: the hero is "still" from now
        self.joypad.now += STUCK_FRAMES + 1
        npc = MagicMock(row=50, column=45, step_destination=None)
        with patch.object(self.game.current_map, 'roaming_characters', [npc]):
            self.assertEqual(TripResult.WALKING, self.trip.drive(self.joypad))
        self.assertEqual(1, self.trip.attempts)
        self.assertEqual({(50, 45)}, self.trip.blocked)
        self.assertNotIn((50, 45), self.trip.leg.cells)

    def test_stuck_for_good_loses_the_way(self):
        self.trip.attempts = ATTEMPTS
        self.trip.drive(self.joypad)
        self.joypad.now += STUCK_FRAMES + 1
        self.assertEqual(TripResult.LOST, self.trip.drive(self.joypad))

    def test_a_lost_trip_stops_auto_grind(self):
        self.player.current_hp = self.player.max_hp  # no HP stop first
        with patch.object(self.trip, 'drive', return_value=TripResult.LOST), \
                patch.object(self.game.cmd_menu, 'show_line_in_dialog_box'):
            self.grind.walk(self.joypad)
        self.assertFalse(self.grind.active)
        self.assertEqual(StopReason.LOST, self.grind.last_stop)
