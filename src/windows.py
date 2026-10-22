"""Where the NES puts its windows (NES Bank01 WndwDataPtrTbl and the ...Dat window data after it).

Each window's data starts with its options, its height in blocks, its width in tiles and its position in blocks
(Y in the upper nibble, X in the lower one). A block is 2x2 NES tiles (16 NES pixels; TILE_SIZE screen pixels), and the
NES block grid maps one to one onto this game's screen, so these are the x, y, width and height that
Graphics.create_window takes. Every window width in the NES data is an even number of tiles.
"""
from typing import NamedTuple


class Window(NamedTuple):
    """A window's position and size, in blocks."""
    x: int
    y: int
    width: int
    height: int


# PopupDat ($AFB0): 6 blocks high, 8 tiles wide, Y = 2, X = 1
POPUP_WINDOW = Window(1, 2, 4, 6)
# StatusDat ($AFC7): 11 blocks high, 20 tiles wide, Y = 3, X = 5
STATUS_WINDOW = Window(5, 3, 10, 11)
# DialogDat ($B04B): 5 blocks high, 24 tiles wide, Y = 9, X = 2
DIALOG_WINDOW = Window(2, 9, 12, 5)
# CmdNonCmbtDat ($B054): 5 blocks high, 16 tiles wide, Y = 1, X = 6
COMMAND_WINDOW = Window(6, 1, 8, 5)
# Its title is in the top border after the corner and 3 border tiles ($8B, "COMMAND")
COMMAND_TITLE_TILE_COLUMN = 4
# CmdCmbtDat ($B095): 3 blocks high, 16 tiles wide, Y = 1, X = 6
COMBAT_COMMAND_WINDOW = Window(6, 1, 8, 3)
# SpellDat ($B0BA) and PlayerInvDat ($B0CC) are variable height; see item_menu_window below.
# ShopInvDat ($B0DA): 18 tiles wide, Y = 2, X = 5. Variable height (WndVariableHeight): one block per item plus one
# for the borders, so the height given here (8 blocks in the data) is only the most it can be.
SHOP_INVENTORY_WINDOW = Window(5, 2, 9, 8)
# draw_text's right edge for a cost in the shop inventory window: a cost is 5 tiles wide after the first half of the
# name (9 tiles from column 2) and a blank tile, so it ends at column 16; this is the left edge of column 17
SHOP_COST_RIGHT_TILE_COLUMN = 17
# YesNo1Dat ($B0EB): 3 blocks high, 8 tiles wide, Y = 2, X = 5
YES_NO_WINDOW = Window(5, 2, 4, 3)
# BuySellDat ($B0FB): 3 blocks high, 8 tiles wide, Y = 2, X = 5
BUY_SELL_WINDOW = Window(5, 2, 4, 3)
# AlphabetDat ($B10D): 7 blocks high, 24 tiles wide, Y = 5, X = 2
ALPHABET_WINDOW = Window(2, 5, 12, 7)
# MsgSpeedDat ($B194): 7 blocks high, 18 tiles wide, Y = 7, X = 4
MESSAGE_SPEED_WINDOW = Window(4, 7, 9, 7)
# InputNameDat ($B1E0): 2 blocks high, 20 tiles wide, Y = 7, X = 3
INPUT_NAME_WINDOW = Window(3, 7, 10, 2)
# NameEntryDat ($B1F7): 3 blocks high, 12 tiles wide, Y = 3, X = 5
NAME_ENTRY_WINDOW = Window(5, 3, 6, 3)
# ContChngErsDat ($B20B): 4 blocks high, 24 tiles wide, Y = 4, X = 2
CONTINUE_CHANGE_ERASE_WINDOW = Window(2, 4, 12, 4)
# FullMenuDat ($B249): 6 blocks high, 24 tiles wide, Y = 4, X = 2
FULL_MENU_WINDOW = Window(2, 4, 12, 6)
# NewQuestDat ($B2A8): 2 blocks high, 24 tiles wide, Y = 4, X = 2
NEW_QUEST_WINDOW = Window(2, 4, 12, 2)
# LogList1Dat1 ($B2C2) to LogList123Dat1 ($B385): 20 tiles wide, Y = 9, X = 5; 1 block high plus one per log listed
ADVENTURE_LOG_WINDOW_1 = Window(5, 9, 10, 4)
# LogList1Dat2 ($B3BF) to LogList123Dat2 ($B494): 24 tiles wide, Y = 6, X = 3; 1 block high plus one per log listed
ADVENTURE_LOG_WINDOW_2 = Window(3, 6, 12, 4)
# EraseLogDat ($B4D4): 6 blocks high, 20 tiles wide, Y = 7, X = 3
ERASE_LOG_WINDOW = Window(3, 7, 10, 6)
# YesNo2Dat ($B50D): 3 blocks high, 8 tiles wide, Y = 3, X = 10
YES_NO_2_WINDOW = Window(10, 3, 4, 3)


