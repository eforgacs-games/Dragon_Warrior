"""SMART A (the options overlay, SMART_A): with it on, A on the map does TALK, TAKE, DOOR or STAIRS when one applies,
in that order, and otherwise opens COMMAND (Game.smart_command, run_smart_command). Off, the NES: A always opens
COMMAND. Enter always does the smart command, and opens nothing when none applies."""
from unittest.mock import patch

from pygame import K_RETURN, K_RIGHT, K_i, K_k

from src.options_overlay import OPTION_ROWS
from src.options_screen import DEFAULT_OPTIONS, options_from_save, options_to_save
from tests.test_freeze_movement import FreezeTestCase, keydown


class SmartATestCase(FreezeTestCase):

    COMMANDS = ('talk', 'take', 'door', 'stairs')

    def setUp(self):
        super().setUp()
        self.used: list[str] = []
        cmd_menu = self.game.cmd_menu
        for name in self.COMMANDS:
            patcher = patch.object(cmd_menu, name, side_effect=lambda name=name: self.used.append(name))
            patcher.start()
            self.addCleanup(patcher.stop)
        self.game.config['SMART_A'] = True
        self.addCleanup(self.game.config.update, SMART_A=False)
        # Nothing applies, until a test puts it there
        self.npc = self.patch(cmd_menu, 'check_across_from_npc', False)
        self.door = self.patch(cmd_menu, 'find_door', None)
        self.game.player.current_tile = 'BRICK'

    def patch(self, owner, name, value):
        patcher = patch.object(owner, name, return_value=value)
        mock = patcher.start()
        self.addCleanup(patcher.stop)
        return mock

    def press_a(self, held=()):
        """A, then frames until the COMMAND window would have opened."""
        self.frame(keydown(K_k), held=held)
        for _ in range(40):
            if not self.game.movement.freeze_pending:
                break
            self.frame(held=held)


class TestOrder(SmartATestCase):

    def test_nothing_applies(self):
        self.assertIsNone(self.game.smart_command())

    def test_talk_first(self):
        self.npc.return_value = True
        self.game.player.current_tile = 'TREASURE_BOX'
        self.assertEqual('TALK', self.game.smart_command())

    def test_not_talk_during_the_opening_dialog(self):
        self.npc.return_value = True
        self.game.game_state.is_initial_dialog = True
        self.assertIsNone(self.game.smart_command())

    def test_take_on_a_chest(self):
        self.game.player.current_tile = 'TREASURE_BOX'
        self.door.return_value = (1, 1)
        self.game.player.inventory.append('Magic Key')
        self.assertEqual('TAKE', self.game.smart_command())

    def test_door_only_with_a_key(self):
        self.door.return_value = (1, 1)
        self.assertIsNone(self.game.smart_command())
        self.game.player.inventory.append('Magic Key')
        self.assertEqual('DOOR', self.game.smart_command())

    def test_stairs(self):
        position = (self.game.player.row, self.game.player.column)
        with patch.dict(self.game.current_map.staircases, {position: {'map': 'X'}}):
            self.game.player.current_tile = 'BRICK_STAIR_DOWN'
            self.assertEqual('STAIRS', self.game.smart_command())
        self.assertIsNone(self.game.smart_command())  # a stair tile that leads nowhere


class TestTheAButton(SmartATestCase):

    def test_off_a_opens_command(self):
        self.game.config['SMART_A'] = False
        self.game.player.current_tile = 'TREASURE_BOX'
        self.press_a()
        self.assertTrue(self.game.cmd_menu.launch_signaled)
        self.assertEqual([], self.used)

    def test_on_a_does_the_command(self):
        self.game.player.current_tile = 'TREASURE_BOX'
        with patch.object(self.game.cmd_menu, 'play_menu_button_sound') as sound:
            self.press_a()
        self.assertEqual(['take'], self.used)
        sound.assert_called_once()
        self.assertFalse(self.game.cmd_menu.launch_signaled)
        self.assertFalse(self.game.movement.freeze_pending)

    def test_on_a_opens_command_when_nothing_applies(self):
        self.press_a()
        self.assertTrue(self.game.cmd_menu.launch_signaled)
        self.assertEqual([], self.used)

    def test_mid_step_it_waits_for_the_step(self):
        # Pressed partway through a step, the command runs on the tile the hero gets to, like the COMMAND window
        start_x = self.game.player.rect.x
        self.frames(3, held=(K_RIGHT,))
        self.assertTrue(self.game.player.is_moving)
        where = []
        self.game.cmd_menu.take.side_effect = lambda: where.append((self.game.player.rect.x, self.game.player.is_moving))
        with patch.object(self.game, 'smart_command', return_value='TAKE'):
            self.frame(keydown(K_k))
            self.assertEqual([], where)
            for _ in range(self.tile_size * 2):
                self.frame()
        self.assertEqual([(start_x + self.tile_size, False)], where)

    def test_start_after_a_pauses_instead(self):
        self.game.player.current_tile = 'TREASURE_BOX'
        self.game.player.is_moving = True
        self.game.handle_keypresses(keydown(K_k))
        self.game.handle_keypresses(keydown(K_i))
        self.game.player.is_moving = False
        for _ in range(40):
            self.frame()
        self.assertEqual([], self.used)
        self.assertTrue(self.game.paused)


class TestEnter(SmartATestCase):

    def test_enter_does_the_command_whatever_the_setting(self):
        for setting in (False, True):
            with self.subTest(smart_a=setting):
                self.used.clear()
                self.game.config['SMART_A'] = setting
                self.game.player.current_tile = 'TREASURE_BOX'
                self.game.handle_enter_key(keydown(K_RETURN))
                self.assertEqual(['take'], self.used)

    def test_enter_opens_nothing_when_nothing_applies(self):
        self.game.handle_enter_key(keydown(K_RETURN))
        self.assertEqual([], self.used)
        self.assertFalse(self.game.cmd_menu.launch_signaled)
        self.assertFalse(self.game.cmd_menu_requested)

    def test_enter_takes_the_stairs_and_opens_doors_with_a_key(self):
        position = (self.game.player.row, self.game.player.column)
        with patch.dict(self.game.current_map.staircases, {position: {'map': 'X'}}):
            self.game.player.current_tile = 'BRICK_STAIR_UP'
            self.game.handle_enter_key(keydown(K_RETURN))
        self.game.player.current_tile = 'BRICK'
        self.door.return_value = (1, 1)
        self.game.player.inventory.append('Magic Key')
        self.game.handle_enter_key(keydown(K_RETURN))
        self.assertEqual(['stairs', 'door'], self.used)


class TestTheOption(SmartATestCase):

    def test_the_row(self):
        row = next(row for row in OPTION_ROWS if row.config_key == 'SMART_A')
        self.assertEqual("SMART A", row.label)
        self.assertEqual(((False, True), ("OFF (NES)", "ON")), (row.values, row.value_labels))

    def test_off_is_the_nes_default_and_it_is_saved(self):
        from src.config.base_config import base_config
        self.assertFalse(base_config['SMART_A'])
        self.assertFalse(DEFAULT_OPTIONS.smart_a)
        self.assertFalse(options_from_save({}).smart_a)
        on = DEFAULT_OPTIONS.__class__(smart_a=True)
        self.assertEqual(on, options_from_save(options_to_save(on)))
