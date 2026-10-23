"""The options overlay's gameplay switches (src/options_overlay.py, src/options_screen.py SWITCHES), each with its NES
value as the default: ENCOUNTERS (#399), EXP/GOLD (#400), RUN BUTTON (#403) and STATUS WINDOW (#406). The ghosting
checks for running are with the others in tests/test_character_redraw.py."""
import os
from collections import defaultdict
from unittest import TestCase
from unittest.mock import Mock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from pygame import K_RIGHT, K_j

from src.battle import MAX_EXPERIENCE, MAX_GOLD, Battle
from src.config.base_config import base_config
from src.config.test_config import test_config
from src.direction import Direction
from src.game_functions import set_character_position
from src.maps import map_lookup
from src.movement import RUN_STEP_FRAMES, STEP_SYNC_FRAMES
from src.options_screen import DEFAULT_OPTIONS, ENCOUNTERS_HALF, ENCOUNTERS_NES, ENCOUNTERS_OFF, \
    STATUS_WINDOW_ALWAYS, STATUS_WINDOW_NES
from tests import helpers


def new_game(**overrides):
    # A copy of test_config, so the settings these tests change don't leak into other tests
    return helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True, **overrides})


class GameTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.game = new_game()
        self.config = self.game.game_state.config


class TestDefaults(TestCase):

    def test_every_one_starts_at_the_nes_value(self):
        self.assertEqual((ENCOUNTERS_NES, 1, False, STATUS_WINDOW_NES),
                         (base_config['ENCOUNTERS'], base_config['EXP_GOLD'], base_config['RUN_BUTTON'],
                          base_config['STATUS_WINDOW']))
        self.assertEqual((ENCOUNTERS_NES, 1, False, STATUS_WINDOW_NES),
                         (DEFAULT_OPTIONS.encounters, DEFAULT_OPTIONS.exp_gold, DEFAULT_OPTIONS.run_button,
                          DEFAULT_OPTIONS.status_window))


class TestEncounters(GameTestCase):
    """ENCOUNTERS: NES / HALF / OFF. The NES's roll decides whether a fight would start (and with what); HALF skips
    every other one of those, OFF all of them."""

    def fights_in(self, rolls):
        """How many fights start from these steps' rolls (None: no fight, otherwise the rolled enemies)."""
        self.game.change_map(map_lookup['Alefgard'](self.config), destination_coordinates=(50, 44))
        with patch('src.game.roll_encounter', side_effect=rolls), \
                patch.object(self.game.battle_ctrl, 'run_battle') as run_battle, \
                patch.object(self.game.map_mgr, 'stay_on_stairs'):
            for _ in rolls:
                self.game.roll_for_fight(47, 43, 'GRASS')
        return [call.args[0] for call in run_battle.call_args_list]

    def test_nes_fights_every_roll(self):
        self.assertEqual([('Slime',), ('Red Slime',)], self.fights_in([('Slime',), None, ('Red Slime',)]))

    def test_half_skips_every_other_fight_the_nes_would_start(self):
        self.config['ENCOUNTERS'] = ENCOUNTERS_HALF
        rolls = [('Slime',), None, ('Red Slime',), ('Drakee',), None, ('Ghost',), ('Magician',)]
        self.assertEqual([('Slime',), ('Drakee',), ('Magician',)], self.fights_in(rolls))

    def test_off_starts_no_random_fight(self):
        self.config['ENCOUNTERS'] = ENCOUNTERS_OFF
        self.assertEqual([], self.fights_in([('Slime',), ('Red Slime',)]))

    def test_the_roll_is_still_made(self):
        # the NES's random numbers go on the same way, so the fights HALF keeps are the ones the NES would start
        for setting in (ENCOUNTERS_HALF, ENCOUNTERS_OFF):
            with self.subTest(setting):
                self.config['ENCOUNTERS'] = setting
                with patch('src.game.roll_encounter', return_value=None) as roll_encounter:
                    self.game.change_map(map_lookup['Alefgard'](self.config), destination_coordinates=(50, 44))
                    self.game.roll_for_fight(47, 43, 'GRASS')
                roll_encounter.assert_called_once()

    def test_scripted_fights_still_happen(self):
        self.config['ENCOUNTERS'] = ENCOUNTERS_OFF
        self.game.battle_ctrl.queue_scripted_battle('Golem')
        with patch.object(self.game.battle_ctrl, 'run_pending_scripted_battle') as run_scripted_battle:
            self.game.handle_battles()
        run_scripted_battle.assert_called_once()

    def test_auto_grind_refuses_to_start_with_encounters_off(self):
        self.config.update(ENCOUNTERS=ENCOUNTERS_OFF, AUTO_GRIND=True)
        self.game.change_map(map_lookup['Alefgard'](self.config), destination_coordinates=(50, 44))
        with patch.object(self.game, 'draw_temporary_text') as draw_temporary_text:
            self.assertFalse(self.game.auto_grind.start())
        draw_temporary_text.assert_called_once_with("Auto-grind: ENCOUNTERS are off")
        self.assertFalse(self.game.auto_grind.active)
        # HALF still has fights, so it starts
        self.config['ENCOUNTERS'] = ENCOUNTERS_HALF
        with patch.object(self.game, 'draw_temporary_text'):
            self.assertTrue(self.game.auto_grind.start())
        self.game.auto_grind.joypad.disconnect()


