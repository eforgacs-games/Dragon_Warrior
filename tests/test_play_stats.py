"""The play statistics (src/play_stats.py) and the stats page (src/stats_screen.py): counted wherever they happen, kept
with the adventure log and save states, and shown with the STATS key (P) when the STATS PAGE option is on."""
import json
import os
import unittest
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from pygame import K_DOWN, K_ESCAPE, K_UP, K_h, K_i, K_j, K_p, K_q, KEYDOWN
from pygame.event import Event

from src import waiting
from src.battle import Battle
from src.battle_controller import BattleController
from src.common import set_gettext_language
from src.config.test_config import test_config
from src.controls import reset_controls
from src.game_events import EventBus
from src.game_options import DEFAULT_OPTIONS, STATS_PAGE, options_from_save, options_to_save
from src.catalog import po_path, read_po
from src.languages import ENGLISH, LANGUAGES
from src.message_log import LINE_WIDTH, VISIBLE_LINES, log_layout, text_width
from src.options_overlay import OPTION_ROWS, PRESET_MODERN, PRESET_NES, preset_values
from src.quest_journal import JOURNAL_LEARNED
from src.play_stats import MAX_COUNTED_FRAME_MS, SAVE_KEY, PlayStats, count_or_zero, play_time_text, \
    subscribe_play_stats
from src.save_file import SaveFile
from src.save_state import decode_snapshot, take_snapshot
from src.stats_screen import STATS_TITLE, StatsScreen, aligned, monsters_in_order, screen_texts, stat_lines
from src.translated_window import draw_translated_window
from src.window_renderer import window_tiles
from tests import helpers
from tests.test_battle_controller import make_game
from tests.test_shop_dialog import ShopDialogTestCase


def key(pressed_key):
    return Event(KEYDOWN, key=pressed_key, mod=0)


def counted() -> PlayStats:
    """Stats with every count set."""
    return PlayStats(play_time_ms=3_723_000, steps=1234, fights_won=15, fights_fled=4, fights_lost=1, deaths=2,
                     gold_earned=980, gold_spent=600, chests_opened=3, monsters_defeated={'Slime': 12, 'Drakee': 3})


class TestCounting(TestCase):

    def test_a_new_quest_starts_at_zero(self):
        stats = PlayStats()
        self.assertEqual((0, 0, 0, 0, 0, 0, 0, 0, 0, {}),
                         (stats.play_time_ms, stats.steps, stats.fights_won, stats.fights_fled, stats.fights_lost,
                          stats.deaths, stats.gold_earned, stats.gold_spent, stats.chests_opened,
                          stats.monsters_defeated))

    def test_each_count(self):
        stats = PlayStats()
        stats.take_step()
        stats.take_step()
        stats.won_fight('Slime')
        stats.won_fight('Slime')
        stats.won_fight('Drakee')
        stats.ran_away()
        stats.lost_fight()
        stats.died()
        stats.earn_gold(25)
        stats.spend_gold(10)
        stats.open_chest()
        self.assertEqual(PlayStats(steps=2, fights_won=3, fights_fled=1, fights_lost=1, deaths=1, gold_earned=25,
                                   gold_spent=10, chests_opened=1, monsters_defeated={'Slime': 2, 'Drakee': 1}),
                         stats)

    def test_the_dragonlords_final_form_is_the_dragonlord(self):
        stats = PlayStats()
        stats.won_fight('Dragonlord 2')
        self.assertEqual({'Dragonlord': 1}, stats.monsters_defeated)

    def test_no_negative_gold(self):
        stats = PlayStats()
        stats.earn_gold(-5)
        stats.spend_gold(-5)
        self.assertEqual((0, 0), (stats.gold_earned, stats.gold_spent))


