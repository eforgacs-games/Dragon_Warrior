"""Nothing on the map moves or animates while the command window or the pause screen is up (issues #99 and #41).

NES: START (PausePrepLoop) and A (DoNCCmdWindow) both wait until the hero and the NPCs have finished their steps,
then pause or set StopNPCMove; nothing calls DoSprites until the game is unpaused or the window closes.
"""
import os
from collections import defaultdict
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import K_LEFT, K_RETURN, K_RIGHT, K_i, K_j, K_k

from src.config.test_config import test_config
from src.direction import Direction
from src.game import Game

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


def keys_held(*held_keys):
    # A dict, not an array: pygame key codes for the arrows are over a billion
    return defaultdict(int, {held_key: 1 for held_key in held_keys})


def keydown(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=pygame.KMOD_NONE, unicode='')


class FreezeTestCase(TestCase):
    """The throne room, run a frame at a time. No tests of its own."""

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
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.game.game_state.is_initial_dialog = False
        self.tile_size = self.game.tile_size
        # TantegelThroneRoom's one roaming guard
        self.guard = self.game.current_map.roaming_characters[0]
        pygame.event.clear()

    def frame(self, *events, held=()):
        """Run one pass of the main loop's update, with these key presses and these keys held down."""
        for current_event in events:
            pygame.event.post(current_event)
        # Replaces only src.game's name for pygame.key, never pygame.key.get_pressed itself
        with patch('src.game.key') as mock_key:
            mock_key.get_pressed.return_value = keys_held(*held)
            self.game.get_events()

    def frames(self, count, held=()):
        for _ in range(count):
            self.frame(held=held)

    def let_guard_start_a_step(self, direction=Direction.LEFT.value):
        """Make the roaming guard pick a direction and take its first pixels of a step."""
        self.guard.last_roaming_clock_check = None
        with patch('src.game.random.choice', return_value=direction):
            self.frame()
        self.frame()
        self.assertTrue(self.guard.is_moving)
        self.assertNotEqual(0, self.guard.rect.x % self.tile_size)

    def guard_position(self):
        return self.guard.rect.x, self.guard.rect.y

    def player_position(self):
        return self.game.player.rect.x, self.game.player.rect.y, tuple(self.game.camera.pos)

    def assert_on_a_tile(self, rect):
        self.assertEqual(0, rect.x % self.tile_size)
        self.assertEqual(0, rect.y % self.tile_size)

    def open_command_menu(self):
        self.frame(keydown(K_k))
        self.assertTrue(self.game.cmd_menu.launch_signaled)
        # Drawer.handle_menu_launch does this on the next draw
        self.game.cmd_menu.menu.enable()