class TestExpGold(TestCase):
    """EXP/GOLD: x1 (NES) / x2 / x4 the experience and gold of a won fight."""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def win(self, multiplier, experience=0, gold=0, enemy_xp=10, enemy_gold=5):
        battle = Battle({'LANGUAGE': 'English', 'TILE_SIZE': 32, 'MUSIC_ENABLED': False,
                         'ORCHESTRA_MUSIC_ENABLED': False, 'SOUND_ENABLED': False, 'EXP_GOLD': multiplier},
                        'Slime', Mock())
        cmd_menu = Mock()
        player = Mock(total_experience=experience, gold=gold, level=1, spells=[])
        enemy = Mock(xp=enemy_xp, gold=enemy_gold)
        enemy.name = 'Slime'
        # NES CalcPlyrGold: 5 * (192 + 63) // 256 = 4 on the highest roll
        with patch.object(battle, 'make_enemy_image_disappear'), \
                patch.object(battle, 'check_player_level_up') as level_up, \
                patch('src.battle.random.randint', return_value=63):
            battle.enemy_defeated(cmd_menu, Mock(), player, enemy)
        level_up.assert_called_once()  # the level up comes after, as it does on the NES
        return player, cmd_menu.show_line_in_dialog_box.call_args_list[-1].args[0]

    def test_the_amounts_and_the_lines(self):
        for multiplier, experience, gold in ((1, 10, 4), (2, 20, 8), (4, 40, 16)):
            with self.subTest(multiplier=multiplier):
                player, line = self.win(multiplier)
                self.assertEqual((experience, gold), (player.total_experience, player.gold))
                self.assertEqual(f"Thy Experience\nincreases by {experience}.\nThy GOLD\nincreases by {gold}.\n",
                                 line)

    def test_the_nes_caps_still_hold(self):
        player, _line = self.win(4, experience=MAX_EXPERIENCE - 5, gold=MAX_GOLD - 5)
        self.assertEqual((MAX_EXPERIENCE, MAX_GOLD), (player.total_experience, player.gold))

    def test_anything_else_is_x1(self):
        player, _line = self.win('lots')
        self.assertEqual((10, 4), (player.total_experience, player.gold))


