"""Synthesizes data/sound/sfx/text_beep.wav, the dialog text sound (SFX_TEXT, $90), from the NES sound data.

Run it from the repository root:  python reference/reference_utility_scripts/make_text_beep.py
It only needs the standard library, and the output is the same on every run.

What the NES does (nmikstas disassembly, Bank01 sound engine)
-------------------------------------------------------------
TextToPPU plays the sound with ``LDA #SFX_TEXT / BRK / .byte $04, $17`` (InitMusicSFX). SFX_TEXT is $90, so it takes
the DoSFX branch:

- DoSFX: SFXActive = 1, NoisIndex = SFXStrtIndxTbl[$10] = TextSFX ($8486), and right away (not at the next frame)
  SQ2Cntrl1 ($4005) = $08 (sweep off), SQ2Cntrl0 ($4004) = $30 and NoiseCntrl0 ($400C) = $30 (constant volume 0).
  So a new SFX silences whatever SFX was still playing on pulse 2 and noise.
- UpdateSound runs once per frame at the end of the NMI. With an SFX active it calls GetNextNote with X = MCTL_NOIS_SW
  and Y = MCTL_SQ2_HW: the SFX data is read through the noise channel's pointer, and note and control bytes go to the
  pulse 2 registers. SFXActive is the noise channel's ChannelLength, so it is also the SFX's frame counter.

TextSFX ($8486):  F8 32 | FB 00 | AD | EE 08 | 00

  frame 0 (the first NMI after TextToPPU; SFXActive 1 -> 0, so ProcessAudioByte runs):
    F8 32   MCTL_NOISE_VOL (NoiseVolume)  $400C = $32  noise: length counter halted, constant volume, volume 2
    FB 00   MCTL_CNTRL0 (ChnlCntrl0)      $4004 = $00  pulse 2: duty 0 (12.5%), length counter on, envelope on,
                                                       envelope period 0 (decays one step per quarter frame)
    AD      note (LoadMusicNote)          $4006 = $7E, $4007 = $08 (MusicalNotesTbl entry #$AD, A5): timer 126,
                                                       length index 1 (254). Writing $4007 restarts the envelope
                                                       and the duty sequence.
    EE      MCTL_NOISE_CFG (LoadNoise)    $400E = $0E  noise: mode 0 (long), period index 14 (2034 CPU cycles)
                                          $400F = $08  noise: length index 1 (halted, so it never runs out)
    08      length (UpdateChnlUsage)      SFXActive = 8
  frames 1-7: GetNextNote counts SFXActive down from 8 to 1. No register writes.
  frame 8: SFXActive reaches 0, ProcessAudioByte reads 00, which stores 0 in SFXActive and returns 0, so UpdateSound
    ends the SFX: $4015 = $05 then $0F (pulse 2 and noise off, which clears their length counters and silences
    them), $4004 = SQ2Config, $4005 = $08, $400C = $30.

The beep is an 880.8 Hz pulse (1789773 / (16 * 127)) at 12.5% duty whose envelope falls from 15 to 0 in 15 quarter
frames (62.5 ms), over a quiet low noise (volume 2, the noise shift register clocked every 2034 CPU cycles, 880 Hz),
and all of it stops after 8 frames (133.1 ms).

How the WAV is made
-------------------
The script runs that list of register writes through a small model of the two APU channels, one APU cycle (2 CPU
cycles) at a time, at the NTSC CPU clock (236.25 MHz / 11 / 12 = 1789772.7 Hz) with NMIs 29780.5 CPU cycles apart:

- pulse 2: an 11-bit timer clocked every APU cycle that steps an 8-step duty sequencer (duty 0: 0 1 0 0 0 0 0 0, read
  as the sequencer counts down from 0), an envelope, and a length counter. The sweep is off and doesn't mute (timer
  >= 8, and negating can't overflow).
- noise: a timer with the NTSC period table and the 15-bit shift register (feedback bit 0 XOR bit 1), muted when
  bit 0 is set. The register starts at 1 at power-on and keeps running between sounds on the NES, so each beep's
  noise differs; the WAV uses the state after a fixed number of clocks (NOISE_SHIFT_SEED_CLOCKS).
- frame counter: 4-step mode (ClearSoundRegs writes $4017 = $00), quarter frames every 7457 CPU cycles (exactly:
  7457, 14913, 22371, 29829, 29830-cycle period). It isn't tied to the NMI, so the WAV puts a quarter frame right at
  the $4007 write: the envelope is at 15 from the first sample. On the NES the first step lands 0-4 ms later, and until
  then the channel plays at whatever envelope level the previous beep was cut off at.
- mixer: the nonlinear DAC curve from the NESdev wiki (APU Mixer):
    pulse_out = 95.88 / (8128 / pulse + 100),  tnd_out = 159.79 / (1 / (noise / 12241) + 100)
- each 44.1 kHz output sample is the average of the DAC output over the CPU cycles it covers (a box filter, which
  removes most of the aliasing), then goes through the console's analog output filters (NESdev: first-order high-pass
  at 90 Hz and 440 Hz and low-pass at 14 kHz).
- the level is scaled so that a full-volume pulse (envelope 15) peaks at PULSE_FULL_VOLUME_SAMPLE, about as loud as the
  recording this file replaced, so the beep doesn't get louder or quieter next to the other sound effects.
- after the frame 8 silence, TAIL_MS of output lets the high-pass filters settle back to 0.
"""
import os
import struct
import wave

