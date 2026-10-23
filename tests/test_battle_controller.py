import unittest
from collections import defaultdict
from unittest.mock import MagicMock, Mock, patch

import pygame
from pygame import KEYDOWN, KEYUP, K_1, K_2, K_3, K_4, K_DOWN, K_ESCAPE, K_LEFT, K_RETURN, K_RIGHT, K_SPACE, K_UP, K_x
from pygame.event import Event
from src.waiting import NES_FPS, game_speed, reset_game_speed

from src import enemy as enemies
from src.color import WHITE
from src.battle_controller import BattleController
from src.enemy_lookup import enemy_string_lookup
from src.spells import Spell
from src.windows import COMBAT_COMMAND_LAYOUT


def make_game():
    game = MagicMock()
    game._ = lambda s: s
    game.auto_battle = False
    game.color = WHITE
    game.config = {"MUSIC_ENABLED": False}
    game.game_state.config = {"TILE_SIZE": 32}
    player = game.player
    player.name = "Erdrick"
    player.strength = 4
    player.current_hp = 15
    player.armor = "Clothes"
    player.inventory = []
    player.is_asleep = False
    player.is_dead = False
    player.is_stopspelled = False
    return game


def make_battle(enemy=None):
    battle = Mock()
    if enemy is None:
        enemy = Mock(hp=3, attack=5, pattern=[], dodge=0, is_asleep=False, is_stopspelled=False)
        enemy.name = "Slime"
    battle.enemy = enemy
    battle.turn = 0
    battle.last_turn = 0
    battle.no_op = False
    battle.enemy_fled = False
    return battle


def patterned_enemy(pattern):
    enemy = Mock(hp=10, max_hp=10, attack=5, dodge=0, pattern=list(pattern), is_asleep=False,
                 is_stopspelled=False)
    enemy.name = "Magician"
    return enemy