class TestFreezeMovement(FreezeTestCase):
    # ------------------------------------------------------------------ #
    #  #99: the command menu                                              #
    # ------------------------------------------------------------------ #

    def test_npcs_do_not_move_while_the_command_menu_is_open(self):
        self.open_command_menu()
        before = self.guard_position()
        for _ in range(5):
            self.guard.last_roaming_clock_check = None  # the guard would pick a new step every frame
            with patch('src.game.random.choice', return_value=Direction.LEFT.value):
                self.frames(20)
        self.assertEqual(before, self.guard_position())
        self.assertFalse(self.guard.is_moving)

    def test_npcs_stay_frozen_in_the_throne_room_although_the_drawer_unpauses_every_frame(self):
        # Drawer.handle_initial_dialog calls set_to_post_initial_dialog -> unpause_all_movement every frame in
        # TantegelThroneRoom; that used to set the guard walking again behind the open menu
        self.open_command_menu()
        before = self.guard_position()
        for _ in range(30):
            self.game.drawer.set_to_post_initial_dialog(self.game.cmd_menu)
            self.game.game_state.enable_movement = True
            self.guard.last_roaming_clock_check = None
            with patch('src.game.random.choice', return_value=Direction.LEFT.value):
                self.frame()
        self.assertEqual(before, self.guard_position())

    def test_sprites_do_not_animate_while_the_command_menu_is_open(self):
        self.assertTrue(self.game.sprites_animate)
        self.open_command_menu()
        self.assertFalse(self.game.sprites_animate)
        self.game.game_state.unpause_all_movement()
        self.assertFalse(self.game.sprites_animate)

    def test_command_window_waits_for_npc_to_finish_its_step(self):
        self.let_guard_start_a_step()
        self.frame(keydown(K_k))
        self.assertFalse(self.game.cmd_menu.launch_signaled)
        frames_waited = 0
        while not self.game.cmd_menu.launch_signaled:
            self.frame()
            frames_waited += 1
            self.assertLess(frames_waited, self.tile_size)
        self.assert_on_a_tile(self.guard.rect)
        self.game.cmd_menu.menu.enable()
        before = self.guard_position()
        self.frames(30)
        self.assertEqual(before, self.guard_position())

    def test_npc_does_not_start_a_new_step_while_the_command_window_is_pending(self):
        self.game.player.is_moving = True  # the window can't open until the hero's step is done
        self.frame(keydown(K_k))
        before = self.guard_position()
        self.guard.last_roaming_clock_check = None
        with patch('src.game.random.choice', return_value=Direction.LEFT.value), \
                patch.object(self.game, 'move_player'):
            self.frames(10)
        self.assertEqual(before, self.guard_position())

    def test_npcs_move_again_once_the_command_menu_closes(self):
        self.open_command_menu()
        self.guard.last_roaming_clock_check = None  # due a step as soon as it may move
        with patch('src.game.random.choice', return_value=Direction.LEFT.value):
            self.frame(keydown(K_j))
        self.assertFalse(self.game.world_frozen)
        before = self.guard_position()
        self.frames(3)
        self.assertNotEqual(before, self.guard_position())

    def test_a_pressed_mid_step_opens_the_command_window_after_the_step(self):
        self.frames(2, held=(K_LEFT,))
        self.assertTrue(self.game.player.is_moving)
        self.frame(keydown(K_k), held=(K_LEFT,))
        self.assertFalse(self.game.cmd_menu.launch_signaled)
        self.frames(self.tile_size, held=(K_LEFT,))
        self.assertTrue(self.game.cmd_menu.launch_signaled)
        self.assertFalse(self.game.player.is_moving)
        self.assert_on_a_tile(self.game.player.rect)
        self.assertEqual(0, self.game.camera.pos[0] % self.tile_size)

    def test_player_does_not_move_while_the_command_menu_is_open(self):
        self.open_command_menu()
        before = self.player_position()
        self.frames(30, held=(K_LEFT,))
        self.assertEqual(before, self.player_position())

    # ------------------------------------------------------------------ #
    #  #41: the pause key                                                 #
    # ------------------------------------------------------------------ #

    def test_pause_mid_step_finishes_the_step_then_stops(self):
        start_x = self.game.player.rect.x
        self.frames(3, held=(K_LEFT,))
        self.assertTrue(self.game.player.is_moving)
        self.frame(keydown(K_i), held=(K_LEFT,))
        self.assertFalse(self.game.paused)
        self.frames(self.tile_size, held=(K_LEFT,))
        self.assertTrue(self.game.paused)
        self.assertFalse(self.game.player.is_moving)
        self.assertEqual(start_x - self.tile_size, self.game.player.rect.x)
        self.assertEqual(0, self.game.camera.pos[0] % self.tile_size)
        before = self.player_position()
        self.frames(60, held=(K_LEFT,))
        self.assertEqual(before, self.player_position())

    def test_pause_freezes_npcs_and_animation(self):
        self.frame(keydown(K_i))
        self.assertTrue(self.game.paused)
        self.assertFalse(self.game.sprites_animate)
        before = self.guard_position()
        for _ in range(5):
            self.guard.last_roaming_clock_check = None
            with patch('src.game.random.choice', return_value=Direction.LEFT.value):
                self.frames(20)
        self.assertEqual(before, self.guard_position())

    def test_pause_waits_for_npc_to_finish_its_step(self):
        self.let_guard_start_a_step()
        self.frame(keydown(K_i))
        self.assertFalse(self.game.paused)
        self.frames(self.tile_size)
        self.assertTrue(self.game.paused)
        self.assert_on_a_tile(self.guard.rect)

    def test_only_start_is_read_while_paused(self):
        self.frame(keydown(K_i))
        with patch.object(self.game.cmd_menu, 'talk') as talk:
            self.frame(keydown(K_k))
            self.frame(keydown(K_RETURN))
            self.frames(5)
        talk.assert_not_called()
        self.assertFalse(self.game.cmd_menu.launch_signaled)
        self.assertTrue(self.game.paused)

    def test_unpause_lets_everything_move_again(self):
        self.frame(keydown(K_i))
        start_x = self.game.player.rect.x
        # NES: unpausing ends with JMP JoypadCheckLoop (FrameCounter = 0), so a direction held then steps at once
        self.frame(keydown(K_i), held=(K_LEFT,))
        self.assertFalse(self.game.paused)
        self.assertTrue(self.game.sprites_animate)
        self.frames(2, held=(K_LEFT,))
        self.assertLess(self.game.player.rect.x, start_x)

    def test_menu_closing_does_not_unfreeze_a_paused_game(self):
        self.frame(keydown(K_i))
        # every command ends with unpause_all_movement
        self.game.game_state.unpause_all_movement()
        before = self.guard_position()
        self.guard.last_roaming_clock_check = None
        with patch('src.game.random.choice', return_value=Direction.LEFT.value):
            self.frames(20)
        self.assertEqual(before, self.guard_position())
        self.assertFalse(self.game.sprites_animate)

    def test_start_does_not_pause_while_the_command_menu_is_open(self):
        self.open_command_menu()
        self.frame(keydown(K_i))
        self.assertFalse(self.game.paused)
        self.assertFalse(self.game.pause_requested)

    def test_stuck_npc_does_not_hold_up_the_pause_forever(self):
        self.guard.is_moving = True
        self.guard.rect.x += 2  # partway through a step it can never finish
        with patch.object(self.game, 'move_roaming_characters'):
            self.frame(keydown(K_i))
            self.frames(self.tile_size)
        self.assertTrue(self.game.paused)


