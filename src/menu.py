import functools
import random
from collections import Counter
from typing import Tuple, List

import pygame_menu
from pygame import Surface, display, KEYDOWN, Rect, event, K_ESCAPE, K_RETURN, K_k, K_j, K_UP, K_DOWN, K_w, K_s
from pygame.sprite import Group
from pygame.time import get_ticks

from data.text.dialog import blink_arrow
from data.text.dialog_lookup_table import DialogLookup
from src.common import DRAGON_QUEST_FONT_PATH, BLACK, menu_button_sfx, DIALOG_BOX_BACKGROUND_PATH, open_treasure_sfx, \
    get_tile_id_by_coordinates, COMMAND_MENU_STATIC_BACKGROUND_PATH, create_window, convert_to_frames_since_start_time, \
    open_door_sfx, \
    STATUS_WINDOW_BACKGROUND_PATH, item_menu_background_lookup, torch_sfx, spell_sfx
from src.config import SCALE, TILE_SIZE, LANGUAGE
from src.game_functions import draw_hovering_stats_window
from src.items import treasure
from src.maps_functions import get_center_point
from src.menu_functions import get_opposite_direction
from src.sound import play_sound
from src.text import draw_text


class Menu:
    def __init__(self):
        self.menu = None
        self.launch_signaled = False
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

        self.command_menu_surface = create_window(x=5, y=1, width=8, height=5,
                                                  window_background=COMMAND_MENU_STATIC_BACKGROUND_PATH,
                                                  screen=self.screen,
                                                  color=self.game.color)
        self.dialog_lookup = DialogLookup(self)
        self.menu = pygame_menu.Menu(
            title='COMMAND',
            width=self.command_menu_surface.get_width() * 2,
            height=self.command_menu_surface.get_height() * 3,
            center_content=False,
            column_max_width=(TILE_SIZE * 4, TILE_SIZE * 3),
            columns=2,
            rows=4,
            theme=pygame_menu.themes.Theme(background_color=BLACK,
                                           cursor_color=self.game.color,
                                           cursor_selection_color=self.game.color,
                                           title_background_color=BLACK,
                                           title_font=DRAGON_QUEST_FONT_PATH,
                                           title_font_color=self.game.color,
                                           title_font_size=8 * SCALE,
                                           title_offset=(32 * SCALE, 0),
                                           widget_font=DRAGON_QUEST_FONT_PATH,
                                           widget_alignment=pygame_menu.locals.ALIGN_LEFT,
                                           widget_background_color=BLACK,
                                           widget_font_color=self.game.color,
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
                                           )
                                           ),
            mouse_enabled=False,
            mouse_visible=False,
            menu_id='command',
            verbose=False
        )
        # TODO: Allow for selection of options using the K ("A" button).
        #  Currently selection is only possible by use of the Enter button.
        self.menu.add.button('TALK', self.talk, padding=(9, 5, 8, 16))
        self.menu.add.button('STATUS', self.status, padding=(4, 5, 8, 16))
        self.menu.add.button('STAIRS', self.stairs, padding=(4, 5, 8, 16))
        self.menu.add.button('SEARCH', self.search, padding=(4, 5, 8, 16))
        self.menu.add.button('SPELL', self.spell, padding=(9, 0, 8, 16))
        self.menu.add.button('ITEM', self.item, padding=(4, 0, 8, 16))
        self.menu.add.button('DOOR', self.door, padding=(4, 0, 8, 16))
        self.menu.add.button('TAKE', self.take, padding=(4, 0, 8, 16))
        self.menu.disable()

    def npc_is_across_counter(self, character_dict):
        return self.player.next_tile_id == 'WOOD' and (
            character_dict['character'].row, character_dict['character'].column) == self.player.next_next_coordinates

    def launch_dialog(self, dialog_character, current_map):
        character = self.dialog_lookup.lookup_table[current_map.identifier].get(dialog_character)
        if character:
            if character.get('dialog'):
                self.dialog_lookup.camera_position = self.camera_position
                self.show_text_in_dialog_box(character['dialog'], add_quotes=True, skip_text=self.skip_text)
        #     else:
        #         print(f"Character has no dialog: {dialog_character}")
        # else:
        #     print(f"Character not in lookup table: {dialog_character}")

    def show_line_in_dialog_box(self, line: str | functools.partial, add_quotes: bool = True,
                                temp_text_start: int = None, skip_text: bool = False, last_line=False,
                                disable_sound=False, letter_by_letter=True):
        """Shows a single line in a dialog box.
        :param last_line:
        :param line: The line of text to print.
        :param skip_text: Whether to automatically skip the text.
        :param add_quotes: Adds single quotes to be displayed on the screen.
        :param temp_text_start: The time at which temporary text started.
        :param disable_sound: Whether to disable the sound.
        :param letter_by_letter: Whether to print the text letter by letter.
        """
        if line:
            if type(line) == str:
                current_time = None
                display_current_line = True
                if add_quotes:
                    if LANGUAGE == 'English':
                        line = f"`{line}’"
                    elif LANGUAGE == 'Korean':
                        if line.isascii():
                            line = f"`{line}’"
                        else:
                            line = f"'{line}'"
                current_line = ""
                while display_current_line:
                    if temp_text_start:
                        current_time = get_ticks()
                    create_window(x=2, y=9, width=12, height=5, window_background=DIALOG_BOX_BACKGROUND_PATH,
                                  screen=self.screen, color=self.game.color)
                    if letter_by_letter:
                        if not current_line:
                            current_line = draw_text(line, TILE_SIZE * 3, TILE_SIZE * 9.75, self.screen, color=self.game.color,
                                                     letter_by_letter=True, disable_sound=disable_sound)
                        else:
                            current_line = draw_text(line, TILE_SIZE * 3, TILE_SIZE * 9.75, self.screen, color=self.game.color,
                                                     letter_by_letter=False, disable_sound=disable_sound)
                    else:
                        current_line = draw_text(line, TILE_SIZE * 3, TILE_SIZE * 9.75, self.screen, color=self.game.color,
                                                 letter_by_letter=False, disable_sound=disable_sound)
                    display.update(Rect(2 * TILE_SIZE, 9 * TILE_SIZE, 12 * TILE_SIZE, 5 * TILE_SIZE))
                    if not last_line:
                        end_of_dialog_box_location = self.screen.get_width() / 2, (self.screen.get_height() * 13 / 16) + TILE_SIZE // 1.5
                        blink_arrow(end_of_dialog_box_location[0], end_of_dialog_box_location[1], "down", self.screen, self.game.color)
                    # playing with fire a bit here with the short-circuiting
                    if skip_text or (temp_text_start and current_time - temp_text_start >= 1000) or any(
                            [current_event.type == KEYDOWN for current_event in event.get()]):
                        if not skip_text and not disable_sound:
                            play_sound(menu_button_sfx)
                        display_current_line = False
            else:
                # if the line is a method
                line()

    def show_text_in_dialog_box(self, text: Tuple | List | str, add_quotes=False, temp_text_start=None, skip_text=False,
                                drop_down=True, drop_up=True, disable_sound=False, letter_by_letter=True):
        """Shows a passage of text in a dialog box.

        :param disable_sound:
        :param text: The text to print.
        :param skip_text: Whether to automatically skip the text.
        :param add_quotes: Adds single quotes to be displayed on the screen.
        :param temp_text_start: The time at which temporary text started.
        :param drop_down: Whether to display the drop-down effect.
        :param drop_up: Whether to display the drop-up effect.
        :param letter_by_letter: Whether to print the text letter by letter.
        """
        if drop_down:
            self.window_drop_down_effect(2, 9, 12, 5)
        if type(text) == str:
            self.show_line_in_dialog_box(text, add_quotes, temp_text_start, skip_text, last_line=True,
                                         disable_sound=disable_sound, letter_by_letter=letter_by_letter)
        else:
            for line_index, line in enumerate(text):
                if line_index == len(text) - 1:
                    self.show_line_in_dialog_box(line, add_quotes, temp_text_start, skip_text, last_line=True,
                                                 disable_sound=disable_sound, letter_by_letter=letter_by_letter)
                else:
                    self.show_line_in_dialog_box(line, add_quotes, temp_text_start, skip_text,
                                                 disable_sound=disable_sound, letter_by_letter=letter_by_letter)
        if drop_up:
            self.window_drop_up_effect(2, 9, 12, 5)

    def window_drop_down_effect(self, left, top, width, height) -> None:
        """Intro effect for menus."""
        window_rect = Rect(left * TILE_SIZE, top * TILE_SIZE, width * TILE_SIZE, height * TILE_SIZE)
        for i in range(height + 1):
            black_box = Surface((TILE_SIZE * width, TILE_SIZE * i))  # lgtm [py/call/wrong-arguments]
            black_box.fill(BLACK)
            drop_down_start = get_ticks()
            # each "bar" lasts 1 frame
            while convert_to_frames_since_start_time(drop_down_start) < 1:
                self.screen.blit(black_box, (TILE_SIZE * left, TILE_SIZE * top))
                display.update(window_rect)

    def window_drop_up_effect(self, left, top, width, height) -> None:
        """Outro effect for menus."""
        # draw all the tiles initially once

        camera_screen_rect = Rect(self.player.rect.x - TILE_SIZE * 8, self.player.rect.y - TILE_SIZE * 7,
                                  self.screen.get_width(), self.screen.get_height())
        if not self.current_map.is_dark:
            # if the map is dark, drawing all the tiles to the screen basically creates an exploit that shows the map tiles lit up,
            # even without a torch or radiant
            # might be good to revisit this later with just a black background?
            group_to_draw = Group()
            for tile, tile_dict in self.current_map.floor_tile_key.items():
                if tile in self.current_map.tile_types_in_current_map and tile_dict.get('group'):
                    for tile_sprite in tile_dict['group']:
                        if camera_screen_rect.colliderect(tile_sprite.rect):
                            group_to_draw.add(tile_sprite)
            group_to_draw.draw(self.background)

            for i in range(height - 1, -1, -1):
                black_box = Surface((TILE_SIZE * width, TILE_SIZE * i))  # lgtm [py/call/wrong-arguments]
                black_box.fill(BLACK)
                drop_up_start = get_ticks()
                while convert_to_frames_since_start_time(drop_up_start) < 1:
                    # draw_player_sprites(self.current_map, self.background, self.player.rect.x, self.player.rect.y)
                    for character, character_dict in self.current_map.characters.items():
                        if camera_screen_rect.colliderect(character_dict['character'].rect):
                            self.background.blit(character_dict['character_sprites'].sprites()[0].image,
                                                 (character_dict['character'].rect.x, character_dict['character'].rect.y))
                    self.screen.blit(self.background, self.camera_position)
                    if self.launch_signaled:
                        self.screen.blit(self.command_menu_surface, (TILE_SIZE * 6, TILE_SIZE * 1))
                    if self.game.display_hovering_stats:
                        draw_hovering_stats_window(self.screen, self.player, self.game.color)
                    display.update(self.screen.blit(black_box, (TILE_SIZE * left, TILE_SIZE * top)))

    def take_item(self, item_name: str):
        play_sound(open_treasure_sfx)
        self.set_tile_by_coordinates('BRICK', self.player.column, self.player.row, self.player)
        found_item_text = f"Fortune smiles upon thee, {self.player.name}.\nThou hast found the {item_name}."

        if item_name == "Tablet":
            self.tablet(found_item_text)
        # could probably assign the new treasure box values by using this line:
        else:
            self.show_text_in_dialog_box(found_item_text, skip_text=self.skip_text)
            self.player.inventory.insert(0, item_name)

    def tablet(self, found_item_text):
        self.show_text_in_dialog_box((
            found_item_text,
            "The tablet reads as follows:",
            "I am Erdrick and thou art my descendant.",
            "Three items were needed to reach the Isle of Dragons, which is south of Brecconary.",
            "I gathered these items, reached the island, and there defeated a creature of great evil.",
            "Now I have entrusted the three items to three worthy keepers.",
            "Their descendants will protect the items until thy quest leads thee to seek them out.",
            "When a new evil arises, find the three items, then fight!"), drop_down=False)

    def take_gold(self, treasure_info: dict):
        play_sound(open_treasure_sfx)
        gold_amount = treasure_info['amount']
        self.set_tile_by_coordinates('BRICK', self.player.column, self.player.row, self.player)
        self.show_text_in_dialog_box(f"Of GOLD thou hast gained {gold_amount}", skip_text=self.skip_text)
        self.player.gold += gold_amount

    def set_tile_by_coordinates(self, new_tile_identifier, column, row, player):
        old_tile_identifier = get_tile_id_by_coordinates(column, row, self.current_map)
        if column == player.column and row == player.row:
            self.current_tile = new_tile_identifier
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

    # Items

    def herb(self):
        self.show_text_in_dialog_box(f"{self.player.name} used the Herb.", skip_text=self.skip_text)
        self.recover_health()

    def wings(self):
        self.show_text_in_dialog_box((f"{self.player.name}  threw The Wings of the Wyvern up into the sky.",))

    def torch(self):
        if not self.current_map.is_dark:
            self.show_text_in_dialog_box(("A torch can be used only in dark places.",), skip_text=self.skip_text)
        else:
            if self.game.radiant_active:
                self.game.radiant_active = False
            self.game.torch_active = True
            play_sound(torch_sfx)
            self.player.inventory.remove("Torch")

    def dragon_scale(self):
        self.show_text_in_dialog_box(f"{self.player.name} used the Dragon Scale.", skip_text=self.skip_text)

    def fairy_water(self):
        self.show_text_in_dialog_box(f"{self.player.name} used the Fairy Water.", skip_text=self.skip_text)

    # spells

    def heal(self):
        self.recover_health()

    def recover_health(self):
        health_addition = random.randrange(10, 17)
        if self.player.current_hp + health_addition > self.player.max_hp:
            health_addition = self.player.max_hp - self.player.current_hp
        self.player.current_hp += health_addition

    def hurt(self):
        self.show_text_in_dialog_box(("But nothing happened.",), skip_text=self.skip_text)

    def sleep(self):
        pass

    def radiant(self):
        if self.current_map.is_dark:
            if self.game.torch_active:
                self.game.torch_active = False
            self.game.radiant_active = True
        else:
            self.show_text_in_dialog_box(("But nothing happened.",), skip_text=self.skip_text)

    def stopspell(self):
        pass

    def outside(self):
        pass

    def return_(self):
        pass

    def repel(self):
        pass

    def healmore(self):
        pass

    def hurtmore(self):
        pass

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
            self.show_text_in_dialog_box("There is no one there.", add_quotes=True, skip_text=self.skip_text)

        self.game.unlaunch_menu(self)
        self.game.unpause_all_movement()

    def status(self) -> None:
        """
        Display the current player's status.
        :return: None
        """
        # open another window (11 tall x 10 wide)
        # print the following attributes:
        # example below:
        play_sound(menu_button_sfx)
        show_status = True
        self.window_drop_down_effect(4, 3, 10, 11)
        create_window(4, 3, 10, 11, STATUS_WINDOW_BACKGROUND_PATH, self.screen, color=self.game.color)
        draw_text(self.player.name, TILE_SIZE * 13, TILE_SIZE * 3.75, self.screen, color=self.game.color, alignment='right', letter_by_letter=False)
        draw_text(str(self.player.strength), TILE_SIZE * 13, TILE_SIZE * 4.75, self.screen, color=self.game.color, alignment='right', letter_by_letter=False)
        draw_text(str(self.player.agility), TILE_SIZE * 13, TILE_SIZE * 5.75, self.screen, color=self.game.color, alignment='right', letter_by_letter=False)
        draw_text(str(self.player.max_hp), TILE_SIZE * 13, TILE_SIZE * 6.75, self.screen, color=self.game.color, alignment='right', letter_by_letter=False)
        draw_text(str(self.player.max_mp), TILE_SIZE * 13, TILE_SIZE * 7.75, self.screen, color=self.game.color, alignment='right', letter_by_letter=False)
        draw_text(str(self.player.attack_power), TILE_SIZE * 13, TILE_SIZE * 8.75, self.screen, color=self.game.color, alignment='right', letter_by_letter=False)
        draw_text(str(self.player.defense_power), TILE_SIZE * 13, TILE_SIZE * 9.75, self.screen, color=self.game.color, alignment='right', letter_by_letter=False)
        draw_text(self.player.weapon, TILE_SIZE * 11.75, TILE_SIZE * 10.75, self.screen, color=self.game.color, text_wrap_length=9, alignment='right', letter_by_letter=False)
        draw_text(self.player.armor, TILE_SIZE * 11.55, TILE_SIZE * 11.75, self.screen, color=self.game.color, text_wrap_length=9, alignment='right', letter_by_letter=False)
        draw_text(self.player.shield, TILE_SIZE * 11.75, TILE_SIZE * 12.75, self.screen, color=self.game.color, text_wrap_length=9, alignment='right', letter_by_letter=False)
        display.update((4 * TILE_SIZE, 3 * TILE_SIZE, 10 * TILE_SIZE, 11 * TILE_SIZE))
        while show_status:
            for current_event in event.get():
                if current_event.type == KEYDOWN:
                    if current_event.key in (K_ESCAPE, K_RETURN, K_k, K_j):
                        show_status = False
        self.window_drop_up_effect(4, 3, 10, 11)
        # print(f"""
        # NAME: {self.player.name}
        # STRENGTH: {self.player.strength}
        # AGILITY: {self.player.agility}
        # MAXIMUM HP: {self.player.max_hp}
        # MAXIMUM MP: {self.player.max_mp}
        # ATTACK POWER: {self.player.attack_power}
        # DEFENSE POWER: {self.player.defense_power}
        # WEAPON: {self.player.weapon}
        # ARMOR: {self.player.armor}
        # SHIELD: {self.player.shield}
        # """)
        self.game.unlaunch_menu(self)
        self.game.unpause_all_movement()

    def stairs(self) -> None:
        """
        Go up or down a staircase.
        :return: None
        """
        play_sound(menu_button_sfx)
        # this might be something we could turn off as one of the "modernization" updates
        if self.player.current_tile in ('BRICK_STAIR_DOWN', 'BRICK_STAIR_UP', 'GRASS_STAIR_DOWN'):
            self.game.process_staircase_warps((self.game.player.row, self.game.player.column),
                                              self.game.current_map.staircases[(self.game.player.row, self.game.player.column)])
            # TODO: activate the staircase warp to wherever the staircase leads
        else:
            # the original game has quotes in this dialog box
            self.show_text_in_dialog_box("There are no stairs here.", add_quotes=True, skip_text=self.skip_text)
        self.game.unlaunch_menu(self)
        self.game.unpause_all_movement()

    def search(self) -> None:
        """
        Search the ground for items.
        :return: None
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
            self.display_item_menu('spells')
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
            self.display_item_menu('inventory')

            # self.show_text_in_dialog_box(inventory_string, skip_text=self.skip_text)
        self.game.unlaunch_menu(self)
        self.game.unpause_all_movement()

    def display_item_menu(self, menu_name):
        """Display a menu of selectable items.
        :param menu_name: The name of the menu to display.)
        """
        if menu_name == 'inventory':
            list_counter = Counter(self.player.inventory)
            list_string = ""
            for item, item_amount in list_counter.items():
                if item == "Magic Key":
                    list_string += f"Magic   {item_amount}\n Key \n"
                else:
                    list_string += f"{item}\n"
            function_dict = {
                # purchasable items
                "Herb": self.herb,
                "Wings": self.wings,
                "Torch": self.torch,
                "Dragon's Scale": self.dragon_scale,
                "Fairy Water": self.fairy_water,
                "Magic Key": self.door,
            }
        elif menu_name == 'spells':
            list_counter = Counter(self.player.spells)
            list_string = ""
            for item, item_amount in list_counter.items():
                list_string += f"{item}\n"
            function_dict = {
                # name, function, MP cost
                "HEAL": (self.heal, 4),
                "HURT": (self.hurt, 2),
                "SLEEP": (self.sleep, 2),
                "RADIANT": (self.radiant, 3),
                "STOPSPELL": (self.stopspell, 2),
                "OUTSIDE": (self.outside, 6),
                "RETURN": (self.return_, 8),
                "REPEL": (self.repel, 2),
                "HEALMORE": (self.healmore, 10),
                "HURTMORE": (self.hurtmore, 5)
            }
        else:
            raise ValueError(f"Invalid menu name: {menu_name}")
        item_menu_displayed = True
        current_arrow_position = 0
        currently_selected_item = list(list_counter.keys())[0]
        while item_menu_displayed:
            create_window(x=9, y=3, width=6, height=len(list_counter) + 1,
                          window_background=item_menu_background_lookup[len(list_counter)], screen=self.screen,
                          color=self.game.color)
            draw_text(list_string, TILE_SIZE * 10, TILE_SIZE * 3.75, self.screen)
            blink_arrow(TILE_SIZE * 9.5, (TILE_SIZE + (current_arrow_position * TILE_SIZE / 4)) * 3.75, "right",
                        self.screen, self.game.color)
            display.update((9 * TILE_SIZE, 3 * TILE_SIZE, 6 * TILE_SIZE, (len(list_counter) + 1) * TILE_SIZE))
            for current_event in event.get():
                if any([current_event.type == KEYDOWN]):
                    if current_event.key in (K_ESCAPE, K_j):
                        item_menu_displayed = False
                    elif current_event.key in (K_RETURN, K_k):
                        if menu_name == 'spells':
                            spell_function, spell_mp_cost = function_dict[currently_selected_item]
                            if self.player.current_mp < spell_mp_cost:
                                self.show_text_in_dialog_box("Thy MP is too low.", skip_text=self.skip_text)
                            else:
                                self.show_text_in_dialog_box(
                                    (f"{self.player.name} chanted the spell of {currently_selected_item}.",),
                                    skip_text=self.skip_text)
                                play_sound(spell_sfx)
                                self.player.current_mp -= spell_mp_cost
                                spell_function()
                        else:
                            function_dict[currently_selected_item]()
                        item_menu_displayed = False
                    elif len(menu_name) > 1:
                        if current_event.key in (K_UP, K_w) and current_arrow_position > 0:
                            current_arrow_position -= 1
                        elif current_event.key in (K_DOWN, K_s) and current_arrow_position < len(list_counter) - 1:
                            current_arrow_position += 1
                        currently_selected_item = list(list_counter.keys())[current_arrow_position]

    def door(self) -> None:
        """
        Open a door.
        :return: None
        """
        play_sound(menu_button_sfx)
        if self.player.next_tile_id == 'DOOR':
            if 'Magic Key' in self.player.inventory:
                # actually open the door
                self.player.inventory.remove('Magic Key')
                self.set_tile_by_coordinates('BRICK', self.player.next_coordinates[1], self.player.next_coordinates[0], self.player)
                play_sound(open_door_sfx)
            else:
                self.show_text_in_dialog_box("Thou hast not a key to use.", skip_text=self.skip_text)
        else:
            self.show_text_in_dialog_box("There is no door here.", skip_text=self.skip_text)
        self.game.unlaunch_menu(self)
        self.game.unpause_all_movement()

    def take(self) -> None:
        """
        Take an item.
        :return: None
        """
        play_sound(menu_button_sfx)
        # open a window
        if self.player.current_tile == 'TREASURE_BOX':
            treasure_info = treasure[self.map_name][(self.player.row, self.player.column)]
            item_name = treasure_info['item']
            if item_name:
                if item_name == 'GOLD':
                    self.take_gold(treasure_info)
                else:
                    self.take_item(item_name)
            else:
                self.show_text_in_dialog_box("Unfortunately, it is empty.", skip_text=self.skip_text)
        #     take it and update inventory accordingly
        # elif there is a hidden item
        # take the hidden item
        else:
            self.show_text_in_dialog_box((f"There is nothing to take here, {self.player.name}.",),
                                         skip_text=self.skip_text)
        self.game.unlaunch_menu(self)
        self.game.unpause_all_movement()
