import random
from collections.abc import Iterable

from src.coordinates import Cell


# Equipment and tool prices are the NES ItemCostTbl (Bank00); the towns are from ShopItemsTbl.

weapons = {
    "Bamboo Pole": {'offense': 2, 'cost': 10, 'found': ("Brecconary", "Cantlin")},
    "Club": {'offense': 4, 'cost': 60, 'found': ("Brecconary", "Cantlin", "Garinham")},
    "Copper Sword": {'offense': 10, 'cost': 180, 'found': ("Brecconary", "Cantlin", "Garinham", "Kol", "Rimuldar")},
    "Hand Axe": {'offense': 15, 'cost': 560, 'found': ("Garinham", "Kol", "Rimuldar", "Cantlin")},
    "Broad Sword": {'offense': 20, 'cost': 1500, 'found': ("Rimuldar", "Cantlin")},
    "Flame Sword": {'offense': 28, 'cost': 9800, 'found': ("Cantlin",)},
    "Erdrick's Sword": {'offense': 40, 'cost': 2, 'found': "Dragonlord's Castle"},
    # adding Erdrick's Sword without the apostrophe
    "Erdricks Sword": {'offense': 40, 'cost': 2, 'found': "Dragonlord's Castle"}
}

armor = {
    "Clothes": {'defense': 2, 'cost': 20, 'sold': ("Brecconary",)},
    "Leather Armor": {'defense': 4, 'cost': 70, 'sold': ("Brecconary", "Garinham", "Cantlin")},
    "Chain Mail": {'defense': 10, 'cost': 300, 'sold': ("Garinham", "Cantlin")},
    "Half Plate": {'defense': 16, 'cost': 1000, 'sold': ("Garinham", "Kol", "Rimuldar")},
    "Full Plate": {'defense': 24, 'cost': 3000, 'sold': ("Kol", "Rimuldar", "Cantlin")},
    "Magic Armor": {'defense': 24, 'cost': 7700, 'sold': ("Rimuldar", "Cantlin")},
    "Erdrick's Armor": {'defense': 28, 'cost': 2, 'found': ("Hauksness",)}
    # restores a lost hit point for every step you take
    # and prevents damage from walking on damaging tiles.
    # This reduces damage from HURT AND HURTMORE by 1/3,
    # prevents Stopspell from working against you.
    # It also reduces damage from flame breath attacks by 1/3 as well.
}

shields = {
    "Small Shield": {'defense': 4, 'cost': 90, 'sold': ("Brecconary", "Kol")},
    "Large Shield": {'defense': 10, 'cost': 800, 'sold': ("Garinham", "Cantlin")},
    "Silver Shield": {'defense': 20, 'cost': 14_800, 'sold': ("Cantlin",)},
}

# Every item that can sit in the inventory. NES NonDiscardTbl: these can't be dropped to make room for a new item.
# Herbs and Magic Keys are counted separately on the NES (InventoryHerbs/InventoryKeys, up to 6 each), so they don't
# use any of the 8 inventory slots.
NON_DISCARDABLE_ITEMS = ("Herb", "Magic Key", "Fairy Flute", "Erdrick's Token", "Gwaelin's Love", "Silver Harp",
                         "Stones of Sunlight", "Staff of Rain", "Rainbow Drop")
UNSLOTTED_ITEMS = ("Herb", "Magic Key")
INVENTORY_SLOTS = 8  # NES AddInvItem: 4 bytes of 2 items each
MAX_HERBS = 6
MAX_KEYS = 6
MAX_GOLD = 65535


def inventory_list(inventory: list[str]) -> list[str]:
    """The items as the NES lists them in the ITEM, discard and sell windows (Bank03 CreateInvList): Herbs, then Magic
    Keys (one entry each, however many there are), then each inventory slot in order, so two Torches are two
    entries."""
    return [item for item in UNSLOTTED_ITEMS if item in inventory] + \
        [item for item in inventory if item not in UNSLOTTED_ITEMS]

GOLD = "GOLD"


