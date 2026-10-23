"""The shop stat preview (src/shop_preview.py, SHOP PREVIEW in the options overlay): the attack or defense power the
highlighted item in a weapon and armor shop's list would give, in a window of its own beside the NES shop windows."""
import os
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
from pygame import KEYDOWN, K_DOWN, K_ESCAPE, K_UP, Rect
from pygame.event import Event

from src.common import set_gettext_language
from src.config.test_config import test_config
from src.directories import Directories
from src.shop_preview import ARROW, ATTACK_LABEL, DEFENSE_LABEL, SHOP_PREVIEW_WINDOW, StatPreview, \
    draw_shop_preview, preview_layout, stat_preview
from src.shops import ShopInventories
from src.text import set_font_by_ascii_chars
from src.window_renderer import window_tiles
from src.windows import COMMAND_WINDOW, DIALOG_WINDOW, POPUP_WINDOW, SHOP_INVENTORY_WINDOW, Window, \
    variable_height_window
from tests import helpers

# Frames with nothing pressed after each press, like tests/test_options_overlay.py
GAP = 2


def presses(*keys):
    """event.get's results for a selection window's loop, which reads it once a frame."""
    results = []
    for pressed_key in keys:
        results += [[]] * GAP + [[Event(KEYDOWN, key=pressed_key, mod=0)]]
    return results


def new_game(**overrides):
    # A copy of test_config, so the settings these tests change don't leak into other tests
    return helpers.new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True,
                             'SHOP_PREVIEW': True, **overrides})


def all_shops(config) -> dict[str, dict]:
    return {name: inventory for name, inventory in vars(ShopInventories(config)).items() if name.endswith('inventory')}


def weapon_and_armor_shops(config) -> dict[str, dict]:
    return {name: inventory for name, inventory in all_shops(config).items()
            if all(item['type'] != 'tool' for item in inventory.values())}


def overlaps(first: Window, second: Window) -> bool:
    return Rect(first.x, first.y, first.width, first.height).colliderect(
        Rect(second.x, second.y, second.width, second.height))


class PreviewTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.mixer.init()

    def setUp(self):
        self.game = self.make_game()
        self.config = self.game.game_state.config
        self.player = self.game.player
        self.dialog_lookup = self.game.cmd_menu.dialog_lookup
        clock = [0]

        def next_frame(frames=1, *_args, **_kwargs):
            clock[0] += round(frames * 1000 / 60)
        patch('src.cursor.get_ticks', lambda: clock[0]).start()
        patch('src.selection.wait_frames', side_effect=next_frame).start()
        patch.object(self.game.cmd_menu, 'window_drop_down_effect').start()
        patch('data.text.dialog_lookup_table.display').start()
        self.addCleanup(patch.stopall)

    def make_game(self):
        return new_game()

    def hero(self, strength=4, agility=4, weapon='', armor='', shield='', dragon_scale=False, cursed=False):
        player = self.player
        player.strength, player.agility = strength, agility
        player.weapon, player.armor, player.shield = weapon, armor, shield
        player.wearing_dragon_scale = dragon_scale
        player.wearing_cursed_belt = cursed
        player.update_attack_power()
        player.update_defense_power()
        return player


