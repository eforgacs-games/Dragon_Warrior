import os
import unittest
from unittest.mock import MagicMock, Mock, patch

import pygame

from src.battle import Battle, can_run_away
from src.battle_controller import BattleController, BattleOutcome
from src.config.test_config import test_config
from tests.helpers import new_game


def answer(*answers):
    """Stand-in for confirmation_prompt that answers each prompt in turn (True = yes)."""
    remaining = list(answers)
    prompts = []

    def fake_prompt(command_menu, prompt_line, yes_path_function, no_path_function, **kwargs):
        prompts.append(prompt_line)
        (yes_path_function if remaining.pop(0) else no_path_function)()

    return fake_prompt, prompts


class TestDragonlordDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        self.game = new_game()
        self.dialog_lookup = self.game.cmd_menu.dialog_lookup
        self.cmd_menu = self.dialog_lookup.command_menu
        self.shown = []
        patch.object(self.cmd_menu, 'show_line_in_dialog_box',
                     side_effect=lambda line, *a, **k: self.shown.append(line)).start()
        self.addCleanup(patch.stopall)

    def test_dragonlord_dialog_matches_nes_text(self):
        # NES DoDrgnLrdDialog: TB13E7, TB11E4, TB13E8, then the yes/no window
        dialog = self.dialog_lookup.lookup_table['CharlockB8']['DRAGONLORD']['dialog']
        self.assertEqual(dialog[0], f"Welcome, {self.game.player.name}.\nI am the Dragonlord--King of Kings.")
        self.assertEqual(dialog[1], "I have been waiting long for one such as thee.")
        self.assertEqual(dialog[2], "I give thee now a chance to share this world and to rule half of it if "
                                    "thou will now stand beside me.")
        self.assertEqual(dialog[3], self.dialog_lookup.dragonlord_offer_prompt)

    def run_offer(self, *answers):
        fake_prompt, prompts = answer(*answers)
        with patch('data.text.dialog_lookup_table.confirmation_prompt', side_effect=fake_prompt), \
                patch.object(self.dialog_lookup, 'bad_ending_spinlock') as spinlock, \
                patch.object(self.dialog_lookup, 'show_bad_ending_palette') as palette:
            self.dialog_lookup.dragonlord_offer_prompt()
        return prompts, spinlock, palette

    def test_no_starts_the_fight_with_the_first_form(self):
        prompts, spinlock, _ = self.run_offer(False)
        self.assertEqual(prompts, ["What sayest thou?\nWill the great warrior stand with me?"])
        self.assertEqual(self.shown, ["Thou art a fool!"])
        self.assertEqual(self.game.battle_ctrl.pending_scripted_battle, 'Dragonlord')
        spinlock.assert_not_called()

    def test_yes_then_no_asks_twice_then_fights(self):
        prompts, spinlock, _ = self.run_offer(True, False)
        self.assertEqual(prompts, ["What sayest thou?\nWill the great warrior stand with me?", "Really?"])
        self.assertEqual(self.shown, ["Thou art a fool!"])
        self.assertEqual(self.game.battle_ctrl.pending_scripted_battle, 'Dragonlord')
        spinlock.assert_not_called()

    def test_yes_twice_is_the_bad_ending(self):
        player = self.game.player
        player.gold, player.total_experience = 500, 12000
        player.inventory = ['Magic Key', 'Herb']
        player.weapon, player.armor, player.shield = 'Broad Sword', 'Chain Mail', 'Small Shield'
        player.spells = ['HEAL']
        prompts, spinlock, palette = self.run_offer(True, True)
        self.assertEqual(len(prompts), 2)
        self.assertEqual(self.shown, [
            "Then half of this world is thine, half of the darkness, and....",
            "If thou dies I can bring thee back for another attempt without loss of thy deeds to date.",
            "Thy journey is over.\nTake now a long, long rest.\nHahahaha....",
        ])
        # NES ZeroStats
        self.assertEqual((player.gold, player.total_experience), (0, 0))
        self.assertEqual(player.inventory, [])
        self.assertEqual((player.weapon, player.armor, player.shield), ("", "", ""))
        self.assertEqual(player.spells, [])
        palette.assert_called_once()
        spinlock.assert_called_once()
        self.assertIsNone(self.game.battle_ctrl.pending_scripted_battle)

    def test_pending_battle_starts_on_next_frame(self):
        self.game.battle_ctrl.queue_scripted_battle('Dragonlord')
        with patch.object(self.game.battle_ctrl, 'start_scripted_battle') as start:
            self.game.handle_battles()
        start.assert_called_once_with('Dragonlord')
        self.assertIsNone(self.game.battle_ctrl.pending_scripted_battle)


def make_game():
    game = MagicMock()
    game._ = lambda s: s
    game.config = {"MUSIC_ENABLED": False}
    game.player.is_dead = False
    return game


def fake_battle(name, hp):
    battle = Mock()
    battle.enemy = Mock(hp=hp)
    battle.enemy.name = name
    return battle


