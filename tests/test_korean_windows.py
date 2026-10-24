"""With the Korean catalog, the generated windows show their text in Korean (src/translated_window.py), and the item,
spell and equipment names drawn over them are translated, each whole on one line (the NES font has no Korean)."""
import builtins
import os
from unittest import TestCase
from unittest.mock import MagicMock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from src.battle_controller import BattleController
from src.common import set_gettext_language
from src.config.test_config import test_config
from src.game import Game
from src.directories import Directories
from src.options_overlay import OPTION_PAGES, OPTION_ROWS, OPTIONS_WINDOW, VALUE_COLUMN, options_layout
from src.options_screen import MESSAGE_SPEED_OPTIONS, OptionsScreen, adventure_log_options
from src.text import NESFont, set_font_by_ascii_chars
from src.translated_window import draw_translated_window
from src.windows import COMBAT_COMMAND_LAYOUT, STATUS_LAYOUT, YES_NO_LAYOUT


class KoreanTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        # set_gettext_language('Korean') installs _ into builtins; put things back afterwards
        had_builtin, old_builtin = hasattr(builtins, '_'), getattr(builtins, '_', None)
        self.korean = set_gettext_language('Korean')
        self.addCleanup(self.restore_builtin, had_builtin, old_builtin)
        self.saved_config = {key: test_config[key] for key in ('NO_WAIT', 'RENDER_TEXT', 'NO_BLIT')}
        test_config.update(NO_WAIT=True, RENDER_TEXT=False, NO_BLIT=False)
        self.addCleanup(test_config.update, self.saved_config)
        with patch('src.game.SCALED'):
            self.game = Game(test_config)
        self.game._ = self.game.cmd_menu._ = self.korean
        self.cmd_menu = self.game.cmd_menu
        self.player = self.game.player
        self.nes_tile = test_config['TILE_SIZE'] / 2

    @staticmethod
    def restore_builtin(had_builtin, old_builtin):
        if had_builtin:
            builtins._ = old_builtin  # type: ignore[attr-defined]
        elif hasattr(builtins, '_'):
            del builtins._  # type: ignore[attr-defined]

    def drawn(self, draw_text):
        """(text, tile column, tile row) of each draw_text call, in screen NES tiles."""
        return [(call.args[0], call.args[1] / self.nes_tile, call.args[2] / self.nes_tile)
                for call in draw_text.call_args_list]

    def texts(self, draw_text):
        return [call.args[0] for call in draw_text.call_args_list]


class TestKoreanItemAndSpellWindows(KoreanTestCase):

    def draw_item_menu(self, menu_name, entries):
        with patch('src.menu.draw_text') as draw_text, patch('src.menu.draw_window'), \
                patch.object(self.cmd_menu, 'draw_window_title') as draw_title:
            self.cmd_menu.draw_item_menu(menu_name, entries)
        return draw_text, draw_title

    def test_item_window_names_are_korean_on_one_line(self):
        self.player.inventory = ['Herb', 'Herb', 'Magic Key', 'Stones of Sunlight']
        draw_text, _ = self.draw_item_menu('inventory', ['Herb', 'Magic Key', 'Stones of Sunlight'])
        # The window is at tile (18, 6); each name whole at tile column 2 of its entry's row, the counts at column 10
        self.assertEqual([('약초', 20, 7.5), ('2', 28, 7.5), ('열쇠', 20, 9.5), ('1', 28, 9.5), ('태양의 돌', 20, 11.5)],
                         self.drawn(draw_text))

    def test_spell_window_names_and_title_are_korean(self):
        draw_text, draw_title = self.draw_item_menu('spells', ['HEAL', 'HURT', 'RETURN'])
        self.assertEqual(['호이미', '기라', '루라'], self.texts(draw_text))
        self.assertEqual('주문', draw_title.call_args.args[0])

    def test_item_window_is_unchanged_in_english(self):
        self.cmd_menu._ = set_gettext_language('English')
        self.player.inventory = ['Magic Key']
        draw_text, _ = self.draw_item_menu('inventory', ['Magic Key'])
        self.assertEqual(['Magic', '1', 'Key'], self.texts(draw_text))


