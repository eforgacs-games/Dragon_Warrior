"""Which track plays at each moment with the NES and SFC soundtracks (src/chiptune_soundtracks.py), and the orchestral
fallback without libgme (src/directories.py playable_soundtrack)."""
import os
from unittest import TestCase
from unittest.mock import patch

from src.chiptune import parse_track_ref, tagged_length_seconds
from src.chiptune_soundtracks import is_clip, nes_clips, nes_music, nes_nsf_path, sfc_clips, sfc_dir, sfc_music
from src.config.test_config import test_config
from src.directories import CLIP_NAMES, MUSIC_NAMES, Directories, orchestra_music, playable_soundtrack
from src.smoke_test import check_chiptune_tracks, chiptune_tracks
from src.soundtrack import SOUNDTRACK_KEY, Soundtrack
from tests.helpers import requires_libgme

# Each moment's NES music number (Bank01 InitMusicSFX's MSC_ value), which is the NSF's track number
NES_MUSIC_NUMBERS = {
    'intro_overture': 0x01,  # MSC_INTRO
    'intermezzo': 0x04,  # MSC_VILLAGE, on the adventure log screens
    'tantegel_castle_throne_room_music': 0x02,  # MSC_THRN_ROOM
    'tantegel_castle_courtyard_music': 0x03,  # MSC_TANTAGEL2
    'village_music': 0x04,  # MSC_VILLAGE
    'overworld_music': 0x05,  # MSC_OUTDOOR
    'dungeon_floor_1_music': 0x06,  # MSC_DUNGEON1
    'dungeon_floor_2_music': 0x07,
    'dungeon_floor_3_music': 0x08,
    'dungeon_floor_4_music': 0x09,
    'dungeon_floor_5_music': 0x0A,
    'dungeon_floor_6_music': 0x0B,
    'dungeon_floor_7_music': 0x0C,
    'dungeon_floor_8_music': 0x0D,  # MSC_DUNGEON8
    'erdricks_cave_floor_1_music': 0x06,
    'erdricks_cave_floor_2_music': 0x07,
    'battle_music': 0x0E,  # MSC_ENTR_FGHT
    'regular_fight_music': 0x18,  # MSC_REG_FGHT
    'end_boss_music': 0x0F,  # MSC_END_BOSS
    'ending_music': 0x10,  # MSC_END
}
NES_CLIP_NUMBERS = {
    'harp_music': 0x11,  # MSC_SILV_HARP
    'flute_music': 0x12,  # MSC_FRY_FLUTE
    'rainbow_bridge_music': 0x13,  # MSC_RNBW_BRDG
    'death_music': 0x14,  # MSC_DEATH
    'inn_music': 0x15,  # MSC_INN
    'princess_gwaelins_love_music': 0x16,  # MSC_PRNCS_LOVE
    'cursed_music': 0x17,  # MSC_CURSED
    'victory_music': 0x19,  # MSC_VICTORY
    'level_up_music': 0x1A,  # MSC_LEVEL_UP
}
SFC_MUSIC_FILES = {
    'intro_overture': '09 Overture March (Original Game Sound).mp3',
    'intermezzo': 'erdricks_descendant.spc',
    'tantegel_castle_throne_room_music': 'tantegel_castle.spc',
    'tantegel_castle_courtyard_music': 'tantegel_castle.spc',
    'village_music': 'peaceful_village.spc',
    'overworld_music': 'kingdom_of_alefgard.spc',
    # The dungeon suite's parts by depth, as the remake plays them in Charlock: A, A, B, C, D, D, D, E
    'dungeon_floor_1_music': 'dark_dungeon_floor_1.spc',
    'dungeon_floor_2_music': 'dark_dungeon_floor_1.spc',
    'dungeon_floor_3_music': 'dark_dungeon_floor_2.spc',
    'dungeon_floor_4_music': 'dark_dungeon_floor_3.spc',
    'dungeon_floor_5_music': 'dark_dungeon_floor_4.spc',
    'dungeon_floor_6_music': 'dark_dungeon_floor_4.spc',
    'dungeon_floor_7_music': 'dark_dungeon_floor_4.spc',
    'dungeon_floor_8_music': 'throne_of_darkness.spc',
    'erdricks_cave_floor_1_music': 'ancestors_legacy.spc',
    'erdricks_cave_floor_2_music': 'ancestors_legacy.spc',
    'battle_music': 'a_monster_draws_near.spc',
    'regular_fight_music': 'a_monster_draws_near.spc',
    'end_boss_music': 'the_dragonlord.spc',
    'ending_music': 'heros_fanfare.spc',
}
SFC_CLIP_FILES = {
    'harp_music': 'silver_harp.spc',
    'flute_music': 'fairy_flute.spc',
    'rainbow_bridge_music': 'rainbow_bridge.spc',
    'death_music': 'thou_hast_died.spc',
    'inn_music': 'good_night.spc',
    'princess_gwaelins_love_music': 'princess_gwaelins_love.spc',
    'cursed_music': 'cursed.spc',
    'victory_music': 'victory.spc',
    'level_up_music': 'improvement.spc',
}