CPU_HZ = 236_250_000 / 11 / 12  # NTSC master clock / 12
CPU_CYCLES_PER_FRAME = 29780.5  # NTSC: 341 x 262 PPU dots / 3, minus the dot skipped on odd frames
SAMPLE_RATE = 44100
TAIL_MS = 10
PULSE_FULL_VOLUME_SAMPLE = 12000
NOISE_SHIFT_SEED_CLOCKS = 1000

SFX_TEXT = 0x90
# Bank01 TextSFX ($8486)
TEXT_SFX_DATA = bytes([0xF8, 0x32, 0xFB, 0x00, 0xAD, 0xEE, 0x08, 0x00])
# Bank01 MusicalNotesTbl entry #$AD (L825F, "880.9HZ (A5)"): timer low byte, then length index / timer high bits
MUSICAL_NOTES = {0xAD: (0x7E, 0x08)}

MCTL_NOTE = 0x80
MCTL_NOISE_CFG = 0xE0
MCTL_NOISE_VOL = 0xF8
MCTL_CNTRL0 = 0xFB

# NESdev APU: length counter load values, NTSC noise periods (CPU cycles), pulse duty sequences
LENGTH_TABLE = [10, 254, 20, 2, 40, 4, 80, 6, 160, 8, 60, 10, 14, 12, 26, 14,
                12, 16, 24, 18, 48, 20, 96, 22, 192, 24, 72, 26, 16, 28, 32, 30]
NOISE_PERIODS = [4, 8, 16, 32, 64, 96, 128, 160, 202, 254, 380, 508, 762, 1016, 2034, 4068]
DUTY_SEQUENCES = [[0, 1, 0, 0, 0, 0, 0, 0], [0, 1, 1, 0, 0, 0, 0, 0], [0, 1, 1, 1, 1, 0, 0, 0], [1, 0, 0, 1, 1, 1, 1, 1]]
# 4-step frame counter: CPU cycles of the quarter-frame clocks within one 29830-cycle sequence
QUARTER_FRAME_CYCLES = (7457, 14913, 22371, 29829)
FRAME_SEQUENCE_CYCLES = 29830


def text_sfx_register_writes() -> list[tuple[int, list[tuple[int, int]]]]:
    """Runs TEXT_SFX_DATA through the sound engine's SFX path (DoSFX, then UpdateSound / GetNextNote /
    ProcessAudioByte once per frame) and returns (frame, [(register, value), ...]) for each frame that writes the APU.
    Frame 0 is the first NMI after InitMusicSFX."""
    writes = []
    index = 0
    sfx_active = 1  # DoSFX
    frame = 0
    while True:
        frame_writes = []
        sfx_active -= 1  # GetNextNote: DEC ChannelLength,X
        if sfx_active == 0:
            while True:  # ProcessAudioByte
                byte = TEXT_SFX_DATA[index]
                index += 1
                if byte == MCTL_NOISE_VOL:  # NoiseVolume
                    frame_writes.append((0x400C, TEXT_SFX_DATA[index]))
                    index += 1
                elif byte == MCTL_CNTRL0:  # ChnlCntrl0, Y = MCTL_SQ2_HW
                    frame_writes.append((0x4004, TEXT_SFX_DATA[index]))
                    index += 1
                elif MCTL_NOISE_CFG <= byte < 0xF6:  # LoadNoise
                    frame_writes += [(0x400E, byte & 0x0F), (0x400F, 0x08)]
                elif MCTL_NOTE <= byte < MCTL_NOISE_CFG:  # LoadMusicNote, NoteOffset is 0 during an SFX
                    low, high = MUSICAL_NOTES[byte]
                    frame_writes += [(0x4006, low), (0x4007, high)]
                elif byte < MCTL_NOTE:  # UpdateChnlUsage: the frame count until the next data byte
                    sfx_active = byte
                    break
                else:
                    raise ValueError(f'TextSFX has no control byte ${byte:02X}')
            if sfx_active == 0:  # UpdateSound: the SFX is over, silence SQ2 and noise
                frame_writes += [(0x4015, 0x05), (0x4015, 0x0F), (0x4005, 0x08), (0x400C, 0x30)]
        if frame_writes:
            writes.append((frame, frame_writes))
        if sfx_active == 0:
            return writes
        frame += 1