class TestThePlayTime(TestCase):

    def test_the_first_tick_only_starts_the_clock(self):
        stats = PlayStats()
        stats.tick(now=5000)
        self.assertEqual(0, stats.play_time_ms)
        stats.tick(now=5016)
        stats.tick(now=6016)
        self.assertEqual(1016, stats.play_time_ms)

    def test_not_while_paused(self):
        stats = PlayStats()
        stats.tick(now=0)
        stats.tick(counting=False, now=60_000)
        stats.tick(now=60_100)
        self.assertEqual(100, stats.play_time_ms)

    def test_real_time_by_default(self):
        stats = PlayStats()
        with patch('src.play_stats.get_ticks', side_effect=[1000, 1500]):
            stats.tick()
            stats.tick()
        self.assertEqual(500, stats.play_time_ms)

    def test_a_long_gap_counts_at_most_one_frame_cap(self):
        # a machine asleep, a debugger's pause or a window being dragged between two map frames
        stats = PlayStats()
        stats.tick(now=0)
        stats.tick(now=3 * 60 * 60 * 1000)
        self.assertEqual(MAX_COUNTED_FRAME_MS, stats.play_time_ms)
        stats.tick(now=3 * 60 * 60 * 1000 + MAX_COUNTED_FRAME_MS - 1)
        self.assertEqual(2 * MAX_COUNTED_FRAME_MS - 1, stats.play_time_ms)

    def test_the_clock_never_runs_backwards(self):
        stats = PlayStats()
        stats.tick(now=1000)
        stats.tick(now=900)
        self.assertEqual(0, stats.play_time_ms)

    def test_text(self):
        self.assertEqual('0:00:00', play_time_text(0))
        self.assertEqual('0:00:59', play_time_text(59_999))
        self.assertEqual('1:02:03', play_time_text(3_723_000))
        self.assertEqual('123:04:05', play_time_text((123 * 3600 + 4 * 60 + 5) * 1000))


class TestSaving(TestCase):

    def test_round_trip(self):
        stats = counted()
        self.assertEqual(stats, PlayStats.from_save(json.loads(json.dumps(stats.to_save()))))

    def test_the_clock_is_not_saved(self):
        stats = PlayStats()
        stats.tick(now=1000)
        self.assertNotIn('clock_at', stats.to_save())
        self.assertIsNone(PlayStats.from_save(stats.to_save()).clock_at)

    def test_an_old_save_has_none(self):
        self.assertEqual(PlayStats(), PlayStats.from_save(None))
        self.assertEqual(PlayStats(), PlayStats.from_save({}))
        self.assertEqual(PlayStats(steps=5), PlayStats.from_save({'steps': 5}))

    def test_what_is_not_a_count_is_zero(self):
        stats = PlayStats.from_save({'steps': -1, 'deaths': True, 'fights_won': '3', 'gold_spent': 1.5,
                                     'monsters_defeated': {'Slime': 2, 'Drakee': 0, 'Ghost': 'many'}})
        self.assertEqual(PlayStats(monsters_defeated={'Slime': 2}), stats)
        self.assertEqual(PlayStats(), PlayStats.from_save({'monsters_defeated': ['Slime']}))
        self.assertEqual(0, count_or_zero(None))

    def test_a_copy_is_its_own(self):
        stats = counted()
        copy = stats.copy()
        copy.won_fight('Slime')
        self.assertEqual(12, stats.monsters_defeated['Slime'])

    def test_kept_with_the_adventure_log(self):
        save = SaveFile(name='Erdrick', experience=0, gold=0, inventory=[], play_stats=counted().to_save())
        written = json.loads(json.dumps(save.to_save()))
        self.assertEqual(counted().to_save(), written[SAVE_KEY])
        self.assertEqual(counted(), PlayStats.from_save(SaveFile.from_save(written).play_stats))

    def test_an_old_log_loads_with_none(self):
        old = {'Name': 'Erdrick', 'Experience': 0, 'Gold': 0, 'Inventory': []}
        self.assertEqual({}, SaveFile.from_save(old).play_stats)
        self.assertEqual(PlayStats(), PlayStats.from_save(SaveFile.from_save(old).play_stats))
        self.assertEqual({}, SaveFile.from_save({**old, SAVE_KEY: 'damaged'}).play_stats)

    def test_a_log_without_stats_is_written_back_without_them(self):
        save = SaveFile(name='Erdrick', experience=0, gold=0, inventory=[])
        self.assertNotIn(SAVE_KEY, save.to_save())


class GameTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        reset_controls()
        self.addCleanup(reset_controls)
        self.game = helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True,
                                      'STATS_PAGE': True})
        self.game.game_state.is_initial_dialog = False
        self.addCleanup(patch.stopall)