def nes_number(ref: str) -> int:
    track = parse_track_ref(ref)
    assert track is not None and track.path == nes_nsf_path(), ref
    return track.number


def sfc_file(ref: str) -> str:
    assert os.path.dirname(ref) == sfc_dir(), ref
    return os.path.basename(ref)


class TestNesSoundtrack(TestCase):

    def test_every_moment_plays_the_nes_track(self):
        self.assertEqual(NES_MUSIC_NUMBERS, {name: nes_number(ref) for name, ref in nes_music().items()})

    def test_every_clip_is_the_nes_track(self):
        self.assertEqual(NES_CLIP_NUMBERS, {name: nes_number(ref) for name, ref in nes_clips().items()})

    def test_every_clip_has_a_tagged_length(self):
        for name, ref in nes_clips().items():
            with self.subTest(clip=name):
                self.assertIsNotNone(tagged_length_seconds(ref))
                self.assertTrue(is_clip(ref))
        self.assertFalse(is_clip(nes_music()['battle_music']))


class TestSfcSoundtrack(TestCase):

    def test_every_moment_plays_its_sfc_track(self):
        self.assertEqual(SFC_MUSIC_FILES, {name: sfc_file(ref) for name, ref in sfc_music().items()})

    def test_every_clip_is_the_sfc_jingle(self):
        self.assertEqual(SFC_CLIP_FILES, {name: sfc_file(ref) for name, ref in sfc_clips().items()})

    def test_every_clip_has_a_tagged_length(self):
        for name, ref in sfc_clips().items():
            with self.subTest(clip=name):
                self.assertIsNotNone(tagged_length_seconds(ref))
                self.assertTrue(is_clip(ref))

    def test_every_file_is_there_and_every_spc_is_used(self):
        used = set(SFC_MUSIC_FILES.values()) | set(SFC_CLIP_FILES.values())
        self.assertEqual(used, set(os.listdir(sfc_dir())))


class TestEveryMomentHasMusic(TestCase):

    def test_the_same_moments_in_every_soundtrack(self):
        for music in (nes_music(), sfc_music(), orchestra_music()):
            self.assertEqual(set(MUSIC_NAMES), set(music))
        self.assertEqual(set(CLIP_NAMES), set(nes_clips()))
        self.assertEqual(set(CLIP_NAMES), set(sfc_clips()))


class TestWithoutLibgme(TestCase):
    """Without libgme the NES and SFC soundtracks' music is the orchestral recordings', and the clips stay chiptune
    tracks (MusicPlayer keeps their timing, silently)."""

    def test_the_orchestral_recordings_instead(self):
        with patch('src.directories.chiptune_available', return_value=False):
            for chosen in (Soundtrack.NES, Soundtrack.SFC, Soundtrack.ORCHESTRA):
                config = {**test_config, SOUNDTRACK_KEY: chosen}
                with self.subTest(soundtrack=chosen):
                    self.assertIs(Soundtrack.ORCHESTRA, playable_soundtrack(config))
                    self.assertEqual(orchestra_music()['overworld_music'], Directories(config).overworld_music)
            self.assertEqual(nes_clips()['victory_music'],
                             Directories({**test_config, SOUNDTRACK_KEY: Soundtrack.NES}).victory_music)

    def test_with_libgme_the_chosen_soundtrack(self):
        with patch('src.directories.chiptune_available', return_value=True):
            for chosen in (Soundtrack.NES, Soundtrack.SFC, Soundtrack.ORCHESTRA):
                self.assertIs(chosen, playable_soundtrack({**test_config, SOUNDTRACK_KEY: chosen}))


@requires_libgme
class TestEveryTrackPlays(TestCase):

    def test_the_smoke_test_renders_every_track(self):
        tracks = chiptune_tracks()
        self.assertEqual(len(set(NES_MUSIC_NUMBERS.values()) | set(NES_CLIP_NUMBERS.values())) +
                         len({name for name in set(SFC_MUSIC_FILES.values()) | set(SFC_CLIP_FILES.values())
                              if name.endswith('.spc')}), len(tracks))
        self.assertEqual([], check_chiptune_tracks())
