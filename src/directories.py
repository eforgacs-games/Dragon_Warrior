import os
from os.path import join, dirname, realpath

from pygame import font


class Directories:

    def __init__(self, config):
        self.config = config

        # menu
        DATA_DIR = join(dirname(dirname(realpath(__file__))), 'data')
        SOUND_DIR = join(DATA_DIR, 'sound')
        SFX_DIR = join(SOUND_DIR, 'sfx')
        self.text_beep_sfx = join(SFX_DIR, 'text_beep.wav')
        self.death_sfx = join(SFX_DIR, '20 Dragon Quest 1 - Thou Hast Died.mp3')
        self.special_item_sfx = join(SFX_DIR, '21 Dragon Quest 1 - Special Item.mp3')
        self.victory_sfx = join(SFX_DIR, '25 Dragon Quest 1 - Victory.mp3')
        self.improvement_sfx = join(SFX_DIR, '26 Dragon Quest 1 - Improvement.mp3')
        self.stairs_up_sfx = join(SFX_DIR, '29 Dragon Quest 1 - Stairs Up.mp3')
        self.stairs_down_sfx = join(SFX_DIR, '30 Dragon Quest 1 - Stairs Down.mp3')
        self.swamp_sfx = join(SFX_DIR, '31 Dragon Quest 1 - Swamp.mp3')
        self.menu_button_sfx = join(SFX_DIR, '32 Dragon Quest 1 - Menu Button.mp3')
        self.confirmation_sfx = join(SFX_DIR, '33 Dragon Quest 1 - Confirmation.mp3')
        self.hit_sfx = join(SFX_DIR, '34 Dragon Quest 1 - Hit.mp3')
        self.excellent_move_sfx = join(SFX_DIR, '35 Dragon Quest 1 - Excellent Move.mp3')
        self.attack_sfx = join(SFX_DIR, '36 Dragon Quest 1 - Attack.mp3')
        self.receive_damage_sfx = join(SFX_DIR, '37 Dragon Quest 1 - Receive Damage.mp3')
        self.receive_damage_2_sfx = join(SFX_DIR, '38 Dragon Quest 1 - Receive Damage (2).mp3')
        self.prepare_attack_sfx = join(SFX_DIR, '39 Dragon Quest 1 - Prepare to Attack.mp3')
        self.missed_sfx = join(SFX_DIR, '40 Dragon Quest 1 - Missed!.mp3')
        self.missed_2_sfx = join(SFX_DIR, '41 Dragon Quest 1 - Missed! (2).mp3')
        self.spell_sfx = join(SFX_DIR, '43 Dragon Quest 1 - Cast A Spell.mp3')
        self.open_treasure_sfx = join(SFX_DIR, '44 Dragon Quest 1 - Open Treasure.mp3')
        self.open_door_sfx = join(SFX_DIR, '45 Dragon Quest 1 - Open Door.mp3')
        self.breathe_fire_sfx = join(SFX_DIR, '46 Dragon Quest 1 - Breathe Fire.mp3')

        # items

        self.torch_sfx = join(SFX_DIR, 'torch.wav')

        # movement

        self.bump_sfx = join(SFX_DIR, '42 Dragon Quest 1 - Bumping into Walls.mp3')
        self.open_treasure_sfx = join(SFX_DIR, '44 Dragon Quest 1 - Open Treasure.mp3')
        self.open_door_sfx = join(SFX_DIR, '45 Dragon Quest 1 - Open Door.mp3')

        # Files/Directories
        self.root_project_path = os.getcwd().split('DragonWarrior', 1)[0]

        # Music

        _music_library = {}
        MUSIC_DIR = join(SOUND_DIR, 'music')

        if self.config["ORCHESTRA_MUSIC_ENABLED"]:
            self.intro_overture = join(MUSIC_DIR, 'orchestra',
                                       '01 Overture March (London Philharmonic Orchestra Version).mp3')
            self.intermezzo = join(MUSIC_DIR, 'orchestra', 'Android_iOS', 'Dragon Quest (Android_iOS) - Intermezzo.mp3')
            self.tantegel_castle_throne_room_music = join(MUSIC_DIR, 'orchestra', '02 Chateau Ladutorm.mp3')
            self.tantegel_castle_courtyard_music = join(MUSIC_DIR, 'orchestra', '02 Chateau Ladutorm.mp3')
            self.village_music = join(MUSIC_DIR, 'orchestra', '03 People.mp3')
            self.overworld_music = join(MUSIC_DIR, 'orchestra', '04 Unknown World.mp3')
            self.battle_music = join(MUSIC_DIR, 'orchestra', '05 Fight.mp3')
            self.dungeon_floor_1_music = \
                self.dungeon_floor_2_music = \
                self.dungeon_floor_3_music = \
                self.dungeon_floor_4_music = \
                self.dungeon_floor_5_music = \
                self.dungeon_floor_6_music = \
                self.dungeon_floor_7_music = \
                self.dungeon_floor_8_music = join(MUSIC_DIR, 'orchestra', '06 Dungeon.mp3')

        else:
            self.intro_overture = join(MUSIC_DIR, 'NES', '01 Dragon Quest 1 - Intro ~ Overture.mp3')
            self.tantegel_castle_throne_room_music = join(MUSIC_DIR, 'NES', '02 Dragon Quest 1 - Tantegel Castle.mp3')
            self.tantegel_castle_courtyard_music = join(MUSIC_DIR, 'NES',
                                                        '03 Dragon Quest 1 - Tantegel Castle (Lower).mp3')
            self.village_music = join(MUSIC_DIR, 'NES', '04 Dragon Quest 1 - Peaceful Village.mp3')
            self.intermezzo = self.village_music
            self.overworld_music = join(MUSIC_DIR, 'NES', '05 Dragon Quest 1 - Kingdom of Alefgard.mp3')
            self.dungeon_floor_1_music = join(MUSIC_DIR, 'NES', '06 Dragon Quest 1 - Dark Dungeon ~ Floor 1.mp3')
            self.dungeon_floor_2_music = join(MUSIC_DIR, 'NES', '07 Dragon Quest 1 - Dark Dungeon ~ Floor 2.mp3')
            self.dungeon_floor_3_music = join(MUSIC_DIR, 'NES', '08 Dragon Quest 1 - Dark Dungeon ~ Floor 3.mp3')
            self.dungeon_floor_4_music = join(MUSIC_DIR, 'NES', '09 Dragon Quest 1 - Dark Dungeon ~ Floor 4.mp3')
            self.dungeon_floor_5_music = join(MUSIC_DIR, 'NES', '10 Dragon Quest 1 - Dark Dungeon ~ Floor 5.mp3')
            self.dungeon_floor_6_music = join(MUSIC_DIR, 'NES', '11 Dragon Quest 1 - Dark Dungeon ~ Floor 6.mp3')
            self.dungeon_floor_7_music = join(MUSIC_DIR, 'NES', '12 Dragon Quest 1 - Dark Dungeon ~ Floor 7.mp3')
            self.dungeon_floor_8_music = join(MUSIC_DIR, 'NES', '13 Dragon Quest 1 - Dark Dungeon ~ Floor 8.mp3')
            self.battle_music = join(MUSIC_DIR, 'NES', '14 Dragon Quest 1 - A Monster Draws Near.mp3')

        self.IMAGES_DIR = join(DATA_DIR, 'images')
        self.MAP_TILES_PATH = join(self.IMAGES_DIR, 'tileset.png')
        self.UNARMED_HERO_PATH = join(self.IMAGES_DIR, 'unarmed_hero.png')
        self.UNARMED_HERO_WITH_SHIELD_PATH = join(self.IMAGES_DIR, 'unarmed_hero_with_shield.png')
        self.ARMED_HERO_PATH = join(self.IMAGES_DIR, 'armed_hero.png')
        self.ARMED_HERO_WITH_SHIELD_PATH = join(self.IMAGES_DIR, 'armed_hero_with_shield.png')
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

        IMAGES_MENUS_DIR = join(self.IMAGES_DIR, 'menus')
        IMAGES_MENUS_ITEM_MENU_DIR = join(IMAGES_MENUS_DIR, 'item_menu')
        ITEM_MENU_1_BACKGROUND_PATH = join(IMAGES_MENUS_ITEM_MENU_DIR, 'item_menu_background_1.png')
        ITEM_MENU_2_BACKGROUND_PATH = join(IMAGES_MENUS_ITEM_MENU_DIR, 'item_menu_background_2.png')
        ITEM_MENU_5_BACKGROUND_PATH = join(IMAGES_MENUS_ITEM_MENU_DIR, 'item_menu_background_5.png')
        self.item_menu_background_lookup = {1: ITEM_MENU_1_BACKGROUND_PATH,
                                            2: ITEM_MENU_2_BACKGROUND_PATH,
                                            # TODO: need to implement more backgrounds
                                            3: ITEM_MENU_2_BACKGROUND_PATH,
                                            4: ITEM_MENU_2_BACKGROUND_PATH,
                                            5: ITEM_MENU_5_BACKGROUND_PATH,
                                            6: ITEM_MENU_5_BACKGROUND_PATH,
                                            7: ITEM_MENU_5_BACKGROUND_PATH,
                                            8: ITEM_MENU_5_BACKGROUND_PATH,
                                            9: ITEM_MENU_5_BACKGROUND_PATH,
                                            10: ITEM_MENU_5_BACKGROUND_PATH,
                                            }

        # main menu

        # begin quest

        BEGIN_QUEST_DIR = join(IMAGES_MENUS_DIR, 'begin_quest')
        self.BEGIN_QUEST_PATH = join(BEGIN_QUEST_DIR, 'begin_quest.png')
        self.BEGIN_QUEST_SELECTED_PATH = join(BEGIN_QUEST_DIR, 'begin_quest_selected.png')

        # adventure log

        ADVENTURE_LOG_DIR = join(IMAGES_MENUS_DIR, 'adventure_log')
        self.ADVENTURE_LOG_PATH = join(ADVENTURE_LOG_DIR, 'adventure_log.png')
        self.ADVENTURE_LOG_1_PATH = join(ADVENTURE_LOG_DIR, 'adventure_log_1.png')
        self.ADVENTURE_LOG_2_PATH = join(ADVENTURE_LOG_DIR, 'adventure_log_2.png')
        self.ADVENTURE_LOG_3_PATH = join(ADVENTURE_LOG_DIR, 'adventure_log_3.png')

        # name selection

        NAME_SELECTION_DIR = join(IMAGES_MENUS_DIR, 'name_selection')

        self.NAME_SELECTION_UPPER_A = join(NAME_SELECTION_DIR, '0_upper_A.png')
        self.NAME_SELECTION_UPPER_B = join(NAME_SELECTION_DIR, '1_upper_B.png')
        self.NAME_SELECTION_UPPER_C = join(NAME_SELECTION_DIR, '2_upper_C.png')
        self.NAME_SELECTION_UPPER_D = join(NAME_SELECTION_DIR, '3_upper_D.png')
        self.NAME_SELECTION_UPPER_E = join(NAME_SELECTION_DIR, '4_upper_E.png')
        self.NAME_SELECTION_UPPER_F = join(NAME_SELECTION_DIR, '5_upper_F.png')
        self.NAME_SELECTION_UPPER_G = join(NAME_SELECTION_DIR, '6_upper_G.png')
        self.NAME_SELECTION_UPPER_H = join(NAME_SELECTION_DIR, '7_upper_H.png')
        self.NAME_SELECTION_UPPER_I = join(NAME_SELECTION_DIR, '8_upper_I.png')
        self.NAME_SELECTION_UPPER_J = join(NAME_SELECTION_DIR, '9_upper_J.png')
        self.NAME_SELECTION_UPPER_K = join(NAME_SELECTION_DIR, '10_upper_K.png')
        self.NAME_SELECTION_UPPER_L = join(NAME_SELECTION_DIR, '11_upper_L.png')
        self.NAME_SELECTION_UPPER_M = join(NAME_SELECTION_DIR, '12_upper_M.png')
        self.NAME_SELECTION_UPPER_N = join(NAME_SELECTION_DIR, '13_upper_N.png')
        self.NAME_SELECTION_UPPER_O = join(NAME_SELECTION_DIR, '14_upper_O.png')
        self.NAME_SELECTION_UPPER_P = join(NAME_SELECTION_DIR, '15_upper_P.png')
        self.NAME_SELECTION_UPPER_Q = join(NAME_SELECTION_DIR, '16_upper_Q.png')
        self.NAME_SELECTION_UPPER_R = join(NAME_SELECTION_DIR, '17_upper_R.png')
        self.NAME_SELECTION_UPPER_S = join(NAME_SELECTION_DIR, '18_upper_S.png')
        self.NAME_SELECTION_UPPER_T = join(NAME_SELECTION_DIR, '19_upper_T.png')
        self.NAME_SELECTION_UPPER_U = join(NAME_SELECTION_DIR, '20_upper_U.png')
        self.NAME_SELECTION_UPPER_V = join(NAME_SELECTION_DIR, '21_upper_V.png')
        self.NAME_SELECTION_UPPER_W = join(NAME_SELECTION_DIR, '22_upper_W.png')
        self.NAME_SELECTION_UPPER_X = join(NAME_SELECTION_DIR, '23_upper_X.png')
        self.NAME_SELECTION_UPPER_Y = join(NAME_SELECTION_DIR, '24_upper_Y.png')
        self.NAME_SELECTION_UPPER_Z = join(NAME_SELECTION_DIR, '25_upper_Z.png')
        self.NAME_SELECTION_HYPHEN = join(NAME_SELECTION_DIR, '26_-.png')
        self.NAME_SELECTION_SINGLE_QUOTE = join(NAME_SELECTION_DIR, "27_'.png")
        self.NAME_SELECTION_EXCLAMATION_POINT = join(NAME_SELECTION_DIR, '28_!.png')
        self.NAME_SELECTION_QUESTION_MARK = join(NAME_SELECTION_DIR, '29_question_mark.png')
        self.NAME_SELECTION_OPEN_PARENTHESIS = join(NAME_SELECTION_DIR, '30_(.png')
        self.NAME_SELECTION_CLOSE_PARENTHESIS = join(NAME_SELECTION_DIR, '31_).png')
        self.NAME_SELECTION_SPACE = join(NAME_SELECTION_DIR, '32_space.png')
        self.NAME_SELECTION_LOWER_A = join(NAME_SELECTION_DIR, '33_a.png')
        self.NAME_SELECTION_LOWER_B = join(NAME_SELECTION_DIR, '34_b.png')
        self.NAME_SELECTION_LOWER_C = join(NAME_SELECTION_DIR, '35_c.png')
        self.NAME_SELECTION_LOWER_D = join(NAME_SELECTION_DIR, '36_d.png')
        self.NAME_SELECTION_LOWER_E = join(NAME_SELECTION_DIR, '37_e.png')
        self.NAME_SELECTION_LOWER_F = join(NAME_SELECTION_DIR, '38_f.png')
        self.NAME_SELECTION_LOWER_G = join(NAME_SELECTION_DIR, '39_g.png')
        self.NAME_SELECTION_LOWER_H = join(NAME_SELECTION_DIR, '40_h.png')
        self.NAME_SELECTION_LOWER_I = join(NAME_SELECTION_DIR, '41_i.png')
        self.NAME_SELECTION_LOWER_J = join(NAME_SELECTION_DIR, '42_j.png')
        self.NAME_SELECTION_LOWER_K = join(NAME_SELECTION_DIR, '43_k.png')
        self.NAME_SELECTION_LOWER_L = join(NAME_SELECTION_DIR, '44_l.png')
        self.NAME_SELECTION_LOWER_M = join(NAME_SELECTION_DIR, '45_m.png')
        self.NAME_SELECTION_LOWER_N = join(NAME_SELECTION_DIR, '46_n.png')
        self.NAME_SELECTION_LOWER_O = join(NAME_SELECTION_DIR, '47_o.png')
        self.NAME_SELECTION_LOWER_P = join(NAME_SELECTION_DIR, '48_p.png')
        self.NAME_SELECTION_LOWER_Q = join(NAME_SELECTION_DIR, '49_q.png')
        self.NAME_SELECTION_LOWER_R = join(NAME_SELECTION_DIR, '50_r.png')
        self.NAME_SELECTION_LOWER_S = join(NAME_SELECTION_DIR, '51_s.png')
        self.NAME_SELECTION_LOWER_T = join(NAME_SELECTION_DIR, '52_t.png')
        self.NAME_SELECTION_LOWER_U = join(NAME_SELECTION_DIR, '53_u.png')
        self.NAME_SELECTION_LOWER_V = join(NAME_SELECTION_DIR, '54_v.png')
        self.NAME_SELECTION_LOWER_W = join(NAME_SELECTION_DIR, '55_w.png')
        self.NAME_SELECTION_LOWER_X = join(NAME_SELECTION_DIR, '56_x.png')
        self.NAME_SELECTION_LOWER_Y = join(NAME_SELECTION_DIR, '57_y.png')
        self.NAME_SELECTION_LOWER_Z = join(NAME_SELECTION_DIR, '58_z.png')
        self.NAME_SELECTION_COMMA = join(NAME_SELECTION_DIR, '59_,.png')
        self.NAME_SELECTION_PERIOD = join(NAME_SELECTION_DIR, '60_period.png')
        self.NAME_SELECTION_BACK = join(NAME_SELECTION_DIR, '61_BACK.png')
        self.NAME_SELECTION_END = join(NAME_SELECTION_DIR, '62_END.png')
        self.NAME_SELECTION_STATIC_IMAGE_LEN_0 = join(NAME_SELECTION_DIR, '63_static_image_len_0.png')
        self.NAME_SELECTION_STATIC_IMAGE_LEN_1 = join(NAME_SELECTION_DIR, '64_static_image_len_1.png')
        self.NAME_SELECTION_STATIC_IMAGE_LEN_2 = join(NAME_SELECTION_DIR, '65_static_image_len_2.png')
        self.NAME_SELECTION_STATIC_IMAGE_LEN_3 = join(NAME_SELECTION_DIR, '66_static_image_len_3.png')
        self.NAME_SELECTION_STATIC_IMAGE_LEN_4 = join(NAME_SELECTION_DIR, '67_static_image_len_4.png')
        self.NAME_SELECTION_STATIC_IMAGE_LEN_5 = join(NAME_SELECTION_DIR, '68_static_image_len_5.png')
        self.NAME_SELECTION_STATIC_IMAGE_LEN_6 = join(NAME_SELECTION_DIR, '69_static_image_len_6.png')
        self.NAME_SELECTION_STATIC_IMAGE_LEN_7 = join(NAME_SELECTION_DIR, '70_static_image_len_7.png')
        self.NAME_SELECTION_STATIC_IMAGE_LEN_8 = join(NAME_SELECTION_DIR, '71_static_image_len_8.png')

        # shops

        IMAGES_SHOPS_DIR = join(self.IMAGES_DIR, 'shops')

        IMAGES_SHOPS_BRECCONARY_DIR = join(IMAGES_SHOPS_DIR, 'brecconary')
        IMAGES_SHOPS_BRECCONARY_WEAPONS_DIR = join(IMAGES_SHOPS_BRECCONARY_DIR, 'weapons')
        self.BRECCONARY_WEAPONS_SHOP_PATH = join(IMAGES_SHOPS_BRECCONARY_WEAPONS_DIR, 'brecconary_shop.png')
        self.BRECCONARY_WEAPONS_SHOP_BAMBOO_POLE_PATH = join(IMAGES_SHOPS_BRECCONARY_WEAPONS_DIR,
                                                             'brecconary_shop_bamboo_pole.png')
        self.BRECCONARY_WEAPONS_SHOP_CLUB_PATH = join(IMAGES_SHOPS_BRECCONARY_WEAPONS_DIR, 'brecconary_shop_club.png')
        self.BRECCONARY_WEAPONS_SHOP_COPPER_SWORD_PATH = join(IMAGES_SHOPS_BRECCONARY_WEAPONS_DIR,
                                                              'brecconary_shop_copper_sword.png')
        self.BRECCONARY_WEAPONS_SHOP_CLOTHES_PATH = join(IMAGES_SHOPS_BRECCONARY_WEAPONS_DIR,
                                                         'brecconary_shop_clothes.png')
        self.BRECCONARY_WEAPONS_SHOP_LEATHER_ARMOR_PATH = join(IMAGES_SHOPS_BRECCONARY_WEAPONS_DIR,
                                                               'brecconary_shop_leather_armor.png')
        self.BRECCONARY_WEAPONS_SHOP_SMALL_SHIELD_PATH = join(IMAGES_SHOPS_BRECCONARY_WEAPONS_DIR,
                                                              'brecconary_shop_small_shield.png')

        IMAGES_SHOPS_GARINHAM_DIR = join(IMAGES_SHOPS_DIR, 'garinham')
        IMAGES_SHOPS_GARINHAM_WEAPONS_DIR = join(IMAGES_SHOPS_GARINHAM_DIR, 'weapons')
        self.GARINHAM_WEAPONS_SHOP_PATH = join(IMAGES_SHOPS_GARINHAM_WEAPONS_DIR, 'garinham_shop.png')
        self.GARINHAM_WEAPONS_SHOP_CHAIN_MAIL_PATH = join(IMAGES_SHOPS_GARINHAM_WEAPONS_DIR, 'garinham_shop_chain_mail.png')
        self.GARINHAM_WEAPONS_SHOP_CLUB_PATH = join(IMAGES_SHOPS_GARINHAM_WEAPONS_DIR, 'garinham_shop_club.png')
        self.GARINHAM_WEAPONS_SHOP_COPPER_SWORD_PATH = join(IMAGES_SHOPS_GARINHAM_WEAPONS_DIR, 'garinham_shop_copper_sword.png')
        self.GARINHAM_WEAPONS_SHOP_HALF_PLATE_PATH = join(IMAGES_SHOPS_GARINHAM_WEAPONS_DIR, 'garinham_shop_half_plate.png')
        self.GARINHAM_WEAPONS_SHOP_HAND_AXE_PATH = join(IMAGES_SHOPS_GARINHAM_WEAPONS_DIR, 'garinham_shop_hand_axe.png')
        self.GARINHAM_WEAPONS_SHOP_LARGE_SHIELD_PATH = join(IMAGES_SHOPS_GARINHAM_WEAPONS_DIR, 'garinham_shop_large_shield.png')
        self.GARINHAM_WEAPONS_SHOP_LEATHER_ARMOR_PATH = join(IMAGES_SHOPS_GARINHAM_WEAPONS_DIR, 'garinham_shop_leather_armor.png')

        IMAGES_SHOPS_KOL_DIR = join(IMAGES_SHOPS_DIR, 'kol')
        IMAGES_SHOPS_KOL_WEAPONS_DIR = join(IMAGES_SHOPS_KOL_DIR, 'weapons')
        self.KOL_WEAPONS_SHOP_PATH = join(IMAGES_SHOPS_KOL_WEAPONS_DIR, 'kol_shop.png')
        self.KOL_WEAPONS_SHOP_COPPER_SWORD_PATH = join(IMAGES_SHOPS_KOL_WEAPONS_DIR, 'kol_shop_copper_sword.png')
        self.KOL_WEAPONS_SHOP_HAND_AXE_PATH = join(IMAGES_SHOPS_KOL_WEAPONS_DIR, 'kol_shop_hand_axe.png')
        self.KOL_WEAPONS_SHOP_HALF_PLATE_PATH = join(IMAGES_SHOPS_KOL_WEAPONS_DIR, 'kol_shop_half_plate.png')
        self.KOL_WEAPONS_SHOP_FULL_PLATE_PATH = join(IMAGES_SHOPS_KOL_WEAPONS_DIR, 'kol_shop_full_plate.png')
        self.KOL_WEAPONS_SHOP_SMALL_SHIELD_PATH = join(IMAGES_SHOPS_KOL_WEAPONS_DIR, 'kol_shop_small_shield.png')

        IMAGES_SHOPS_RIMULDAR_DIR = join(IMAGES_SHOPS_DIR, 'rimuldar')
        IMAGES_SHOPS_RIMULDAR_WEAPONS_DIR = join(IMAGES_SHOPS_RIMULDAR_DIR, 'weapons')
        self.RIMULDAR_WEAPONS_SHOP_PATH = join(IMAGES_SHOPS_RIMULDAR_WEAPONS_DIR, 'rimuldar_shop.png')
        self.RIMULDAR_WEAPONS_SHOP_COPPER_SWORD_PATH = join(IMAGES_SHOPS_RIMULDAR_WEAPONS_DIR, 'rimuldar_shop_copper_sword.png')
        self.RIMULDAR_WEAPONS_SHOP_HAND_AXE_PATH = join(IMAGES_SHOPS_RIMULDAR_WEAPONS_DIR, 'rimuldar_shop_hand_axe.png')
        self.RIMULDAR_WEAPONS_SHOP_BROAD_SWORD_PATH = join(IMAGES_SHOPS_RIMULDAR_WEAPONS_DIR, 'rimuldar_shop_broad_sword.png')
        self.RIMULDAR_WEAPONS_SHOP_HALF_PLATE_PATH = join(IMAGES_SHOPS_RIMULDAR_WEAPONS_DIR, 'rimuldar_shop_half_plate.png')
        self.RIMULDAR_WEAPONS_SHOP_FULL_PLATE_PATH = join(IMAGES_SHOPS_RIMULDAR_WEAPONS_DIR, 'rimuldar_shop_full_plate.png')
        self.RIMULDAR_WEAPONS_SHOP_MAGIC_ARMOR_PATH = join(IMAGES_SHOPS_RIMULDAR_WEAPONS_DIR, 'rimuldar_shop_magic_armor.png')


        # battle menu
        BATTLE_MENU_DIR = join(IMAGES_MENUS_DIR, 'battle_menu')

        self.BATTLE_MENU_FIGHT_PATH = join(BATTLE_MENU_DIR, 'battle_menu_fight.png')
        self.BATTLE_MENU_SPELL_PATH = join(BATTLE_MENU_DIR, 'battle_menu_spell.png')
        self.BATTLE_MENU_ITEM_PATH = join(BATTLE_MENU_DIR, 'battle_menu_item.png')
        self.BATTLE_MENU_RUN_PATH = join(BATTLE_MENU_DIR, 'battle_menu_run.png')
        self.BATTLE_MENU_STATIC_PATH = join(BATTLE_MENU_DIR, 'battle_menu_static.png')

        # Fonts

        font.init()

        FONTS_DIR = join(DATA_DIR, 'fonts')
        self.DRAGON_QUEST_FONT_PATH = join(FONTS_DIR, 'dragon-quest.ttf')

        self.DRAGON_QUEST_FONT = font.Font(self.DRAGON_QUEST_FONT_PATH, 15)

        self.SMB_FONT_PATH = join(FONTS_DIR, 'super_mario_bros__nes_font.ttf')
        self.SMB_FONT = font.Font(self.SMB_FONT_PATH, 15)

        self.UNIFONT_PATH = join(FONTS_DIR, 'unifont.ttf')
