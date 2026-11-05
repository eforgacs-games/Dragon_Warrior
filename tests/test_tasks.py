"""Cooperative tasks (src/tasks.py): the game's own loops running side by side, a frame at a time."""
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import K_DOWN, K_k, KEYDOWN
from pygame.event import Event

from src.config.test_config import test_config
from src.controls import PLAYER_ONE, PLAYER_TWO, input_player, player_input, reset_controls
from src.party import new_hero
from src.selection import run_selection, stop_at_edges
from src.tasks import Scheduler, Task, current_task, next_task_frame
from src.waiting import frames_to_ms, get_events, wait, wait_frames
from tests import helpers


def key(pressed_key):
    return Event(KEYDOWN, key=pressed_key, mod=0)


class TestTasks(TestCase):

    def setUp(self):
        self.addCleanup(patch.stopall)
        self.clock = helpers.fake_game_clock()

    def tick(self):
        self.clock.advance_frames(1)

    def test_outside_a_task_nothing_changes(self):
        self.assertIsNone(current_task())
        self.assertFalse(next_task_frame())

    def test_a_wait_takes_frames_and_lets_the_others_go_on(self):
        log = []

        def waiter():
            log.append('waiting')
            wait_frames(3)
            log.append('waited')

        def counter():
            for number in range(5):
                log.append(number)
                next_task_frame()
        scheduler = Scheduler()
        scheduler.add(Task('waiter', waiter))
        scheduler.add(Task('counter', counter))
        scheduler.run_until_done(20, between_frames=self.tick)
        self.assertEqual(['waiting', 0, 1, 2, 3, 'waited', 4], log)

    def test_each_task_reads_its_own_events(self):
        answers = {}

        def menu(name):
            def run():
                answer = run_selection(lambda index, visible: None, 0, move=stop_at_edges(3))
                answers[name] = answer.entry
            return run
        scheduler = Scheduler()
        one, two = scheduler.add(Task('one', menu('one'))), scheduler.add(Task('two', menu('two')))
        presses = {one: [[key(K_DOWN)], [], [key(K_k)]], two: [[], [key(K_DOWN)], [key(K_DOWN)], [], [key(K_k)]]}
        for frame in range(40):
            for task in (one, two):
                if presses[task]:
                    task.events.extend(presses[task].pop(0))
            scheduler.run_frame()
            self.tick()
            if not scheduler.tasks:
                break
        self.assertEqual({'one': 1, 'two': 2}, answers)

    def test_get_events_in_a_task(self):
        seen = []
        scheduler = Scheduler()
        task = scheduler.add(Task('reader', lambda: seen.append(get_events())))
        task.events = [key(K_k)]
        scheduler.run_frame()
        self.assertEqual([[key(K_k)]], seen)

    def test_each_task_has_its_own_player(self):
        reset_controls()
        seen = []

        def as_player(player):
            def run():
                with player_input(player):
                    next_task_frame()
                    seen.append(input_player())
            return run
        scheduler = Scheduler()
        scheduler.add(Task('one', as_player(PLAYER_ONE)))
        scheduler.add(Task('two', as_player(PLAYER_TWO)))
        scheduler.run_until_done(5)
        self.assertEqual([PLAYER_ONE, PLAYER_TWO], seen)
        self.assertEqual(PLAYER_ONE, input_player())

    def test_an_exception_ends_the_task_and_goes_up(self):
        def broken():
            next_task_frame()
            raise ValueError("broken")
        scheduler = Scheduler()
        task = scheduler.add(Task('broken', broken))
        scheduler.run_frame()
        self.assertRaises(ValueError, scheduler.run_frame)
        self.assertTrue(task.done)

    def test_closing_ends_a_waiting_task_at_once(self):
        log = []

        def waiter():
            try:
                wait_frames(100)
            finally:
                log.append('unwound')
        scheduler = Scheduler()
        task = scheduler.add(Task('waiter', waiter))
        scheduler.run_frame()
        self.assertEqual([], log)
        scheduler.close()
        self.assertEqual(['unwound'], log)
        self.assertTrue(task.done)
        self.assertEqual([], scheduler.tasks)
        task.close()  # twice is nothing

    def test_a_real_wait_outside_a_task_still_waits(self):
        start = self.clock.ms
        wait(100)
        self.assertGreaterEqual(self.clock.ms - start, 100)


class TestAFightBesideAnotherTask(TestCase):
    """The game's real fight loop (BattleController.fight_enemy, with its dialogs, waits and sounds) in one task, while
    another task goes on frame by frame: the heart of free roam."""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.addCleanup(patch.stopall)
        self.clock = helpers.fake_game_clock()
        self.game = helpers.new_game({**test_config, 'NO_WAIT': False, 'RENDER_TEXT': False, 'NO_BLIT': True})
        self.game.game_state.is_initial_dialog = False
        self.game.player.name = 'Ann'
        self.game.player.current_hp = 99
        self.game.player.strength = 99
        self.game.player.update_attack_power()
        self.game.companion = new_hero(self.game, 'Gwen')

    def test_the_fight_takes_frames_while_the_other_task_goes_on(self):
        game = self.game
        game.auto_battle = True
        game.battle_ctrl.last_battle_action = 'Fight'
        frames_while_fighting = []
        outcome = []

        def fight():
            outcome.append(game.battle_ctrl.fight_enemy('Slime'))

        def walker():
            while not outcome:
                frames_while_fighting.append(self.clock.ms)
                next_task_frame()
        scheduler = Scheduler()
        fighting = scheduler.add(Task('fight', fight))
        scheduler.add(Task('walker', walker))
        with patch.object(game.cmd_menu, 'wait_for_button'), patch.object(game.cmd_menu, 'show_text_in_dialog_box'):
            scheduler.run_until_done(20_000, between_frames=lambda: self.clock.advance_frames(1))
        self.assertTrue(outcome, "the fight didn't end")
        self.assertGreater(fighting.frames, 30)  # it took many frames: its waits were frames, not sleeps
        self.assertGreater(len(frames_while_fighting), 30)  # and the other task ran on every one of them
        self.assertGreater(self.clock.ms, frames_to_ms(30))
