"""Rewind (src/rewind.py): hold Backspace on the map to step back through the last snapshots. Not NES."""
import json
import os
import random
import sys
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from pygame import K_BACKSPACE, K_ESCAPE, K_k, KEYDOWN, KEYUP
from pygame.event import Event

from src.battle_controller import BattleOutcome
from src.debug_tools import DebugTools
from src.rewind import REWIND_CAPACITY, REWIND_INTERVAL_FRAMES
from src.save_state import take_snapshot
from src.virtual_joypad import VirtualJoypad
from src.waiting import WINDOW_CONTEXT
from tests.test_save_state import ALEFGARD_GRASS, SEED, SaveStateTestCase, comparable, key


def key_up(released_key):
    return Event(KEYUP, key=released_key, mod=0, unicode='', scancode=0)


def deep_size(value, seen=None) -> int:
    """The memory a value takes, with everything it holds (each object counted once)."""
    seen = set() if seen is None else seen
    if id(value) in seen:
        return 0
    seen.add(id(value))
    size = sys.getsizeof(value)
    if isinstance(value, dict):
        size += sum(deep_size(k, seen) + deep_size(v, seen) for k, v in value.items())
    elif isinstance(value, (list, tuple, set)):
        size += sum(deep_size(item, seen) for item in value)
    return size


class RewindTestCase(SaveStateTestCase):

    def setUp(self):
        super().setUp()
        self.rewind = self.game.rewind
        self.go_to(self.game, 'Brecconary')
        random.seed(SEED)

    def press_backspace(self):
        self.game._handle_pygame_events([key(K_BACKSPACE)])

    def release_backspace(self):
        self.game._handle_pygame_events([key_up(K_BACKSPACE)])


class TestRecording(RewindTestCase):

    def test_a_snapshot_every_30_frames(self):
        self.run_frames(self.game, REWIND_INTERVAL_FRAMES - 1)
        self.assertEqual(0, len(self.rewind.snapshots))
        self.run_frames(self.game, 1, first_frame=REWIND_INTERVAL_FRAMES - 1)
        self.assertEqual(1, len(self.rewind.snapshots))
        self.assertEqual(comparable(take_snapshot(self.game)), comparable(self.rewind.snapshots[-1]))
        self.run_frames(self.game, REWIND_INTERVAL_FRAMES * 3, first_frame=REWIND_INTERVAL_FRAMES)
        self.assertEqual(4, len(self.rewind.snapshots))

    def test_not_while_a_window_is_open(self):
        self.game.cmd_menu.launch_signaled = True
        with patch.object(self.game.drawer, 'draw_all'):
            self.run_frames(self.game, REWIND_INTERVAL_FRAMES * 2, script=lambda frame: set())
        self.assertEqual(0, len(self.rewind.snapshots))

    def test_the_buffer_keeps_the_last_60(self):
        for gold in range(REWIND_CAPACITY + 10):
            self.game.player.gold = gold
            self.rewind.record()
        self.assertEqual(REWIND_CAPACITY, len(self.rewind.snapshots))
        self.assertEqual([10, REWIND_CAPACITY + 9],
                         [self.rewind.snapshots[0]['hero']['gold'], self.rewind.snapshots[-1]['hero']['gold']])

    def test_memory_of_60_snapshots(self):
        """60 snapshots of a town with NPCs, after walking: a few hundred KB, nowhere near the low MB."""
        self.run_frames(self.game, REWIND_INTERVAL_FRAMES * REWIND_CAPACITY)
        self.assertEqual(REWIND_CAPACITY, len(self.rewind.snapshots))
        size = deep_size(list(self.rewind.snapshots))
        print(f"\n60 rewind snapshots: {size / 1024:.0f} KB in memory, "
              f"{sum(len(json.dumps(s)) for s in self.rewind.snapshots) / 1024:.0f} KB as JSON")
        self.assertLess(size, 2 * 1024 * 1024)


