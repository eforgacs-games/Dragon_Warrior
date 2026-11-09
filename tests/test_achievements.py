"""Achievements (src/achievements.py): when each is earned, the option and the cheats, the file they're kept in, the
banner, the page and the T key."""
import json
import os
import tempfile
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import K_t, KEYDOWN, Surface
from pygame.event import Event

from data.text.locales import catalog_tools
from src.achievements import ACHIEVEMENTS, ACHIEVEMENTS_BY_KEY, ACHIEVEMENTS_FILE_NAME, BANNER_MS, EVERY_MONSTER, \
    UNLOCKED_LABEL, AchievementBanner, Achievements, achievement_texts, achievements_path, load_unlocked, page_lines
from src.config.test_config import test_config
from src.controls import ACTIONS_BY_NAME, reset_controls
from src.game_events import ChestOpened, FightWon, LevelUp, StepTaken
from src.game_options import ACHIEVEMENTS as ACHIEVEMENTS_OPTION, DEFAULT_OPTIONS, options_from_save
from src.message_log import LINE_WIDTH, text_width
from src.options_overlay import PRESET_MODERN, PRESET_NES, preset_values
from src.play_stats import PlayStats
from src.story_flags import StoryFlags
from tests import helpers


def key(pressed_key: int) -> Event:
    return Event(KEYDOWN, key=pressed_key, mod=0)


def fake_game(**config) -> SimpleNamespace:
    """What the achievements read of a game: its config, stats, story flags and hero."""
    return SimpleNamespace(game_state=SimpleNamespace(config={'ACHIEVEMENTS': True, **config}),
                           play_stats=PlayStats(), story_flags=StoryFlags(),
                           player=SimpleNamespace(level=1, gold=0, weapon='', armor=''))


def earned(game: SimpleNamespace) -> set[str]:
    return {achievement.key for achievement in ACHIEVEMENTS if achievement.earned(game)}


class TestWhenEachIsEarned(TestCase):

    def setUp(self):
        self.game = fake_game()

    def test_nothing_at_the_start(self):
        self.assertEqual(set(), earned(self.game))

    def test_fights(self):
        self.game.play_stats.won_fight('Slime')
        self.assertEqual({'first_victory'}, earned(self.game))
        self.game.play_stats.fights_won = 100
        self.assertIn('many_fights', earned(self.game))

    def test_the_guardians(self):
        for monster, achievement in (('Golem', 'golem'), ('Green Dragon', 'green_dragon'),
                                     ('Metal Slime', 'metal_slime')):
            with self.subTest(monster=monster):
                self.game.play_stats.won_fight(monster)
                self.assertIn(achievement, earned(self.game))

    def test_the_story(self):
        flags = self.game.story_flags
        flags.gwaelin_returned = flags.death_necklace_found = flags.rainbow_bridge_built = True
        self.assertEqual({'gwaelin_home', 'death_necklace', 'rainbow_bridge'}, earned(self.game))

    def test_erdricks_armor_and_sword_together(self):
        self.game.player.armor = "Erdrick's Armor"
        self.assertNotIn('erdricks_heir', earned(self.game))
        self.game.player.weapon = "Erdrick's Sword"
        self.assertIn('erdricks_heir', earned(self.game))

    def test_the_dragonlord_and_the_challenges(self):
        self.game.player.level = 20
        self.game.play_stats.play_time_ms = 2 * 60 * 60 * 1000 - 1
        self.game.play_stats.won_fight('Dragonlord 2')  # his two forms are one fight, counted as the Dragonlord
        self.assertLessEqual({'dragonlord', 'no_deaths', 'low_level', 'fast'}, earned(self.game))

    def test_the_challenges_missed(self):
        self.game.player.level = 21
        self.game.play_stats.play_time_ms = 2 * 60 * 60 * 1000
        self.game.play_stats.deaths = 1
        self.game.play_stats.won_fight('Dragonlord 2')
        self.assertEqual({'dragonlord', 'first_victory', 'first_death', 'level_10', 'level_20'},
                         earned(self.game))

    def test_every_monster(self):
        for monster in sorted(EVERY_MONSTER - {'Slime'}):
            self.game.play_stats.won_fight(monster)
        self.assertNotIn('every_monster', earned(self.game))
        self.game.play_stats.won_fight('Slime')
        self.assertIn('every_monster', earned(self.game))
        self.assertNotIn('Dragonlord 2', EVERY_MONSTER)
        self.assertIn('Dragonlord', EVERY_MONSTER)

    def test_levels(self):
        for level, achievements in ((9, set()), (10, {'level_10'}), (20, {'level_10', 'level_20'}),
                                    (30, {'level_10', 'level_20', 'level_30'})):
            with self.subTest(level=level):
                self.game.player.level = level
                self.assertEqual(achievements, earned(self.game))

    def test_counts(self):
        self.game.play_stats.fights_fled = 50
        self.game.play_stats.steps = 10000
        self.game.player.gold = 65535
        self.game.play_stats.deaths = 1
        self.assertEqual({'many_escapes', 'many_steps', 'max_gold', 'first_death'}, earned(self.game))

    def test_keys_are_unique(self):
        self.assertEqual(len(ACHIEVEMENTS), len(ACHIEVEMENTS_BY_KEY))


