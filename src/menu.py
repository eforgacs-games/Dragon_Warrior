import pygame_menu

from common import DRAGON_QUEST_FONT_PATH, BLACK, WHITE, play_sound, menu_button_sfx
from config import SCALE, TILE_SIZE
from data.text.dialog import Dialog
from src.common import print_with_beep_sfx


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
                                                                      #  Might be a problem with pygame-menu. Investigation needed.
                                                                      # blink_ms=500,
                                                                      # TODO: Fix LeftArrowSelection size.
                                                                      arrow_size=(SCALE * 5, SCALE * 6))
                                                                  )


class CommandMenu(Menu):

    def __init__(self, background, column, row, next_tile, characters, dialog_box):
        super().__init__()
        self.dialog_box = dialog_box
        self.next_tile = next_tile
        self.characters = characters
        self.player_name = 'Eddie'
        self.launch_signaled = False
        self.launched = False
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
        dialog = Dialog(player_name='Eddie')

        # for now, implementing using print statements. will be useful for debugging as well.
        if self.next_tile in [character.name for character in self.characters]:
            self.dialog_box.launch_signaled = True
            dialog.dialog_lookup[self.next_tile]()
        else:
            print_with_beep_sfx("'There is no one there.'")

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
        NAME: {self.player_name}
        STRENGTH: 22
        MAXIMUM HP: 44
        MAXIMUM MP: 29
        ATTACK POWER: 37
        DEFENSE POWER: 20
        WEAPON: Hand Axe
        ARMOR: Chain Mail
        SHIELD: Small Shield
        """)

    @staticmethod
    def stairs():
        """
        Go up or down a staircase. (Not yet implemented)
        :return: To be determined upon implementation
        """
        play_sound(menu_button_sfx)
        # this might be something we could turn off as one of the "modernization" updates, but the implementation would be as follows:
        # check if the player is standing on a staircase
        # if so, activate the staircase warp to wherever the staircase leads
        # else:
        # open a window and print:
        print("'There are no stairs here.'")

    def search(self):
        """
        Search the ground for items. (Not yet implemented)
        :return: To be determined upon implementation
        """
        play_sound(menu_button_sfx)
        # open a window
        print(f"{self.player_name} searched the ground all about.")
        print(f"But there found nothing.")
        # print f"{player_name} searched the ground all about."
        # wait for input...
        # check if there is anything on the ground:
        # if so:
        # print: f"There is a {item}."

    def spell(self):
        """
        Cast a magic spell. (Not yet implemented)
        :return: To be determined upon implementation
        """
        play_sound(menu_button_sfx)
        # the implementation of this will vary upon which spell is being cast.
        print(f"{self.player_name} cannot yet use the spell.")

    @staticmethod
    def item():
        """
        View/use items. (Not yet implemented)
        :return: To be determined upon implementation
        """
        play_sound(menu_button_sfx)
        # the implementation of this will vary upon which item is being used.
        # if no items:
        print("Nothing of use has yet been given to thee.")

    def door(self):
        """
        Open a door. (Not yet implemented)
        :return: To be determined upon implementation
        """
        play_sound(menu_button_sfx)
        if self.next_tile != 'DOOR':
            print("There is no door here.")
        else:
            print("Thou hast not a key to use.")
        # check if there is a door in front of the player
        # if there is a door in front:
        #   check if it is a locked door
        #   if it is locked:
        #       check if the player has a key
        #       if the player does have a key:
        #           open the door
        #       else:
        #           open a window and print "Thou hast not a key to use."
        #   else:
        #       open the door

    def take(self):
        """
        Take an item. (Not yet implemented)
        :return: To be determined upon implementation
        """
        play_sound(menu_button_sfx)
        # open a window
        # check if there is something to take
        # if there is something to take:
        #   take it and update inventory accordingly
        # else:
        print(f'There is nothing to take here, {self.player_name}.')


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
