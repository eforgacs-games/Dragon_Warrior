"""A party in the world (src/party.py): the party's gold, the inns, the shops, the chests and STATUS."""
from unittest.mock import patch

from pygame import KEYDOWN, K_k
from pygame.event import Event

from src.party import acting, new_hero
from tests.test_shop_dialog import ShopDialogTestCase


class PartyTestCase(ShopDialogTestCase):

    def setUp(self):
        super().setUp()
        self.player.name = 'Ann'
        self.companion = self.game.companion = new_hero(self.game, 'Gwen')
        self.companion.inventory = []


class TestTheGold(PartyTestCase):

    def test_the_partys(self):
        with acting(self.game, self.companion):
            self.assertEqual(1000, self.game.player.gold)
            self.game.player.gold -= 300
        self.assertEqual(700, self.player.gold)


class TestTheInn(PartyTestCase):

    def test_each_hero_pays(self):
        self.answers = [True]
        with patch.object(self.dialog_lookup, 'inn_sleep') as inn_sleep:
            self.dialog_lookup.check_stay_at_inn(6)
        inn_sleep.assert_called_once_with(12)
        self.assertIn('12', self.prompts[0])

    def test_one_hero_pays_the_nes_price(self):
        self.game.companion = None
        self.answers = [True]
        with patch.object(self.dialog_lookup, 'inn_sleep') as inn_sleep:
            self.dialog_lookup.check_stay_at_inn(6)
        inn_sleep.assert_called_once_with(6)

    def test_both_rest(self):
        for hero in (self.player, self.companion):
            hero.current_hp = hero.current_mp = 1
        self.dialog_lookup.command_menu.show_line_in_dialog_box = lambda *args, **kwargs: None
        with patch('data.text.dialog_lookup_table.screen_fade'), \
                patch.object(self.game.music_player, 'play_until_end'), \
                patch.object(self.game.music_player, 'load_and_play_music'), \
                patch.object(self.dialog_lookup.command_menu, 'show_popup_window'):
            self.dialog_lookup.inn_sleep(12)
        self.assertEqual((self.player.max_hp, self.companion.max_hp),
                         (self.player.current_hp, self.companion.current_hp))
        self.assertEqual(988, self.player.gold)


class TestTheShops(PartyTestCase):

    def test_the_chosen_hero_shops(self):
        shoppers = []
        with patch.object(self.dialog_lookup, 'choose_hero', return_value=self.companion), \
                patch.object(self.dialog_lookup, 'confirm',
                             side_effect=lambda *args, **kwargs: shoppers.append(self.game.player.name)):
            self.dialog_lookup.check_buy_weapons_armor(self.store('brecconary_weapons_store_inventory'))
        self.assertEqual(['Gwen'], shoppers)
        self.assertIs(self.player, self.game.player)

    def test_a_weapon_bought_for_the_second_hero(self):
        self.answers = [True, True, False]
        with patch.object(self.dialog_lookup, 'choose_hero', return_value=self.companion), \
                patch.object(self.dialog_lookup, 'open_store_inventory', side_effect=['Club']):
            self.dialog_lookup.check_buy_weapons_armor(self.store('brecconary_weapons_store_inventory'))
        self.assertEqual(('Club', ''), (self.companion.weapon, self.player.weapon))
        self.assertEqual(1000 - 60, self.player.gold)  # paid from the party's gold

    def test_b_leaves(self):
        with patch.object(self.dialog_lookup, 'choose_hero', return_value=None), \
                patch.object(self.dialog_lookup, 'confirm') as confirm:
            self.dialog_lookup.fairy_water_shop()
        confirm.assert_not_called()

    def test_no_choice_for_one_hero(self):
        self.game.companion = None
        with patch.object(self.dialog_lookup, 'choose_hero') as choose_hero, \
                patch.object(self.dialog_lookup, 'confirm'):
            self.dialog_lookup.check_buy_magic_keys(53)
        choose_hero.assert_not_called()

    def test_asked_once_while_shopping(self):
        with patch.object(self.dialog_lookup, 'choose_hero', return_value=self.companion) as choose_hero, \
                patch.object(self.dialog_lookup, 'say'), \
                patch.object(self.dialog_lookup, 'select_in_generated_window', side_effect=[1, None]), \
                patch.object(self.dialog_lookup, 'sell_tool',
                             side_effect=lambda inventory: self.dialog_lookup.tool_shop(inventory)):
            self.dialog_lookup.tool_shop(self.store('brecconary_item_store_inventory'))
        choose_hero.assert_called_once()

    def test_choosing_by_name(self):
        with patch.object(self.dialog_lookup, 'select_from_text_menu', return_value=1) as menu:
            self.assertIs(self.companion, self.dialog_lookup.choose_hero())
        self.assertEqual(['Ann', 'Gwen'], menu.call_args.args[0])
        self.assertEqual("Who will it be?", self.lines[-1])


class TestTheChests(PartyTestCase):

    def setUp(self):
        super().setUp()
        cmd_menu = self.game.cmd_menu
        patch.object(cmd_menu, 'open_chest').start()
        self.texts = []
        patch.object(cmd_menu, 'show_text_in_dialog_box',
                     side_effect=lambda text, **kwargs: self.texts.append(text)).start()
        self.addCleanup(patch.stopall)

    def test_the_first_hero_with_room(self):
        self.game.cmd_menu.take_item('Torch')
        self.assertEqual((['Torch'], []), (list(self.player.inventory), list(self.companion.inventory)))
        self.player.inventory = ['Wings'] * 8
        self.game.cmd_menu.take_item('Torch')
        self.assertEqual(['Torch'], list(self.companion.inventory))
        self.assertIn('Gwen', self.texts[-1])

    def test_both_full(self):
        self.player.inventory = ['Wings'] * 8
        self.companion.inventory = ['Wings'] * 8
        with patch.object(self.game.cmd_menu, 'discard_for_item') as discard:
            self.game.cmd_menu.take_item('Torch')
        discard.assert_called_once_with('Torch')

    def test_herbs(self):
        self.player.inventory = ['Herb'] * 6
        self.game.cmd_menu.take_counted_item('Herb', 6)
        self.assertEqual(['Herb'], list(self.companion.inventory))
        self.companion.inventory = ['Herb'] * 6
        with patch.object(self.game.cmd_menu, 'take_empty_chest') as empty:
            self.game.cmd_menu.take_counted_item('Herb', 6)
        empty.assert_called_once()


class TestStatus(PartyTestCase):

    def test_each_hero_in_turn(self):
        cmd_menu = self.game.cmd_menu
        shown = []
        with patch.object(cmd_menu, 'draw_status_window',
                          side_effect=lambda: shown.append(self.game.player.name) or cmd_menu.screen.get_rect()), \
                patch.object(cmd_menu, 'window_drop_up_effect'), \
                patch('src.menu.next_game_frame'), \
                patch('src.menu.frame_events', return_value=[Event(KEYDOWN, key=K_k, mod=0)]):
            cmd_menu.status()
        self.assertEqual(['Ann', 'Gwen'], shown)
        self.assertIs(self.player, self.game.player)