class TestTheGameCounts(GameTestCase):

    def test_steps(self):
        self.game.step_triggers.count_step()
        self.game.step_triggers.count_step()
        self.assertEqual(2, self.game.play_stats.steps)

    def test_deaths(self):
        self.game.player.current_hp = 0
        with patch.object(self.game.hero_death, 'set_post_death_attributes'), \
                patch.object(self.game.music_player, 'play_until_end'), \
                patch.object(self.game.cmd_menu, 'show_text_in_dialog_box'):
            self.game.hero_death.handle_death()
        self.assertEqual(1, self.game.play_stats.deaths)

    def test_chests_and_their_gold(self):
        cmd_menu = self.game.cmd_menu
        with patch.object(cmd_menu, 'show_text_in_dialog_box'), patch.object(cmd_menu, 'show_popup_window'), \
                patch.object(cmd_menu, 'window_drop_up_effect'), \
                patch('src.menu.roll_treasure_gold', return_value=120):
            cmd_menu.take_gold({'item': 'GOLD', 'gold': 120})
        self.assertEqual((1, 120), (self.game.play_stats.chests_opened, self.game.play_stats.gold_earned))

    def test_a_fights_gold(self):
        enemy = unittest.mock.Mock(xp=1, gold=2)
        enemy.name = 'Slime'
        current_battle = unittest.mock.Mock(config=self.game.config, _=str)
        with patch('src.battle.randomize_enemy_gold', return_value=2), \
                patch.object(self.game.cmd_menu, 'show_line_in_dialog_box'):
            Battle.enemy_defeated(current_battle, self.game.cmd_menu, self.game.screen, self.game.player, enemy)
        self.assertEqual(2, self.game.play_stats.gold_earned)

    def test_kept_with_the_adventure_log(self):
        self.game.play_stats = counted()
        saved = SaveFile.from_game(self.game.player, 'TantegelThroneRoom', self.game.story_flags, DEFAULT_OPTIONS,
                                   play_stats=self.game.play_stats.to_save()).to_save()
        self.game.play_stats = PlayStats()
        with patch.object(self.game.map_mgr, 'change_map'):
            self.game.load_game(saved)
        self.assertEqual(counted(), self.game.play_stats)

    def test_an_old_log_starts_at_zero(self):
        self.game.play_stats = counted()
        with patch.object(self.game.map_mgr, 'change_map'):
            self.game.load_game({'Name': 'Erdrick', 'Experience': 0, 'Gold': 0, 'Inventory': []})
        self.assertEqual(PlayStats(), self.game.play_stats)

    def test_kept_in_save_states(self):
        self.game.play_stats = counted()
        snapshot = json.loads(json.dumps(take_snapshot(self.game)))
        self.assertEqual(counted(), decode_snapshot(snapshot)['play_stats'])
        del snapshot['play_stats']  # a state saved before they were kept
        self.assertEqual(PlayStats(), decode_snapshot(snapshot)['play_stats'])


FRAME_MS = 16


