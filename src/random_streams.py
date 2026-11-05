"""The game's random numbers, drawn from separate streams (#438).

The NES keeps one random number (UpdateRandNum, Bank03), and this game used Python's one global generator the same
way. Now every roll comes from one of two streams, each its own generator:

- HERO (``hero_random``): what the hero's own play rolls. Whether a step starts a fight and which enemy, everything in
  a fight, spells and herbs, a chest's gold, the Death Necklace and the Silver Harp's enemy.
- WORLD (``world_random``): what goes on around him. Where the NPCs wander, which way one makes way, and what a
  townsperson or Gwaelin picks to say.

Each roll is drawn exactly as before (the same ``randint``, ``choice`` or ``sample`` call, with the same chances); only
the generator it is drawn from has changed. The split is for what comes after 1.0:

- With a seed (``--seed``), the hero's rolls depend only on what the hero does. Time spent in a town while its NPCs
  wander doesn't move them, so two players on the same seed meet the same rolls if they play the same way.
- A second hero can be given a HERO stream of their own.

``RandomStreams`` holds the generators. The game has one (``Game.random_streams``), and it's active: ``hero_random``
and ``world_random`` draw from the active streams, so modules call them the way they called the ``random`` module,
and tests patch their methods (``patch('src.battle.hero_random.randint', ...)``). A save state keeps every stream's
state (``to_save``) so a rewind or a loaded state rolls what it would have rolled.

With no seed, the seed is drawn from Python's global generator when the streams are made. A tool or test that calls
``random.seed()`` before it starts the game still gets the same game.
"""
import base64
import random
from array import array
from collections.abc import MutableSequence, Sequence
from enum import StrEnum
from typing import Any, TypeVar

T = TypeVar('T')


class Stream(StrEnum):
    HERO = 'hero'
    WORLD = 'world'


def encode_random_state(state: tuple) -> list:
    """random.Random.getstate() as JSON: the Mersenne Twister's 625 words packed into base64 (3.3 KB, where a list of
    them would be about 7 KB of JSON and 25 KB of Python ints in memory)."""
    version, internal_state, gauss_next = state
    words = array('I', internal_state)
    return [version, base64.b64encode(words.tobytes()).decode('ascii'), gauss_next]


def decode_random_state(encoded: list) -> tuple:
    version, packed, gauss_next = encoded
    words = array('I')
    words.frombytes(base64.b64decode(packed))
    if len(words) != 625:
        raise ValueError("not a random number generator state")
    return int(version), tuple(words), None if gauss_next is None else float(gauss_next)


def stream_generator(seed: int, stream: Stream) -> random.Random:
    """The generator of one stream for a seed. A string seed is hashed (SHA-512) into the generator's state, so each
    stream's numbers are unrelated to the others' and the same on every machine and Python run."""
    return random.Random(f'{seed}/{stream}')


class RandomStreams:
    """One generator per Stream, all from one seed."""

    def __init__(self, seed: int | None = None) -> None:
        # None only for streams carried over from a version 2 save state, whose seed isn't known
        self.seed: int | None = 0
        self.generators: dict[Stream, random.Random] = {}
        self.reseed(random.getrandbits(64) if seed is None else seed)

    def reseed(self, seed: int) -> None:
        """Start every stream over from ``seed``, in place (``hero_random`` and ``world_random`` keep drawing from
        these streams if they're active)."""
        self.seed = seed
        self.generators = {stream: stream_generator(seed, stream) for stream in Stream}

    def __getitem__(self, stream: Stream) -> random.Random:
        return self.generators[stream]

    def to_save(self) -> dict[str, Any]:
        """The seed and every stream's state, as JSON values (a save state's 'random')."""
        return {'seed': self.seed,
                **{stream.value: encode_random_state(generator.getstate())
                   for stream, generator in self.generators.items()}}

    @staticmethod
    def decode_save(saved: Any) -> dict[str, Any]:
        """What ``to_save`` wrote, checked and decoded (raises KeyError, TypeError or ValueError if it can't be
        read), for ``restore``."""
        seed = saved['seed']
        if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool)):
            raise ValueError(f"not a seed: {seed!r}")
        return {'seed': seed, **{stream.value: decode_random_state(saved[stream.value]) for stream in Stream}}

    def restore(self, decoded: dict[str, Any]) -> None:
        """Put back what ``decode_save`` decoded: the seed and every stream where it was."""
        self.seed = decoded['seed']
        for stream in Stream:
            self.generators[stream].setstate(decoded[stream.value])


_active = RandomStreams()


def active_streams() -> RandomStreams:
    return _active


def activate(streams: RandomStreams) -> None:
    """Draw ``hero_random`` and ``world_random`` from ``streams`` from now on (a new Game activates its own)."""
    global _active
    _active = streams


def seed_all(seed: int) -> None:
    """Seed Python's global generator and start the active streams over from ``seed``: the game rolls the same from
    here whether it's already running (its streams are the active ones) or starts after this (its streams' seed is
    drawn from the global generator)."""
    random.seed(seed)
    _active.reseed(seed)


class StreamRandom:
    """One stream of the active RandomStreams, called like the ``random`` module. Its methods are written out (not
    forwarded) so they're typed, and so a test can patch one stream's ``randint`` without touching the other's."""

    def __init__(self, stream: Stream) -> None:
        self.stream = stream

    def generator(self) -> random.Random:
        return _active[self.stream]

    def randint(self, a: int, b: int) -> int:
        return self.generator().randint(a, b)

    def choice(self, sequence: Sequence[T]) -> T:
        return self.generator().choice(sequence)

    def sample(self, population: Sequence[T], k: int) -> list[T]:
        return self.generator().sample(population, k)

    def shuffle(self, items: MutableSequence[Any]) -> None:
        self.generator().shuffle(items)

    def random(self) -> float:
        return self.generator().random()


hero_random = StreamRandom(Stream.HERO)
world_random = StreamRandom(Stream.WORLD)
