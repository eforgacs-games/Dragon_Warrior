import logging

import pygame_menu

from data.text.dialog import show_line_in_dialog_box, show_text_in_dialog_box
from data.text.dialog_lookup_table import DialogLookup
from src.common import DRAGON_QUEST_FONT_PATH, BLACK, WHITE, menu_button_sfx
from src.config import SCALE, TILE_SIZE
from src.items import treasure
from src.menu_functions import get_opposite_direction
from src.sound import play_sound


class Menu:
    def __init__(self):
        self.menu = None
        self.dragon_warrior_menu_theme = pygame_menu.themes.Theme(background_color=BLACK,
                                                                  cursor_color=WHITE,
                                                                  cursor_selection_color=WHITE,
                                                                  focus_background_color=BLACK,
                                                                  title_background_color=BLACK,
                                                                  title_font=DRAGON_QUEST_FONT_PATH,
                                                                  title_font_size=8 * SCALE,
                                                                  title_offset=(32 * SCALE, 0),
                                                                  widget_font=DRAGON_QUEST_FONT_PATH,
                                                                  widget_alignment=pygame_menu.locals.ALIGN_LEFT,
                                                                  widget_background_color=BLACK,
                                                                  widget_font_color=WHITE,
                                                                  widget_font_size=8 * SCALE,
                                                                  widget_selection_effect=pygame_menu.widgets.
                                                                  LeftArrowSelection(
                                                                      # TODO: Disabling blinking arrow for now,
                                                                      #  because the arrow disappears between selections.
                                                                      #  Might be a problem with pygame-menu.
                                                                      #  Or a problem with the animation being shut off when the menu launches.
                                                                      #  Investigation needed.
                                                                      # blink_ms=500,
                                                                      # TODO: Fix LeftArrowSelection size.
                                                                      arrow_size=(SCALE * 5, SCALE * 6))
                                                                  )
        self.launch_signaled = False
        self.launched = False