class TestThePlayClock(GameTestCase):
    """The play time ticks on every loop's frames (src/waiting.py frame_passed), with a clock the test moves."""

    def setUp(self):
        super().setUp()
        self.now = 0
        patch('src.play_stats.get_ticks', side_effect=lambda: self.now).start()
        self.game.play_clock.running = True  # as Game.main does once the title screen is behind
        waiting.frame_passed()

    def frames(self, count: int, frame_ms: int = FRAME_MS) -> None:
        """A loop running ``count`` frames, reading the events each one, as every loop does."""
        for _ in range(count):
            self.now += frame_ms
            waiting.get_events()

    def test_the_map(self):
        with patch.object(waiting.time, 'wait'):
            for _ in range(10):
                self.now += FRAME_MS
                waiting.FrameClock(sleep=lambda seconds: None).tick()
        self.assertEqual(10 * FRAME_MS, self.game.play_stats.play_time_ms)

    def test_a_fight_adds_its_duration(self):
        def fight(run_away, current_battle):
            self.frames(300)  # five seconds of turns, messages and waits
            return True
        with patch('src.battle_controller.Battle') as battle_class, \
                patch.object(self.game.battle_ctrl, 'start_fight', return_value=False), \
                patch.object(self.game.battle_ctrl, 'step_back_after_running', return_value=False), \
                patch.object(self.game.battle_ctrl, 'handle_battle_prompts', side_effect=fight):
            battle_class.return_value.enemy.hp = 3
            self.game.battle_ctrl.run_battle(['Slime'])
        self.assertEqual(300 * FRAME_MS, self.game.play_stats.play_time_ms)

    def test_a_dialog_adds_its_duration(self):
        cmd_menu = self.game.cmd_menu
        with patch.object(cmd_menu, 'window_drop_down_effect'), patch.object(cmd_menu, 'window_drop_up_effect'), \
                patch.object(cmd_menu, 'wait_for_dialog_key', side_effect=lambda *args, **kwargs: self.frames(120)):
            cmd_menu.show_text_in_dialog_box("Welcome to Tantegel Castle.")
        self.assertEqual(120 * FRAME_MS, self.game.play_stats.play_time_ms)

    def test_a_wait_adds_its_duration(self):
        self.now += 500
        waiting.check_for_quit()
        self.assertEqual(500, self.game.play_stats.play_time_ms)

    def test_not_while_paused(self):
        self.game.paused = True
        self.frames(600)
        self.game.paused = False
        self.frames(1)
        self.assertEqual(FRAME_MS, self.game.play_stats.play_time_ms)

    def test_not_on_the_title_screen(self):
        self.game.play_clock.running = False
        self.frames(600)
        self.assertEqual(0, self.game.play_stats.play_time_ms)

    def test_not_while_a_page_is_up(self):
        self.game.play_stats_requested = True
        with patch.object(self.game.hotkeys, 'open_play_stats', side_effect=lambda: self.frames(600)):
            self.game.hotkeys.open_requested()
        self.game.config['QUEST_JOURNAL'] = JOURNAL_LEARNED
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box', side_effect=lambda *_: self.frames(600)):
            self.game.hotkeys.press_quest_journal(key(K_q))
            self.game.hotkeys.press_help(key(K_h))
        self.frames(1)
        self.assertEqual(FRAME_MS, self.game.play_stats.play_time_ms)

    def test_a_long_gap_adds_at_most_a_second(self):
        self.frames(1, frame_ms=3 * 60 * 60 * 1000)  # the machine asleep for three hours
        self.assertLessEqual(self.game.play_stats.play_time_ms, 1000)

    def test_a_loaded_game_ticks_its_own_stats(self):
        self.game.play_stats = counted()
        self.frames(2)  # its clock starts at its first frame
        self.assertEqual(counted().play_time_ms + FRAME_MS, self.game.play_stats.play_time_ms)


@patch('src.battle_controller.Battle')
class TestFights(unittest.TestCase):

    def setUp(self):
        self.game = make_game()
        self.game.play_stats = PlayStats()
        self.game.event_bus = EventBus()
        subscribe_play_stats(self.game.event_bus, lambda: self.game.play_stats)
        self.controller = BattleController(self.game)
        patch.object(self.controller, 'start_fight', return_value=False).start()
        patch.object(self.controller, 'step_back_after_running', return_value=False).start()
        self.addCleanup(patch.stopall)

    def fight(self, prompts):
        with patch.object(self.controller, 'handle_battle_prompts', side_effect=prompts):
            self.controller.run_battle(['Slime'])

    def test_won(self, mock_battle_class):
        mock_battle_class.return_value.enemy.hp = 3
        mock_battle_class.return_value.enemy.name = 'Slime'

        def kill(run_away, current_battle):
            current_battle.enemy.hp = 0
            return False
        self.fight(kill)
        self.assertEqual((1, {'Slime': 1}), (self.game.play_stats.fights_won, self.game.play_stats.monsters_defeated))

    def test_fled(self, mock_battle_class):
        mock_battle_class.return_value.enemy.hp = 3
        mock_battle_class.return_value.enemy_fled = False

        def run(run_away, current_battle):
            self.controller.player_ran_away = True
            return True
        self.fight(run)
        self.assertEqual(1, self.game.play_stats.fights_fled)

    def test_an_enemy_that_runs_away_is_not_fled(self, mock_battle_class):
        mock_battle_class.return_value.enemy.hp = 3
        mock_battle_class.return_value.enemy_fled = True
        self.fight(lambda run_away, current_battle: True)
        self.assertEqual(PlayStats(), self.game.play_stats)

    def test_lost(self, mock_battle_class):
        mock_battle_class.return_value.enemy.hp = 3

        def die(run_away, current_battle):
            self.game.player.is_dead = True
            return False
        self.fight(die)
        self.assertEqual(1, self.game.play_stats.fights_lost)


