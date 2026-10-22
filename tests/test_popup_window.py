"""The pop-up status window (name, level, HP, MP, gold, experience) is redrawn when the NES redraws it: Dowindow WND_POPUP
right after a dialog event changes what it shows (Bank03)."""
import os
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame  # noqa: E402
from pygame import Rect  # noqa: E402

from src.color import RED, WHITE  # noqa: E402
from src.config.test_config import test_config  # noqa: E402
from src.drawer import Drawer  # noqa: E402
from src.game import Game  # noqa: E402
from src.maps import Brecconary  # noqa: E402
from src.windows import POPUP_WINDOW  # noqa: E402

INN_COST = 6


class PopupWindowTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        test_config['NO_WAIT'] = True
        test_config['RENDER_TEXT'] = False
        test_config['NO_BLIT'] = True
        self.addCleanup(test_config.__setitem__, 'NO_BLIT', True)
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.game.change_map(Brecconary(self.game.config), destination_coordinates=(29, 18))
        self.cmd_menu = self.game.cmd_menu
        self.dialog_lookup = self.cmd_menu.dialog_lookup
        self.player = self.game.player
        self.player.name = "Edward"
        self.player.max_hp, self.player.current_hp = 15, 2
        self.player.max_mp, self.player.current_mp = 10, 1
        self.player.gold = 100
        self.game.load_window_palette()
        self.cmd_menu.skip_text = True
        # what happened, in order: the pop-up drawn (with what it showed), lines said, fades
        self.events: list[tuple] = []
        real_draw = self.game.drawer.draw_hovering_stats_window

        def draw_popup(screen, player, color=WHITE):
            self.events.append(('popup', player.current_hp, player.current_mp, player.gold, color))
            real_draw(screen, player, color)

        patch.object(self.game.drawer, 'draw_hovering_stats_window', side_effect=draw_popup).start()
        self.addCleanup(patch.stopall)

    def record_lines(self):
        def line(text, *_args, **_kwargs):
            self.events.append(('line', text))

        def text(lines, *_args, **kwargs):
            self.events.append(('text', lines, kwargs.get('drop_down', True)))

        patch.object(self.cmd_menu, 'show_line_in_dialog_box', side_effect=line).start()
        patch.object(self.cmd_menu, 'show_text_in_dialog_box', side_effect=text).start()

    def popups(self):
        return [event[1:] for event in self.events if event[0] == 'popup']


class TestInnStay(PopupWindowTestCase):
    """NES BuyInnStay (LD8C9)."""

    def run_inn_stay(self):
        def fade(fade_out, **_kwargs):
            self.events.append(('fade out' if fade_out else 'fade in',))

        patch('data.text.dialog_lookup_table.fade', side_effect=fade).start()
        self.dialog_lookup.inn_sleep(INN_COST)

    def test_popup_shows_the_paid_gold_then_the_restored_hp_and_mp_before_good_morning(self):
        self.record_lines()
        self.run_inn_stay()
        self.assertEqual(self.events, [
            # gold paid, Dowindow WND_POPUP, "Good night." (still at the old HP: red)
            ('popup', 2, 1, 100 - INN_COST, RED),
            ('line', "Good night."),
            ('fade out',),
            # HP and MP restored, Dowindow WND_POPUP while the screen is black; PalFadeIn shows it, now white
            ('popup', 15, 10, 100 - INN_COST, WHITE),
            ('fade in',),
            # the innkeeper carries on in the dialog window that is still open
            ('text', ("Good morning.\nThou seems to have spent a good night.", "I shall see thee again."), False),
        ])
        self.assertTrue(self.game.drawer.display_hovering_stats)


    def test_fade_in_shows_the_restored_popup_and_the_open_dialog_window(self):
        """Draw the stay for real and look at the screen PalFadeIn starts from: the pop-up must be exactly the white
        pop-up with the full HP and MP, and the dialog window must still hold "Good night."."""
        test_config['NO_BLIT'] = False
        test_config['RENDER_TEXT'] = True
        self.addCleanup(test_config.__setitem__, 'RENDER_TEXT', False)
        screen = self.game.screen
        tile_size = self.game.config['TILE_SIZE']
        left, top, width, height = POPUP_WINDOW
        popup_rect = Rect(left * tile_size, top * tile_size, width * tile_size, height * tile_size)
        self.cmd_menu.show_line_in_dialog_box("Welcome to the traveler's Inn.", skip_text=True)
        seen = {}

        def fade(fade_out, **_kwargs):
            if not fade_out:
                seen['popup'] = pygame.image.tobytes(screen.subsurface(popup_rect), 'RGB')
                seen['dialog'] = [''.join(row).strip() for row in self.cmd_menu.dialog_buffer.rows if ''.join(row).strip()]

        patch('data.text.dialog_lookup_table.fade', side_effect=fade).start()
        self.dialog_lookup.inn_sleep(INN_COST)

        self.assertEqual((self.player.current_hp, self.player.current_mp, self.player.gold), (15, 10, 100 - INN_COST))
        expected = pygame.Surface(screen.get_size())
        Drawer.draw_hovering_stats_window(self.game.drawer, expected, self.player, WHITE)
        self.assertEqual(seen['popup'], pygame.image.tobytes(expected.subsurface(popup_rect), 'RGB'))
        self.assertIn("`Good night.’", seen['dialog'])


