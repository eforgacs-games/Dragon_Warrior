"""RANDOMNESS NES: the NES's own random number (src/random_streams.py NesRandom), its option and its lock, and the rolls
read the way the NES reads them."""
import os
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame  # noqa: E402
from pygame import K_DOWN, K_PAGEDOWN, K_RIGHT, K_u  # noqa: E402

from src.config.test_config import test_config  # noqa: E402
from src.direction import Direction, nes_direction  # noqa: E402
from src.game_options import RANDOMNESS  # noqa: E402
from src.menu import silver_harp_enemy  # noqa: E402
from src.options_overlay import FIRST_ROW, FIXED_ROWS, OPTION_PAGES, OPTIONS_WINDOW, OptionsOverlay  # noqa: E402
from src.random_streams import NES_STATES, RANDOMNESS_NES, RANDOMNESS_SEEDED, NesRandom, RandomStreams, Stream, \
    activate, active_streams, hero_random, nes_update, seed_all, world_random  # noqa: E402
from src.waiting import frame_at, frame_passed, game_ticks, set_frame_listener, set_game_speed  # noqa: E402
from tests import helpers  # noqa: E402
from tests.test_options_overlay import OverlayTestCase, page_texts  # noqa: E402


def update_6502(state: int) -> int:
    """NES UpdateRandNum (Bank03, $C55B), instruction by instruction, on the two bytes."""
    lb, ub = state & 0xFF, state >> 8
    old_ub = ub                                   # LDA RandNumUB, STA GenWord3CUB; LDA RandNumLB, STA GenWord3CLB
    a = lb
    carry, lb = lb >> 7, lb << 1 & 0xFF           # ASL RandNumLB
    carry, ub = ub >> 7, (ub << 1 | carry) & 0xFF  # ROL RandNumUB
    total = a + lb                                # CLC, ADC RandNumLB, STA RandNumLB
    lb, carry = total & 0xFF, total >> 8
    total = ub + old_ub + carry                   # LDA RandNumUB, ADC GenWord3CUB, STA RandNumUB
    ub = total & 0xFF
    ub = (lb + ub) & 0xFF                         # LDA RandNumLB, CLC, ADC RandNumUB, STA RandNumUB
    total = lb + 0x81                             # LDA RandNumLB, CLC, ADC #$81, STA RandNumLB
    lb, carry = total & 0xFF, total >> 8
    ub = (ub + carry) & 0xFF                      # LDA RandNumUB, ADC #$00, STA RandNumUB
    return ub << 8 | lb


class TestNesRandom(TestCase):

    def test_update_is_the_nes_routine_for_every_number(self):
        self.assertEqual([update_6502(state) for state in range(NES_STATES)],
                         [nes_update(state) for state in range(NES_STATES)])

    def test_a_roll_reads_the_upper_byte_after_one_update(self):
        nes = NesRandom(0x1234)
        self.assertEqual(nes_update(0x1234) >> 8, nes.update())
        self.assertEqual(nes_update(0x1234), nes.state)

    def test_advance_is_that_many_updates(self):
        for steps in (0, 1, 2, 3, 255, 4096, 100_000):
            stepped, jumped = NesRandom(777), NesRandom(777)
            for _ in range(steps):
                stepped.update()
            jumped.advance(steps)
            with self.subTest(steps=steps):
                self.assertEqual(stepped.state, jumped.state)

    def test_randint_masks_the_low_bits_of_the_upper_byte(self):
        # NES DoHeal: AND #$07, ADC #$0A
        for state in (0, 0x4321, 0xFFFF):
            with self.subTest(state=state):
                self.assertEqual(10 + (nes_update(state) >> 8 & 0x07), NesRandom(state).randint(10, 17))
                self.assertEqual(nes_update(state) >> 8, NesRandom(state).randint(0, 255))

    def test_randint_rolls_again_past_the_count(self):
        # GetEnemyInRow: AND #$07, again while it's 5 or more
        nes = NesRandom(0)
        expected, state = None, 0
        while expected is None:
            state = nes_update(state)
            if state >> 8 & 0x07 < 5:
                expected = state >> 8 & 0x07
        self.assertEqual(expected, nes.randint(0, 4))
        self.assertEqual(state, nes.state)

    def test_randint_refuses_more_than_a_byte(self):
        with self.assertRaises(ValueError):
            NesRandom().randint(0, 256)

    def test_choice_sample_shuffle_and_random_read_the_number(self):
        nes = NesRandom(5)
        self.assertIn(nes.choice('abc'), 'abc')
        self.assertEqual(sorted(nes.sample(range(4), 4)), [0, 1, 2, 3])
        items = list(range(8))
        nes.shuffle(items)
        self.assertEqual(sorted(items), list(range(8)))
        state = nes.state
        self.assertEqual((nes_update(state) >> 8) / 256, nes.random())

    def test_store_upper_byte(self):
        # SetEnDmg1: STA RandNumUB
        nes = NesRandom(0xABCD)
        nes.store_upper_byte(0x3F)
        self.assertEqual(0x3FCD, nes.state)

    def test_one_update_a_frame(self):
        nes = NesRandom(9)
        nes.frames_passed(100)  # the first: where counting starts
        self.assertEqual(9, nes.state)
        nes.frames_passed(103)
        nes.frames_passed(103)  # the same frame again: nothing
        expected = NesRandom(9)
        expected.advance(3)
        self.assertEqual(expected.state, nes.state)


