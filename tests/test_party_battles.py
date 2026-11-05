"""A party's fights (src/party.py, src/battle_controller.py): each hero standing acts, then the enemy against one of
them; a fallen hero sits the fight out; the experience for each hero standing and the gold once."""
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

import pygame

from src.battle import Battle
from src.config.test_config import test_config
from src.party import acting, heroes, in_party_mode, living, new_hero
from tests import helpers
from tests.test_battle_controller import make_battle


class PartyTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.addCleanup(patch.stopall)
        self.game = helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True})
        self.hero = self.game.player
        self.hero.name = 'Ann'
        self.companion = self.game.companion = new_hero(self.game, 'Gwen')
        self.controller = self.game.battle_ctrl
        patch.object(self.game.cmd_menu, 'show_line_in_dialog_box').start()
        patch.object(self.game.drawer, 'draw_hovering_stats_window').start()


class TestActing(PartyTestCase):

    def test_the_hero_is_game_player_for_the_block(self):
        cmd_menu = self.game.cmd_menu
        with acting(self.game, self.companion):
            self.assertIs(self.companion, self.game.player)
            self.assertIs(self.companion, cmd_menu.player)
            self.assertIs(self.companion, cmd_menu.dialog_lookup.player)
        self.assertIs(self.hero, self.game.player)
        self.assertIs(self.hero, cmd_menu.player)
        self.assertIs(self.hero, cmd_menu.dialog_lookup.player)

    def test_put_back_after_an_exception(self):
        def fail_while_acting():
            with acting(self.game, self.companion):
                raise ValueError
        self.assertRaises(ValueError, fail_while_acting)
        self.assertIs(self.hero, self.game.player)

    def test_nested(self):
        with acting(self.game, self.companion):
            with acting(self.game, self.hero):
                self.assertIs(self.hero, self.game.player)
            self.assertIs(self.companion, self.game.player)
        self.assertIs(self.hero, self.game.player)


class TestWhoIsStanding(PartyTestCase):

    def test_heroes_and_living(self):
        self.assertTrue(in_party_mode(self.game))
        self.assertEqual([self.hero, self.companion], heroes(self.game))
        self.companion.is_dead = True
        self.assertEqual([self.hero], living(self.game))
        self.assertFalse(self.controller.party_fallen())
        self.hero.is_dead = True
        self.assertTrue(self.controller.party_fallen())

    def test_a_test_double_has_no_party(self):
        game = MagicMock()
        self.assertFalse(in_party_mode(game))
        self.assertEqual([game.player], heroes(game))


class TestTheEnemysTarget(PartyTestCase):

    def test_bit_0_of_a_random_byte(self):
        for roll, target in ((0, self.hero), (1, self.companion), (254, self.hero), (255, self.companion)):
            with self.subTest(roll=roll), patch('src.battle_controller.hero_random.randint', return_value=roll):
                self.assertIs(target, self.controller.enemy_target())

    def test_no_roll_for_one_hero_standing(self):
        self.hero.is_dead = True
        with patch('src.battle_controller.hero_random.randint') as randint:
            self.assertIs(self.companion, self.controller.enemy_target())
        randint.assert_not_called()

    def test_no_roll_without_a_party(self):
        self.game.companion = None
        with patch('src.battle_controller.hero_random.randint') as randint:
            self.assertIs(self.hero, self.controller.enemy_target())
        randint.assert_not_called()


@patch('src.battle_controller.display')
class TestTheRounds(PartyTestCase):
    """Every command FIGHT: Ann, Gwen, then the enemy, round after round."""

    def setUp(self):
        super().setUp()
        self.battle = make_battle()
        self.battle.enemy.hp = 100
        self.order = []
        controller = self.controller
        patch.object(controller, 'open_command_window',
                     side_effect=lambda: setattr(controller, 'command_window_open', True)).start()
        patch.object(controller, 'draw_command_window').start()
        patch.object(controller, 'remove_command_window').start()
        patch('src.battle_controller.next_frame').start()
        patch('src.battle_controller.frame_events', return_value=[]).start()
        patch.object(controller, 'process_command_input', return_value='Fight').start()
        patch.object(controller, 'hero_attack',
                     side_effect=lambda battle: self.order.append(self.game.player.name)).start()
        patch.object(controller, 'enemy_move',
                     side_effect=lambda battle: self.order.append(f'enemy: {self.game.player.name}')).start()

    def turns(self, count):
        for _ in range(count):
            with acting(self.game, self.controller.hero_to_act()):
                self.controller.handle_battle_prompts(False, self.battle)

    def test_each_hero_then_the_enemy(self, _display):
        with patch('src.battle_controller.hero_random.randint', side_effect=[0, 1]):
            self.turns(4)
        self.assertEqual(['Ann', 'Gwen', 'enemy: Ann', 'Ann', 'Gwen', 'enemy: Gwen'], self.order)
        self.assertIs(self.hero, self.game.player)

    def test_a_fallen_hero_sits_it_out(self, _display):
        self.companion.is_dead = True
        self.turns(2)
        self.assertEqual(['Ann', 'enemy: Ann', 'Ann', 'enemy: Ann'], self.order)

    def test_the_first_hero_fallen(self, _display):
        self.hero.is_dead = True
        self.turns(2)
        self.assertEqual(['Gwen', 'enemy: Gwen', 'Gwen', 'enemy: Gwen'], self.order)

    def test_the_prompt_names_the_hero(self, _display):
        self.controller.open_command_window = type(self.controller).open_command_window.__get__(self.controller)
        with patch.object(self.game.cmd_menu, 'window_drop_down_effect'), \
                patch.object(self.game.cmd_menu, 'covered_area'), patch.object(self.game, 'sound'):
            with acting(self.game, self.companion):
                self.controller.open_command_window()
        self.assertEqual("Command for Gwen?\n", self.game.cmd_menu.show_line_in_dialog_box.call_args.args[0])

    def test_a_blocked_run_lets_the_other_hero_act(self, _display):
        self.controller.process_command_input.side_effect = ['Run', 'Fight']
        self.battle.battle_run.return_value = False
        with patch('src.battle_controller.hero_random.randint', return_value=0):
            self.turns(2)
        self.assertFalse(self.battle.battle_run.call_args.kwargs['enemy_moves'])
        self.assertEqual(['Gwen', 'enemy: Ann'], self.order)


