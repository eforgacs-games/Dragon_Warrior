"""Auto-grind (src/auto_grind.py): G on the map, driven by the virtual joypad (src/virtual_joypad.py). Not NES."""
import os
import random
import time
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from pygame import K_2, K_DOWN, K_LCTRL, K_UP, K_g, K_k, KEYDOWN, KMOD_CTRL
from pygame.event import Event

from src.auto_grind import ALL_DIRECTION_KEYS, GRIND_STOP_HALF_HP, GRIND_STOP_RED_HP, GRIND_STOP_THREE_QUARTERS_HP, \
    UNSAFE_TILES, AutoGrind, StopReason, at_grind_stop_hp
from src.battle import Battle
from src.battle_controller import BattleController, BattleOutcome
from src.config.test_config import test_config
from src.direction import Direction
from src.maps import map_lookup
from src.maps_functions import get_center_point
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
                                 'AUTO_GRIND_STOP': GRIND_STOP_RED_HP, **overrides})

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
        real_count_step = self.game.count_step

        def count_step():
            cells.append(self.grind.hero_cell())
            real_count_step()
        with patch.object(self.game, 'count_step', side_effect=count_step):
            deadline = time.monotonic() + 20
            while len(cells) < 6 and time.monotonic() < deadline:
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
        self.game.count_step()
        self.assertTrue(self.grind.active)
        self.player.current_hp = self.player.max_hp // 4 + 1
        self.game.count_step()
        self.assert_stopped(StopReason.HP_LOW)
        self.temporary_text.assert_called_once_with("Auto-grind stopped: HP low")

    def test_after_a_fight(self):
        def fight(_enemies):
            self.player.current_hp = 1
            return BattleOutcome.VICTORY
        self.game.config['FORCE_BATTLE'] = True
        with patch.object(self.game.battle_ctrl, 'run_battle', side_effect=fight):
            self.game.roll_for_fight(44, 50, 'GRASS')
        self.assert_stopped(StopReason.HP_LOW)
        self.temporary_text.assert_called_once_with("Auto-grind stopped: HP low")

    def test_a_death_stops_it_silently(self):
        def fight(_enemies):
            self.player.current_hp = 0
            return BattleOutcome.DEFEAT
        self.game.config['FORCE_BATTLE'] = True
        with patch.object(self.game.battle_ctrl, 'run_battle', side_effect=fight):
            self.game.roll_for_fight(44, 50, 'GRASS')
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
                        patch('src.battle_controller.random.randint', return_value=0):
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


class TestHeadlessGrind(GrindTestCase):
    """The real game loop, near Tantegel: G, then nothing until auto-grind hands the game back."""

    def setUp(self):
        super().setUp()
        self.temporary_text.stop()  # the real messages, through the dialog code
        patch.stopall()
        self.sound = patch.object(self.game.sound, 'play_sound').start()
        player = self.player
        player.total_experience = 23  # level 3: several fights before HP is low, and none of them a level up
        player.level = player.get_level_by_experience()
        player.set_stats_by_level(player.level)
        player.update_attack_power()
        player.update_defense_power()
        player.current_hp = player.max_hp

    def test_fights_until_hp_is_low_and_hands_over_the_command_window(self):
        random.seed(1)
        set_game_speed(8)
        cells, fights, stops = set(), [], []
        game = self.game
        real_count_step, real_fight, real_open = game.count_step, game.battle_ctrl.fight_enemy, \
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
        with patch.object(game, 'count_step', side_effect=count_step), \
                patch.object(game.battle_ctrl, 'fight_enemy', side_effect=fight_enemy), \
                patch.object(game.battle_ctrl, 'open_command_window', side_effect=open_command_window):
            deadline = time.monotonic() + 45
            with self.assertRaises(Done):
                while time.monotonic() < deadline:
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