class TestNumbers(PreviewTestCase):

    def test_weapons(self):
        # NES: attack power = strength + the weapon's attack bonus (Club 4, Copper Sword 10, Flame Sword 28)
        cases = ((dict(strength=4), 'Club', (4, 8)),
                 (dict(strength=4), 'Copper Sword', (4, 14)),
                 (dict(strength=35, weapon='Copper Sword'), 'Hand Axe', (45, 50)),
                 (dict(strength=35, weapon='Copper Sword'), 'Bamboo Pole', (45, 37)),
                 (dict(strength=140, weapon='Broad Sword'), 'Flame Sword', (160, 168)))
        for hero, item, (now, with_item) in cases:
            with self.subTest(hero=hero, item=item):
                self.assertEqual(StatPreview(ATTACK_LABEL, now, with_item),
                                 stat_preview(self.hero(**hero), item, 'weapon'))

    def test_armor_and_shields(self):
        # NES: defense power = agility / 2 (rounded down) + the armor's and the shield's defense bonuses
        cases = ((dict(agility=5), 'Clothes', 'armor', (2, 4)),
                 (dict(agility=5, shield='Small Shield'), 'Leather Armor', 'armor', (6, 10)),
                 (dict(agility=20, armor='Chain Mail'), 'Large Shield', 'shield', (20, 30)),
                 (dict(agility=20, armor='Chain Mail', shield='Large Shield'), 'Small Shield', 'shield', (30, 24)),
                 (dict(agility=130, armor='Full Plate', shield='Large Shield'), 'Magic Armor', 'armor', (99, 99)),
                 (dict(agility=130, armor='Magic Armor', shield='Large Shield'), 'Silver Shield', 'shield',
                  (99, 109)))
        for hero, item, item_type, (now, with_item) in cases:
            with self.subTest(hero=hero, item=item):
                self.assertEqual(StatPreview(DEFENSE_LABEL, now, with_item),
                                 stat_preview(self.hero(**hero), item, item_type))

    def test_the_equipped_item_changes_nothing(self):
        for hero, item, item_type in ((dict(strength=20, weapon='Club'), 'Club', 'weapon'),
                                      (dict(agility=9, armor='Half Plate'), 'Half Plate', 'armor'),
                                      (dict(agility=9, shield='Small Shield'), 'Small Shield', 'shield')):
            with self.subTest(item=item):
                preview = stat_preview(self.hero(**hero), item, item_type)
                self.assertIsNotNone(preview)
                assert preview is not None
                self.assertEqual(preview.now, preview.with_item)

    def test_now_is_what_the_status_window_shows(self):
        player = self.hero(strength=17, agility=11, weapon='Club', armor='Clothes', shield='Small Shield',
                           dragon_scale=True)
        self.assertEqual(player.attack_power, stat_preview(player, 'Hand Axe', 'weapon').now)
        self.assertEqual(player.defense_power, stat_preview(player, 'Chain Mail', 'armor').now)
        self.assertEqual(player.defense_power, stat_preview(player, 'Large Shield', 'shield').now)

    def test_the_dragons_scale_counts_on_both_sides(self):
        # NES: wearing the Dragon's Scale adds 2 to the defense power, with any armor
        self.assertEqual(StatPreview(DEFENSE_LABEL, 11, 17),
                         stat_preview(self.hero(agility=10, armor='Leather Armor', dragon_scale=True), 'Chain Mail',
                                      'armor'))

    def test_a_cursed_hero(self):
        # The Cursed Belt and the Death Necklace don't change the attack or defense power on the NES
        player = self.hero(strength=30, agility=30, weapon='Club', armor='Clothes', cursed=True)
        self.assertTrue(player.is_cursed)
        self.assertEqual(StatPreview(ATTACK_LABEL, 34, 50), stat_preview(player, 'Broad Sword', 'weapon'))
        self.assertEqual(StatPreview(DEFENSE_LABEL, 17, 39), stat_preview(player, 'Full Plate', 'armor'))

    def test_a_tool_has_none(self):
        self.assertIsNone(stat_preview(self.hero(), 'Herb', 'tool'))


class TestWindow(PreviewTestCase):

    def test_no_nes_window_is_covered(self):
        # Above the pop-up, left of the COMMAND window, clear of the dialog window and every shop's list
        for window in (POPUP_WINDOW, COMMAND_WINDOW, DIALOG_WINDOW, SHOP_INVENTORY_WINDOW):
            with self.subTest(window=window):
                self.assertFalse(overlaps(SHOP_PREVIEW_WINDOW, window))
        for name, inventory in weapon_and_armor_shops(self.config).items():
            with self.subTest(shop=name):
                self.assertFalse(overlaps(SHOP_PREVIEW_WINDOW, variable_height_window(SHOP_INVENTORY_WINDOW,
                                                                                      len(inventory))))

    def test_layout(self):
        layout = preview_layout(StatPreview(ATTACK_LABEL, 12, 20))
        self.assertEqual(SHOP_PREVIEW_WINDOW, layout.window)
        self.assertEqual([("ATTACK", 2, 1), (f"12{ARROW}20", 2, 2)], [tuple(text) for text in layout.texts])

    def test_the_biggest_numbers_fit(self):
        # Level 30 strength (140) with Erdrick's Sword, and the most defense power a hero can have, in English (one
        # NES tile a character; window_tiles raises ValueError for text outside the window) and in Korean (Unifont)
        korean = set_gettext_language('Korean')
        font = set_font_by_ascii_chars(['공격력'], 16, None, Directories(test_config))
        nes_tile = test_config['TILE_SIZE'] / 2
        right_border = SHOP_PREVIEW_WINDOW.width * 2 - 1
        for preview in (StatPreview(ATTACK_LABEL, 180, 168), StatPreview(DEFENSE_LABEL, 115, 111)):
            with self.subTest(preview=preview):
                layout = preview_layout(preview)
                window_tiles(layout._replace(texts=tuple(text._replace(text=text.text.replace(ARROW, ' '))
                                                         for text in layout.texts)))
                for text in layout.texts:
                    self.assertLessEqual(text.column + font.size(korean(text.text))[0] / nes_tile, right_border)
        self.assertEqual(("공격력", "수비력"), (korean(ATTACK_LABEL), korean(DEFENSE_LABEL)))

    def test_english_is_drawn_in_nes_tiles_with_the_arrow(self):
        screen = pygame.Surface((512, 480))
        config = {**self.config, 'NO_BLIT': False}
        rect = draw_shop_preview(screen, StatPreview(ATTACK_LABEL, 12, 20), (255, 255, 255), config, lambda text: text)
        tile_size = config['TILE_SIZE']
        self.assertEqual(Rect(0, 0, 6 * tile_size, 2 * tile_size), rect)
        nes_tile = tile_size // 2
        # the arrow's tile, after "12" on the numbers row (tile column 2 + 2, tile row 2), has white in it
        arrow = screen.subsurface((4 * nes_tile, 2 * nes_tile, nes_tile, nes_tile))
        self.assertIn((255, 255, 255), {tuple(arrow.get_at((x, y)))[:3] for x in range(nes_tile)
                                        for y in range(nes_tile)})

    def test_korean_is_drawn_translated(self):
        korean = set_gettext_language('Korean')
        config = {**self.config, 'NO_BLIT': False}
        with patch('src.translated_window.draw_text') as draw_text:
            draw_shop_preview(pygame.Surface((512, 480)), StatPreview(DEFENSE_LABEL, 5, 9), (255, 255, 255), config,
                              korean)
        self.assertEqual(['수비력', f'5{ARROW}9'], [call.args[0] for call in draw_text.call_args_list])

    def test_nothing_is_drawn_with_no_blit(self):
        screen = pygame.Surface((512, 480))
        draw_shop_preview(screen, StatPreview(ATTACK_LABEL, 12, 20), (255, 255, 255), self.config, lambda text: text)
        self.assertEqual({(0, 0, 0)}, {tuple(screen.get_at((x, y)))[:3] for x in range(0, 512, 8)
                                       for y in range(0, 480, 8)})