@patch('src.battle_controller.display')
@patch('src.battle_controller.Battle')
class TestScriptedBattle(unittest.TestCase):

    def setUp(self):
        self.game = make_game()
        self.controller = BattleController(self.game)
        # The opening CheckEnRun / CalcWhoIsNext rolls are tested in test_battle_controller.TestStartFight
        patch.object(self.controller, 'start_fight', return_value=False).start()
        self.addCleanup(patch.stopall)

    def test_dragonlord_transforms_into_second_form_and_victory_is_normal(self, mock_battle_class, _):
        first, second = fake_battle('Dragonlord', 100), fake_battle('Dragonlord 2', 130)
        mock_battle_class.side_effect = [first, second]

        def kill(run_away, current_battle):
            current_battle.enemy.hp = 0
            return False
        with patch.object(self.controller, 'handle_battle_prompts', side_effect=kill):
            outcome = self.controller.start_scripted_battle('Dragonlord')

        self.assertEqual([c.args[1] for c in mock_battle_class.call_args_list], ['Dragonlord', 'Dragonlord 2'])
        first.dragonlord_first_form_defeated.assert_called_once()
        first.enemy_defeated.assert_not_called()
        # The final form ends with the regular victory path, which the ending code keys on.
        second.enemy_defeated.assert_called_once()
        self.assertEqual(outcome, BattleOutcome.VICTORY)
        self.assertIsNone(self.game.cmd_menu.current_battle)
        self.assertFalse(self.controller.launch_battle)

    def test_scripted_battle_is_not_repelled(self, mock_battle_class, _):
        self.game.repel_timer = 255
        self.game.current_map.identifier = 'Alefgard'
        self.game.player.defense_power = 255
        mock_battle_class.return_value = fake_battle('Golem', 70)
        with patch.object(self.controller, 'handle_battle_prompts', return_value=True):
            outcome = self.controller.start_scripted_battle('Golem')
        mock_battle_class.assert_called_once()
        self.assertEqual(outcome, BattleOutcome.ESCAPED)

    def test_death_keeps_launch_battle_for_death_screen(self, mock_battle_class, _):
        mock_battle_class.return_value = fake_battle('Dragonlord', 100)

        def die(run_away, current_battle):
            self.game.player.is_dead = True
            return False
        with patch.object(self.controller, 'handle_battle_prompts', side_effect=die):
            outcome = self.controller.start_scripted_battle('Dragonlord')
        self.assertEqual(outcome, BattleOutcome.DEFEAT)
        self.assertTrue(self.controller.launch_battle)

    def test_running_from_final_form_returns_to_map(self, mock_battle_class, mock_display):
        mock_battle_class.return_value = fake_battle('Dragonlord 2', 130)
        with patch.object(self.controller, 'handle_battle_prompts', return_value=True):
            outcome = self.controller.start_scripted_battle('Dragonlord 2')
        self.assertEqual(outcome, BattleOutcome.ESCAPED)
        self.game.screen.fill.assert_called_once()
        self.game.music_player.load_and_play_music.assert_called_once_with(self.game.current_map.music_file_path)


class TestDragonlordBattle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.config = {**test_config, 'TILE_SIZE': 32, 'MUSIC_ENABLED': True}

    def test_both_forms_use_the_hardest_run_odds(self):
        # NES TryRun: Stoneman and up (both Dragonlord forms) roll the full 0-255 against the player
        self.assertEqual(Battle.get_group_factor('Dragonlord'), 4)
        self.assertEqual(Battle.get_group_factor('Dragonlord 2'), 4)

    def test_run_odds_follow_try_run(self):
        # Player rolls 100 * agility 100 = 10000; enemy rolls 200 * defense 75 = 15000: blocked
        with patch('src.battle.random.randint', side_effect=[200, 100]):
            self.assertFalse(can_run_away(100, 75, 4))
        # Same rolls against a group 1 enemy: 200 & 0x3F = 8, so 8 * 75 = 600: escapes
        with patch('src.battle.random.randint', side_effect=[200, 100]):
            self.assertTrue(can_run_away(100, 75, 1))
        # Equal products count as a successful run (no borrow in the NES subtraction)
        with patch('src.battle.random.randint', side_effect=[100, 100]):
            self.assertTrue(can_run_away(75, 75, 4))

    def test_blocked_run_from_dragonlord_gives_him_a_turn(self):
        battle = Battle(self.config, 'Dragonlord', Mock())
        cmd_menu = Mock()
        cmd_menu.game.battle_ctrl.enemy_move = Mock(return_value=False)
        player = Mock(agility=1, current_hp=50)
        with patch('src.battle.random.randint', return_value=255):
            self.assertFalse(battle.battle_run(cmd_menu, player, battle))
        cmd_menu.game.battle_ctrl.enemy_move.assert_called_once_with(battle)

    def test_end_boss_music_only_for_final_form(self):
        music_player = Mock()
        first = Battle(self.config, 'Dragonlord', Mock())
        first.play_battle_music(music_player)
        music_player.load_and_play_music.assert_called_with(first.directories.battle_music)
        second = Battle(self.config, 'Dragonlord 2', Mock())
        second.play_battle_music(music_player)
        music_player.load_and_play_music.assert_called_with(second.directories.end_boss_music)
        self.assertTrue(os.path.exists(second.directories.end_boss_music))

    def test_final_form_has_full_hp_and_reveal_text(self):
        battle = Battle(self.config, 'Dragonlord 2', Mock())
        self.assertEqual(battle.enemy.hp, battle.enemy.max_hp)
        self.assertTrue(battle.get_enemy_draws_near_string().startswith('The Dragonlord revealed his true self!'))

    @patch('src.battle.wait_frames')
    def test_first_form_defeat_gives_no_experience(self, mock_wait_frames):
        battle = Battle(self.config, 'Dragonlord', Mock())
        cmd_menu, screen = Mock(), Mock()
        with patch.object(battle, 'make_enemy_image_disappear'):
            battle.dragonlord_first_form_defeated(cmd_menu, screen)
        lines = [c.args[0] for c in cmd_menu.show_line_in_dialog_box.call_args_list]
        self.assertEqual(lines, ["Thou hast done well in defeating the Dragonlord.\n"])


if __name__ == '__main__':
    unittest.main()
