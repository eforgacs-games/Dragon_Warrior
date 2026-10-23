import unittest
from unittest.mock import MagicMock, patch

import pygame
from pygame import KEYDOWN, K_DOWN, K_ESCAPE, K_RETURN, K_j, K_k, K_n, K_y
from pygame.event import Event

from data.text.dialog import confirmation_prompt
from src.config.test_config import test_config
from src.directories import Directories
from src.sound import Sound, _sound_library, sfx_channel
from src.waiting import game_ticks

CONFIG = {'TILE_SIZE': 32, 'NO_WAIT': True}


def accept():
    return Event(KEYDOWN, key=K_RETURN, unicode='\r')


class TestConfirmationPrompt(unittest.TestCase):

    def prompt(self, events):
        yes, no = MagicMock(), MagicMock()
        command_menu = MagicMock()
        command_menu._ = lambda text: text  # English: the YES/NO window is generated in the NES font
        with patch('src.selection.event.get', side_effect=[events]), \
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



class TestConfirmationSound(unittest.TestCase):
    """NES WindowSequence (Bank01, LAF02 -> DoConfirmSFX LAF19): SFX_CONFIRM starts as the YES/NO window is built, with
    no pause in between. It used to come 300 ms after the window."""

    def setUp(self):
        pygame.mixer.init()
        self.addCleanup(pygame.mixer.stop)
        patcher = patch.dict('src.sound._sound_library', clear=True)  # real sounds, not another test's mocks
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_confirmation_sound_plays_when_the_window_is_drawn(self):
        config = {**test_config, 'SOUND_ENABLED': True, 'NO_WAIT': False}
        directories = Directories(config)
        command_menu = MagicMock()
        command_menu._ = lambda text: text
        sound = command_menu.sound = Sound(config)
        command_menu.directories = directories
        window_drawn_at = []
        sounds_started_at = []
        sound_when_selection_starts = []
        play_sound = sound.play_sound

        def play_and_note_the_time(path):
            sounds_started_at.append(game_ticks())
            play_sound(path)

        def selection_events(*args, **kwargs):
            sound_when_selection_starts.append(sfx_channel().get_sound())
            return [accept()]

        with patch('data.text.dialog.display') as display, patch('data.text.dialog.event'), \
                patch('src.selection.event.get', side_effect=selection_events), \
                patch.object(sound, 'play_sound', side_effect=play_and_note_the_time):
            display.update.side_effect = lambda *args: window_drawn_at.append(game_ticks())
            confirmation_prompt(command_menu, "Dost thou want a room?", MagicMock(), MagicMock(), config,
                                color=(255, 255, 255))
        self.assertIs(sound_when_selection_starts[0], _sound_library[directories.confirmation_sfx])
        # No game time between drawing the window and starting the sound (less than a frame)
        self.assertLess(sounds_started_at[0] - window_drawn_at[0], 1000 / 60)


if __name__ == '__main__':
    unittest.main()
