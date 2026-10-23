import os
import unittest
from unittest.mock import MagicMock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from pygame import KEYDOWN, K_RETURN  # noqa: E402
from pygame.event import Event  # noqa: E402

from data.text.dialog import confirmation_prompt  # noqa: E402

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


if __name__ == '__main__':
    unittest.main()
