import os
from os.path import join, dirname, realpath

from pygame import font


class Directories:

    def __init__(self, config):
        self.config = config

        # menu
        src_dir = join(dirname(dirname(realpath(__file__))), 'src')
        data_dir = join(dirname(dirname(realpath(__file__))), 'data')
        sound_dir = join(data_dir, 'sound')
        sfx_dir = join(sound_dir, 'sfx')
        self.save_dir = join(src_dir, 'saves')
        self.text_beep_sfx = join(sfx_dir, 'text_beep.wav')
        self.death_sfx = join(sfx_dir, '20 Dragon Quest 1 - Thou Hast Died.mp3')
        self.special_item_sfx = join(sfx_dir, '21 Dragon Quest 1 - Special Item.mp3')
        self.princess_gwaelins_love_sfx = join(sfx_dir, "22 Dragon Quest 1 - Princess Gwaelin's Love.mp3")
        self.victory_sfx = join(sfx_dir, '25 Dragon Quest 1 - Victory.mp3')
        self.improvement_sfx = join(sfx_dir, '26 Dragon Quest 1 - Improvement.mp3')
        self.stairs_up_sfx = join(sfx_dir, '29 Dragon Quest 1 - Stairs Up.mp3')
        self.stairs_down_sfx = join(sfx_dir, '30 Dragon Quest 1 - Stairs Down.mp3')
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

        self.torch_sfx = join(sfx_dir, 'torch.wav')
        self.harp_sfx = join(sfx_dir, '17 Dragon Quest 1 - Silver Harp.mp3')


        # movement

        self.bump_sfx = join(sfx_dir, '42 Dragon Quest 1 - Bumping into Walls.mp3')
        self.open_treasure_sfx = join(sfx_dir, '44 Dragon Quest 1 - Open Treasure.mp3')
        self.open_door_sfx = join(sfx_dir, '45 Dragon Quest 1 - Open Door.mp3')

        # Files/Directories
        self.root_project_path = os.getcwd().split('DragonWarrior', 1)[0]

        # Music

        _music_library = {}
        music_dir = join(sound_dir, 'music')

        if self.config["ORCHESTRA_MUSIC_ENABLED"]:
            self.intro_overture = join(music_dir, 'orchestra',
                                       '01 Overture March (London Philharmonic Orchestra Version).mp3')
            self.intermezzo = join(music_dir, 'orchestra', 'Android_iOS', 'Dragon Quest (Android_iOS) - Intermezzo.mp3')
            self.tantegel_castle_throne_room_music = join(music_dir, 'orchestra', '02 Chateau Ladutorm.mp3')
            self.tantegel_castle_courtyard_music = join(music_dir, 'orchestra', '02 Chateau Ladutorm.mp3')
            self.village_music = join(music_dir, 'orchestra', '03 People.mp3')
            self.overworld_music = join(music_dir, 'orchestra', '04 Unknown World.mp3')
            self.battle_music = join(music_dir, 'orchestra', '05 Fight.mp3')
            self.dungeon_floor_1_music = \
                self.dungeon_floor_2_music = \
                self.dungeon_floor_3_music = \
                self.dungeon_floor_4_music = \
                self.dungeon_floor_5_music = \
                self.dungeon_floor_6_music = \
                self.dungeon_floor_7_music = \
                self.dungeon_floor_8_music = join(music_dir, 'orchestra', '06 Dungeon.mp3')

        else:
            self.intro_overture = join(music_dir, 'NES', '01 Dragon Quest 1 - Intro ~ Overture.mp3')
            self.tantegel_castle_throne_room_music = join(music_dir, 'NES', '02 Dragon Quest 1 - Tantegel Castle.mp3')
            self.tantegel_castle_courtyard_music = join(music_dir, 'NES',
                                                        '03 Dragon Quest 1 - Tantegel Castle (Lower).mp3')
            self.village_music = join(music_dir, 'NES', '04 Dragon Quest 1 - Peaceful Village.mp3')
            self.intermezzo = self.village_music
            self.overworld_music = join(music_dir, 'NES', '05 Dragon Quest 1 - Kingdom of Alefgard.mp3')
            self.dungeon_floor_1_music = join(music_dir, 'NES', '06 Dragon Quest 1 - Dark Dungeon ~ Floor 1.mp3')
            self.dungeon_floor_2_music = join(music_dir, 'NES', '07 Dragon Quest 1 - Dark Dungeon ~ Floor 2.mp3')
            self.dungeon_floor_3_music = join(music_dir, 'NES', '08 Dragon Quest 1 - Dark Dungeon ~ Floor 3.mp3')
            self.dungeon_floor_4_music = join(music_dir, 'NES', '09 Dragon Quest 1 - Dark Dungeon ~ Floor 4.mp3')
            self.dungeon_floor_5_music = join(music_dir, 'NES', '10 Dragon Quest 1 - Dark Dungeon ~ Floor 5.mp3')
            self.dungeon_floor_6_music = join(music_dir, 'NES', '11 Dragon Quest 1 - Dark Dungeon ~ Floor 6.mp3')
            self.dungeon_floor_7_music = join(music_dir, 'NES', '12 Dragon Quest 1 - Dark Dungeon ~ Floor 7.mp3')
            self.dungeon_floor_8_music = join(music_dir, 'NES', '13 Dragon Quest 1 - Dark Dungeon ~ Floor 8.mp3')
            self.battle_music = join(music_dir, 'NES', '14 Dragon Quest 1 - A Monster Draws Near.mp3')

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

        # main menu

        main_menu_dir = join(images_menus_dir, 'main_menu')

        # begin quest

        # empty logs

        main_menu_empty_log_dir = join(main_menu_dir, 'empty_log')
        self.main_menu_empty_log_0 = join(main_menu_empty_log_dir, '0_begin_quest.png')
        self.main_menu_empty_log_unselected = join(main_menu_empty_log_dir, '-1_unselected.png')

        # adventure log

        empty_log_adventure_log_dir = join(main_menu_empty_log_dir, 'adventure_log')
        self.empty_log_adventure_log_path = join(empty_log_adventure_log_dir, '-1_unselected.png')
        self.ADVENTURE_LOG_1_PATH = join(empty_log_adventure_log_dir, '0_adventure_log_1.png')
        self.ADVENTURE_LOG_2_PATH = join(empty_log_adventure_log_dir, '1_adventure_log_2.png')
        self.ADVENTURE_LOG_3_PATH = join(empty_log_adventure_log_dir, '2_adventure_log_3.png')

        # partially full logs

        main_menu_partially_full_log = join(main_menu_dir, 'partially_full_log')
        self.main_menu_partially_full_log_0 = join(main_menu_partially_full_log, '0_continue_quest.png')
        self.main_menu_partially_full_log_1 = join(main_menu_partially_full_log, '1_change_message_speed.png')
        self.main_menu_partially_full_log_2 = join(main_menu_partially_full_log, '2_begin_new_quest.png')
        self.main_menu_partially_full_log_3 = join(main_menu_partially_full_log, '3_copy_quest.png')
        self.main_menu_partially_full_log_4 = join(main_menu_partially_full_log, '4_erase_quest.png')
        self.main_menu_partially_full_log_unselected = join(main_menu_partially_full_log, '-1_unselected.png')

        # one adventure log

        one_adventure_log_dir = join(main_menu_partially_full_log, 'one_adventure_log')
        self.one_adventure_log_0 = join(one_adventure_log_dir, '0_adventure_log_1.png')
        self.one_adventure_log_unselected = join(one_adventure_log_dir, '-1_unselected.png')

        # full logs

        main_menu_full_log = join(main_menu_dir, 'full_log')
        self.continue_quest_full_log_0 = join(main_menu_full_log, '0_continue_quest.png')
        self.continue_quest_full_log_1 = join(main_menu_full_log, '1_change_message_speed.png')
        self.continue_quest_full_log_2 = join(main_menu_full_log, '2_erase_quest.png')
        self.continue_quest_full_log_unselected = join(main_menu_full_log, '-1_unselected.png')

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

        images_shops_dir = join(self.IMAGES_DIR, 'shops')

        images_shops_brecconary_dir = join(images_shops_dir, 'brecconary')
        images_shops_brecconary_weapons_dir = join(images_shops_brecconary_dir, 'weapons')
        self.BRECCONARY_WEAPONS_SHOP_PATH = join(images_shops_brecconary_weapons_dir, 'brecconary_shop.png')
        self.BRECCONARY_WEAPONS_SHOP_BAMBOO_POLE_PATH = join(images_shops_brecconary_weapons_dir,
                                                             'brecconary_shop_bamboo_pole.png')
        self.BRECCONARY_WEAPONS_SHOP_CLUB_PATH = join(images_shops_brecconary_weapons_dir, 'brecconary_shop_club.png')
        self.BRECCONARY_WEAPONS_SHOP_COPPER_SWORD_PATH = join(images_shops_brecconary_weapons_dir,
                                                              'brecconary_shop_copper_sword.png')
        self.BRECCONARY_WEAPONS_SHOP_CLOTHES_PATH = join(images_shops_brecconary_weapons_dir,
                                                         'brecconary_shop_clothes.png')
        self.BRECCONARY_WEAPONS_SHOP_LEATHER_ARMOR_PATH = join(images_shops_brecconary_weapons_dir,
                                                               'brecconary_shop_leather_armor.png')
        self.BRECCONARY_WEAPONS_SHOP_SMALL_SHIELD_PATH = join(images_shops_brecconary_weapons_dir,
                                                              'brecconary_shop_small_shield.png')

        images_shops_garinham_dir = join(images_shops_dir, 'garinham')
        images_shops_garinham_weapons_dir = join(images_shops_garinham_dir, 'weapons')
        self.GARINHAM_WEAPONS_SHOP_PATH = join(images_shops_garinham_weapons_dir, 'garinham_shop.png')
        self.GARINHAM_WEAPONS_SHOP_CHAIN_MAIL_PATH = join(images_shops_garinham_weapons_dir,
                                                          'garinham_shop_chain_mail.png')
        self.GARINHAM_WEAPONS_SHOP_CLUB_PATH = join(images_shops_garinham_weapons_dir, 'garinham_shop_club.png')
        self.GARINHAM_WEAPONS_SHOP_COPPER_SWORD_PATH = join(images_shops_garinham_weapons_dir,
                                                            'garinham_shop_copper_sword.png')
        self.GARINHAM_WEAPONS_SHOP_HALF_PLATE_PATH = join(images_shops_garinham_weapons_dir,
                                                          'garinham_shop_half_plate.png')
        self.GARINHAM_WEAPONS_SHOP_HAND_AXE_PATH = join(images_shops_garinham_weapons_dir, 'garinham_shop_hand_axe.png')
        self.GARINHAM_WEAPONS_SHOP_LARGE_SHIELD_PATH = join(images_shops_garinham_weapons_dir,
                                                            'garinham_shop_large_shield.png')
        self.GARINHAM_WEAPONS_SHOP_LEATHER_ARMOR_PATH = join(images_shops_garinham_weapons_dir,
                                                             'garinham_shop_leather_armor.png')

        images_shops_kol_dir = join(images_shops_dir, 'kol')
        images_shops_kol_weapons_dir = join(images_shops_kol_dir, 'weapons')
        self.KOL_WEAPONS_SHOP_PATH = join(images_shops_kol_weapons_dir, 'kol_shop.png')
        self.KOL_WEAPONS_SHOP_COPPER_SWORD_PATH = join(images_shops_kol_weapons_dir, 'kol_shop_copper_sword.png')
        self.KOL_WEAPONS_SHOP_HAND_AXE_PATH = join(images_shops_kol_weapons_dir, 'kol_shop_hand_axe.png')
        self.KOL_WEAPONS_SHOP_HALF_PLATE_PATH = join(images_shops_kol_weapons_dir, 'kol_shop_half_plate.png')
        self.KOL_WEAPONS_SHOP_FULL_PLATE_PATH = join(images_shops_kol_weapons_dir, 'kol_shop_full_plate.png')
        self.KOL_WEAPONS_SHOP_SMALL_SHIELD_PATH = join(images_shops_kol_weapons_dir, 'kol_shop_small_shield.png')

        images_shops_rimuldar_dir = join(images_shops_dir, 'rimuldar')
        images_shops_rimuldar_weapons_dir = join(images_shops_rimuldar_dir, 'weapons')
        self.RIMULDAR_WEAPONS_SHOP_PATH = join(images_shops_rimuldar_weapons_dir, 'rimuldar_shop.png')
        self.RIMULDAR_WEAPONS_SHOP_COPPER_SWORD_PATH = join(images_shops_rimuldar_weapons_dir,
                                                            'rimuldar_shop_copper_sword.png')
        self.RIMULDAR_WEAPONS_SHOP_HAND_AXE_PATH = join(images_shops_rimuldar_weapons_dir, 'rimuldar_shop_hand_axe.png')
        self.RIMULDAR_WEAPONS_SHOP_BROAD_SWORD_PATH = join(images_shops_rimuldar_weapons_dir,
                                                           'rimuldar_shop_broad_sword.png')
        self.RIMULDAR_WEAPONS_SHOP_HALF_PLATE_PATH = join(images_shops_rimuldar_weapons_dir,
                                                          'rimuldar_shop_half_plate.png')
        self.RIMULDAR_WEAPONS_SHOP_FULL_PLATE_PATH = join(images_shops_rimuldar_weapons_dir,
                                                          'rimuldar_shop_full_plate.png')
        self.RIMULDAR_WEAPONS_SHOP_MAGIC_ARMOR_PATH = join(images_shops_rimuldar_weapons_dir,
                                                           'rimuldar_shop_magic_armor.png')

        images_shops_cantlin_dir = join(images_shops_dir, 'cantlin')
        images_shops_cantlin_weapons_dir = join(images_shops_cantlin_dir, 'weapons')
        images_shops_cantlin_weapons_north_dir = join(images_shops_cantlin_weapons_dir, 'north')
        self.CANTLIN_WEAPONS_SHOP_NORTH_PATH = join(images_shops_cantlin_weapons_north_dir, 'cantlin_shop_north.png')
        self.CANTLIN_WEAPONS_SHOP_NORTH_BAMBOO_POLE_PATH = join(images_shops_cantlin_weapons_north_dir,
                                                                'cantlin_shop_north_bamboo_pole.png')
        self.CANTLIN_WEAPONS_SHOP_NORTH_CLUB_PATH = join(images_shops_cantlin_weapons_north_dir,
                                                         'cantlin_shop_north_club.png')
        self.CANTLIN_WEAPONS_SHOP_NORTH_COPPER_SWORD_PATH = join(images_shops_cantlin_weapons_north_dir,
                                                                 'cantlin_shop_north_copper_sword.png')
        self.CANTLIN_WEAPONS_SHOP_NORTH_LEATHER_ARMOR_PATH = join(images_shops_cantlin_weapons_north_dir,
                                                                  'cantlin_shop_north_leather_armor.png')
        self.CANTLIN_WEAPONS_SHOP_NORTH_CHAIN_MAIL_PATH = join(images_shops_cantlin_weapons_north_dir,
                                                               'cantlin_shop_north_chain_mail.png')
        self.CANTLIN_WEAPONS_SHOP_NORTH_LARGE_SHIELD_PATH = join(images_shops_cantlin_weapons_north_dir,
                                                                 'cantlin_shop_north_large_shield.png')

        images_shops_cantlin_weapons_south_dir = join(images_shops_cantlin_weapons_dir, 'south')
        self.CANTLIN_WEAPONS_SHOP_SOUTH_PATH = join(images_shops_cantlin_weapons_south_dir, 'cantlin_shop_south.png')
        self.CANTLIN_WEAPONS_SHOP_SOUTH_FULL_PLATE_PATH = join(images_shops_cantlin_weapons_south_dir,
                                                               'cantlin_shop_south_full_plate.png')
        self.CANTLIN_WEAPONS_SHOP_SOUTH_MAGIC_ARMOR_PATH = join(images_shops_cantlin_weapons_south_dir,
                                                                'cantlin_shop_south_magic_armor.png')
        self.CANTLIN_WEAPONS_SHOP_SOUTH_HAND_AXE_PATH = join(images_shops_cantlin_weapons_south_dir,
                                                             'cantlin_shop_south_hand_axe.png')
        self.CANTLIN_WEAPONS_SHOP_SOUTH_BROAD_SWORD_PATH = join(images_shops_cantlin_weapons_south_dir,
                                                                'cantlin_shop_south_broad_sword.png')

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
