from typing import Any

# The inventory limits (NES AddInvItem, ChkToolPurchase/ChkBuyKey) and the 65535 gold cap (GetSellGold) are
# shared with treasure chests
from src.items import INVENTORY_SLOTS, MAX_GOLD, UNSLOTTED_ITEMS, armor, shields, tools, weapons

# NES KeyCostTbl (Bank00)
KEY_COSTS = {'Cantlin': 98, 'Rimuldar': 53, 'TantegelCourtyard': 85}
# NES FairyDialog: LDA #$26
FAIRY_WATER_COST = 38


def inventory_slots_used(inventory: list[str]) -> int:
    return sum(1 for item in inventory if item not in UNSLOTTED_ITEMS)


def inventory_is_full(inventory: list[str], slots: int = INVENTORY_SLOTS) -> bool:
    """No slot free in a bag of this many slots (src/items.py bag_slots); a bag holding more than that, after BAG was
    set back to 8, is full too."""
    return inventory_slots_used(inventory) >= slots


def pay_player(gold: int, amount: int) -> int:
    return min(gold + amount, MAX_GOLD)


def sell_price(item: str) -> int:
    """NES DoToolSell (SellableTool): half of the ItemCostTbl price, rounded down (LSR/ROR). 0 means unsellable."""
    return tools[item]['cost'] // 2 if item in tools else 0


def buyback_price(equipped_item: str, item_type: str) -> int:
    """NES GetBuybackPrice: when buying equipment, the shop buys the equipped piece of that type for half its price."""
    table: dict[str, dict[str, Any]] = {'weapon': weapons, 'armor': armor, 'shield': shields}[item_type]
    if not equipped_item or equipped_item not in table:
        return 0
    return table[equipped_item]['cost'] // 2


class ShopInventories:
    def __init__(self, config):
        self.config = config

        self.brecconary_weapons_store_inventory = {
            "Bamboo Pole": {'cost': 10, 'type': 'weapon'},
            "Club": {'cost': 60, 'type': 'weapon'},
            "Copper Sword": {'cost': 180, 'type': 'weapon'},
            "Clothes": {'cost': 20, 'type': 'armor'},
            "Leather Armor": {'cost': 70, 'type': 'armor'},
            "Small Shield": {'cost': 90, 'type': 'shield'}
        }

        self.rimuldar_weapons_store_inventory = {
            "Copper Sword": {'cost': 180, 'type': 'weapon'},
            "Hand Axe": {'cost': 560, 'type': 'weapon'},
            "Broad Sword": {'cost': 1500, 'type': 'weapon'},
            "Half Plate": {'cost': 1000, 'type': 'armor'},
            "Full Plate": {'cost': 3000, 'type': 'armor'},
            "Magic Armor": {'cost': 7700, 'type': 'armor'}
        }

        self.garinham_weapons_store_inventory = {
            "Club": {'cost': 60, 'type': 'weapon'},
            "Copper Sword": {'cost': 180, 'type': 'weapon'},
            "Hand Axe": {'cost': 560, 'type': 'weapon'},
            "Leather Armor": {'cost': 70, 'type': 'armor'},
            "Chain Mail": {'cost': 300, 'type': 'armor'},
            "Half Plate": {'cost': 1000, 'type': 'armor'},
            "Large Shield": {'cost': 800, 'type': 'shield'}
        }

        self.kol_weapons_store_inventory = {
            "Copper Sword": {'cost': 180, 'type': 'weapon'},
            "Hand Axe": {'cost': 560, 'type': 'weapon'},
            "Half Plate": {'cost': 1000, 'type': 'armor'},
            "Full Plate": {'cost': 3000, 'type': 'armor'},
            "Small Shield": {'cost': 90, 'type': 'shield'}
        }

        self.cantlin_weapons_store_north_inventory = {
            "Bamboo Pole": {'cost': 10, 'type': 'weapon'},
            "Club": {'cost': 60, 'type': 'weapon'},
            "Copper Sword": {'cost': 180, 'type': 'weapon'},
            "Leather Armor": {'cost': 70, 'type': 'armor'},
            "Chain Mail": {'cost': 300, 'type': 'armor'},
            "Large Shield": {'cost': 800, 'type': 'shield'},
        }

        # NES ShopItemsTbl "Cantlin weapons and armor shop 3" (the guard behind the counter)
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
            "Hand Axe": {'cost': 560, 'type': 'weapon'},
            "Broad Sword": {'cost': 1500, 'type': 'weapon'},
            "Full Plate": {'cost': 3000, 'type': 'armor'},
            "Magic Armor": {'cost': 7700, 'type': 'armor'},
        }
