import json
import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

import pygame

from src.config.test_config import test_config
from src.game import BACK_TO_TITLE_MENU, Game, save_slot_number
from src.options_screen import OptionsScreen
from tests.helpers import new_game


class TestContinueQuest(TestCase):
    """CONTINUE A QUEST must load a save, and saving afterwards must write back to the same adventure log."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()
        pygame.display.set_mode((800, 600))

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        self.save_dir = tempfile.TemporaryDirectory()
        self.config = {**test_config, 'SAVE_DIR': self.save_dir.name}
        self.addCleanup(self.save_dir.cleanup)

    def write_save(self, slot: int, name: str, experience: int, modified: float) -> None:
        game = new_game(self.config)
        game.player.name = name
        game.player.total_experience = experience
        game.player.adventure_log = slot
        game.cmd_menu.save()
        path = os.path.join(self.save_dir.name, f'save_slot_{slot}.json')
        os.utime(path, (modified, modified))

    def continue_quest(self) -> Game:
        game = new_game(self.config)
        game.save_dir_contents = game.save_files()
        with patch.object(game.game_functions, 'main_menu_selection', return_value=0), \
                patch('src.map_manager.screen_fade'), patch.object(game.music_player, 'load_and_play_music'):
            game.continue_quest()
        return game

    def test_one_save_is_loaded_and_saved_back_to_its_log(self):
        self.write_save(2, 'Eddie', 8, modified=1000)
        game = self.continue_quest()
        self.assertEqual((game.player.name, game.player.total_experience), ('Eddie', 8))
        self.assertEqual(game.player.adventure_log, 2)
        game.cmd_menu.save()
        self.assertEqual(game.save_files(), ['save_slot_2.json'])

    def test_with_two_saves_the_chosen_log_is_continued(self):
        # This used to continue the most recently saved log, so CHANGE MESSAGE SPEED (which saves the log it changes)
        # changed which log CONTINUE A QUEST loaded
        self.write_save(1, 'Eddie', 2, modified=1000)
        self.write_save(3, 'Loto', 8, modified=2000)
        with patch.object(OptionsScreen, 'choose_log', return_value=1) as choose_log:
            game = self.continue_quest()
        self.assertEqual([(1, 'Eddie'), (3, 'Loto')], choose_log.call_args.args[0])
        self.assertEqual((game.player.name, game.player.total_experience), ('Eddie', 2))
        self.assertEqual(game.player.adventure_log, 1)

    def test_b_in_the_log_window_goes_back_to_the_title_menu(self):
        self.write_save(1, 'Eddie', 2, modified=1000)
        self.write_save(2, 'Loto', 8, modified=2000)
        game = new_game(self.config)
        game.save_dir_contents = game.save_files()
        with patch.object(OptionsScreen, 'choose_log', return_value=None), \
                patch.object(game, 'load_game') as load_game, patch.object(game, 'start_at_throne_room') as start:
            self.assertIs(game.continue_quest(), BACK_TO_TITLE_MENU)
        load_game.assert_not_called()
        start.assert_not_called()

    def test_other_files_in_the_save_folder_are_ignored(self):
        self.write_save(1, 'Eddie', 5, modified=1000)
        for stray in ('.gitkeep', 'notes.txt', 'save_slot_1.json.bak'):
            with open(os.path.join(self.save_dir.name, stray), 'w') as stray_file:
                json.dump({}, stray_file)
        game = new_game(self.config)
        self.assertEqual(game.save_files(), ['save_slot_1.json'])
        self.assertEqual(self.continue_quest().player.total_experience, 5)

    def test_full_logs_menu_continues_the_quest(self):
        # NES with all three logs used: CONTINUE A QUEST, CHANGE MESSAGE SPEED, ERASE AN ADVENTURE LOG
        for slot in (1, 2, 3):
            self.write_save(slot, 'Eddie', slot, modified=1000 + slot)
        game = new_game(self.config)
        with patch.object(game.game_functions, 'main_menu_selection', return_value=0), \
                patch.object(game, 'continue_quest') as continue_quest:
            game.show_main_menu_screen(game.screen)
        continue_quest.assert_called_once()

    def title_menu_then_continue(self, selections: list[int]) -> Game:
        """Runs the title menu with these main_menu_selection choices; it must come back to the title menu for the
        last one, CONTINUE A QUEST."""
        game = new_game(self.config)
        with patch.object(game.game_functions, 'main_menu_selection', side_effect=selections), \
                patch.object(game, 'continue_quest') as continue_quest:
            game.show_main_menu_screen(game.screen)
        continue_quest.assert_called_once()
        return game

    def test_erase_goes_back_to_the_title_menu(self):
        # ERASE used to go on into a game with no log, whose save then wrote a fourth save file
        self.write_save(1, 'Eddie', 2, modified=1000)
        self.write_save(2, 'Loto', 8, modified=2000)
        # ERASE AN ADVENTURE LOG, log 1, then CONTINUE A QUEST
        game = self.title_menu_then_continue([4, 0, 0])
        self.assertEqual(game.save_files(), ['save_slot_2.json'])

    def test_copy_goes_back_to_the_title_menu(self):
        self.write_save(1, 'Eddie', 2, modified=1000)
        # COPY A QUEST, from log 1, to log 2, then CONTINUE A QUEST
        game = self.title_menu_then_continue([3, 0, 1, 0])
        self.assertEqual(game.save_files(), ['save_slot_1.json', 'save_slot_2.json'])

    def saved_logs(self) -> dict[str, tuple[str, int] | None]:
        """Each file in the save folder: its hero's name and experience, or None if it isn't a readable save."""
        logs: dict[str, tuple[str, int] | None] = {}
        for file_name in sorted(os.listdir(self.save_dir.name)):
            try:
                with open(os.path.join(self.save_dir.name, file_name)) as save_file:
                    save = json.load(save_file)
                logs[file_name] = (save['Name'], save['Experience'])
            except ValueError:
                logs[file_name] = None
        return logs

    def save_with_no_log(self, name: str, experience: int = 99) -> Game:
        """Saves a game whose title menu was skipped, so no adventure log was chosen."""
        game = new_game(self.config)
        self.assertEqual(game.player.adventure_log, 0)
        game.player.name = name
        game.player.total_experience = experience
        game.cmd_menu.save()
        return game

    def test_a_game_with_no_log_saves_to_the_log_with_its_heros_name(self):
        self.write_save(1, 'Eddie', 2, modified=1000)
        self.write_save(2, 'Loto', 8, modified=2000)
        game = self.save_with_no_log('Loto')
        self.assertEqual(game.player.adventure_log, 2)
        self.assertEqual({'save_slot_1.json': ('Eddie', 2), 'save_slot_2.json': ('Loto', 99)}, self.saved_logs())

    def test_the_log_with_its_heros_name_is_used_even_when_every_log_is_used(self):
        for slot, name in ((1, 'Eddie'), (2, 'Loto'), (3, 'Gwen')):
            self.write_save(slot, name, slot, modified=1000 + slot)
        game = self.save_with_no_log('Gwen')
        self.assertEqual(game.player.adventure_log, 3)
        self.assertEqual({'save_slot_1.json': ('Eddie', 1), 'save_slot_2.json': ('Loto', 2),
                          'save_slot_3.json': ('Gwen', 99)}, self.saved_logs())

    def test_a_game_with_no_log_and_a_new_name_saves_to_an_open_log(self):
        # It used to write save_slot_0.json, which the title menu counted as a log
        self.write_save(1, 'Eddie', 2, modified=1000)
        game = self.save_with_no_log('Loto')
        self.assertEqual(game.player.adventure_log, 2)
        # and saving again goes to the same log
        game.player.total_experience = 100
        game.cmd_menu.save()
        self.assertEqual({'save_slot_1.json': ('Eddie', 2), 'save_slot_2.json': ('Loto', 100)}, self.saved_logs())

    def test_a_game_with_no_log_and_a_new_name_saves_nothing_when_every_log_is_used(self):
        for slot in (1, 2, 3):
            self.write_save(slot, 'Eddie', slot, modified=1000 + slot)
        game = self.save_with_no_log('Loto')
        self.assertEqual(game.player.adventure_log, 0)
        self.assertEqual({'save_slot_1.json': ('Eddie', 1), 'save_slot_2.json': ('Eddie', 2),
                          'save_slot_3.json': ('Eddie', 3)}, self.saved_logs())

    def test_a_game_with_no_log_saves_nothing_when_several_logs_have_its_heros_name(self):
        self.write_save(1, 'Loto', 2, modified=1000)
        self.write_save(2, 'Loto', 8, modified=2000)
        game = self.save_with_no_log('Loto')
        self.assertEqual(game.player.adventure_log, 0)
        self.assertEqual({'save_slot_1.json': ('Loto', 2), 'save_slot_2.json': ('Loto', 8)}, self.saved_logs())

    def test_an_unreadable_log_is_never_overwritten(self):
        with open(os.path.join(self.save_dir.name, 'save_slot_1.json'), 'w') as save_file:
            save_file.write('{not json')
        self.write_save(2, 'Eddie', 2, modified=1000)
        self.write_save(3, 'Gwen', 3, modified=2000)
        game = self.save_with_no_log('Loto')
        self.assertEqual(game.player.adventure_log, 0)
        self.assertEqual({'save_slot_1.json': None, 'save_slot_2.json': ('Eddie', 2),
                          'save_slot_3.json': ('Gwen', 3)}, self.saved_logs())

    def test_files_that_arent_one_of_the_three_logs_are_ignored(self):
        # A save_slot_0.json made before used to make a fourth log, and the title menu then exited
        for slot in (0, 1, 2, 3, 4):
            with open(os.path.join(self.save_dir.name, f'save_slot_{slot}.json'), 'w') as save_file:
                json.dump({'Name': 'Eddie'}, save_file)
        self.assertEqual(new_game(self.config).save_files(), ['save_slot_1.json', 'save_slot_2.json', 'save_slot_3.json'])

    def test_save_slot_number(self):
        self.assertEqual(save_slot_number('save_slot_3.json'), 3)
        with self.assertRaises(ValueError):
            save_slot_number('notes.txt')
