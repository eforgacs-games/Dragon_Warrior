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

The RANDOMNESS option (src/game_options.py) picks between these streams (SEEDED) and the NES's own generator (NES, the
default): ``NesRandom``, the NES's 16-bit number and its UpdateRandNum, one for everything, the hero's rolls and the
world's alike, as on the NES. On the NES, GetJoypadStatus calls UpdateRandNum before every read of the joypad, about
once a frame, so the rolls depend on when the buttons are pressed; here the NES number takes one step for every frame
of game time that passes (``frames_passed``), whatever the game speed, as well as one for every roll. Each roll reads
the NES's upper byte (RandNumUB) the way its NES routine does: ``randint`` over a power of two values masks its low
bits (AND #$07 + 10 for HEAL's 10-17), and the call sites roll the rest as the NES does (src/nes_random.py). Its
timing isn't the console's to the frame (this game's loops aren't the NES's), so the rolls a frame-perfect input
would get on a console aren't the same here; the generator and how each roll reads it are. A seed, or a multiplayer
game, needs the streams: either keeps the option on SEEDED (Option.locked_by).
"""
import base64
import random
from array import array
from collections.abc import MutableSequence, Sequence
from collections.abc import Callable
from enum import StrEnum
from typing import Any, Protocol, TypeVar

T = TypeVar('T')

# The RANDOMNESS option's values (src/game_options.py)
RANDOMNESS_NES = 'NES'
RANDOMNESS_SEEDED = 'Seeded'

# NES UpdateRandNum (Bank03, $C55B): RandNum = RandNum * 3 (ASL, ROL, then the old value added), its upper byte plus
# its lower byte (so * $0303 in all), plus $81
NES_MULTIPLIER = 0x0303
NES_INCREMENT = 0x81
NES_STATES = 0x10000


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


class Generator(Protocol):
    """What a roll draws from: a stream's random.Random, or the NES's generator."""

    def randint(self, a: int, b: int) -> int: ...

    def choice(self, sequence: Sequence[T]) -> T: ...

    def sample(self, population: Sequence[T], k: int) -> list[T]: ...

    def shuffle(self, x: MutableSequence[Any]) -> None: ...

    def random(self) -> float: ...


def nes_update(state: int) -> int:
    """NES UpdateRandNum: the next 16-bit random number."""
    return (state * NES_MULTIPLIER + NES_INCREMENT) % NES_STATES


class NesRandom:
    """The NES's random number (RandNumUB, RandNumLB) and UpdateRandNum, read the way the NES reads it: every roll
    takes one UpdateRandNum and reads the upper byte."""

    def __init__(self, state: int = 0) -> None:
        self.state = state % NES_STATES
        # The frame of game time the number has been stepped up to (frames_passed), None until the first
        self.last_frame: int | None = None

    @property
    def upper_byte(self) -> int:
        return self.state >> 8

    def update(self) -> int:
        """UpdateRandNum, then RandNumUB."""
        self.state = nes_update(self.state)
        return self.upper_byte

    def store_upper_byte(self, value: int) -> None:
        """STA RandNumUB: a routine that writes its masked roll back (SetEnDmg1), changing the numbers after it."""
        self.state = (value & 0xFF) << 8 | self.state & 0xFF

    def advance(self, steps: int) -> None:
        """``steps`` UpdateRandNums at once: the affine step x -> a * x + c composed with itself by squaring, so a long
        wait costs a few dozen multiplications, not one per frame."""
        multiplier, increment = 1, 0  # the steps so far (none)
        step_multiplier, step_increment = NES_MULTIPLIER, NES_INCREMENT  # 1, 2, 4, ... steps
        while steps > 0:
            if steps & 1:
                multiplier, increment = (step_multiplier * multiplier % NES_STATES,
                                         (step_multiplier * increment + step_increment) % NES_STATES)
            step_multiplier, step_increment = (step_multiplier * step_multiplier % NES_STATES,
                                               (step_multiplier * step_increment + step_increment) % NES_STATES)
            steps >>= 1
        self.state = (multiplier * self.state + increment) % NES_STATES

    def frames_passed(self, frame: int) -> None:
        """GetJoypadStatus: one UpdateRandNum for every frame of game time since the last call."""
        if self.last_frame is not None and frame > self.last_frame:
            self.advance(frame - self.last_frame)
        self.last_frame = frame

    def randint(self, a: int, b: int) -> int:
        """A roll of a to b: the low bits of RandNumUB (AND with the power of two up to the count, less one), added to
        a, rolled again while it's too big (as GetEnemyInRow does for 5 slots)."""
        count = b - a + 1
        if not 1 <= count <= 256:
            raise ValueError(f"the NES rolls a byte: no {count} values")
        mask = (1 << (count - 1).bit_length()) - 1
        while (value := self.update() & mask) >= count:
            pass
        return a + value

    def choice(self, sequence: Sequence[T]) -> T:
        return sequence[self.randint(0, len(sequence) - 1)]

    def sample(self, population: Sequence[T], k: int) -> list[T]:
        """Not an NES roll (NPCS MAKE WAY's): k picks without putting back, each a randint."""
        pool = list(population)
        return [pool.pop(self.randint(0, len(pool) - 1)) for _ in range(k)]

    def shuffle(self, x: MutableSequence[Any]) -> None:
        for i in reversed(range(1, len(x))):
            j = self.randint(0, i)
            x[i], x[j] = x[j], x[i]

    def random(self) -> float:
        return self.update() / 256


def stream_generator(seed: int, stream: Stream) -> random.Random:
    """The generator of one stream for a seed. A string seed is hashed (SHA-512) into the generator's state, so each
    stream's numbers are unrelated to the others' and the same on every machine and Python run."""
    return random.Random(f'{seed}/{stream}')


class RandomStreams:
    """One generator per Stream, all from one seed, and the NES's generator, which every roll draws from instead while
    ``nes_mode()`` says so (the RANDOMNESS option: Game.nes_randomness)."""

    def __init__(self, seed: int | None = None, nes_mode: Callable[[], bool] = lambda: False) -> None:
        # None only for streams carried over from a version 2 save state, whose seed isn't known
        self.seed: int | None = 0
        self.generators: dict[Stream, random.Random] = {}
        self.nes = NesRandom()
        self.nes_mode = nes_mode
        self.reseed(random.getrandbits(64) if seed is None else seed)

    def reseed(self, seed: int) -> None:
        """Start every stream over from ``seed``, in place (``hero_random`` and ``world_random`` keep drawing from
        these streams if they're active), and the NES's number from its low 16 bits."""
        self.seed = seed
        self.generators = {stream: stream_generator(seed, stream) for stream in Stream}
        self.nes.state = seed % NES_STATES

    def __getitem__(self, stream: Stream) -> Generator:
        return self.nes if self.nes_mode() else self.generators[stream]

    def frames_passed(self, frame: int) -> None:
        """A loop has passed a frame (src/waiting.py frame_passed): ``frame`` frames of game time have gone by. The
        NES's number takes a step for each (GetJoypadStatus) while it's the one in use; while it isn't, it waits, and
        starts counting again from the frame it's next used on."""
        if self.nes_mode():
            self.nes.frames_passed(frame)
        else:
            self.nes.last_frame = None

    def to_save(self) -> dict[str, Any]:
        """The seed, every stream's state and the NES's number, as JSON values (a save state's 'random')."""
        return {'seed': self.seed,
                **{stream.value: encode_random_state(generator.getstate())
                   for stream, generator in self.generators.items()},
                'nes': self.nes.state}

    @staticmethod
    def decode_save(saved: Any) -> dict[str, Any]:
        """What ``to_save`` wrote, checked and decoded (raises KeyError, TypeError or ValueError if it can't be
        read), for ``restore``."""
        seed = saved['seed']
        if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool)):
            raise ValueError(f"not a seed: {seed!r}")
        nes = saved['nes']
        if not isinstance(nes, int) or isinstance(nes, bool) or not 0 <= nes < NES_STATES:
            raise ValueError(f"not an NES random number: {nes!r}")
        return {'seed': seed, 'nes': nes,
                **{stream.value: decode_random_state(saved[stream.value]) for stream in Stream}}

    def restore(self, decoded: dict[str, Any]) -> None:
        """Put back what ``decode_save`` decoded: the seed, every stream and the NES's number where they were."""
        self.seed = decoded['seed']
        for stream in Stream:
            self.generators[stream].setstate(decoded[stream.value])
        self.nes.state = decoded['nes']


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

    def generator(self) -> Generator:
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

    def store_upper_byte(self, value: int) -> None:
        """NES STA RandNumUB (SetEnDmg1 writes its masked dodge roll back): with the NES's generator in use, its upper
        byte is now ``value``; the streams have nothing to write to."""
        generator = self.generator()
        if isinstance(generator, NesRandom):
            generator.store_upper_byte(value)


hero_random = StreamRandom(Stream.HERO)
world_random = StreamRandom(Stream.WORLD)
