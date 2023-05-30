from unittest import TestCase

from data.text.dialog_lookup_table import DialogLookup
from src.config import prod_config
from src.player.player import Player


class TestDialogLookup(TestCase):
    def setUp(self):
        config = prod_config
        config['NO_WAIT'] = True
        player = Player(None, None, None, config)
        player.name = 'Edward'
        self.dialog_lookup = DialogLookup(None, config)
