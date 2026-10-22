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


class WindowText(NamedTuple):
    """Text in a window, at a tile position counted from the window's top left corner tile (column 0 is the left
    border, row 0 the top border; text in row 0 is a title in the top border)."""
    text: str
    column: int
    row: int


class WindowLayout(NamedTuple):
    """What a window's data draws (src/window_renderer.py draws it): its position and size, its title in the top
    border, its text, and the cursor's tile for each selectable entry, in selection order. Text and cursor positions
    are tiles counted from the window's top left corner tile."""
    window: Window
    title: WindowText | None = None
    texts: tuple[WindowText, ...] = ()
    cursor_tiles: tuple[tuple[int, int], ...] = ()


def selection_cursor_tiles(home_column: int, home_row: int, columns: int, column_spacing: int, rows: int,
                           row_spacing: int = 2) -> tuple[tuple[int, int], ...]:
    """The cursor's tile for each entry of a selection window, row by row (the order the NES numbers the entries):
    the window data's cursor home (its first entry) and its columns' spacing. Rows are one block (2 tiles) apart."""
    return tuple((home_column + column * column_spacing, home_row + row * row_spacing)
                 for row in range(rows) for column in range(columns))


# CmdCmbtDat ($B095): a selection window (options $80) with 2 columns 8 tiles apart ($08) and the cursor home at
# Y = 2 tiles, X = 1 tile ($21). The top border has 3 border tiles ($8B), "COMMAND", and border to the end ($88);
# then, on the cursor home's row, 1 blank tile ($81), FIGHT, 3 blank tiles ($83), SPELL, and on the next one 1 blank
# tile ($81), RUN, 5 blank tiles ($85), ITEM.
COMBAT_COMMAND_LAYOUT = WindowLayout(
    window=COMBAT_COMMAND_WINDOW,
    title=WindowText("COMMAND", COMMAND_TITLE_TILE_COLUMN, 0),
    texts=(WindowText("FIGHT", 2, 2), WindowText("SPELL", 10, 2), WindowText("RUN", 2, 4), WindowText("ITEM", 10, 4)),
    # FIGHT, SPELL, RUN, ITEM
    cursor_tiles=selection_cursor_tiles(home_column=1, home_row=2, columns=2, column_spacing=8, rows=2),
)


# PopupDat ($AFB0): the top border has 1 border tile ($89), the name, 4 tiles ($B0), and border to the end ($88), so
# the border tile before the name is TL_TOP2 whatever the name is. The labels follow, double spaced (a blank row after
# each), each in the tile after the left border: LV ($2F, $39), HP ($2B, $33), MP ($30, $33), G ($2A) and E ($28).
# The name and the values ($A0, $90, $94, $98, $A8) are drawn over the window (Drawer.draw_hovering_stats_window).
POPUP_NAME_TILE_COLUMN = 2
POPUP_NAME_LENGTH = 4
POPUP_LAYOUT = WindowLayout(
    window=POPUP_WINDOW,
    title=WindowText(" " * POPUP_NAME_LENGTH, POPUP_NAME_TILE_COLUMN, 0),
    texts=tuple(WindowText(label, 1, row) for label, row in (("LV", 2), ("HP", 4), ("MP", 6), ("G", 8), ("E", 10))),
)

# StatusDat ($AFC7): single spaced, but every line but the equipment is followed by a blank row ($80). Each label is
# after a run of blank tiles ($85 NAME:, $86 STRENGTH:, $87 AGILITY:, $84 MAXIMUM HP:, $84 MAXIMUM MP:, $82 ATTACK
# POWER:, $81 DEFENSE POWER:, $82 WEAPON:, $83 ARMOR:, $82 SHIELD:), counted from the tile after the left border.
# The name, the numbers and the equipment are drawn over the window (CommandMenu.draw_status_window).
STATUS_LAYOUT = WindowLayout(
    window=STATUS_WINDOW,
    texts=(
        WindowText("NAME:", 6, 1),
        WindowText("STRENGTH:", 7, 3),
        WindowText("AGILITY:", 8, 5),
        WindowText("MAXIMUM HP:", 5, 7),
        WindowText("MAXIMUM MP:", 5, 9),
        WindowText("ATTACK POWER:", 3, 11),
        WindowText("DEFENSE POWER:", 2, 13),
        WindowText("WEAPON:", 3, 15),
        WindowText("ARMOR:", 4, 17),
        WindowText("SHIELD:", 3, 19),
    ),
)

