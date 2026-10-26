from functools import cache
from os.path import join

from pygame import font

from src.paths import data_path, default_save_dir, project_root
from src.soundtrack import SOUNDTRACKS, Soundtrack, soundtrack


# Each soundtrack's folder under data/sound/music
SOUNDTRACK_FOLDERS = {Soundtrack.NES: 'NES', Soundtrack.SFC: 'SFC', Soundtrack.ORCHESTRA: 'orchestra'}
DUNGEON_FLOOR_MUSIC_NAMES = tuple(f'dungeon_floor_{floor}_music' for floor in range(1, 9))


def _arrangement_paths(folder: str, overture: str, intermezzo: str, castle: str, village: str, overworld: str,
                       fight: str, dungeon: str, end_boss: str, ending: str) -> dict[str, str]:
    """The music of a soundtrack with one track per moment (SFC, ORCHESTRA): both castle maps share the castle
    track, the fight music has no separate start, and every dungeon floor has the dungeon track."""
    def track(name: str) -> str:
        return join(folder, name)
    return {
        'intro_overture': track(overture),
        'intermezzo': track(intermezzo),
        'tantegel_castle_throne_room_music': track(castle),
        'tantegel_castle_courtyard_music': track(castle),
        'village_music': track(village),
        'overworld_music': track(overworld),
        'battle_music': track(fight),
        'regular_fight_music': track(fight),
        'end_boss_music': track(end_boss),
        'ending_music': track(ending),
        **{name: track(dungeon) for name in DUNGEON_FLOOR_MUSIC_NAMES},
    }


@cache
def music_paths(chosen: Soundtrack) -> dict[str, str]:
    """The music files for the MUSIC setting (SOUNDTRACK, src/soundtrack.py): the NES's, the Super Famicom's or the
    orchestral soundtrack. The jingles aren't here: every soundtrack uses the NES's (Directories)."""
    sound_dir = join(data_path(), 'sound')
    sfx_dir = join(sound_dir, 'sfx')
    music_dir = join(sound_dir, 'music')
    if chosen is Soundtrack.ORCHESTRA:
        return _arrangement_paths(
            join(music_dir, SOUNDTRACK_FOLDERS[Soundtrack.ORCHESTRA]),
            overture='01 Overture March (London Philharmonic Orchestra Version).mp3',
            # The orchestral album has no Intermezzo: the Android/iOS version's
            intermezzo=join('Android_iOS', 'Dragon Quest (Android_iOS) - Intermezzo.mp3'),
            castle='02 Chateau Ladutorm.mp3', village='03 People.mp3', overworld='04 Unknown World.mp3',
            fight='05 Fight.mp3', dungeon='06 Dungeon.mp3', end_boss='07 King Dragon.mp3', ending='08 Finale.mp3')
    if chosen is Soundtrack.SFC:
        # The Super Famicom remake's tracks. "18 ME Sound Collection.mp3", its jingles in one recording, is kept for
        # when it is split into the jingles; until then the SFC soundtrack uses the NES's, as the orchestral one does.
        return _arrangement_paths(
            join(music_dir, SOUNDTRACK_FOLDERS[Soundtrack.SFC]),
            overture='09 Overture March (Original Game Sound).mp3', intermezzo='10 Intermezzo (SFC Version).mp3',
            castle='11 Chateau Ladutorm (SFC Version).mp3', village='12 People (SFC Version).mp3',
            overworld='13 Unknown World (SFC Version).mp3', fight='14 Fight (SFC Version).mp3',
            dungeon='15 Dungeon (SFC Version).mp3', end_boss='16 King Dragon (SFC Version).mp3',
            ending='17 Finale (SFC Version).mp3')
    nes_dir = join(music_dir, SOUNDTRACK_FOLDERS[Soundtrack.NES])
    village = join(nes_dir, '04 Dragon Quest 1 - Peaceful Village.mp3')
    return {
        'intro_overture': join(nes_dir, '01 Dragon Quest 1 - Intro ~ Overture.mp3'),
        'intermezzo': village,
        'tantegel_castle_throne_room_music': join(nes_dir, '02 Dragon Quest 1 - Tantegel Castle.mp3'),
        'tantegel_castle_courtyard_music': join(nes_dir, '03 Dragon Quest 1 - Tantegel Castle (Lower).mp3'),
        'village_music': village,
        'overworld_music': join(nes_dir, '05 Dragon Quest 1 - Kingdom of Alefgard.mp3'),
        **{f'dungeon_floor_{floor}_music': join(nes_dir, f'{floor + 5:02} Dragon Quest 1 - Dark Dungeon ~ Floor {floor}.mp3')
           for floor in range(1, 9)},
        # NES MSC_ENTR_FGHT, the music every fight but the last starts with (InitFight): the 'monster draws near' run
        # (SQ1EntFight), which then falls through into the fight loop (SQ1Fight)
        'battle_music': join(nes_dir, '14 Dragon Quest 1 - A Monster Draws Near.mp3'),
        # NES MSC_REG_FGHT, the fight loop on its own: what the fight music restarts with after the flute, the harp or
        # a cursed item (ChkUseFlute, ChkUseHarp, ChkUseBelt, ChkUseNecklace), and what follows MSC_ENTR_FGHT
        'regular_fight_music': join(sfx_dir, '24 Dragon Quest 1 - Monster Battle.mp3'),
        'end_boss_music': join(nes_dir, '15 Dragon Quest 1 - The Dragon Lord.mp3'),
        'ending_music': join(nes_dir, "16 Dragon Quest 1 - Hero's Fanfare.mp3"),  # NES MSC_END
    }