class TestUnlocking(TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.path = os.path.join(self.tmp_dir.name, ACHIEVEMENTS_FILE_NAME)
        self.game = fake_game()
        self.game.play_stats.won_fight('Slime')

    def achievements(self) -> Achievements:
        return Achievements(self.game, self.path)  # type: ignore[arg-type]

    def test_unlocked_once_saved_and_shown(self):
        achievements = self.achievements()
        self.assertEqual(['first_victory'], [achievement.key for achievement in achievements.check()])
        self.assertEqual([], achievements.check())
        self.assertTrue(achievements.is_unlocked('first_victory'))
        self.assertEqual(['first_victory'], [achievement.key for achievement in achievements.banner.waiting])
        self.assertEqual({'first_victory'}, set(load_unlocked(self.path)[0]))
        self.assertTrue(self.achievements().is_unlocked('first_victory'))

    def test_nothing_with_the_option_off(self):
        self.game.game_state.config['ACHIEVEMENTS'] = False
        self.assertEqual([], self.achievements().check())
        self.assertFalse(os.path.exists(self.path))

    def test_turning_it_on_later_unlocks_what_was_done(self):
        self.game.game_state.config['ACHIEVEMENTS'] = False
        achievements = self.achievements()
        achievements.check()
        self.game.game_state.config['ACHIEVEMENTS'] = True
        self.assertEqual(['first_victory'], [achievement.key for achievement in achievements.check()])

    def test_nothing_while_a_cheat_is_on(self):
        for cheat in ('GOD_MODE', 'DEBUG_KEYS', 'CHEAT_KEYS'):
            with self.subTest(cheat=cheat):
                self.game.game_state.config[cheat] = True
                self.assertEqual([], self.achievements().check())
                self.game.game_state.config[cheat] = False

    def test_kept_nowhere_without_a_path(self):
        achievements = Achievements(self.game, None)  # type: ignore[arg-type]
        self.assertEqual(1, len(achievements.check()))
        self.assertEqual([], os.listdir(self.tmp_dir.name))

    def test_a_newer_builds_entries_are_kept(self):
        with open(self.path, 'w', encoding='utf-8') as achievements_file:
            json.dump({'version': 9, 'unlocked': {'future': '2030-01-01'}, 'extra': [1]}, achievements_file)
        self.achievements().check()
        with open(self.path, encoding='utf-8') as achievements_file:
            saved = json.load(achievements_file)
        self.assertEqual(9, saved['version'])
        self.assertEqual([1], saved['extra'])
        self.assertEqual({'future', 'first_victory'}, set(saved['unlocked']))

    def test_a_damaged_file_is_none(self):
        for text in ('not json', '[1, 2]', '{"unlocked": 3}'):
            with self.subTest(text=text):
                with open(self.path, 'w', encoding='utf-8') as achievements_file:
                    achievements_file.write(text)
                self.assertEqual({}, self.achievements().unlocked)

    def test_a_file_that_cant_be_written_only_warns(self):
        achievements = Achievements(self.game, os.path.join(self.path, 'in', 'a', 'file'))  # type: ignore[arg-type]
        with open(self.path, 'w') as blocking_file:  # a file where a folder should be
            blocking_file.write('')
        with patch('builtins.print') as warning:
            self.assertEqual(1, len(achievements.check()))
        warning.assert_called_once()


class TestThePath(TestCase):

    def test_next_to_the_settings(self):
        self.assertEqual(os.path.join('folder', ACHIEVEMENTS_FILE_NAME),
                         achievements_path({'SETTINGS_PATH': os.path.join('folder', 'settings.json')}))

    def test_nowhere_when_the_settings_are_kept_nowhere(self):
        self.assertIsNone(achievements_path({'SETTINGS_PATH': None}))
        self.assertIsNone(achievements_path(test_config))


class TestTheBanner(TestCase):

    def test_one_after_another(self):
        banner = AchievementBanner()
        first, second = ACHIEVEMENTS[:2]
        self.assertIsNone(banner.current(0))
        banner.show(first)
        banner.show(second)
        self.assertIs(first, banner.current(1000))
        self.assertIs(first, banner.current(1000 + BANNER_MS - 1))
        self.assertIs(second, banner.current(1000 + BANNER_MS))
        self.assertIs(second, banner.current(1000 + 2 * BANNER_MS - 1))
        self.assertIsNone(banner.current(1000 + 2 * BANNER_MS))

    def test_drawn(self):
        pygame.init()
        screen = Surface((256, 240))
        banner = AchievementBanner()
        banner.show(ACHIEVEMENTS[0])
        with patch('src.achievements.get_ticks', return_value=0):
            banner.draw(screen, (252, 252, 252), {**test_config, 'NO_BLIT': False}, str)
        self.assertTrue(pygame.image.tobytes(screen, 'RGB').strip(b'\x00'))  # something was drawn


class TestThePage(TestCase):

    def test_the_count_then_each_one(self):
        lines = page_lines({'first_victory': '2026-11-05', 'unknown': '2030-01-01'})
        self.assertTrue(lines[0].startswith(UNLOCKED_LABEL))
        self.assertTrue(lines[0].endswith(f'1/{len(ACHIEVEMENTS)}'))
        self.assertEqual(['', 'FIRST VICTORY', 'Win a fight.'], [lines[1], lines[2].split()[0] + ' ' +
                                                                 lines[2].split()[1], lines[3].strip()])
        self.assertTrue(lines[2].endswith('2026-11-05'))
        self.assertEqual('STONE GUARDIAN', lines[5])  # not unlocked: no day
        self.assertTrue(all(text_width(line) <= LINE_WIDTH for line in lines))

    def test_texts_are_in_the_catalog(self):
        messages = catalog_tools.dynamic_messages()
        for text in achievement_texts():
            with self.subTest(text=text):
                self.assertIn('src/achievements.py', messages[text])

    def test_titles_fit_the_banner(self):
        for achievement in ACHIEVEMENTS:
            with self.subTest(achievement=achievement.key):
                self.assertLessEqual(text_width(achievement.title), 24)


class TestTheOption(TestCase):

    def test_off_on_the_nes_and_on_in_modern(self):
        self.assertFalse(DEFAULT_OPTIONS.achievements)
        self.assertFalse(options_from_save({}).achievements)
        self.assertEqual('Achievements', ACHIEVEMENTS_OPTION.save_key)
        self.assertFalse(preset_values(PRESET_NES)['ACHIEVEMENTS'])
        self.assertTrue(preset_values(PRESET_MODERN)['ACHIEVEMENTS'])

    def test_the_key(self):
        self.assertEqual("TROPHIES", ACTIONS_BY_NAME['TROPHIES'].label)
        self.assertEqual(K_t, ACTIONS_BY_NAME['TROPHIES'].keys[0].key)


class TestInTheGame(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        reset_controls()
        self.addCleanup(reset_controls)
        self.addCleanup(patch.stopall)
        self.game = helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True,
                                      'ACHIEVEMENTS': True})
        self.game.game_state.is_initial_dialog = False

    def unlocked(self) -> set[str]:
        return set(self.game.achievements.unlocked)

    def test_kept_nowhere_in_the_tests(self):
        self.assertIsNone(self.game.achievements.path)

    def test_a_fight_won(self):
        self.game.event_bus.emit(FightWon('Metal Slime'))  # the stats count it first
        self.assertEqual({'first_victory', 'metal_slime'}, self.unlocked())

    def test_a_level_up(self):
        self.game.player.level = 10
        self.game.event_bus.emit(LevelUp(10))
        self.assertEqual({'level_10'}, self.unlocked())

    def test_a_story_event_by_the_next_step(self):
        self.game.story_flags.rainbow_bridge_built = True
        self.game.event_bus.emit(ChestOpened())
        self.assertEqual({'rainbow_bridge'}, self.unlocked())
        self.game.story_flags.gwaelin_returned = True
        self.game.event_bus.emit(StepTaken())
        self.assertIn('gwaelin_home', self.unlocked())

    def test_kept_across_a_loaded_log(self):
        self.game.event_bus.emit(FightWon('Slime'))
        self.game.play_stats = PlayStats()
        self.game.event_bus.emit(StepTaken())
        self.assertEqual({'first_victory'}, self.unlocked())

    def test_t_opens_the_page(self):
        with patch.object(self.game.hotkeys, 'open_achievements') as open_page:
            self.game.handle_keypresses(key(K_t))
        open_page.assert_called_once()
        self.assertFalse(self.game.achievements_requested)

    def test_not_with_the_option_off(self):
        self.game.config['ACHIEVEMENTS'] = False
        with patch.object(self.game.hotkeys, 'open_achievements') as open_page:
            self.game.handle_keypresses(key(K_t))
        open_page.assert_not_called()

    def test_the_page_closes_with_b(self):
        self.game.event_bus.emit(FightWon('Slime'))
        with patch('src.message_log.frame_events', side_effect=[[], [key(pygame.K_DOWN)], [key(pygame.K_j)]]), \
                patch('src.message_log.next_frame'):
            self.game.hotkeys.open_achievements()