class TestShops(ShopDialogTestCase):

    def setUp(self):
        super().setUp()
        self.game.play_stats = PlayStats()

    def test_tools_bought_and_sold(self):
        shop = self.store('brecconary_item_store_inventory')
        self.run_shop(lambda: self.dialog_lookup.tool_shop(shop), [False], [0, 0])  # a Herb
        self.player.inventory = ['Wings']
        self.run_shop(lambda: self.dialog_lookup.tool_shop(shop), [True, False], [1, 0])  # sell the Wings
        self.assertEqual((35, 24), (self.game.play_stats.gold_earned, self.game.play_stats.gold_spent))

    def test_a_weapon_traded_in(self):
        self.player.weapon = 'Club'
        self.answers = [True, True, False]
        with patch.object(self.dialog_lookup, 'open_store_inventory', side_effect=['Copper Sword']):
            self.dialog_lookup.check_buy_weapons_armor(self.store('brecconary_weapons_store_inventory'))
        self.assertEqual((30, 180), (self.game.play_stats.gold_earned, self.game.play_stats.gold_spent))

    def test_keys_and_fairy_water(self):
        self.answers = [True, False]
        self.dialog_lookup.check_buy_magic_keys(53)
        self.answers = [True, False]
        self.dialog_lookup.fairy_water_shop()
        self.assertEqual(53 + 38, self.game.play_stats.gold_spent)

    def test_the_inn(self):
        self.dialog_lookup.command_menu.show_line_in_dialog_box = lambda *args, **kwargs: None
        with patch('data.text.dialog_lookup_table.screen_fade'), \
                patch.object(self.game.music_player, 'play_until_end'), \
                patch.object(self.game.music_player, 'load_and_play_music'), \
                patch.object(self.dialog_lookup.command_menu, 'show_popup_window'):
            self.dialog_lookup.inn_sleep(6)
        self.assertEqual(6, self.game.play_stats.gold_spent)


class TestTheKey(GameTestCase):

    def test_p_opens_it_on_the_map(self):
        with patch.object(self.game.hotkeys, 'open_play_stats') as open_stats:
            self.game.handle_keypresses(key(K_p))
        open_stats.assert_called_once()
        self.assertFalse(self.game.play_stats_requested)

    def test_not_with_the_option_off(self):
        self.game.config['STATS_PAGE'] = False
        with patch.object(self.game.hotkeys, 'open_play_stats') as open_stats:
            self.game.handle_keypresses(key(K_p))
        open_stats.assert_not_called()

    def test_the_play_time_stops_while_it_is_open(self):
        self.game.play_clock.running = True
        self.game.play_stats.tick(now=0)
        with patch.object(self.game.hotkeys, 'open_play_stats',
                          side_effect=lambda: self.assertFalse(self.game.play_clock.running)) as open_stats:
            self.game.handle_keypresses(key(K_p))
        open_stats.assert_called_once()
        self.assertTrue(self.game.play_clock.running)


class TestTheOption(TestCase):

    def test_the_row(self):
        row = next(row for row in OPTION_ROWS if row.config_key == 'STATS_PAGE')
        self.assertEqual(("STATS PAGE", (False, True), ("OFF (NES)", "ON")), (row.label, row.values, row.value_labels))

    def test_off_under_the_nes_preset_and_on_under_modern(self):
        self.assertFalse(preset_values(PRESET_NES)['STATS_PAGE'])
        self.assertTrue(preset_values(PRESET_MODERN)['STATS_PAGE'])

    def test_off_by_default_and_saved_with_the_log(self):
        self.assertFalse(DEFAULT_OPTIONS.stats_page)
        self.assertFalse(options_from_save({}).stats_page)
        on = DEFAULT_OPTIONS.__class__(stats_page=True)
        self.assertEqual(on, options_from_save(options_to_save(on)))
        self.assertEqual('StatsPage', STATS_PAGE.save_key)


