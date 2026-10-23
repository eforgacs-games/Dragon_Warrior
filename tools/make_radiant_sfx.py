"""
Render the NES RADIANT/torch sound (SFX_RADIANT) to data/sound/sfx/radiant.wav by emulating the APU's noise channel.

The soundtrack has no recording of it. RadiantSFX (Bank01, L84A0) is all noise channel:

    MCTL_NOISE_VOL, $3F   constant volume 15, length counter halted
    $EF, $03              noise period 15 (4068 CPU cycles) for 3 frames
    $EE, $02              period 14 (2034) for 2 frames
    $ED, $01              period 13 (1016) for 1 frame
    $EC, $02              period 12 (762) for 2 frames

LoadNoise (L8138) writes only the low nibble to $400E, so it is the normal (long) noise mode. The sound engine runs
once a frame (NMI), so each period lasts whole NES frames.

    uv run python -m tools.make_radiant_sfx
"""
import argparse
import math
import os
import struct
import wave

CPU_HZ = 1789773  # NTSC 2A03
FRAME_CPU_CYCLES = 29780.5  # one NTSC frame, 60.0988 per second
NOISE_PERIODS = (4, 8, 16, 32, 64, 96, 128, 160, 202, 254, 380, 508, 762, 1016, 2034, 4068)  # $400E low nibble
SAMPLE_RATE = 44100

# (period index, volume, frames)
RADIANT_SFX = ((15, 15, 3), (14, 15, 2), (13, 15, 1), (12, 15, 2))

# The soundtrack's wall bump (WallSFX: square channel, volume 15) peaks at -8 dBFS. The APU mixer gives a volume 15
# square 95.88 / (8128 / 15 + 100) = 0.149, so the same factor puts this noise at the soundtrack's level.
OUTPUT_GAIN = 10 ** (-8 / 20) / (95.88 / (8128 / 15 + 100))

OUT_PATH = os.path.join('data', 'sound', 'sfx', 'radiant.wav')


def noise_mixer_level(volume: int) -> float:
    """The APU's non-linear mixer for the noise channel alone (triangle and DMC silent)."""
    return 0.0 if volume == 0 else 159.79 / (1 / (volume / 12241) + 100)


def render_noise_sfx(steps) -> list[float]:
    """The noise channel's output, sampled at SAMPLE_RATE, through the NES's output filters."""
    lfsr = 1  # the shift register's power-on value
    cycles_per_sample = CPU_HZ / SAMPLE_RATE
    timer = 0.0
    raw = []
    for period_index, volume, frames in steps:
        period = NOISE_PERIODS[period_index]
        for _ in range(round(frames * FRAME_CPU_CYCLES / cycles_per_sample)):
            timer += cycles_per_sample
            while timer >= period:  # the timer clocks the shift register once per period
                timer -= period
                feedback = (lfsr & 1) ^ ((lfsr >> 1) & 1)  # long mode taps bits 0 and 1
                lfsr = (lfsr >> 1) | (feedback << 14)
            raw.append(noise_mixer_level(volume) if lfsr & 1 == 0 else 0.0)
    return nes_output_filters(raw + [0.0] * (SAMPLE_RATE // 100))  # 10 ms for the filters to settle


def nes_output_filters(samples: list[float]) -> list[float]:
    """The NES's first-order high-pass filters at 90 Hz and 440 Hz and low-pass at 14 kHz."""
    def high_pass(data, cutoff):
        rc = 1 / (2 * math.pi * cutoff)
        alpha = rc / (rc + 1 / SAMPLE_RATE)
        out, previous_in, previous_out = [], 0.0, 0.0
        for sample in data:
            previous_out = alpha * (previous_out + sample - previous_in)
            previous_in = sample
            out.append(previous_out)
        return out

    def low_pass(data, cutoff):
        rc = 1 / (2 * math.pi * cutoff)
        alpha = (1 / SAMPLE_RATE) / (rc + 1 / SAMPLE_RATE)
        out, previous = [], 0.0
        for sample in data:
            previous += alpha * (sample - previous)
            out.append(previous)
        return out

    return low_pass(high_pass(high_pass(samples, 90), 440), 14000)


def write_wav(path: str, samples: list[float]) -> None:
    with wave.open(path, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(b''.join(struct.pack('<h', max(-32768, min(32767, round(sample * OUTPUT_GAIN * 32767))))
                                 for sample in samples))


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', default=OUT_PATH, help=f"where to write the WAV (default {OUT_PATH})")
    args = parser.parse_args(argv)
    write_wav(args.out, render_noise_sfx(RADIANT_SFX))
    print(f"Wrote {args.out}")


if __name__ == '__main__':
    main()
