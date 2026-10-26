"""
The NES and SFC soundtracks' tracks (src/chiptune.py track references), for each moment the game plays music at:
the music (maps, fights, the title, the ending), which loops, and the clips (jingles), which play once.

- NES: data/sound/music/NES/dragon_warrior.nsf, the NES game's own music data and sound engine. Its track numbers are
  the NES's music numbers (Bank01 InitMusicSFX's MSC_ values), so every moment plays exactly the NES's track. Its
  playlist (dragon_warrior.m3u) tags each clip's length.
- SFC: the Super Famicom remake's (Dragon Quest I & II, 1993) Dragon Quest I tracks, one SPC file each, in
  data/sound/music/SFC. Each SPC's ID666 tag gives its length. The remake has no SPC of its own for the title (the
  shared Dragon Quest I & II overture), so the title keeps its recording.
"""
from functools import cache
from os.path import join

from src.chiptune import track_ref
from src.paths import data_path

DUNGEON_FLOORS = range(1, 9)


def dungeon_floor_music_name(floor: int) -> str:
    return f'dungeon_floor_{floor}_music'


# NES music numbers (Bank01 InitMusicSFX's MSC_ values), which are also the NSF's track numbers
MSC_INTRO = 0x01
MSC_THRN_ROOM = 0x02
MSC_TANTAGEL2 = 0x03  # the castle's courtyard and lower floors
MSC_VILLAGE = 0x04
MSC_OUTDOOR = 0x05
MSC_DUNGEON1 = 0x06  # MSC_DUNGEON1 to MSC_DUNGEON8 are $06 to $0D, one a floor deeper each
MSC_ENTR_FGHT = 0x0E  # the "monster draws near" run, which falls through into the fight loop (SQ1Fight)
MSC_END_BOSS = 0x0F
MSC_END = 0x10
MSC_SILV_HARP = 0x11
MSC_FRY_FLUTE = 0x12
MSC_RNBW_BRDG = 0x13
MSC_DEATH = 0x14
MSC_INN = 0x15
MSC_PRNCS_LOVE = 0x16
MSC_CURSED = 0x17
MSC_REG_FGHT = 0x18  # the fight loop on its own
MSC_VICTORY = 0x19
MSC_LEVEL_UP = 0x1A


def nes_nsf_path() -> str:
    return data_path('sound', 'music', 'NES', 'dragon_warrior.nsf')


def nes_track(music_number: int) -> str:
    return track_ref(nes_nsf_path(), music_number)


def nes_music() -> dict[str, str]:
    """The NES's music for each moment (the dungeon floors: MSC_DUNGEON1 to 8, one a minor third lower and slower each)."""
    return {
        'intro_overture': nes_track(MSC_INTRO),
        # The NES plays the village music on the adventure log screens (the title menu)
        'intermezzo': nes_track(MSC_VILLAGE),
        'tantegel_castle_throne_room_music': nes_track(MSC_THRN_ROOM),
        'tantegel_castle_courtyard_music': nes_track(MSC_TANTAGEL2),
        'village_music': nes_track(MSC_VILLAGE),
        'overworld_music': nes_track(MSC_OUTDOOR),
        **{dungeon_floor_music_name(floor): nes_track(MSC_DUNGEON1 + floor - 1) for floor in DUNGEON_FLOORS},
        # Erdrick's Cave is an ordinary dungeon on the NES
        'erdricks_cave_floor_1_music': nes_track(MSC_DUNGEON1),
        'erdricks_cave_floor_2_music': nes_track(MSC_DUNGEON1 + 1),
        # NES MSC_ENTR_FGHT, the music every fight but the last starts with (InitFight). The track already runs into
        # the fight loop, so it loops on by itself
        'battle_music': nes_track(MSC_ENTR_FGHT),
        # NES MSC_REG_FGHT, the fight loop on its own: what the fight music restarts with after the flute, the harp or
        # a cursed item (ChkUseFlute, ChkUseHarp, ChkUseBelt, ChkUseNecklace)
        'regular_fight_music': nes_track(MSC_REG_FGHT),
        'end_boss_music': nes_track(MSC_END_BOSS),
        'ending_music': nes_track(MSC_END),
    }