def _gold(base: int, random_bits: int) -> dict[str, object]:
    """NES GetTrsrGold: the chest holds base + (random byte AND random_bits) gold, rolled when it is opened."""
    return {'item': GOLD, 'gold': (base, random_bits)}


# NES TreasureTbl (Bank01): every treasure chest in the game, keyed by map and then by (row, column) in this game's
# layouts. Each map's layout is padded, so the NES (x, y) of each chest is noted next to it, with the map's offset.
# Chests on other maps (Kol, Cantlin, the Rainbow Drop cave...) aren't in the NES table, and TAKE finds nothing in them.

# NES ItemCostTbl (Bank00), tool entries. Shops buy a tool back for half this (DoToolSell), and refuse
# anything that costs 0 ("I cannot buy it.").
tools = {
    "Herb": {'cost': 24},
    "Magic Key": {'cost': 53},
    "Torch": {'cost': 8},
    "Fairy Water": {'cost': 38},
    "Wings": {'cost': 70},
    "Dragon's Scale": {'cost': 20},
    "Fairy Flute": {'cost': 0},
    "Fighter's Ring": {'cost': 30},
    "Erdrick's Token": {'cost': 0},
    "Gwaelin's Love": {'cost': 0},
    "Cursed Belt": {'cost': 360},
    "Silver Harp": {'cost': 0},
    "Death Necklace": {'cost': 2400},
    "Stones of Sunlight": {'cost': 0},
    "Staff of Rain": {'cost': 0},
    "Rainbow Drop": {'cost': 0},
}

treasure: dict[str, dict[Cell, dict[str, object]]] = {
    # MAP_TANTCSTL_GF: row = y + 7, column = x + 7
    'TantegelCourtyard': {
        (20, 8): _gold(6, 0x07),  # (1, 13): 6-13 gold
        (22, 8): _gold(6, 0x07),  # (1, 15): 6-13 gold
        (21, 9): _gold(6, 0x07),  # (2, 14): 6-13 gold
        (22, 10): _gold(6, 0x07),  # (3, 15): 6-13 gold
    },
    # MAP_THRONEROOM: row = y + 6, column = x + 10
    'TantegelThroneRoom': {
        (10, 14): _gold(120, 0x00),  # (4, 4): 120 gold
        (10, 15): {'item': 'Torch'},  # (5, 4)
        (7, 16): {'item': 'Magic Key'},  # (6, 1)
    },
    # MAP_RIMULDAR: row = y + 8, column = x + 8
    'Rimuldar': {
        (31, 32): {'item': 'Wings'},  # (24, 23)
    },
    # MAP_GARINHAM: row = y + 1, column = x + 9
    'Garinham': {
        (6, 17): _gold(10, 0x07),  # (8, 5): 10-17 gold
        (7, 17): {'item': 'Herb'},  # (8, 6)
        (6, 18): {'item': 'Torch'},  # (9, 5)
    },
    # MAP_DLCSTL_BF (the Dragonlord's floor): row = y + 4, column = x + 6
    'CharlockB8': {
        (15, 17): {'item': 'Herb'},  # (11, 11)
        (16, 17): _gold(500, 0xFF),  # (11, 12): 500-755 gold
        (17, 17): {'item': 'Wings'},  # (11, 13)
        (16, 18): {'item': 'Magic Key'},  # (12, 12)
        (17, 18): {'item': 'Cursed Belt'},  # (12, 13)
        (17, 19): {'item': 'Herb'},  # (13, 13)
    },
    # MAP_TANTCSTL_SL: row = y + 1, column = x + 1
    'TantegelCellar': {
        # The cellar's stairs are in the far south-east corner of the castle grounds (TantGFDat 29,29), and the only way
        # there is through the locked door at 18,6 (courtyard (13, 25)), so a Magic Key is needed.
        (6, 5): {'item': 'Stones of Sunlight'},  # (4, 5)
    },
    # MAP_RAIN: row = y + 2, column = x + 2
    'StaffOfRainCave': {
        # The old man (RainStaffDialog) blocks the only way in until he is given the Silver Harp.
        (6, 5): {'item': 'Staff of Rain'},  # (3, 4)
    },
    # MAP_CVGAR_B1: row = y + 1, column = x + 1
    'GarinsGraveB1': {
        (1, 12): {'item': 'Herb'},  # (11, 0)
        (1, 13): _gold(5, 0x0F),  # (12, 0): 5-20 gold
        (1, 14): _gold(6, 0x07),  # (13, 0): 6-13 gold
    },
    # MAP_CVGAR_B3: row = y + 1, column = x + 1
    'GarinsGraveB3': {
        (2, 2): {'item': 'Cursed Belt'},  # (1, 1)
        (7, 14): {'item': 'Silver Harp'},  # (13, 6)
    },
    # MAP_DLCSTL_SL2: row = y + 3, column = x + 3
    'CharlockB3': {
        (8, 8): {'item': "Erdrick's Sword"},  # (5, 5)
    },
    # MAP_RCKMTN_B2: row = y + 1, column = x + 1
    'MountainCaveB2': {
        (7, 2): {'item': 'Death Necklace'},  # (1, 6): the Death Necklace 1 time in 32, otherwise 100-131 gold
        (3, 4): {'item': 'Torch'},  # (3, 2)
        (3, 3): {'item': "Fighter's Ring"},  # (2, 2)
        (10, 11): _gold(10, 0x07),  # (10, 9): 10-17 gold
    },
    # MAP_RCKMTN_B1: row = y + 1, column = x + 1
    'MountainCaveB1': {
        (6, 14): {'item': 'Herb'},  # (13, 5)
    },
    # MAP_ERDRCK_B2: row = y + 1, column = x + 1
    'ErdricksCaveB2': {
        (4, 10): {'item': 'Tablet'},  # (9, 3)
    },
}

