"""The text beep WAV (data/sound/sfx/text_beep.wav) against SFX_TEXT's decoded APU writes (Bank01 TextSFX).
The WAV comes from reference/reference_utility_scripts/make_text_beep.py."""
import importlib.util
import math
import os
import wave
from unittest import TestCase

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
SCRIPT = os.path.join(ROOT, 'reference', 'reference_utility_scripts', 'make_text_beep.py')
WAV = os.path.join(ROOT, 'data', 'sound', 'sfx', 'text_beep.wav')

NTSC_CPU_HZ = 1789772.7
NMI_HZ = NTSC_CPU_HZ / 29780.5  # 60.0988 frames per second
# $4006 = $7E, $4007 = $08: timer period 126, so the pulse runs at CPU / (16 * 127)
PULSE_HZ = NTSC_CPU_HZ / (16 * (0x7E + 1))
SFX_FRAMES = 8  # TextSFX's length byte
ENVELOPE_MS = 15 / 240 * 1000  # constant volume off, envelope period 0: 15 to 0 in 15 quarter frames


def load_script():
    spec = importlib.util.spec_from_file_location('make_text_beep', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_wav():
    with wave.open(WAV) as wav:
        params = wav.getparams()
        data = wav.readframes(params.nframes)
    samples = [int.from_bytes(data[i:i + 2], 'little', signed=True) for i in range(0, len(data), 2)]
    return params, samples


def magnitude(samples, rate, frequency):
    """Goertzel: the strength of one frequency in a Hann-windowed block of samples."""
    n = len(samples)
    coefficient = 2 * math.cos(2 * math.pi * frequency / rate)
    s1 = s2 = 0.0
    for i, x in enumerate(samples):
        windowed = x * (0.5 - 0.5 * math.cos(2 * math.pi * i / (n - 1)))
        s1, s2 = windowed + coefficient * s1 - s2, s1
    return math.sqrt(max(0.0, s1 * s1 + s2 * s2 - coefficient * s1 * s2))


class TestTextBeepSound(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.script = load_script()
        cls.params, cls.samples = read_wav()

    def test_decoded_register_writes(self):
        self.assertEqual([
            (0, [(0x400C, 0x32), (0x4004, 0x00), (0x4006, 0x7E), (0x4007, 0x08), (0x400E, 0x0E), (0x400F, 0x08)]),
            (8, [(0x4015, 0x05), (0x4015, 0x0F), (0x4005, 0x08), (0x400C, 0x30)]),
        ], self.script.text_sfx_register_writes())

    def test_wav_format(self):
        self.assertEqual((1, 2, 44100), (self.params.nchannels, self.params.sampwidth, self.params.framerate))

    def test_lasts_8_frames(self):
        rate = self.params.framerate
        sfx_ms = SFX_FRAMES / NMI_HZ * 1000  # 133.1 ms
        tail_ms = self.script.TAIL_MS
        self.assertAlmostEqual(sfx_ms + tail_ms, len(self.samples) / rate * 1000, delta=0.1)
        # sound up to the end of frame 8, then only the filters settling
        last_loud = max(i for i, x in enumerate(self.samples) if abs(x) > 500)
        self.assertAlmostEqual(sfx_ms, last_loud / rate * 1000, delta=1.5)

    def test_pitch_is_the_pulse_timer(self):
        rate = self.params.framerate
        block = self.samples[:int(rate * 0.06)]
        candidates = [PULSE_HZ - 20 + i * 0.25 for i in range(161)]
        peak = max(candidates, key=lambda frequency: magnitude(block, rate, frequency))
        self.assertAlmostEqual(880.8, PULSE_HZ, delta=0.05)
        self.assertAlmostEqual(PULSE_HZ, peak, delta=1)

    def test_pulse_envelope_dies_out_and_noise_carries_on(self):
        rate = self.params.framerate

        def tone(start_ms, end_ms):
            return magnitude(self.samples[int(rate * start_ms / 1000):int(rate * end_ms / 1000)], rate, PULSE_HZ)

        def peak(start_ms, end_ms):
            return max(abs(x) for x in self.samples[int(rate * start_ms / 1000):int(rate * end_ms / 1000)])

        self.assertGreater(tone(0, 20), 1.4 * tone(25, 45))  # envelope about 13 on average, then about 8
        self.assertLess(tone(ENVELOPE_MS + 5, 130), tone(0, 20) / 50)  # pulse silent after 62.5 ms
        self.assertGreater(peak(ENVELOPE_MS + 5, 130), 500)  # the volume 2 noise is still there

    def test_script_reproduces_the_wav(self):
        with wave.open(WAV) as wav:
            committed = wav.readframes(wav.getnframes())
        self.assertEqual(committed, self.script.render())
