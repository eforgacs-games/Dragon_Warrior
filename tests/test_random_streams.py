"""The random number streams (src/random_streams.py, #438): the hero's rolls and the world's, each its own generator."""
import json
import random
import sys
from unittest import TestCase
from unittest.mock import patch

from src.config.test_config import test_config
from src.random_streams import RandomStreams, Stream, activate, active_streams, decode_random_state, \
    encode_random_state, hero_random, seed_all, world_random
from src.save_state import STATE_MIGRATIONS
from tests.helpers import new_game


def rolls(streams: RandomStreams, stream: Stream, count: int = 20) -> list[int]:
    return [streams[stream].randint(0, 255) for _ in range(count)]


class TestRandomStreams(TestCase):

    def setUp(self):
        self.was_active = active_streams()

    def tearDown(self):
        activate(self.was_active)

    def test_a_seed_rolls_the_same_every_time(self):
        for stream in Stream:
            with self.subTest(stream):
                self.assertEqual(rolls(RandomStreams(1985), stream), rolls(RandomStreams(1985), stream))
        self.assertNotEqual(rolls(RandomStreams(1985), Stream.HERO), rolls(RandomStreams(1986), Stream.HERO))

    def test_the_streams_roll_differently(self):
        streams = RandomStreams(7)
        self.assertNotEqual(rolls(streams, Stream.HERO), rolls(streams, Stream.WORLD))

    def test_the_worlds_rolls_dont_move_the_heros(self):
        # The point of the split: however many rolls the NPCs make meanwhile, the hero's next rolls are the same
        quiet = RandomStreams(42)
        busy = RandomStreams(42)
        for _ in range(1000):
            busy[Stream.WORLD].choice(range(4))
        self.assertEqual(rolls(quiet, Stream.HERO), rolls(busy, Stream.HERO))

    def test_no_seed_takes_one_from_pythons_generator(self):
        random.seed(3)
        first = RandomStreams()
        random.seed(3)
        self.assertEqual(first.seed, RandomStreams().seed)
        self.assertEqual(rolls(first, Stream.HERO), rolls(RandomStreams(first.seed), Stream.HERO))

    def test_the_module_level_streams_draw_from_the_active_ones(self):
        streams = RandomStreams(11)
        expected_hero, expected_world = rolls(RandomStreams(11), Stream.HERO, 5), rolls(RandomStreams(11), Stream.WORLD, 5)
        activate(streams)
        self.assertIs(streams, active_streams())
        self.assertEqual(expected_hero, [hero_random.randint(0, 255) for _ in range(5)])
        self.assertEqual(expected_world, [world_random.randint(0, 255) for _ in range(5)])

    def test_every_call_draws_from_its_own_stream(self):
        activate(RandomStreams(5))
        reference = RandomStreams(5)[Stream.HERO]
        self.assertEqual(reference.choice('abcd'), hero_random.choice('abcd'))
        self.assertEqual(reference.sample(range(10), 3), hero_random.sample(range(10), 3))
        self.assertEqual(reference.random(), hero_random.random())
        items, reference_items = list(range(10)), list(range(10))
        reference.shuffle(reference_items)
        hero_random.shuffle(items)
        self.assertEqual(reference_items, items)

    def test_seed_all_restarts_the_active_streams_and_pythons_generator(self):
        streams = RandomStreams(1)
        activate(streams)
        hero_random.randint(0, 255)
        seed_all(99)
        self.assertEqual(99, streams.seed)
        self.assertEqual(rolls(RandomStreams(99), Stream.HERO), rolls(streams, Stream.HERO))
        python_roll = random.random()
        random.seed(99)
        self.assertEqual(random.random(), python_roll)


class TestSaving(TestCase):

    def test_saved_and_restored_the_streams_roll_on_where_they_were(self):
        streams = RandomStreams(8)
        rolls(streams, Stream.HERO, 3)
        saved = json.loads(json.dumps(streams.to_save()))
        expected = {stream: rolls(streams, stream) for stream in Stream}
        restored = RandomStreams(123)
        restored.restore(RandomStreams.decode_save(saved))
        self.assertEqual(8, restored.seed)
        self.assertEqual(expected, {stream: rolls(restored, stream) for stream in Stream})

    def test_a_save_that_cant_be_read_is_refused(self):
        good = RandomStreams(8).to_save()
        for broken in ({**good, 'seed': 'eight'}, {**good, 'seed': True}, {'seed': 8, 'hero': good['hero']},
                       {**good, 'world': [3, 'AAAA', None]}, [3, 'AAAA', None]):
            with self.subTest(broken=str(broken)[:40]), self.assertRaises((KeyError, TypeError, ValueError)):
                RandomStreams.decode_save(broken)

    def test_an_unknown_seed_is_kept_unknown(self):
        saved = {**RandomStreams(8).to_save(), 'seed': None}
        self.assertIsNone(RandomStreams.decode_save(saved)['seed'])

    def test_a_version_2_state_carries_the_old_generator_on_as_the_heros(self):
        old = random.Random(17)
        old.randint(0, 255)
        snapshot = {'random': encode_random_state(old.getstate())}
        migrated = STATE_MIGRATIONS[2](snapshot)
        streams = RandomStreams(0)
        streams.restore(RandomStreams.decode_save({**migrated['random'], 'nes': 0}))  # 'nes': from version 4 on
        self.assertIsNone(streams.seed)
        self.assertEqual([old.randint(0, 255) for _ in range(20)], rolls(streams, Stream.HERO))
        # The world's stream is a different one, and the same for the same state
        self.assertEqual(migrated, STATE_MIGRATIONS[2](snapshot))
        self.assertNotEqual(decode_random_state(migrated['random']['hero']),
                            decode_random_state(migrated['random']['world']))


class TestTheGamesStreams(TestCase):

    def test_a_seeded_game_rolls_its_seed_and_is_the_active_one(self):
        game = new_game({**test_config, 'SEED': 1985})
        self.assertEqual(1985, game.random_streams.seed)
        self.assertIs(game.random_streams, active_streams())
        self.assertEqual(rolls(RandomStreams(1985), Stream.HERO), [hero_random.randint(0, 255) for _ in range(20)])

    def test_the_seed_flag_seeds_the_game(self):
        from src import game as game_module
        for argv, seed in ((['dragon_warrior', '--seed', '1985'], 1985), (['dragon_warrior'], None)):
            with patch.object(sys, 'argv', argv), patch.object(game_module, 'install_crash_log'), \
                    patch.object(game_module, 'Game') as game_class:
                game_module.run()
            with self.subTest(argv=argv):
                self.assertEqual(seed, game_class.call_args.kwargs['config'].get('SEED'))