# NES GetDthNeckGold: once the Death Necklace has been found (or the 1-in-32 roll fails), its chest holds this instead
DEATH_NECKLACE_GOLD = (100, 0x1F)

# NES InitMapData: once the hero has left the throne room, its three chests are written into history slots 5-7
# every time the throne room is entered, so they never come back.
THRONE_ROOM_CHEST_SLOTS = {5: (7, 16), 6: (10, 15), 7: (10, 14)}


def roll_treasure_gold(gold: tuple[int, int]) -> int:
    """NES GetTrsrGold: base gold plus a random byte masked with the chest's random bits."""
    base, random_bits = gold
    return base + (random.randint(0, 255) & random_bits)


class TreasureChestHistory:
    """Which chests have been opened: the one place this game keeps that state.

    NES TrsrXPos/TrsrYPos: 8 slots holding the position of each chest taken since the hero was last on the
    overworld. GetBlockID reads a chest in this list as plain brick, InitMapData clears the list when the overworld
    is entered (so chests refill), and GetTreasure doesn't record a chest at all when all 8 slots are in use.
    The NES keeps only (x, y), not the map; no two chests share a position on maps reachable from each other
    without going outside, so keeping the map name here behaves the same.
    Like the NES, the history isn't saved: MainGameEngine clears it whenever a game is started or continued.
    """

    def __init__(self):
        self.slots: list[tuple[str, Cell] | None] = [None] * 8

    def is_opened(self, map_name: str, coordinates: Cell) -> bool:
        return (map_name, tuple(coordinates)) in self.slots

    def record(self, map_name: str, coordinates: Cell) -> bool:
        """NES GetTreasure: store the chest in the first free slot. Returns False when every slot is taken."""
        for index, slot in enumerate(self.slots):
            if slot is None:
                row, column = coordinates
                self.slots[index] = (map_name, (row, column))
                return True
        return False

    def enter_map(self, map_name: str, left_throne_room: bool) -> None:
        """NES InitMapData, run whenever a map is loaded. left_throne_room is the F_LEFT_THROOM story flag: once the
        hero has been beyond the throne room, its chests are always shown as opened."""
        if map_name == 'Alefgard':
            self.slots = [None] * 8
        if left_throne_room and map_name == 'TantegelThroneRoom':
            for index, coordinates in THRONE_ROOM_CHEST_SLOTS.items():
                self.slots[index] = ('TantegelThroneRoom', coordinates)

    def apply_to_layout(self, map_name: str, layout: list[list[int]], chest_value: int, opened_value: int) -> None:
        """Show each of the map's chests as closed or opened, according to the history."""
        for (row, column) in treasure.get(map_name, {}):
            layout[row][column] = opened_value if self.is_opened(map_name, (row, column)) else chest_value


