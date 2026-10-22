import json
import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

import pygame

from src.config.test_config import test_config
from src.game import Game, save_slot_number

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


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

    def new_game(self) -> Game:
        with patch('src.game.SCALED'):
            return Game(self.config)

    def write_save(self, slot: int, name: str, experience: int, modified: float) -> None:
        game = self.new_game()
        game.player.name = name
        game.player.total_experience = experience
        game.player.adventure_log = slot
        game.cmd_menu.save()
        path = os.path.join(self.save_dir.name, f'save_slot_{slot}.json')
        os.utime(path, (modified, modified))

    def continue_quest(self) -> Game:
        game = self.new_game()
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

    def test_with_two_saves_the_latest_is_continued_instead_of_a_new_game(self):
        # This used to load nothing, so the hero started a new game in the throne room
        self.write_save(1, 'Eddie', 2, modified=1000)
        self.write_save(0, 'Eddie', 8, modified=2000)
        game = self.continue_quest()
        self.assertEqual(game.player.total_experience, 8)
        self.assertEqual(game.player.adventure_log, 0)

    def test_other_files_in_the_save_folder_are_ignored(self):
        self.write_save(1, 'Eddie', 5, modified=1000)
        for stray in ('.gitkeep', 'notes.txt', 'save_slot_1.json.bak'):
            with open(os.path.join(self.save_dir.name, stray), 'w') as stray_file:
                json.dump({}, stray_file)
        game = self.new_game()
        self.assertEqual(game.save_files(), ['save_slot_1.json'])
        self.assertEqual(self.continue_quest().player.total_experience, 5)

    def test_full_logs_menu_continues_the_quest(self):
        # NES with all three logs used: CONTINUE A QUEST, CHANGE MESSAGE SPEED, ERASE AN ADVENTURE LOG
        for slot in (1, 2, 3):
            self.write_save(slot, 'Eddie', slot, modified=1000 + slot)
        game = self.new_game()
        with patch.object(game.game_functions, 'main_menu_selection', return_value=0), \
                patch.object(game, 'continue_quest') as continue_quest:
            game.show_main_menu_screen(game.screen)
        continue_quest.assert_called_once()

    def test_save_slot_number(self):
        self.assertEqual(save_slot_number('save_slot_3.json'), 3)
        with self.assertRaises(ValueError):
            save_slot_number('notes.txt')