class TestRunButton(GameTestCase):
    """RUN BUTTON: holding B while walking on the map, a step takes 8 frames instead of 16."""

    def setUp(self):
        super().setUp()
        self.game.game_state.is_initial_dialog = False
        self.config['RUN_BUTTON'] = True

    def walk(self, frames, *held):
        """Run frames of the hero holding these keys; returns how many steps were counted, and on which frames."""
        held_keys = defaultdict(int, {held_key: 1 for held_key in held})
        steps = []
        with patch('src.movement.key.get_pressed', return_value=held_keys), \
                patch.object(self.game, 'count_step', side_effect=lambda: steps.append(frame)):
            for frame in range(1, frames + 1):
                self.game.movement.handle_player_movement()
                if not self.game.player.is_moving:
                    set_character_position(self.game.player, self.game.tile_size)
                self.game.movement.sprites_frame()
        return steps

    def go_to_open_ground(self):
        # The overworld south of Tantegel: grass and trees to the right, a long way
        self.game.change_map(map_lookup['Alefgard'](self.config), destination_coordinates=(50, 44),
                             direction=Direction.RIGHT.value)
        self.game.movement.npc_schedule.frame_counter = 0

    def test_holding_b_walks_a_step_every_8_frames(self):
        self.go_to_open_ground()
        steps = self.walk(4 * STEP_SYNC_FRAMES, K_RIGHT, K_j)
        self.assertEqual(8, len(steps))
        self.assertEqual([RUN_STEP_FRAMES] * 7, [later - earlier for earlier, later in zip(steps, steps[1:])])
        self.assertEqual(44 + 8, self.game.player.rect.x // self.game.tile_size)

    def test_without_b_or_with_the_option_off_it_is_the_nes_walk(self):
        for held, run_button in (((K_RIGHT,), True), ((K_RIGHT, K_j), False)):
            with self.subTest(held=held, run_button=run_button):
                self.config['RUN_BUTTON'] = run_button
                self.go_to_open_ground()
                steps = self.walk(4 * STEP_SYNC_FRAMES, *held)
                self.assertEqual(4, len(steps))
                self.assertEqual([STEP_SYNC_FRAMES] * 3, [later - earlier for earlier, later in zip(steps, steps[1:])])

    def test_the_npcs_keep_their_own_pace(self):
        # FrameCounter's place in the NPC turns, and whose turn it is, go on as they do while the hero walks
        places = []
        for held in ((K_RIGHT,), (K_RIGHT, K_j)):
            self.go_to_open_ground()
            self.walk(2 * STEP_SYNC_FRAMES + 3, *held)
            places.append((self.game.movement.frame_counter % STEP_SYNC_FRAMES,
                           self.game.movement.npc_schedule.update_counter))
        self.assertEqual((3, 2), places[0])
        self.assertEqual(places[0], places[1])

    def test_a_running_step_only_starts_half_way_into_a_clear_block(self):
        # Not into a clear block, the half-way step waits for the NES's own step frame (a multiple of 16), where a
        # wall or an NPC bumps as walking does: each step still runs, in 8 frames, but only every 16
        self.go_to_open_ground()
        with patch.object(self.game.movement, 'run_step_is_clear', return_value=False):
            steps = self.walk(2 * STEP_SYNC_FRAMES, K_RIGHT, K_j)
        self.assertEqual([RUN_STEP_FRAMES, STEP_SYNC_FRAMES + RUN_STEP_FRAMES], steps)

    def test_what_is_a_clear_block(self):
        self.go_to_open_ground()
        movement = self.game.movement
        self.assertTrue(movement.run_step_is_clear())
        with patch.object(movement, 'is_impassable', return_value=True):
            self.assertFalse(movement.run_step_is_clear())
        with patch.object(movement, 'character_in_path', return_value=True):
            self.assertFalse(movement.run_step_is_clear())
        with patch.object(self.game.current_map, 'is_map_exit', return_value=True):
            self.assertFalse(movement.run_step_is_clear())

    def test_b_does_nothing_else_on_the_map(self):
        self.go_to_open_ground()
        self.game.handle_keypresses(pygame.event.Event(pygame.KEYDOWN, key=K_j, mod=0))
        self.assertFalse(self.game.cmd_menu_requested or self.game.pause_requested or self.game.options_requested)

    def test_the_main_loop_draws_at_least_every_half_running_step(self):
        self.go_to_open_ground()
        with patch.object(self.game.frame_pacer, 'frames_due', return_value=0):
            self.game.run_due_frames()
        self.assertEqual(RUN_STEP_FRAMES // 2, self.game.frame_pacer.max_frames)
        self.config['RUN_BUTTON'] = False
        with patch.object(self.game.frame_pacer, 'frames_due', return_value=0):
            self.game.run_due_frames()
        self.assertEqual(STEP_SYNC_FRAMES // 2, self.game.frame_pacer.max_frames)


class TestStatusWindow(GameTestCase):
    """STATUS WINDOW: NES (the pop-up after standing still, IdleUpdate) / ALWAYS (on the map all the time)."""

    def test_nes_a_direction_press_closes_it(self):
        drawer = self.game.drawer
        drawer.display_hovering_stats = True
        drawer.remove_pop_up(self.game.cmd_menu)
        self.assertFalse(drawer.display_hovering_stats)

    def test_always_stays_up_while_walking(self):
        self.config['STATUS_WINDOW'] = STATUS_WINDOW_ALWAYS
        self.game.game_state.is_initial_dialog = False
        drawer = self.game.drawer
        drawer.remove_pop_up(self.game.cmd_menu)
        self.assertTrue(drawer.status_window_always())
        with patch.object(drawer, 'draw_hovering_stats_window') as draw_window, \
                patch.object(self.game.cmd_menu, 'window_drop_down_effect'):
            self.game.player.is_moving = True
            drawer.draw_all(self.game, False)
            drawer.draw_all(self.game, False)
        self.assertEqual(2, draw_window.call_count)

    def test_not_over_the_throne_rooms_automatic_dialogs(self):
        self.config['STATUS_WINDOW'] = STATUS_WINDOW_ALWAYS
        for flag in ('is_initial_dialog', 'is_post_death_dialog'):
            with self.subTest(flag), patch.object(self.game.game_state, flag, True):
                self.assertFalse(self.game.drawer.status_window_always())


class TestStatusWindowFrames(TestCase):
    """With ALWAYS, walking redraws the window each frame over the map: it never changes while the values don't, and
    it follows them when they do."""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_the_window_on_screen_while_walking(self):
        from tests.test_character_redraw import draw_frame, make_game
        from src.windows import POPUP_WINDOW
        game = make_game('Alefgard')
        game.game_state.config.update(STATUS_WINDOW=STATUS_WINDOW_ALWAYS, NO_BATTLES=True, RENDER_TEXT=True)
        game.game_state.is_initial_dialog = False
        game.change_map(map_lookup['Alefgard'](game.config), destination_coordinates=(50, 44),
                        direction=Direction.RIGHT.value)
        tile_size = game.tile_size
        area = pygame.Rect(*(value * tile_size for value in POPUP_WINDOW))
        held_keys = defaultdict(int, {K_RIGHT: 1})
        windows = []
        with patch('src.movement.key.get_pressed', return_value=held_keys), \
                patch.object(game.cmd_menu, 'window_drop_down_effect'):
            for frame in range(3 * STEP_SYNC_FRAMES):
                game.movement.handle_player_movement()
                game.movement.sprites_frame()
                draw_frame(game)
                windows.append(pygame.image.tobytes(game.screen.subsurface(area), 'RGB'))
                if frame == 2 * STEP_SYNC_FRAMES:
                    game.player.current_hp -= 1
        self.assertGreater(game.player.rect.x // tile_size, 44)
        self.assertEqual(2, len(set(windows)))  # one picture before the HP changed, one after
        self.assertEqual(windows[0], windows[2 * STEP_SYNC_FRAMES])
        self.assertNotEqual(windows[0], windows[-1])
