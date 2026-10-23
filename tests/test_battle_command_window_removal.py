"""The battle command window is taken off the screen after every command, the way the NES does it: PlyrFight, PlyrRun,
PlyrSpell and PlyrItem (Bank03) call RemoveWindow WND_CMD_CMB, which puts back the battle scene it covered. So an
earlier turn's window isn't left on the screen during the hero's action, the enemy's turn or while the hero sleeps
(#310)."""
import hashlib
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame
from pygame import KEYDOWN, K_RETURN, Rect
from pygame.event import Event

from src.config.test_config import test_config
from src.spells import Spell
from src.windows import COMBAT_COMMAND_WINDOW
from tests.helpers import new_game, skip_window_frame_waits

# A stand-in for the battle scene: whatever is on the screen where the command window opens
BATTLE_SCENE_COLOR = (12, 34, 56)


def image_digest(surface) -> str:
    return hashlib.sha1(pygame.image.tobytes(surface, 'RGB')).hexdigest()


class TestBattleCommandWindowRemoval(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['NO_BLIT'] = False
        self.addCleanup(test_config.__setitem__, 'NO_BLIT', True)
        skip_window_frame_waits()
        self.addCleanup(patch.stopall)
        self.game = new_game()
        self.controller = self.game.battle_ctrl
        self.cmd_menu = self.game.cmd_menu
        self.battle = MagicMock(turn=0, last_turn=0, no_op=False)
        self.battle.enemy.hp = 10
        self.cmd_menu.current_battle = self.battle
        self.addCleanup(setattr, self.cmd_menu, 'current_battle', None)
        tile_size = self.game.config['TILE_SIZE']
        x, y, width, height = COMBAT_COMMAND_WINDOW
        self.window_rect = Rect(x * tile_size, y * tile_size, width * tile_size, height * tile_size)
        self.game.screen.fill((0, 0, 0))
        self.game.screen.fill(BATTLE_SCENE_COLOR, self.window_rect.inflate(-tile_size, -tile_size))
        self.battle_scene = self.window_area()
        # What is under the command window whenever a line is shown
        self.seen_with_lines: list[str] = []
        patch.object(self.cmd_menu, 'show_line_in_dialog_box',
                     side_effect=lambda *args, **kwargs: self.seen_with_lines.append(self.window_area())).start()

    def window_area(self) -> str:
        return image_digest(self.game.screen.subsurface(self.window_rect))

    def choose(self, command: str | None) -> None:
        """One pass of the fight loop, in which the command window (opened if it isn't) gives ``command``."""
        with patch.object(self.controller, 'process_command_input', return_value=command):
            self.controller.handle_battle_prompts(False, self.battle)

    def test_the_window_opens_over_the_battle_scene(self):
        self.choose(None)
        self.assertNotEqual(self.battle_scene, self.window_area())

    def test_fight_removes_the_window_before_the_attack(self):
        self.choose(None)
        with patch.object(self.controller, 'fight',
                          side_effect=lambda battle: self.seen_with_lines.append(self.window_area())), \
                patch.object(self.controller, 'enemy_move', return_value=False):
            self.choose('Fight')
        self.assertEqual([self.battle_scene], self.seen_with_lines)

    def test_no_window_while_the_hero_sleeps(self):
        # The enemy puts the hero to sleep after a FIGHT: the window of that turn isn't on the screen on the next,
        # when "Thou art still asleep." is shown
        self.choose(None)

        def fall_asleep(battle):
            self.game.player.is_asleep = True
            return False
        with patch.object(self.controller, 'fight'), patch.object(self.controller, 'enemy_move', side_effect=fall_asleep):
            self.choose('Fight')
            with patch('src.battle_controller.random.randint', return_value=0):
                self.choose(None)
        self.assertEqual("Thou art still asleep.\n", self.cmd_menu.show_line_in_dialog_box.call_args.args[0])
        self.assertEqual([self.battle_scene], self.seen_with_lines)

    def test_run_removes_the_window(self):
        self.choose(None)
        self.battle.battle_run.side_effect = lambda *args: self.seen_with_lines.append(self.window_area()) or True
        self.choose('Run')
        self.assertEqual([self.battle_scene], self.seen_with_lines)

    def test_spell_without_spells_removes_the_window(self):
        self.game.player.spells = []
        self.choose(None)
        self.battle.battle_spell.side_effect = lambda *args: self.seen_with_lines.append(self.window_area())
        with patch.object(self.controller, 'enemy_move', return_value=False):
            self.choose('Spell')
        self.assertEqual([self.battle_scene], self.seen_with_lines)

    def test_item_without_items_removes_the_window(self):
        self.game.player.inventory = []
        self.choose(None)
        self.choose('Item')
        self.assertEqual([self.battle_scene], self.seen_with_lines)

    def test_the_spell_window_and_then_the_command_window_are_removed_before_the_spell(self):
        # PlyrSpellChosen: the SPELL window is removed (WindowSequence), then the command window under it
        self.game.player.spells = [Spell.HEAL]
        self.game.player.current_mp = self.game.player.max_mp = 10
        self.choose(None)
        pygame.event.post(Event(KEYDOWN, key=K_RETURN, unicode='\r'))
        with patch.object(self.cmd_menu, 'heal'), patch.object(self.cmd_menu, 'show_popup_window'):
            self.assertEqual(Spell.HEAL, self.cmd_menu.display_item_menu('spells'))
        self.assertEqual([self.battle_scene], self.seen_with_lines)  # "Erdrick chanted the spell of HEAL."
        self.assertFalse(self.controller.command_window_shown)

    def test_a_cancelled_spell_window_takes_the_command_window_with_it(self):
        # LE6DE: RemoveWindow WND_CMD_CMB, then StartPlayerTurn opens it again
        self.game.player.spells = [Spell.HEAL]
        self.choose(None)
        pygame.event.post(Event(KEYDOWN, key=pygame.K_ESCAPE, unicode='\x1b'))
        self.assertIsNone(self.cmd_menu.display_item_menu('spells'))
        self.assertEqual(self.battle_scene, self.window_area())

    def test_b_leaves_the_window_up_and_it_still_puts_the_battle_scene_back(self):
        # WND_ABORT: ShowCmbtCmd opens the window again over itself; removing it later still restores the battle
        # scene, not the window
        self.choose(None)
        with_window = self.window_area()
        self.controller.command_window_open = False  # what B does (process_command_input)
        self.choose(None)
        self.assertEqual(with_window, self.window_area())
        with patch.object(self.controller, 'fight'), patch.object(self.controller, 'enemy_move', return_value=False):
            self.choose('Fight')
        self.assertEqual(self.battle_scene, self.window_area())
