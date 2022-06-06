weapons = {
    "Bamboo Pole": {'offense': 2, 'cost': 10, 'found': ("Brecconary", "Cantlin")},
    "Club": {'offense': 4, 'cost': 60, 'found': ("Brecconary", "Cantlin", "Garinham")},
    "Copper Sword": {'offense': 10, 'cost': 180, 'found': ("Brecconary", "Cantlin", "Garinham", "Kol", "Rimuldar")},
    "Hand Axe": {'offense': 15, 'cost': 560, 'found': ("Garinham", "Rimuldar")},
    "Broad Sword": {'offense': 20, 'cost': 1500, 'found': ("Rimuldar", "Cantlin")},
    "Flame Sword": {'offense': 28, 'cost': 9800, 'found': ("Cantlin",)},
    "Erdrick's Sword": {'offense': 40, 'cost': None, 'found': "Dragonlord's Castle"}
}

armor = {
    "Clothes": {'defense': 2, 'cost': 20, 'sold': ("Brecconary",)},
    "Leather Armor": {'defense': 4, 'cost': 70, 'sold': ("Brecconary", "Garinham")},
    "Chain Mail": {'defense': 10, 'cost': 300, 'sold': ("Garinham", "Cantlin")},
    "Half Plate": {'defense': 16, 'cost': 1000, 'sold': ("Garinham", "Kol", "Rimuldar", "Cantlin")},
    "Full Plate": {'defense': 24, 'cost': 3000, 'sold': ("Kol", "Rimuldar", "Cantlin")},
    "Magic Armor": {'defense': 24, 'cost': 7700, 'sold': ("Rimuldar", "Cantlin")},
    "Erdrick's Armor": {'defense': 28, 'cost': None, 'found': ("Hauksness",)}
    # restores a lost hit point for every step you take
    # and prevents damage from walking on damaging tiles.
    # This reduces damage from HURT AND HURTMORE by 1/3,
    # prevents Stopspell from working against you.
    # It also reduces damage from flame breath attacks by 1/3 as well.
}

treasure = {
    'TantegelThroneRoom': {(7, 17): {'item': 'Magic Key'},
                           (10, 14): {'item': "GOLD", 'amount': 120},
                           (10, 15): {'item': "Torch"}}
}
