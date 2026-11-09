"""The game's events (src/game_events.py): the bus that tells whoever subscribed, and the play statistics
(src/play_stats.py) counted from them, whichever PlayStats the game has."""
import contextlib
import io
import os
from unittest import TestCase
from unittest.mock import Mock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from src.battle import Battle
from src.config.test_config import test_config
from src.game_events import (HERO, ChestOpened, EventBus, FightLost, FightWon, GameEvent, GoldEarned, GoldSpent,
                             HeroDied, LevelUp, RanAway, StepTaken)
from src.play_stats import PlayStats, subscribe_play_stats
from src.player.player import Player
from tests import helpers
from tests.mock_map import MockMap


class TestEventBus(TestCase):

    def setUp(self):
        self.bus = EventBus()
        self.heard = []

    def test_handlers_hear_their_event_type_in_subscription_order(self):
        self.bus.subscribe(FightWon, lambda event: self.heard.append(('first', event.enemy_name)))
        self.bus.subscribe(FightWon, lambda event: self.heard.append(('second', event.enemy_name)))
        self.bus.subscribe(FightLost, lambda event: self.heard.append('lost'))
        self.bus.emit(FightWon('Slime'))
        self.assertEqual([('first', 'Slime'), ('second', 'Slime')], self.heard)

    def test_a_handler_for_game_event_hears_every_event_after_the_types_own(self):
        self.bus.subscribe(GameEvent, lambda event: self.heard.append(('any', type(event).__name__)))
        self.bus.subscribe(StepTaken, lambda event: self.heard.append('step'))
        self.bus.emit(StepTaken())
        self.bus.emit(GoldSpent(5))
        self.assertEqual(['step', ('any', 'StepTaken'), ('any', 'GoldSpent')], self.heard)

    def test_unsubscribe(self):
        def handler(event):
            self.heard.append(event)
        self.bus.subscribe(ChestOpened, handler)
        self.bus.unsubscribe(ChestOpened, handler)
        self.bus.unsubscribe(ChestOpened, handler)  # not subscribed any more: nothing happens
        self.bus.unsubscribe(HeroDied, handler)  # never subscribed
        self.bus.emit(ChestOpened())
        self.assertEqual([], self.heard)

    def test_a_handler_may_unsubscribe_as_it_runs(self):
        def once(event):
            self.heard.append('once')
            self.bus.unsubscribe(RanAway, once)
        self.bus.subscribe(RanAway, once)
        self.bus.subscribe(RanAway, lambda event: self.heard.append('always'))
        self.bus.emit(RanAway())
        self.bus.emit(RanAway())
        self.assertEqual(['once', 'always', 'always'], self.heard)

    def test_a_handler_that_raises_does_not_stop_the_others(self):
        def broken(event):
            raise ValueError('a bug in an achievement')
        self.bus.subscribe(LevelUp, broken)
        self.bus.subscribe(LevelUp, lambda event: self.heard.append(event.level))
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.bus.emit(LevelUp(5))
        self.assertEqual([5], self.heard)
        self.assertIn('LevelUp', stderr.getvalue())
        self.assertIn('a bug in an achievement', stderr.getvalue())

    def test_events_are_the_heros_and_frozen(self):
        self.assertEqual(HERO, GoldEarned(10).hero)
        self.assertEqual(1, GoldEarned(10, hero=1).hero)
        with self.assertRaises(AttributeError):
            GoldEarned(10).amount = 20  # type: ignore[misc]


class TestPlayStatsCountEvents(TestCase):

    def setUp(self):
        self.bus = EventBus()
        self.stats = PlayStats()
        subscribe_play_stats(self.bus, lambda: self.stats)

    def test_each_event_counts(self):
        for event in (StepTaken(), FightWon('Slime'), FightWon('Dragonlord 2'), RanAway(), FightLost(), HeroDied(),
                      GoldEarned(30), GoldSpent(12), ChestOpened(), LevelUp(2)):
            self.bus.emit(event)
        self.assertEqual(PlayStats(steps=1, fights_won=2, fights_fled=1, fights_lost=1, deaths=1, gold_earned=30,
                                   gold_spent=12, chests_opened=1,
                                   monsters_defeated={'Slime': 1, 'Dragonlord': 1}), self.stats)

    def test_replaced_stats_count_from_then_on(self):
        self.bus.emit(StepTaken())
        old, self.stats = self.stats, PlayStats()
        self.bus.emit(StepTaken())
        self.assertEqual((1, 1), (old.steps, self.stats.steps))


class TestTheGamesBus(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))  # the level-up music and the player's images need a display

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_a_loaded_or_rewound_games_stats_count(self):
        game = helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True})
        game.step_triggers.count_step()
        old = game.play_stats
        game.play_stats = old.copy()  # as a rewind or a state's restore does (src/save_state.py)
        game.step_triggers.count_step()
        self.assertEqual((1, 2), (old.steps, game.play_stats.steps))

    def test_a_level_up_is_announced_with_the_new_level(self):
        # NES DoLevelUp: LoadStats works the level out from the experience, so it can jump by more than one
        player = Player(center_point=None, images=None, current_map=MockMap(test_config))
        player.name = 'Erdrick'
        player.level = player.get_level_by_experience()
        player.update_stats_to_current_level()
        player.total_experience = 110  # level 5: four levels at once
        cmd_menu = Mock()
        battle = Battle({**test_config, 'LANGUAGE': 'English'}, 'Slime', Mock())
        battle.check_player_level_up(cmd_menu, player)
        cmd_menu.game.event_bus.emit.assert_called_once_with(LevelUp(5))

    def test_no_level_up_no_event(self):
        player = Player(center_point=None, images=None, current_map=MockMap(test_config))
        player.level = player.get_level_by_experience()
        cmd_menu = Mock()
        with patch.object(Battle, 'resume_map_music'):
            Battle({**test_config, 'LANGUAGE': 'English'}, 'Slime', Mock()).check_player_level_up(cmd_menu, player)
        cmd_menu.game.event_bus.emit.assert_not_called()
