from unittest import TestCase

from data.text.dialog_lookup_table import DialogLookup
from src.player.player import Player


class TestDialogLookup(TestCase):
    def setUp(self):
        player = Player(None, None, None)
        player.name = 'Edward'
        self.dialog_lookup = DialogLookup(player)
