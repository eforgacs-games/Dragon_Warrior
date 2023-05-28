import gettext
import os
from functools import partial

from pygame import display, time, mixer, KEYDOWN, K_DOWN, K_UP, K_w, K_s, K_k, K_RETURN, K_j, Rect
from pygame.event import get, pump
from pygame.time import get_ticks

from data.text.dialog import confirmation_prompt
from src.common import play_sound, special_item_sfx, BRECCONARY_WEAPONS_SHOP_PATH, convert_to_frames_since_start_time, \
    create_window, WHITE
from src.config import MUSIC_ENABLED, TILE_SIZE, LANGUAGE
from src.items import weapons, armor, shields
from src.menu_functions import draw_player_sprites, draw_character_sprites
from src.shops import brecconary_store_inventory
from src.visual_effects import fade, flash_transparent_color

# if LANGUAGE == 'en':
#     en = gettext.translation('base', localedir=os.path.join('../data/text/locales'), languages=['en'])
#     en.install()
#     _ = en.gettext
if LANGUAGE == 'Korean':
    ko = gettext.translation('base', localedir=os.path.join('../data/text/locales'), languages=['ko'])
    ko.install()
    _ = ko.gettext
else:
    _ = gettext.gettext

weapons_and_armor_intro = _("We deal in weapons and armor.\n Dost thou wish to buy anything today?")


