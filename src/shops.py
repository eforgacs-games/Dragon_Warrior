from src.config import dev_config
from src.directories import Directories


class ShopInventories:
    def __init__(self, config):
        self.config = config
        self.directories = Directories(config=dev_config)

        self.brecconary_weapons_store_inventory = {
            "Bamboo Pole": {'cost': 10, 'type': 'weapon', 'menu_image': self.directories.BRECCONARY_WEAPONS_SHOP_BAMBOO_POLE_PATH},
            "Club": {'cost': 60, 'type': 'weapon', 'menu_image': self.directories.BRECCONARY_WEAPONS_SHOP_CLUB_PATH},
            "Copper Sword": {'cost': 180, 'type': 'weapon', 'menu_image': self.directories.BRECCONARY_WEAPONS_SHOP_COPPER_SWORD_PATH},
            "Clothes": {'cost': 20, 'type': 'armor', 'menu_image': self.directories.BRECCONARY_WEAPONS_SHOP_CLOTHES_PATH},
            "Leather Armor": {'cost': 70, 'type': 'armor', 'menu_image': self.directories.BRECCONARY_WEAPONS_SHOP_LEATHER_ARMOR_PATH},
            "Small Shield": {'cost': 90, 'type': 'shield', 'menu_image': self.directories.BRECCONARY_WEAPONS_SHOP_SMALL_SHIELD_PATH}
        }

        self.rimuldar_weapons_store_inventory = {
            # TODO: Fix menu_images to match the town they're in
            "Copper Sword": {'cost': 180, 'type': 'weapon', 'menu_image': self.directories.BRECCONARY_WEAPONS_SHOP_COPPER_SWORD_PATH},
            "Hand Axe": {'cost': 560, 'type': 'weapon', 'menu_image': self.directories.BRECCONARY_WEAPONS_SHOP_BAMBOO_POLE_PATH},
            "Broad Sword": {'cost': 1500, 'type': 'weapon', 'menu_image': self.directories.BRECCONARY_WEAPONS_SHOP_CLUB_PATH},
            "Half Plate": {'cost': 1000, 'type': 'armor', 'menu_image': self.directories.BRECCONARY_WEAPONS_SHOP_CLOTHES_PATH},
            "Full Plate": {'cost': 3000, 'type': 'armor', 'menu_image': self.directories.BRECCONARY_WEAPONS_SHOP_LEATHER_ARMOR_PATH},
            "Magic Armor": {'cost': 7700, 'type': 'shield', 'menu_image': self.directories.BRECCONARY_WEAPONS_SHOP_SMALL_SHIELD_PATH}
        }

        self.garinham_weapons_store_inventory = {
            "Club": {'cost': 60, 'type': 'weapon', 'menu_image': self.directories.GARINHAM_WEAPONS_SHOP_CLUB_PATH},
            "Copper Sword": {'cost': 180, 'type': 'weapon', 'menu_image': self.directories.GARINHAM_WEAPONS_SHOP_COPPER_SWORD_PATH},
            "Hand Axe": {'cost': 560, 'type': 'weapon', 'menu_image': self.directories.GARINHAM_WEAPONS_SHOP_HAND_AXE_PATH},
            "Leather Armor": {'cost': 70, 'type': 'armor', 'menu_image': self.directories.GARINHAM_WEAPONS_SHOP_LEATHER_ARMOR_PATH},
            "Chain Mail": {'cost': 300, 'type': 'armor', 'menu_image': self.directories.GARINHAM_WEAPONS_SHOP_CHAIN_MAIL_PATH},
            "Half Plate": {'cost': 1000, 'type': 'armor', 'menu_image': self.directories.GARINHAM_WEAPONS_SHOP_HALF_PLATE_PATH},
            "Large Shield": {'cost': 800, 'type': 'shield', 'menu_image': self.directories.GARINHAM_WEAPONS_SHOP_LARGE_SHIELD_PATH}
        }

        self.kol_weapons_store_inventory = {
            "Copper Sword": {'cost': 180, 'type': 'weapon', 'menu_image': self.directories.KOL_WEAPONS_SHOP_COPPER_SWORD_PATH},
            "Hand Axe": {'cost': 560, 'type': 'weapon', 'menu_image': self.directories.KOL_WEAPONS_SHOP_HAND_AXE_PATH},
            "Half Plate": {'cost': 1000, 'type': 'armor', 'menu_image': self.directories.KOL_WEAPONS_SHOP_HALF_PLATE_PATH},
            "Full Plate": {'cost': 3000, 'type': 'armor', 'menu_image': self.directories.KOL_WEAPONS_SHOP_FULL_PLATE_PATH},
            "Small Shield": {'cost': 90, 'type': 'shield', 'menu_image': self.directories.KOL_WEAPONS_SHOP_SMALL_SHIELD_PATH}
        }