class TestCommandsOnlyBetweenSteps(FreezeTestCase):
    """
    A command can't be used partway through a step (NES GameEngineLoop: A is only read between steps, since DoJoyUp
    etc. move a whole tile before returning to CheckInputs).
    Before #217, START mid-step stopped the hero between two tiles, and the command menu could still be opened while
    paused, so SEARCH (or any other command) could be used over and over with the hero stuck halfway between tiles.
    The Enter shortcut (TAKE/DOOR/TALK) had no movement check at all.
    """

    COMMANDS = ('talk', 'search', 'stairs', 'door', 'take')
    TITLES = ('TALK', 'SEARCH', 'STAIRS', 'DOOR', 'TAKE')

    def setUp(self):
        super().setUp()
        self.commands_used = []
        cmd_menu = self.game.cmd_menu
        for name in self.COMMANDS:
            real_command = getattr(cmd_menu, name)

            def record(*args, name=name, real_command=real_command, **kwargs):
                player = self.game.player
                self.commands_used.append((name, player.rect.x, player.rect.y, player.is_moving))
                return real_command(*args, **kwargs)

            setattr(cmd_menu, name, record)
            # pygame-menu keeps its own reference to each button's command
            for widget in cmd_menu.menu.get_widgets():
                if widget.get_title() == self.TITLES[self.COMMANDS.index(name)]:
                    widget.update_callback(record)
        for blocking in ('show_text_in_dialog_box', 'window_drop_down_effect', 'window_drop_up_effect'):
            patcher = patch.object(cmd_menu, blocking)
            patcher.start()
            self.addCleanup(patcher.stop)

    def frame(self, *events, held=()):
        super().frame(*events, held=held)
        # What Drawer.draw_all does with the command menu each frame
        cmd_menu = self.game.cmd_menu
        if cmd_menu.launch_signaled and not cmd_menu.menu.is_enabled():
            cmd_menu.menu.enable()
        if cmd_menu.menu.is_enabled():
            cmd_menu.menu.update(self.game.events)

    def select(self, title):
        menu = self.game.cmd_menu.menu
        for widget in menu.get_widgets():
            if widget.get_title() == title:
                menu.select_widget(widget)
                return
        self.fail(f"No {title} button")

    def spam_command(self, title, count, first_events=()):
        """Press A, pick the command and press Enter, over and over, while holding RIGHT."""
        for press in range(count):
            self.frame(*(first_events if press == 0 else ()), keydown(K_k), held=(K_RIGHT,))
            if self.game.cmd_menu.menu.is_enabled():
                self.select(title)
            self.frame(keydown(K_RETURN), held=(K_RIGHT,))

    def start_a_step(self):
        start_x = self.game.player.rect.x
        self.frames(3, held=(K_RIGHT,))
        self.assertTrue(self.game.player.is_moving)
        self.assertNotEqual(0, self.game.player.rect.x % self.tile_size)
        return start_x

    def test_commands_cannot_be_used_after_pausing_mid_step(self):
        for title in self.TITLES:
            with self.subTest(title):
                self.setUp()
                start_x = self.start_a_step()
                self.spam_command(title, self.tile_size // self.game.speed, first_events=(keydown(K_i),))
                self.assertTrue(self.game.paused)
                self.assertEqual([], self.commands_used)
                self.assertEqual(start_x + self.tile_size, self.game.player.rect.x)

    def test_commands_chosen_mid_step_wait_for_the_step_to_finish(self):
        for title in self.TITLES:
            with self.subTest(title):
                self.setUp()
                start_x = self.start_a_step()
                self.spam_command(title, self.tile_size)
                self.assertTrue(self.commands_used)
                for name, x, y, is_moving in self.commands_used:
                    self.assertFalse(is_moving, name)
                    self.assertEqual((0, 0), (x % self.tile_size, y % self.tile_size), name)
                # The first one waited for the hero to reach the next tile
                self.assertEqual(start_x + self.tile_size, self.commands_used[0][1])

    def test_enter_shortcut_does_nothing_mid_step(self):
        self.start_a_step()
        self.game.player.current_tile = 'TREASURE_BOX'
        self.game.handle_enter_key(keydown(K_RETURN))
        self.assertEqual([], self.commands_used)

    def test_enter_shortcut_still_works_standing_still(self):
        self.game.player.current_tile = 'TREASURE_BOX'
        self.game.handle_enter_key(keydown(K_RETURN))
        self.assertEqual(['take'], [name for name, *_ in self.commands_used])

    def test_enter_shortcut_does_nothing_while_the_command_menu_is_pending_or_open(self):
        self.game.player.current_tile = 'TREASURE_BOX'
        self.game.cmd_menu_requested = True
        self.game.handle_enter_key(keydown(K_RETURN))
        self.game.cmd_menu_requested = False
        self.game.cmd_menu.launch_signaled = True
        self.game.handle_enter_key(keydown(K_RETURN))
        self.assertEqual([], self.commands_used)

    def test_enter_shortcut_does_nothing_while_paused(self):
        self.frame(keydown(K_i))
        self.game.player.current_tile = 'TREASURE_BOX'
        self.frame(keydown(K_RETURN))
        self.assertEqual([], self.commands_used)