class TestKoreanStatusWindow(KoreanTestCase):

    def draw_status_window(self):
        self.player.name = 'ERDRICK'
        self.player.weapon, self.player.armor, self.player.shield = 'Copper Sword', 'Clothes', 'Small Shield'
        with patch('src.menu.draw_text') as values, patch('src.translated_window.draw_text') as labels, \
                patch('src.translated_window.draw_window') as draw_window:
            self.cmd_menu.draw_status_window()
        return values, labels, draw_window

    def test_labels_are_korean_and_end_where_the_nes_labels_end(self):
        _, labels, draw_window = self.draw_status_window()
        # Only the border is generated; the labels are drawn as text over it
        self.assertEqual((), draw_window.call_args.args[1].texts)
        self.assertEqual([('이름:', 10 + 11, 6 + 1.5), ('힘:', 10 + 16, 6 + 3.5), ('민첩성:', 10 + 16, 6 + 5.5),
                          ('최대 HP:', 10 + 16, 6 + 7.5), ('최대 MP:', 10 + 16, 6 + 9.5),
                          ('공격력:', 10 + 16, 6 + 11.5), ('수비력:', 10 + 16, 6 + 13.5), ('무기:', 10 + 10, 6 + 15.5),
                          ('갑옷:', 10 + 10, 6 + 17.5), ('방패:', 10 + 10, 6 + 19.5)], self.drawn(labels))
        self.assertTrue(all(call.kwargs['alignment'] == 'right' for call in labels.call_args_list))

    def test_equipment_is_korean_on_one_line(self):
        values, _, _ = self.draw_status_window()
        self.assertEqual([('구리 검', 10 + 10, 6 + 15.5), ('천 옷', 10 + 10, 6 + 17.5), ('가죽 방패', 10 + 10, 6 + 19.5)],
                         self.drawn(values)[7:])

    def test_english_status_window_is_generated(self):
        self.cmd_menu._ = set_gettext_language('English')
        values, labels, draw_window = self.draw_status_window()
        self.assertIs(STATUS_LAYOUT, draw_window.call_args.args[1])
        labels.assert_not_called()
        self.assertEqual(['Copper', 'Sword', 'Clothes', 'Small', 'Shield'], self.texts(values)[7:])


class TestKoreanSelectionWindows(KoreanTestCase):

    def test_yes_no_window(self):
        with patch('src.translated_window.draw_text') as draw_text, \
                patch('src.translated_window.draw_window', return_value=pygame.Rect(0, 0, 1, 1)) as draw_window:
            self.cmd_menu.draw_yes_no_window(True, True)
        # YesNo1Dat is at tile (10, 4): YES and NO at tile column 2 of rows 2 and 4
        self.assertEqual([('예', 12, 6.5), ('아니요', 12, 8.5)], self.drawn(draw_text))
        self.assertEqual(0, draw_window.call_args.kwargs['cursor_index'])  # the cursor on YES

    def test_combat_command_window(self):
        controller = BattleController(self.game)
        with patch('src.translated_window.draw_text') as draw_text, \
                patch('src.translated_window.draw_window', return_value=pygame.Rect(0, 0, 1, 1)):
            controller.draw_command_window(cursor_visible=True)
        self.assertEqual(['작전', '공격', '주문', '도망치기', '도구'], self.texts(draw_text))

    def test_untranslated_window_is_generated_in_the_nes_font(self):
        with patch('src.translated_window.draw_text') as draw_text, \
                patch('src.translated_window.draw_window') as draw_window:
            draw_translated_window(MagicMock(), COMBAT_COMMAND_LAYOUT, (255, 255, 255), test_config, str,
                                   cursor_index=2)
        draw_text.assert_not_called()
        self.assertIs(COMBAT_COMMAND_LAYOUT, draw_window.call_args.args[1])
        self.assertEqual(2, draw_window.call_args.kwargs['cursor_index'])

    def test_title_is_cut_out_of_the_top_border(self):
        screen = MagicMock()
        with patch('src.translated_window.draw_text'), patch('src.translated_window.draw_window'):
            draw_translated_window(screen, COMBAT_COMMAND_LAYOUT, (255, 255, 255), test_config, self.korean)
        # "COMMAND" starts at tile column 4 of the window at tile (12, 2)
        left = screen.fill.call_args.args[1][0]
        self.assertEqual((12 + 4) * self.nes_tile - test_config['SCALE'], left)

    def test_nothing_is_drawn_without_blit(self):
        screen = MagicMock()
        with patch('src.translated_window.draw_text') as draw_text:
            rect = draw_translated_window(screen, YES_NO_LAYOUT, (255, 255, 255), {**test_config, 'NO_BLIT': True},
                                          self.korean)
        draw_text.assert_not_called()
        screen.blit.assert_not_called()
        tile_size = test_config['TILE_SIZE']
        self.assertEqual(pygame.Rect(*(value * tile_size for value in YES_NO_LAYOUT.window)), rect)


