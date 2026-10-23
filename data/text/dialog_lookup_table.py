import random
from functools import partial
from collections.abc import Callable

from pygame import display, time, Rect
from pygame.event import get, pump

from data.text.dialog import confirmation_prompt
from src.color import BLACK, window_color
from src.common import WHITE, Graphics, set_gettext_language, singular_or_plural
from src.constants import GWAELIN_THRONE_ROOM_COORDINATES, GWAELINS_LOVE_REPLACEABLE_ITEMS
from src.cursor import IN_A
from src.direction import Direction
from src.directories import Directories
from src.items import INVENTORY_SLOTS, MAX_HERBS, MAX_KEYS, UNSLOTTED_ITEMS, inventory_list
from src import maps
from src.maps import DragonWarriorMap
from src.maps_functions import get_center_point
from src.npcs import GWAELIN_RESCUE
from src.window_renderer import draw_window as generated_window
from src.windows import BUY_SELL_LAYOUT, WindowLayout, shop_inventory_layout
from src.menu_functions import draw_player_sprites, draw_character_sprites
from src.shops import ShopInventories, FAIRY_WATER_COST, KEY_COSTS, buyback_price, \
    inventory_is_full, pay_player, sell_price
from src.selection import run_selection, stop_at_edges
from src.sound import Sound
from src.story_flags import StoryFlags
from src.text import draw_text
from src.windows import BUY_SELL_WINDOW, DIALOG_WINDOW, ITEM_MENU_BORDER, ITEM_MENU_FIRST_TILE_ROW, \
    SHOP_COST_RIGHT_TILE_COLUMN, SHOP_INVENTORY_WINDOW, Window, item_menu_window, name_halves, variable_height_window
from src.visual_effects import NES_RED, bw_screen_flash, greyscale_screen, screen_fade
from src.waiting import POLL_INTERVAL_MS, quit_if_requested, wait_frames

NES_MAX_LEVEL = 30  # LVL_30


