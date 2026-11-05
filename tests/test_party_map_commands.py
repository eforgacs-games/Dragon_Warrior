"""A party's ITEM and SPELL on the map (src/menu.py, src/party.py): the player chooses the hero; the cost is theirs,
and a spell or item that acts for the party works as the first hero's, where the party stands."""
from unittest.mock import patch

from src.items import inventory_list
from src.party import new_hero
from src.spells import Spell
from tests.test_shop_dialog import ShopDialogTestCase


class MapCommandTestCase(ShopDialogTestCase):

    def setUp(self):
        super().setUp()
        self.addCleanup(patch.stopall)
        self.cmd_menu = self.game.cmd_menu
        self.leader = self.player
        self.leader.name = 'Ann'
        self.companion = self.game.companion = new_hero(self.game, 'Gwen')
        patch.object(self.cmd_menu, 'show_text_in_dialog_box').start()
        patch.object(self.game, 'unlaunch_menu').start()
        self.choose = patch.object(self.cmd_menu.dialog_lookup, 'choose_hero', return_value=self.companion).start()

    def use(self, name, menu='inventory', effect=None):
        """Choose ``name`` in the menu, its effect recording who it acts as and what the first hero holds then."""
        seen = []

        def record(*args):
            seen.append((self.game.player.name, list(self.leader.inventory)))
            if effect is not None:
                effect()
        with patch('src.menu.run_selection') as selection, patch.object(self.cmd_menu, 'draw_item_menu'), \
                patch.object(self.cmd_menu, 'remove_window'), patch.object(self.cmd_menu, 'draw_window_cursor'), \
                patch.object(self.cmd_menu, 'show_popup_window'), patch('src.menu.bw_screen_flash'), \
                patch.object(self.cmd_menu, 'wait_for_button'), patch.object(self.cmd_menu.sound, 'play_sound'), \
                patch.object(self.cmd_menu.sound, 'wait_for_sfx_end'), \
                patch.object(type(self.cmd_menu), self.method(name), side_effect=record):
            hero = self.choose.return_value if self.game.companion is not None else self.leader
            entries = list(hero.spells) if menu == 'spells' else None
            entries = entries if entries is not None else inventory_list(hero.inventory)
            selection.return_value.entry = entries.index(name)
            selection.return_value.accepted = True
            (self.cmd_menu.spell if menu == 'spells' else self.cmd_menu.item)()
        return seen

    @staticmethod
    def method(name):
        return {'Wings': 'wings', 'Herb': 'herb', 'Torch': 'torch', Spell.RETURN: 'return_', Spell.HEAL: 'heal',
                'Silver Harp': 'silver_harp'}[name]


class TestItems(MapCommandTestCase):

    def test_the_chosen_hero_uses_their_own(self):
        self.companion.inventory = ['Herb']
        self.assertEqual([('Gwen', [])], self.use('Herb'))
        self.assertIs(self.leader, self.game.player)

    def test_a_party_item_works_as_the_first_hero_with_the_second_ones_item(self):
        self.companion.inventory = ['Wings']
        self.leader.inventory = []
        seen = self.use('Wings', effect=lambda: self.leader.inventory.remove('Wings'))
        self.assertEqual([('Ann', ['Wings'])], seen)  # lent to the first hero for the effect
        self.assertEqual(([], []), (list(self.leader.inventory), list(self.companion.inventory)))  # used up

    def test_an_item_not_used_up_goes_back(self):
        self.companion.inventory = ['Silver Harp']
        self.use('Silver Harp')
        self.assertEqual((['Silver Harp'], []), (list(self.companion.inventory), list(self.leader.inventory)))

    def test_b_chooses_no_one(self):
        self.choose.return_value = None
        with patch.object(self.cmd_menu, 'display_item_menu') as menu:
            self.cmd_menu.item()
        menu.assert_not_called()
        self.game.unlaunch_menu.assert_called_once()

    def test_the_first_hero_as_ever(self):
        self.choose.return_value = self.leader
        self.leader.inventory = ['Wings']
        self.assertEqual([('Ann', ['Wings'])], self.use('Wings'))

    def test_no_choice_for_one_hero(self):
        self.game.companion = None
        self.leader.inventory = ['Herb']
        self.use('Herb')
        self.choose.assert_not_called()


class TestSpells(MapCommandTestCase):

    def setUp(self):
        super().setUp()
        self.companion.spells = [Spell.HEAL, Spell.RETURN]
        self.companion.current_mp = 20
        self.leader.current_mp = 0

    def test_heal_heals_the_caster(self):
        self.assertEqual('Gwen', self.use(Spell.HEAL, 'spells')[0][0])
        self.assertEqual(16, self.companion.current_mp)

    def test_return_moves_the_party_with_the_casters_mp(self):
        self.assertEqual('Ann', self.use(Spell.RETURN, 'spells')[0][0])
        self.assertEqual((12, 0), (self.companion.current_mp, self.leader.current_mp))
