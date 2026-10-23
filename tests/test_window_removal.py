"""Answered selection windows (YES/NO, BUY/SELL, shop inventories, SPELL and ITEM) are taken off the screen the way
the NES does it: WindowSequence (Bank01) calls RemoveWindow (Bank00), which puts back what the window covered, the open
background windows (pop-up, COMMAND, dialog) or else the map, and touches nothing else."""
import hashlib
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame
from pygame import KEYDOWN, K_RETURN, Rect
from pygame.event import Event

from data.text.dialog import confirmation_prompt
from src.config.test_config import test_config
from src.direction import Direction
from src.maps import Brecconary
from src.spells import Spell
from src.windows import BUY_SELL_WINDOW, COMMAND_WINDOW, YES_NO_WINDOW, item_menu_window
from tests.helpers import new_game


def image_digest(surface) -> str:
    """A short stand-in for a surface's pixels, so a failed comparison doesn't diff megabytes."""
    return hashlib.sha1(pygame.image.tobytes(surface, 'RGB')).hexdigest()


def accept() -> Event:
    return Event(KEYDOWN, key=K_RETURN, unicode='\r')


class TestWindowRemoval(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = True
        test_config['NO_BLIT'] = False
        self.addCleanup(test_config.__setitem__, 'NO_BLIT', True)
        self.addCleanup(test_config.__setitem__, 'RENDER_TEXT', False)
        self.game = new_game()
        self.game.change_map(Brecconary(self.game.config), destination_coordinates=(29, 18),
                             direction=Direction.RIGHT.value)
        self.cmd_menu = self.game.cmd_menu
        self.tile_size = self.game.config['TILE_SIZE']
        # The A button: the pop-up and the COMMAND window open (NES ShowNCCmdWindow), then a dialog window
        self.draw_frame()
        self.game.drawer.display_hovering_stats = True
        self.cmd_menu.launch_signaled = True
        for _ in range(3):
            self.draw_frame()
        self.assertTrue(self.cmd_menu.menu.is_enabled())
        # TALK is chosen (CommandMenu.choose_command, WndAPressed): its arrow stays on while the dialog runs
        self.cmd_menu.cursor.hold()
        self.draw_frame()
        self.cmd_menu.show_text_in_dialog_box("Welcome to the traveler's Inn.", skip_text=True, drop_up=False)
        pygame.event.clear()

    def draw_frame(self):
        game = self.game
        game.drawer.draw_all(game.screen, game.loop_count, game.big_map, game.current_map, game.player, game.cmd_menu,
                             game.foreground_rects, game.sprites_animate, game.camera, game.initial_dialog_enabled, [],
                             game.skip_text, game.story_flags.left_throne_room, game.game_state, game.color)
        game.loop_count += 1

    def rect(self, window) -> Rect:
        return Rect(window[0] * self.tile_size, window[1] * self.tile_size, window[2] * self.tile_size,
                    window[3] * self.tile_size)

    def screen_bytes(self) -> str:
        return image_digest(self.game.screen)

    def assert_window_removed(self, before: str, window) -> None:
        """Everything is as it was before the window opened: what it covered is back, and nothing else changed."""
        self.assertEqual(self.screen_bytes(), before)
        self.assertTrue(self.rect(window).colliderect(self.rect(COMMAND_WINDOW)))  # it did cover the COMMAND window

    def test_confirmation_prompt(self):
        # the window is gone before the answer is acted on, and only its area is redrawn: the map and the COMMAND window
        yes_no = self.rect(YES_NO_WINDOW)
        before = image_digest(self.game.screen.subsurface(yes_no))
        answered = []
        with patch('src.selection.event.get', side_effect=[[accept()]]), \
                patch.object(self.cmd_menu, 'show_line_in_dialog_box'):
            confirmation_prompt(self.cmd_menu, "Dost thou want a room?",
                                lambda: answered.append(image_digest(self.game.screen.subsurface(yes_no))),
                                lambda: None, self.game.config, show_arrow=True, color=self.game.color)
        self.assertEqual(answered, [before])

    def test_prompt_yes_no(self):
        before = self.screen_bytes()
        pygame.event.post(accept())
        self.assertTrue(self.cmd_menu.prompt_yes_no())
        self.assert_window_removed(before, YES_NO_WINDOW)

    def test_buy_sell_window(self):
        before = self.screen_bytes()
        pygame.event.post(accept())
        dialog_lookup = self.cmd_menu.dialog_lookup
        self.assertEqual(dialog_lookup.select_from_text_menu(["BUY", "SELL"], BUY_SELL_WINDOW), 0)
        self.assert_window_removed(before, BUY_SELL_WINDOW)

    def test_cancelled_window_is_removed_too(self):
        before = self.screen_bytes()
        pygame.event.post(Event(KEYDOWN, key=pygame.K_ESCAPE, unicode='\x1b'))
        dialog_lookup = self.cmd_menu.dialog_lookup
        self.assertIsNone(dialog_lookup.select_from_text_menu(["BUY", "SELL"], BUY_SELL_WINDOW))
        self.assert_window_removed(before, BUY_SELL_WINDOW)

    def test_spell_window_is_gone_before_the_spell_is_cast(self):
        window = item_menu_window('spells', 1)
        self.assertTrue(self.rect(window).colliderect(self.rect(COMMAND_WINDOW)))
        before = image_digest(self.game.screen.subsurface(self.rect(window)))
        self.game.player.spells = [Spell.HEAL]
        self.game.player.current_mp = self.game.player.max_mp = 10
        seen = []
        pygame.event.post(accept())
        with patch.object(self.cmd_menu, 'show_line_in_dialog_box',
                          side_effect=lambda *args, **kwargs: seen.append(
                              image_digest(self.game.screen.subsurface(self.rect(window))))), \
                patch.object(self.cmd_menu, 'heal'), patch.object(self.cmd_menu, 'show_popup_window'):
            self.assertEqual(Spell.HEAL, self.cmd_menu.display_item_menu('spells'))
        self.assertEqual([before], seen)

    def test_cancelled_item_window_is_removed(self):
        before = self.screen_bytes()
        self.game.player.inventory = ['Torch', 'Wings']
        pygame.event.post(Event(KEYDOWN, key=pygame.K_ESCAPE, unicode='\x1b'))
        self.assertIsNone(self.cmd_menu.display_item_menu('inventory'))
        self.assert_window_removed(before, item_menu_window('inventory', 2))

    def test_in_a_fight_the_battle_scene_is_put_back(self):
        # The window covers the battle scene, not the map: what it covered is put back
        self.cmd_menu.current_battle = MagicMock()
        self.addCleanup(setattr, self.cmd_menu, 'current_battle', None)
        self.game.screen.fill((12, 34, 56), self.rect((5, 4, 7, 7)))  # a stand-in for the enemy and its background
        before = self.screen_bytes()
        self.game.player.inventory = ['Torch']
        pygame.event.post(Event(KEYDOWN, key=pygame.K_ESCAPE, unicode='\x1b'))
        self.assertIsNone(self.cmd_menu.display_item_menu('inventory'))
        self.assertEqual(before, self.screen_bytes())
