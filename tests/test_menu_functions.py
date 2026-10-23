from unittest import TestCase
from unittest.mock import patch, MagicMock

from pygame import KEYDOWN, K_RETURN, QUIT, event, K_e, K_d
from pygame.time import get_ticks

from src.config.test_config import test_config
from src.game import Game
from src.menu_functions import NameSelection, get_opposite_direction, toggle_joystick_input


class TestMenuFunctions(TestCase):
    def setUp(self) -> None:
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        with patch('src.game.SCALED'):
            self.game = Game(test_config)

    def test_select_name(self):
        # mocked_k = MagicMock()
        # mocked_k.type = KEYDOWN
        # mocked_k.key = K_k
        #
        mocked_e = MagicMock()
        mocked_e.type = KEYDOWN
        mocked_e.key = K_e
        mocked_e.unicode = 'e'

        mocked_d = MagicMock()
        mocked_d.type = KEYDOWN
        mocked_d.key = K_d
        mocked_d.unicode = 'd'

        mocked_return = MagicMock()
        mocked_return.type = KEYDOWN
        mocked_return.key = K_RETURN
        with patch.object(event, 'get', return_value=[mocked_e, mocked_d, mocked_return]):
            self.assertEqual('ed', NameSelection(self.game.game_state.config).select_name(get_ticks(), self.game.screen,
                                                                                          self.game.cmd_menu))

    def test_closing_the_window_during_name_entry_quits_the_game(self):
        # It used to call pygame.quit() and carry on, so the next draw raised "video system not initialized"
        with patch.object(event, 'get', side_effect=[[event.Event(QUIT)]]), \
                patch.object(self.game.cmd_menu, 'show_line_in_dialog_box'), \
                patch('src.waiting.pygame_quit') as pygame_quit, self.assertRaises(SystemExit):
            NameSelection(self.game.game_state.config).select_name(get_ticks(), self.game.screen, self.game.cmd_menu)
        pygame_quit.assert_called_once()

    def test_get_opposite_direction(self):
        self.assertEqual(0, get_opposite_direction(2))
        self.assertEqual(1, get_opposite_direction(3))
        self.assertEqual(2, get_opposite_direction(0))
        self.assertEqual(3, get_opposite_direction(1))

    @patch('src.menu.CommandMenu.show_text_in_dialog_box')
    def test_toggle_joystick_input(self, mock_show_text_in_dialog_box):
        self.assertEqual(True,
                         toggle_joystick_input(self.game.cmd_menu, MagicMock(), False,
                                               self.game.screen))
        self.assertEqual(False,
                         toggle_joystick_input(self.game.cmd_menu, MagicMock(), True,
                                               self.game.screen))
