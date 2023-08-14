from unittest import TestCase

from data.text.dialog_lookup_table import DialogLookup
from src.config import prod_config
from src.maps import TantegelThroneRoom
from src.player.player import Player


class TestDialogLookup(TestCase):
    def setUp(self):
        prod_config['NO_WAIT'] = True
        prod_config['RENDER_TEXT'] = False
        prod_config['NO_BLIT'] = True
        player = Player(None, None, TantegelThroneRoom(), god_mode=prod_config['GOD_MODE'])
        player.name = 'Edward'
        self.dialog_lookup = DialogLookup(None, prod_config)