class TestTheStreamsInNesMode(TestCase):

    def setUp(self):
        self.was_active = active_streams()
        self.nes_mode = True
        self.streams = RandomStreams(1985, nes_mode=lambda: self.nes_mode)
        activate(self.streams)

    def tearDown(self):
        activate(self.was_active)

    def test_the_hero_and_the_world_share_the_nes_number(self):
        self.assertIs(self.streams[Stream.HERO], self.streams[Stream.WORLD])
        self.assertIs(self.streams.nes, self.streams[Stream.HERO])
        first = hero_random.randint(0, 255)
        self.assertEqual(nes_update(nes_update(1985)) >> 8, world_random.randint(0, 255))
        self.assertEqual(nes_update(1985) >> 8, first)
        self.nes_mode = False
        self.assertIsNot(self.streams[Stream.HERO], self.streams[Stream.WORLD])

    def test_frames_step_it_only_while_it_is_in_use(self):
        self.streams.frames_passed(10)
        self.streams.frames_passed(12)
        expected = NesRandom(1985)
        expected.advance(2)
        self.assertEqual(expected.state, self.streams.nes.state)
        self.nes_mode = False
        self.streams.frames_passed(500)
        self.nes_mode = True
        self.streams.frames_passed(501)  # counting starts again here, not from frame 12
        self.assertEqual(expected.state, self.streams.nes.state)

    def test_the_store_only_reaches_the_nes_number(self):
        hero_random.store_upper_byte(0x12)
        self.assertEqual(0x12, self.streams.nes.upper_byte)
        self.nes_mode = False
        state = self.streams.nes.state
        hero_random.store_upper_byte(0x34)
        self.assertEqual(state, self.streams.nes.state)

    def test_seed_all_and_reseed_set_the_number(self):
        seed_all(0x12345)
        self.assertEqual(0x2345, self.streams.nes.state)

    def test_saved_and_restored(self):
        hero_random.randint(0, 255)
        saved = self.streams.to_save()
        restored = RandomStreams(0)
        restored.restore(RandomStreams.decode_save(saved))
        self.assertEqual(self.streams.nes.state, restored.nes.state)
        for nes in (-1, NES_STATES, 'one', True, None):
            with self.subTest(nes=nes), self.assertRaises(ValueError):
                RandomStreams.decode_save({**saved, 'nes': nes})


class TestTheOption(TestCase):

    def test_seed_and_multiplayer_lock_it_on_seeded(self):
        config = {'RANDOMNESS': RANDOMNESS_NES}
        self.assertFalse(RANDOMNESS.locked(config))
        self.assertEqual(RANDOMNESS_NES, RANDOMNESS.in_force(config))
        for lock in ({'SEED': 0}, {'SEED': 1985}, {'MULTIPLAYER': True}):
            with self.subTest(lock=lock):
                self.assertTrue(RANDOMNESS.locked({**config, **lock}))
                self.assertEqual(RANDOMNESS_SEEDED, RANDOMNESS.in_force({**config, **lock}))
        self.assertFalse(RANDOMNESS.locked({**config, 'SEED': None, 'MULTIPLAYER': False}))

    def test_the_game_goes_by_the_option_in_force(self):
        game = helpers.new_game({**test_config, 'RANDOMNESS': RANDOMNESS_NES})
        self.assertTrue(game.nes_randomness())
        self.assertIs(game.random_streams.nes, game.random_streams[Stream.HERO])
        game.config['SEED'] = 7
        self.assertFalse(game.nes_randomness())
        game.config['SEED'] = None
        game.config['RANDOMNESS'] = RANDOMNESS_SEEDED
        self.assertFalse(game.nes_randomness())

    def test_the_nes_number_steps_with_game_time_whatever_the_speed(self):
        game = helpers.new_game({**test_config, 'RANDOMNESS': RANDOMNESS_NES})
        clock = helpers.fake_game_clock()
        self.addCleanup(patch.stopall)
        self.addCleanup(set_game_speed, 1)
        for speed in (1, 4):
            set_game_speed(speed)
            frame_passed()
            start, first_frame = game.random_streams.nes.state, frame_at(game_ticks())
            clock.advance_frames(60)  # 60 frames of game time: a 15th of the real time at 4x
            frame_passed()
            frames = frame_at(game_ticks()) - first_frame
            expected = NesRandom(start)
            expected.advance(frames)
            with self.subTest(speed=speed):
                self.assertIn(frames, (59, 60, 61))  # the clock counts whole milliseconds
                self.assertEqual(expected.state, game.random_streams.nes.state)