MUSIC_NAMES = tuple(music_paths(Soundtrack.NES))
# The music a map can have: not the title's overture or the intermezzo (which, on the NES, is the village music's file,
# so a village's music would otherwise be taken for it)
MAP_MUSIC_NAMES = tuple(name for name in MUSIC_NAMES if name not in ('intro_overture', 'intermezzo'))


def music_name(path: str) -> str | None:
    """Which map music a file is (its Directories attribute), with any MUSIC setting; None if it's no map music."""
    for chosen in SOUNDTRACKS:
        paths = music_paths(chosen)
        for name in MAP_MUSIC_NAMES:
            if paths[name] == path:
                return name
    return None


class Directories:
    # The music (music_paths): read from the config each time, so the MUSIC option (SOUNDTRACK) switches
    # every one at once, in every Directories the game holds
    intro_overture: str
    intermezzo: str
    tantegel_castle_throne_room_music: str
    tantegel_castle_courtyard_music: str
    village_music: str
    overworld_music: str
    battle_music: str
    regular_fight_music: str
    end_boss_music: str
    ending_music: str
    dungeon_floor_1_music: str
    dungeon_floor_2_music: str
    dungeon_floor_3_music: str
    dungeon_floor_4_music: str
    dungeon_floor_5_music: str
    dungeon_floor_6_music: str
    dungeon_floor_7_music: str
    dungeon_floor_8_music: str

    def __init__(self, config):
        self.config = config

        # menu
        data_dir = data_path()
        sound_dir = join(data_dir, 'sound')
        sfx_dir = join(sound_dir, 'sfx')
        # SAVE_DIR redirects saving, e.g. for a game started from a checkpoint (src/checkpoints.py). Otherwise src/saves
        # from source, or a per-user folder in a PyInstaller build (src/paths.py)
        self.save_dir = config.get('SAVE_DIR') or default_save_dir()
        self.text_beep_sfx = join(sfx_dir, 'text_beep.wav')
        # MSC_DEATH, a music clip like the ones below (PlayerHasDied / InitDeathSequence: InitMusicSFX, WaitForMusicEnd)
        self.death_music = join(sfx_dir, '20 Dragon Quest 1 - Thou Hast Died.mp3')
        # NES MSC_INN ($15), the inn's jingle (BuyInnStay). The soundtrack calls it "Special Item"; it is the track
        # between Thou Hast Died (MSC_DEATH, $14) and Princess Gwaelin's Love (MSC_PRNCS_LOVE, $16), and the only place
        # the game plays it is the inn. Like every jingle, it is the NES's with every soundtrack.
        self.inn_music = join(sfx_dir, '21 Dragon Quest 1 - Special Item.mp3')
        # The NES plays these clips as music, not as sound effects (InitMusicSFX with an MSC_ number, then usually
        # WaitForMusicEnd), so they go through MusicPlayer.play_clip / play_until_end, never Sound.play_sound.
        # MSC_PRNCS_LOVE
        self.princess_gwaelins_love_music = join(sfx_dir, "22 Dragon Quest 1 - Princess Gwaelin's Love.mp3")
        self.victory_music = join(sfx_dir, '25 Dragon Quest 1 - Victory.mp3')  # MSC_VICTORY
        self.level_up_music = join(sfx_dir, '26 Dragon Quest 1 - Improvement.mp3')  # MSC_LEVEL_UP
        # NES SFX_STAIRS (Bank01 StairsSFX, $839E: 4 bursts 12 frames apart), the one sound for every map change with
        # sound (MapChngWithSound), up or down. The soundtrack's "Stairs Down" is a different sound: RunSFX ($83C2, 6
        # bursts 3 frames apart), SFX_RUN, played when the hero (PlyrRun) or an enemy (LEFCB) runs away.
        self.stairs_sfx = join(sfx_dir, '29 Dragon Quest 1 - Stairs Up.mp3')
        self.run_away_sfx = join(sfx_dir, '30 Dragon Quest 1 - Stairs Down.mp3')
        self.swamp_sfx = join(sfx_dir, '31 Dragon Quest 1 - Swamp.mp3')
        self.menu_button_sfx = join(sfx_dir, '32 Dragon Quest 1 - Menu Button.mp3')
        self.confirmation_sfx = join(sfx_dir, '33 Dragon Quest 1 - Confirmation.mp3')
        self.hit_sfx = join(sfx_dir, '34 Dragon Quest 1 - Hit.mp3')
        self.excellent_move_sfx = join(sfx_dir, '35 Dragon Quest 1 - Excellent Move.mp3')
        self.attack_sfx = join(sfx_dir, '36 Dragon Quest 1 - Attack.mp3')
        self.receive_damage_sfx = join(sfx_dir, '37 Dragon Quest 1 - Receive Damage.mp3')
        self.receive_damage_2_sfx = join(sfx_dir, '38 Dragon Quest 1 - Receive Damage (2).mp3')
        self.prepare_attack_sfx = join(sfx_dir, '39 Dragon Quest 1 - Prepare to Attack.mp3')
        self.missed_sfx = join(sfx_dir, '40 Dragon Quest 1 - Missed!.mp3')
        self.missed_2_sfx = join(sfx_dir, '41 Dragon Quest 1 - Missed! (2).mp3')
        self.spell_sfx = join(sfx_dir, '43 Dragon Quest 1 - Cast A Spell.mp3')
        self.open_treasure_sfx = join(sfx_dir, '44 Dragon Quest 1 - Open Treasure.mp3')
        self.open_door_sfx = join(sfx_dir, '45 Dragon Quest 1 - Open Door.mp3')
        self.breathe_fire_sfx = join(sfx_dir, '46 Dragon Quest 1 - Breathe Fire.mp3')

        # items

        # NES SFX_RADIANT (Bank01 RadiantSFX, $84A0: noise at 4 pitches for 3+2+1+2 = 8 frames, about 0.13 s), played
        # by RADIANT (LDA89) and a torch (LDD4B). The soundtrack has no track for it, so tools/make_radiant_sfx.py
        # renders it from that data with an emulated noise channel.
        self.radiant_sfx = join(sfx_dir, 'radiant.wav')
        # music clips too (see victory_music)
        self.harp_music = join(sfx_dir, '17 Dragon Quest 1 - Silver Harp.mp3')  # MSC_SILV_HARP
        self.flute_music = join(sfx_dir, '18 Dragon Quest 1 - Fairy Flute.mp3')  # MSC_FRY_FLUTE
        self.cursed_music = join(sfx_dir, '23 Dragon Quest 1 - Cursed!.mp3')  # MSC_CURSED
        self.rainbow_bridge_music = join(sfx_dir, '19 Dragon Quest 1 - Rainbow Bridge.mp3')  # MSC_RNBW_BRDG
        self.barrier_sfx = join(sfx_dir, '27 Dragon Quest 1 - Barrier.mp3')  # SFX_FFDAMAGE (force field damage)
        self.wyvern_wing_sfx = join(sfx_dir, '28 Dragon Quest 1 - Wyvern Wing.mp3')  # SFX_WVRN_WNG (RETURN, Wings)


        # movement

        self.bump_sfx = join(sfx_dir, '42 Dragon Quest 1 - Bumping into Walls.mp3')
        self.open_treasure_sfx = join(sfx_dir, '44 Dragon Quest 1 - Open Treasure.mp3')
        self.open_door_sfx = join(sfx_dir, '45 Dragon Quest 1 - Open Door.mp3')

        # Files/Directories: where Graphics.get_image looks for an image it can't find at its path
        self.root_project_path = project_root()


        self.IMAGES_DIR = join(data_dir, 'images')
        self.MAP_TILES_PATH = join(self.IMAGES_DIR, 'tileset.png')
        self.UNARMED_HERO_PATH = join(self.IMAGES_DIR, 'unarmed_hero.png')
        self.UNARMED_HERO_WITH_SHIELD_PATH = join(self.IMAGES_DIR, 'unarmed_hero_with_shield.png')
        self.ARMED_HERO_PATH = join(self.IMAGES_DIR, 'armed_hero.png')
        self.ARMED_HERO_WITH_SHIELD_PATH = join(self.IMAGES_DIR, 'armed_hero_with_shield.png')
        self.HERO_CARRYING_PRINCESS_PATH = join(self.IMAGES_DIR, 'hero_carrying_princess.png')
        self.KING_LORIK_PATH = join(self.IMAGES_DIR, 'king_lorik.png')
        self.GUARD_PATH = join(self.IMAGES_DIR, 'guard.png')
        self.MAN_PATH = join(self.IMAGES_DIR, 'man.png')
        self.WOMAN_PATH = join(self.IMAGES_DIR, 'woman.png')
        self.WISE_MAN_PATH = join(self.IMAGES_DIR, 'wise_man.png')
        self.SOLDIER_PATH = join(self.IMAGES_DIR, 'soldier.png')
        self.MERCHANT_PATH = join(self.IMAGES_DIR, 'merchant.png')
        self.PRINCESS_GWAELIN_PATH = join(self.IMAGES_DIR, 'princess_gwaelin.png')
        self.DRAGONLORD_PATH = join(self.IMAGES_DIR, 'dragonlord.png')
        self.INTRO_BANNER_PATH = join(self.IMAGES_DIR, 'intro_banner', 'intro_banner.png')
        self.INTRO_BANNER_WITH_DRAGON_PATH = join(self.IMAGES_DIR, 'intro_banner', 'intro_banner_with_dragon.png')
        self.ICON_PATH = join(self.IMAGES_DIR, 'walking_hero.gif')
        self.BATTLE_BACKGROUND_PATH = join(self.IMAGES_DIR, 'battle_background.png')
        self.IMAGES_ENEMIES_DIR = join(self.IMAGES_DIR, 'enemies')

        # menus/windows

        self.DIALOG_BOX_BACKGROUND_PATH = join(self.IMAGES_DIR, 'dialog_box_background.png')
        self.COMMAND_MENU_BACKGROUND_PATH = join(self.IMAGES_DIR, 'command_menu_background.png')
        self.COMMAND_MENU_STATIC_BACKGROUND_PATH = join(self.IMAGES_DIR, 'command_menu_static.png')
        self.CONFIRMATION_BACKGROUND_PATH = join(self.IMAGES_DIR, 'confirmation.png')
        self.CONFIRMATION_YES_BACKGROUND_PATH = join(self.IMAGES_DIR, 'confirmation_yes.png')
        self.CONFIRMATION_NO_BACKGROUND_PATH = join(self.IMAGES_DIR, 'confirmation_no.png')
        self.HOVERING_STATS_BACKGROUND_PATH = join(self.IMAGES_DIR, 'hovering_stats_window.png')
        self.STATUS_WINDOW_BACKGROUND_PATH = join(self.IMAGES_DIR, 'status_window_background.png')

        images_menus_dir = join(self.IMAGES_DIR, 'menus')
        images_menus_item_menu_dir = join(images_menus_dir, 'item_menu')
        item_menu_1_background_path = join(images_menus_item_menu_dir, 'item_menu_background_1.png')
        item_menu_2_background_path = join(images_menus_item_menu_dir, 'item_menu_background_2.png')
        item_menu_5_background_path = join(images_menus_item_menu_dir, 'item_menu_background_5.png')
        # The SPELL and ITEM windows: one background stretched to the number of entries (Graphics.create_window border)
        self.ITEM_MENU_BACKGROUND_PATH = item_menu_5_background_path
        self.item_menu_background_lookup = {1: item_menu_1_background_path,
                                            2: item_menu_2_background_path,
                                            # TODO: need to implement more backgrounds
                                            3: item_menu_2_background_path,
                                            4: item_menu_2_background_path,
                                            5: item_menu_5_background_path,
                                            6: item_menu_5_background_path,
                                            7: item_menu_5_background_path,
                                            8: item_menu_5_background_path,
                                            9: item_menu_5_background_path,
                                            10: item_menu_5_background_path,
                                            }

        # name selection

        name_selection_dir = join(images_menus_dir, 'name_selection')

        self.NAME_SELECTION_UPPER_A = join(name_selection_dir, '0_upper_A.png')
        self.NAME_SELECTION_UPPER_B = join(name_selection_dir, '1_upper_B.png')
        self.NAME_SELECTION_UPPER_C = join(name_selection_dir, '2_upper_C.png')
        self.NAME_SELECTION_UPPER_D = join(name_selection_dir, '3_upper_D.png')
        self.NAME_SELECTION_UPPER_E = join(name_selection_dir, '4_upper_E.png')
        self.NAME_SELECTION_UPPER_F = join(name_selection_dir, '5_upper_F.png')
        self.NAME_SELECTION_UPPER_G = join(name_selection_dir, '6_upper_G.png')
        self.NAME_SELECTION_UPPER_H = join(name_selection_dir, '7_upper_H.png')
        self.NAME_SELECTION_UPPER_I = join(name_selection_dir, '8_upper_I.png')
        self.NAME_SELECTION_UPPER_J = join(name_selection_dir, '9_upper_J.png')
        self.NAME_SELECTION_UPPER_K = join(name_selection_dir, '10_upper_K.png')
        self.NAME_SELECTION_UPPER_L = join(name_selection_dir, '11_upper_L.png')
        self.NAME_SELECTION_UPPER_M = join(name_selection_dir, '12_upper_M.png')
        self.NAME_SELECTION_UPPER_N = join(name_selection_dir, '13_upper_N.png')
        self.NAME_SELECTION_UPPER_O = join(name_selection_dir, '14_upper_O.png')
        self.NAME_SELECTION_UPPER_P = join(name_selection_dir, '15_upper_P.png')
        self.NAME_SELECTION_UPPER_Q = join(name_selection_dir, '16_upper_Q.png')
        self.NAME_SELECTION_UPPER_R = join(name_selection_dir, '17_upper_R.png')
        self.NAME_SELECTION_UPPER_S = join(name_selection_dir, '18_upper_S.png')
        self.NAME_SELECTION_UPPER_T = join(name_selection_dir, '19_upper_T.png')
        self.NAME_SELECTION_UPPER_U = join(name_selection_dir, '20_upper_U.png')
        self.NAME_SELECTION_UPPER_V = join(name_selection_dir, '21_upper_V.png')
        self.NAME_SELECTION_UPPER_W = join(name_selection_dir, '22_upper_W.png')
        self.NAME_SELECTION_UPPER_X = join(name_selection_dir, '23_upper_X.png')
        self.NAME_SELECTION_UPPER_Y = join(name_selection_dir, '24_upper_Y.png')
        self.NAME_SELECTION_UPPER_Z = join(name_selection_dir, '25_upper_Z.png')
        self.NAME_SELECTION_HYPHEN = join(name_selection_dir, '26_-.png')
        self.NAME_SELECTION_SINGLE_QUOTE = join(name_selection_dir, "27_'.png")
        self.NAME_SELECTION_EXCLAMATION_POINT = join(name_selection_dir, '28_!.png')
        self.NAME_SELECTION_QUESTION_MARK = join(name_selection_dir, '29_question_mark.png')
        self.NAME_SELECTION_OPEN_PARENTHESIS = join(name_selection_dir, '30_(.png')
        self.NAME_SELECTION_CLOSE_PARENTHESIS = join(name_selection_dir, '31_).png')
        self.NAME_SELECTION_SPACE = join(name_selection_dir, '32_space.png')
        self.NAME_SELECTION_LOWER_A = join(name_selection_dir, '33_a.png')
        self.NAME_SELECTION_LOWER_B = join(name_selection_dir, '34_b.png')
        self.NAME_SELECTION_LOWER_C = join(name_selection_dir, '35_c.png')
        self.NAME_SELECTION_LOWER_D = join(name_selection_dir, '36_d.png')
        self.NAME_SELECTION_LOWER_E = join(name_selection_dir, '37_e.png')
        self.NAME_SELECTION_LOWER_F = join(name_selection_dir, '38_f.png')
        self.NAME_SELECTION_LOWER_G = join(name_selection_dir, '39_g.png')
        self.NAME_SELECTION_LOWER_H = join(name_selection_dir, '40_h.png')
        self.NAME_SELECTION_LOWER_I = join(name_selection_dir, '41_i.png')
        self.NAME_SELECTION_LOWER_J = join(name_selection_dir, '42_j.png')
        self.NAME_SELECTION_LOWER_K = join(name_selection_dir, '43_k.png')
        self.NAME_SELECTION_LOWER_L = join(name_selection_dir, '44_l.png')
        self.NAME_SELECTION_LOWER_M = join(name_selection_dir, '45_m.png')
        self.NAME_SELECTION_LOWER_N = join(name_selection_dir, '46_n.png')
        self.NAME_SELECTION_LOWER_O = join(name_selection_dir, '47_o.png')
        self.NAME_SELECTION_LOWER_P = join(name_selection_dir, '48_p.png')
        self.NAME_SELECTION_LOWER_Q = join(name_selection_dir, '49_q.png')
        self.NAME_SELECTION_LOWER_R = join(name_selection_dir, '50_r.png')
        self.NAME_SELECTION_LOWER_S = join(name_selection_dir, '51_s.png')
        self.NAME_SELECTION_LOWER_T = join(name_selection_dir, '52_t.png')
        self.NAME_SELECTION_LOWER_U = join(name_selection_dir, '53_u.png')
        self.NAME_SELECTION_LOWER_V = join(name_selection_dir, '54_v.png')
        self.NAME_SELECTION_LOWER_W = join(name_selection_dir, '55_w.png')
        self.NAME_SELECTION_LOWER_X = join(name_selection_dir, '56_x.png')
        self.NAME_SELECTION_LOWER_Y = join(name_selection_dir, '57_y.png')
        self.NAME_SELECTION_LOWER_Z = join(name_selection_dir, '58_z.png')
        self.NAME_SELECTION_COMMA = join(name_selection_dir, '59_,.png')
        self.NAME_SELECTION_PERIOD = join(name_selection_dir, '60_period.png')
        self.NAME_SELECTION_BACK = join(name_selection_dir, '61_BACK.png')
        self.NAME_SELECTION_END = join(name_selection_dir, '62_END.png')
        self.NAME_SELECTION_STATIC_IMAGE_LEN_0 = join(name_selection_dir, '63_static_image_len_0.png')
        self.NAME_SELECTION_STATIC_IMAGE_LEN_1 = join(name_selection_dir, '64_static_image_len_1.png')
        self.NAME_SELECTION_STATIC_IMAGE_LEN_2 = join(name_selection_dir, '65_static_image_len_2.png')
        self.NAME_SELECTION_STATIC_IMAGE_LEN_3 = join(name_selection_dir, '66_static_image_len_3.png')
        self.NAME_SELECTION_STATIC_IMAGE_LEN_4 = join(name_selection_dir, '67_static_image_len_4.png')
        self.NAME_SELECTION_STATIC_IMAGE_LEN_5 = join(name_selection_dir, '68_static_image_len_5.png')
        self.NAME_SELECTION_STATIC_IMAGE_LEN_6 = join(name_selection_dir, '69_static_image_len_6.png')
        self.NAME_SELECTION_STATIC_IMAGE_LEN_7 = join(name_selection_dir, '70_static_image_len_7.png')
        self.NAME_SELECTION_STATIC_IMAGE_LEN_8 = join(name_selection_dir, '71_static_image_len_8.png')

        # shops

        # The weapon and armor shops' inventory windows (ShopInvDat), NES screenshots: the game generates the window
        # (src/windows.py shop_inventory_layout), and tests compare it with these, pixel for pixel. Next to each one,
        # <name>_<item>.png is the same window with the cursor at that item.
        images_shops_dir = join(self.IMAGES_DIR, 'shops')
        self.BRECCONARY_WEAPONS_SHOP_PATH = join(images_shops_dir, 'brecconary', 'weapons', 'brecconary_shop.png')
        self.GARINHAM_WEAPONS_SHOP_PATH = join(images_shops_dir, 'garinham', 'weapons', 'garinham_shop.png')
        self.KOL_WEAPONS_SHOP_PATH = join(images_shops_dir, 'kol', 'weapons', 'kol_shop.png')
        self.RIMULDAR_WEAPONS_SHOP_PATH = join(images_shops_dir, 'rimuldar', 'weapons', 'rimuldar_shop.png')
        self.CANTLIN_WEAPONS_SHOP_NORTH_PATH = join(images_shops_dir, 'cantlin', 'weapons', 'north',
                                                    'cantlin_shop_north.png')
        self.CANTLIN_WEAPONS_SHOP_SOUTH_PATH = join(images_shops_dir, 'cantlin', 'weapons', 'south',
                                                    'cantlin_shop_south.png')

        # battle menu
        battle_menu_dir = join(images_menus_dir, 'battle_menu')

        self.BATTLE_MENU_FIGHT_PATH = join(battle_menu_dir, 'battle_menu_fight.png')
        self.BATTLE_MENU_SPELL_PATH = join(battle_menu_dir, 'battle_menu_spell.png')
        self.BATTLE_MENU_ITEM_PATH = join(battle_menu_dir, 'battle_menu_item.png')
        self.BATTLE_MENU_RUN_PATH = join(battle_menu_dir, 'battle_menu_run.png')
        self.BATTLE_MENU_STATIC_PATH = join(battle_menu_dir, 'battle_menu_static.png')

        # Fonts

        font.init()

        fonts_dir = join(data_dir, 'fonts')
        self.DRAGON_QUEST_FONT_PATH = join(fonts_dir, 'dragon-quest.ttf')

        self.DRAGON_QUEST_FONT = font.Font(self.DRAGON_QUEST_FONT_PATH, 15)

        self.SMB_FONT_PATH = join(fonts_dir, 'super_mario_bros__nes_font.ttf')
        self.SMB_FONT = font.Font(self.SMB_FONT_PATH, 15)

        self.UNIFONT_PATH = join(fonts_dir, 'unifont.ttf')


def _music_property(name: str) -> property:
    return property(lambda directories: music_paths(soundtrack(directories.config))[name])


for _name in MUSIC_NAMES:
    setattr(Directories, _name, _music_property(_name))