class TestOtherPopupRedraws(PopupWindowTestCase):

    def setUp(self):
        super().setUp()
        self.record_lines()
        self.player.current_hp = 15
        self.game.load_window_palette()

    def test_tool_purchase(self):
        # NES PurchaseTool: the thanks, then Dowindow WND_POPUP
        shop = self.dialog_lookup.shop_inventories.brecconary_item_store_inventory
        with patch.object(self.dialog_lookup, 'open_store_inventory', return_value='Herb'), \
                patch('data.text.dialog_lookup_table.confirmation_prompt'):
            self.dialog_lookup.buy_tool(shop)
        self.assertEqual(self.events[1:], [('line', "The Herb?\nThank you very much."), ('popup', 15, 1, 76, WHITE)])

    def test_magic_key_purchase(self):
        # NES BuyKey: Dowindow WND_POPUP, then "Here, take this key."
        with patch('data.text.dialog_lookup_table.confirmation_prompt'):
            self.dialog_lookup.buy_magic_key(53)
        self.assertEqual(self.popups(), [(15, 1, 47, WHITE)])

    def test_fairy_water_purchase(self):
        with patch('data.text.dialog_lookup_table.confirmation_prompt'):
            self.dialog_lookup.buy_fairy_water()
        self.assertEqual(self.popups(), [(15, 1, 62, WHITE)])

    def test_weapon_purchase_in_the_window_color(self):
        # NES CompWeapPurchase: "I thank thee.", then Dowindow WND_POPUP; low HP: red
        self.player.current_hp = 2
        self.game.load_window_palette()
        shop = self.dialog_lookup.shop_inventories.brecconary_weapons_store_inventory
        self.dialog_lookup.complete_transaction('Bamboo Pole', shop, None)
        self.assertEqual(self.events, [('line', "I thank thee."), ('popup', 2, 1, 90, RED)])

    def test_chest_gold(self):
        # NES GainGoldDialog: the message, then Dowindow WND_POPUP
        with patch.object(self.cmd_menu, 'open_chest'):
            self.cmd_menu.take_gold({'item': 'GOLD', 'gold': (120, 0)})
        self.assertEqual(self.events[0][0], 'text')
        # (and the dialog window's drop up keeps drawing it while it closes)
        self.assertEqual(set(self.popups()), {(15, 1, 220, WHITE)})
        self.assertTrue(self.game.drawer.display_hovering_stats)

    def test_herb(self):
        # NES HerbHeal: LoadRegBGPal, then Dowindow WND_POPUP with the new HP, white again
        self.player.current_hp = 2
        self.game.load_window_palette()
        self.player.inventory = ['Herb']
        with patch('src.menu.random.randint', return_value=23):
            self.cmd_menu.herb()
        self.assertEqual(self.popups(), [(15, 1, 100, WHITE)])