def nes_clips() -> dict[str, str]:
    """The NES's music clips (InitMusicSFX with an MSC_ number, then usually WaitForMusicEnd)."""
    return {
        'death_music': nes_track(MSC_DEATH),
        'inn_music': nes_track(MSC_INN),
        'princess_gwaelins_love_music': nes_track(MSC_PRNCS_LOVE),
        'victory_music': nes_track(MSC_VICTORY),
        'level_up_music': nes_track(MSC_LEVEL_UP),
        'harp_music': nes_track(MSC_SILV_HARP),
        'flute_music': nes_track(MSC_FRY_FLUTE),
        'cursed_music': nes_track(MSC_CURSED),
        'rainbow_bridge_music': nes_track(MSC_RNBW_BRDG),
    }


def sfc_dir() -> str:
    return data_path('sound', 'music', 'SFC')


def sfc_track(file_name: str) -> str:
    return track_ref(join(sfc_dir(), file_name))


# The remake's dungeon music (the SPC set's "Dark Dungeon" floors 1 to 4, then "Throne of Darkness") is the five parts
# of the orchestral suite, A to E, which it plays by depth: in Charlock, A on the ground floor and B1, B on B2, C on
# B3, D on B4 to B6 and E on B7, the Dragonlord's floor. The game's dungeon floors 1 to 8 are those depths (Charlock's
# ground floor to B7), so every dungeon gets the part for its depth.
SFC_DUNGEON_PART_FILES = {
    1: 'dark_dungeon_floor_1.spc',  # A
    2: 'dark_dungeon_floor_1.spc',  # A
    3: 'dark_dungeon_floor_2.spc',  # B
    4: 'dark_dungeon_floor_3.spc',  # C
    5: 'dark_dungeon_floor_4.spc',  # D
    6: 'dark_dungeon_floor_4.spc',  # D
    7: 'dark_dungeon_floor_4.spc',  # D
    8: 'throne_of_darkness.spc',  # E
}


def sfc_music() -> dict[str, str]:
    """The Super Famicom remake's music for each moment."""
    castle = sfc_track('tantegel_castle.spc')
    fight = sfc_track('a_monster_draws_near.spc')  # opens with the "monster draws near" run, then loops the fight
    return {
        # The remake's title plays the Dragon Quest I & II overture, which has no SPC here: its recording
        'intro_overture': join(sfc_dir(), '09 Overture March (Original Game Sound).mp3'),
        # "Erdrick's Descendant" is the remake's Intermezzo, on the adventure log screens
        'intermezzo': sfc_track('erdricks_descendant.spc'),
        # The remake's castle has one theme, upstairs and down
        'tantegel_castle_throne_room_music': castle,
        'tantegel_castle_courtyard_music': castle,
        'village_music': sfc_track('peaceful_village.spc'),
        'overworld_music': sfc_track('kingdom_of_alefgard.spc'),
        **{dungeon_floor_music_name(floor): sfc_track(file_name) for floor, file_name in SFC_DUNGEON_PART_FILES.items()},
        # "Ancestor's Legacy", the whole suite as a medley, is what the remake plays in Erdrick's Cave
        'erdricks_cave_floor_1_music': sfc_track('ancestors_legacy.spc'),
        'erdricks_cave_floor_2_music': sfc_track('ancestors_legacy.spc'),
        'battle_music': fight,
        'regular_fight_music': fight,
        'end_boss_music': sfc_track('the_dragonlord.spc'),
        'ending_music': sfc_track('heros_fanfare.spc'),  # the remake's finale
    }


def sfc_clips() -> dict[str, str]:
    """The Super Famicom remake's jingles."""
    return {
        'death_music': sfc_track('thou_hast_died.spc'),
        'inn_music': sfc_track('good_night.spc'),
        'princess_gwaelins_love_music': sfc_track('princess_gwaelins_love.spc'),
        'victory_music': sfc_track('victory.spc'),
        'level_up_music': sfc_track('improvement.spc'),
        'harp_music': sfc_track('silver_harp.spc'),
        'flute_music': sfc_track('fairy_flute.spc'),
        'cursed_music': sfc_track('cursed.spc'),
        'rainbow_bridge_music': sfc_track('rainbow_bridge.spc'),
    }


@cache
def clip_refs() -> frozenset[str]:
    """Every chiptune clip, of either soundtrack."""
    return frozenset(nes_clips().values()) | frozenset(sfc_clips().values())


def is_clip(ref: str) -> bool:
    """Whether a chiptune track is a clip, which plays once and ends, rather than music the console loops."""
    return ref in clip_refs()
