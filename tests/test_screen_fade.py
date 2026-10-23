"""Full-screen fades: the NES palette fade (PalFadeOut, Bank03 $C212; PalFadeIn, $C529), the smooth alpha fade kept as
an option (FADE_STYLE), and which transitions use them."""
from unittest import TestCase
from unittest.mock import patch

import pygame

from src.config.test_config import test_config
from src.ending import CREDITS
from src.intro import Intro
from src.maps import Brecconary
from src.visual_effects import FADE_IN_STEPS, FADE_OUT_STEPS, FADE_STEP_FRAMES, FADE_STYLE_NES, FADE_STYLE_SMOOTH, \
    NES_FPS, NES_PALETTE, PAL_BLACK, fade_style, nes_fade_palette, nes_palette_fade, screen_fade
from tests.helpers import new_game

BLACK_RGB = NES_PALETTE[PAL_BLACK]
# NES color numbers the game's palettes use (OverworldPal, TownPal, RegSPPal, the windows' $30 and low HP $26)
COLORS = (0x30, 0x10, 0x00, 0x11, 0x29, 0x1A, 0x27, 0x37, 0x35, 0x12, 0x16, 0x26, 0x07, PAL_BLACK)
BLOCK = 8


def faded(color_number: int, pal_mod: int) -> tuple[int, int, int]:
    """NES AddPalByte/ChkPalFade: subtract PalModByte from the color number; below $00 is black."""
    return BLACK_RGB if color_number - pal_mod < 0 else NES_PALETTE[color_number - pal_mod]


