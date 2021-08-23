import pygame_menu

from common import DRAGON_QUEST_FONT_PATH, BLACK, WHITE
from config import SCALE, TILE_SIZE


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

    def __init__(self, background, column, row):
        super().__init__()
        command_menu_subsurface = background.subsurface((column - 2) * TILE_SIZE,
                                                        (row - 6) * TILE_SIZE,
                                                        8 * TILE_SIZE,
                                                        5 * TILE_SIZE)
        self.command_menu = pygame_menu.Menu('COMMAND',
                                             command_menu_subsurface.get_width() * 2,
                                             command_menu_subsurface.get_height() * 3,
                                             center_content=False,
                                             column_max_width=(TILE_SIZE * 4, TILE_SIZE * 4),
                                             columns=2,
                                             rows=4,
                                             theme=self.dragon_warrior_menu_theme,
                                             mouse_enabled=False,
                                             mouse_visible=False,
                                             )
        # TODO: Allow for selection of options using the K ("A" button).
        #  Currently selection is only possible by use of the Enter button.
        self.command_menu.add.button('TALK', self.talk, margin=(9, 4))
        self.command_menu.add.button('STATUS', self.status, margin=(9, 4))
        self.command_menu.add.button('STAIRS', self.stairs, margin=(9, 4))
        self.command_menu.add.button('SEARCH', self.search, margin=(9, 4))
        self.command_menu.add.button('SPELL', self.spell, margin=(0, 4))
        self.command_menu.add.button('ITEM', self.item, margin=(0, 4))
        self.command_menu.add.button('DOOR', self.door, margin=(0, 4))
        self.command_menu.add.button('TAKE', self.take, margin=(0, 4))

    def talk(self):
        """
        Talk to an NPC. (Not yet implemented)
        :return: To be determined upon implementation
        """
        # open another window
        # check if block in front of player contains an NPC
        # if it does:
        #      print the contents of the NPC's dialog to the window
        # else:
        #      print 'There is no one there.' to the window
        print("TALK")

    @staticmethod
    def status():
        """
        Display the current player's status. (Not yet implemented)
        :return: To be determined upon implementation
        """
        # open another window (11 tall x 10 wide)
        # print the following attributes:
        # example below:

        # NAME: ED
        # STRENGTH: 22
        # MAXIMUM HP: 44
        # MAXIMUM MP: 29
        # ATTACK POWER: 37
        # DEFENSE POWER: 20
        # WEAPON: Hand Axe
        # ARMOR: Chain Mail
        # SHIELD: Small Shield

        print("STATUS")

    @staticmethod
    def stairs():
        """
        Go up or down a staircase. (Not yet implemented)
        :return: To be determined upon implementation
        """
        # this might be something we could turn off as one of the "modernization" updates, but the implementation would be as follows:
        # check if the player is standing on a staircase
        # if so, activate the staircase warp to wherever the staircase leads
        # else:
        # open a window and print: 'There are no stairs here.'
        print("STAIRS")

    @staticmethod
    def search():
        """
        Search the ground for items. (Not yet implemented)
        :return: To be determined upon implementation
        """
        # open a window
        # print f"{player_name} searched the ground all about."
        # wait for input...
        # check if there is anything on the ground:
        # if so:
        # print: f"There is a {item}."
        print("SEARCH")

    @staticmethod
    def spell():
        """
        Cast a magic spell. (Not yet implemented)
        :return: To be determined upon implementation
        """
        # the implementation of this will vary upon which spell is being cast.
        print("SPELL")

    @staticmethod
    def item():
        """
        View/use items. (Not yet implemented)
        :return: To be determined upon implementation
        """
        # the implementation of this will vary upon which item is being used.
        print("ITEM")

    @staticmethod
    def door():
        """
        Open a door. (Not yet implemented)
        :return: To be determined upon implementation
        """
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
        print("DOOR")

    @staticmethod
    def take():
        """
        Take an item. (Not yet implemented)
        :return: To be determined upon implementation
        """
        # open a window
        # check if there is something to take
        # if there is something to take:
        #   take it and update inventory accordingly
        # else:
        #   print 'There is nothing to take here, {player_name}.'
        print("TAKE")