class TestFrameListeners(TestCase):

    def test_each_name_has_its_own_listener(self):
        calls = []
        set_frame_listener(lambda: calls.append('a'), 'test a')
        set_frame_listener(lambda: calls.append('b'), 'test b')
        set_frame_listener(lambda: calls.append('a2'), 'test a')  # in place of the first
        try:
            frame_passed()
        finally:
            set_frame_listener(None, 'test a')
            set_frame_listener(None, 'test b')
        self.assertEqual(['a2', 'b'], [call for call in calls if call in ('a', 'a2', 'b')])


class TestNesReads(TestCase):

    def test_the_silver_harp_rolls_again_on_5_and_7(self):
        # HarpRNGLoop: AND #$07; 5 and 7 again; 6 is the Scorpion
        with patch('src.menu.hero_random.randint', side_effect=[0xFD, 0x0F, 0xEE]) as randint:
            self.assertEqual('Scorpion', silver_harp_enemy())
        self.assertEqual(3, randint.call_count)
        for number, name in ((0, 'Slime'), (1, 'Red Slime'), (2, 'Drakee'), (3, 'Ghost'), (4, 'Magician')):
            with self.subTest(number), patch('src.menu.hero_random.randint', return_value=0x08 | number):
                self.assertEqual(name, silver_harp_enemy())

    def test_npc_directions_are_the_nes_ones(self):
        # DIR_UP $00, DIR_RIGHT $01, DIR_DOWN $02, DIR_LEFT $03
        self.assertEqual([Direction.UP, Direction.RIGHT, Direction.DOWN, Direction.LEFT],
                         [nes_direction(value) for value in range(4)])


class TestTheRow(OverlayTestCase):
    """The RANDOMNESS row, and how a locked row looks and behaves."""

    def go_to_randomness(self):
        """The keys from the first row to the RANDOMNESS row."""
        page = next(number for number, page in enumerate(OPTION_PAGES) if any(
            getattr(row, 'config_key', None) == 'RANDOMNESS' for row in page.rows))
        row = next(number for number, row in enumerate(OPTION_PAGES[page].rows)
                   if getattr(row, 'config_key', None) == 'RANDOMNESS')
        return page, (K_PAGEDOWN,) * page + (K_DOWN,) * (FIXED_ROWS + row)

    def randomness_texts(self, page):
        """The RANDOMNESS row's label and value on the page."""
        texts = page_texts(self.config, page)
        label = texts.index("RANDOMNESS")
        return texts[label:label + 2]

    def test_it_switches_between_nes_and_seeded(self):
        page, keys = self.go_to_randomness()
        self.config['RANDOMNESS'] = RANDOMNESS_NES
        self.assertEqual(["RANDOMNESS", "NES"], self.randomness_texts(page))
        self.run_overlay(*keys, K_RIGHT, K_u)
        self.assertEqual(RANDOMNESS_SEEDED, self.config['RANDOMNESS'])
        self.assertEqual(["RANDOMNESS", "SEEDED"], self.randomness_texts(page))

    def test_a_locked_row_shows_seeded_and_does_not_change(self):
        page, keys = self.go_to_randomness()
        self.config['RANDOMNESS'] = RANDOMNESS_NES
        self.config['SEED'] = 1985
        self.addCleanup(self.config.update, SEED=None)
        self.assertEqual(["RANDOMNESS", "SEEDED"], self.randomness_texts(page))
        sounds = self.run_overlay(*keys, K_RIGHT, K_u)
        self.assertEqual(RANDOMNESS_NES, self.config['RANDOMNESS'])  # kept for when nothing locks it
        self.assertEqual(page, sounds)  # the page turns' sounds, none for the locked row

    def test_a_locked_row_is_dimmed(self):
        page, _ = self.go_to_randomness()
        overlay = OptionsOverlay(self.game)
        overlay.page = page
        screen = pygame.Surface((256 * 2, 240 * 2))
        row = next(number for number, row in enumerate(overlay.rows) if getattr(row, 'config_key', None) == 'RANDOMNESS')
        nes_tile = self.config['TILE_SIZE'] // 2
        y = (OPTIONS_WINDOW.y * 2 + FIRST_ROW + 2 * (FIXED_ROWS + row)) * nes_tile
        point = (4 * nes_tile, y + nes_tile // 2)
        for locked in (False, True):
            screen.fill((255, 255, 255))
            self.config['SEED'] = 1985 if locked else None
            overlay.dim_locked_rows(screen)
            with self.subTest(locked=locked):
                self.assertEqual(locked, screen.get_at(point)[:3] != (255, 255, 255))
        self.config['SEED'] = None