def ticks_at_frame(frame: int) -> int:
    """The first millisecond of an NES frame, counted from 0."""
    return -(-frame * 1000 // NES_FPS)


class BattlePromptFrames(unittest.TestCase):
    """Runs handle_battle_prompts one NES frame at a time, with a fake clock, the keyboard state from
    key.get_pressed and key presses posted to the real pygame event queue."""

    def setUp(self):
        pygame.init()
        pygame.event.clear()
        self.game = make_game()
        self.frame_number = 0
        patch('src.battle_controller.display').start()
        patch('src.battle_controller.time').start()
        patch('src.cursor.get_ticks', side_effect=lambda: ticks_at_frame(self.frame_number)).start()
        # frame() moves the fake clock on a frame per pass itself: the loop's real one-frame wait isn't needed
        patch('src.battle_controller.next_frame').start()
        self.held = defaultdict(int)
        patch('src.battle_controller.key.get_pressed', side_effect=lambda: self.held).start()
        self.controller = BattleController(self.game)
        self.battle = make_battle()
        self.random = patch('src.battle_controller.random.random', return_value=0.99).start()
        self.addCleanup(patch.stopall)
        self.frame()  # the first player turn opens the command window

    def patch_enemy_move(self, fled=False):
        return patch.object(self.controller, 'enemy_move', return_value=fled)

    def frame(self, *held_keys):
        """One NES frame later, with held_keys down: one pass of the battle prompt loop."""
        self.frame_number += 1
        self.held = defaultdict(int, {held_key: 1 for held_key in held_keys})
        return self.controller.handle_battle_prompts(False, self.battle)

    def frames(self, count, *held_keys):
        for _ in range(count):
            self.frame(*held_keys)

    def post(self, *keys):
        for pressed_key in keys:
            pygame.event.post(Event(KEYDOWN, key=pressed_key))

    def press(self, *keys):
        """Two frames with nothing held (so the window reads the next press), then the keys pressed and held for a
        frame; they are let go on the next frame."""
        self.frames(2)
        self.post(*keys)
        return self.frame(*keys)

    @property
    def selection(self):
        return self.controller.battle_menu_row, self.controller.battle_menu_column


FIGHT, SPELL, RUN, ITEM = (0, 0), (0, 1), (1, 0), (1, 1)


@patch('src.battle_controller.display')
@patch('src.battle_controller.time')
class TestHandleBattlePrompts(BattlePromptFrames):

    def test_no_input_does_nothing(self, mock_time, mock_display):
        self.assertFalse(self.controller.handle_battle_prompts(False, self.battle))
        self.assertEqual(self.battle.turn, 0)
        self.game.receive_damage.assert_not_called()

    def test_down_moves_to_run_without_taking_turn(self, mock_time, mock_display):
        self.press(K_DOWN)
        self.assertEqual(RUN, self.selection)
        self.press(K_UP)
        self.assertEqual(FIGHT, self.selection)
        self.assertEqual(self.battle.turn, 0)

    def test_right_and_left_move_between_columns(self, mock_time, mock_display):
        self.press(K_RIGHT)
        self.assertEqual(SPELL, self.selection)
        self.press(K_LEFT)
        self.assertEqual(FIGHT, self.selection)

    def test_moving_the_cursor_restarts_its_blink(self, mock_time, mock_display):
        # WndUpdateCrsrPos: the moved cursor is visible again right away
        with patch.object(self.controller.command_cursor, 'restart') as restart:
            self.press(K_DOWN)
        restart.assert_called_once_with(None)

    def test_cursor_is_at_the_selected_command(self, mock_time, mock_display):
        # CmdCmbtDat: FIGHT (1, 2), SPELL (9, 2), RUN (1, 4), ITEM (9, 4)
        for row, column, tile in ((0, 0, (1, 2)), (0, 1, (9, 2)), (1, 0, (1, 4)), (1, 1, (9, 4))):
            with self.subTest(row=row, column=column), patch('src.translated_window.draw_window') as draw_window:
                self.controller.battle_menu_row, self.controller.battle_menu_column = row, column
                self.controller.drawn_command_window = None  # drawn on changes only: draw it again for this check
                self.controller.handle_battle_prompts(False, self.battle)
                self.assertIs(COMBAT_COMMAND_LAYOUT, draw_window.call_args.args[1])
                self.assertEqual(tile, COMBAT_COMMAND_LAYOUT.cursor_tiles[draw_window.call_args.kwargs['cursor_index']])

    def test_chosen_command_keeps_its_cursor_on(self, mock_time, mock_display):
        # WndAPressed: the arrow is drawn once more, visible, and stays on while the command runs
        visible_during_fight = []
        with patch.object(self.controller, 'fight',
                          side_effect=lambda battle: visible_during_fight.append(
                              self.controller.command_cursor.visible())), self.patch_enemy_move(), \
                patch('src.translated_window.draw_window') as draw_window:
            self.press(K_RETURN)
        self.assertEqual([True], visible_during_fight)
        self.assertIs(draw_window.call_args_list[-1].kwargs['cursor_visible'], True)

    def test_fight_attacks_then_enemy_moves(self, mock_time, mock_display):
        with patch.object(self.controller, 'fight') as fight, self.patch_enemy_move() as enemy_move:
            self.assertFalse(self.press(K_RETURN))
        fight.assert_called_once_with(self.battle)
        enemy_move.assert_called_once_with(self.battle)
        self.assertEqual(self.battle.turn, 1)
        self.assertEqual(self.controller.last_battle_action, 'Fight')

    def test_killing_enemy_skips_enemy_turn(self, mock_time, mock_display):
        def kill(battle):
            battle.enemy.hp = 0
        with patch.object(self.controller, 'fight', side_effect=kill), \
                self.patch_enemy_move() as enemy_move:
            self.assertFalse(self.press(K_RETURN))
        enemy_move.assert_not_called()

    def test_player_dies_when_enemy_reduces_hp_to_zero(self, mock_time, mock_display):
        def lethal(battle):
            self.game.player.current_hp = 0
        with patch.object(self.controller, 'fight'), patch.object(self.controller, 'enemy_move', side_effect=lethal):
            self.press(K_RETURN)
        self.assertTrue(self.game.player.is_dead)

    def test_spell_selection_casts_spell(self, mock_time, mock_display):
        self.controller.battle_menu_column = 1
        with self.patch_enemy_move():
            self.press(K_RETURN)
        self.battle.battle_spell.assert_called_once_with(self.game.cmd_menu, self.game.player, self.battle)
        self.assertEqual(self.controller.last_battle_action, 'Spell')

    def test_spell_no_op_skips_enemy_turn(self, mock_time, mock_display):
        self.controller.battle_menu_column = 1
        self.battle.battle_spell.side_effect = lambda *args: setattr(self.battle, 'no_op', True)
        with self.patch_enemy_move() as enemy_move:
            self.press(K_RETURN)
        enemy_move.assert_not_called()

    def test_enemy_attacks_again_after_skipped_turn(self, mock_time, mock_display):
        # no_op must be cleared after a skipped turn (failed run, empty item menu, failed spell),
        # or the enemy never attacks again that battle.
        self.controller.battle_menu_row = 1
        self.battle.battle_run.return_value = False
        with patch.object(self.controller, 'fight'), self.patch_enemy_move() as enemy_move:
            self.press(K_RETURN)
            self.controller.battle_menu_row = 0
            self.press(K_RETURN)
        enemy_move.assert_called_once_with(self.battle)

    def test_successful_run_ends_battle(self, mock_time, mock_display):
        self.controller.battle_menu_row = 1
        self.battle.battle_run.return_value = True
        with self.patch_enemy_move() as enemy_move:
            self.assertTrue(self.press(K_RETURN))
        enemy_move.assert_not_called()
        self.assertTrue(self.controller.player_ran_away)
        # fight_enemy resumes the map's music once the fight is over, not the command prompt
        self.game.music_player.load_and_play_music.assert_not_called()

    def test_enemy_fleeing_after_a_blocked_run_is_not_the_hero_escaping(self, mock_time, mock_display):
        # battle_run returns True when the enemy ran away on its turn after "But was blocked in front."
        self.controller.battle_menu_row = 1

        def blocked_then_enemy_flees(*args):
            return self.controller.enemy_run_away(self.battle, self.battle.enemy)
        self.battle.battle_run.side_effect = blocked_then_enemy_flees
        self.assertTrue(self.press(K_RETURN))
        self.assertFalse(self.controller.player_ran_away)

    def test_failed_run_does_not_give_enemy_a_second_turn(self, mock_time, mock_display):
        # battle_run already lets the enemy attack when the run fails (regression test for #179)
        self.controller.battle_menu_row = 1
        self.battle.battle_run.return_value = False
        with self.patch_enemy_move() as enemy_move:
            self.assertFalse(self.press(K_RETURN))
        enemy_move.assert_not_called()
        self.assertEqual(self.battle.turn, 1)

    def test_item_with_empty_inventory_skips_enemy_turn(self, mock_time, mock_display):
        self.controller.battle_menu_row = 1
        self.controller.battle_menu_column = 1
        with self.patch_enemy_move() as enemy_move:
            self.press(K_RETURN)
        self.assertIn('Nothing of use', self.game.cmd_menu.show_line_in_dialog_box.call_args.args[0])
        enemy_move.assert_not_called()

    def test_item_with_inventory_opens_item_menu(self, mock_time, mock_display):
        self.controller.battle_menu_row = 1
        self.controller.battle_menu_column = 1
        self.game.player.inventory = ["Herb"]
        with self.patch_enemy_move():
            self.press(K_RETURN)
        self.game.cmd_menu.display_item_menu.assert_called_once_with('inventory')

    def test_auto_battle_repeats_last_action_without_input(self, mock_time, mock_display):
        self.game.auto_battle = True
        self.controller.last_battle_action = 'Fight'
        self.post(K_DOWN)
        with patch.object(self.controller, 'fight') as fight, self.patch_enemy_move():
            self.controller.handle_battle_prompts(False, self.battle)
        fight.assert_called_once()
        self.assertTrue(pygame.event.peek(KEYDOWN))  # the keyboard isn't read

    def test_asleep_player_loses_turn_on_any_key(self, mock_time, mock_display):
        # NES StartPlayerTurn: bit 0 of the roll clear, so "Thou art still asleep." and the enemy moves
        self.game.player.is_asleep = True
        with patch.object(self.controller, 'fight') as fight, \
                self.patch_enemy_move() as enemy_move, \
                patch('src.battle_controller.random.randint', return_value=0):
            self.press(K_DOWN)
        fight.assert_not_called()
        enemy_move.assert_called_once()
        self.assertEqual(self.controller.last_battle_action, 'Fight')
        self.assertTrue(self.game.player.is_asleep)
        self.assertEqual(self.game.cmd_menu.show_line_in_dialog_box.call_args.args[0], 'Thou art still asleep.\n')

    def test_asleep_player_ignores_keys_that_are_not_buttons(self, mock_time, mock_display):
        self.game.player.is_asleep = True
        with self.patch_enemy_move() as enemy_move:
            self.press(K_x, K_SPACE)
        enemy_move.assert_not_called()
        self.assertEqual(self.battle.turn, 0)

    def test_asleep_player_wakes_and_gets_the_turn(self, mock_time, mock_display):
        # NES StartPlayerTurn -> PlayerAwakes -> ShowCmbtCmd: the hero wakes and chooses a command this turn,
        # so the enemy doesn't move first.
        self.game.player.is_asleep = True
        with self.patch_enemy_move() as enemy_move, patch('src.battle_controller.random.randint', return_value=1):
            self.press(K_RETURN)
        self.assertFalse(self.game.player.is_asleep)
        enemy_move.assert_not_called()
        self.assertEqual(self.game.cmd_menu.show_line_in_dialog_box.call_args.args[0], 'Erdrick awakes.\nCommand?\n')
        self.assertFalse(self.battle.no_op)

    def test_wake_roll_is_bit_zero_of_a_random_byte(self, mock_time, mock_display):
        # 128 of the 256 rolls wake the hero, with no cap on how many turns the sleep lasts
        woke = 0
        for roll in range(256):
            self.game.player.is_asleep = True
            with self.patch_enemy_move(), patch('src.battle_controller.random.randint', return_value=roll):
                self.press(K_RETURN)
            woke += not self.game.player.is_asleep
            self.assertEqual(not self.game.player.is_asleep, roll & 1 == 1)
        self.assertEqual(woke, 128)

    def test_sleep_has_no_turn_limit(self, mock_time, mock_display):
        self.game.player.is_asleep = True
        with self.patch_enemy_move() as enemy_move, patch('src.battle_controller.random.randint', return_value=0):
            for _ in range(20):
                self.press(K_RETURN)
        self.assertTrue(self.game.player.is_asleep)
        self.assertEqual(enemy_move.call_count, 20)

    def test_enemy_does_not_flee_before_player_acts(self, mock_time, mock_display):
        # NES checks for fleeing at the start of the enemy's turn, not while waiting for the player.
        self.game.player.strength = 10
        self.random.return_value = 0
        with patch.object(self.controller, 'enemy_run_away') as run_away:
            self.assertFalse(self.controller.handle_battle_prompts(False, self.battle))
        run_away.assert_not_called()

    def test_enemy_fleeing_on_its_turn_ends_battle(self, mock_time, mock_display):
        with patch.object(self.controller, 'fight'), self.patch_enemy_move(fled=True):
            self.assertTrue(self.press(K_RETURN))
        self.assertFalse(self.game.player.is_dead)


class TestCommandWindowInput(BattlePromptFrames):
    """Bank01 WndDoSelect, WndGetButtons and WndProcessInput, as the battle command window uses them (Bank03
    StartPlayerTurn: Dowindow WND_CMD_CMB)."""

    def choose(self, *keys):
        """Move with keys, then press A."""
        for pressed_key in keys:
            self.press(pressed_key)
        return self.press(K_RETURN)

    # Where the cursor starts

    def test_every_turn_starts_on_fight(self):
        # WndInitSelect clears WndCol and WndRow every time the window opens, whatever was chosen last turn
        self.game.player.inventory = ['Herb']
        self.battle.battle_run.return_value = False
        for keys in ((K_RIGHT,), (K_DOWN,), (K_DOWN, K_RIGHT)):
            with self.subTest(keys=keys), self.patch_enemy_move():
                turn = self.battle.turn
                self.choose(*keys)
                self.assertEqual(turn + 1, self.battle.turn)
                self.frame()  # the next player turn
                self.assertEqual(FIGHT, self.selection)
        self.battle.battle_spell.assert_called_once()
        self.battle.battle_run.assert_called_once()
        self.game.cmd_menu.display_item_menu.assert_called_once_with('inventory')

    def test_every_fight_starts_on_fight(self):
        self.press(K_DOWN)
        self.controller.command_window_open = False  # fight_enemy: a new fight's first player turn
        self.frame()
        self.assertEqual(FIGHT, self.selection)

    def test_b_says_command_again_and_starts_over_on_fight(self):
        # WndBPressed: WND_ABORT matches no command, so ChkPlyrRun jumps to ShowCmbtCmd
        self.press(K_RIGHT)
        self.press(K_ESCAPE)
        self.assertEqual('Command?\n', self.game.cmd_menu.show_line_in_dialog_box.call_args.args[0])
        self.frame()
        self.assertEqual(FIGHT, self.selection)
        self.assertEqual(0, self.battle.turn)

    # Held keys

    def test_holding_a_direction_moves_the_cursor_once(self):
        with patch.object(self.controller.command_buttons, 'moved',
                          wraps=self.controller.command_buttons.moved) as moved:
            self.frames(2)
            self.post(K_DOWN)
            self.frames(120, K_DOWN)  # two seconds: the retrigger lets it be read again every 16 frames
        self.assertEqual(RUN, self.selection)
        moved.assert_called_once()

    def test_another_press_waits_for_the_retrigger_while_a_direction_is_held(self):
        # While WndBtnRetrig is set no button is read; it is cleared 11 frames after a move (FrameCounter 5 to 16)
        self.frames(2)
        self.post(K_DOWN)
        self.frame(K_DOWN)
        self.assertEqual(RUN, self.selection)
        self.post(K_RIGHT)
        self.frames(10, K_DOWN, K_RIGHT)
        self.assertEqual(RUN, self.selection)
        self.frame(K_DOWN, K_RIGHT)  # FrameCounter 16: DOWN is tested first and does nothing on the bottom row
        self.assertEqual(RUN, self.selection)
        self.frames(16, K_DOWN, K_RIGHT)  # and it wins again 16 frames later while it's held
        self.assertEqual(RUN, self.selection)
        self.frames(15, K_RIGHT)  # DOWN let go, but RIGHT still waits for the retrigger to time out
        self.assertEqual(RUN, self.selection)
        self.frame(K_RIGHT)
        self.assertEqual(ITEM, self.selection)

    # Keys from before the window opened

    def test_keys_pressed_before_the_window_opened_are_dropped(self):
        # The NES has no event queue: a key pressed and let go during the walk into the fight, the enemy's
        # fade-in, "draws near" or the enemy's turn is gone by the time the window reads the joypad
        self.controller.command_window_open = False
        self.post(K_DOWN, K_RIGHT, K_RETURN)
        pygame.event.post(Event(KEYUP, key=K_DOWN))
        with self.patch_enemy_move() as enemy_move:
            self.frames(30)
        self.assertEqual(FIGHT, self.selection)
        enemy_move.assert_not_called()
        self.assertEqual(0, self.battle.turn)

    def test_speed_keys_pressed_before_the_window_opened_still_count(self):
        self.controller.command_window_open = False
        self.post(K_DOWN, K_3)
        self.addCleanup(reset_game_speed)
        self.frame()
        self.assertEqual(4, game_speed())  # key 3 is 4x
        self.assertEqual(FIGHT, self.selection)

    def test_speed_keys_do_nothing_in_the_window(self):
        self.addCleanup(reset_game_speed)
        for speed_key in (K_1, K_2, K_3, K_4):
            self.press(speed_key)
            self.assertEqual(FIGHT, self.selection)
            self.assertEqual(0, self.battle.turn)

    def test_a_direction_held_into_the_fight_is_ignored_if_let_go_in_time(self):
        # WndDoSelect sets WndBtnRetrig = JoypadBtns = IN_RIGHT: nothing is read until every button is let go, or
        # until FrameCounter AND #$0F is 0 (11 frames, as WndInitSelect sets it to 5)
        self.controller.command_window_open = False
        self.held = defaultdict(int, {K_DOWN: 1})
        self.frame(K_DOWN)  # opens the window with DOWN held
        self.frames(10, K_DOWN)
        self.frames(30)
        self.assertEqual(FIGHT, self.selection)

    def test_a_direction_held_into_the_fight_moves_after_11_frames(self):
        self.controller.command_window_open = False
        self.held = defaultdict(int, {K_DOWN: 1})
        self.frame(K_DOWN)
        self.frames(10, K_DOWN)
        self.assertEqual(FIGHT, self.selection)
        self.frame(K_DOWN)
        self.assertEqual(RUN, self.selection)

    def test_a_held_into_the_next_turn_fights_again_after_11_frames(self):
        with patch.object(self.controller, 'fight') as fight, self.patch_enemy_move():
            self.press(K_RETURN)
            self.frame(K_RETURN)  # the next turn's window opens with A still held
            self.frames(10, K_RETURN)
            fight.assert_called_once()
            self.frame(K_RETURN)
        self.assertEqual(2, fight.call_count)

    def test_after_letting_go_the_next_press_is_read_at_once(self):
        self.controller.command_window_open = False
        self.frame(K_DOWN)
        self.frame()  # let go: the retrigger is cleared on the next frame
        self.post(K_RIGHT)
        self.frame(K_RIGHT)
        self.assertEqual(SPELL, self.selection)

    # Edges

    def test_the_cursor_stops_at_the_edges(self):
        for start, pressed_key in ((FIGHT, K_UP), (FIGHT, K_LEFT), (SPELL, K_UP), (SPELL, K_RIGHT),
                                   (RUN, K_DOWN), (RUN, K_LEFT), (ITEM, K_DOWN), (ITEM, K_RIGHT)):
            with self.subTest(start=start, key=pygame.key.name(pressed_key)):
                self.controller.battle_menu_row, self.controller.battle_menu_column = start
                with patch.object(self.controller.command_cursor, 'restart') as restart:
                    self.press(pressed_key)
                self.assertEqual(start, self.selection)
                restart.assert_not_called()  # no WndUpdateCrsrPos: the blink isn't restarted

    def test_each_direction_moves_one_step(self):
        for start, pressed_key, end in ((FIGHT, K_DOWN, RUN), (FIGHT, K_RIGHT, SPELL), (ITEM, K_UP, SPELL),
                                        (ITEM, K_LEFT, RUN)):
            with self.subTest(start=start, key=pygame.key.name(pressed_key)):
                self.controller.battle_menu_row, self.controller.battle_menu_column = start
                self.press(pressed_key)
                self.assertEqual(end, self.selection)

    # A

    def test_a_chooses_the_highlighted_command(self):
        for keys, chosen in (((), 'Fight'), ((K_RIGHT,), 'Spell'), ((K_DOWN,), 'Run'), ((K_DOWN, K_RIGHT), 'Item')):
            with self.subTest(chosen=chosen), self.patch_enemy_move(), patch.object(self.controller, 'fight'):
                self.battle.battle_run.return_value = False
                self.frame()  # the next turn's window
                self.choose(*keys)
                self.assertEqual(chosen, self.controller.last_battle_action)

    def test_a_and_a_direction_on_the_same_frame_choose_without_moving(self):
        # WndProcessInput tests A first and handles only that one button
        with patch.object(self.controller, 'fight') as fight, self.patch_enemy_move():
            self.press(K_DOWN, K_RETURN)
        fight.assert_called_once_with(self.battle)

    def test_a_tap_shorter_than_a_frame_still_counts(self):
        self.frames(2)
        self.post(K_DOWN)
        pygame.event.post(Event(KEYUP, key=K_DOWN))
        self.frame()  # already let go when the frame reads the keyboard
        self.assertEqual(RUN, self.selection)


@patch('src.battle_controller.Battle')
class TestRunBattle(unittest.TestCase):

    def setUp(self):
        self.game = make_game()
        self.controller = BattleController(self.game)
        # The opening flee and first-turn rolls are covered by TestStartFight
        patch.object(self.controller, 'start_fight', return_value=False).start()
        self.addCleanup(patch.stopall)

    def test_defeated_enemy_triggers_victory(self, mock_battle_class):
        battle = mock_battle_class.return_value
        battle.enemy.hp = 3

        def kill(run_away, current_battle):
            current_battle.enemy.hp = 0
            return False
        with patch.object(self.controller, 'handle_battle_prompts', side_effect=kill):
            self.controller.run_battle(['Slime'])
        battle.enemy_defeated.assert_called_once()
        # enemy_defeated has already resumed the map music after the victory music (ChkLevelUp, ResumeMusicTbl)
        self.game.music_player.load_and_play_music.assert_not_called()

    def test_force_enemy_overrides_zone_enemies(self, mock_battle_class):
        self.game.config["FORCE_ENEMY"] = "Poltergeist"
        mock_battle_class.return_value.enemy.hp = 3
        with patch.object(self.controller, 'handle_battle_prompts', return_value=True):
            self.controller.run_battle(['Slime'])
        self.assertEqual(mock_battle_class.call_args.args[1], "Poltergeist")

    def test_command_menu_sees_current_battle_only_during_battle(self, mock_battle_class):
        battle = mock_battle_class.return_value
        battle.enemy.hp = 3
        seen = []

        def record(run_away, current_battle):
            seen.append(self.game.cmd_menu.current_battle)
            return True
        with patch.object(self.controller, 'handle_battle_prompts', side_effect=record):
            self.controller.run_battle(['Slime'])
        self.assertEqual(seen, [battle])
        self.assertIsNone(self.game.cmd_menu.current_battle)

    def test_player_status_cleared_at_battle_start(self, mock_battle_class):
        mock_battle_class.return_value.enemy.hp = 3
        player = self.game.player
        player.is_asleep, player.is_stopspelled = True, True
        seen = []

        def record(run_away, current_battle):
            seen.append((player.is_asleep, player.is_stopspelled))
            return True
        with patch.object(self.controller, 'handle_battle_prompts', side_effect=record):
            self.controller.run_battle(['Slime'])
        self.assertEqual(seen, [(False, False)])

    def test_enemy_fleeing_at_the_start_skips_the_fight(self, mock_battle_class):
        mock_battle_class.return_value.enemy.hp = 3
        self.controller.start_fight.return_value = True
        with patch.object(self.controller, 'handle_battle_prompts') as prompts:
            self.assertEqual(self.controller.run_battle(['Slime']).value, 'escaped')
        prompts.assert_not_called()
        mock_battle_class.return_value.enemy_defeated.assert_not_called()

    def test_repel_avoids_weak_enemies_on_the_overworld(self, mock_battle_class):
        # Slime repel value 5: repelled when 5 - defense // 2 <= 5 // 2, i.e. defense >= 6
        self.game.repel_timer = 255
        self.game.current_map.identifier = 'Alefgard'
        for defense, repelled in ((5, False), (6, True)):
            with self.subTest(defense=defense):
                self.game.player.defense_power = defense
                self.assertEqual(self.controller.is_repelled('Slime'), repelled)
        self.controller.run_battle(['Slime'])
        mock_battle_class.assert_not_called()

    def test_repel_only_works_on_the_overworld_while_active(self, mock_battle_class):
        self.game.player.defense_power = 100
        self.game.current_map.identifier = 'SwampCave'
        self.game.repel_timer = 255
        self.assertFalse(self.controller.is_repelled('Slime'))
        self.game.current_map.identifier = 'Alefgard'
        self.game.repel_timer = 0
        self.assertFalse(self.controller.is_repelled('Slime'))

    def test_running_away_skips_victory(self, mock_battle_class):
        battle = mock_battle_class.return_value
        battle.enemy.hp = 3
        with patch.object(self.controller, 'handle_battle_prompts', return_value=True):
            self.controller.run_battle(['Slime'])
        battle.enemy_defeated.assert_not_called()
        self.game.music_player.load_and_play_music.assert_called_once()

    # launch_battle tells Game.handle_death whether to draw the in-battle death screen: only a defeat keeps it set

    def test_launch_battle_is_cleared_after_a_win_or_an_escape(self, mock_battle_class):
        battle = mock_battle_class.return_value

        def kill(run_away, current_battle):
            current_battle.enemy.hp = 0
            return False
        for prompts in (dict(side_effect=kill), dict(return_value=True)):
            with self.subTest(prompts=prompts):
                battle.enemy.hp = 3
                self.controller.launch_battle = True
                with patch.object(self.controller, 'handle_battle_prompts', **prompts):
                    self.controller.run_battle(['Slime'])
                self.assertFalse(self.controller.launch_battle)

    def test_launch_battle_stays_set_after_a_defeat(self, mock_battle_class):
        mock_battle_class.return_value.enemy.hp = 3

        def die(run_away, current_battle):
            self.game.player.is_dead = True
            return False
        with patch.object(self.controller, 'handle_battle_prompts', side_effect=die):
            self.assertEqual(self.controller.run_battle(['Slime']).value, 'defeat')
        self.assertTrue(self.controller.launch_battle)
        self.game.music_player.load_and_play_music.assert_not_called()  # the death music comes next


@patch('pygame.mixer.music')
@patch('src.battle_controller.Battle')
class TestMapMusicAfterAFight(unittest.TestCase):
    """However a fight ends, the map's music starts exactly once, through MusicPlayer."""

    def setUp(self):
        self.game = make_game()
        self.game.config["MUSIC_ENABLED"] = True
        self.controller = BattleController(self.game)
        patch.object(self.controller, 'start_fight', return_value=False).start()
        patch.object(self.controller, 'draw_command_window').start()
        patch.object(self.controller, 'open_command_window').start()
        patch.object(self.controller, 'step_back_after_running').start()
        patch('src.battle_controller.time').start()
        self.addCleanup(patch.stopall)
        # auto battle repeats RUN without waiting for a key
        self.game.auto_battle = True
        self.controller.last_battle_action = 'Run'

    @staticmethod
    def battle(mock_battle_class, name='Slime'):
        battle = mock_battle_class.return_value
        battle.enemy.name = name
        battle.enemy.hp = 3
        battle.enemy_fled = False
        battle.turn = battle.last_turn = 0
        return battle

    def map_music_starts(self, mixer_music):
        mixer_music.play.assert_not_called()  # never around MusicPlayer
        return [c.args for c in self.game.music_player.load_and_play_music.call_args_list]

    def test_battle_music_goes_through_music_player(self, mock_battle_class, mixer_music):
        battle = self.battle(mock_battle_class)
        battle.battle_run.return_value = True
        self.controller.run_battle(['Slime'])
        battle.play_battle_music.assert_called_once_with(self.game.music_player)

    def test_running_away(self, mock_battle_class, mixer_music):
        self.battle(mock_battle_class).battle_run.return_value = True
        self.assertEqual(self.controller.run_battle(['Slime']).value, 'escaped')
        self.assertEqual(self.map_music_starts(mixer_music), [(self.game.current_map.music_file_path,)])
        self.controller.step_back_after_running.assert_called_once()

    def test_enemy_running_away_at_the_start(self, mock_battle_class, mixer_music):
        battle = self.battle(mock_battle_class)
        self.controller.start_fight.side_effect = lambda b: self.controller.enemy_run_away(b, b.enemy)
        self.assertEqual(self.controller.run_battle(['Slime']).value, 'escaped')
        self.assertEqual(self.map_music_starts(mixer_music), [(self.game.current_map.music_file_path,)])
        battle.battle_run.assert_not_called()
        self.controller.step_back_after_running.assert_not_called()

    def test_enemy_running_away_after_a_blocked_run(self, mock_battle_class, mixer_music):
        battle = self.battle(mock_battle_class)
        battle.battle_run.side_effect = lambda *args: self.controller.enemy_run_away(battle, battle.enemy)
        self.assertEqual(self.controller.run_battle(['Slime']).value, 'escaped')
        self.assertEqual(self.map_music_starts(mixer_music), [(self.game.current_map.music_file_path,)])
        # NES: the hero didn't escape, so he isn't moved back off a guardian's block
        self.controller.step_back_after_running.assert_not_called()

    def test_beating_the_dragonlords_final_form(self, mock_battle_class, mixer_music):
        battle = self.battle(mock_battle_class, 'Dragonlord 2')

        def kill(run_away, current_battle):
            current_battle.enemy.hp = 0
            return False

        def final_boss_defeated(*args):
            # Ending.final_boss_defeated -> change_map, which starts the overworld music
            self.game.music_player.load_and_play_music('overworld')
        battle.enemy_defeated.side_effect = final_boss_defeated
        with patch.object(self.controller, 'handle_battle_prompts', side_effect=kill):
            self.assertEqual(self.controller.start_scripted_battle('Dragonlord 2').value, 'victory')
        self.assertEqual(self.map_music_starts(mixer_music), [('overworld',)])


class TestEnemyRunAway(unittest.TestCase):

    def setUp(self):
        self.game = make_game()
        self.controller = BattleController(self.game)
        self.battle = make_battle()

    def test_enemy_run_away(self):
        self.assertTrue(self.controller.enemy_run_away(self.battle, self.battle.enemy))
        self.game.cmd_menu.show_line_in_dialog_box.assert_called_once()
        self.assertEqual(self.game.cmd_menu.show_line_in_dialog_box.call_args.args[0], 'The Slime is running away.')
        self.battle.make_enemy_image_disappear.assert_called_once_with(self.game.screen)
        self.assertTrue(self.battle.enemy_fled)
        # the map's music is resumed by fight_enemy once the fight is over
        self.game.music_player.load_and_play_music.assert_not_called()


class TestHeroAttack(unittest.TestCase):

    def setUp(self):
        self.game = make_game()
        self.controller = BattleController(self.game)
        self.battle = make_battle()
        self.battle.enemy.hp = 10
        self.battle.enemy.dodge = 1 / 64

    def test_hit_reduces_enemy_hp(self):
        self.battle.calculate_attack_damage.return_value = 4
        with patch('src.battle_controller.random.randint', return_value=1):
            self.controller.fight(self.battle)
        self.assertEqual(self.battle.enemy.hp, 6)
        self.game.sound.play_sound.assert_called_with(self.game.directories.hit_sfx)

    def test_zero_damage_misses(self):
        self.battle.calculate_attack_damage.return_value = 0
        self.controller.hero_attack(self.battle)
        self.battle.missed_attack.assert_called_once_with(self.game.cmd_menu)
        self.assertEqual(self.battle.enemy.hp, 10)

    def test_sleeping_enemy_cannot_dodge(self):
        self.battle.enemy.is_asleep = True
        self.battle.calculate_attack_damage.return_value = 4
        with patch('src.battle_controller.random.randint', return_value=0):
            self.controller.hero_attack(self.battle)
        self.assertEqual(self.battle.enemy.hp, 6)

    def test_enemy_can_dodge(self):
        # NES SetEnDmg1: dodge 1/64 means only a 0-63 roll of 0 dodges
        self.battle.calculate_attack_damage.return_value = 4
        with patch('src.battle_controller.random.randint', return_value=64):
            self.controller.hero_attack(self.battle)
        self.assertEqual(self.battle.enemy.hp, 10)
        self.game.sound.play_sound.assert_called_with(self.game.directories.missed_sfx)
        self.game.drawer.flash_enemy.assert_not_called()

    def test_hit_flashes_enemy_red_before_the_damage_text(self):
        # NES PlyrHitEn: SFX, PaletteFlash, then "The enemy's Hit Points have been reduced"
        self.battle.calculate_attack_damage.return_value = 4
        order = []
        self.game.drawer.flash_enemy.side_effect = lambda *a: order.append('flash')
        self.game.cmd_menu.show_line_in_dialog_box.side_effect = lambda line, **k: order.append(line)
        with patch('src.battle_controller.random.random', return_value=0.5):
            self.controller.hero_attack(self.battle)
        self.game.drawer.flash_enemy.assert_called_once_with(self.game.screen, 'Slime')
        self.assertEqual(order[-2:], ['flash', "The Slime's Hit Points have been reduced by 4.\n"])

    def test_miss_does_not_flash_enemy(self):
        self.battle.calculate_attack_damage.return_value = 0
        self.controller.hero_attack(self.battle)
        self.game.drawer.flash_enemy.assert_not_called()


@patch('src.battle_controller.player_hit_shake')
class TestPlayerHitEffect(unittest.TestCase):

    def setUp(self):
        self.game = make_game()
        self.game.config = {"TILE_SIZE": 32}
        self.controller = BattleController(self.game)
        self.battle = make_battle()
        self.game.cmd_menu.current_battle = self.battle

    def test_hit_shakes_without_red_flash(self, mock_shake):
        self.controller.player_hit_effect()
        mock_shake.assert_called_once_with(
            self.game.screen, self.game.config, deathblow=False,
            enemy=self.game.drawer.get_enemy_image.return_value,
            background=(self.battle.get_battle_background_image.return_value, (160, 128)), shake=True)
        self.game.drawer.get_enemy_image.assert_called_once_with('Slime')

    def test_deathblow_flashes_red(self, mock_shake):
        self.game.player.current_hp = 0
        self.controller.player_hit_effect()
        self.assertTrue(mock_shake.call_args.kwargs['deathblow'])

    def test_final_form_does_not_shake(self, mock_shake):
        # NES PlayerHit/DoShake: no shake and no red flash against EN_DRAGONLORD2
        self.battle.enemy.name = 'Dragonlord 2'
        self.game.player.current_hp = 0
        self.controller.player_hit_effect()
        self.assertFalse(mock_shake.call_args.kwargs['shake'])
        self.assertIsNone(mock_shake.call_args.kwargs['background'])

    def test_no_battle_no_effect(self, mock_shake):
        self.game.cmd_menu.current_battle = None
        self.controller.player_hit_effect()
        mock_shake.assert_not_called()


@patch('src.battle_controller.time')
class TestEnemyMove(unittest.TestCase):

    def setUp(self):
        self.game = make_game()
        self.controller = BattleController(self.game)
        patch('src.battle_controller.wait').start()  # the 1-second pause after an enemy's spell
        self.addCleanup(patch.stopall)

    def move(self, enemy, roll=0, effect=None):
        battle = make_battle(enemy)
        randint = Mock(side_effect=lambda a, b: roll if (a, b) == (0, 99) else (effect if effect is not None else a))
        with patch('src.battle_controller.random.randint', randint), \
                patch('src.battle_controller.calculate_enemy_attack_damage', return_value=2):
            self.controller.enemy_move(battle)
        return battle

    def last_message(self):
        return self.game.cmd_menu.show_line_in_dialog_box.call_args.args[0]

    def test_enemy_without_pattern_attacks(self, mock_time):
        self.move(enemies.Slime())
        self.game.receive_damage.assert_called_once_with(2)
        self.assertEqual(self.last_message(), 'The Slime attacks!\n')

    def test_enemy_attack_can_miss(self, mock_time):
        battle = make_battle()
        with patch('src.battle_controller.calculate_enemy_attack_damage', return_value=0):
            self.controller.enemy_move(battle)
        battle.enemy_missed_attack.assert_called_once_with(self.game.cmd_menu)
        battle.missed_attack.assert_not_called()
        self.game.receive_damage.assert_not_called()

    def test_successful_hurt_damages_player(self, mock_time):
        self.move(enemies.Magician(), roll=0, effect=7)
        self.game.receive_damage.assert_called_once_with(7)
        self.game.sound.play_sound.assert_any_call(self.game.directories.spell_sfx)

    def test_failed_spell_roll_falls_through_to_attack(self, mock_time):
        self.move(enemies.Magician(), roll=99)
        self.game.receive_damage.assert_called_once_with(2)
        self.assertEqual(self.last_message(), 'The Magician attacks!\n')

    def test_magic_armor_reduces_hurt(self, mock_time):
        self.game.player.armor = "Magic Armor"
        self.move(enemies.Magician(), roll=0, effect=10)
        self.assertEqual(self.game.receive_damage.call_args.args[0], 6)

    def test_sleep_puts_player_to_sleep_and_the_enemy_moves_again(self, mock_time):
        # NES EnCastSleep -> PlayerAsleepDialog -> StartEnemyTurn: the hero gets no wake roll before the enemy's
        # next turn. SLEEP is skipped on that turn (the hero is asleep), so the enemy attacks.
        self.move(patterned_enemy([(100, Spell.SLEEP, True), Spell.ATTACK]))
        self.assertTrue(self.game.player.is_asleep)
        self.game.receive_damage.assert_called_once_with(2)
        shown = [c.args[0] for c in self.game.cmd_menu.show_line_in_dialog_box.call_args_list]
        self.assertEqual(shown[1:3], ['Thou art asleep.\n', 'Thou art still asleep.\n'])

    def test_no_second_enemy_turn_if_the_hero_was_already_asleep(self, mock_time):
        self.game.player.is_asleep = True
        with patch.object(self.controller, 'enemy_turn', return_value=False) as enemy_turn:
            self.controller.enemy_move(make_battle())
        enemy_turn.assert_called_once()

    def test_sleep_skipped_when_player_already_asleep(self, mock_time):
        self.game.player.is_asleep = True
        self.move(patterned_enemy([(100, Spell.SLEEP, True), Spell.ATTACK]))
        self.game.receive_damage.assert_called_once_with(2)

    def test_stopspell(self, mock_time):
        self.move(patterned_enemy([(100, Spell.STOPSPELL, True), Spell.ATTACK]), effect=1)
        self.assertTrue(self.game.player.is_stopspelled)

    def test_erdricks_armor_blocks_stopspell(self, mock_time):
        self.game.player.armor = "Erdrick's Armor"
        self.move(patterned_enemy([(100, Spell.STOPSPELL, True), Spell.ATTACK]), effect=1)
        self.assertFalse(self.game.player.is_stopspelled)

    def test_firebreath(self, mock_time):
        self.move(patterned_enemy([(100, Spell.FIREBREATH, True), Spell.ATTACK]), effect=20)
        self.game.receive_damage.assert_called_once_with(20)
        self.game.sound.play_sound.assert_any_call(self.game.directories.breathe_fire_sfx)
        self.assertEqual(self.game.cmd_menu.show_line_in_dialog_box.call_args_list[0].args[0],
                         'The Magician is breathing fire.\n')

    def test_erdricks_armor_reduces_firebreath(self, mock_time):
        self.game.player.armor = "Erdrick's Armor"
        self.move(patterned_enemy([(100, Spell.FIREBREATH, True), Spell.ATTACK]), effect=20)
        self.assertEqual(self.game.receive_damage.call_args.args[0], 12)

    def test_heal_condition_false_skips_to_next_entry(self, mock_time):
        self.move(enemies.Drakeema(), roll=0, effect=5)
        # HEAL is skipped at full HP, so HURT is cast instead
        self.game.receive_damage.assert_called_once_with(5)

    def test_heal_recovers_enemy_hp(self, mock_time):
        # HP drops after the pattern was last built; the heal check must still see the new HP.
        drakeema = enemies.Drakeema()
        drakeema.hp = 1
        self.move(drakeema, roll=0, effect=5)
        self.assertEqual(drakeema.hp, 6)
        self.game.receive_damage.assert_not_called()

    def test_heal_does_not_exceed_max_hp(self, mock_time):
        drakeema = enemies.Drakeema()
        drakeema.hp = 1
        self.move(drakeema, roll=0, effect=25)
        self.assertEqual(drakeema.hp, drakeema.max_hp)

    def test_heal_at_exactly_one_quarter_hp(self, mock_time):
        # NES casts heal when current HP <= max HP // 4 (Drakeema: 20 // 4 = 5).
        drakeema = enemies.Drakeema()
        drakeema.hp = 5
        self.move(drakeema, roll=0, effect=5)
        self.assertEqual(drakeema.hp, 10)

    def test_no_heal_above_one_quarter_hp(self, mock_time):
        drakeema = enemies.Drakeema()
        drakeema.hp = 6
        self.move(drakeema, roll=0, effect=5)
        self.assertEqual(drakeema.hp, 6)

    def test_spell_chance_is_exact_percentage(self, mock_time):
        # A 75% spell casts on rolls 0-74 of 0-99.
        self.move(patterned_enemy([(75, Spell.HURT, True), Spell.ATTACK]), roll=74, effect=7)
        self.game.receive_damage.assert_called_once_with(7)
        self.game.reset_mock()
        self.move(patterned_enemy([(75, Spell.HURT, True), Spell.ATTACK]), roll=75, effect=7)
        self.game.receive_damage.assert_called_once_with(2)

    def test_stopspell_skipped_when_already_stopspelled(self, mock_time):
        self.game.player.is_stopspelled = True
        self.move(patterned_enemy([(100, Spell.STOPSPELL, True), Spell.ATTACK]), effect=1)
        self.game.receive_damage.assert_called_once_with(2)
        self.assertEqual(self.last_message(), 'The Magician attacks!\n')

    def test_sleeping_enemy_stays_asleep(self, mock_time):
        slime = enemies.Slime()
        slime.is_asleep = True
        battle = make_battle(slime)
        with patch('src.battle_controller.random.randint', return_value=2), \
                patch('src.battle_controller.calculate_enemy_attack_damage', return_value=2):
            self.assertFalse(self.controller.enemy_move(battle))
        self.assertTrue(slime.is_asleep)
        self.game.receive_damage.assert_not_called()
        self.assertEqual(self.last_message(), 'The Slime is asleep.')

    def test_sleeping_enemy_wakes_and_attacks(self, mock_time):
        slime = enemies.Slime()
        slime.is_asleep = True
        battle = make_battle(slime)
        with patch('src.battle_controller.random.randint', return_value=1), \
                patch('src.battle_controller.calculate_enemy_attack_damage', return_value=2):
            self.controller.enemy_move(battle)
        self.assertFalse(slime.is_asleep)
        messages = [c.args[0] for c in self.game.cmd_menu.show_line_in_dialog_box.call_args_list]
        self.assertEqual(messages[0], 'Slime hath woken up.')
        self.game.receive_damage.assert_called_once_with(2)

    def test_sleeping_enemy_wakes_one_time_in_three(self, mock_time):
        slime = enemies.Slime()
        slime.is_asleep = True
        with patch('src.battle_controller.random.randint', return_value=1) as randint, \
                patch('src.battle_controller.calculate_enemy_attack_damage', return_value=2):
            self.controller.enemy_move(make_battle(slime))
        self.assertEqual(randint.call_args_list[0].args, (1, 3))

    def test_sleeping_enemy_does_not_flee(self, mock_time):
        self.game.player.strength = 10
        slime = enemies.Slime()
        slime.is_asleep = True
        with patch('src.battle_controller.random.random', return_value=0), \
                patch('src.battle_controller.random.randint', return_value=2), \
                patch.object(self.controller, 'enemy_run_away') as run_away:
            self.assertFalse(self.controller.enemy_move(make_battle(slime)))
        run_away.assert_not_called()

    def test_stopspelled_enemy_chants_but_spell_is_blocked(self, mock_time):
        enemy = patterned_enemy([(100, Spell.HURT, True), Spell.ATTACK])
        enemy.is_stopspelled = True
        self.move(enemy, effect=7)
        self.game.receive_damage.assert_not_called()
        messages = [c.args[0] for c in self.game.cmd_menu.show_line_in_dialog_box.call_args_list]
        self.assertEqual(messages, ['Magician chants the spell of HURT.', 'But that spell hath been blocked.'])

    def test_stopspell_does_not_block_fire_breath(self, mock_time):
        enemy = patterned_enemy([(100, Spell.FIREBREATH, True), Spell.ATTACK])
        enemy.is_stopspelled = True
        self.move(enemy, effect=20)
        self.game.receive_damage.assert_called_once_with(20)

    def test_enemy_flees_from_strong_player(self, mock_time):
        self.game.player.strength = 10
        battle = make_battle(enemies.Slime())
        with patch('src.battle_controller.random.randint', return_value=4), \
                patch.object(self.controller, 'enemy_run_away', return_value=True) as run_away:
            self.assertTrue(self.controller.enemy_move(battle))
        run_away.assert_called_once_with(battle, battle.enemy)
        self.game.receive_damage.assert_not_called()

    def test_enemy_attacks_when_flee_roll_fails(self, mock_time):
        self.game.player.strength = 10
        battle = make_battle(enemies.Slime())
        with patch('src.battle_controller.random.randint', return_value=1), \
                patch('src.battle_controller.calculate_enemy_attack_damage', return_value=2):
            self.assertFalse(self.controller.enemy_move(battle))
        self.game.receive_damage.assert_called_once_with(2)

    def test_enemy_does_not_flee_from_weak_player(self, mock_time):
        self.game.player.strength = 9
        battle = make_battle(enemies.Slime())
        with patch('src.battle_controller.random.randint', return_value=0), \
                patch('src.battle_controller.calculate_enemy_attack_damage', return_value=2):
            self.assertFalse(self.controller.enemy_move(battle))
        self.game.receive_damage.assert_called_once_with(2)

    def test_every_enemy_can_take_a_turn(self, mock_time):
        # Every pattern entry must be ATTACK or a (chance, spell, condition) 3-tuple;
        # Metal Slime, Poltergeist and Specter used to crash with 2-tuples.
        for name, enemy_class in enemy_string_lookup.items():
            for roll in (0, 99):
                with self.subTest(enemy=name, roll=roll):
                    self.game.reset_mock()
                    self.move(enemy_class(), roll=roll)

    def test_pattern_survives_refresh(self, mock_time):
        # Patterns assigned in __init__ instead of set_pattern() were wiped after the first turn.
        for enemy_class in (enemies.Magidrakee, enemies.Poltergeist):
            with self.subTest(enemy=enemy_class.__name__):
                enemy = enemy_class()
                original = list(enemy.pattern)
                enemy.refresh_pattern()
                self.assertEqual(enemy.pattern, original)

    def test_starwyvern_acts_at_full_hp(self, mock_time):
        # A bare "FIREBREATH" in Starwyvern's pattern used to make it skip its turn.
        self.move(enemies.Starwyvern(), roll=99)
        self.game.receive_damage.assert_called_once()

    def test_armor_reduced_damage_is_whole_number(self, mock_time):
        self.game.player.armor = "Magic Armor"
        self.move(enemies.Magician(), roll=0, effect=10)
        self.assertIsInstance(self.game.receive_damage.call_args.args[0], int)


class TestStartFight(unittest.TestCase):
    """NES InitFight after SetEnHP: CheckEnRun, then CalcWhoIsNext."""

    def setUp(self):
        self.game = make_game()
        self.game.player.agility = 10
        self.controller = BattleController(self.game)
        self.battle = make_battle(enemies.Slime())  # attack 5, defense 3

    def start(self, rolls):
        with patch('src.battle_controller.random.randint', side_effect=rolls):
            return self.controller.start_fight(self.battle)

    def test_enemy_can_run_away_as_soon_as_it_appears(self):
        self.game.player.strength = 10
        with patch.object(self.controller, 'enemy_run_away', return_value=True) as run_away, \
                patch.object(self.controller, 'enemy_move') as enemy_move:
            self.assertTrue(self.start([0]))
        run_away.assert_called_once_with(self.battle, self.battle.enemy)
        enemy_move.assert_not_called()

    def test_hero_acts_first_when_agility_roll_wins(self):
        # flee roll 1 (no flee), enemy roll 63 * defense 3 = 189 vs. hero roll 19 * agility 10 = 190
        with patch.object(self.controller, 'enemy_move') as enemy_move:
            self.assertFalse(self.start([1, 63, 19]))
        enemy_move.assert_not_called()
        self.game.cmd_menu.show_line_in_dialog_box.assert_not_called()

    def test_tie_goes_to_the_hero(self):
        # 63 * 3 == 63 * 3: CalcWhoIsNext's subtraction doesn't borrow, so the carry is set
        self.game.player.agility = 3
        with patch.object(self.controller, 'enemy_move') as enemy_move:
            self.start([1, 63, 63])
        enemy_move.assert_not_called()

    def test_enemy_attacks_before_the_hero_is_ready(self):
        # 63 * 3 = 189 vs. 18 * 10 = 180
        with patch.object(self.controller, 'enemy_move', return_value=False) as enemy_move:
            self.assertFalse(self.start([1, 63, 18]))
        enemy_move.assert_called_once_with(self.battle)
        self.assertEqual(self.game.cmd_menu.show_line_in_dialog_box.call_args.args[0],
                         'The Slime attacked before Erdrick was ready.')

    def test_enemy_roll_uses_only_six_bits(self):
        # rand 255 & 0x3F = 63
        with patch.object(self.controller, 'enemy_move') as enemy_move:
            self.start([1, 255, 19])
        enemy_move.assert_not_called()

    def test_ambush_can_kill_the_hero(self):
        def lethal(battle):
            self.game.player.current_hp = 0
            return False
        with patch.object(self.controller, 'enemy_move', side_effect=lethal):
            self.assertFalse(self.start([1, 63, 0]))
        self.assertTrue(self.game.player.is_dead)

    def test_enemy_can_flee_during_its_ambush_turn(self):
        with patch.object(self.controller, 'enemy_move', return_value=True):
            self.assertTrue(self.start([1, 63, 0]))


@patch('src.battle_controller.time')
class TestEnemySpellResults(unittest.TestCase):
    """The text after an enemy's HEAL and STOPSPELL (NES EnemyAddHP, EnCastStopspell)."""

    def setUp(self):
        self.game = make_game()
        self.controller = BattleController(self.game)

    def cast(self, spell, roll, hp=2):
        enemy = patterned_enemy([(100, spell, True), Spell.ATTACK])
        enemy.hp = hp
        enemy.recover_hp = lambda amount: setattr(enemy, 'hp', min(enemy.hp + amount, enemy.max_hp))
        battle = make_battle(enemy)
        with patch('src.battle_controller.random.randint', side_effect=lambda a, b: roll if (a, b) == (0, 255)
                   else a):
            self.controller.enemy_move(battle)
        return enemy

    def shown(self):
        return [c.args[0] for c in self.game.cmd_menu.show_line_in_dialog_box.call_args_list]

    def test_heal_says_the_enemy_recovered(self, mock_time):
        enemy = self.cast(Spell.HEAL, roll=1)
        self.assertEqual(enemy.hp, 10)
        self.assertEqual(self.shown()[-1], 'The Magician hath recovered.')

    def test_stopspell_success_text(self, mock_time):
        # flee roll 1 (no flee), then bit 0 set: the hero is stopspelled
        self.cast(Spell.STOPSPELL, roll=1)
        self.assertTrue(self.game.player.is_stopspelled)
        self.assertEqual(self.shown()[-1], "Erdrick's spell is blocked.")

    def test_stopspell_failure_text(self, mock_time):
        self.cast(Spell.STOPSPELL, roll=2)
        self.assertFalse(self.game.player.is_stopspelled)
        self.assertEqual(self.shown()[-1], 'The spell will not work.')

    def test_erdricks_armor_always_blocks_stopspell(self, mock_time):
        self.game.player.armor = "Erdrick's Armor"
        self.cast(Spell.STOPSPELL, roll=1)
        self.assertFalse(self.game.player.is_stopspelled)
        self.assertEqual(self.shown()[-1], 'The spell will not work.')


if __name__ == '__main__':
    unittest.main()