class TestRewinding(RewindTestCase):

    def test_rewinding_restores_each_snapshot_exactly(self):
        self.run_frames(self.game, REWIND_INTERVAL_FRAMES * 4 + 7)
        snapshots = [comparable(snapshot) for snapshot in self.rewind.snapshots]
        self.assertEqual(4, len(snapshots))
        self.press_backspace()
        self.assertTrue(self.rewind.active)
        self.assertEqual(snapshots[3], comparable(take_snapshot(self.game)))
        for position in (2, 1, 0):
            self.rewind.step_back()
            self.assertEqual(snapshots[position], comparable(take_snapshot(self.game)))
        self.rewind.step_back()  # the oldest stays
        self.assertEqual(snapshots[0], comparable(take_snapshot(self.game)))

    def test_holding_backspace_steps_back_every_few_real_frames(self):
        self.run_frames(self.game, REWIND_INTERVAL_FRAMES * 3)
        with patch('src.rewind.time.get_ticks', return_value=1000):
            self.press_backspace()
        self.assertEqual(2, self.rewind.position)
        frame_counter = self.game.movement.frame_counter
        with patch('src.game.Game.read_events'):
            for now, position in ((1030, 2), (1066, 1), (1080, 1), (1140, 0), (1300, 0)):
                with patch('src.rewind.time.get_ticks', return_value=now):
                    self.game.run_due_frames()
                self.assertEqual(position, self.rewind.position, now)
        # no map frame ran meanwhile
        self.assertEqual(comparable(self.rewind.snapshots[0]), comparable(take_snapshot(self.game)))
        self.assertNotEqual(frame_counter, self.game.movement.frame_counter)

    def test_letting_go_plays_on_and_drops_the_snapshots_after(self):
        self.run_frames(self.game, REWIND_INTERVAL_FRAMES * 5)
        kept = [comparable(snapshot) for snapshot in list(self.rewind.snapshots)[:3]]
        self.press_backspace()
        self.rewind.step_back()
        self.rewind.step_back()
        self.release_backspace()
        self.assertFalse(self.rewind.active)
        self.assertEqual(kept, [comparable(snapshot) for snapshot in self.rewind.snapshots])
        self.assertEqual(kept[-1], comparable(take_snapshot(self.game)))
        # play goes on from there, and the next snapshot comes 30 frames later
        self.run_frames(self.game, REWIND_INTERVAL_FRAMES, first_frame=1000)
        self.assertEqual(4, len(self.rewind.snapshots))
        self.assertNotEqual(kept[-1], comparable(self.rewind.snapshots[-1]))

    def test_rewinding_plays_out_the_same_again(self):
        """Letting go on a snapshot and pressing the same keys gives the same frames as the first time."""
        self.run_frames(self.game, REWIND_INTERVAL_FRAMES)
        expected = self.run_frames(self.game, 150, first_frame=REWIND_INTERVAL_FRAMES)
        while len(self.rewind.snapshots) > 1:
            self.rewind.snapshots.pop()
        self.press_backspace()
        self.release_backspace()
        self.assertEqual(expected, self.run_frames(self.game, 150, first_frame=REWIND_INTERVAL_FRAMES))

    def test_across_maps(self):
        self.run_frames(self.game, REWIND_INTERVAL_FRAMES)
        brecconary = comparable(self.rewind.snapshots[-1])
        self.go_to(self.game, 'Alefgard', ALEFGARD_GRASS)
        self.run_frames(self.game, REWIND_INTERVAL_FRAMES)
        self.press_backspace()
        self.assertEqual('Alefgard', self.game.current_map.identifier)
        alefgard_map = self.game.current_map
        self.rewind.step_back()
        self.assertEqual('Brecconary', self.game.current_map.identifier)
        self.assertEqual(brecconary, comparable(take_snapshot(self.game)))
        self.assertIsNot(alefgard_map, self.game.current_map)

    def test_the_same_map_is_not_loaded_again(self):
        self.run_frames(self.game, REWIND_INTERVAL_FRAMES * 2)
        current_map = self.game.current_map
        self.press_backspace()
        self.rewind.step_back()
        self.assertIs(current_map, self.game.current_map)

    def test_the_screen_is_redrawn_cleanly(self):
        self.game.config['NO_BLIT'] = False
        pygame.display.set_mode((256 * 3, 240 * 3))
        game = self.game
        game.screen = pygame.display.get_surface()
        screens = []
        for frame in range(REWIND_INTERVAL_FRAMES * 3):
            recorded = len(self.rewind.snapshots)
            self.run_frames(game, 1, first_frame=frame)
            if len(self.rewind.snapshots) > recorded:
                screens.append(pygame.image.tobytes(game.screen, 'RGB'))
        self.assertEqual(3, len(screens))
        self.press_backspace()
        for screen in reversed(screens):
            game.drawer.draw_all(game, game.movement.sprites_animate)
            self.assertEqual(screen, pygame.image.tobytes(game.screen, 'RGB'))
            self.rewind.step_back()