class TestInTheShop(PreviewTestCase):

    def browse(self, inventory, *keys):
        """Open the shop's list, press the keys, and return the previews drawn, in order."""
        return [preview for _, preview in self.browse_entries(inventory, *keys)]

    def browse_entries(self, inventory, *keys):
        """Open the shop's list, press the keys, and return each (cursor entry, preview) drawn, in order."""
        entries = []
        make_drawer = self.dialog_lookup.shop_preview_drawer

        def recording_drawer(current_store_inventory):
            draw = make_drawer(current_store_inventory)
            if draw is None:
                return None

            def draw_for(index):
                entries.append(index)
                return draw(index)
            return draw_for

        with patch('src.selection.event.get', side_effect=presses(*keys)), \
                patch.object(self.dialog_lookup, 'shop_preview_drawer', recording_drawer), \
                patch('data.text.dialog_lookup_table.draw_shop_preview', return_value=Rect(0, 0, 1, 1)) as draw:
            self.dialog_lookup.open_store_inventory(inventory)
        return list(zip(entries, [call.args[1] for call in draw.call_args_list]))

    def shown(self, inventory, *keys):
        """The previews shown, one for each entry the cursor stops on (the blink redraws the same one)."""
        entries = self.browse_entries(inventory, *keys)
        return [preview for number, (index, preview) in enumerate(entries)
                if number == 0 or index != entries[number - 1][0]]

    def test_it_follows_the_cursor(self):
        inventory = ShopInventories(self.config).brecconary_weapons_store_inventory
        self.hero(strength=4, agility=4)
        shown = self.shown(inventory, K_DOWN, K_DOWN, K_DOWN, K_UP, K_ESCAPE)
        self.assertEqual([StatPreview(ATTACK_LABEL, 4, 6),  # Bamboo Pole
                          StatPreview(ATTACK_LABEL, 4, 8),  # Club
                          StatPreview(ATTACK_LABEL, 4, 14),  # Copper Sword
                          StatPreview(DEFENSE_LABEL, 2, 4),  # Clothes
                          StatPreview(ATTACK_LABEL, 4, 14)], shown)  # back on the Copper Sword

    def test_in_every_weapon_and_armor_shop_and_in_korean(self):
        for language in ('English', 'Korean'):
            self.dialog_lookup._ = set_gettext_language(language)
            for name, inventory in weapon_and_armor_shops(self.config).items():
                with self.subTest(language=language, shop=name):
                    expected = [stat_preview(self.player, item, details['type'])
                                for item, details in inventory.items()]
                    self.assertEqual(expected, self.shown(inventory, *(K_DOWN,) * (len(inventory) - 1), K_ESCAPE))

    def test_not_in_an_item_shop(self):
        for name, inventory in all_shops(self.config).items():
            if name in weapon_and_armor_shops(self.config):
                continue
            with self.subTest(shop=name):
                self.assertEqual([], self.browse(inventory, K_DOWN, K_ESCAPE))

    def test_nothing_is_drawn_with_the_option_off(self):
        self.config['SHOP_PREVIEW'] = False
        for name, inventory in weapon_and_armor_shops(self.config).items():
            with self.subTest(shop=name):
                self.assertEqual([], self.browse(inventory, K_DOWN, K_ESCAPE))

    def test_the_option_is_read_each_time_the_list_opens(self):
        inventory = ShopInventories(self.config).garinham_weapons_store_inventory
        self.config['SHOP_PREVIEW'] = False
        self.assertEqual([], self.browse(inventory, K_ESCAPE))
        self.config['SHOP_PREVIEW'] = True
        self.assertNotEqual([], self.browse(inventory, K_ESCAPE))

    def test_the_preview_goes_with_the_list(self):
        inventory = ShopInventories(self.config).kol_weapons_store_inventory
        with patch.object(self.game.cmd_menu, 'remove_window') as remove_window:
            self.browse(inventory, K_ESCAPE)
        self.assertEqual([variable_height_window(SHOP_INVENTORY_WINDOW, len(inventory)), SHOP_PREVIEW_WINDOW],
                         [call.args[0] for call in remove_window.call_args_list])
        self.config['SHOP_PREVIEW'] = False
        with patch.object(self.game.cmd_menu, 'remove_window') as remove_window:
            self.browse(inventory, K_ESCAPE)
        self.assertEqual([variable_height_window(SHOP_INVENTORY_WINDOW, len(inventory))],
                         [call.args[0] for call in remove_window.call_args_list])

    def test_the_choice_is_the_nes_choice(self):
        inventory = ShopInventories(self.config).rimuldar_weapons_store_inventory
        for shop_preview in (False, True):
            self.config['SHOP_PREVIEW'] = shop_preview
            with self.subTest(shop_preview=shop_preview), \
                    patch('src.selection.event.get', side_effect=presses(K_DOWN, K_DOWN, pygame.K_k)):
                self.assertEqual("Broad Sword", self.dialog_lookup.open_store_inventory(inventory))