def variable_height_window(window: Window, number_of_entries: int) -> Window:
    """A variable height window (WndVariableHeight, WndBuildVariable, WndBuildEnd) sized to its entries: one block
    per entry plus one block for the top and bottom borders."""
    return window._replace(height=number_of_entries + 1)


# The SPELL and ITEM windows (NES Bank01 SpellDat and PlayerInvDat; the discard window is PlayerInvDat too).
# Positions and sizes are in blocks of 2x2 NES tiles (16 NES pixels, TILE_SIZE screen pixels), as in the window data.
# Both windows are 12 tiles (6 blocks) wide at block column 9; the SPELL window is at block row 2, the ITEM window at
# row 3. Both are variable height (WndVariableHeight, WndBuildVariable, WndBuildEnd): one block per entry plus one
# for the borders, so 2 to 11 blocks for 1 to 10 spells or items. The cursor moves 2 tile rows (one block) per entry
# (WndDownCont3).
ITEM_MENU_X = 9
ITEM_MENU_WIDTH = 6
ITEM_MENU_Y = {'spells': 2, 'inventory': 3, 'discard': 3}
# Tile row of the first entry, from the cursor home position: SpellDat is double spaced, so the title row is followed
# by a blank row; PlayerInvDat is single spaced, its first item's name starts on the row after the top border.
ITEM_MENU_FIRST_TILE_ROW = {'spells': 2, 'inventory': 1, 'discard': 1}
# The window corners are one NES tile (8 NES pixels)
ITEM_MENU_BORDER = 8
# Tile column of the SPELL window's title, after the corner and 3 border tiles (SpellDat: $8B, "SPELL")
SPELL_MENU_TITLE_TILE_COLUMN = 4
# NES ItemNames11TbL/ItemNames12TbL/ItemNames21TbL/ItemNames22TbL (Bank01): an item's name is shown in two halves,
# the second one on the next tile row, indented by one tile (PlayerInvDat: $81, first half, $82, second half).
ITEM_NAME_HALVES = {
    "Herb": ("Herb", ""),
    "Torch": ("Torch", ""),
    "Dragon's Scale": ("Dragon's", "Scale"),
    "Wings": ("Wings", ""),
    "Magic Key": ("Magic", "Key"),
    "Fairy Water": ("Fairy", "Water"),
    "Ball of Light": ("Ball of", "Light"),
    "Tablet": ("Tablet", ""),
    "Fairy Flute": ("Fairy", "Flute"),
    "Silver Harp": ("Silver", "Harp"),
    "Staff of Rain": ("Staff of", "Rain"),
    "Stones of Sunlight": ("Stones of", "Sunlight"),
    "Gwaelin's Love": ("Gwaelin's", "Love"),
    "Rainbow Drop": ("Rainbow", "Drop"),
    "Cursed Belt": ("Cursed", "Belt"),
    "Death Necklace": ("Death", "Necklace"),
    "Fighter's Ring": ("Fighter's", "Ring"),
    "Erdrick's Token": ("Erdrick's", "Token"),
}
# The same tables name the weapons, armor and shields, which the status window shows in two halves too (StatusDat:
# $B8, $B9 and $BA)
EQUIPMENT_NAME_HALVES = {
    "Bamboo Pole": ("Bamboo", "Pole"),
    "Club": ("Club", ""),
    "Copper Sword": ("Copper", "Sword"),
    "Hand Axe": ("Hand", "Axe"),
    "Broad Sword": ("Broad", "Sword"),
    "Flame Sword": ("Flame", "Sword"),
    "Erdrick's Sword": ("Erdrick's", "Sword"),
    "Clothes": ("Clothes", ""),
    "Leather Armor": ("Leather", "Armor"),
    "Chain Mail": ("Chain", "Mail"),
    "Half Plate": ("Half", "Plate"),
    "Full Plate": ("Full", "Plate"),
    "Magic Armor": ("Magic", "Armor"),
    "Erdrick's Armor": ("Erdrick's", "Armor"),
    "Small Shield": ("Small", "Shield"),
    "Large Shield": ("Large", "Shield"),
    "Silver Shield": ("Silver", "Shield"),
}


