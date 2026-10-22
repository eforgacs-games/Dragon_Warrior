from src.enemy import Slime, RedSlime, MetalSlime, Drakee, Magidrakee, Drakeema, Ghost, Poltergeist, Specter, Magician, \
    Warlock, Wizard, Scorpion, MetalScorpion, RogueScorpion, Druin, Druinlord, Droll, Drollmagi, Skeleton, Wraith, \
    WraithKnight, DemonKnight, Wolf, Wolflord, Werewolf, Goldman, Golem, Stoneman, Wyvern, Magiwyvern, Starwyvern, \
    Knight, AxeKnight, ArmoredKnight, GreenDragon, BlueDragon, RedDragon, Dragonlord, Dragonlord2

enemy_string_lookup = {
    'Slime': Slime,
    'Red Slime': RedSlime,
    'Metal Slime': MetalSlime,
    'Drakee': Drakee,
    'Magidrakee': Magidrakee,
    'Drakeema': Drakeema,
    'Ghost': Ghost,
    'Poltergeist': Poltergeist,
    'Specter': Specter,
    'Magician': Magician,
    'Warlock': Warlock,
    'Wizard': Wizard,
    'Scorpion': Scorpion,
    'Metal Scorpion': MetalScorpion,
    'Rogue Scorpion': RogueScorpion,
    'Druin': Druin,
    'Druinlord': Druinlord,
    'Droll': Droll,
    'Drollmagi': Drollmagi,
    'Skeleton': Skeleton,
    'Wraith': Wraith,
    'Wraith Knight': WraithKnight,
    'Demon Knight': DemonKnight,
    'Wolf': Wolf,
    'Wolflord': Wolflord,
    'Werewolf': Werewolf,
    'Goldman': Goldman,
    'Golem': Golem,
    'Stoneman': Stoneman,
    'Wyvern': Wyvern,
    'Magiwyvern': Magiwyvern,
    'Starwyvern': Starwyvern,
    'Knight': Knight,
    'Axe Knight': AxeKnight,
    'Armored Knight': ArmoredKnight,
    'Green Dragon': GreenDragon,
    'Blue Dragon': BlueDragon,
    'Red Dragon': RedDragon,
    'Dragonlord': Dragonlord,
    'Dragonlord 2': Dragonlord2,
}

enemy_image_position_lookup = {
    'Slime': (8, 7),
    'Red Slime': (8, 7),
    'Metal Slime': (8, 7),

    'Drakee': (7.75, 6.25),
    'Magidrakee': (7.75, 6.25),
    'Drakeema': (7.75, 6.25),

    'Ghost': (7.8, 5.9),
    'Poltergeist': (7.8, 5.9),
    'Specter': (7.8, 5.9),

    'Magician': (7.3, 6),
    'Warlock': (7.3, 6),
    'Wizard': (7.3, 6),

    'Scorpion': (7.4, 6.5),
    'Metal Scorpion': (7.4, 6.5),
    'Rogue Scorpion': (7.4, 6.5),

    'Druin': (8, 6.5),
    'Druinlord': (8, 6.5),

    'Droll': (7.5, 6),
    'Drollmagi': (7.5, 6),

    'Skeleton': (7.46, 5.74),
    'Wraith': (7.46, 5.74),
    'Wraith Knight': (7.46, 5.74),
    'Demon Knight': (7.46, 5.74),

    'Wolf': (7.11, 5.95),
    'Wolflord': (7.11, 5.95),
    'Werewolf': (7.11, 5.95),

    'Goldman': (7.1, 5.6),
    'Golem': (7.1, 5.6),
    'Stoneman': (7.1, 5.6),

    'Wyvern': (7.25, 5.5),
    'Magiwyvern': (7.25, 5.5),
    'Starwyvern': (7.25, 5.5),

    'Knight': (7.1, 5.75),
    'Axe Knight': (7.1, 5.75),
    'Armored Knight': (7.1, 5.75),

    'Green Dragon': (6.5, 6.25),
    'Blue Dragon': (6.5, 6.25),
    'Red Dragon': (6.5, 6.25),

    'Dragonlord': (7.5, 6),
    'Dragonlord 2': (5.1, 4),

}


# NES RepelTbl (Bank03): an enemy is repelled when repel - player defense // 2 <= repel // 2
enemy_repel_lookup = {
    'Slime': 5,
    'Red Slime': 7,
    'Drakee': 9,
    'Ghost': 11,
    'Magician': 11,
    'Magidrakee': 14,
    'Scorpion': 18,
    'Druin': 20,
    'Poltergeist': 18,
    'Droll': 24,
    'Drakeema': 22,
    'Skeleton': 28,
    'Warlock': 28,
    'Metal Scorpion': 36,
    'Wolf': 40,
    'Wraith': 44,
    'Metal Slime': 10,
    'Specter': 40,
    'Wolflord': 50,
    'Druinlord': 47,
    'Drollmagi': 52,
    'Wyvern': 56,
    'Rogue Scorpion': 60,
    'Wraith Knight': 68,
    'Golem': 120,
    'Goldman': 48,
    'Knight': 76,
    'Magiwyvern': 78,
    'Demon Knight': 79,
    'Werewolf': 86,
    'Green Dragon': 88,
    'Starwyvern': 86,
    'Wizard': 80,
    'Axe Knight': 94,
    'Blue Dragon': 98,
    'Stoneman': 100,
    'Armored Knight': 105,
    'Red Dragon': 120,
    'Dragonlord': 90,
    'Dragonlord 2': 140,
}