class Envelope:
    def __init__(self) -> None:
        self.start = False
        self.divider = 0
        self.decay = 0
        self.period = 0
        self.loop = False
        self.constant = False

    def write_control(self, value: int) -> None:
        self.loop = bool(value & 0x20)
        self.constant = bool(value & 0x10)
        self.period = value & 0x0F

    def quarter_frame(self) -> None:
        if self.start:
            self.start = False
            self.decay = 15
            self.divider = self.period
        elif self.divider == 0:
            self.divider = self.period
            if self.decay:
                self.decay -= 1
            elif self.loop:
                self.decay = 15
        else:
            self.divider -= 1

    @property
    def volume(self) -> int:
        return self.period if self.constant else self.decay


class Pulse:
    def __init__(self) -> None:
        self.envelope = Envelope()
        self.duty = 0
        self.timer_period = 0
        self.timer = 0
        self.step = 0
        self.length = 0
        self.enabled = False

    def write(self, register: int, value: int) -> None:
        if register == 0:
            self.duty = value >> 6
            self.envelope.write_control(value)
        elif register == 2:
            self.timer_period = (self.timer_period & 0x700) | value
        elif register == 3:
            self.timer_period = (self.timer_period & 0xFF) | ((value & 0x07) << 8)
            if self.enabled:
                self.length = LENGTH_TABLE[value >> 3]
            self.step = 0
            self.envelope.start = True
        # register 1 (sweep): TextSFX only ever writes $08, sweep off

    def apu_cycle(self) -> None:
        if self.timer == 0:
            self.timer = self.timer_period
            self.step = (self.step - 1) & 7
        else:
            self.timer -= 1

    def output(self) -> int:
        if not self.length or self.timer_period < 8 or not DUTY_SEQUENCES[self.duty][self.step]:
            return 0
        return self.envelope.volume


class Noise:
    def __init__(self) -> None:
        self.envelope = Envelope()
        self.timer_period = NOISE_PERIODS[0]
        self.timer = 0
        self.shift = 1  # power-on value
        self.mode = 0
        self.length = 0
        self.enabled = False

    def write(self, register: int, value: int) -> None:
        if register == 0:
            self.envelope.write_control(value)
        elif register == 2:
            self.mode = value >> 7
            self.timer_period = NOISE_PERIODS[value & 0x0F]
        elif register == 3:
            if self.enabled:
                self.length = LENGTH_TABLE[value >> 3]
            self.envelope.start = True

    def clock_shift(self) -> None:
        feedback = (self.shift ^ (self.shift >> (6 if self.mode else 1))) & 1
        self.shift = (self.shift >> 1) | (feedback << 14)

    def cpu_cycles(self, cycles: int) -> None:
        """The noise timer counts CPU cycles in NOISE_PERIODS (half of them in APU cycles)."""
        self.timer -= cycles
        while self.timer <= 0:
            self.timer += self.timer_period
            self.clock_shift()

    def output(self) -> int:
        if not self.length or self.shift & 1:
            return 0
        return self.envelope.volume


def pulse_dac(pulse: int) -> float:
    return 95.88 / (8128 / pulse + 100) if pulse else 0.0


def tnd_dac(noise: int) -> float:
    return 159.79 / (1 / (noise / 12241) + 100) if noise else 0.0