def name_halves(name: str) -> tuple[str, str]:
    """An item's or a piece of equipment's name in the two halves the NES shows it in (see ITEM_NAME_HALVES)."""
    return ITEM_NAME_HALVES.get(name) or EQUIPMENT_NAME_HALVES.get(name) or (name, "")


# NES WndItemDesc: herbs and keys show how many the hero has, in the tile column after an 8 tile name
COUNTED_ITEMS = ("Herb", "Magic Key")
ITEM_COUNT_TILE_COLUMN = 10

# The status window (NES StatusDat): single spaced, but every line but the equipment is followed by a blank row ($80).
# The name follows "NAME:" (tile columns 6-10); the numbers are 3 tiles wide and end at column 18, the last one before
# the right border; the weapon, armor and shield follow "WEAPON:", "ARMOR:" and "SHIELD:" (which end at column 9).
STATUS_NAME_TILE_COLUMN = 11
STATUS_NAME_TILE_ROW = 1
# Strength, agility, maximum HP, maximum MP, attack power and defense power
STATUS_VALUE_TILE_ROWS = (3, 5, 7, 9, 11, 13)
# draw_text's right edge for the numbers: the left edge of column 19, the right border
STATUS_VALUE_RIGHT_TILE_COLUMN = 19
# Weapon, armor and shield: the first half of the name on these rows, the second half on the next one
STATUS_EQUIPMENT_TILE_ROWS = (15, 17, 19)
STATUS_EQUIPMENT_TILE_COLUMN = 10


def item_menu_window(menu_name: str, number_of_entries: int) -> tuple[int, int, int, int]:
    """
    The SPELL or ITEM window's position and size for a number of entries.
    :param menu_name: 'spells', 'inventory' or 'discard'.
    :param number_of_entries: How many spells or items are listed (see src.items.inventory_list).
    :return: (x, y, width, height), in blocks.
    """
    return ITEM_MENU_X, ITEM_MENU_Y[menu_name], ITEM_MENU_WIDTH, number_of_entries + 1


# Tile column of an entry's text (after the left border and the cursor column) and of the cursor (cursor home X = 1)
ITEM_MENU_TEXT_TILE_COLUMN = 2
ITEM_MENU_CURSOR_TILE_COLUMN = 1


def item_menu_entry_tile_row(menu_name: str, index: int) -> int:
    """
    The tile row of an entry in the SPELL or ITEM window, counted from the window's top border. Entries are 2 tile rows
    (one block) apart; the cursor is drawn on the same row.
    :param menu_name: 'spells', 'inventory' or 'discard'.
    :param index: The entry's index in the window, from 0.
    :return: The tile row.
    """
    return ITEM_MENU_FIRST_TILE_ROW[menu_name] + 2 * index