# DialogDat ($B04B): the border ($88) and 4 rows of blank tiles ($80); the text is drawn over it (src/dialog_box.py)
DIALOG_LAYOUT = WindowLayout(DIALOG_WINDOW)

# YesNo1Dat ($B0EB): a selection window (options $80) of 1 column with the cursor home at Y = 2 tiles, X = 1 tile
# ($21); after the top border ($88), 1 blank tile ($81) and YES ($3C, $28, $36), then 1 blank tile ($81) and NO ($31,
# $32), double spaced. The cursor tiles are YES, then NO.
YES_NO_LAYOUT = WindowLayout(
    window=YES_NO_WINDOW,
    texts=(WindowText("YES", 2, 2), WindowText("NO", 2, 4)),
    cursor_tiles=selection_cursor_tiles(home_column=1, home_row=2, columns=1, column_spacing=0, rows=2),
)


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


# ShopInvDat ($B0DA): a selection window (options $A0: single spaced), 1 column, cursor home Y = 1 tile, X = 1 tile
# ($11). After the top border ($88), each item (one block, $D5 then $E8 repeat the item lines for the shop's
# ShopItemsTbl entries) is: 1 blank tile ($81), the first half of its name ($BC, ItemNames11TbL/ItemNames21TbL, at
# most 9 tiles), 1 blank tile ($81), its cost ($C8, WndItemCost: 5 tiles, right-aligned, no leading zeros); and on the
# next tile row 2 blank tiles ($82), the second half of its name ($BC, ItemNames12TbL/ItemNames22TbL).
SHOP_ITEM_NAME_TILE_COLUMN = 2
SHOP_ITEM_SECOND_HALF_TILE_COLUMN = 3
SHOP_ITEM_COST_TILES = 5


def shop_inventory_layout(item_names: tuple[str, ...], costs: tuple[int, ...]) -> WindowLayout:
    """
    The shop inventory window (ShopInvDat) for a shop's stock, as the NES builds it: as high as the stock
    (WndVariableHeight), each item's name in its two halves (name_halves) and its cost right-aligned, ending in the
    tile column before SHOP_COST_RIGHT_TILE_COLUMN.
    :param item_names: The shop's items, in ShopItemsTbl order (src/shops.py).
    :param costs: Their costs (ItemCostTbl), in the same order.
    """
    texts: list[WindowText] = []
    for index, (name, cost) in enumerate(zip(item_names, costs)):
        row = 1 + 2 * index
        first_half, second_half = name_halves(name)
        cost_text = str(cost)
        if len(cost_text) > SHOP_ITEM_COST_TILES:
            raise ValueError(f"{name} costs {cost}: WndItemCost shows at most {SHOP_ITEM_COST_TILES} digits")
        texts.append(WindowText(first_half, SHOP_ITEM_NAME_TILE_COLUMN, row))
        texts.append(WindowText(cost_text, SHOP_COST_RIGHT_TILE_COLUMN - len(cost_text), row))
        if second_half:
            texts.append(WindowText(second_half, SHOP_ITEM_SECOND_HALF_TILE_COLUMN, row + 1))
    return WindowLayout(window=variable_height_window(SHOP_INVENTORY_WINDOW, len(item_names)), texts=tuple(texts),
                        cursor_tiles=selection_cursor_tiles(home_column=1, home_row=1, columns=1, column_spacing=0,
                                                            rows=len(item_names)))


# BuySellDat ($B0FB): a selection window (options $80: double spaced), 1 column, cursor home Y = 2 tiles, X = 1 tile
# ($21). After the top border ($88), a blank row, then 1 blank tile ($81) and BUY, a blank row, 1 blank tile ($81) and
# SELL.
BUY_SELL_LAYOUT = WindowLayout(
    window=BUY_SELL_WINDOW,
    texts=(WindowText("BUY", 2, 2), WindowText("SELL", 2, 4)),
    # BUY, SELL
    cursor_tiles=selection_cursor_tiles(home_column=1, home_row=2, columns=1, column_spacing=0, rows=2),
)


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


def item_menu_layout(menu_name: str, number_of_entries: int) -> WindowLayout:
    """
    The SPELL or ITEM window's border (SpellDat, PlayerInvDat), sized to its entries (see item_menu_window). The
    title and the entries are drawn over it (CommandMenu.draw_item_menu), so that they can be translated.
    :param menu_name: 'spells', 'inventory' or 'discard'.
    :param number_of_entries: How many spells or items are listed.
    """
    return WindowLayout(Window(*item_menu_window(menu_name, number_of_entries)))


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