def synthesize() -> list[float]:
    """The beep as DAC output (0.0 to 1.0) averaged to SAMPLE_RATE, before the output filters."""
    pulse, noise = Pulse(), Noise()
    for _ in range(NOISE_SHIFT_SEED_CLOCKS):
        noise.clock_shift()
    channels = {0x4004: (pulse, 0), 0x4005: (pulse, 1), 0x4006: (pulse, 2), 0x4007: (pulse, 3),
                0x400C: (noise, 0), 0x400E: (noise, 2), 0x400F: (noise, 3)}

    def write(register: int, value: int) -> None:
        if register == 0x4015:
            pulse.enabled = bool(value & 0x02)
            noise.enabled = bool(value & 0x08)
            if not pulse.enabled:
                pulse.length = 0
            if not noise.enabled:
                noise.length = 0
        else:
            channel, index = channels[register]
            channel.write(index, value)

    write(0x4015, 0x0F)  # ClearSoundRegs (and every earlier SFX's end) leaves all four channels enabled
    for register, value in ((0x4005, 0x08), (0x4004, 0x30), (0x400C, 0x30)):  # DoSFX
        write(register, value)

    frames = text_sfx_register_writes()
    last_frame = frames[-1][0]
    end_cycle = round(last_frame * CPU_CYCLES_PER_FRAME) + round(CPU_HZ * TAIL_MS / 1000)
    pending = [(round(frame * CPU_CYCLES_PER_FRAME), frame_writes) for frame, frame_writes in frames]

    samples = []
    sample_end = CPU_HZ / SAMPLE_RATE
    total = 0.0
    count = 0
    quarter_index = 0
    sequence_start = 0
    for cycle in range(0, end_cycle, 2):  # one APU cycle per step
        while pending and pending[0][0] <= cycle:
            for register, value in pending.pop(0)[1]:
                write(register, value)
        quarter_cycle = sequence_start + QUARTER_FRAME_CYCLES[quarter_index]
        if cycle >= quarter_cycle - QUARTER_FRAME_CYCLES[0]:  # a quarter frame lands right at the first write
            pulse.envelope.quarter_frame()
            noise.envelope.quarter_frame()
            quarter_index += 1
            if quarter_index == len(QUARTER_FRAME_CYCLES):
                quarter_index = 0
                sequence_start += FRAME_SEQUENCE_CYCLES
        pulse.apu_cycle()
        noise.cpu_cycles(2)
        total += 2 * (pulse_dac(pulse.output()) + tnd_dac(noise.output()))
        count += 2
        if cycle + 2 >= sample_end:
            samples.append(total / count)
            total, count = 0.0, 0
            sample_end += CPU_HZ / SAMPLE_RATE
    return samples


def output_filters(samples: list[float]) -> list[float]:
    """NESdev APU Mixer: the console's output goes through first-order high-pass filters at 90 Hz and 440 Hz and a
    first-order low-pass filter at 14 kHz."""
    dt = 1 / SAMPLE_RATE

    def high_pass(signal: list[float], cutoff: float) -> list[float]:
        rc = 1 / (2 * 3.141592653589793 * cutoff)
        alpha = rc / (rc + dt)
        out, previous_in, previous_out = [], 0.0, 0.0
        for x in signal:
            previous_out = alpha * (previous_out + x - previous_in)
            previous_in = x
            out.append(previous_out)
        return out

    def low_pass(signal: list[float], cutoff: float) -> list[float]:
        rc = 1 / (2 * 3.141592653589793 * cutoff)
        alpha = dt / (rc + dt)
        out, y = [], 0.0
        for x in signal:
            y += alpha * (x - y)
            out.append(y)
        return out

    return low_pass(high_pass(high_pass(samples, 90), 440), 14000)


def render() -> bytes:
    """The finished WAV sample data: 16-bit signed mono."""
    scale = PULSE_FULL_VOLUME_SAMPLE / pulse_dac(15)
    filtered = output_filters(synthesize())
    return b''.join(struct.pack('<h', max(-32768, min(32767, round(x * scale)))) for x in filtered)


def main() -> None:
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))),
                        'data', 'sound', 'sfx', 'text_beep.wav')
    with wave.open(path, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(render())
    for frame, frame_writes in text_sfx_register_writes():
        print(f'frame {frame}: ' + ', '.join(f'${register:04X}=${value:02X}' for register, value in frame_writes))
    print(f'wrote {path}')


if __name__ == '__main__':
    main()
