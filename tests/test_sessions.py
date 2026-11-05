"""Hero sessions (src/sessions.py): each hero's own part of the game, in use in their own task."""
from collections import defaultdict
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import K_DOWN, K_LEFT, K_UP

from src.config.test_config import test_config
from src.party import new_hero
from src.sessions import SESSION_ATTRIBUTES, HeroSession, session_in_use, use_session
from src.tasks import Scheduler, Task, next_task_frame
from tests import helpers


class SessionTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.addCleanup(patch.stopall)
        self.game = helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True})
        self.game.game_state.is_initial_dialog = False
        self.ann = self.game.player
        self.ann.name = 'Ann'
        self.gwen = new_hero(self.game, 'Gwen')


class TestTheAttributes(SessionTestCase):

    def test_the_first_heros_by_default(self):
        self.assertIsNone(session_in_use())
        self.assertIs(self.game.main_session, self.game.current_session)
        for name in SESSION_ATTRIBUTES:
            with self.subTest(name=name):
                self.assertIs(getattr(self.game.main_session, name), getattr(self.game, name))
                self.assertNotIn(name, vars(self.game))

    def test_written_in_the_session_in_use(self):
        other = HeroSession('other')
        with use_session(other):
            self.game.repel_timer = 99
            self.assertEqual(99, self.game.repel_timer)
        self.assertEqual(0, self.game.repel_timer)
        self.assertEqual(99, other.repel_timer)

    def test_patching_one_puts_it_back(self):
        cmd_menu = self.game.cmd_menu
        with patch.object(self.game, 'cmd_menu') as patched:
            self.assertIs(patched, self.game.cmd_menu)
        self.assertIs(cmd_menu, self.game.cmd_menu)

    def test_a_missing_one_is_an_attribute_error(self):
        with use_session(HeroSession('empty')):
            self.assertFalse(hasattr(self.game, 'player'))


class TestASecondHero(SessionTestCase):

    def setUp(self):
        super().setUp()
        self.session = self.game.add_hero_session(self.gwen, 'Brecconary')

    def test_their_own_map_and_everything_else(self):
        with use_session(self.session):
            self.assertIs(self.gwen, self.game.player)
            self.assertEqual('Brecconary', self.game.current_map.identifier)
            self.assertEqual(self.game.current_map.initial_coordinates, (self.gwen.row, self.gwen.column))
            gwens = {name: getattr(self.game, name) for name in ('cmd_menu', 'battle_ctrl', 'movement', 'camera',
                                                                 'map_mgr', 'drawer', 'step_triggers')}
            self.assertIs(self.gwen, self.game.cmd_menu.player)
        self.assertIs(self.ann, self.game.player)
        self.assertEqual('TantegelThroneRoom', self.game.current_map.identifier)
        for name, gwens_own in gwens.items():
            with self.subTest(name=name):
                self.assertIsNot(gwens_own, getattr(self.game, name))

    def test_the_world_is_shared(self):
        with use_session(self.session):
            self.game.story_flags.rainbow_bridge_built = True
            stats = self.game.play_stats
        self.assertTrue(self.game.story_flags.rainbow_bridge_built)
        self.assertIs(stats, self.game.play_stats)

    def test_both_walk_at_once_in_their_own_tasks(self):
        """Ann walks down in the throne room while Gwen walks up in Brecconary, each a map frame at a time in a task
        of their own."""
        held = {'Ann': {K_DOWN}, 'Gwen': {K_UP}}
        start = {'Ann': (self.ann.row, self.ann.column), 'Gwen': (self.gwen.row, self.gwen.column)}

        def walk(name, session):
            def run():
                with use_session(session):
                    for _ in range(40):
                        keys = defaultdict(int, {pressed: 1 for pressed in held[name]})
                        with patch('src.movement.key') as movement_key:
                            movement_key.get_pressed.return_value = keys
                            self.game.map_frame()
                        next_task_frame()
            return run
        scheduler = Scheduler()
        scheduler.add(Task('Ann', walk('Ann', self.game.main_session)))
        scheduler.add(Task('Gwen', walk('Gwen', self.session)))
        with patch.object(self.game.autosave, 'frame'):
            scheduler.run_until_done(100)
        self.assertGreater(self.ann.row, start['Ann'][0])  # down, in the throne room
        self.assertLess(self.gwen.row, start['Gwen'][0])  # up, in Brecconary
        self.assertEqual('TantegelThroneRoom', self.game.current_map.identifier)
        with use_session(self.session):
            self.assertEqual('Brecconary', self.game.current_map.identifier)

    def test_a_map_change_is_the_heros_own(self):
        """Gwen walks left out of Brecconary onto the overworld; Ann stays in the throne room."""
        def leave():
            with use_session(self.session):
                for _ in range(60):
                    with patch('src.movement.key') as movement_key:
                        movement_key.get_pressed.return_value = defaultdict(int, {K_LEFT: 1})
                        self.game.map_frame()
                    next_task_frame()
        scheduler = Scheduler()
        scheduler.add(Task('Gwen', leave))
        with patch.object(self.game.autosave, 'frame'), patch('src.map_manager.screen_fade'):
            scheduler.run_until_done(100)
        with use_session(self.session):
            self.assertEqual('Alefgard', self.game.current_map.identifier)
            self.assertIs(self.gwen, self.game.player)
        self.assertEqual('TantegelThroneRoom', self.game.current_map.identifier)
        self.assertIs(self.ann, self.game.player)