class CommandMenu(Menu):

    def __init__(self, background, current_map, dialog_box, player, screen, camera_position):
        super().__init__()
        self.dialog_box = dialog_box
        self.current_tile = player.current_tile
        self.current_map = current_map
        self.characters = current_map.characters
        self.player = player
        self.map_name = current_map.__class__.__name__
        self.background = background
        self.screen = screen
        self.camera_position = camera_position
        # TODO: This gives a ValueError if the map is too small.
        try:
            command_menu_subsurface = background.subsurface((player.column - 2) * TILE_SIZE,
                                                            (player.row - 6) * TILE_SIZE,
                                                            8 * TILE_SIZE,
                                                            5 * TILE_SIZE)
            self.menu = pygame_menu.Menu('COMMAND',
                                         command_menu_subsurface.get_width() * 2,
                                         command_menu_subsurface.get_height() * 3,
                                         center_content=False,
                                         column_max_width=(TILE_SIZE * 4, TILE_SIZE * 3),
                                         columns=2,
                                         rows=4,
                                         theme=self.dragon_warrior_menu_theme,
                                         mouse_enabled=False,
                                         mouse_visible=False,
                                         menu_id='command'
                                         )
            # TODO: Allow for selection of options using the K ("A" button).
            #  Currently selection is only possible by use of the Enter button.
            self.menu.add.button('TALK', self.talk, margin=(9, 4))
            self.menu.add.button('STATUS', self.status, margin=(9, 4))
            self.menu.add.button('STAIRS', self.stairs, margin=(9, 4))
            self.menu.add.button('SEARCH', self.search, margin=(9, 4))
            self.menu.add.button('SPELL', self.spell, margin=(0, 4))
            self.menu.add.button('ITEM', self.item, margin=(0, 4))
            self.menu.add.button('DOOR', self.door, margin=(0, 4))
            self.menu.add.button('TAKE', self.take, margin=(0, 4))
            self.dialog_lookup = DialogLookup(self.player, self.map_name, self.screen)
        except ValueError as e:
            logging.error(e)
            self.command_menu_subsurface = None
            self.menu = None

    def talk(self):
        """
        Talk to an NPC.
        :return: None
        """
        play_sound(menu_button_sfx)
        # dialog = Dialog(player=self.player)

        # for now, implementing using print statements. will be useful for debugging as well.
        character_coordinates = [character_dict['coordinates'] for character_dict in self.characters.values()]
        # if self.player.next_tile_id not in self.characters.keys() and self.player.next_next_tile_id not in self.characters.keys():
        if not any(
                c in character_coordinates for c in [self.player.next_coordinates, self.player.next_next_coordinates]):
            show_text_in_dialog_box(("There is no one there.",), self.background, self.camera_position,
                                    self.current_map, self.screen)
            return
        for character_identifier, character_info in self.characters.items():
            if character_info['coordinates'] == self.player.next_coordinates or self.npc_is_across_counter(
                    character_info):
                if character_info['character'].direction_value != get_opposite_direction(self.player.direction_value):
                    character_info['character'].direction_value = get_opposite_direction(self.player.direction_value)
                    character_info['character'].animate()
                    character_info['character'].pause()
                self.launch_dialog(character_identifier, self.current_map, self.background, self.camera_position)
                break

    def npc_is_across_counter(self, character_info):
        return self.player.next_tile_id == 'WOOD' and character_info['coordinates'] == self.player.next_next_coordinates

    def launch_dialog(self, dialog_character, current_map, background, camera_position):
        self.dialog_box.launch_signaled = True
        character = self.dialog_lookup.lookup_table.get(dialog_character)
        if character:
            character.say_dialog(current_map, background, camera_position)
        else:
            print(f"Character not in lookup table: {dialog_character}")

    def status(self):
        """
        Display the current player's status. (Not yet implemented)
        :return: To be determined upon implementation
        """
        # open another window (11 tall x 10 wide)
        # print the following attributes:
        # example below:
        play_sound(menu_button_sfx)
        print(f"""
        NAME: {self.player.name}
        STRENGTH: {self.player.strength}
        MAXIMUM HP: {self.player.max_hp}
        MAXIMUM MP: {self.player.max_mp}
        ATTACK POWER: {self.player.attack_power}
        DEFENSE POWER: {self.player.defense_power}
        WEAPON: {self.player.weapon}
        ARMOR: {self.player.armor}
        SHIELD: {self.player.shield}
        """)

    def stairs(self):
        """
        Go up or down a staircase. (Not yet implemented)
        :return: To be determined upon implementation
        """
        play_sound(menu_button_sfx)
        # this might be something we could turn off as one of the "modernization" updates, but the implementation would be as follows:
        if self.player.current_tile in ('BRICK_STAIR_DOWN', 'BRICK_STAIR_UP', 'GRASS_STAIR_DOWN'):
            print("'There are stairs here.'")
            # TODO: activate the staircase warp to wherever the staircase leads
        else:
            show_text_in_dialog_box(("There are no stairs here.",), self.background, self.camera_position,
                                    self.current_map, self.screen)

    def search(self):
        """
        Search the ground for items. (Not yet implemented)
        :return: To be determined upon implementation
        """
        play_sound(menu_button_sfx)
        # open a window
        text_to_print = [f"{self.player.name} searched the ground all about.", ]
        # wait for input...
        if self.player.current_tile == 'TREASURE_BOX':
            text_to_print.append(f"There is a {self.player.current_tile.lower().replace('_', ' ')}.")
        # elif there is a hidden item:
        # print(f"There is a {hidden_item}")
        else:
            text_to_print.append("But there found nothing.")
        show_text_in_dialog_box(text_to_print, self.background, self.camera_position, self.current_map, self.screen,
                                add_quotes=False)

    def spell(self):
        """
        Cast a magic spell. (Not yet implemented)
        :return: To be determined upon implementation
        """
        play_sound(menu_button_sfx)
        # the implementation of this will vary upon which spell is being cast.
        if not self.player.spells:
            show_text_in_dialog_box((f"{self.player.name} cannot yet use the spell.",), self.background,
                                    self.camera_position, self.current_map, self.screen, add_quotes=False)
        else:
            show_line_in_dialog_box(self.player.spells, self.screen)

    def item(self):
        """
        View/use items. (Not yet implemented)
        :return: To be determined upon implementation
        """
        play_sound(menu_button_sfx)
        # the implementation of this will vary upon which item is being used.
        if not self.player.inventory:
            show_text_in_dialog_box(("Nothing of use has yet been given to thee.",), self.background,
                                    self.camera_position, self.current_map, self.screen, add_quotes=False)
        else:
            show_line_in_dialog_box(self.player.inventory, self.screen)

    def door(self):
        """
        Open a door. (Not yet implemented)
        :return: To be determined upon implementation
        """
        play_sound(menu_button_sfx)
        if self.player.next_tile_id == 'DOOR':
            if 'key' in self.player.inventory:
                # actually open the door
                print("Door opened!")
            else:
                show_text_in_dialog_box(("Thou hast not a key to use.",), self.background, self.camera_position,
                                        self.current_map, self.screen, add_quotes=False)
        else:
            show_text_in_dialog_box(("There is no door here.",), self.background, self.camera_position,
                                    self.current_map, self.screen, add_quotes=False)

    def take(self):
        """
        Take an item. (Not yet implemented)
        :return: To be determined upon implementation
        """
        play_sound(menu_button_sfx)
        # open a window
        if self.player.current_tile == 'TREASURE_BOX':
            map_treasure_info = treasure[self.map_name]
            current_treasure_info = map_treasure_info[(self.player.row, self.player.column)]
            item_name = current_treasure_info['item']
            if item_name == 'GOLD':
                # TODO(ELF): Add get item sound effect.
                # play_sound(get_item_sfx)
                gold_amount = current_treasure_info['amount']
                show_line_in_dialog_box(f"Of {item_name} thou hast gained {gold_amount}",
                                        self.screen)
                self.player.gold += gold_amount

                self.player.current_tile = 'BRICK'
                self.current_map.add_tile(self.current_map.floor_tile_key['BRICK'])

                # del map_treasure_info[(self.player.row, self.player.column)]
            else:
                print("Error obtaining treasure.")
        #     take it and update inventory accordingly
        # elif there is a hidden item
        # take the hidden item
        else:
            show_text_in_dialog_box((f"There is nothing to take here, {self.player.name}.",), self.background,
                                    self.camera_position,
                                    self.current_map, self.screen)


class DialogBox(Menu):
    def __init__(self, background, column, row):
        super().__init__()
        try:
            self.dialog_box_subsurface = background.subsurface((column - 2) * TILE_SIZE,
                                                               (row - 6) * TILE_SIZE,
                                                               12 * TILE_SIZE,
                                                               5 * TILE_SIZE)
            self.menu = pygame_menu.Menu('Dialog Box',
                                         self.dialog_box_subsurface.get_width(),
                                         self.dialog_box_subsurface.get_height(),
                                         center_content=False,
                                         theme=self.dragon_warrior_menu_theme,
                                         mouse_enabled=False,
                                         mouse_visible=False,
                                         menu_id='dialog_box'
                                         )
        except ValueError as e:
            logging.error(e)
            self.dialog_box_subsurface = None
            self.menu = None
