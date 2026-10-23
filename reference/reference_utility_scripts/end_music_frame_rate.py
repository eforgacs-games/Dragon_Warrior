"""
Measure the frame rate the end music recording (MSC_END, data/sound/music/NES/16 ...Hero's Fanfare.mp3) was made at,
for #315: does the music follow 60 Hz or the NES's 60.0988 Hz?

Usage (from the project root):
    python reference/reference_utility_scripts/end_music_frame_rate.py path/to/Bank01.asm \
        path/to/Dragon_Warrior_Defines.asm "data/sound/music/NES/16 Dragon Quest 1 - Hero's Fanfare.mp3"

The note starts of the square channels come from playing the end music the way the sound engine does
(end_music_timing.py), in NES frames. The mp3's onsets are where its loudness rises (5 ms windows). For each frame rate
from 59.98 to 60.14 Hz, the note starts are laid over the onsets at the best offset, and the frame rate whose notes land
on the most onset strength is the one the recording plays at. It prints the score for each rate: the peak is at
60.084 to 60.096 Hz, and 60 Hz scores no better than rates far from either.
"""
import array
import os
import sys

os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import end_music_timing  # noqa: E402
import pygame  # noqa: E402

SAMPLE_RATE = 44100
HOP = 220  # 5 ms


def note_start_frames(bank01_path: str, defines_path: str) -> list[int]:
    with open(bank01_path) as bank01, open(defines_path) as defines:
        lines, names = bank01.readlines(), end_music_timing.aliases(defines.readlines())
    memory, labels = end_music_timing.memory_map(lines, names)
    music = end_music_timing.EndMusic(memory, labels, names)
    starts: list[int] = []
    frame = 0
    next_note = music.next_note

    def recording_next_note(channel):
        before = channel.length
        next_note(channel)
        if before == 1 and channel.length and not channel.quiet and channel is not music.channels[end_music_timing.TRI]:
            starts.append(frame)

    music.next_note = recording_next_note
    while music.playing():
        frame += 1
        music.frame()
    return starts


def onset_strength(mp3_path: str) -> list[float]:
    pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1)
    samples = array.array('h', pygame.mixer.Sound(mp3_path).get_raw())
    energy = [sum(abs(sample) for sample in samples[i:i + HOP]) / HOP for i in range(0, len(samples) - HOP, HOP)]
    flux = [0.0] + [max(0.0, energy[i] - energy[i - 1]) for i in range(1, len(energy))]
    return [max(flux[max(0, i - 1):i + 2]) for i in range(len(flux))]  # a window either side


def score(strength: list[float], note_frames: list[int], fps: float, offset: float) -> float:
    total = 0.0
    for frame in note_frames:
        index = int((offset + frame / fps) * SAMPLE_RATE / HOP)
        if 0 <= index < len(strength):
            total += strength[index]
    return total


def main():
    bank01_path, defines_path, mp3_path = sys.argv[1:4]
    note_frames = note_start_frames(bank01_path, defines_path)
    strength = onset_strength(mp3_path)
    for step in range(41):
        fps = 59.98 + step * 0.004
        best, offset_ms = max((score(strength, note_frames, fps, offset_ms / 1000), offset_ms)
                              for offset_ms in range(-1500, 1500, 1))
        print(f'{fps:.3f} Hz: score {best:.0f} (offset {offset_ms} ms)')


if __name__ == '__main__':
    main()