class DialogLookup:
    @property
    def color(self) -> tuple[int, int, int]:
        """The window color, red when HP is low (Game.load_window_palette)."""
        return self.command_menu.color

    def __init__(self, command_menu, config: dict):
        self.config = config
        self.sound = Sound(config)
        self._ = _ = set_gettext_language(self.config['LANGUAGE'])

        self.shop_inventories = ShopInventories(self.config)
        self.command_menu = command_menu
        self.player = command_menu.player
        self.screen = command_menu.screen
        self.current_map: DragonWarriorMap = command_menu.current_map
        self.background = command_menu.background
        self.camera_position = command_menu.camera_position
        # menu

        self.goodbye_tempt_not_the_fates = _("Goodbye now, {}.\n'Take care and tempt not the Fates.")

        where_is_princess_gwaelin = _("Where oh where can I find Princess Gwaelin?")
        brecconary_inn_cost = 6
        kol_inn_cost = 20
        garinham_inn_cost = 25
        rimuldar_inn_cost = 55
        cantlin_inn_cost = 100

        self.tools_intro = _("Welcome.\n"
                             "We deal in tools.\n"
                             "What can I do for thee?")
        self.directories = Directories(self.config)
        # NES TextBlock13 entry 1: AMTP prints "Point" when exactly 1 is left (Bank01 DoAMTP)
        points_to_next_level = self.player.points_to_next_level
        before_reaching_thy_next_level_of_experience = singular_or_plural(
            points_to_next_level,
            _("Before reaching thy next level of experience thou must gain {} Point."),
            _("Before reaching thy next level of experience thou must gain {} Points.")).format(points_to_next_level)
        # NES TextBlock1 entry 2: King Lorik says this instead of the experience line once DisplayedLevel is LVL_30
        thou_art_strong_enough = _("Thou art strong enough!\nWhy can thou not defeat the Dragonlord?")
        at_max_level = self.player.level == NES_MAX_LEVEL

        self.magic_key_prompt = _("Magic keys!\nThey will unlock any door.\n"
                                  "Dost thou wish to purchase one for {} GOLD?")

        # What each NPC says, by its NES dialog byte (NPC.dialog in the maps' NPC tables, src/npcs.py). Bytes $00-$15
        # are the shops and inns, $16-$5D show the TextBlock entry at the byte + $2F (DoVariousDialog2, Bank03), so $16
        # is TextBlock5 entry 5 and so on, and the rest have their own code (DoDialog). Each comment says who has the
        # byte. Once the Dragonlord is dead, Ending.npc_dialog takes over (NES LD134).
        npc_dialog: dict[int | str, dict] = {
            # WeaponsDialog: the weapons and armor shops
            0x00: {'dialog': (partial(self.check_buy_weapons_armor, self.shop_inventories.kol_weapons_store_inventory),)},
            0x01: {'dialog': (
                partial(self.check_buy_weapons_armor, self.shop_inventories.brecconary_weapons_store_inventory),)},
            0x02: {'dialog': (
                partial(self.check_buy_weapons_armor, self.shop_inventories.garinham_weapons_store_inventory),)},
            # Cantlin's shop 1 is the mobile shopkeeper at 22,5, shop 2 the shopkeeper at 27,26 and shop 3 the guard
            # at 24,12
            0x03: {'dialog': (
                partial(self.check_buy_weapons_armor, self.shop_inventories.cantlin_weapons_store_north_inventory),)},
            0x04: {'dialog': (
                partial(self.check_buy_weapons_armor, self.shop_inventories.cantlin_weapons_store_south_inventory),)},
            0x05: {'dialog': (
                partial(self.check_buy_weapons_armor, self.shop_inventories.cantlin_weapons_store_3_inventory),)},
            0x06: {'dialog': (
                partial(self.check_buy_weapons_armor, self.shop_inventories.rimuldar_weapons_store_inventory),)},
            # ToolsDialog: the item shops (Cantlin's shop 1 is the male villager at 2,7)
            0x07: {'dialog': (partial(self.tool_shop, self.shop_inventories.kol_item_store_inventory),)},
            0x08: {'dialog': (partial(self.tool_shop, self.shop_inventories.brecconary_item_store_inventory),)},
            0x09: {'dialog': (partial(self.tool_shop, self.shop_inventories.garinham_item_store_inventory),)},
            0x0A: {'dialog': (partial(self.tool_shop, self.shop_inventories.cantlin_item_store_1_inventory),)},
            0x0B: {'dialog': (partial(self.tool_shop, self.shop_inventories.cantlin_item_store_2_inventory),)},
            # KeysDialog: the magic key sellers (KeyCostTbl), Cantlin's and Rimuldar's wizards and Tantegel's shopkeeper
            0x0C: {'dialog': (partial(self.check_buy_magic_keys, KEY_COSTS['Cantlin']),)},
            0x0D: {'dialog': (partial(self.check_buy_magic_keys, KEY_COSTS['Rimuldar']),)},
            0x0E: {'dialog': (partial(self.check_buy_magic_keys, KEY_COSTS['TantegelCourtyard']),)},
            # FairyDialog: Brecconary's mobile female villager at 24,4 and Cantlin's female villager at 22,13
            0x0F: {'dialog': (self.fairy_water_shop,)},
            0x10: {'dialog': (self.fairy_water_shop,)},
            # InnDialog: the inns (InnCostTbl), in Kol, Brecconary, Garinham, Cantlin and Rimuldar
            0x11: {'dialog': (partial(self.check_stay_at_inn, kol_inn_cost),)},
            0x12: {'dialog': (partial(self.check_stay_at_inn, brecconary_inn_cost),)},
            0x13: {'dialog': (partial(self.check_stay_at_inn, garinham_inn_cost),)},
            0x14: {'dialog': (partial(self.check_stay_at_inn, cantlin_inn_cost),)},
            0x15: {'dialog': (partial(self.check_stay_at_inn, rimuldar_inn_cost),)},
            # Tantegel: the mobile fighter at 25,11 (TextBlock5 entry 5)
            0x16: {'dialog': _("I am looking for the castle cellar.\nI heard it is not easily found.")},
            # Tantegel: the mobile guard at 19,2 (TextBlock5 entry 6)
            0x17: {'dialog': _("Thou must have a key to open a door.")},
            # Tantegel: the male villager at 2,8 (TextBlock5 entry 7)
            0x18: {'dialog': _("To become strong enough to face future trials thou must first battle many foes.")},
            # Tantegel: the guard at 8,6 (TextBlock5 entry 8)
            0x19: {'dialog': (
                _("King Lorik will record thy deeds in his Imperial Scroll so thou may return to thy quest later."),)},
            # Tantegel: the female villager at 27,5 (TextBlock5 entry 9, then TextBlock12 entry 0)
            0x1A: {'dialog': (_("When the sun and rain meet, a Rainbow Bridge shall appear."), _("It's a legend."))},
            # Tantegel: the mobile guard at 2,12 (TextBlock5 entry 10)
            0x1B: {'dialog': _("Never does a brave person steal.")},
            # Tantegel: the mobile male villager at 11,11 (TextBlock5 entry 11)
            0x1C: {'dialog': _("There was a time when Brecconary was a paradise.\nThen the Dragonlord's minions came.")},
            # Tantegel: the mobile wizard at 17,11 (TextBlock5 entry 12)
            0x1D: {'dialog': (_("Let us wish the warrior well!"), _("May the light be thy strength!"))},
            # Tantegel: the guard at 26,15 (TextBlock5 entry 13)
            0x1E: {'dialog': _("If thy Hit Points are high enough, by all means, enter.")},
            # Tantegel: the mobile shopkeeper at 4,21 (TextBlock5 entry 14)
            0x1F: {'dialog': _("We are merchants who have traveled much in this land.\n"
                               "Many of our colleagues have been killed by servants of the Dragonlord.")},
            # Tantegel: the mobile shopkeeper at 6,25 (TextBlock5 entry 15)
            0x20: {'dialog': _("Rumor has it that entire towns have been destroyed by the Dragonlord's servants.")},
            # Tantegel: the gate guards at 9,27 and 12,27 (TextBlock6 entry 0)
            0x21: {'dialog': _("Welcome to Tantegel Castle.")},
            # Tantegel: the mobile fighter at 24,21 (TextBlock6 entry 1; the ROM has no space in "Garinham,look")
            0x22: {'dialog': _("In Garinham,look for the grave of Garin.\n"
                               "Thou must push on a wall of darkness there.")},
            # The throne room: the guard at 3,6. NES RegularDialog: until F_LEFT_THROOM is set it's TextBlock17 entry
            # 1, then DoVariousDialog1 shows the byte + $2F, TextBlock6 entry 2
            0x23: {'dialog': (partial(
                self.dialog_once_left_throne_room,
                (_("East of this castle is a town where armor, weapons, and many other items may be purchased."),
                 _("Return to the Inn for a rest if thou art wounded in battle, {}.").format(self.player.name),
                 _("Sleep heals all.")),
                (_("A word of advice."), _("Save thy money for more expensive armor."))),)},
            # The throne room: the guard at 5,6 (ThrnRmDialog2): TextBlock17 entry 0, then TextBlock6 entry 3
            0x24: {'dialog': (partial(
                self.dialog_once_left_throne_room,
                (_("If thou hast collected all the Treasure Chests,\na key will be found."),
                 _("Once used, the key will disappear, but the door will be open and thou may pass through.")),
                (_("Listen to what people say.\nIt can be of great help."),)),)},
            # Brecconary: the fighter at 28,1 (TextBlock6 entry 4)
            0x25: {'dialog': (_("Beware the bridges!"), _("Danger grows when thou crosses."))},
            # Brecconary: the male villager at 20,10 (TextBlock6 entry 5)
            0x26: {'dialog': _("There is a town where magic keys can be purchased.")},
            # Brecconary: the mobile fighter at 3,26 (TextBlock6 entry 6)
            0x27: {'dialog': _("Some say that Garin's grave is home to a Silver Harp.")},
            # Brecconary: the male villager at 20,23 (TextBlock6 entry 7)
            0x28: {'dialog': _("Enter where thou can.")},
            # Brecconary: the female villager at 4,7 (TextBlock6 entry 8). The space before the line break isn't in the
            # NES text, but it doesn't show and the translations are keyed on it.
            0x29: {'dialog': _("Welcome! \n"
                               "Enter the shop and speak to its keeper across the desk.")},
            # Brecconary: the male villager at 1,13 (TextBlock6 entry 9)
            0x2A: {'dialog': _("Thou art most welcome in Brecconary.")},
            # Brecconary: the mobile wizard at 9,4 (TextBlock6 entry 10)
            0x2B: {'dialog': _("Watch thy Hit Points when in the Poisonous Marsh.")},
            # Brecconary: the mobile male villager at 10,14 (TextBlock6 entry 11)
            0x2C: {'dialog': _("Go north to the seashore, then follow the coastline west until thou hath "
                               "reached Garinham.")},
            # Brecconary: the mobile female villager at 15,24 (TextBlock6 entry 12)
            0x2D: {'dialog': _("No,I am not Princess Gwaelin.")},
            # Brecconary: the mobile shopkeeper at 15,9, and Kol: the mobile female villager at 11,14 (TextBlock6
            # entry 13)
            0x2E: {'dialog': _("Please,save us from the minions of the Dragonlord.")},
            # Brecconary: the mobile guard at 26,15 (TextBlock6 entry 14)
            0x2F: {'dialog': _("See King Lorik when thy experience levels are raised.")},
            # Brecconary: the mobile fighter at 19,18, Kol: the mobile male villager at 5,12, and Rimuldar: the mobile
            # male villager at 11,8 (TextBlock6 entry 15)
            0x30: {'dialog': _("Art thou the descendant of Erdrick?\n"
                               "Hast thou any proof?")},
            # Brecconary: the mobile male villager at 25,22 (TextBlock7 entry 0)
            0x31: {'dialog': (_("Within sight of Tantegel Castle to the south is Charlock,"),
                              _("The fortress of the Dragonlord."))},
            # Kol: the female villager at 12,1 (TextBlock7 entry 1)
            0x32: {'dialog': _("This bath cures rheumatism.")},
            # Kol: the fighter at 20,13 (TextBlock7 entry 2)
            0x33: {'dialog': _("East of Hauksness there is a town, ʼtis said, where one may purchase "
                               "weapons of extraordinary quality.")},
            # Kol: the guard at 1,23 (TextBlock7 entry 3)
            0x34: {'dialog': _("Rimuldar is the place to buy keys.")},
            # Kol: the mobile fighter at 6,7 (TextBlock7 entry 4)
            0x35: {'dialog': _("Hast thou seen Nester?\nI think he may need help.")},
            # Kol: the mobile male villager at 14,13 (TextBlock7 entry 5)
            0x36: {'dialog': (_("Dreadful is the South Island."),
                              _("Great strength and skill and wit only will bring thee back from that place."))},
            # Kol: the mobile guard at 12,10 (TextBlock7 entry 6)
            0x37: {'dialog': _("Golem is afraid of the music of the flute, so ʼtis said.")},
            # Kol: the mobile wizard at 20,19 (TextBlock7 entry 7)
            0x38: {'dialog': _("This is the village of Kol.")},
            # Kol: the mobile wizard at 20,8 (TextBlock7 entry 8)
            0x39: {'dialog': _("In legends it is said that fairies know how to put Golem to sleep.")},
            # Garinham: the wizard at 14,1 (TextBlock7 entry 9)
            0x3A: {'dialog': _("The harp attracts enemies.\nStay away from the grave in Garinham.")},
            # Garinham: the guards at 3,5 and 5,5 (TextBlock7 entry 10)
            0x3B: {'dialog': _("I'm too busy.\nAsk the other guard.")},
            # Garinham: the shopkeeper at 9,6 (TextBlock7 entry 11)
            0x3C: {'dialog': _("I suggest making a map if thy path leads into the darkness.")},
            # Garinham: the mobile male villager at 11,7 (TextBlock7 entry 12)
            0x3D: {'dialog': _("Once there was a town called Hauksness far to the south,but I do not know if "
                               "it still exists.")},
            # Garinham: the mobile female villager at 12,4 (TextBlock7 entry 13)
            0x3E: {'dialog': _("I hate people!\nGo! Leave me!")},
            # Garinham: the mobile wizard at 12,8 (TextBlock7 entry 14)
            0x3F: {'dialog': _("They say that Erdrick's armor was hidden long ago.")},
            # Garinham: the wizard at 2,17 (TextBlock7 entry 15)
            0x40: {'dialog': _("Many believe that Princess Gwaelin is hidden away in a cave.")},
            # Garinham: the mobile fighter at 7,17 (TextBlock8 entry 0)
            0x41: {'dialog': _("I have heard of one named Nester.\nDost thou know such a one?")},
            # Garinham: the mobile wizard at 2,10 (TextBlock8 entry 1)
            0x42: {'dialog': _("Garin, a wandering minstrel of legendary fame, is said to have built this town.")},
            # Garinham: the mobile female villager at 12,12 (TextBlock8 entry 2)
            0x43: {'dialog': _("Welcome to Garinham.\nMay thy stay be a peaceful one.")},
            # Garinham: the mobile male villager at 18,12 (TextBlock8 entry 3)
            0x44: {'dialog': _("It is said that the Princess was kidnapped and taken eastward.")},
            # Cantlin: the shopkeeper at 2,12 (TextBlock8 entry 4)
            0x45: {'dialog': _("Come buy my radishes! They are fresh and cheap.\nBuy thy radishes today!")},
            # Cantlin: the wizard at 15,16 (TextBlock8 entry 5)
            0x46: {'dialog': _("To learn how proof may be obtained that thy ancestor was the great Erdrick, "
                               "see a man in this very town.")},
            # Cantlin: the wizard at 22,22 (TextBlock8 entry 6)
            0x47: {'dialog': _("ʼTis said that Erdrick's sword could cleave steel.")},
            # Cantlin: the mobile guard at 15,6 (TextBlock8 entry 7)
            0x48: {'dialog': _("Welcome to Cantlin, the castle town.")},
            # Cantlin: the mobile female villager at 4,14 (TextBlock8 entry 8)
            0x49: {'dialog': _("What shall I get for thy dinner?")},
            # Cantlin: the mobile female villager at 9,16 (TextBlock8 entry 9)
            0x4A: {'dialog': _("I know nothing.")},
            # Cantlin: the mobile male villager at 20,15 (TextBlock8 entry 10)
            0x4B: {'dialog': _("I'm Nester.\nHey, where am I? No, don't tell me!")},
            # Cantlin: the mobile shopkeeper at 25,17 (TextBlock8 entry 11)
            0x4C: {'dialog': _("Grandfather used to say that his friend, Wynn, had buried something of "
                               "great value at the foot of a tree behind his shop.")},
            # Cantlin: the mobile guard at 22,9 (TextBlock8 entry 12)
            0x4D: {'dialog': (_("It is said that many have held Erdrick's armor."),
                              _("The last to have it was a fellow named Wynn."))},
            # Cantlin: the mobile shopkeeper at 3,26 (TextBlock8 entry 13)
            0x4E: {'dialog': _("My Grandfather Wynn once had a shop on the east side of Hauksness.")},
            # Rimuldar: the shopkeeper at 2,4 (TextBlock8 entry 14)
            0x4F: {'dialog': _("Welcome!")},
            # Rimuldar: the female villager at 15,8 (TextBlock8 entry 15)
            0x50: {'dialog': _("Who art thou?\nLeave at once or I will call my friends.")},
            # Rimuldar: the male villager at 27,0 (TextBlock9 entry 0)
            0x51: {'dialog': _("I am Orwick, and I am waiting for my girl friend.")},
            # Rimuldar: the mobile fighter at 23,11 (TextBlock9 entry 1)
            0x52: {'dialog': _("The scales of the Dragonlord are as hard as steel.")},
            # Rimuldar: the wizard at 6,13 (TextBlock9 entry 2)
            0x53: {'dialog': (_("Over the western part of this island Erdrick created a rainbow."),
                              _("ʼTis also said that he entered the darkness from a hidden entrance in "
                                "the room of the Dragonlord."))},
            # Rimuldar: the mobile guard at 8,16 (TextBlock9 entry 3)
            0x54: {'dialog': _("Thou shalt find the Stones of Sunlight in Tantegel Castle,\nif thou has not "
                               "found them yet.")},
            # Rimuldar: the mobile male villager at 14,11 (TextBlock9 entry 4)
            0x55: {'dialog': _("Welcome to the town of Rimuldar.")},
            # Rimuldar: the mobile female villager at 22,14 (TextBlock9 entry 5)
            0x56: {'dialog': _("No, I have no tomatoes.\nI have no tomatoes today.")},
            # Rimuldar: the mobile fighter at 24,19 (TextBlock9 entry 6)
            0x57: {'dialog': _("You are {}?\nIt has been long since last we met.").format(self.player.name)},
            # Rimuldar: the wizard at 20,23 (TextBlock9 entry 7)
            0x58: {'dialog': _("Good day,I am Howard. Four steps south of the bath in Kol thou shalt "
                               "find a magic item.")},
            # Rimuldar: the mobile female villager at 6,21 (TextBlock9 entry 8)
            0x59: {'dialog': _("Before long the enemy will arrive.")},
            # Rimuldar: the mobile male villager at 6,23 (TextBlock9 entry 9)
            0x5A: {'dialog': _("Heed my warning! Travel not to the south for there the monsters are fierce "
                               "and terrible.")},
            # Rimuldar: the mobile fighter at 5,25 (TextBlock9 entry 10)
            0x5B: {'dialog': _("In this world is there any sword that can pierce the scales of the "
                               "Dragonlord?")},
            # Rimuldar: the female villager at 0,26 (TextBlock9 entry 11)
            0x5C: {'dialog': _("Orwick is late again. I'm starving.")},
            # Brecconary: the mobile fighter at 12,19 (TextBlock9 entry 12)
            0x5D: {'dialog': (_("Many have been the warriors who have perished on this quest."),
                              _("But for thee I wish success, {}.").format(self.player.name))},
            # Kol: the mobile wizard at 2,12 (CheckYesNoDialog): TextBlock9 entry 13, then a yes/no window
            0x5E: {'dialog': (self.kol_hast_thou_found_the_flute,)},
            # Kol: the mobile shopkeeper at 7,19 (CheckYesNoDialog): TextBlock9 entry 14, then a yes/no window
            0x5F: {'dialog': (self.kol_hast_thou_been_to_the_southern_island,)},
            # Cantlin: the mobile guard at 5,6 (CheckYesNoDialog): TextBlock9 entry 15, then a yes/no window
            0x60: {'dialog': (_("ʼTis said that the Dragonlord hath claws that can cleave iron and fiery "
                                "breath that can melt stone."),
                              self.cantlin_still_wish_to_go_on)},
            # Rimuldar: the wizard at 3,23 (CheckYesNoDialog): TextBlock10 entry 0, then a yes/no window
            0x61: {'dialog': (_("This is a magic place."), self.rimuldar_hast_thou_found_a_magic_temple)},
            # Tantegel: the mobile female villager at 8,13 (ChkPrncsDialog1)
            0x62: {'dialog': (partial(self.dialog_once_gwaelin_rescued, where_is_princess_gwaelin,
                                      _("Thank you for saving the Princess.")),)},
            # Tantegel: the guard at 15,20 (ChkPrncsDialog2)
            0x63: {'dialog': (partial(self.dialog_once_gwaelin_rescued, where_is_princess_gwaelin,
                                      _("Oh, my dearest Gwaelin!’\n`I hate thee, {}.").format(self.player.name)),)},
            # Brecconary: the guard at 10,26 (ChkPrncsDialog3): TextBlock10 entry 14, or entry 15 once F_DONE_GWAELIN
            # is set
            0x64: {'dialog': (partial(self.dialog_once_gwaelin_rescued,
                                      (_("Tell King Lorik that the search for his daughter hath failed."),
                                       _("I am almost gone....")),
                                      _("Who touches me?’\n`I see nothing, nor can I hear.")),)},
            # The throne room: the mobile guard at 7,5 (ChkPrncsDialog4)
            0x65: {'dialog': (self.tantegel_throne_room_roaming_guard,)},
            # Tantegel's cellar: the wizard at 4,6 (WzdGuardDialog)
            0x66: {'dialog': (self.tantegel_cellar_stones_of_sunlight_guardian,)},
            # Brecconary: the wizard at 24,10 (ChkCursedDialog)
            0x67: {'dialog': (self.remove_curse,)},
            # Kol: the wizard at 1,1 (ChkWeaponDialog): TextBlock11 entry 9, or entry 10 with Erdrick's Sword
            0x68: {'dialog': (self.kol_erdricks_sword_wizard,)},
            # Rimuldar: the mobile fighter at 16,26 (ChkRingDialog)
            0x69: {'dialog': (self.rimuldar_fighters_ring_dialog,)},
            # Tantegel: the wizard at 20,26 (ChkMagicDialog): TextBlock11 entry 13, BWScreenFlash, MP to the max
            0x6A: {'dialog': (
                _("{}'s coming was foretold by legend.\nMay the light shine upon this brave warrior.").format(
                    self.player.name),
                self.flash_and_restore_mp)},
            # Cantlin: the mobile wizard at 14,28 (ErdTknDialog): TextBlock5 entry 12, then TextBlock11 entries 14 and
            # 15. He only gives the hint; the token itself is found on the overworld.
            0x6B: {'dialog': (_("Let us wish the warrior well!"),
                              _("May the light be thy strength!"),
                              _("Thou may go and search."),
                              _("From Tantegel Castle travel 70 leagues to the south and 40 to the "
                                "east."))},
            # The Staff of Rain shrine's wizard (RainStaffDialog)
            0x6C: {'dialog': (self.staff_of_rain_guardian,)},
            # The Rainbow Drop shrine's wizard (RnbwDrpDialog)
            0x6D: {'dialog': (self.magic_temple_rainbow_drop_exchange,)},
            # The throne room: King Lorik (DoKingDialog). 'dialog' starts as the opening speech (MainGameEngine,
            # TextBlock17 entry 2) and CommandMenu.set_king_lorik_dialog switches it as the story goes on.
            0x6E: {
                'dialog': (
                    _("Descendant of Erdrick, listen now to my words."),
                    _("It is told that in ages past Erdrick fought demons with a Ball of Light."),
                    _("Then came the Dragonlord who stole the precious globe and hid it in the darkness."),
                    _("Now, {}, thou must help us recover the Ball of Light and restore peace to our land.").format(
                        self.player.name),
                    _("The Dragonlord must be defeated."),
                    _("Take now whatever thou may find in these Treasure Chests to aid thee in thy quest."),
                    _("Then speak with the guards, for they have much knowledge that may aid thee."),
                    _("May the light shine upon thee, {}.").format(self.player.name)
                ),
                'post_initial_dialog': _(
                    "When thou art finished preparing for thy departure, please see me.\nI shall wait."),
                # NES DoKingDialog, KingDialog2/LeftThRoom: TextBlock13 entry 0, then TextBlock1 entry 2 at
                # level 30 (LVL_30) or TextBlock13 entry 1 (GetExpRemaining) below it, then SaveDialog
                'returned_dialog': (
                    _("I am greatly pleased that thou hast returned, {}.").format(self.player.name),
                    thou_art_strong_enough if at_max_level else before_reaching_thy_next_level_of_experience,
                    self.prompt_for_save,
                    self.prompt_to_continue_quest,
                ),
                # NES MainGameEngine (LCA23): TextBlock18 entry 7, then at level 30 TextBlock1 entry 2 and
                # straight on to EndKingDialog; below it TextBlock13 entry 1 and TextBlock18 entry 8
                'load_from_save_dialog': (self._("I am glad thou hast returned.\n"
                                                 "All our hopes are riding on thee."),
                                          *((thou_art_strong_enough,) if at_max_level else (
                                              before_reaching_thy_next_level_of_experience,
                                              self._("See me again when thy level has increased."))),
                                          self.goodbye_tempt_not_the_fates.format(self.player.name)
                                          ),
                # NES KingDeathDialog (LEDF2): TextBlock17 entry 13, TextBlock18 entry 2 unless the hero is
                # level 30 (NowGoText skips it), then entry 3
                'post_death_dialog': (_("Death should not have taken thee, {}.").format(self.player.name),
                                      _("I will give thee another chance."),
                                      *(() if at_max_level else (
                                          singular_or_plural(
                                              points_to_next_level,
                                              _("To reach the next level, thy Experience Point must increase by {}."),
                                              _("To reach the next level, thy Experience Points must increase by {}.")
                                          ).format(points_to_next_level),)),
                                      _("Now, go, {}!").format(self.player.name)),
                # NES DoKingDialog (Bank03), when F_GOT_GWAELIN is set: TextBlock12 entry 9, AddInvItem
                # (Gwaelin's Love), entries 11 and 12, then Gwaelin is put on the throne and it goes straight
                # to SaveDialog. No experience or gold is given.
                'carrying_princess_dialog': (
                    _("Forever shall I be grateful for the gift of my daughter returned to her home, {}.\n"
                      "Accept my thanks.").format(self.player.name),
                    _("Now, Gwaelin, come to my side."),
                    self.princess_whispers,
                    _("Please accept my love, {}.").format(self.player.name),
                    self.receive_gwaelins_love,
                    self.even_when_we_two_are_parted,
                    _("Farewell, {}.").format(self.player.name),
                    self.put_princess_on_throne,
                    self.prompt_for_save,
                    self.prompt_to_continue_quest,
                ),
            },
            # The throne room: Princess Gwaelin (PrincessDialog), only there once she's been returned (ChkGwaelinNPC)
            0x6F: {'dialog': (self.princess_gwaelin_throne_room,)},
            # Charlock: the Dragonlord. DoDrgnLrdDialog (Bank03): TextBlock13 entries 7 and 8 around TextBlock11 entry
            # 4, then the yes/no window.
            0x70: {'dialog': (
                _("Welcome, {}.\nI am the Dragonlord--King of Kings.").format(self.player.name),
                _("I have been waiting long for one such as thee."),
                _("I give thee now a chance to share this world and to rule half of it if thou will now stand "
                  "beside me."),
                self.dragonlord_offer_prompt,
            )},
            # Tantegel: the guard at 8,8 (GuardDialog1: TextBlock1 entry 3)
            0x71: {'dialog': _("If thou art planning to take a rest, first see King Lorik.")},
            # Tantegel: the mobile guard at 18,18 (GuardDialog2: TextBlock10 entry 1)
            0x72: {'dialog': _("When entering the cave, take with thee a torch.")},
            # Gwaelin in the Swamp Cave. NES DoTalkResults / DoGwaelinRescue (Bank03): TextBlock12 entry 5, then
            # PrincessRescueLoop (TextBlock13 entry 5 and a yes/no window, "But thou must." (TextBlock12 entry 6) until
            # the answer is yes)
            GWAELIN_RESCUE: {'dialog': (_("Thou art brave indeed to rescue me, {}.").format(self.player.name),
                                        _("I am Gwaelin, daughter of Lorik."),
                                        self.take_to_castle_confirmation_prompt)},
        }
        # Map name -> NPC identifier -> what it says, for every NPC in the maps' NPC tables. Each NPC gets its own copy
        # of its dialog byte's entry (set_king_lorik_dialog changes King Lorik's 'dialog').
        self.lookup_table: dict[str, dict[str, dict]] = {}
        for map_name, map_class in maps.map_lookup.items():
            for npc in map_class.npc_table:  # type: ignore[attr-defined]
                if npc.dialog in npc_dialog:
                    self.lookup_table.setdefault(map_name, {})[npc.name] = {**npc_dialog[npc.dialog],
                                                                            'dialog_character': npc.name}

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
        """NES DoGwaelinRescue (Bank03, LD072-LD09A): F_GOT_GWAELIN is set and DoSprites draws the hero carrying her,
        and ModMapBlock removes her block, all before "Princess Gwaelin embraces thee" and the music."""
        self.command_menu.game.story_flags.carrying_gwaelin = True
        self.player.images = self.current_map.scale_sprite_sheet(self.directories.HERO_CARRYING_PRINCESS_PATH)
        self.player.set_images(self.player.images)
        self.player.show_facing()
        self.command_menu.show_character_now(self.player)
        gwaelin = self.current_map.characters.pop('PRINCESS_GWAELIN', None)
        self.current_map.fixed_characters = []
        if gwaelin is not None:
            self.command_menu.erase_character_now(gwaelin['character'])

        self.command_menu.show_line_in_dialog_box(self._("Princess Gwaelin embraces thee.\n"),
                                                  add_quotes=False)
        # NES DoGwaelinRescue: MSC_PRNCS_LOVE right after the line, WaitForMusicEnd, then MSC_DUNGEON1 (the map's music)
        self.play_gwaelins_love_music()
        self.command_menu.show_line_in_dialog_box(self._("I'm so happy!"))

    def but_thou_must(self, original_function):
        self.command_menu.show_line_in_dialog_box(self._("But thou must."))
        original_function()

    def dragonlord_offer_prompt(self):
        """NES DoDrgnLrdDialog: answering no goes straight to the fight, answering yes gets a second chance
        ("Really?", TextBlock18 entry 6) before the bad ending."""
        return confirmation_prompt(
            self.command_menu,
            self._("What sayest thou?\nWill the great warrior stand with me?"),
            yes_path_function=self.dragonlord_really_prompt,
            no_path_function=self.refuse_dragonlord,
            config=self.config,
            show_arrow=self.command_menu.game.show_arrow,
            color=self.color)

    def dragonlord_really_prompt(self):
        return confirmation_prompt(
            self.command_menu,
            self._("Really?"),
            yes_path_function=self.join_dragonlord,
            no_path_function=self.refuse_dragonlord,
            config=self.config,
            show_arrow=self.command_menu.game.show_arrow,
            color=self.color)

    def refuse_dragonlord(self):
        """NES RefuseDglrdDialog: "Thou art a fool!", a 40-frame pause, then the dialog, command and pop-up
        windows close and the fight with the Dragonlord's first form (EN_DRAGONLORD1) starts."""
        self.command_menu.show_line_in_dialog_box(self._("Thou art a fool!"), hide_arrow=True, skip_text=True)
        wait_frames(40, self.config)
        self.command_menu.game.battle_ctrl.queue_scripted_battle('Dragonlord')

    def join_dragonlord(self):
        """NES ChooseDrgnLrd / ZeroStats: the bad ending. The Dragonlord answers (TextBlock13 entries 10 and 2),
        the player's experience, gold, items, equipment, spells and flags are all zeroed, "Thy journey is over"
        (entry 11) is shown, the background palettes switch to BadEndBGPal (show_bad_ending_palette), the pop-up
        status window opens, and the game spinlocks (Spinlock3) until the console is reset."""
        _ = self._
        self.command_menu.show_line_in_dialog_box(
            _("Then half of this world is thine, half of the darkness, and...."))
        self.command_menu.show_line_in_dialog_box(
            _("If thou dies I can bring thee back for another attempt without loss of thy deeds to date."))
        self.zero_stats_for_bad_ending()
        journey_is_over = _("Thy journey is over.\nTake now a long, long rest.\nHahahaha....")
        self.command_menu.show_line_in_dialog_box(journey_is_over, add_quotes=False, hide_arrow=True,
                                                  skip_text=True)
        self.show_bad_ending_palette()
        self.bad_ending_spinlock()

    def zero_stats_for_bad_ending(self):
        """NES ZeroStats: experience, gold, inventory (items, keys and herbs), equipment, spells and the player
        and story flags are cleared. HP, MP and the displayed level are left alone."""
        game = self.command_menu.game
        self.player.total_experience = 0
        self.player.gold = 0
        self.player.inventory = []
        self.player.weapon = self.player.armor = self.player.shield = ""
        self.player.spells = []
        # ModsnSpells is zeroed too: the worn-item bits as well as the Rainbow Bridge and Charlock passage flags
        self.player.wearing_dragon_scale = self.player.wearing_fighters_ring = False
        self.player.wearing_cursed_belt = self.player.wearing_death_necklace = False
        game.story_flags = StoryFlags()
        self.player.update_attack_power()
        self.player.update_defense_power()

    def show_bad_ending_palette(self):
        """NES ChooseDrgnLrd (Bank03, LD515-LD52D): BadEndBGPal is loaded into the background palettes (PrepBGPalLoad),
        then the pop-up window is shown again (Dowindow WND_POPUP). BadEndBGPal is $16 (red) for background palette 0's
        color 1 and black for every other background color, so the windows (the COMMAND, dialog and pop-up windows)
        turn red on black, the map goes black but for the palette 0 blocks' color 1 pixels, which turn red too
        (DragonWarriorMap.load_bad_ending_palette), and the hero and the Dragonlord, which are sprites, keep their
        colors. PrepBGPalLoad's AddPalByte still runs ChkLowHPPal on that color: ZeroStats doesn't touch HitPoints, so
        if HP is low it is the low HP red ($26) instead of $16."""
        game = self.command_menu.game
        color = window_color(self.player.current_hp, self.player.max_hp)
        color = NES_RED if color == WHITE else color
        game.set_window_color(color)
        current_map = game.current_map
        current_map.load_bad_ending_palette(color)
        drawer = game.drawer
        if not self.config['NO_BLIT'] and drawer.background is not None:
            drawer.draw_all_tiles_in_current_map(current_map, drawer.background)
            drawer.handle_sprite_drawing_and_animation(current_map, game.foreground_rects, drawer.background, False)
            self.screen.blit(drawer.background, game.camera.pos)
            self.command_menu.redraw_command_window()
            self.command_menu.draw_dialog_window()
        drawer.draw_hovering_stats_window(self.screen, self.player, color)
        display.flip()

    def bad_ending_spinlock(self):
        """NES Spinlock3: the game hangs here, and only a reset gets out. Closing the window is the
        equivalent."""
        while True:
            for current_event in get():
                quit_if_requested(current_event)
            pump()
            time.wait(16)

    def princess_whispers(self):
        # NES TextBlock12 entry 9 (the ROM really has no space in "moment,please")
        self.command_menu.show_text_line_in_dialog_box(
            line=self._("Gwaelin then whispers:\n"
                        "`Wait a moment,please.\n"
                        "I would give a present to {}.’").format(self.player.name),
            add_quotes=False, disable_sound=False, hide_arrow=False, letter_by_letter=True, skip_text=False,
            temp_text_start=None, tile_size=self.config['TILE_SIZE'])

    def receive_gwaelins_love(self):
        """NES DoKingDialog: AddInvItem gives Gwaelin's Love. If the inventory is full, TakeItemLoop takes the first
        item from InvListTbl that the hero has to make room, and TextBlock12 entry 10 asks for it. If none of those
        items is there, Gwaelin's Love isn't given at all."""
        _ = self._
        used_slots = [item for item in self.player.inventory if item not in UNSLOTTED_ITEMS]
        if len(used_slots) >= INVENTORY_SLOTS:
            taken_item = next((item for item in GWAELINS_LOVE_REPLACEABLE_ITEMS if item in self.player.inventory),
                              None)
            if taken_item is None:
                return
            # TakeItemFound (LD3D8): RemoveInvItem leaves the F_DRGSCALE/F_FTR_RING flags as they are, as selling
            # does, so a Dragon's Scale or Fighter's Ring that is taken stays worn
            self.player.inventory.remove(taken_item)
            self.player.inventory.append("Gwaelin's Love")
            self.command_menu.show_line_in_dialog_box(
                _("And I would like to have something of thine--a token."))
            self.command_menu.show_line_in_dialog_box(_("Please give me thy {}.").format(_(taken_item)))
            return
        self.player.inventory.append("Gwaelin's Love")

    def even_when_we_two_are_parted(self):
        self.command_menu.show_line_in_dialog_box(
            self._("Even when we two are parted by great distances, I shall be with thee."))

    def put_princess_on_throne(self):
        """NES DoKingDialog: clear F_GOT_GWAELIN, set F_RTN_GWAELIN and place Gwaelin's NPC beside the king."""
        game = self.command_menu.game
        game.story_flags.carrying_gwaelin = False
        game.story_flags.gwaelin_returned = True
        game.set_player_images_by_equipment()
        current_map = game.current_map
        if current_map.identifier == 'TantegelThroneRoom' and 'PRINCESS_GWAELIN' not in current_map.characters:
            row, column = GWAELIN_THRONE_ROOM_COORDINATES
            current_map.include_npc('PRINCESS_GWAELIN')
            current_map.center_pt = get_center_point(column, row, tile_size=self.config['TILE_SIZE'])
            princess = current_map.character_key['PRINCESS_GWAELIN']
            current_map.map_npc('PRINCESS_GWAELIN', Direction.DOWN.value, princess['underlying_tile'],
                                princess['path'], princess['four_sided'], GWAELIN_THRONE_ROOM_COORDINATES,
                                is_roaming=False)

    def princess_gwaelin_throne_room(self):
        """NES PrincessDialog: two random bits pick what Gwaelin says when spoken to in the throne room."""
        _ = self._
        random_bits = random.randint(0, 3)
        if random_bits == 0:
            self.even_when_we_two_are_parted()
        elif random_bits == 3:
            self.command_menu.show_line_in_dialog_box(_("I love thee, {}.").format(self.player.name))
        else:
            self.dost_thou_love_me()

    def dost_thou_love_me(self):
        # NES PrncsRndDialog2: she asks until the answer is yes
        return confirmation_prompt(
            self.command_menu,
            self._("Dost thou love me, {}?").format(self.player.name),
            yes_path_function=self.im_so_happy,
            no_path_function=partial(self.but_thou_must, self.dost_thou_love_me),
            config=self.config,
            show_arrow=self.command_menu.game.show_arrow,
            color=self.color)

    def im_so_happy(self):
        # NES PrncsLoveDialog: "I'm so happy!", then the Gwaelin's Love clip, then the throne room music again
        self.command_menu.show_line_in_dialog_box(self._("I'm so happy!"))
        self.play_gwaelins_love_music()

    def play_gwaelins_love_music(self):
        """NES MSC_PRNCS_LOVE, then WaitForMusicEnd, then the map's music again from the start (MSC_DUNGEON1 in the
        Swamp Cave, LD09F; MSC_THRN_ROOM in the throne room, LD49C)."""
        music_player = self.command_menu.game.music_player
        music_player.play_until_end(self.directories.princess_gwaelins_love_music, self.config)
        music_player.load_and_play_music(self.command_menu.game.current_map.music_file_path)

    def dialog_once_gwaelin_rescued(self, not_saved_dialog, saved_dialog):
        """NES ChkPrncsDialog1-4: these NPCs change what they say once F_DONE_GWAELIN is set, which is as soon as
        the hero is carrying Gwaelin, not just once she's been returned."""
        dialog = saved_dialog if self.command_menu.game.story_flags.gwaelin_rescued else not_saved_dialog
        self.command_menu.show_text_in_dialog_box(dialog, add_quotes=True, skip_text=self.command_menu.skip_text,
                                                  drop_down=False, drop_up=False)

    def dialog_once_left_throne_room(self, first_visit_dialog, later_dialog):
        """NES RegularDialog: the throne room's static guards (dialog bytes $23 and $24) say TextBlock17 entries 1 and 0
        until F_LEFT_THROOM is set, then the byte + $2F like any other NPC (DoVariousDialog1)."""
        self.say(*(later_dialog if self.command_menu.game.story_flags.left_throne_room else first_visit_dialog))

    def say(self, *lines, hide_arrow=False):
        """Show NPC lines in the dialog box that is already open."""
        for line in lines:
            self.command_menu.show_line_in_dialog_box(line, hide_arrow=hide_arrow, skip_text=self.command_menu.skip_text)

    def remove_curse(self):
        """NES ChkCursedDialog: the Brecconary wizard (dialog $67, NES (24, 10)) lifts any curse, free of charge."""
        if not self.player.is_cursed:
            lines = (self._("If thou art cursed, come again."),)
        else:
            lines = (self._("I will free thee from thy curse."), self.player.remove_curse, self._("Now, go."))
        for line in lines:
            self.command_menu.show_line_in_dialog_box(line, add_quotes=True, skip_text=self.command_menu.skip_text)

    def kol_erdricks_sword_wizard(self):
        """NES ChkWeaponDialog, dialog byte $68 (the Kol wizard at NES 1,1): TextBlock11 entry 10 if Erdrick's Sword
        is equipped, otherwise entry 9."""
        _ = self._
        if self.player.weapon == "Erdrick's Sword":
            self.say(_("Finally thou hast obtained it, {}.").format(self.player.name))
        else:
            self.say(_("Though thou art as brave as thy ancestor, {}, thou cannot defeat the great Dragonlord with "
                       "such weapons.").format(self.player.name), _("Thou shouldst come here again."))

    def kol_hast_thou_found_the_flute(self):
        """NES CheckYesNoDialog, dialog byte $5E (the Kol wizard at NES 2,12): TextBlock9 entry 13 ($5E + $2F) and the
        yes/no window. Yes shows TextBlock10 entry 2 ($8D + $05) and no shows entry 7 ($8D + $0A)."""
        _ = self._
        self.confirm(_("Hast thou found the flute?"),
                     yes_path_function=partial(self.command_menu.show_line_in_dialog_box,
                                               _("Go to the town of Cantlin."), hide_arrow=True),
                     no_path_function=partial(self.command_menu.show_line_in_dialog_box,
                                              _("Howard had it, but he went to Rimuldar and never returned."),
                                              hide_arrow=True))

    def kol_hast_thou_been_to_the_southern_island(self):
        """NES CheckYesNoDialog, dialog byte $5F (the Kol shopkeeper at NES 7,19): TextBlock9 entry 14 ($5F + $2F) and
        the yes/no window. Yes shows TextBlock10 entry 3 ($8E + $05) and no shows entry 8 ($8E + $0A)."""
        _ = self._
        self.confirm(_("Hast thou been to the southern island?"),
                     yes_path_function=partial(self.command_menu.show_line_in_dialog_box,
                                               _("I have heard that powerful enemies live there."), hide_arrow=True),
                     no_path_function=partial(self.command_menu.show_line_in_dialog_box,
                                              _("To the south, I believe, there is a town called Rimuldar."),
                                              hide_arrow=True))

    def thou_hast_no_business_here(self):
        # NES HaveUniqueItem/HaveItemDialog: TextBlock11, entry 5
        self.say(self._("Thou hast no business here.\nGo away."))

    def tantegel_cellar_stones_of_sunlight_guardian(self):
        # NES WzdGuardDialog: the wizard guarding the Stones of Sunlight chest sends the player away once they have
        # the Stones or the Rainbow Drop. Taking the chest is up to the player; he doesn't give anything himself.
        if "Stones of Sunlight" in self.player.inventory or "Rainbow Drop" in self.player.inventory:
            self.thou_hast_no_business_here()
            return
        self.say(self._("I have been waiting long for one such as thee."), self._("Take the Treasure Chest."))

    def staff_of_rain_guardian(self):
        # NES RainStaffDialog: the old man stands in the only way to the Staff of Rain chest. Once he has the Silver
        # Harp he takes it and leaves, freeing the chest (he is back whenever the map is entered again).
        if "Rainbow Drop" in self.player.inventory or "Staff of Rain" in self.player.inventory:
            self.thou_hast_no_business_here()
            return
        if "Silver Harp" not in self.player.inventory:
            # NES HarpNotFound: TextBlock12, entry 1
            self.say(self._("Thy bravery must be proven."),
                     self._("Thus, I propose a test."),
                     self._("There is a Silver Harp that beckons to the creatures of the Dragonlord."),
                     self._("Bring this to me and I will reward thee with the Staff of Rain."))
            return
        # NES ChkSlvrHarp: TextBlock12 entry 2, TextBlock11 entry 4, TextBlock13 entry 6
        self.say(self._("Thou hast brought the harp. Good."),
                 self._("I have been waiting long for one such as thee."),
                 self._("Take the Treasure Chest."))
        self.player.inventory.remove("Silver Harp")
        self.remove_npc('WISE_MAN')

    def remove_npc(self, identifier: str):
        """NES: an NPC is removed from the screen by zeroing its position (until the map is loaded again). Its mobile
        slot is left empty, so the other roaming NPCs keep theirs (RoamingCharacter.slot)."""
        character_dict = self.current_map.characters.pop(identifier, None)
        if character_dict is None:
            return
        character = character_dict['character']
        if character in self.current_map.fixed_characters:
            self.current_map.fixed_characters.remove(character)
        if character in self.current_map.roaming_characters:
            self.current_map.roaming_characters.remove(character)

    def magic_temple_rainbow_drop_exchange(self):
        # NES RnbwDrpDialog: the old man at the shrine south of Rimuldar
        if "Rainbow Drop" in self.player.inventory:
            self.thou_hast_no_business_here()
            return
        if "Erdrick's Token" not in self.player.inventory:
            # Without Erdrick's Token the player isn't proven to be Erdrick's descendant: TextBlock12 entry 3, then
            # BWScreenFlash and CheckMapExit force the player out to the overworld (ChangeMaps -> SetPlyrPixelLoc ->
            # MapChngWithSound, which plays the stairs sound)
            self.say(self._("In thy task thou hast failed. Alas, I fear thou art not the one Erdrick predicted "
                            "would save us."),
                     self._("Go now!"))
            self.bw_screen_flash()
            # Move the player onto the temple's staircase (6, 2), then out to the overworld in front of the entrance
            self.player.row = 6
            self.player.column = 2
            alefgard_map = maps.map_lookup['Alefgard'](self.config)
            alefgard_map.destination_coordinates = (116, 116)
            self.command_menu.game.change_map(alefgard_map, stairs_sound=True)
            self.player.direction_value = Direction.DOWN.value
            return
        if "Stones of Sunlight" not in self.player.inventory or "Staff of Rain" not in self.player.inventory:
            # NES NoRnbwDrpDialog: TextBlock5 entry 9, then TextBlock11 entry 14
            self.say(self._("When the sun and rain meet, a Rainbow Bridge shall appear."),
                     self._("Thou may go and search."))
            return
        # NES HaveErdToken: TextBlock12 entry 4; the Stones and the Staff are taken, the Rainbow Drop is given and the
        # screen turns greyscale for 30 frames. Erdrick's Token is kept.
        self.say(self._("Now the sun and rain shall meet and the Rainbow Drop passes to thy keeping."))
        self.player.inventory.remove("Stones of Sunlight")
        self.player.inventory.remove("Staff of Rain")
        self.player.inventory.append("Rainbow Drop")  # NES AddInvItem: the first empty slot
        greyscale_screen(self.screen, self.config, frames=30)

    def bw_screen_flash(self):
        """NES BWScreenFlash (Bank03, LDB37): see src.visual_effects.bw_screen_flash."""
        bw_screen_flash(self.screen, self.config)

    def rimuldar_hast_thou_found_a_magic_temple(self):
        """NES CheckYesNoDialog, dialog byte $61 (the Rimuldar wizard at NES 3,23): after the first line of TextBlock10
        entry 0, the yes/no window. Yes shows TextBlock10 entry 5 ($61 + $2F + $05) and no shows entry 10
        ($61 + $2F + $0A)."""
        _ = self._
        self.confirm(_("Hast thou found a magic temple?"),
                     yes_path_function=partial(self.command_menu.show_line_in_dialog_box,
                                               _("In this temple do the sun and rain meet."), hide_arrow=True),
                     no_path_function=partial(self.command_menu.show_line_in_dialog_box,
                                              _("Go to the south."), hide_arrow=True))

    def rimuldar_fighters_ring_dialog(self):
        """NES ChkRingDialog, dialog byte $69 (the Rimuldar fighter at NES 16,26). Without a Fighter's Ring in the
        inventory the ring's worn flag is cleared first. Wearing it shows TextBlock11 entry 11, otherwise entry 12."""
        _ = self._
        if "Fighter's Ring" not in self.player.inventory and self.player.wearing_fighters_ring:
            self.player.wearing_fighters_ring = False
            self.player.update_attack_power()
        if self.player.wearing_fighters_ring:
            self.say(_("Is that a wedding ring?’\n`Thou seems too young to be married."))
        else:
            self.say(_("All true warriors wear a ring."))

    def prompt_for_save(self):
        return confirmation_prompt(self.command_menu,
                                   self._("Will thou tell me now of thy deeds so they won't be forgotten?"),
                                   yes_path_function=self.save_game,
                                   # NES SaveDialog: either way it goes on to "Dost thou wish to continue thy quest?",
                                   # which is the next entry in the king's dialog
                                   no_path_function=lambda: None,
                                   config=self.config,
                                   show_arrow=self.command_menu.game.show_arrow, color=self.color)

    def save_game(self):
        self.command_menu.save()
        self.command_menu.show_line_in_dialog_box(
            self._("Thy deeds have been recorded on the Imperial Scrolls of Honor."))

    def prompt_to_continue_quest(self):
        return confirmation_prompt(self.command_menu, self._("Dost thou wish to continue thy quest?"),
                                   yes_path_function=partial(self.command_menu.show_line_in_dialog_box,
                                                             self.goodbye_tempt_not_the_fates.format(
                                                                 self.player.name)),
                                   no_path_function=self.rest_then_for_awhile,
                                   config=self.config,
                                   show_arrow=self.command_menu.game.show_arrow, color=self.color)

    def rest_then_for_awhile(self):
        self.command_menu.show_line_in_dialog_box(self._("Rest then for awhile."))
        # NES ExitGame (Bank01): the music is silenced (MSC_NOSOUND) before the screen goes black for the reset message
        self.command_menu.game.music_player.stop_music()
        # NES LoadCreditsPals (Bank00, LAA62): PalFadeOut. Then EndGameClearPPU clears the screen and LoadStartPals
        # (LAA7E) does a PalFadeIn over the empty screen before the window opens.
        screen_fade(fade_out=True, screen=self.screen, config=self.config)
        self.screen.fill(BLACK)
        display.flip()
        screen_fade(fade_out=False, screen=self.screen, config=self.config)
        # NES ExitGame: EndGameClearPPU clears the whole screen, then Dowindow WND_DIALOG opens a new, empty dialog
        # window for the reset message, so it isn't a continuation of King Lorik's dialog
        self.command_menu.window_drop_down_effect(*DIALOG_WINDOW)
        # NES TextBlock19 entry 8: a WAIT for a button after the first sentence, then the second sentence and END with
        # no wait. ExitGame returns, MMCShutdown runs and Spinlock2 hangs: no button does anything after this.
        self.command_menu.show_line_in_dialog_box(
            self._("Please push RESET, hold it in, then turn off the POWER."), add_quotes=False)
        self.command_menu.show_line_in_dialog_box(
            self._("If you turn the power off first, the Imperial Scroll of Honor containing your deeds may be lost."),
            add_quotes=False, skip_text=True, hide_arrow=True)
        self.wait_for_reset()

    @staticmethod
    def wait_for_reset():
        """NES Spinlock2: the game hangs until the console is reset or switched off. Every button is ignored; closing
        the window is the only way out."""
        while True:
            for current_event in get():
                quit_if_requested(current_event)
            time.wait(POLL_INTERVAL_MS)

    def cantlin_still_wish_to_go_on(self):
        """NES CheckYesNoDialog, dialog byte $60 (the Cantlin guard at NES 5,6): after TextBlock9 entry 15, the
        yes/no window. Yes shows TextBlock10 entry 4 ($60 + $2F + $05) and no shows entry 9 ($60 + $2F + $0A)."""
        _ = self._
        self.confirm(_("Dost thou still wish to go on?"),
                     yes_path_function=partial(self.command_menu.show_line_in_dialog_box,
                                               _("Thou art truly brave."), hide_arrow=True),
                     no_path_function=partial(self.command_menu.show_line_in_dialog_box,
                                              _("That is good.’\n`No one will say thou art afraid."),
                                              hide_arrow=True))

    def tantegel_throne_room_roaming_guard(self):
        _ = self._
        if self.command_menu.game.story_flags.gwaelin_rescued:
            self.command_menu.show_line_in_dialog_box(_("Oh, brave {}.").format(self.player.name))
        else:
            player_please_save_the_princess = _("{}, please save the Princess.").format(self.player.name)
            confirmation_prompt(self.command_menu, _("Dost thou know about Princess Gwaelin?"),
                                yes_path_function=partial(self.command_menu.show_line_in_dialog_box,
                                                          player_please_save_the_princess, hide_arrow=True),
                                no_path_function=partial(self.command_menu.show_text_in_dialog_box,
                                                         (
                                                             _("Half a year now hath passed since the "
                                                               "Princess was kidnapped by the enemy."),
                                                             _("Never does the King speak of it, but he must "
                                                               "be suffering much."),
                                                             player_please_save_the_princess),
                                                         drop_down=False, drop_up=False,
                                                         skip_text=self.command_menu.skip_text), config=self.config,
                                show_arrow=self.command_menu.game.show_arrow, color=self.color)

    def get_inn_intro(self, inn_cost):
        _ = self._
        return _("Welcome to the traveler's Inn.\n"
                 "Room and board is {} GOLD per night.\n"
                 "Dost thou want a room?").format(inn_cost)

    def flash_and_restore_mp(self):
        """NES ChkMagicDialog (LD2D7): BWScreenFlash, then MP is set to the max (DisplayedMaxMP) and Dowindow
        WND_POPUP shows the restored MP."""
        self.bw_screen_flash()
        self.player.restore_mp()
        self.command_menu.show_popup_window()

    # Shops. Each NES shop routine (Bank03) is a chain of dialogs and yes/no windows; here every "loop back" in the
    # NES routine is a call to the method for that step.

    def confirm(self, prompt, yes_path_function, no_path_function):
        confirmation_prompt(self.command_menu, prompt, yes_path_function=yes_path_function,
                            no_path_function=no_path_function, config=self.config,
                            show_arrow=self.command_menu.game.show_arrow, color=self.color)

    def select_in_window(self, window: Window, number_of_entries: int, draw_window: Callable[[], object],
                         first_tile_row: int, initial_index: int = 0) -> int | None:
        """Show a selection window with a blinking cursor. Returns the chosen entry's index, or None if cancelled.
        :param window: Where the window goes and how big it is, in blocks.
        :param number_of_entries: How many entries the window lists.
        :param draw_window: Draws the window and its entries, without the cursor.
        :param first_tile_row: The tile row of the first entry and the cursor (the window data's cursor home Y).
        Entries are 2 tile rows (one block) apart, in single and double spaced windows alike.
        """
        tile_size = self.config['TILE_SIZE']
        x, y, width, height = window
        self.command_menu.window_drop_down_effect(x, y, width, height)
        window_rect = Rect(x * tile_size, y * tile_size, width * tile_size, height * tile_size)

        def draw(index: int, cursor_visible: bool) -> None:
            draw_window()
            # The cursor goes in tile column 1, between the left border and the entry (cursor home X = 1)
            self.command_menu.draw_window_cursor(x, y, 1, first_tile_row + 2 * index, cursor_visible)
            if not self.config['NO_BLIT']:
                display.update(window_rect)

        # The NES cursor (src/cursor.py), visible when the window opens (WndInitSelect), stops at the first and last
        # entries. A chooses, with the menu sound; B cancels, silently. Either way the arrow is drawn once more and
        # stays on (WndAPressed, WndBPressed), and the window is removed once it's answered or cancelled (NES
        # WindowSequence, Bank01).
        answer = run_selection(draw, initial_index, move=stop_at_edges(number_of_entries),
                               sound=lambda: self.sound.play_sound(self.directories.menu_button_sfx),
                               sound_buttons=(IN_A,))
        self.command_menu.remove_window(window)
        return answer.entry if answer.accepted else None

    def draw_window_background(self, window: Window) -> None:
        """A blank window with a border, stretched to its size (Graphics.create_window border)."""
        Graphics(self.config).create_window(*window, self.directories.ITEM_MENU_BACKGROUND_PATH, self.screen,
                                            self.color, border=ITEM_MENU_BORDER)

    def draw_in_window(self, window: Window, text: str, column: int, row: int, alignment: str = 'left') -> None:
        """Draw text in a window's tile (see CommandMenu.window_text_position)."""
        text_x, text_y = self.command_menu.window_text_position(window.x, window.y, column, row)
        draw_text(text, text_x, text_y, self.screen, self.config, self.color, alignment=alignment,
                  letter_by_letter=False)

    def select_from_text_menu(self, lines: list[str], window: Window, initial_index: int = 0) -> int | None:
        """A double spaced selection window of one column, like BuySellDat or YesNo1Dat: after the top border and a
        blank row, each line is at tile column 2 with a blank row after it (cursor home Y = 2)."""

        def draw_window() -> None:
            self.draw_window_background(window)
            for index, line in enumerate(lines):
                self.draw_in_window(window, line, 2, 2 + 2 * index)

        return self.select_in_window(window, len(lines), draw_window, 2, initial_index)

    def select_in_generated_window(self, layout: WindowLayout, initial_index: int = 0) -> int | None:
        """A selection window generated from its NES window data (src/window_renderer.py), with the blinking NES
        cursor at each entry's cursor tile (select_in_window). Returns the chosen entry's index, or None if cancelled."""
        first_row = layout.cursor_tiles[0][1]
        # select_in_window puts the cursor in tile column 1, one block (2 tile rows) per entry
        if layout.cursor_tiles != tuple((1, first_row + 2 * index) for index in range(len(layout.cursor_tiles))):
            raise ValueError(f"{layout.cursor_tiles} is not a single column of entries")
        return self.select_in_window(layout.window, len(layout.cursor_tiles),
                                     lambda: generated_window(self.screen, layout, self.color, self.config),
                                     first_row, initial_index)

    def is_nes_text(self, *texts: str) -> bool:
        """Whether the texts are shown untranslated, so in the NES font a generated window can draw (Korean is drawn
        as text on a window background instead)."""
        return all(self._(text) == text for text in texts)

    def select_shop_item(self, item_names: list[str], costs: list[int]) -> int | None:
        """The shop inventory window (NES ShopInvDat): single spaced and as high as the shop's stock
        (WndVariableHeight). Each item takes 2 tile rows: the first half of its name at tile column 2 and its cost,
        5 tiles wide, ending at column 16 (WndItemCost); the second half on the next row at column 3 (cursor home
        Y = 1). In English it is generated tile by tile (shop_inventory_layout); a translation is drawn as text."""
        if self.is_nes_text(*item_names):
            return self.select_in_generated_window(shop_inventory_layout(tuple(item_names), tuple(costs)))
        window = variable_height_window(SHOP_INVENTORY_WINDOW, len(item_names))

        def draw_window() -> None:
            self.draw_window_background(window)
            for index, (name, cost) in enumerate(zip(item_names, costs)):
                row = 1 + 2 * index
                translated_name = self._(name)
                first_half, second_half = name_halves(name) if translated_name == name else (translated_name, '')
                self.draw_in_window(window, first_half, 2, row)
                self.draw_in_window(window, str(cost), SHOP_COST_RIGHT_TILE_COLUMN, row, alignment='right')
                if second_half:
                    self.draw_in_window(window, second_half, 3, row + 1)

        return self.select_in_window(window, len(item_names), draw_window, 1)

    def select_from_inventory(self, items: list[str]) -> int | None:
        """The player inventory window (NES PlayerInvDat), as the ITEM command shows it."""
        window = Window(*item_menu_window('inventory', len(items)))
        return self.select_in_window(window, len(items),
                                     lambda: self.command_menu.draw_item_menu('inventory', items),
                                     ITEM_MENU_FIRST_TILE_ROW['inventory'])

    def open_store_inventory(self, current_store_inventory):
        """NES GetShopItems: show the shop's stock (ShopInvDat, select_shop_item) and return the name of the item
        chosen, or None if cancelled. The pop-up status window stays up with it."""
        self.command_menu.game.drawer.display_hovering_stats = True
        item_names = list(current_store_inventory)
        selected_index = self.select_shop_item(item_names,
                                               [current_store_inventory[name]['cost'] for name in item_names])
        return None if selected_index is None else item_names[selected_index]

    def please_come_again(self):
        self.say(self._("Please, come again."), hide_arrow=True)

    # Weapon and armor shops (NES WeaponsDialog). They only sell; the only way to sell equipment is the buyback
    # offered when buying a replacement.

    def check_buy_weapons_armor(self, current_store_inventory):
        self.confirm(self._("We deal in weapons and armor.\n Dost thou wish to buy anything today?"),
                     yes_path_function=partial(self.choose_weapon_or_armor, current_store_inventory),
                     no_path_function=self.please_come_again)

    def choose_weapon_or_armor(self, current_store_inventory):
        self.command_menu.show_line_in_dialog_box(self._("What dost thou wish to buy?"), skip_text=True)
        selected_item = self.open_store_inventory(current_store_inventory)
        if selected_item is None:
            self.please_come_again()
        else:
            self.buy_item_dialog(selected_item, current_store_inventory)

    def buy_item_dialog(self, selected_item, current_store_inventory):
        _ = self._
        self.say(_("The {}?").format(_(selected_item)))
        selected_item_dict = current_store_inventory[selected_item]
        # NES CheckBuyWeapon: only the price of the new item is compared with the player's gold
        if self.player.gold >= selected_item_dict['cost']:
            old_item = self.equipped_item(selected_item_dict['type'])
            old_item_cost = buyback_price(old_item, selected_item_dict['type'])
            if old_item:
                # NES GetBuybackPrice: offered whenever something of the same type is equipped
                self.say(_("Then I will buy thy {} for {} GOLD.").format(_(old_item), old_item_cost))
            self.confirm(_("Is that Okay.?"),
                         yes_path_function=partial(self.complete_transaction, selected_item,
                                                   current_store_inventory, old_item_cost),
                         no_path_function=partial(self.say, _("Oh, yes?\nThat's too bad.")))
        else:
            self.say(_("Sorry.\nThou hast not enough money."))
        self.confirm(_("Dost thou wish to buy anything more?"),
                     yes_path_function=partial(self.choose_weapon_or_armor, current_store_inventory),
                     no_path_function=self.please_come_again)

    def equipped_item(self, item_type):
        return {'weapon': self.player.weapon, 'armor': self.player.armor, 'shield': self.player.shield}[item_type]

    def complete_transaction(self, item, current_store_inventory, old_item_cost):
        # NES ComitWeapPurchase: pay for the new item, then receive the buyback price (gold capped at 65535)
        item_dict = current_store_inventory[item]
        item_type = item_dict['type']
        self.player.gold = pay_player(self.player.gold - item_dict['cost'], old_item_cost or 0)
        if item_type == 'weapon':
            self.player.weapon = item
        elif item_type == 'armor':
            self.player.armor = item
        elif item_type == 'shield':
            self.player.shield = item
        self.player.update_attack_power()
        self.player.update_defense_power()
        # NES CompWeapPurchase: "I thank thee.", then Dowindow WND_POPUP with the new gold
        self.say(self._("I thank thee."))
        self.command_menu.show_popup_window()

    # Item shops (NES ToolsDialog)

    def tool_shop(self, current_store_inventory):
        self.say(self.tools_intro)
        # NES WND_BUY_SELL (BuySellDat): generated in English, drawn as text when translated
        if self.is_nes_text("BUY", "SELL"):
            choice = self.select_in_generated_window(BUY_SELL_LAYOUT)
        else:
            choice = self.select_from_text_menu([self._("BUY"), self._("SELL")], BUY_SELL_WINDOW)
        if choice == 0:
            self.buy_tool(current_store_inventory)
        elif choice == 1:
            self.sell_tool(current_store_inventory)
        else:
            self.tool_shop_goodbye()

    def tool_shop_goodbye(self):
        self.say(self._("I will be waiting for thy next visit."), hide_arrow=True)

    def buy_tool(self, current_store_inventory):
        _ = self._
        self.say(_("What dost thou want?"))
        selected_item = self.open_store_inventory(current_store_inventory)
        if selected_item is None:
            self.tool_shop_goodbye()
            return
        cost = current_store_inventory[selected_item]['cost']
        if self.player.gold < cost:
            self.say(_("Thou hast not enough money."))
        elif selected_item == 'Herb' and self.player.inventory.count('Herb') >= MAX_HERBS:
            # NES ChkToolPurchase
            self.say(_("Thou cannot hold more Herbs."))
        elif selected_item != 'Herb' and inventory_is_full(self.player.inventory):
            # NES DoOthrToolPurchase: AddInvItem returns INV_FULL. Nothing stops buying a second Dragon's Scale.
            self.say(_("Thou cannot carry anymore."))
        else:
            self.player.gold -= cost
            self.player.inventory.append(selected_item)
            self.say(_("The {}?\nThank you very much.").format(_(selected_item)))
            self.command_menu.show_popup_window()  # NES PurchaseTool: the thanks, then Dowindow WND_POPUP
        # NES NextToolDialog
        self.confirm(_("Dost thou want anything else?"),
                     yes_path_function=partial(self.buy_tool, current_store_inventory),
                     no_path_function=self.tool_shop_goodbye)

    def sell_tool(self, current_store_inventory):
        """NES DoToolSell."""
        _ = self._
        items = inventory_list(self.player.inventory)
        if not items:
            self.say(_("Thou hast no possessions."))
            self.tool_shop_goodbye()
            return
        self.say(_("What art thou selling?"))
        # NES DoToolSell: WND_INVTRY1, the window the ITEM command uses
        selected_index = self.select_from_inventory(items)
        if selected_index is None:
            self.tool_shop_goodbye()
            return
        item = items[selected_index]
        price = sell_price(item)
        if not price:
            self.say(_("I cannot buy it."))
            self.sell_more(current_store_inventory)
            return
        self.confirm(_("Thou said the {}.\nI will buy thy {} for {} GOLD.\nIs that all right?").format(
            _(item), _(item), price),
            yes_path_function=partial(self.complete_sale, item, price, current_store_inventory),
            no_path_function=partial(self.sell_more, current_store_inventory))

    def complete_sale(self, item, price, current_store_inventory):
        if self.player.is_wearing_cursed_item(item):
            # NES ChkSellBelt / ChkSellNecklace / CantSellCrsdItm
            self.say(self._("A curse is upon thy body."))
            self.say(self._("I am sorry."))
        else:
            # NES DoSellTool only removes the item; a sold Dragon's Scale or Fighter's Ring stays "worn"
            self.player.inventory.remove(item)
            self.player.gold = pay_player(self.player.gold, price)
            self.command_menu.show_popup_window()  # NES DoneSellingTool: Dowindow WND_POPUP
        self.sell_more(current_store_inventory)

    def sell_more(self, current_store_inventory):
        # NES ItemSellLoop
        self.confirm(self._("Wilt thou sell anything else?"),
                     yes_path_function=partial(self.sell_tool, current_store_inventory),
                     no_path_function=self.tool_shop_goodbye)

    # Fairy Water shops (NES FairyDialog)

    def fairy_water_shop(self):
        self.confirm(self._("Will thou buy some Fairy Water for {} GOLD to keep the Dragonlord's minions away?").format(
            FAIRY_WATER_COST),
            yes_path_function=self.buy_fairy_water, no_path_function=self.fairy_water_goodbye)

    def fairy_water_goodbye(self):
        self.say(self._("All the best to thee."), hide_arrow=True)

    def buy_fairy_water(self):
        _ = self._
        if self.player.gold < FAIRY_WATER_COST:
            self.say(_("Thou hast not enough money."))
            self.fairy_water_goodbye()
        elif inventory_is_full(self.player.inventory):
            self.say(_("Thou cannot carry anymore."))
            self.fairy_water_goodbye()
        else:
            self.player.gold -= FAIRY_WATER_COST
            self.player.inventory.append('Fairy Water')
            self.command_menu.show_popup_window()  # NES BuyFairyWater: Dowindow WND_POPUP, then the thanks
            self.confirm(_("I thank thee.\nWon't thou buy one more bottle?"),
                         yes_path_function=self.buy_fairy_water, no_path_function=self.fairy_water_goodbye)

    # Magic Key shops (NES KeysDialog)

    def check_buy_magic_keys(self, magic_key_cost):
        self.confirm(self.magic_key_prompt.format(magic_key_cost),
                     yes_path_function=partial(self.buy_magic_key, magic_key_cost),
                     no_path_function=self.magic_key_goodbye)

    def magic_key_goodbye(self):
        self.say(self._("I will see thee later."), hide_arrow=True)

    def buy_magic_key(self, magic_key_cost):
        _ = self._
        if self.player.inventory.count('Magic Key') >= MAX_KEYS:
            self.say(_("I am sorry, but I cannot sell thee anymore."))
            self.magic_key_goodbye()
        elif self.player.gold < magic_key_cost:
            self.say(_("Thou hast not enough money."))
            self.magic_key_goodbye()
        else:
            self.player.gold -= magic_key_cost
            self.player.inventory.append('Magic Key')
            self.command_menu.show_popup_window()  # NES BuyKey: Dowindow WND_POPUP, then "Here,take this key."
            self.confirm(_("Here,take this key.\nDost thou wish to purchase more?"),
                         yes_path_function=partial(self.buy_magic_key, magic_key_cost),
                         no_path_function=self.magic_key_goodbye)

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
        """NES BuyInnStay (Bank03, LD8C9). The pop-up status window (opened with the COMMAND window, ShowNCCmdWindow)
        and the dialog window stay up through the whole stay; only the palettes fade:

        1. the gold is paid and Dowindow WND_POPUP shows what is left, then the innkeeper says "Good night."
        2. PalFadeOut fades everything, windows included, to black
        3. HP and MP are restored and Dowindow WND_POPUP redraws the pop-up with them, while the screen is black
        4. PalFadeIn brings it all back: the map, the COMMAND window, the pop-up with the full HP and MP, and the
           dialog window still showing "Good night.", all in the white of the restored HP (its palette loads run
           ChkLowHPPal)
        5. "Good morning." is printed below "Good night." in the same dialog window."""
        _ = self._
        game = self.command_menu.game
        config = game.game_state.config
        self.player.gold -= inn_cost
        self.command_menu.show_popup_window()
        self.command_menu.show_line_in_dialog_box(_("Good night."), skip_text=self.command_menu.skip_text)
        screen_fade(fade_out=True, screen=self.screen, config=self.config)  # PalFadeOut (LD8DC)
        # LD8DF-LD8FB, with the screen black: MSC_INN starts and HP and MP are restored,
        # WaitForMusicEnd lets the jingle finish, then MSC_VILLAGE starts, and only then PalFadeIn
        self.player.restore_hp()
        self.player.restore_mp()
        game.music_player.play_until_end(self.directories.inn_music, config)
        game.music_player.load_and_play_music(self.directories.village_music)
        game.load_window_palette()
        if not config['NO_BLIT']:
            background = game.drawer.background
            game.drawer.draw_all_tiles_in_current_map(self.current_map, background)
            draw_player_sprites(self.current_map, background, self.player.column, self.player.row, self.config)
            for character, character_dict in self.current_map.characters.items():
                if character != 'HERO':
                    draw_character_sprites(self.current_map, background, character_dict['coordinates'][1],
                                           character_dict['coordinates'][0], self.config, character)
            self.screen.blit(background, game.camera.pos)
            self.command_menu.redraw_command_window()
        self.command_menu.draw_dialog_window()
        self.command_menu.show_popup_window()
        screen_fade(fade_out=False, screen=self.screen, config=self.config)  # PalFadeIn (LD8FB)
        # NES (after PalFadeIn): TextBlock1 entry 6 if the hero is carrying Gwaelin, otherwise entry 8
        if game.story_flags.carrying_gwaelin:
            good_morning = _("Good morning.\nThou hast had a good night's sleep I hope.")
        else:
            good_morning = _("Good morning.\nThou seems to have spent a good night.")
        self.command_menu.show_text_in_dialog_box((good_morning, _("I shall see thee again.")),
                                                  skip_text=self.command_menu.skip_text, drop_down=False,
                                                  drop_up=False)
