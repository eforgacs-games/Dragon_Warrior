import functools
from typing import Tuple, List

import pygame_menu
from pygame import Surface, display, KEYDOWN
from pygame.event import get
from pygame.sprite import Group
from pygame.time import get_ticks

from data.text.dialog import set_window_background, blink_down_arrow
from data.text.dialog_lookup_table import DialogLookup
from src.common import DRAGON_QUEST_FONT_PATH, BLACK, WHITE, menu_button_sfx, DIALOG_BOX_BACKGROUND_PATH, open_treasure_sfx, \
    get_tile_id_by_coordinates, COMMAND_MENU_STATIC_BACKGROUND_PATH
from src.config import SCALE, TILE_SIZE
from src.items import treasure
from src.maps_functions import get_center_point
from src.menu_functions import get_opposite_direction, convert_list_to_newline_separated_string, draw_player_sprites
from src.sound import play_sound
from src.text import draw_text


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
        self.skip_text = False


class CommandMenu(Menu):

    def __init__(self, game):
        super().__init__()
        self.game = game
        self.player = self.game.player
        self.background = self.game.background
        self.screen = self.game.screen
        self.camera_position = self.game.camera.get_pos()
        self.current_map = self.game.current_map
        self.current_tile = self.player.current_tile
        self.characters = self.current_map.characters
        self.map_name = self.current_map.__class__.__name__
        self.window_drop_down_effect(width=8, height=5, x=5, y=1)
        self.command_menu_surface = self.create_window(width=8, height=5, x=5, y=1, window_background=COMMAND_MENU_STATIC_BACKGROUND_PATH)
        self.dialog_lookup = DialogLookup(self)
        self.menu = pygame_menu.Menu(
            title='COMMAND',
            width=self.command_menu_surface.get_width() * 2,
            height=self.command_menu_surface.get_height() * 3,
            center_content=False,
            column_max_width=(TILE_SIZE * 4, TILE_SIZE * 3),
            columns=2,
            rows=4,
            theme=self.dragon_warrior_menu_theme,
            mouse_enabled=False,
            mouse_visible=False,
            menu_id='command',
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

    def npc_is_across_counter(self, character_dict):
        return self.player.next_tile_id == 'WOOD' and (
            character_dict['character'].row, character_dict['character'].column) == self.player.next_next_coordinates

    def launch_dialog(self, dialog_character, current_map):
        character = self.dialog_lookup.lookup_table[current_map.identifier].get(dialog_character)
        if character:
            if character.get('dialog'):
                self.dialog_lookup.camera_position = self.camera_position
                self.show_text_in_dialog_box(character['dialog'], add_quotes=True, skip_text=self.skip_text)
                if character.get('side_effects'):
                    for side_effect in character['side_effects']:
                        side_effect()
            else:
                print(f"Character has no dialog: {dialog_character}")
        else:
            print(f"Character not in lookup table: {dialog_character}")

    def show_line_in_dialog_box(self, line: str | functools.partial, add_quotes: bool = True, temp_text_start: int = None, skip_text: bool = False):
        """Shows a single line in a dialog box.
        :param line: The line of text to print.
        :param skip_text: Whether to automatically skip the text.
        :param add_quotes: Adds single quotes to be displayed on the screen.
        :param temp_text_start: The time at which temporary text started.
        """
        if line:
            if type(line) == str:
                current_time = None
                display_current_line = True
                if add_quotes:
                    line = f"`{line}’"
                while display_current_line:
                    if temp_text_start:
                        current_time = get_ticks()
                    self.create_window(width=12, height=5, x=2, y=9, window_background=DIALOG_BOX_BACKGROUND_PATH)
                    # if print_by_character:
                    #     for i in range(len(line)):
                    #         for j in range(16):
                    #             white_line = line[:i]
                    #             black_line = line[i:]
                    #             draw_text(white_line, 15, WHITE, self.screen.get_width() / 2, (self.screen.get_height() * 5 / 8),
                    #                       DRAGON_QUEST_FONT_PATH,
                    #                       self.screen)
                    #             draw_text(black_line, 15, BLACK, self.screen.get_width() / 2, (self.screen.get_height() * 5 / 8),
                    #                       DRAGON_QUEST_FONT_PATH,
                    #                       self.screen)
                    # else:
                    draw_text(line, WHITE, TILE_SIZE * 3, TILE_SIZE * 9.75, self.screen, 15, DRAGON_QUEST_FONT_PATH, center_align=False)
                    display.flip()
                    blink_down_arrow(self.screen)
                    # playing with fire a bit here with the short-circuiting
                    if skip_text or (temp_text_start and current_time - temp_text_start >= 200) or any(
                            [current_event.type == KEYDOWN for current_event in get()]):
                        if not skip_text:
                            play_sound(menu_button_sfx)
                        display_current_line = False
            else:
                # if the line is a method
                line()

    def create_window(self, width, height, x, y, window_background):
        window_box = Surface((TILE_SIZE * width, TILE_SIZE * height))  # lgtm [py/call/wrong-arguments]
        set_window_background(window_box, window_background)
        self.screen.blit(window_box, (TILE_SIZE * x, TILE_SIZE * y))
        return window_box

    def show_text_in_dialog_box(self, text: Tuple[str] | List[str] | str, add_quotes=False, temp_text_start=None, skip_text=False, drop_down=True,
                                drop_up=True):
        """Shows a passage of text in a dialog box.

        :param text: The text to print.
        :param skip_text: Whether to automatically skip the text.
        :param add_quotes: Adds single quotes to be displayed on the screen.
        :param temp_text_start: The time at which temporary text started.
        :param drop_down: Whether to display the drop-down effect.
        :param drop_up: Whether to display the drop-up effect.
        """
        if drop_down:
            self.window_drop_down_effect(width=12, height=5, x=2, y=9)
        if type(text) == str:
            self.show_line_in_dialog_box(text, add_quotes, temp_text_start, skip_text)
        else:
            for line in text:
                self.show_line_in_dialog_box(line, add_quotes, temp_text_start, skip_text)
                # TODO(ELF): This commented out code just makes the sound for printing by letter.
                #  Need to actually show the letters one by one.
                #  (Better to leave it commented out until it's working)
                # for letter_index, letter in enumerate(line):
                #     time.sleep(0.01)
                #     if letter_index % 2 == 0:
                #         play_sound(text_beep_sfx)
        if drop_up:
            self.window_drop_up_effect(width=12, height=5, x=2, y=9)

    def window_drop_down_effect(self, width, height, x, y):
        """Intro effect for windows."""
        for i in range(height + 1):
            black_box = Surface((TILE_SIZE * width, TILE_SIZE * i))  # lgtm [py/call/wrong-arguments]
            black_box.fill(BLACK)
            for j in range(64):
                self.screen.blit(black_box, (TILE_SIZE * x, TILE_SIZE * y))
                display.update()

    def window_drop_up_effect(self, width, height, x, y):
        """Outro effect for windows."""
        # TODO(ELF): Needs work - doesn't always drop up smoothly. One observation is that it appears to work better closer
        #  to the origin (0, 0) of the map.
        # draw all the tiles initially once
        for tile, tile_dict in self.current_map.floor_tile_key.items():
            if tile in self.current_map.tile_types_in_current_map:
                tile_dict['group'].draw(self.background)
        for i in range(height - 1, -1, -1):
            black_box = Surface((TILE_SIZE * width, TILE_SIZE * i))  # lgtm [py/call/wrong-arguments]
            black_box.fill(BLACK)
            for j in range(64):
                for tile, tile_dict in self.current_map.floor_tile_key.items():
                    if tile in self.get_dialog_box_underlying_tiles(self.current_map, i):
                        tile_dict['group'].draw(self.background)
                draw_player_sprites(self.current_map, self.background, self.player.column, self.player.row)
                for character, character_dict in self.current_map.characters.items():
                    self.background.blit(character_dict['character_sprites'].sprites()[0].image,
                                         (character_dict['character'].column * TILE_SIZE, character_dict['character'].row * TILE_SIZE))
                self.screen.blit(self.background, self.camera_position)
                self.screen.blit(black_box, (TILE_SIZE * x, TILE_SIZE * y))
                display.update()

    # Menu functions

    def talk(self):
        """
        Talk to an NPC.
        :return: None
        """
        play_sound(menu_button_sfx)
        # dialog = Dialog(player=self.player)

        # for now, implementing using print statements. will be useful for debugging as well.
        character_coordinates = [(character_dict['character'].row, character_dict['character'].column) for character_dict in self.characters.values()]
        # if self.player.next_tile_id not in self.characters.keys() and self.player.next_next_tile_id not in self.characters.keys():

        if any(c in character_coordinates for c in [self.player.next_coordinates]) or \
                any(c in character_coordinates for c in [self.player.next_next_coordinates]) and self.player.next_tile_id == 'WOOD':
            for character_identifier, character_dict in self.characters.items():
                if (character_dict['character'].row, character_dict['character'].column) == self.player.next_coordinates or self.npc_is_across_counter(
                        character_dict):
                    if character_dict['character'].direction_value != get_opposite_direction(self.player.direction_value):
                        character_dict['character'].direction_value = get_opposite_direction(self.player.direction_value)
                        character_dict['character'].animate()
                        character_dict['character'].pause()
                    self.launch_dialog(character_identifier, self.current_map)
                    break
        else:
            self.show_text_in_dialog_box(("There is no one there.",), add_quotes=True, skip_text=self.skip_text)
        self.game.unlaunch_menu(self)
        self.game.unpause_all_movement()
        # TODO(ELF): Add drop up effect upon closing command menu - currently blits to the wrong place,
        #  and also clears the command menu before blitting.
        # self.window_drop_up_effect(width=8, height=5, x=5, y=1)

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
        self.game.unlaunch_menu(self)
        self.game.unpause_all_movement()

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
            # the original game has quotes in this dialog box
            self.show_text_in_dialog_box(("There are no stairs here.",), add_quotes=True, skip_text=self.skip_text)
        self.game.unlaunch_menu(self)
        self.game.unpause_all_movement()

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
        self.show_text_in_dialog_box(text_to_print, skip_text=self.skip_text)
        self.game.unlaunch_menu(self)
        self.game.unpause_all_movement()

    def spell(self):
        """
        Cast a magic spell. (Not yet implemented)
        :return: To be determined upon implementation
        """
        play_sound(menu_button_sfx)
        # the implementation of this will vary upon which spell is being cast.
        if not self.player.spells:
            self.show_text_in_dialog_box((f"{self.player.name} cannot yet use the spell.",), skip_text=self.skip_text)
        else:
            self.show_text_in_dialog_box(convert_list_to_newline_separated_string(self.player.spells), skip_text=self.skip_text)
        self.game.unlaunch_menu(self)
        self.game.unpause_all_movement()

    def item(self):
        """
        View/use items. (Not yet implemented)
        :return: To be determined upon implementation
        """
        play_sound(menu_button_sfx)
        # the implementation of this will vary upon which item is being used.
        if not self.player.inventory:
            self.show_text_in_dialog_box(("Nothing of use has yet been given to thee.",), skip_text=self.skip_text)
        else:
            self.show_text_in_dialog_box(convert_list_to_newline_separated_string(self.player.inventory), skip_text=self.skip_text)
        self.game.unlaunch_menu(self)
        self.game.unpause_all_movement()

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
                self.show_text_in_dialog_box(("Thou hast not a key to use.",), skip_text=self.skip_text)
        else:
            self.show_text_in_dialog_box(("There is no door here.",), skip_text=self.skip_text)
        self.game.unlaunch_menu(self)
        self.game.unpause_all_movement()

    def take(self):
        """
        Take an item. (Not yet implemented)
        :return: To be determined upon implementation
        """
        play_sound(menu_button_sfx)
        # open a window
        if self.player.current_tile == 'TREASURE_BOX':
            treasure_info = treasure[self.map_name][(self.player.row, self.player.column)]
            item_name = treasure_info['item']
            if item_name:
                if item_name == 'GOLD':
                    play_sound(open_treasure_sfx)
                    gold_amount = treasure_info['amount']

                    self.set_tile_by_coordinates('BRICK', self.player.column, self.player.row, self.player)
                    self.show_text_in_dialog_box(f"Of GOLD thou hast gained {gold_amount}", skip_text=self.skip_text)

                    self.player.gold += gold_amount
                else:
                    play_sound(open_treasure_sfx)

                    self.set_tile_by_coordinates('BRICK', self.player.column, self.player.row, self.player)
                    self.show_text_in_dialog_box(f"Fortune smiles upon thee, {self.player.name}.\n"
                                                 f"Thou hast found the {item_name}.", skip_text=self.skip_text)
                    # could probably assign the new treasure box values by using this line:
                    self.player.inventory.append(item_name)

                    # self.player.current_tile = 'BRICK'
            else:
                self.show_text_in_dialog_box("Unfortunately, it is empty.", skip_text=self.skip_text)
        #     take it and update inventory accordingly
        # elif there is a hidden item
        # take the hidden item
        else:
            self.show_text_in_dialog_box((f"There is nothing to take here, {self.player.name}.",), skip_text=self.skip_text)
        self.game.unlaunch_menu(self)
        self.game.unpause_all_movement()

    def set_tile_by_coordinates(self, new_tile_identifier, column, row, player):
        # TODO(ELF): This works, but resets whenever the map is reloaded.
        self.current_tile = 'BRICK'
        old_tile_identifier = get_tile_id_by_coordinates(column, row, self.current_map)
        if column == player.column and row == player.row:
            player.current_tile = new_tile_identifier
        self.current_map.layout[row][column] = self.game.layouts.map_layout_lookup[self.current_map.__class__.__name__][row][column] = \
            self.current_map.floor_tile_key[new_tile_identifier]['val']
        center_pt = get_center_point(column, row)

        self.current_map.floor_tile_key[old_tile_identifier]['group'] = Group()
        self.current_map.add_tile(self.current_map.floor_tile_key[new_tile_identifier], center_pt)
        for row in range(len(self.current_map.layout)):
            for column in range(len(self.current_map.layout[row])):
                self.current_map.center_pt = get_center_point(column, row)
                if self.current_map.layout[row][column] <= max(self.current_map.floor_tile_key[old_tile_identifier]['val'],
                                                               self.current_map.floor_tile_key[new_tile_identifier]['val']):
                    self.current_map.map_floor_tiles(column, row)

    def get_dialog_box_underlying_tiles(self, current_map, current_box_height):
        # TODO(ELF): Can be improved further by narrowing the columns to just where the box is, not only the rows.
        box_start_row = 2
        box_end_row = current_box_height + box_start_row
        row_tile_sets = [set(row) for row in
                         current_map.layout[self.player.row + box_start_row:self.player.row + box_end_row]]
        return set([item for sublist in row_tile_sets for item in sublist])