# NES InitMapData (ChkLeftThRoom): once F_LEFT_THROOM is set, the throne room door is written into door history
# slot 7 (DoorXPos+14 = 4, DoorYPos+14 = 7) every time the throne room is entered, so it never locks again.
THRONE_ROOM_DOOR_SLOT = 7


class OpenDoorHistory:
    """Which locked doors are open: the one place this game keeps that state.

    NES DoorXPos/DoorYPos: 8 slots holding the position of each door opened since the hero was last on the
    overworld. GetBlockID (ChkDoorBlock, Bank00 LAD45) reads a door in this list as plain brick, InitMapData
    (ChkOverworldMap/ClrOpenDoorsLoop, LAF2B-LAF3A) clears the list when the overworld is entered, so doors lock
    again and every visit costs another key, and UseKey (DoorCheckLoop, Bank03 LDCA8-LDCB7) takes the key but
    doesn't open the door when all 8 slots are in use.
    As with TreasureChestHistory, the map name is kept with the position, which behaves the same as the NES (x, y),
    and the history isn't saved: MainGameEngine (LCA0F-LCA18) clears it whenever a game is started or continued.
    """

    def __init__(self):
        self.slots: list[tuple[str, Cell] | None] = [None] * 8

    def is_opened(self, map_name: str, coordinates: Cell) -> bool:
        return (map_name, tuple(coordinates)) in self.slots

    def record(self, map_name: str, coordinates: Cell) -> bool:
        """NES UseKey: store the door in the first free slot. Returns False when every slot is taken."""
        for index, slot in enumerate(self.slots):
            if slot is None:
                row, column = coordinates
                self.slots[index] = (map_name, (row, column))
                return True
        return False

    def enter_map(self, map_name: str, left_throne_room: bool, throne_room_door: Cell) -> None:
        """NES InitMapData, run whenever a map is loaded. left_throne_room is the F_LEFT_THROOM story flag: once the
        hero has been beyond the throne room, its door is always shown as opened."""
        if map_name == 'Alefgard':
            self.slots = [None] * 8
        if left_throne_room and map_name == 'TantegelThroneRoom':
            row, column = throne_room_door
            self.slots[THRONE_ROOM_DOOR_SLOT] = ('TantegelThroneRoom', (row, column))

    def apply_to_layout(self, map_name: str, layout: list[list[int]], doors: Iterable[Cell], door_value: int,
                        opened_value: int) -> None:
        """Show each of the map's doors (doors: where the map's own layout has one) as locked or opened, according
        to the history."""
        for (row, column) in doors:
            layout[row][column] = opened_value if self.is_opened(map_name, (row, column)) else door_value


# NES DoSearch: the hidden items found with SEARCH, by map and then (row, column) in this codebase's coordinates.
# Nothing here is tracked with a "found" flag: like the NES, an item is found again only if the player doesn't
# already have it (Erdrick's Token, Fairy Flute) or isn't wearing it (Erdrick's Armor), so the inventory and
# equipment (already saved) are the only state.
hidden_items: dict[str, dict[Cell, str]] = {
    'Alefgard': {(120, 91): "Erdrick's Token"},  # NES overworld (X 83, Y 113)
    'Kol': {(14, 19): 'Fairy Flute'},  # NES Kol (X 9, Y 6)
    # Stepping onto this tile starts the fixed Axe Knight fight first (NES CheckAxeKnight, see src/guardians.py)
    'Hauksness': {(20, 27): "Erdrick's Armor"},  # NES Hauksness (X 18, Y 12)
}
