"""atomic_write_json (src/json_files.py): the adventure logs, save states, autosave and settings are written in one
step, so a crash or a full disk part way through never leaves one half written."""
import json
import os
import tempfile
from unittest import TestCase
from unittest.mock import patch

from src.json_files import atomic_write_json


class TestAtomicWriteJson(TestCase):

    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.folder = temp_dir.name
        self.path = os.path.join(self.folder, 'saves', 'save_slot_1.json')

    def read(self) -> str:
        with open(self.path, encoding='utf-8') as json_file:
            return json_file.read()

    def test_writes_the_json_and_makes_the_folder(self):
        atomic_write_json(self.path, {'Name': 'Erdrick'}, indent=4)
        self.assertEqual('{\n    "Name": "Erdrick"\n}', self.read())
        atomic_write_json(self.path, {'zoom': 2}, trailing_newline=True)
        self.assertEqual('{"zoom": 2}\n', self.read())
        self.assertEqual(['save_slot_1.json'], os.listdir(os.path.dirname(self.path)))

    def test_a_failure_part_way_leaves_the_old_file_whole(self):
        atomic_write_json(self.path, {'Name': 'Erdrick'})
        for failing in ('src.json_files.os.replace', 'src.json_files.os.fsync'):
            with self.subTest(failing), patch(failing, side_effect=OSError("No space left on device")):
                with self.assertRaises(OSError):
                    atomic_write_json(self.path, {'Name': 'Loto'})
                self.assertEqual({'Name': 'Erdrick'}, json.loads(self.read()))
                self.assertEqual(['save_slot_1.json'], os.listdir(os.path.dirname(self.path)))

    def test_a_value_that_isnt_json_leaves_the_old_file_whole(self):
        atomic_write_json(self.path, {'Name': 'Erdrick'})
        with self.assertRaises(TypeError):
            atomic_write_json(self.path, {'Name': object()})
        self.assertEqual({'Name': 'Erdrick'}, json.loads(self.read()))
