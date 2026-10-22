from src.directories import Directories
# The inventory limits (NES AddInvItem, ChkToolPurchase/ChkBuyKey) and the 65535 gold cap (GetSellGold) are
# shared with treasure chests
from src.items import INVENTORY_SLOTS, MAX_GOLD, UNSLOTTED_ITEMS, armor, shields, tools, weapons

# NES KeyCostTbl (Bank00)
KEY_COSTS = {'Cantlin': 98, 'Rimuldar': 53, 'TantegelCourtyard': 85}
# NES FairyDialog: LDA #$26
FAIRY_WATER_COST = 38


def inventory_slots_used(inventory: list[str]) -> int:
    return sum(1 for item in inventory if item not in UNSLOTTED_ITEMS)


def inventory_is_full(inventory: list[str]) -> bool:
    return inventory_slots_used(inventory) >= INVENTORY_SLOTS


def pay_player(gold: int, amount: int) -> int:
    return min(gold + amount, MAX_GOLD)


def sell_price(item: str) -> int:
    """NES DoToolSell (SellableTool): half of the ItemCostTbl price, rounded down (LSR/ROR). 0 means unsellable."""
    return tools[item]['cost'] // 2 if item in tools else 0


def buyback_price(equipped_item: str, item_type: str) -> int:
    """NES GetBuybackPrice: when buying equipment, the shop buys the equipped piece of that type for half its price."""
    table = {'weapon': weapons, 'armor': armor, 'shield': shields}[item_type]
    if not equipped_item or equipped_item not in table:
        return 0
    return table[equipped_item]['cost'] // 2


def sell_list(inventory: list[str]) -> list[str]:
    """NES CreateInvList: Herbs and Magic Keys first (one entry each), then each inventory slot in order."""
    return [item for item in UNSLOTTED_ITEMS if item in inventory] + \
        [item for item in inventory if item not in UNSLOTTED_ITEMS]


