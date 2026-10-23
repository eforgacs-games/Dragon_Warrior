"""
Work out when the NES end credits music (MSC_END) gives its timing events, for src/ending.py.

Usage:
    python reference/reference_utility_scripts/end_music_timing.py path/to/Bank01.asm path/to/Dragon_Warrior_Defines.asm

Both files are in source_files/ of https://github.com/nmikstas/dragon-warrior-disassembly.

DoEndCredits (Bank01) moves on to the next credits screen after a number of "music timing events": WaitForMusicEnd
($815E) waits a frame at a time until the next byte the SQ1 or triangle channel will read is MCTL_NO_OP ($FC), then
skips that byte. The end music's triangle part (TRIEndGame) has a no-op after every few notes; SQ1 has none. A no-op
is waiting to be read for as long as the note before it plays, so each event can be caught during that window. Once
the note ends, the sound engine skips the no-op itself and the event is gone.

This plays the end music the way the sound engine (UpdateSound, $8028) does, one NMI a frame: TempoCntr += Tempo, and
each time that carries, 150 is taken off and the triangle, SQ2 and SQ1 channels (in that order) count down their
note lengths, reading their next bytes when a length runs out. The tempo bytes (MCTL_TEMPO) are in the SQ1 part.

It prints each event's window as (first frame, frame it ends), counted in NMIs after InitMusicSFX starts the music.

Assumptions: Tempo and TempoCntr aren't reset by InitMusicSFX. The music before the ending is Tantegel's ($7D, the
first byte of SQ1Tantagel; EndGameTriggered's MSC_NOSOUND doesn't change it) and TempoCntr is taken as 0, so the
first tick can be a frame off. No SFX plays during the credits, so the noise channel, which WaitForMusicEnd also
checks, never points at a no-op.
"""
import re
import sys

DATA_LINE = re.compile(r'^L([0-9A-F]{4}):\s+\.(byte|word)\s+([^;]*)')
LABEL_LINE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):')
ALIAS_LINE = re.compile(r'^\.alias\s+(\w+)\s+\$([0-9A-F]+)')

MCTL_NO_OP = 0xFC
TEMPO_TICK = 150  # SBC #$96
TANTEGEL_TEMPO = 0x7D
SQ1, SQ2, TRI = 'SQ1', 'SQ2', 'TRI'
CHANNEL_ORDER = (TRI, SQ2, SQ1)  # UpdateSound
EVENT_CHANNELS = (SQ1, TRI)  # WaitForMusicEnd (and the noise channel, see above)


def aliases(lines):
    return {match.group(1): int(match.group(2), 16) for match in map(ALIAS_LINE.match, lines) if match}


def memory_map(lines, names):
    """Address -> byte for Bank01's data, with the defines' names and the labels resolved."""
    labels = {}
    pending = []
    data_lines = []
    for line in lines:
        data = DATA_LINE.match(line)
        if data:
            address = int(data.group(1), 16)
            for label in pending:
                labels[label] = address
            pending = []
            data_lines.append((address, data.group(2), data.group(3)))
            continue
        label = LABEL_LINE.match(line)
        if label:
            pending.append(label.group(1))
    memory = {}
    for address, kind, operands in data_lines:
        values = [value.strip() for value in operands.split(',') if value.strip()]
        for value in values:
            number = int(value[1:], 16) if value.startswith('$') else names.get(value, labels.get(value))
            size = 1 if kind == 'byte' else 2
            if number is not None:  # expressions (outside the music data) are left out
                memory[address] = number & 0xFF
                if size == 2:
                    memory[address + 1] = number >> 8
            address += size
    return memory, labels


class Channel:
    def __init__(self, start):
        self.pointer = start
        self.return_pointer = 0
        self.length = 1  # InitMusicSFX
        self.quiet = 0


class EndMusic:
    def __init__(self, memory, labels, names):
        self.memory = memory
        self.names = names
        self.channels = {SQ1: Channel(labels['SQ1EndGame']), SQ2: Channel(labels['SQ2EndGame']),
                         TRI: Channel(labels['TRIEndGame'])}
        self.tempo = TANTEGEL_TEMPO
        self.tempo_counter = 0

    def read(self, channel):
        value = self.memory[channel.pointer]
        channel.pointer += 1
        return value

    def next_note(self, channel):
        """GetNextNote and ProcessAudioByte: count the note down, and read up to the next length when it ends."""
        if not channel.length:
            return
        channel.length -= 1
        if channel.length:
            return
        n = self.names
        while True:
            value = self.read(channel)
            if value == n['MCTL_JUMP']:
                low, high = self.read(channel), self.read(channel)
                channel.return_pointer = channel.pointer
                channel.pointer = high << 8 | low
            elif value == n['MCTL_TEMPO']:
                self.tempo = self.read(channel)
            elif value == n['MCTL_NO_OP']:
                pass
            elif value == n['MCTL_RETURN']:
                channel.pointer = channel.return_pointer
            elif value in (n['MCTL_CNTRL0'], n['MCTL_CNTRL1'], n['MCTL_NOISE_VOL'], n['MCTL_NOTE_OFST']):
                self.read(channel)
            elif value == n['MCTL_ADD_SPACE']:
                channel.quiet = self.read(channel)
            elif value == n['MCTL_END_SPACE']:
                channel.quiet = 0
            elif value >= n['MCTL_NOISE_CFG']:
                pass
            elif value >= n['MCTL_NOTE']:
                if channel.quiet:
                    channel.length = channel.quiet
                    return
            else:
                channel.length = value  # $00 ends the channel
                return

    def frame(self):
        """One NMI's UpdateSound."""
        total = self.tempo_counter + self.tempo
        self.tempo_counter = total & 0xFF
        if total < 0x100:
            return
        self.tempo_counter = (self.tempo_counter - TEMPO_TICK) & 0xFF
        for name in CHANNEL_ORDER:
            self.next_note(self.channels[name])

    def playing(self):
        return any(channel.length for channel in self.channels.values())

    def event_pending(self):
        return any(self.memory.get(self.channels[name].pointer) == MCTL_NO_OP for name in EVENT_CHANNELS)


def event_windows(music):
    windows = []
    frame = 0
    start = None
    while music.playing():
        frame += 1
        music.frame()
        pending = music.event_pending()
        if pending and start is None:
            start = frame
        elif not pending and start is not None:
            windows.append((start, frame))
            start = None
    return windows, frame


def main():
    with open(sys.argv[1]) as bank01, open(sys.argv[2]) as defines:
        lines, names = bank01.readlines(), aliases(defines.readlines())
    memory, labels = memory_map(lines, names)
    windows, length = event_windows(EndMusic(memory, labels, names))
    print(f'# {len(windows)} timing events; the music ends after {length} frames')
    print('END_MUSIC_TIMING_EVENTS = (')
    for start, end in windows:
        print(f'    ({start}, {end}),')
    print(')')


if __name__ == '__main__':
    main()
