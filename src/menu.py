import pygame_menu

from data.text.dialog_lookup_table import DialogLookupTable
from src.common import DRAGON_QUEST_FONT_PATH, BLACK, WHITE, play_sound, menu_button_sfx, get_opposite_direction
from src.common import print_with_beep_sfx
from src.config import SCALE, TILE_SIZE


class Menu:
    def __init__(self):
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


class CommandMenu(Menu):

    def __init__(self, background, column, row, current_tile, current_map, dialog_box, player):
        super().__init__()
        self.dialog_box = dialog_box
        self.current_tile = current_tile
        self.characters = current_map.characters
        self.player = player
        self.launch_signaled = False
        self.launched = False
        self.map_name = current_map.__class__.__name__
        self.background = background
        command_menu_subsurface = background.subsurface((column - 2) * TILE_SIZE,
                                                        (row - 6) * TILE_SIZE,
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

    def talk(self):
        """
        Talk to an NPC. (Not yet implemented)
        :return: To be determined upon implementation
        """
        play_sound(menu_button_sfx)
        # dialog = Dialog(player=self.player)
        # TODO: Get an actual dialog box to show!

        # for now, implementing using print statements. will be useful for debugging as well.
        if self.player.next_tile_id not in self.characters.keys() and self.player.next_next_tile_id not in self.characters.keys():
            print_with_beep_sfx("'There is no one there.'")
            return
        for character_identifier, character_info in self.characters.items():
            if character_info['coordinates'] == self.player.next_coordinates or self.npc_is_across_counter(character_info):
                if character_info['character'].direction != get_opposite_direction(self.player.direction):
                    character_info['character'].direction = get_opposite_direction(self.player.direction)
                    character_info['character'].animate()
                    character_info['character'].pause()
                self.launch_dialog(character_identifier)
                break

    def npc_is_across_counter(self, character_info):
        return self.player.next_tile_id == 'WOOD' and character_info['coordinates'] == self.player.next_next_coordinates

    def launch_dialog(self, dialog_character):
        self.dialog_box.launch_signaled = True
        dlt = DialogLookupTable(self.player, self.map_name, dialog_character)
        character = dlt.dialog_lookup.get(self.player.next_tile_id)
        character_across_counter = dlt.dialog_lookup.get(self.player.next_next_tile_id)
        if character:
            character.say_dialog()
        elif character_across_counter:
            character_across_counter.say_dialog()
        else:
            print("Character not in lookup table.")

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
        if self.player.current_tile in ('BRICK_STAIR_DOWN', 'BRICK_STAIRUP', 'GRASS_STAIRDN'):
            print("'There are stairs here.'")
            # TODO: activate the staircase warp to wherever the staircase leads
        else:
            print("'There are no stairs here.'")

    def search(self):
        """
        Search the ground for items. (Not yet implemented)
        :return: To be determined upon implementation
        """
        play_sound(menu_button_sfx)
        # open a window
        print(f"{self.player.name} searched the ground all about.")
        # wait for input...
        if self.player.current_tile == 'TREASURE_BOX':
            print(f"There is a {self.player.current_tile.lower().replace('_', ' ')}.")
        # elif there is a hidden item:
        # print(f"There is a {hidden_item}")
        else:
            print(f"But there found nothing.")

    def spell(self):
        """
        Cast a magic spell. (Not yet implemented)
        :return: To be determined upon implementation
        """
        play_sound(menu_button_sfx)
        # the implementation of this will vary upon which spell is being cast.
        if not self.player.spells:
            print(f"{self.player.name} cannot yet use the spell.")
        else:
            print(self.player.spells)

    def item(self):
        """
        View/use items. (Not yet implemented)
        :return: To be determined upon implementation
        """
        play_sound(menu_button_sfx)
        # the implementation of this will vary upon which item is being used.
        if not self.player.inventory:
            print("Nothing of use has yet been given to thee.")
        else:
            print(self.player.inventory)

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
                print("Thou hast not a key to use.")
        else:
            print("There is no door here.")

    def take(self):
        """
        Take an item. (Not yet implemented)
        :return: To be determined upon implementation
        """
        play_sound(menu_button_sfx)
        # open a window
        if self.player.current_tile == 'TREASURE_BOX':
            print("Took what was in the treasure box.")
        #     take it and update inventory accordingly
        # elif there is a hidden item
        # take the hidden item
        else:
            print(f'There is nothing to take here, {self.player.name}.')


class DialogBox(Menu):
    def __init__(self, background, column, row):
        super().__init__()
        self.launch_signaled = False
        self.launched = False
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


def draw_menu_on_subsurface(menu_to_draw, subsurface):
    return menu_to_draw.draw(subsurface)