class TestFalling(PartyTestCase):

    def test_a_hero_brought_to_0_hp_falls(self):
        battle = make_battle()

        def hit(_battle):
            self.game.player.current_hp = 0
            return False
        with patch.object(self.controller, 'enemy_move', side_effect=hit), \
                patch('src.battle_controller.hero_random.randint', return_value=1):
            self.assertFalse(self.controller.enemy_round(battle))
        self.assertTrue(self.companion.is_dead)
        self.assertFalse(self.hero.is_dead)
        self.assertEqual("Gwen hath fallen.\n", self.game.cmd_menu.show_line_in_dialog_box.call_args.args[0])

    def test_no_fallen_line_when_the_party_falls(self):
        self.hero.is_dead = True
        battle = make_battle()

        def hit(_battle):
            self.game.player.current_hp = 0
            return False
        with patch.object(self.controller, 'enemy_move', side_effect=hit):
            self.controller.enemy_round(battle)
        self.assertTrue(self.controller.party_fallen())
        self.game.cmd_menu.show_line_in_dialog_box.assert_not_called()

    def test_back_up_with_1_hp_after_the_fight(self):
        self.companion.is_dead = True
        self.companion.current_hp = 0
        self.controller.get_fallen_heroes_up()
        self.assertEqual((False, 1), (self.companion.is_dead, self.companion.current_hp))

    def test_both_back_with_the_king(self):
        for hero in (self.hero, self.companion):
            hero.current_hp = 0
            hero.is_dead = True
        with patch.object(self.game, 'change_map'), patch.object(self.game.cmd_menu, 'show_text_in_dialog_box'):
            self.game.hero_death.set_post_death_attributes()
        self.assertEqual((False, self.companion.max_hp), (self.companion.is_dead, self.companion.current_hp))
        self.assertEqual(self.hero.max_hp, self.hero.current_hp)


class TestWinning(PartyTestCase):

    def win(self, standing):
        battle = Battle(self.game.config, 'Slime', self.game.current_map)
        enemy = Mock(xp=10, gold=5)
        enemy.name = 'Slime'
        with patch.object(battle, 'announce_enemy_defeated'), \
                patch('src.battle.randomize_enemy_gold', return_value=5), \
                patch.object(Battle, 'check_party_level_up') as party_level_up, \
                patch.object(Battle, 'check_player_level_up') as level_up:
            battle.enemy_defeated(self.game.cmd_menu, self.game.screen, self.hero, enemy, heroes=standing)
        return party_level_up, level_up

    def test_experience_for_each_hero_standing_gold_once(self):
        self.hero.gold = 0
        party_level_up, _ = self.win([self.hero, self.companion])
        self.assertEqual((10, 10), (self.hero.total_experience, self.companion.total_experience))
        self.assertEqual(5, self.hero.gold)
        self.assertEqual(0, self.companion.gold)
        party_level_up.assert_called_once()

    def test_a_fallen_hero_gets_none(self):
        _, level_up = self.win([self.hero])
        self.assertEqual((10, 0), (self.hero.total_experience, self.companion.total_experience))
        level_up.assert_called_once()

    def test_the_gold_is_the_partys_with_the_first_hero_fallen(self):
        self.hero.gold = 0
        self.win([self.companion])
        self.assertEqual(5, self.hero.gold)
        self.assertEqual((0, 10), (self.hero.total_experience, self.companion.total_experience))


class TestLevelUps(PartyTestCase):

    def test_the_music_once_then_each_hero(self):
        battle = Battle(self.game.config, 'Slime', self.game.current_map)
        cmd_menu = MagicMock()
        cmd_menu.game = self.game
        order = []
        cmd_menu.wait_for_button.side_effect = lambda **kwargs: order.append(('wait', kwargs['shows_arrow']))
        for hero in (self.hero, self.companion):
            hero.total_experience = 7  # level 2
        with patch.object(self.game, 'music_player') as music_player, \
                patch.object(battle, 'display_level_up_message',
                             side_effect=lambda menu, hero, level: order.append(hero.name)), \
                patch.object(battle, 'display_stat_increases'):
            battle.check_party_level_up(cmd_menu, [self.hero, self.companion])
        music_player.play_until_end.assert_called_once()
        self.assertEqual([('wait', True), 'Ann', ('wait', True), 'Gwen', ('wait', False)], order)
        self.assertEqual((2, 2), (self.hero.level, self.companion.level))


class TestTheDamageLine(PartyTestCase):

    def test_names_the_hero(self):
        with acting(self.game, self.companion), patch.object(self.controller, 'player_hit_effect'):
            self.game.hero_damage.receive_damage(3)
        self.assertEqual("Gwen's Hit Points decreased by 3.\n",
                         self.game.cmd_menu.show_line_in_dialog_box.call_args.args[0])
        self.assertEqual(self.companion.max_hp - 3, self.companion.current_hp)

    def test_thy_without_a_party(self):
        self.game.companion = None
        with patch.object(self.controller, 'player_hit_effect'):
            self.game.hero_damage.receive_damage(1)
        self.assertEqual("Thy Hit decreased by 1.\n", self.game.cmd_menu.show_line_in_dialog_box.call_args.args[0])