class DialogLookup:
    def __init__(self, command_menu):
        self.command_menu = command_menu
        self.player = command_menu.player
        self.screen = command_menu.screen
        self.current_map = command_menu.current_map
        self.background = command_menu.background
        self.camera_position = command_menu.camera_position
        self.thou_art_dead = _("Thou art dead.")
        self.normal_speed_string = _("Game set to normal speed.\n(60 FPS)")
        self.double_speed_string = _("Game set to double speed.\n(120 FPS)")
        self.triple_speed_string = _("Game set to triple speed.\n(240 FPS)")
        self.quadruple_speed_string = _("Game set to quadruple speed.\n(480 FPS)")

        where_is_princess_gwaelin = _("Where oh where can I find Princess Gwaelin?")
        welcome_to_tantegel = _("Welcome to Tantegel Castle.")
        brecconary_inn_cost = 6
        garinham_inn_cost = 25
        tools_intro = _("Welcome.\n"
                        "We deal in tools.\n"
                        "What can I do for thee?")
        self.lookup_table = {
            'TantegelThroneRoom': {
                'KING_LORIK': {'dialog': (
                    _("Descendant of Erdrick, listen now to my words."),
                    _("It is told that in ages past Erdrick fought demons with a Ball of Light."),
                    _("Then came the Dragonlord who stole the precious globe and hid it in the darkness."),
                    _("Now, {}, thou must help us recover the Ball of Light and restore peace to our land.").format(
                        self.player.name),
                    _("The Dragonlord must be defeated."),
                    _("Take now whatever thou may find in these Treasure Chests to aid thee in thy quest."),
                    _("Then speak with the guards, for they have much knowledge that may aid thee."),
                    _("May the light shine upon thee, {}.").format(self.player.name)
                ), 'post_initial_dialog': _(
                    "When thou art finished preparing for thy departure, please see me.\nI shall wait."),
                    'returned_dialog': (
                        _("I am greatly pleased that thou hast returned, {}.").format(self.player.name),
                        _("Before reaching thy next level of experience thou must gain {} Points.").format(
                            self.player.points_to_next_level),
                        _("Will thou tell me now of thy deeds so they won't be forgotten?"),
                        # if yes:
                        _("Thy deeds have been recorded on the Imperial Scrolls of Honor."),
                        _("Dost thou wish to continue thy quest?"),
                        # if yes:
                        _("Goodbye now, {}.\n'Take care and tempt not the Fates.").format(self.player.name),
                        # if no:
                        # "Rest then for awhile."
                    ),
                    'post_death_dialog': (_("Death should not have taken thee, {}.").format(self.player.name),
                                          _("I will give thee another chance."),
                                          _("To reach the next level, thy Experience Points must increase by {}.").format(
                                              self.player.points_to_next_level),
                                          _("Now, go, {}!").format(self.player.name))},
                'RIGHT_FACE_GUARD': {'dialog': (
                    _("East of this castle is a town where armor, weapons, and many other items may be purchased."),
                    _("Return to the Inn for a rest if thou art wounded in battle, {}.").format(self.player.name),
                    _("Sleep heals all.")
                )},
                'LEFT_FACE_GUARD': {'dialog': (
                    _("If thou hast collected all the Treasure Chests, a key will be found."),
                    _("Once used, the key will disappear, but the door will be open and thou may pass through.")
                )},
                'ROAMING_GUARD': {'dialog': (
                    self.tantegel_throne_room_roaming_guard,
                )}},
            'TantegelCourtyard': {
                'MERCHANT': {'dialog': (
                _("Magic keys! They will unlock any door.\nDost thou wish to purchase one for {} GOLD?").format(85),)},
                'MERCHANT_2': {'dialog': _(
                    "We are merchants who have traveled much in this land. Many of our colleagues have been killed by servants of the Dragonlord.")},
                'MERCHANT_3': {
                    'dialog': _("Rumor has it that entire towns have been destroyed by the Dragonlord's servants.")},
                'MAN': {'dialog': _("To become strong enough to face future trials thou must first battle many foes.")},
                'MAN_2': {'dialog': _(
                    "There was a time when Brecconary was a paradise.\nThen the Dragonlord's minions came.")},
                'WOMAN': {
                    'dialog': (_("When the sun and rain meet, a Rainbow Bridge shall appear."), _("It's a legend."))},
                'WOMAN_2': {'dialog': where_is_princess_gwaelin},
                'RIGHT_FACE_GUARD': {'dialog': where_is_princess_gwaelin},
                'LEFT_FACE_GUARD': {'dialog': welcome_to_tantegel},
                'DOWN_FACE_GUARD': {'dialog': (
                    _("King Lorik will record thy deeds in his Imperial Scroll so thou may return to thy quest later."),)},
                'UP_FACE_GUARD': {'dialog': _("If thou art planning to take a rest, first see King Lorik.")},
                'RIGHT_FACE_GUARD_2': {'dialog': welcome_to_tantegel},
                'WISE_MAN': {'dialog': (
                    _("{}'s coming was foretold by legend. May the light shine upon this brave warrior.").format(
                        self.player.name),
                    self.flash_and_restore_mp)}},
            'TantegelCellar': {'WISE_MAN': {
                'dialog': (_("I have been waiting long for one such as thee."), _("Take the Treasure Chest."))}},
            'Brecconary': {
                'MAN': {'dialog': _("There is a town where magic keys can be purchased.")},
                'WISE_MAN': {'dialog': _("If thou art cursed, come again.")},
                'MERCHANT': {'dialog': (
                partial(self.check_buy_weapons_armor, brecconary_store_inventory, BRECCONARY_WEAPONS_SHOP_PATH),)},
                'MERCHANT_2': {'dialog': (partial(self.check_stay_at_inn, brecconary_inn_cost),)},
                'UP_FACE_GUARD': {'dialog': (_("Tell King Lorik that the search for his daughter hath failed."),
                                             _("I am almost gone...."))},
                'WOMAN_2': {'dialog': _("Welcome! \n"
                                        "Enter the shop and speak to its keeper across the desk.")},
            },
            'Garinham': {
                'MERCHANT': {'dialog': (tools_intro,)},
                'MERCHANT_2': {'dialog': (
                    (partial(self.check_stay_at_inn, garinham_inn_cost),),
                )},
                'MERCHANT_3': {'dialog': weapons_and_armor_intro},
                'WISE_MAN': {'dialog': "Many believe that Princess Gwaelin is hidden away in a cave."}

            },
            'StaffOfRainCave': {'WISE_MAN': {'dialog': ("Thy bravery must be proven.",
                                                        "Thus, I propose a test.",
                                                        "There is a Silver Harp that beckons to the creatures of the Dragonlord.",
                                                        "Bring this to me and I will reward thee with the Staff of Rain.")}}
        }

        for map_dict in self.lookup_table.values():
            for character_identifier, character_dict in map_dict.items():
                character_dict['dialog_character'] = character_identifier

    def tantegel_throne_room_roaming_guard(self):
        player_please_save_the_princess = _("{}, please save the Princess.").format(self.player.name)
        confirmation_prompt(self.command_menu, _("Dost thou know about Princess Gwaelin?"),
                            yes_path_function=partial(self.command_menu.show_line_in_dialog_box,
                                                      player_please_save_the_princess, last_line=True),
                            no_path_function=partial(self.command_menu.show_text_in_dialog_box,
                                                     (
                                                         _("Half a year now hath passed since the Princess was kidnapped by the enemy."),
                                                         _("Never does the King speak of it, but he must be suffering much."),
                                                         player_please_save_the_princess),
                                                     drop_down=False, drop_up=False,
                                                     skip_text=self.command_menu.skip_text))

    def check_buy_weapons_armor(self, current_store_inventory, static_store_image):
        confirmation_prompt(self.command_menu, weapons_and_armor_intro,
                            yes_path_function=partial(self.open_store_inventory, current_store_inventory,
                                                      static_store_image),
                            no_path_function=partial(self.command_menu.show_line_in_dialog_box, "Please, come again.",
                                                     last_line=True))

    def flash_and_restore_mp(self):
        self.player.restore_mp()
        # flash for 3 frames on, 3 frames off
        # flash white 8 times
        # TODO(ELF): This flashes once, but needs to flash 8 times.
        flash_transparent_color(WHITE, self.screen, transparency=128)
        display.flip()
        flash_transparent_color(WHITE, self.screen, transparency=255)
        display.flip()
        # draw_all_tiles_in_current_map(self.current_map, self.background)
        # draw_player_sprites(self.current_map, self.background, self.player.column, self.player.row)
        # display.flip()

        # start_time = get_ticks()
        # if convert_to_frames_since_start_time(start_time) <= 25:
        #     if convert_to_frames_since_start_time(start_time) % 3 == 0:
        #         start_flash = get_ticks()
        #         while convert_to_frames_since_start_time(start_flash) < 3:
        #             flash_transparent_color(WHITE, self.screen)
        #             display.flip()

    def open_store_inventory(self, current_store_inventory, static_store_image, color=WHITE):
        self.command_menu.show_line_in_dialog_box(_("What dost thou wish to buy?"), skip_text=True)
        self.command_menu.window_drop_down_effect(6, 2, 9, 7)
        # store_inventory_window = create_window(6, 2, 9, 7, static_store_image, self.command_menu.screen)
        # display.update(store_inventory_window.get_rect())
        store_inventory_window_rect = Rect(6 * TILE_SIZE, 2 * TILE_SIZE, 9 * TILE_SIZE, 7 * TILE_SIZE)
        selecting = True
        current_item_index = 0
        start_time = get_ticks()
        # arrow stays on and off for 16 frames at a time
        while selecting:
            current_item_name = list(current_store_inventory)[current_item_index]
            current_item_menu_image = current_store_inventory[current_item_name]['menu_image']
            frames_elapsed = convert_to_frames_since_start_time(start_time)
            if frames_elapsed <= 16:
                create_window(6, 2, 9, 7, current_item_menu_image, self.command_menu.screen, color)
                display.update(store_inventory_window_rect)
            elif frames_elapsed <= 32:
                create_window(6, 2, 9, 7, static_store_image, self.command_menu.screen, color)
                display.update(store_inventory_window_rect)
            else:
                start_time = get_ticks()
            selected_item = None
            for current_event in get():
                if current_event.type == KEYDOWN:
                    if current_event.key in (K_DOWN, K_s) and current_item_index < len(current_store_inventory) - 1:
                        current_item_index += 1
                        start_time = get_ticks()
                    elif current_event.key in (K_UP, K_w) and current_item_index > 0:
                        current_item_index -= 1
                        start_time = get_ticks()
                    elif current_event.key == K_j:
                        self.command_menu.show_line_in_dialog_box(_("Please, come again."), last_line=True)
                        selecting = False
                    elif current_event.key in (K_RETURN, K_k):
                        selected_item = current_item_name
            if selected_item:
                create_window(6, 2, 9, 7, current_item_menu_image, self.command_menu.screen, color)
                display.update(store_inventory_window_rect)
                self.buy_item_dialog(selected_item, current_store_inventory, static_store_image)
                selecting = False
            pump()
            # print(f"Item index {current_item_index}: {current_item_name}")

    def buy_item_dialog(self, selected_item, current_store_inventory, static_store_image):
        self.command_menu.show_line_in_dialog_box(f"The {selected_item}?", last_line=False)
        selected_item_dict = current_store_inventory[selected_item]
        selected_item_type = selected_item_dict['type']
        if self.player.gold > selected_item_dict['cost']:
            old_item_cost = None
            if selected_item_type == 'weapon':
                old_item_cost = self.shopkeeper_buy_old_item(old_item_cost, self.player.weapon, weapons)
            elif selected_item_type == 'armor':
                old_item_cost = self.shopkeeper_buy_old_item(old_item_cost, self.player.armor, armor)
            elif selected_item_type == 'shield':
                old_item_cost = self.shopkeeper_buy_old_item(old_item_cost, self.player.shield, shields)
            confirmation_prompt(self.command_menu, _("Is that Okay.?"),
                                yes_path_function=partial(self.complete_transaction, selected_item,
                                                          current_store_inventory, old_item_cost),
                                no_path_function=partial(self.command_menu.show_line_in_dialog_box,
                                                         _("Oh, yes? That's too bad."), last_line=False))
        else:
            self.command_menu.show_line_in_dialog_box(_("Sorry.\n"
                                                        "Thou hast not enough money."), last_line=False)
        confirmation_prompt(self.command_menu, _("Dost thou wish to buy anything more?"),
                            yes_path_function=partial(self.open_store_inventory, current_store_inventory,
                                                      static_store_image),
                            no_path_function=partial(self.command_menu.show_line_in_dialog_box,
                                                     _("Please, come again."), last_line=True))

    def shopkeeper_buy_old_item(self, old_item_cost, old_item, old_item_lookup_table):
        if old_item:
            if old_item_lookup_table[old_item].get('cost'):
                old_item_cost = old_item_lookup_table[old_item]['cost'] // 2
                self.command_menu.show_line_in_dialog_box(
                    _("Then I will buy thy {} for {} GOLD.").format(old_item, old_item_cost), last_line=False)
        return old_item_cost

    def complete_transaction(self, item, current_store_inventory, old_item_cost):
        item_dict = current_store_inventory[item]
        item_type = item_dict['type']
        self.player.gold -= item_dict['cost']
        if old_item_cost:
            self.player.gold += old_item_cost
        if item_type == 'weapon':
            self.player.weapon = item
        elif item_type == 'armor':
            self.player.armor = item
        elif item_type == 'shield':
            self.player.shield = item
        self.player.update_attack_power()
        self.player.update_defense_power()
        self.command_menu.game.drawer.draw_hovering_stats_window(self.screen, self.player)
        self.command_menu.show_line_in_dialog_box(_("I thank thee."))

    def check_stay_at_inn(self, inn_cost):
        confirmation_prompt(self.command_menu, get_inn_intro(inn_cost),
                            yes_path_function=partial(self.check_money, inn_cost),
                            no_path_function=partial(self.command_menu.show_line_in_dialog_box,
                                                     _("Okay.\n"
                                                       "Good-bye, traveler."),
                                                     skip_text=self.command_menu.skip_text),
                            skip_text=self.command_menu.skip_text)

    def check_money(self, inn_cost):
        if self.player.gold >= inn_cost:
            self.inn_sleep(inn_cost)
        else:
            self.command_menu.show_line_in_dialog_box(_("Thou hast not enough money."),
                                                      skip_text=self.command_menu.skip_text)

    def inn_sleep(self, inn_cost):
        self.command_menu.show_line_in_dialog_box(_("Good night."), skip_text=self.command_menu.skip_text)
        fade(fade_out=True, screen=self.screen)
        if MUSIC_ENABLED:
            mixer.music.stop()
        play_sound(special_item_sfx)
        self.player.restore_hp()
        self.player.restore_mp()
        self.player.gold -= inn_cost
        time.wait(3000)
        if MUSIC_ENABLED:
            mixer.music.load(self.current_map.music_file_path)
            mixer.music.play(-1)
        self.command_menu.game.drawer.draw_all_tiles_in_current_map(self.current_map, self.background)
        draw_player_sprites(self.current_map, self.background, self.player.column, self.player.row)
        for character, character_dict in self.current_map.characters.items():
            if character != 'HERO':
                draw_character_sprites(self.current_map, self.background, character_dict['coordinates'][1],
                                       character_dict['coordinates'][0], character)
        self.screen.blit(self.background, self.camera_position)
        self.screen.blit(self.command_menu.command_menu_surface, (TILE_SIZE * 6, TILE_SIZE * 1))
        display.flip()
        self.command_menu.show_text_in_dialog_box((_("Good morning.\nThou seems to have spent a good night."),
                                                   _("I shall see thee again.")), skip_text=self.command_menu.skip_text,
                                                  drop_up=False)


def get_inn_intro(inn_cost):
    return _("Welcome to the traveler's Inn.\n"
             "Room and board is {} GOLD per night.\n"
             "Dost thou want a room?").format(inn_cost)
