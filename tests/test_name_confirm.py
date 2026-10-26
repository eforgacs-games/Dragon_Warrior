"""CONFIRM NAME (not NES): a full name waits on END instead of ending at the 8th character, and START ends the name
(src/name_entry.py NameEntry, src/menu_functions.py NameSelection.select_name)."""
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pygame
from pygame import K_BACKSPACE, K_RETURN, K_TAB, K_i, K_k

from src.config.test_config import test_config
from src.controls import Binding, Controls, reset_controls, set_controls
from src.menu_functions import NameSelection
from src.name_entry import END, NAME_LENGTH, NameEntry
from src.options_overlay import OPTION_PAGES
from src.settings import Settings
from tests.test_name_entry import key_event


class TestConfirmEntry(TestCase):

    def full_entry(self) -> NameEntry:
        entry = NameEntry(confirm=True)
        for character in 'Lorikeet':
            entry.move_to(character)
            entry.enter(character)
        return entry

    def test_a_full_name_waits_on_end(self):
        entry = self.full_entry()
        self.assertFalse(entry.finished)
        self.assertEqual((NAME_LENGTH, END), (entry.index, entry.selection))
        self.assertEqual('Lorikeet', entry.name)

    def test_a_full_name_can_still_be_changed(self):
        entry = self.full_entry()
        entry.back()
        entry.move_to('h')
        entry.enter('h')
        self.assertFalse(entry.finished)
        self.assertEqual(('Lorikeeh', END), (entry.name, entry.selection))

    def test_more_characters_are_ignored_once_full(self):
        entry = self.full_entry()
        entry.move_to('A')
        entry.enter('A')
        self.assertEqual('Lorikeet', entry.name)

    def test_end_ends_it(self):
        entry = self.full_entry()
        entry.select()  # A on END, where the cursor went
        self.assertTrue(entry.finished)
        self.assertEqual('Lorikeet', entry.name)

    def test_nes_rule_without_confirm(self):
        # WndMaxNameLength: the 8th character ends the name
        entry = NameEntry()
        for character in 'Lorikeet':
            entry.enter(character)
        self.assertTrue(entry.finished)


class TestConfirmSelectName(TestCase):

    def setUp(self):
        self.config = dict(test_config, NO_BLIT=True, NAME_CONFIRM=True)
        self.command_menu = MagicMock()
        self.command_menu.game.game_state.config = self.config
        self.screen = pygame.Surface((256, 240))

    def select_name(self, events: list, joystick: bool = False) -> str | None:
        with patch('src.selection.event.get', side_effect=[[current_event] for current_event in events]), \
                patch('src.menu_functions.display'), patch('src.menu_functions.Sound'), \
                patch('src.menu_functions.toggle_joystick_input', return_value=joystick):
            return NameSelection(self.config).select_name(0, self.screen, self.command_menu)

    def test_typing_8_characters_waits_for_return(self):
        events = [key_event(0, character) for character in 'Lorikeet']
        events += [key_event(K_BACKSPACE), key_event(pygame.K_h, 'h'), key_event(K_RETURN)]
        self.assertEqual('Lorikeeh', self.select_name(events))

    def test_start_ends_the_name_with_joystick_input(self):
        # Tab, A on A, START
        self.assertEqual('A', self.select_name([key_event(K_TAB), key_event(K_k), key_event(K_i)], joystick=True))

    def test_start_needs_a_name(self):
        # START with nothing entered does nothing; then A on A, START
        events = [key_event(K_TAB), key_event(K_i), key_event(K_k), key_event(K_i)]
        self.assertEqual('A', self.select_name(events, joystick=True))

    def test_tab_only_switches_to_the_joypad_whatever_it_is_bound_to(self):
        # A on K and Tab (an old settings file: the CONTROLS screen refuses Tab for A now)
        controls = Controls.defaults()
        controls.keys['A'] = [Binding(K_k), Binding(K_TAB)]
        set_controls(controls)
        self.addCleanup(reset_controls)
        self.assertEqual('A', self.select_name([key_event(K_TAB), key_event(K_k), key_event(K_i)], joystick=True))

    def test_a_after_the_8th_character_chooses_end(self):
        # Tab, A on A eight times: the cursor goes to END, so the next A ends the name
        events = [key_event(K_TAB)] + [key_event(K_k)] * NAME_LENGTH + [key_event(K_k)]
        self.assertEqual('A' * NAME_LENGTH, self.select_name(events, joystick=True))


class TestConfirmSetting(TestCase):

    def test_on_by_default_and_saved_globally(self):
        self.assertTrue(Settings().name_confirm)
        self.assertTrue(Settings.from_json({}).name_confirm)
        self.assertFalse(Settings.from_json({'name_confirm': False}).name_confirm)
        self.assertTrue(Settings.from_json({'name_confirm': 'maybe'}).name_confirm)
        self.assertFalse(Settings.from_json(Settings(name_confirm=False).to_json()).name_confirm)

    def test_options_row_on_other_off_in_the_nes_preset(self):
        other = next(page for page in OPTION_PAGES if page.title == 'OTHER')
        row = next(row for row in other.rows if getattr(row, 'config_key', None) == 'NAME_CONFIRM')
        self.assertEqual('CONFIRM NAME', row.label)
        self.assertEqual((False, True), row.presets)
