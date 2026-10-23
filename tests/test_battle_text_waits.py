"""
How many button presses a turn of a fight takes (#381).

On the NES a fight's messages are TextBlock entries that end with END and no WAIT ("Player attacks!", "The ENMY's Hit
Points have been reduced by AMNT.", "The ENMY attacks!", "Thy Hits decreased by AMNT."...). DoDialogLoBlock and
DoDialogHiBlock print them and return, so a turn's lines flow on their own, letter by letter, and the only button the
turn waits for is the command window's (and the SPELL or ITEM window's, when one is opened). These turns run on a real
Game, through the real dialog code, and count every wait for a button.
"""
import unittest
from unittest.mock import MagicMock, patch

import pygame

from src.battle import Battle
from src.battle_controller import BattleController
from src.config.test_config import test_config
from src.cursor import IN_A
from src.menu import CommandMenu
from src.selection import Answer
from src.spells import Spell
from tests.helpers import new_game, skip_window_frame_waits


def setUpModule():
    pygame.init()


class TestOnePressATurn(unittest.TestCase):

    def setUp(self):
        self.addCleanup(patch.stopall)
        skip_window_frame_waits()
        config = {**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True, 'SOUND_ENABLED': False,
                  'MUSIC_ENABLED': False}
        self.game = new_game(config)
        self.player = self.game.player
        self.player.name = 'Erdrick'
        self.player.current_hp = self.player.max_hp = 200
        self.events: list = []
        self.commands: list[str] = []

        # Every button the game waits for, and every line it shows (printed by the real dialog code)
        def wait_for_dialog_key(_menu, shows_arrow, skip_text, temp_text_start, disable_sound, advance_keys=None):
            if not skip_text and not temp_text_start:
                self.events.append(('button', shows_arrow))
        patch.object(CommandMenu, 'wait_for_dialog_key', autospec=True, side_effect=wait_for_dialog_key).start()
        real_show_line = CommandMenu.show_line_in_dialog_box

        def show_line(menu, line, *args, **kwargs):
            self.events.append(('line', line))
            real_show_line(menu, line, *args, **kwargs)
        patch.object(CommandMenu, 'show_line_in_dialog_box', autospec=True, side_effect=show_line).start()

        # The command window: one press of A on the scripted command
        def process_command_input(_controller, _presses):
            if not self.commands:
                return None
            command = self.commands.pop(0)
            self.events.append(('button', 'command'))
            return command
        patch.object(BattleController, 'process_command_input', autospec=True,
                     side_effect=process_command_input).start()

        def run_selection(*_args, **_kwargs):
            self.events.append(('button', 'spell window'))
            return Answer(IN_A, 0)
        patch('src.menu.run_selection', side_effect=run_selection).start()

        patch('src.battle_controller.next_frame').start()
        patch('src.battle_controller.time').start()
        patch('src.waiting.time.wait').start()
        # No dodge, no excellent move, no running away: the turns go as scripted
        patch('src.battle_controller.enemy_dodges', return_value=False).start()
        patch('src.battle_controller.enemy_flees', return_value=False).start()
        patch('src.battle.is_excellent_move', return_value=False).start()
        patch('src.battle_controller.calculate_enemy_attack_damage', return_value=2).start()

    def fight(self, enemy_name: str) -> Battle:
        battle = Battle(self.game.config, enemy_name, self.game.current_map)
        battle.enemy.hp = battle.enemy.max_hp = 200
        self.game.cmd_menu.current_battle = battle
        self.game.battle_ctrl.command_window_open = False
        self.game.battle_ctrl.command_window_shown = False
        return battle

    def play_turn(self, battle: Battle, command: str) -> list:
        """From the command window opening to its opening again for the next turn."""
        controller = self.game.battle_ctrl
        self.commands = [command]
        turn = battle.turn
        for _ in range(10):
            controller.handle_battle_prompts(False, battle)
            if battle.turn != turn:
                break
        self.assertNotEqual(battle.turn, turn, 'the command was never chosen')
        # the next player turn: the command window again, waiting for the next command
        controller.handle_battle_prompts(False, battle)
        self.assertTrue(controller.command_window_open)
        return self.events

    def buttons(self, events: list) -> list:
        return [event[1] for event in events if event[0] == 'button']

    def lines(self, events: list) -> list:
        return [event[1] for event in events if event[0] == 'line' and event[1] != 'Command?\n']

    def test_a_fight_turn_takes_one_press(self):
        # FIGHT, the hero's hit, the enemy's attack, back to the command window
        battle = self.fight('Slime')
        # a hit that lands (a level 1 hero's damage roll on a Slime can be 0, which is the missed-hit line)
        with patch('src.battle.player_hit_damage', return_value=3):
            events = self.play_turn(battle, 'Fight')
        self.assertEqual(self.buttons(events), ['command'], events)
        lines = self.lines(events)
        self.assertEqual(lines[0], 'Erdrick attacks!\n')
        self.assertIn("The Slime's Hit Point", lines[1])
        self.assertEqual(lines[2:], ['The Slime attacks!\n', 'Thy Hits decreased by 2.\n'])

    def test_a_missed_hit_and_a_missed_attack_take_one_press(self):
        # TB15E7 and TB16E11 have no WAIT either
        battle = self.fight('Slime')
        with patch('src.battle.player_hit_damage', return_value=0), \
                patch('src.battle_controller.calculate_enemy_attack_damage', return_value=0):
            events = self.play_turn(battle, 'Fight')
        self.assertEqual(self.buttons(events), ['command'], events)
        self.assertEqual(self.lines(events), ['Erdrick attacks!\n',
                                              'The attack failed and there was no loss of Hit Points!',
                                              'The Slime attacks!\n', 'A miss! No damage hath been scored!'])

    def test_a_spell_turn_takes_the_command_and_the_spell(self):
        # SPELL, HURT chosen in the SPELL window, "chanted the spell" (TB4E0), the damage, the enemy's attack
        self.player.spells = [Spell.HURT]
        self.player.current_mp = 10
        battle = self.fight('Slime')
        with patch('src.menu.bw_screen_flash'):
            events = self.play_turn(battle, 'Spell')
        self.assertEqual(self.buttons(events), ['command', 'spell window'], events)
        lines = self.lines(events)
        self.assertEqual(lines[0], 'Erdrick chanted the spell of HURT.')
        self.assertIn("The Slime's Hit Point", lines[1])
        self.assertEqual(lines[2:], ['The Slime attacks!\n', 'Thy Hits decreased by 2.\n'])

    def test_a_spell_with_too_little_mp_takes_no_turn_and_no_extra_press(self):
        # TB4E2 "Thy MP is too low." has no WAIT: straight back to the command window (StartPlayerTurn)
        self.player.spells = [Spell.HURT]
        self.player.current_mp = 0
        battle = self.fight('Slime')
        events = self.play_turn(battle, 'Spell')
        self.assertEqual(self.buttons(events), ['command', 'spell window'], events)
        self.assertEqual(self.lines(events), ['Thy MP is too low.'])

    def test_a_blocked_run_takes_one_press(self):
        # RUN, "started to run away." (TB16E5), "But was blocked in front." (TB16E6), the enemy's attack
        battle = self.fight('Slime')
        with patch('src.battle.can_run_away', return_value=False):
            events = self.play_turn(battle, 'Run')
        self.assertEqual(self.buttons(events), ['command'], events)
        self.assertEqual(self.lines(events), ['Erdrick started to run away.\n', 'But was blocked in front.',
                                              'The Slime attacks!\n', 'Thy Hits decreased by 2.\n'])

    def test_an_enemy_spell_takes_no_press(self):
        # FIGHT, then the enemy chants HURT (TB16E12 and TB16E13) and the hero is hit: one press, the command
        battle = self.fight('Magician')
        controller_random = MagicMock()
        controller_random.randint.side_effect = lambda low, _high: low  # the spell is cast, for its least damage
        with patch('src.battle_controller.random', controller_random):
            events = self.play_turn(battle, 'Fight')
        self.assertEqual(self.buttons(events), ['command'], events)
        lines = self.lines(events)
        self.assertEqual(lines[0], 'Erdrick attacks!\n')
        self.assertEqual(lines[2:], ['Magician chants the spell of HURT.', 'Thy Hits decreased by 3.\n'])

    def test_an_enemy_putting_the_hero_to_sleep_takes_no_press(self):
        # EnCastSleep: "Thou art asleep." (TB17E6), then PlayerAsleepDialog's "Thou art still asleep." (TB17E7) and
        # another enemy turn at once, all with no WAIT
        battle = self.fight('Slime')
        battle.enemy.refresh_pattern = lambda: None
        battle.enemy.pattern = [(100, Spell.SLEEP, True), 'ATTACK']
        with patch('src.battle_controller.random.randint', side_effect=lambda low, _high: low):
            self.game.battle_ctrl.enemy_move(battle)
        self.assertEqual(self.buttons(self.events), [], self.events)
        self.assertEqual(self.lines(self.events), ['Slime chants the spell of SLEEP.', 'Thou art asleep.\n',
                                                   'Thou art still asleep.\n', 'The Slime attacks!\n',
                                                   'Thy Hits decreased by 2.\n'])


