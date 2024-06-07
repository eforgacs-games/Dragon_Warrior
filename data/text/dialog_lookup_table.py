from functools import partial

from pygame import display, time, mixer, KEYDOWN, K_DOWN, K_UP, K_w, K_s, Rect, QUIT
from pygame.event import get, pump
from pygame.time import get_ticks

from data.text.dialog import confirmation_prompt
from src.calculation import Calculation
from src.color import BLACK
from src.common import WHITE, reject_keys, accept_keys, Graphics, set_gettext_language
from src.directories import Directories
from src.items import weapons, armor, shields
from src.maps import DragonWarriorMap
from src.menu_functions import draw_player_sprites, draw_character_sprites
from src.shops import ShopInventories
from src.sound import Sound
from src.visual_effects import fade, flash_transparent_color


class DialogLookup:
    def __init__(self, command_menu, config: dict):
        self.config = config
        self.calculation = Calculation(config)
        self.sound = Sound(config)
        self._ = _ = set_gettext_language(self.config['LANGUAGE'])

        self.shop_inventories = ShopInventories(self.config)
        self.command_menu = command_menu
        self.color = self.command_menu.game.color
        self.player = command_menu.player
        self.screen = command_menu.screen
        self.current_map: DragonWarriorMap = command_menu.current_map
        self.background = command_menu.background
        self.camera_position = command_menu.camera_position
        # menu

        self.goodbye_tempt_not_the_fates = "Goodbye now, {}.\n'Take care and tempt not the Fates."

        where_is_princess_gwaelin = _("Where oh where can I find Princess Gwaelin?")
        welcome_to_tantegel = _("Welcome to Tantegel Castle.")
        brecconary_inn_cost = 6
        kol_inn_cost = 20
        garinham_inn_cost = 25
        rimuldar_inn_cost = 55
        cantlin_inn_cost = 100

        tantegel_courtyard_magic_key_cost = 85
        cantlin_magic_key_cost = 98

        tools_intro = _("Welcome.\n"
                        "We deal in tools.\n"
                        "What can I do for thee?")
        self.directories = Directories(self.config)
        before_reaching_thy_next_level_of_experience = "Before reaching thy next level of experience thou must gain {} Points."

        self.magic_key_prompt = "Magic keys! They will unlock any door.\nDost thou wish to purchase one for {} GOLD?"

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
                        _(before_reaching_thy_next_level_of_experience).format(
                            self.player.points_to_next_level),
                        self.prompt_for_save,
                        self.prompt_to_continue_quest,
                    ),
                    'load_from_save_dialog': (self._("I am glad thou hast returned.\n"
                                                     "All our hopes are riding on thee."),
                                              before_reaching_thy_next_level_of_experience.format(
                                                  self.player.points_to_next_level),
                                              self._("See me again when thy level has increased."),
                                              self.goodbye_tempt_not_the_fates.format(self.player.name)
                                              ),
                    'post_death_dialog': (_("Death should not have taken thee, {}.").format(self.player.name),
                                          _("I will give thee another chance."),
                                          _("To reach the next level, thy Experience Points must increase by {}.").format(
                                              self.player.points_to_next_level),
                                          _("Now, go, {}!").format(self.player.name)),
                    'carrying_princess_dialog': (
                        _("Forever shall I be grateful for the gift of my daughter returned to her home, {}. "
                          "Accept my thanks.").format(self.player.name),
                        _("Now, Gwaelin, come to my side."),
                        self.princess_whispers,
                        self._("Please accept my love, {}.").format(self.player.name),
                        self._("Even when we two are parted by great distances, I shall be with thee."),
                        self._("Farewell, {}.").format(self.player.name),
                        self.receive_gwaelins_love,
                        self.put_princess_on_throne,
                        # TODO: Put Princess on her throne at this point, and reset character images
                        self.prompt_for_save,
                        self.prompt_to_continue_quest,
                    ),
                },

                'GUARD': {'dialog': (
                    self.tantegel_throne_room_roaming_guard,
                )},
                'GUARD_2': {'dialog': (
                    _("If thou hast collected all the Treasure Chests, a key will be found."),
                    _("Once used, the key will disappear, but the door will be open and thou may pass through.")
                )},
                'GUARD_3': {'dialog': (
                    _("East of this castle is a town where armor, weapons, and many other items may be purchased."),
                    _("Return to the Inn for a rest if thou art wounded in battle, {}.").format(self.player.name),
                    _("Sleep heals all.")
                )},
            },
            'TantegelCourtyard': {
                'MERCHANT': {'dialog': (partial(self.check_buy_magic_keys, tantegel_courtyard_magic_key_cost),)},
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

                'GUARD': {'dialog': (
                    _("King Lorik will record thy deeds in his Imperial Scroll so thou may return to thy quest later."),)},
                'GUARD_2': {'dialog': _("If thou art planning to take a rest, first see King Lorik.")},
                'GUARD_3': {'dialog': _("Never does a brave person steal.")},
                'GUARD_4': {'dialog': where_is_princess_gwaelin},
                'GUARD_5': {'dialog': welcome_to_tantegel},
                'GUARD_6': {'dialog': welcome_to_tantegel},
                'WISE_MAN': {'dialog': (
                    _("{}'s coming was foretold by legend. May the light shine upon this brave warrior.").format(
                        self.player.name),
                    self.flash_and_restore_mp)}},
            'TantegelCellar': {'WISE_MAN': {
                'dialog': (_("I have been waiting long for one such as thee."), _("Take the Treasure Chest."))}},
            'Brecconary': {
                'MAN': {'dialog': _("There is a town where magic keys can be purchased.")},
                'MAN_2': {'dialog': _("Thou art most welcome in Brecconary.")},
                'MAN_3': {'dialog': _("Enter where thou can.")},
                'SOLDIER': {'dialog': (_("Beware the bridges!"), _("Danger grows when thou crosses."))},
                'WISE_MAN': {'dialog': _("If thou art cursed, come again.")},
                'MERCHANT': {'dialog': (
                    partial(self.check_buy_weapons_armor, self.shop_inventories.brecconary_weapons_store_inventory,
                            self.directories.BRECCONARY_WEAPONS_SHOP_PATH),)},
                'MERCHANT_2': {'dialog': (partial(self.check_stay_at_inn, brecconary_inn_cost),)},
                'MERCHANT_3': {'dialog': (tools_intro,)},
                'GUARD': {'dialog': (_("Tell King Lorik that the search for his daughter hath failed."),
                                     _("I am almost gone...."))},
                'WOMAN_2': {'dialog': _("Welcome! \n"
                                        "Enter the shop and speak to its keeper across the desk.")},
            },
            'Garinham': {
                'MERCHANT': {'dialog': _("I suggest making a map if thy path leads into the darkness.")},
                'MERCHANT_2': {'dialog': (tools_intro,)},
                'MERCHANT_3': {'dialog': (partial(self.check_stay_at_inn, garinham_inn_cost),)},
                'MERCHANT_4': {'dialog': (
                    partial(self.check_buy_weapons_armor, self.shop_inventories.garinham_weapons_store_inventory,
                            self.directories.GARINHAM_WEAPONS_SHOP_PATH),)},
                'GUARD': {'dialog': _("I'm too busy.\n"
                                      "Ask the other guard."), },
                'GUARD_2': {'dialog': _("I'm too busy.\n"
                                        "Ask the other guard."), },
                'WOMAN': {'dialog': _("Welcome to Garinham. May thy stay be a peaceful one.")},
                'WISE_MAN': {'dialog': _("The harp attracts enemies. Stay away from the grave in Garinham.")},
                'WISE_MAN_2': {
                    'dialog': _("Garin, a wandering minstrel of legendary fame, is said to have built this town.")},
                'WISE_MAN_3': {'dialog': _("Many believe that Princess Gwaelin is hidden away in a cave.")}

            },
            'Kol': {'MERCHANT': {'dialog': (partial(self.check_stay_at_inn, kol_inn_cost),)},
                    'MERCHANT_2': {'dialog': (
                        partial(self.check_buy_weapons_armor, self.shop_inventories.kol_weapons_store_inventory,
                                self.directories.KOL_WEAPONS_SHOP_PATH),)},
                    'WISE_MAN': {'dialog': (
                        _("Though thou art as brave as thy ancestor, {}, "
                          "thou cannot defeat the great Dragonlord with such weapons.").format(
                            self.player.name), _("Thou shouldst come here again."))},
                    'WISE_MAN_2': {'dialog': _("In legends it is said that fairies know how to put Golem to sleep.")},
                    'WISE_MAN_3': {'dialog': _("This is the village of Kol.")},
                    'GUARD': {'dialog': _("Golem is afraid of the music of the flute, so 'tis said.")},
                    'WOMAN': {'dialog': _("This bath cures rheumatism.")},
                    'WOMAN_2': {'dialog': _("Please,save us from the minions of the Dragonlord.")},
                    'MAN': {'dialog': _("Art thou the descendant of Erdrick?\n"
                                        "Hast thou any proof?")},
                    'MAN_2': {'dialog': (_("Dreadful is the South Island."),
                                         _("Great strength and skill and wit only will bring thee back from that place."))},
                    'SOLDIER': {'dialog': _("Hast thou seen Nester?\n"
                                            "I think he may need help.")},
                    'SOLDIER_2': {'dialog': _(
                        "East of Hauksness there is a town, 'tis said, where one may purchase weapons of extraordinary quality.")},
                    },
            'Rimuldar': {
                'MERCHANT_2': {'dialog': (
                    partial(self.check_buy_weapons_armor, self.shop_inventories.rimuldar_weapons_store_inventory,
                            self.directories.RIMULDAR_WEAPONS_SHOP_PATH),)},
                'MERCHANT_3': {'dialog': (partial(self.check_stay_at_inn, kol_inn_cost),)},
            },
            'Cantlin': {
                'MERCHANT': {'dialog': (partial(self.check_stay_at_inn, cantlin_inn_cost),)},
                'MERCHANT_2': {'dialog': (
                    partial(self.check_buy_weapons_armor, self.shop_inventories.cantlin_weapons_store_north_inventory,
                            self.directories.CANTLIN_WEAPONS_SHOP_NORTH_PATH),)},
                'MERCHANT_3': {
                    'dialog': self._("Come buy my radishes! They are fresh and cheap.\nBuy thy radishes today!")},
                'MERCHANT_6': {'dialog': (
                    partial(self.check_buy_weapons_armor, self.shop_inventories.cantlin_weapons_store_south_inventory,
                            self.directories.CANTLIN_WEAPONS_SHOP_SOUTH_PATH),)},
                'WISE_MAN': {'dialog': (partial(self.check_buy_magic_keys, cantlin_magic_key_cost),)},
                'WISE_MAN_2': {
                    'dialog': _("To learn how proof may be obtained that thy ancestor was the great Erdrick, "
                                "see a man in this very town.")},

            },
            'SwampCave': {
                'PRINCESS_GWAELIN': {'dialog': (_("Thou art brave indeed to rescue me, {}.").format(self.player.name),
                                                _("I am Gwaelin, daughter of Lorik."),
                                                self.take_to_castle_confirmation_prompt
                                                )}},

            'StaffOfRainCave': {'WISE_MAN': {'dialog': ("Thy bravery must be proven.",
                                                        "Thus, I propose a test.",
                                                        "There is a Silver Harp that beckons to the creatures of the Dragonlord.",
                                                        "Bring this to me and I will reward thee with the Staff of Rain.")}},
            'MagicTemple': {'WISE_MAN': {'dialog': (
                "In thy task thou hast failed. Alas, I fear thou art not the one Erdrick predicted would save us.",
                "Go now!",
                partial(flash_transparent_color, WHITE, self.screen, self.calculation),
                partial(self.sound.play_sound, self.directories.stairs_up_sfx),
                # TODO: Kick player out of the Magic Temple and back to the overworld map on the staircase
                # partial(self.command_menu.game.change_map, Alefgard)
            )}}
        }

        for map_dict in self.lookup_table.values():
            for character_identifier, character_dict in map_dict.items():
                character_dict['dialog_character'] = character_identifier

    def take_to_castle_confirmation_prompt(self):
        return confirmation_prompt(
            self.command_menu,
            self._("Will thou take me to the castle?"),
            yes_path_function=self.embrace_princess_gwaelin,
            no_path_function=partial(self.but_thou_must, self.take_to_castle_confirmation_prompt),
            config=self.config,
            show_arrow=self.command_menu.game.show_arrow,
            color=self.color)

    def embrace_princess_gwaelin(self):
        self.command_menu.show_line_in_dialog_box(self._("Princess Gwaelin embraces thee.\n"),
                                                  add_quotes=False)
        mixer.music.stop()
        time.wait(1000)
        self.sound.play_sound(self.directories.princess_gwaelins_love_sfx)
        time.wait(5000)
        mixer.music.play(-1)

        self.current_map.fixed_characters = []
        del self.current_map.characters['PRINCESS_GWAELIN']

        self.player.images = self.current_map.scale_sprite_sheet(self.directories.HERO_CARRYING_PRINCESS_PATH)
        self.player.set_images(self.player.images)
        self.player.is_carrying_princess = True
        self.command_menu.show_line_in_dialog_box(self._("I'm so happy!"))

    def but_thou_must(self, original_function):
        self.command_menu.show_line_in_dialog_box(self._("But thou must."))
        original_function()

    def princess_whispers(self):
        self.command_menu.show_text_line_in_dialog_box(
            line=self._("Gwaelin then whispers:\n"
                        "'Wait a moment, please. "
                        "I would give a present to {}.'").format(self.player.name),
            add_quotes=False, disable_sound=False, hide_arrow=False, letter_by_letter=True, skip_text=False,
            temp_text_start=None, tile_size=self.config['TILE_SIZE'])

    def receive_gwaelins_love(self):
        self.player.inventory.append("Gwaelin's Love")

    def put_princess_on_throne(self):
        # TODO: This put_princess_on_throne method doesn't quite work yet...
        self.command_menu.game.set_player_images_by_equipment()
        self.player.set_images(self.player.images)
        self.player.is_carrying_princess = False
        self.current_map.fixed_characters.append('PRINCESS_GWAELIN')
        # this dialog is totally made up, fix later
        # self.current_map.characters['PRINCESS_GWAELIN'] = {
        #     'dialog': self._("I am Gwaelin, daughter of Lorik. I shall wait here for thy return."),
        #     'dialog_character': 'PRINCESS_GWAELIN',
        #     'images': self.current_map.scale_sprite_sheet(self.directories.PRINCESS_GWAELIN_PATH)[0]
        # }

    def prompt_for_save(self):
        return confirmation_prompt(self.command_menu,
                                   self._("Will thou tell me now of thy deeds so they won't be forgotten?"),
                                   yes_path_function=self.save_game,
                                   no_path_function=self.prompt_to_continue_quest,
                                   config=self.config,
                                   show_arrow=self.command_menu.game.show_arrow, color=self.color)

    def save_game(self):
        self.command_menu.save()
        self._("Thy deeds have been recorded on the Imperial Scrolls of Honor."),

    def prompt_to_continue_quest(self):
        return confirmation_prompt(self.command_menu, self._("Dost thou wish to continue thy quest?"),
                                   yes_path_function=partial(self.command_menu.show_line_in_dialog_box,
                                                             self._(
                                                                 self.goodbye_tempt_not_the_fates).format(
                                                                 self.player.name)),
                                   no_path_function=self.rest_then_for_awhile,
                                   config=self.config,
                                   show_arrow=self.command_menu.game.show_arrow, color=self.color)

    def rest_then_for_awhile(self):
        self.command_menu.show_line_in_dialog_box(self._("Rest then for awhile."))
        fade(fade_out=True, screen=self.screen, config=self.config)
        self.screen.fill(BLACK)
        display.flip()
        self.command_menu.show_text_in_dialog_box((self._("Please push RESET, hold it in, then turn off the POWER."),
                                                   self._(
                                                       "If you turn the power off first, the Imperial Scroll of Honor containing your deeds may be lost."))
                                                  )
        quit()

    def tantegel_throne_room_roaming_guard(self):
        _ = self._
        if self.command_menu.game.princess_saved:
            self.command_menu.show_line_in_dialog_box(_("Oh, brave {}.").format(self.player.name))
        else:
            player_please_save_the_princess = _("{}, please save the Princess.").format(self.player.name)
            confirmation_prompt(self.command_menu, _("Dost thou know about Princess Gwaelin?"),
                                yes_path_function=partial(self.command_menu.show_line_in_dialog_box,
                                                          player_please_save_the_princess, hide_arrow=True),
                                no_path_function=partial(self.command_menu.show_text_in_dialog_box,
                                                         (
                                                             _("Half a year now hath passed since the Princess was kidnapped by the enemy."),
                                                             _("Never does the King speak of it, but he must be suffering much."),
                                                             player_please_save_the_princess),
                                                         drop_down=False, drop_up=False,
                                                         skip_text=self.command_menu.skip_text), config=self.config,
                                show_arrow=self.command_menu.game.show_arrow, color=self.color)

    def check_buy_weapons_armor(self, current_store_inventory, static_store_image):
        confirmation_prompt(self.command_menu,
                            self._("We deal in weapons and armor.\n Dost thou wish to buy anything today?"),
                            yes_path_function=partial(self.open_store_inventory, current_store_inventory,
                                                      static_store_image, color=self.command_menu.color),
                            no_path_function=partial(self.command_menu.show_line_in_dialog_box,
                                                     self._("Please, come again."),
                                                     hide_arrow=True),
                            config=self.config, show_arrow=self.command_menu.game.show_arrow, color=self.color)

    def check_buy_magic_keys(self, magic_key_cost):
        confirmation_prompt(self.command_menu, self.magic_key_prompt.format(magic_key_cost),
                            yes_path_function=partial(self.buy_magic_key, magic_key_cost),
                            no_path_function=partial(self.command_menu.show_line_in_dialog_box,
                                                     self._("Please, come again."), hide_arrow=True),
                            config=self.config, show_arrow=self.command_menu.game.show_arrow, color=self.color)

    def buy_magic_key(self, magic_key_cost):
        _ = self._
        if self.player.gold >= magic_key_cost:
            self.player.gold -= magic_key_cost
            self.player.inventory.append('Magic Key')
            self.command_menu.show_line_in_dialog_box(_("Thank you very much."))
        else:
            self.command_menu.show_line_in_dialog_box(_("Thou hast not enough money."))

    def get_inn_intro(self, inn_cost):
        _ = self._
        return _("Welcome to the traveler's Inn.\n"
                 "Room and board is {} GOLD per night.\n"
                 "Dost thou want a room?").format(inn_cost)

    def flash_and_restore_mp(self):
        self.player.restore_mp()
        # flash for 3 frames on, 3 frames off
        # flash white 8 times
        # TODO(ELF): This flashes once, but needs to flash 8 times.
        flash_transparent_color(WHITE, self.screen, self.calculation, transparency=128)
        display.flip()
        flash_transparent_color(WHITE, self.screen, self.calculation, transparency=255)
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

    def open_store_inventory(self, current_store_inventory, static_store_image, color):
        _ = self._
        tile_size = self.command_menu.game.game_state.config['TILE_SIZE']
        self.command_menu.show_line_in_dialog_box(_("What dost thou wish to buy?"), skip_text=True)
        height = len(current_store_inventory) + 1
        self.command_menu.window_drop_down_effect(6, 2, 9, height)
        store_inventory_window_rect = Rect(6 * tile_size, 2 * tile_size, 9 * tile_size, height * tile_size)
        selecting = True
        current_item_index = 0
        start_time = get_ticks()
        # arrow stays on and off for 16 frames at a time
        graphics = Graphics(self.config)
        while selecting:
            self.command_menu.game.drawer.display_hovering_stats = True
            display.flip()
            current_item_name = list(current_store_inventory)[current_item_index]
            current_item_menu_image = current_store_inventory[current_item_name]['menu_image']
            frames_elapsed = self.calculation.convert_to_frames_since_start_time(start_time)

            if frames_elapsed <= 16:
                graphics.create_window(6, 2, 9, height, current_item_menu_image, self.command_menu.screen, color)
                display.update(store_inventory_window_rect)
            elif frames_elapsed <= 32:
                graphics.create_window(6, 2, 9, height, static_store_image, self.command_menu.screen, color)
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
                    elif current_event.key in reject_keys:
                        self.command_menu.show_line_in_dialog_box(_("Please, come again."), hide_arrow=True)
                        selecting = False
                    elif current_event.key in accept_keys:
                        selected_item = current_item_name
                elif current_event.type == QUIT:
                    quit()
            if selected_item:
                graphics.create_window(6, 2, 9, height, current_item_menu_image, self.command_menu.screen, color)
                display.update(store_inventory_window_rect)
                self.buy_item_dialog(selected_item, current_store_inventory, static_store_image)
                selecting = False
            pump()
            # print(f"Item index {current_item_index}: {current_item_name}")

    def buy_item_dialog(self, selected_item, current_store_inventory, static_store_image):
        _ = self._
        self.command_menu.show_line_in_dialog_box(_("The {}?").format(_(selected_item)), hide_arrow=False)
        selected_item_dict = current_store_inventory[selected_item]
        selected_item_type = selected_item_dict['type']
        if self.player.gold >= selected_item_dict['cost']:
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
                                                         _("Oh, yes? That's too bad.")), config=self.config,
                                show_arrow=self.command_menu.game.show_arrow, color=self.color)
        else:
            self.command_menu.show_line_in_dialog_box(_("Sorry.\n"
                                                        "Thou hast not enough money."), hide_arrow=False)
        confirmation_prompt(self.command_menu, _("Dost thou wish to buy anything more?"),
                            yes_path_function=partial(self.open_store_inventory, current_store_inventory,
                                                      static_store_image, self.color),
                            no_path_function=partial(self.command_menu.show_line_in_dialog_box,
                                                     _("Please, come again."), hide_arrow=True), config=self.config,
                            show_arrow=self.command_menu.game.show_arrow, color=self.color)

    def shopkeeper_buy_old_item(self, old_item_cost, old_item, old_item_lookup_table):
        _ = self._
        if old_item:
            if old_item_lookup_table[old_item].get('cost'):
                old_item_cost = old_item_lookup_table[old_item]['cost'] // 2
                self.command_menu.show_line_in_dialog_box(
                    _("Then I will buy thy {} for {} GOLD.").format(self._(old_item), old_item_cost), hide_arrow=False)
        return old_item_cost

    def complete_transaction(self, item, current_store_inventory, old_item_cost):
        _ = self._
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
        _ = self._
        confirmation_prompt(self.command_menu, self.get_inn_intro(inn_cost),
                            yes_path_function=partial(self.check_money, inn_cost),
                            no_path_function=partial(self.command_menu.show_line_in_dialog_box,
                                                     _("Okay.\n"
                                                       "Good-bye, traveler."),
                                                     skip_text=self.command_menu.skip_text, hide_arrow=True),
                            config=self.command_menu.game.game_state.config,
                            show_arrow=self.command_menu.game.show_arrow, color=self.color,
                            skip_text=self.command_menu.skip_text)

    def check_money(self, inn_cost):
        _ = self._
        if self.player.gold >= inn_cost:
            self.inn_sleep(inn_cost)
        else:
            self.command_menu.show_line_in_dialog_box(_("Thou hast not enough money."),
                                                      skip_text=self.command_menu.skip_text)

    def inn_sleep(self, inn_cost: int):
        _ = self._
        self.command_menu.show_line_in_dialog_box(_("Good night."), skip_text=self.command_menu.skip_text)
        fade(fade_out=True, screen=self.screen, config=self.config)
        music_enabled = self.command_menu.game.game_state.config['MUSIC_ENABLED']
        tile_size = self.command_menu.game.game_state.config['TILE_SIZE']
        if music_enabled:
            mixer.music.stop()
        self.sound.play_sound(self.directories.special_item_sfx)
        self.player.restore_hp()
        self.player.restore_mp()
        self.player.gold -= inn_cost
        if not self.command_menu.game.game_state.config['NO_WAIT']:
            time.wait(3000)
        if music_enabled:
            mixer.music.load(self.current_map.music_file_path)
            mixer.music.play(-1)
        if not self.command_menu.game.game_state.config['NO_BLIT']:
            self.command_menu.game.drawer.draw_all_tiles_in_current_map(self.current_map, self.background)
            draw_player_sprites(self.current_map, self.background, self.player.column, self.player.row, self.config)
            for character, character_dict in self.current_map.characters.items():
                if character != 'HERO':
                    draw_character_sprites(self.current_map, self.background, character_dict['coordinates'][1],
                                           character_dict['coordinates'][0], self.config, character)
            self.screen.blit(self.background, self.camera_position)
            self.screen.blit(self.command_menu.command_menu_surface, (tile_size * 6, tile_size * 1))
            display.flip()
        self.command_menu.game.color = self.color = WHITE
        self.command_menu.show_text_in_dialog_box((_("Good morning.\nThou seems to have spent a good night."),
                                                   _("I shall see thee again.")), skip_text=self.command_menu.skip_text,
                                                  drop_up=False)