class TestFights(RewindTestCase):

    def test_the_snapshot_before_a_fight(self):
        game = self.game
        self.go_to(game, 'Alefgard', ALEFGARD_GRASS)
        game.config['FORCE_BATTLE'] = True
        frame_starts = []
        fights = []

        def fight(enemy_name):
            fights.append((enemy_name, comparable(frame_starts[-1])))
            return BattleOutcome.VICTORY

        real_map_frame = game.map_frame

        def map_frame():
            frame_starts.append(take_snapshot(game))
            real_map_frame()

        with patch.object(game.battle_ctrl, 'fight_enemy', side_effect=fight), \
                patch.object(game, 'map_frame', side_effect=map_frame):
            self.run_frames(game, 20)
            self.assertEqual(1, len(fights))
            enemy, before_fight = fights[0]
            self.assertEqual(before_fight, comparable(self.rewind.snapshots[-1]))
            self.run_frames(game, 5, first_frame=20)
            # after the fight, rewinding reaches the snapshot from just before it
            self.press_backspace()
            self.assertEqual(before_fight, comparable(take_snapshot(game)))
            self.assertEqual(before_fight, comparable(frame_starts[15]))  # the start of the step's last frame
            self.release_backspace()
            # and the same fight starts again
            self.run_frames(game, 1, first_frame=15)
        self.assertEqual(2, len(fights))
        self.assertEqual(fights[0], fights[1])

    def test_not_in_a_fight(self):
        """A fight reads the keys in its own loops: Backspace there doesn't rewind."""
        game = self.game
        self.run_frames(game, REWIND_INTERVAL_FRAMES)
        player = game.player
        player.total_experience = 65535
        player.level = player.get_level_by_experience()
        player.update_stats_to_current_level()
        player.restore_hp()
        player.weapon = "Erdrick's Sword"
        player.update_attack_power()

        class FightDriver:
            def __init__(self):
                self.pressed = False

            def update(self, joypad, context):
                if not self.pressed:
                    self.pressed = True
                    pygame.event.post(key(K_BACKSPACE))
                if context == WINDOW_CONTEXT and K_k not in joypad.held:
                    joypad.tap(K_k, 2)

            def real_key(self, current_event):
                return True

        joypad = VirtualJoypad(FightDriver())
        joypad.connect()
        self.addCleanup(joypad.disconnect)
        with patch.object(self.rewind, 'start') as start:
            outcome = game.battle_ctrl.launch_fight('Slime')
            start.assert_not_called()
        self.assertIn(outcome, (BattleOutcome.VICTORY, BattleOutcome.ESCAPED))
        self.assertFalse(self.rewind.active)


class TestWhenItCantRewind(RewindTestCase):

    def test_nothing_recorded(self):
        before = comparable(take_snapshot(self.game))
        self.press_backspace()
        self.assertFalse(self.rewind.active)
        self.assertEqual(before, comparable(take_snapshot(self.game)))

    def test_not_with_a_window_open_or_asked_for(self):
        self.run_frames(self.game, REWIND_INTERVAL_FRAMES)
        for setup in ('launch_signaled', 'paused', 'pause_requested'):
            with self.subTest(setup=setup):
                if setup == 'launch_signaled':
                    self.game.cmd_menu.launch_signaled = True
                else:
                    setattr(self.game, setup, True)
                self.press_backspace()
                self.assertFalse(self.rewind.active)
                self.game.cmd_menu.launch_signaled = self.game.paused = self.game.pause_requested = False

    def test_other_keys_wait_while_rewinding(self):
        self.run_frames(self.game, REWIND_INTERVAL_FRAMES)
        self.press_backspace()
        self.game._handle_pygame_events([key(K_k)])
        self.assertFalse(self.game.cmd_menu_requested)
        self.release_backspace()
        self.game._handle_pygame_events([key(K_k)])
        self.assertTrue(self.game.cmd_menu_requested or self.game.cmd_menu.launch_signaled)


class TestBackspaceElsewhere(RewindTestCase):

    def test_the_debug_list_filter_still_erases(self):
        self.run_frames(self.game, REWIND_INTERVAL_FRAMES)
        tools = DebugTools(self.game)
        typed = [Event(KEYDOWN, key=pygame.key.key_code(letter), mod=0, unicode=letter, scancode=0)
                 for letter in 'brecx']
        for current_event in [*typed, key(K_BACKSPACE), key_up(K_BACKSPACE), key(pygame.K_RETURN)]:
            pygame.event.post(current_event)
        with patch.object(tools, 'draw_list'):
            self.assertEqual('Brecconary', tools.pick('Warp', ['Alefgard', 'Brecconary']))
        self.assertFalse(self.rewind.active)
        pygame.event.post(key(K_ESCAPE))
        pygame.event.clear()