class TestFieldSpellWaits(TestOnePressATurn):
    """The same count for a spell cast from the COMMAND window (#429). NES DoSpell: "chanted the spell" (TB4E0) has no
    WAIT in the field either; the spell's press, if any, is ResumeGamePlay's, after the spell."""

    def cast(self, spell: Spell, mp: int = 10) -> list:
        self.player.spells = [spell]
        self.player.current_mp = mp
        self.game.cmd_menu.current_battle = None
        with patch('src.menu.bw_screen_flash'):
            self.game.cmd_menu.display_item_menu('spells')
        return self.events

    def test_heal_waits_once_after_healing(self):
        real_recover_health = CommandMenu.recover_health

        def recover_health(menu, *args):
            self.events.append(('healed', None))
            real_recover_health(menu, *args)
        with patch.object(CommandMenu, 'recover_health', autospec=True, side_effect=recover_health):
            events = self.cast(Spell.HEAL)
        self.assertEqual(self.buttons(events), ['spell window', False], events)
        self.assertEqual(self.lines(events), ['Erdrick chanted the spell of HEAL.'])
        # the press is waited for once the HP is back (DoHeal, then ResumeGamePlay), not after the chant
        self.assertEqual(events[-2:], [('healed', None), ('button', False)])

    def test_a_spell_that_does_nothing_waits_once(self):
        # HURT in the field: SpellFizzle's "But nothing happened.", then ResumeGamePlay
        events = self.cast(Spell.HURT)
        self.assertEqual(self.buttons(events), ['spell window', False], events)
        self.assertEqual(self.lines(events), ['Erdrick chanted the spell of HURT.', 'But nothing happened.'])

    def test_radiant_in_a_dungeon_waits_for_nothing(self):
        # DoSpell's LightIncreaseLoop returns at once (LDA83): no ResumeGamePlay
        self.game.current_map.is_dark = True
        events = self.cast(Spell.RADIANT)
        self.assertEqual(self.buttons(events), ['spell window'], events)

    def test_too_little_mp_waits_once(self):
        # TB4E2, then ResumeGamePlay (LDA44)
        events = self.cast(Spell.HEAL, mp=0)
        self.assertEqual(self.buttons(events), ['spell window', False], events)
        self.assertEqual(self.lines(events), ['Thy MP is too low.'])
