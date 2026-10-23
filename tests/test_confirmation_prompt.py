import unittest
from unittest.mock import MagicMock, patch

from pygame import KEYDOWN, K_DOWN, K_ESCAPE, K_RETURN, K_j, K_k, K_n, K_y
from pygame.event import Event

from data.text.dialog import confirmation_prompt

CONFIG = {'TILE_SIZE': 32, 'NO_WAIT': True}


def accept():
    return Event(KEYDOWN, key=K_RETURN, unicode='\r')


class TestConfirmationPrompt(unittest.TestCase):

    def prompt(self, events):
        yes, no = MagicMock(), MagicMock()
        command_menu = MagicMock()
        command_menu._ = lambda text: text  # English: the YES/NO window is generated in the NES font
        with patch('data.text.dialog.get', side_effect=[events]), \
                patch('data.text.dialog.display'), patch('data.text.dialog.event'):
            confirmation_prompt(command_menu, "Dost thou want a room?", yes, no, CONFIG, show_arrow=True,
                                color=(255, 255, 255))
        return yes, no

    def test_accept_chooses_yes(self):
        yes, no = self.prompt([accept()])
        yes.assert_called_once()
        no.assert_not_called()

    def test_mashing_accept_only_chooses_once(self):
        # Issue #97: extra accept presses queued in the same batch used to run the chosen option again
        yes, no = self.prompt([accept(), accept(), accept()])
        yes.assert_called_once()
        no.assert_not_called()

    def test_escape_answers_no(self):
        # Escape is B everywhere else (src/common.py reject_keys); it used to do nothing here
        yes, no = self.prompt([Event(KEYDOWN, key=K_ESCAPE, unicode='\x1b')])
        no.assert_called_once()
        yes.assert_not_called()

    def test_b_answers_no(self):
        yes, no = self.prompt([Event(KEYDOWN, key=K_j, unicode='j')])
        no.assert_called_once()
        yes.assert_not_called()

    def test_a_with_caps_lock_answers_yes(self):
        # Matched by key code: with Caps Lock on, K types 'K', which used to be ignored
        yes, no = self.prompt([Event(KEYDOWN, key=K_k, unicode='K')])
        yes.assert_called_once()
        no.assert_not_called()

    def test_a_on_no_answers_no(self):
        yes, no = self.prompt([Event(KEYDOWN, key=K_DOWN, unicode=''), accept()])
        no.assert_called_once()
        yes.assert_not_called()

    def test_y_and_n_shortcuts(self):
        yes, no = self.prompt([Event(KEYDOWN, key=K_n, unicode='n')])
        no.assert_called_once()
        yes.assert_not_called()
        yes, no = self.prompt([Event(KEYDOWN, key=K_DOWN, unicode=''), Event(KEYDOWN, key=K_y, unicode='y')])
        yes.assert_called_once()
        no.assert_not_called()


if __name__ == '__main__':
    unittest.main()