class TestKoreanOptionsScreen(KoreanTestCase):

    def draw(self, options, index=0):
        options_screen = OptionsScreen(self.game.screen, {**self.game.game_state.config, 'LANGUAGE': 'Korean'})
        with patch('src.options_screen.draw_text') as draw_text:
            options_screen.draw_window(options, index, show_cursor=True)
        return self.texts(draw_text)

    def test_message_speed_window(self):
        self.assertEqual(['표시 속도를', '어느 것으로', '하겠습니까?', '빠름', '보통', '느림'],
                         self.draw(MESSAGE_SPEED_OPTIONS))

    def overlay_texts(self, config, page=0):
        with patch('src.translated_window.draw_text') as draw_text:
            draw_translated_window(self.game.screen, options_layout(config, page), (255, 255, 255), config,
                                   self.korean, cursor_index=0)
        return self.drawn(draw_text)

    def test_options_overlay(self):
        config = {**self.game.game_state.config, **{row.config_key: row.values[0] for row in OPTION_ROWS}}
        self.assertEqual([['화면과 소리', '프리셋', '커스텀', '페이지', '1/3', '표시 속도', '빠름', '대화 방식',
                           '클래식 (NES)', '페이드 방식', 'NES', '음악', '오케스트라', '언어', 'ENGLISH', '주사선',
                           '끄기', '화면 배율', '스무스', '능력치 창', 'NES', '상점 미리보기', '끄기 (NES)'],
                          ['게임 플레이', '프리셋', '커스텀', '페이지', '2/3', 'NPC가 길 비키기', '켜기', '계단',
                           '밟으면 이동', '빠른 행동', '끄기 (NES)', '적 출현', 'NES', '경험치/골드', 'x1 (NES)',
                           '모험 일지', '끄기 (NES)', '자동 저장', '끄기 (NES)'],
                          ['조작', '프리셋', '커스텀', '페이지', '3/3', '게임 속도', '끄기 (NES)', '상태 저장',
                           '끄기 (NES)', '되감기', '끄기 (NES)', '자동 사냥', '끄기 (NES)', '사냥 멈춤', '빨간 HP',
                           '메뉴 속도', '보통', '치트', '끄기 (NES)', '달리기 버튼', '끄기 (NES)']],
                         [[text for text, _, _ in self.overlay_texts(config, page)] for page in range(3)])
        config.update({row.config_key: row.values[1] for row in OPTION_ROWS})
        self.assertEqual([['화면과 소리', '프리셋', '커스텀', '페이지', '1/3', '표시 속도', '보통', '대화 방식', '모던',
                           '페이드 방식', '스무스', '음악', 'NES', '언어', '한국어', '주사선', '켜기',
                           '화면 배율', '정수 배율', '능력치 창', '항상', '상점 미리보기', '켜기'],
                          ['게임 플레이', '프리셋', '커스텀', '페이지', '2/3', 'NPC가 길 비키기', '끄기 (NES)', '계단',
                           'NES', '빠른 행동', '켜기', '적 출현', '절반', '경험치/골드', 'x2', '모험 일지', '목표',
                           '자동 저장', '켜기'],
                          ['조작', '프리셋', '커스텀', '페이지', '3/3', '게임 속도', '켜기', '상태 저장', '켜기',
                           '되감기', '켜기', '자동 사냥', '켜기', '사냥 멈춤', 'HP 절반', '메뉴 속도', '게임 속도대로',
                           '치트', '켜기', '달리기 버튼', '켜기']],
                         [[text for text, _, _ in self.overlay_texts(config, page)] for page in range(3)])

    def test_a_translated_window_draws_every_line_in_one_font(self):
        # "NES" stays in English. Picked by its own characters it was drawn in the NES font, bigger than the Korean
        # (Unifont) on the other rows.
        config = {**self.game.game_state.config, 'DIALOG_STYLE': 'Classic', 'NPCS_MAKE_WAY': True,
                  'FADE_STYLE': 'NES', 'AUTO_STAIRS': False}
        with patch('src.translated_window.draw_text') as draw_text:
            draw_translated_window(self.game.screen, options_layout(config), (255, 255, 255), config, self.korean)
        fonts = {call.kwargs['text_font'] for call in draw_text.call_args_list}
        self.assertIn('NES', [call.args[0] for call in draw_text.call_args_list])
        self.assertEqual(1, len(fonts))
        self.assertNotIsInstance(fonts.pop(), NESFont)

    def test_options_overlay_text_fits(self):
        # Each label ends before its value starts, and each value inside the window's right border, in the window's
        # one font (Unifont), with every value of every row, on every page
        directories = Directories(test_config)
        right_border = (OPTIONS_WINDOW.x + OPTIONS_WINDOW.width) * 2 - 1
        title_end = OPTIONS_WINDOW.x * 2 + OPTIONS_WINDOW.width * 2 - 1
        font = set_font_by_ascii_chars(['설정'], 16, None, directories)
        for choice in range(3):
            config = {**self.game.game_state.config,
                      **{row.config_key: row.values[choice % len(row.values)] for row in OPTION_ROWS}}
            for page in range(len(OPTION_PAGES)):
                title, *texts = self.overlay_texts(config, page)
                with self.subTest(text=title[0]):
                    self.assertLessEqual(title[1] + font.size(title[0])[0] / self.nes_tile, title_end)
                for text, column, row in texts:
                    width = font.size(text)[0] / self.nes_tile
                    end = OPTIONS_WINDOW.x * 2 + (VALUE_COLUMN - 1 if column < VALUE_COLUMN else right_border)
                    with self.subTest(text=text):
                        self.assertLessEqual(column + width, end)

    def test_adventure_log_window(self):
        self.assertEqual(['모험의 서 1:ERDR', '모험의 서 3:LORA'],
                         self.draw(adventure_log_options([(1, 'ERDRICK'), (3, 'LORA')], self.korean)))

    def test_english_options_are_unchanged(self):
        options_screen = OptionsScreen(self.game.screen, {**self.game.game_state.config, 'LANGUAGE': 'English'})
        with patch('src.options_screen.draw_text') as draw_text:
            options_screen.draw_window(MESSAGE_SPEED_OPTIONS, 0, show_cursor=True)
        self.assertEqual(['Which Message', 'Speed Do You', 'Want To Use?', 'FAST', 'NORMAL', 'SLOW'],
                         self.texts(draw_text))
        self.assertEqual(['ADVENTURE LOG 2:ERDR'], list(adventure_log_options([(2, 'ERDRICK')]).labels))