class TestScreen(PreviewTestCase):
    """Drawn for real: the NES shop window's pixels are the same with the preview on or off, and off, nothing else on
    the screen changes either."""

    def make_game(self):
        return new_game(NO_BLIT=False)

    def screen_after_browsing(self, inventory, shop_preview):
        self.config['SHOP_PREVIEW'] = shop_preview
        screen = self.game.screen
        screen.fill((0, 64, 0))
        # the list and the preview stay on the screen (no RemoveWindow), to compare them
        with patch('src.selection.event.get', side_effect=presses(K_DOWN, K_DOWN, K_ESCAPE)), \
                patch.object(self.game.cmd_menu, 'remove_window'):
            self.dialog_lookup.open_store_inventory(inventory)
        return screen.copy()

    def bytes_in(self, surface, window: Window):
        tile_size = self.config['TILE_SIZE']
        return pygame.image.tobytes(surface.subsurface(
            Rect(window.x * tile_size, window.y * tile_size, window.width * tile_size, window.height * tile_size)),
            'RGB')

    def test_shop_window_bytes(self):
        for name, inventory in weapon_and_armor_shops(self.config).items():
            with self.subTest(shop=name):
                shop_window = variable_height_window(SHOP_INVENTORY_WINDOW, len(inventory))
                off = self.screen_after_browsing(inventory, False)
                on = self.screen_after_browsing(inventory, True)
                self.assertEqual(self.bytes_in(off, shop_window), self.bytes_in(on, shop_window))
                # off, the preview's place is as it was; on, the preview is there
                untouched = pygame.Surface(off.get_size())
                untouched.fill((0, 64, 0))
                self.assertEqual(self.bytes_in(untouched, SHOP_PREVIEW_WINDOW), self.bytes_in(off, SHOP_PREVIEW_WINDOW))
                self.assertNotEqual(self.bytes_in(off, SHOP_PREVIEW_WINDOW), self.bytes_in(on, SHOP_PREVIEW_WINDOW))
                # and everything but the preview is the same
                on.blit(off.subsurface(self.rect(SHOP_PREVIEW_WINDOW)), self.rect(SHOP_PREVIEW_WINDOW))
                self.assertEqual(pygame.image.tobytes(off, 'RGB'), pygame.image.tobytes(on, 'RGB'))

    def rect(self, window: Window) -> Rect:
        tile_size = self.config['TILE_SIZE']
        return Rect(window.x * tile_size, window.y * tile_size, window.width * tile_size, window.height * tile_size)