class ShopInventories:
    def __init__(self, config):
        self.config = config
        self.directories = Directories(config=config)

        self.brecconary_weapons_store_inventory = {
            "Bamboo Pole": {'cost': 10, 'type': 'weapon',
                            'menu_image': self.directories.BRECCONARY_WEAPONS_SHOP_BAMBOO_POLE_PATH},
            "Club": {'cost': 60, 'type': 'weapon', 'menu_image': self.directories.BRECCONARY_WEAPONS_SHOP_CLUB_PATH},
            "Copper Sword": {'cost': 180, 'type': 'weapon',
                             'menu_image': self.directories.BRECCONARY_WEAPONS_SHOP_COPPER_SWORD_PATH},
            "Clothes": {'cost': 20, 'type': 'armor', 'menu_image': self.directories.BRECCONARY_WEAPONS_SHOP_CLOTHES_PATH},
            "Leather Armor": {'cost': 70, 'type': 'armor',
                              'menu_image': self.directories.BRECCONARY_WEAPONS_SHOP_LEATHER_ARMOR_PATH},
            "Small Shield": {'cost': 90, 'type': 'shield',
                             'menu_image': self.directories.BRECCONARY_WEAPONS_SHOP_SMALL_SHIELD_PATH}
        }

        self.rimuldar_weapons_store_inventory = {
            "Copper Sword": {'cost': 180, 'type': 'weapon',
                             'menu_image': self.directories.RIMULDAR_WEAPONS_SHOP_COPPER_SWORD_PATH},
            "Hand Axe": {'cost': 560, 'type': 'weapon', 'menu_image': self.directories.RIMULDAR_WEAPONS_SHOP_HAND_AXE_PATH},
            "Broad Sword": {'cost': 1500, 'type': 'weapon',
                            'menu_image': self.directories.RIMULDAR_WEAPONS_SHOP_BROAD_SWORD_PATH},
            "Half Plate": {'cost': 1000, 'type': 'armor',
                           'menu_image': self.directories.RIMULDAR_WEAPONS_SHOP_HALF_PLATE_PATH},
            "Full Plate": {'cost': 3000, 'type': 'armor',
                           'menu_image': self.directories.RIMULDAR_WEAPONS_SHOP_FULL_PLATE_PATH},
            "Magic Armor": {'cost': 7700, 'type': 'armor',
                            'menu_image': self.directories.RIMULDAR_WEAPONS_SHOP_MAGIC_ARMOR_PATH}
        }

        self.garinham_weapons_store_inventory = {
            "Club": {'cost': 60, 'type': 'weapon', 'menu_image': self.directories.GARINHAM_WEAPONS_SHOP_CLUB_PATH},
            "Copper Sword": {'cost': 180, 'type': 'weapon',
                             'menu_image': self.directories.GARINHAM_WEAPONS_SHOP_COPPER_SWORD_PATH},
            "Hand Axe": {'cost': 560, 'type': 'weapon', 'menu_image': self.directories.GARINHAM_WEAPONS_SHOP_HAND_AXE_PATH},
            "Leather Armor": {'cost': 70, 'type': 'armor',
                              'menu_image': self.directories.GARINHAM_WEAPONS_SHOP_LEATHER_ARMOR_PATH},
            "Chain Mail": {'cost': 300, 'type': 'armor', 'menu_image': self.directories.GARINHAM_WEAPONS_SHOP_CHAIN_MAIL_PATH},
            "Half Plate": {'cost': 1000, 'type': 'armor',
                           'menu_image': self.directories.GARINHAM_WEAPONS_SHOP_HALF_PLATE_PATH},
            "Large Shield": {'cost': 800, 'type': 'shield',
                             'menu_image': self.directories.GARINHAM_WEAPONS_SHOP_LARGE_SHIELD_PATH}
        }

        self.kol_weapons_store_inventory = {
            "Copper Sword": {'cost': 180, 'type': 'weapon', 'menu_image': self.directories.KOL_WEAPONS_SHOP_COPPER_SWORD_PATH},
            "Hand Axe": {'cost': 560, 'type': 'weapon', 'menu_image': self.directories.KOL_WEAPONS_SHOP_HAND_AXE_PATH},
            "Half Plate": {'cost': 1000, 'type': 'armor', 'menu_image': self.directories.KOL_WEAPONS_SHOP_HALF_PLATE_PATH},
            "Full Plate": {'cost': 3000, 'type': 'armor', 'menu_image': self.directories.KOL_WEAPONS_SHOP_FULL_PLATE_PATH},
            "Small Shield": {'cost': 90, 'type': 'shield', 'menu_image': self.directories.KOL_WEAPONS_SHOP_SMALL_SHIELD_PATH}
        }

        self.cantlin_weapons_store_north_inventory = {
            "Bamboo Pole": {'cost': 10, 'type': 'weapon',
                            'menu_image': self.directories.CANTLIN_WEAPONS_SHOP_NORTH_BAMBOO_POLE_PATH},
            "Club": {'cost': 60, 'type': 'weapon', 'menu_image': self.directories.CANTLIN_WEAPONS_SHOP_NORTH_CLUB_PATH},
            "Copper Sword": {'cost': 180, 'type': 'weapon',
                             'menu_image': self.directories.CANTLIN_WEAPONS_SHOP_NORTH_COPPER_SWORD_PATH},
            "Leather Armor": {'cost': 70, 'type': 'armor',
                              'menu_image': self.directories.CANTLIN_WEAPONS_SHOP_NORTH_LEATHER_ARMOR_PATH},
            "Chain Mail": {'cost': 300, 'type': 'armor',
                           'menu_image': self.directories.CANTLIN_WEAPONS_SHOP_NORTH_CHAIN_MAIL_PATH},
            "Large Shield": {'cost': 800, 'type': 'shield',
                             'menu_image': self.directories.CANTLIN_WEAPONS_SHOP_NORTH_LARGE_SHIELD_PATH},
        }

        # NES ShopItemsTbl "Cantlin weapons and armor shop 3" (the guard behind the counter). There are no
        # pre-rendered menu images for this shop, so its window is drawn as text.
        self.cantlin_weapons_store_3_inventory = {
            "Flame Sword": {'cost': weapons['Flame Sword']['cost'], 'type': 'weapon'},
            "Silver Shield": {'cost': shields['Silver Shield']['cost'], 'type': 'shield'},
        }

        # NES ShopItemsTbl item shops (ToolsDialog), in table order
        herb = {'cost': tools['Herb']['cost'], 'type': 'tool'}
        torch = {'cost': tools['Torch']['cost'], 'type': 'tool'}
        dragons_scale = {'cost': tools["Dragon's Scale"]['cost'], 'type': 'tool'}
        wings = {'cost': tools['Wings']['cost'], 'type': 'tool'}
        self.kol_item_store_inventory = {"Herb": herb, "Torch": torch, "Dragon's Scale": dragons_scale,
                                         "Wings": wings}
        self.brecconary_item_store_inventory = {"Herb": herb, "Torch": torch, "Dragon's Scale": dragons_scale}
        self.garinham_item_store_inventory = {"Herb": herb, "Torch": torch, "Dragon's Scale": dragons_scale}
        self.cantlin_item_store_1_inventory = {"Herb": herb, "Torch": torch}
        self.cantlin_item_store_2_inventory = {"Dragon's Scale": dragons_scale, "Wings": wings}

        self.cantlin_weapons_store_south_inventory = {
            "Hand Axe": {'cost': 560, 'type': 'weapon',
                         'menu_image': self.directories.CANTLIN_WEAPONS_SHOP_SOUTH_HAND_AXE_PATH},
            "Broad Sword": {'cost': 1500, 'type': 'weapon',
                            'menu_image': self.directories.CANTLIN_WEAPONS_SHOP_SOUTH_BROAD_SWORD_PATH},
            "Full Plate": {'cost': 3000, 'type': 'armor',
                           'menu_image': self.directories.CANTLIN_WEAPONS_SHOP_SOUTH_FULL_PLATE_PATH},
            "Magic Armor": {'cost': 7700, 'type': 'armor',
                            'menu_image': self.directories.CANTLIN_WEAPONS_SHOP_SOUTH_MAGIC_ARMOR_PATH},
        }
