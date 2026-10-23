"""read_save_name: the hero's name an adventure log window shows (src/title_windows.py has the windows)."""
import json
import os
import tempfile
from unittest import TestCase

from src.save_file import read_save_name


def write_save(directory: str, slot: int, contents) -> str:
    save_path = os.path.join(directory, f'save_slot_{slot}.json')
    with open(save_path, 'w') as save_file:
        if isinstance(contents, str):
            save_file.write(contents)
        else:
            json.dump(contents, save_file)
    return save_path


class TestReadSave(TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

    def test_reads_name(self):
        self.assertEqual('ERDRICK', read_save_name(write_save(self.tmp_dir.name, 1, {'Name': 'ERDRICK'})))

    def test_missing_file(self):
        self.assertIsNone(read_save_name(os.path.join(self.tmp_dir.name, 'save_slot_1.json')))

    def test_unreadable_files(self):
        for contents in ('{not json', '', '["a list"]', {'Gold': 5}, {'Name': None}, {'Name': 3}):
            with self.subTest(contents=contents):
                self.assertIsNone(read_save_name(write_save(self.tmp_dir.name, 1, contents)))
