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
                                                                  widget_margin=(10 * SCALE, 5 * SCALE),
                                                                  widget_offset=(0, 5 * SCALE),
                                                                  widget_selection_effect=pygame_menu.widgets.
                                                                  LeftArrowSelection(blink_ms=500,
                                                                                     arrow_size=(SCALE * 5, SCALE * 6)))
        # TODO: Fix LeftArrowSelection size.


class CommandMenu(Menu):

    def __init__(self, background, column, row):
        super().__init__()
        command_menu_subsurface = background.subsurface((column - 2) * TILE_SIZE,
                                                        (row - 6) * TILE_SIZE,
                                                        8 * TILE_SIZE,
                                                        5 * TILE_SIZE)
        self.command_menu = pygame_menu.Menu(height=command_menu_subsurface.get_height() * 3,
                                             width=command_menu_subsurface.get_width() * 2,
                                             title='COMMAND',
                                             center_content=False,
                                             # column_max_width=(TILE_SIZE * 1, TILE_SIZE * 3),
                                             columns=2,
                                             enabled=True,
                                             joystick_enabled=True,
                                             mouse_enabled=False,
                                             mouse_visible=False,
                                             rows=4,
                                             theme=self.dragon_warrior_menu_theme)
        self.command_menu.add.button('TALK', self.talk, margin=(9, 0))
        self.command_menu.add.button('STATUS', self.status, margin=(9, 0))
        self.command_menu.add.button('STAIRS', self.stairs, margin=(9, 0))
        self.command_menu.add.button('SEARCH', self.search, margin=(9, 0))
        self.command_menu.add.button('SPELL', self.spell, margin=(9, 0))
        self.command_menu.add.button('ITEM', self.item, margin=(9, 0))
        self.command_menu.add.button('DOOR', self.door, margin=(9, 0))
        self.command_menu.add.button('TAKE', self.take, margin=(9, 0))

    @staticmethod
    def talk():
        """
        Talk to an NPC. (Not yet implemented)
        :return: To be determined upon implementation
        """
        print("TALK")

    @staticmethod
    def status():
        """
        Display the current player's status. (Not yet implemented)
        :return: To be determined upon implementation
        """
        print("STATUS")

    @staticmethod
    def stairs():
        """
        Go up or down a staircase. (Not yet implemented)
        :return: To be determined upon implementation
        """
        print("STAIRS")

    @staticmethod
    def search():
        """
        Search the ground for items. (Not yet implemented)
        :return: To be determined upon implementation
        """
        print("SEARCH")

    @staticmethod
    def spell():
        """
        Cast a magic spell. (Not yet implemented)
        :return: To be determined upon implementation
        """
        print("SPELL")

    @staticmethod
    def item():
        """
        View/use items. (Not yet implemented)
        :return: To be determined upon implementation
        """
        print("ITEM")

    @staticmethod
    def door():
        """
        Open a door. (Not yet implemented)
        :return: To be determined upon implementation
        """
        print("DOOR")

    @staticmethod
    def take():
        """
        Take an item. (Not yet implemented)
        :return: To be determined upon implementation
        """
        print("TAKE")