class TestNesPaletteFade(TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((len(COLORS) * BLOCK, BLOCK))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.config = {'NO_WAIT': False, 'NO_BLIT': False}
        self.waits: list[float] = []  # milliseconds of game time before each frame is shown
        self.shown: list[list[tuple[int, int, int]]] = []  # each block's color, at every display.flip

        def wait(milliseconds, _config=None):
            self.waits.append(milliseconds)

        def wait_frames(frames, _config=None):
            self.waits.append(frames * 1000 / NES_FPS)

        def flip():
            self.shown.append([tuple(self.screen.get_at((index * BLOCK + 1, 1)))[:3] for index in range(len(COLORS))])

        for target, replacement in (('src.visual_effects.wait', wait), ('src.visual_effects.wait_frames', wait_frames),
                                    ('src.visual_effects.display.flip', flip)):
            patcher = patch(target, side_effect=replacement)
            patcher.start()
            self.addCleanup(patcher.stop)

    def draw_colors(self, colors=COLORS):
        for index, color_number in enumerate(colors):
            color = color_number if isinstance(color_number, tuple) else NES_PALETTE[color_number]
            self.screen.fill(color, (index * BLOCK, 0, BLOCK, BLOCK))

    def test_the_nes_steps(self):
        self.assertEqual(FADE_IN_STEPS, (0x30, 0x20, 0x10, 0x00))  # PalFadeIn: from $30, minus $10 until $F0
        self.assertEqual(FADE_OUT_STEPS, (0x00, 0x10, 0x20, 0x30, 0x40))  # PalFadeOut: from $00, plus $10 until $50
        self.assertEqual(FADE_STEP_FRAMES, 4)  # both: LDX #$04, then WaitForNMI until X is 0

    def test_fade_in_shows_each_palette_step_four_frames_apart(self):
        self.draw_colors()
        nes_palette_fade(False, self.screen, self.config)
        # first the black palette, then $30, $20, $10 and $00 (the picture as it was)
        expected = [[BLACK_RGB] * len(COLORS)] + [[faded(color, pal_mod) for color in COLORS]
                                                    for pal_mod in FADE_IN_STEPS]
        self.assertEqual(self.shown, expected)
        self.assertEqual(len(self.waits), 4)
        self.assertEqual(self.waits[1:], [4000 / NES_FPS] * 3)
        # the first wait is what is left of 4 frames once the color numbers have been worked out
        self.assertLessEqual(self.waits[0], 4000 / NES_FPS)

    def test_fade_out_ends_all_black_after_twenty_frames(self):
        self.draw_colors()
        nes_palette_fade(True, self.screen, self.config)
        expected = [[faded(color, pal_mod) for color in COLORS] for pal_mod in FADE_OUT_STEPS]
        self.assertEqual(self.shown, expected)
        self.assertEqual(self.shown[-1], [BLACK_RGB] * len(COLORS))
        self.assertLessEqual(sum(self.waits), 20 * 1000 / NES_FPS + 1e-9)
        self.assertEqual(self.waits[1:], [4000 / NES_FPS] * 4)

    def test_known_colors_fade_to_the_right_color_numbers(self):
        self.draw_colors()
        nes_palette_fade(False, self.screen, self.config)
        by_step = dict(zip(FADE_IN_STEPS, self.shown[1:]))
        white, grey, dark_grey, red = (COLORS.index(number) for number in (0x30, 0x10, 0x00, 0x26))
        self.assertEqual(by_step[0x10][white], NES_PALETTE[0x20])
        self.assertEqual(by_step[0x20][white], NES_PALETTE[0x10])
        self.assertEqual(by_step[0x30][white], NES_PALETTE[0x00])
        self.assertEqual(by_step[0x10][grey], NES_PALETTE[0x00])
        self.assertEqual(by_step[0x10][dark_grey], BLACK_RGB)
        self.assertEqual(by_step[0x10][red], NES_PALETTE[0x16])  # the low HP windows fade too
        self.assertEqual(by_step[0x20][red], NES_PALETTE[0x06])
        self.assertEqual(by_step[0x30][red], BLACK_RGB)

    def test_a_color_that_is_not_an_nes_color_fades_like_the_nearest_one(self):
        off_white, off_red = (250, 250, 250), (250, 110, 100)
        self.draw_colors((off_white, off_red))
        nes_palette_fade(False, self.screen, self.config)
        by_step = dict(zip(FADE_IN_STEPS, self.shown[1:]))
        self.assertEqual(by_step[0x10][:2], [NES_PALETTE[0x20], NES_PALETTE[0x16]])
        self.assertEqual(by_step[0x00][:2], [off_white, off_red])  # the last step is the picture itself

    def test_no_blit_only_waits(self):
        self.draw_colors()
        before = pygame.image.tobytes(self.screen, 'RGB')
        nes_palette_fade(True, self.screen, {**self.config, 'NO_BLIT': True})
        self.assertEqual(self.shown, [])
        self.assertEqual(self.waits, [4000 / NES_FPS] * 5)
        self.assertEqual(pygame.image.tobytes(self.screen, 'RGB'), before)

    def test_fade_palette(self):
        self.assertEqual(nes_fade_palette(0), list(NES_PALETTE))
        self.assertEqual(nes_fade_palette(0x40), [BLACK_RGB] * 64)
        self.assertEqual(nes_fade_palette(0x10)[0x37], NES_PALETTE[0x27])
        self.assertEqual(nes_fade_palette(0x10)[0x0F], BLACK_RGB)


class TestFadeStyle(TestCase):

    def test_nes_is_the_default(self):
        self.assertEqual(test_config['FADE_STYLE'], FADE_STYLE_NES)
        self.assertEqual(fade_style({}), FADE_STYLE_NES)
        self.assertEqual(fade_style({'FADE_STYLE': FADE_STYLE_SMOOTH}), FADE_STYLE_SMOOTH)

    def test_screen_fade_uses_the_selected_fade(self):
        for style, used, unused in ((FADE_STYLE_NES, 'nes_palette_fade', 'fade'),
                                    (FADE_STYLE_SMOOTH, 'fade', 'nes_palette_fade')):
            with self.subTest(style), patch(f'src.visual_effects.{used}') as used_fade, \
                    patch(f'src.visual_effects.{unused}') as unused_fade:
                screen_fade(fade_out=True, screen=None, config={'FADE_STYLE': style})
                used_fade.assert_called_once()
                unused_fade.assert_not_called()


class TestTransitionsUseTheSelectedFade(TestCase):
    """Every transition the NES makes with PalFadeOut or PalFadeIn goes through screen_fade, and so uses the fade
    FADE_STYLE selects. Each record is True for a fade out and False for a fade in."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        for key, value in (('NO_WAIT', True), ('RENDER_TEXT', False), ('NO_BLIT', True)):
            self.addCleanup(test_config.__setitem__, key, test_config[key])
            test_config[key] = value
        self.addCleanup(test_config.__setitem__, 'FADE_STYLE', test_config['FADE_STYLE'])
        self.game = new_game()

    def record_fades(self, style: str):
        test_config['FADE_STYLE'] = style
        fades = {'nes': [], 'smooth': []}
        nes = patch('src.visual_effects.nes_palette_fade', side_effect=lambda fade_out, *_: fades['nes'].append(fade_out))
        smooth = patch('src.visual_effects.fade', side_effect=lambda fade_out, **_: fades['smooth'].append(fade_out))
        for patcher in (nes, smooth):
            patcher.start()
            self.addCleanup(patcher.stop)
        return fades

    def assert_fades(self, run, expected: list[bool], prepare=None):
        for style, used, unused in ((FADE_STYLE_NES, 'nes', 'smooth'), (FADE_STYLE_SMOOTH, 'smooth', 'nes')):
            with self.subTest(style):
                self.setUp()
                if prepare is not None:
                    prepare()
                fades = self.record_fades(style)
                run()
                self.assertEqual(fades[used], expected)
                self.assertEqual(fades[unused], [])
                patch.stopall()

    def test_stairs_fade_out_then_in(self):
        # MapChngWithSound: ScreenFadeOut (PalFadeOut), then PalFadeIn
        self.assert_fades(lambda: self.game.change_map(Brecconary(self.game.config), destination_coordinates=(29, 18)),
                          [True, False])

    def test_begin_a_new_quest_only_fades_in(self):
        def run():
            with patch.object(self.game.title_menu, 'select_adventure_log'), patch('src.title_menu.NameSelection'), \
                    patch.object(self.game.title_menu, 'choose_new_quest_options'):
                self.game.title_menu.begin_new_quest()

        self.assert_fades(run, [False])

    def test_continue_a_quest_only_fades_in(self):
        def run():
            self.game.load_game({'Name': 'Erdrick', 'Experience': 0, 'Gold': 0, 'Inventory': []})

        self.assert_fades(run, [False])

    def test_death_only_fades_in(self):
        # NES DeathText -> StartAtThroneRoom: a cut to black, then the throne room fades in
        def run():
            self.game.player.is_dead = True
            with patch.object(self.game.cmd_menu.__class__, 'show_text_in_dialog_box'):
                self.game.set_post_death_attributes()

        self.assert_fades(run, [False])

    def test_inn_fades_out_then_in(self):
        # BuyInnStay: PalFadeOut (LD8DC), then PalFadeIn (LD8FB)
        def run():
            with patch.object(self.game.cmd_menu, 'show_line_in_dialog_box'), \
                    patch.object(self.game.cmd_menu, 'show_text_in_dialog_box'):
                self.game.cmd_menu.dialog_lookup.inn_sleep(6)

        self.assert_fades(run, [True, False], prepare=lambda: self.game.change_map(
            Brecconary(self.game.config), destination_coordinates=(29, 18)))

    def test_credits_fade_in_and_out(self):
        def run():
            ending = self.game.ending
            ending.show_credit_screen(CREDITS[0])
            with patch.object(ending, 'show_credit_screen'):
                ending.roll_credits()

        self.assert_fades(run, [False] + [True] * (len(CREDITS) - 1))

    def test_declining_to_continue_fades_out(self):
        # NES ExitGame: LoadCreditsPals (PalFadeOut), then LoadStartPals (PalFadeIn) over the cleared screen
        def run():
            dialog_lookup = self.game.cmd_menu.dialog_lookup
            with patch.object(self.game.cmd_menu, 'show_line_in_dialog_box'), \
                    patch.object(dialog_lookup, 'wait_for_reset'):
                dialog_lookup.rest_then_for_awhile()

        self.assert_fades(run, [True, False])

    def test_title_screen_cuts_to_black_then_fades_the_empty_screen_in(self):
        # NES DoIntroRoutine (LBDBA) cuts to black with IntroPalPtr3; ShowStartGame's LoadStartPals then runs a
        # PalFadeIn over the cleared screen. There is no fade out.
        def run():
            start = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i, mod=pygame.KMOD_NONE, unicode='')
            with patch('src.intro.get_events', return_value=[start]):
                Intro(self.game.config).show_intro_dragon_banner_with_text(self.game.screen, self.game.clock,
                                                                          self.game.game_state.config)

        self.assert_fades(run, [False])

    def test_the_final_form_fades_the_screen_out_first(self):
        # NES LoadEndBossGFX ($BABD): a whole-screen PalFadeOut before the final form fades in (that one is the enemy's
        # own sprite fade, enemy_fade_in)
        self.assert_fades(lambda: self.game.drawer.fade_in_enemy(self.game.screen, 'Dragonlord 2'), [True])

    def test_running_from_the_final_form_cuts_to_black_then_fades_in(self):
        # NES RunSuccessful (LE8B5): BlackPal at once, then MapChngNoSound reloads the map with a PalFadeIn
        self.assert_fades(lambda: self.game.battle_ctrl.reload_map_after_running_from_final_form(), [False])