class TestThePage(TestCase):

    def test_the_counts_then_the_monsters(self):
        lines = stat_lines(counted())
        self.assertEqual(aligned("PLAY TIME", "1:02:03"), lines[0])
        self.assertEqual(aligned("CHESTS OPENED", "3"), lines[8])
        self.assertEqual(['', "MONSTERS DEFEATED", aligned(" Slime", "12"), aligned(" Drakee", "3")], lines[9:])
        for line in lines[:9] + lines[11:]:
            self.assertEqual(LINE_WIDTH, text_width(line), line)

    def test_no_monsters_yet(self):
        self.assertEqual(9, len(stat_lines(PlayStats())))

    def test_monsters_in_the_enemy_tables_order(self):
        self.assertEqual([('Slime', 1), ('Drakee', 2), ('Dragonlord', 1), ('Unknown', 1)],
                         monsters_in_order({'Unknown': 1, 'Dragonlord': 1, 'Drakee': 2, 'Slime': 1}))

    def test_a_value_too_long_still_has_a_blank(self):
        self.assertEqual("A" * LINE_WIDTH + " 1", aligned("A" * LINE_WIDTH, "1"))

    def test_korean(self):
        _ = set_gettext_language('Korean')
        lines = stat_lines(counted(), _)
        self.assertEqual(aligned("플레이 시간", "1:02:03"), lines[0])
        self.assertEqual(aligned(" 슬라임", "12"), lines[-2])

    def test_japanese(self):
        _ = set_gettext_language('Japanese')
        lines = stat_lines(counted(), _)
        self.assertEqual(aligned("プレイ時間", "1:02:03"), lines[0])
        self.assertEqual("やっつけたまもの", lines[10])

    def test_chinese(self):
        for language, play_time, monsters in (('Traditional Chinese', "遊戲時間", "打倒的魔物"),
                                              ('Simplified Chinese', "游戏时间", "打倒的魔物")):
            with self.subTest(language):
                lines = stat_lines(counted(), set_gettext_language(language))
                self.assertEqual(aligned(play_time, "1:02:03"), lines[0])
                self.assertEqual(monsters, lines[10])

    def test_every_language_fits_and_is_translated(self):
        for language in LANGUAGES:
            with self.subTest(language.name):
                _ = set_gettext_language(language.name)
                for line in stat_lines(counted(), _):
                    self.assertLessEqual(text_width(line), LINE_WIDTH, line)
                if language is ENGLISH:
                    continue
                catalog = read_po(po_path(language.locale_code or ''))
                for text in screen_texts():
                    self.assertTrue(catalog.get(text), text)
                    # English (2014) keeps the NES words where the remake has none of its own (STEPS, ...)
                    if not helpers.drawn_in_nes_font(language):
                        self.assertNotEqual(text, _(text))

    def test_fits_the_window(self):
        window_tiles(log_layout(stat_lines(counted()), 0, title=STATS_TITLE))

    def test_drawn(self):
        pygame.init()
        screen = pygame.Surface((512, 480))
        for language in [language.name for language in LANGUAGES]:
            with self.subTest(language):
                config = {**test_config, 'LANGUAGE': language, 'RENDER_TEXT': True}
                layout = log_layout(stat_lines(counted(), set_gettext_language(language)), 0, title=STATS_TITLE)
                screen.fill((0, 0, 0))
                draw_translated_window(screen, layout, (255, 255, 255), config, set_gettext_language(language))
                self.assertIsNotNone(pygame.transform.average_color(screen))
                self.assertNotEqual((0, 0, 0, 255), tuple(pygame.transform.average_color(screen)))


class TestTheScreen(GameTestCase):

    def setUp(self):
        super().setUp()
        self.game.play_stats = counted()
        for number in range(10):
            self.game.play_stats.won_fight(f'Monster {number}')
        patch('src.selection.wait_frames').start()

    def run_screen(self, *keys):
        screen = StatsScreen(self.game)
        events = [[key(pressed_key)] for pressed_key in keys]
        with patch('src.waiting.event.get', side_effect=[[]] + events):
            screen.run()
        return screen

    def test_it_starts_at_the_top(self):
        screen = StatsScreen(self.game)
        self.assertEqual(0, screen.top)
        self.assertEqual(STATS_TITLE, screen.title)

    def test_scrolling(self):
        self.assertEqual(2, self.run_screen(K_DOWN, K_DOWN, K_j).top)
        self.assertEqual(len(StatsScreen(self.game).lines) - VISIBLE_LINES,
                         self.run_screen(*(K_DOWN,) * 30, K_j).top)
        self.assertEqual(0, self.run_screen(K_DOWN, K_UP, K_UP, K_j).top)

    def test_closing(self):
        for close in (K_j, K_ESCAPE, K_i, K_p):
            with self.subTest(key=pygame.key.name(close)):
                self.run_screen(close)

    def test_drawn_over_the_map(self):
        self.game.config['NO_BLIT'] = False
        self.addCleanup(self.game.config.__setitem__, 'NO_BLIT', True)
        with patch('src.message_log.draw_translated_window') as draw:
            self.run_screen(K_j)
        self.assertEqual(STATS_TITLE, draw.call_args.args[1].title)

    def test_opened_by_the_key(self):
        with patch('src.waiting.event.get', side_effect=[[], [key(K_j)]]):
            self.game.hotkeys.open_play_stats()
