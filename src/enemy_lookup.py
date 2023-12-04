# using the colors from https://gamefaqs.gamespot.com/nes/563408-dragon-warrior/map/5948-enemy-territory-map
from src.enemy import Slime, RedSlime, MetalSlime, Drakee, Magidrakee, Drakeema, Ghost, Poltergeist, Specter, Magician, \
    Warlock, Wizard, Scorpion, MetalScorpion, RogueScorpion, Druin, Druinlord, Droll, Drollmagi, Skeleton, Wraith, \
    WraithKnight, DemonKnight, Wolf, Wolflord, Werewolf, Goldman, Golem, Stoneman, Wyvern, Magiwyvern, Starwyvern, \
    Knight, AxeKnight, ArmoredKnight, GreenDragon, BlueDragon, RedDragon, Dragonlord, Dragonlord2

dark_brown = ('Red Slime', 'Drakee', 'Ghost', 'Magician')
dark_yellow = ('Ghost', 'Magician', 'Magidrakee', 'Scorpion')
light_yellow = ('Ghost', 'Magician', 'Magidrakee', 'Scorpion', 'Skeleton')
dark_turquoise = ('Wyvern', 'Rogue Scorpion', 'Wraith Knight', 'Knight', 'Demon Knight')
light_turquoise = ('Wraith Knight', 'Knight', 'Demon Knight', 'Metal Slime', 'Magiwyvern')
light_brown = ('Slime', 'Red Slime', 'Drakee', 'Ghost')
light_red = ('Slime', 'Red Slime', 'Drakee')
green = ('Skeleton', 'Warlock', 'Wolf', 'Metal Scorpion')
green_cyan = ('Wolflord', 'Wraith', 'Goldman', 'Wyvern')
dark_red = ('Slime', 'Red Slime')
light_jade_green = ('Metal Scorpion', 'Wolflord', 'Wraith', 'Goldman')
medium_blue = ('Knight', 'Demon Knight', 'Magiwyvern', 'Starwyvern', 'Werewolf')
dark_blue = ('Starwyvern', 'Werewolf', 'Wizard', 'Green Dragon')
grass_green = ('Magidrakee', 'Scorpion', 'Skeleton', 'Warlock', 'Wolf')
swamp_cave = ('Druin', 'Ghost', 'Magician', 'Scorpion')
garins_grave_b1 = ('Drakeema', 'Droll', 'Poltergeist', 'Skeleton', 'Warlock')
garins_grave_b2 = ('Metal Scorpion', 'Skeleton', 'Warlock', 'Wolf')
garins_grave_b3 = garins_grave_b4 = ('Drollmagi', 'Druinlord', 'Specter', 'Wolflord', 'Wraith Knight')

enemy_territory_map = {
    (0, 0): dark_brown,
    (0, 1): dark_brown,
    (0, 2): dark_yellow,
    (0, 3): light_yellow,
    (0, 4): light_yellow,
    (0, 5): dark_turquoise,
    (0, 6): dark_turquoise,
    (0, 7): light_turquoise,

    (1, 0): dark_brown,
    (1, 1): light_brown,
    (1, 2): light_red,
    (1, 3): light_red,
    (1, 4): light_yellow,
    (1, 5): green_cyan,
    (1, 6): dark_turquoise,
    (1, 7): light_turquoise,

    (2, 0): light_brown,
    (2, 1): light_red,
    (2, 2): dark_red,
    (2, 3): light_red,
    (2, 4): dark_yellow,
    (2, 5): light_jade_green,
    (2, 6): light_turquoise,
    (2, 7): medium_blue,

    (3, 0): light_brown,
    (3, 1): light_brown,
    (3, 2): dark_red,
    (3, 3): medium_blue,
    (3, 4): medium_blue,
    (3, 5): medium_blue,
    (3, 6): medium_blue,
    (3, 7): dark_blue,

    (4, 0): dark_brown,
    (4, 1): dark_brown,
    (4, 2): light_brown,
    (4, 3): grass_green,
    (4, 4): medium_blue,
    (4, 5): medium_blue,
    (4, 6): dark_blue,
    (4, 7): dark_blue,

    (5, 0): light_yellow,
    (5, 1): dark_brown,
    (5, 2): dark_brown,
    (5, 3): grass_green,
    (5, 4): green,
    (5, 5): medium_blue,
    (5, 6): dark_blue,
    (5, 7): medium_blue,

    (6, 0): dark_yellow,
    (6, 1): dark_yellow,
    (6, 2): dark_yellow,
    (6, 3): grass_green,
    (6, 4): green,
    (6, 5): light_jade_green,
    (6, 6): green_cyan,
    (6, 7): green_cyan,

    (7, 0): light_yellow,
    (7, 1): light_yellow,
    (7, 2): light_yellow,
    (7, 3): grass_green,
    (7, 4): green,
    (7, 5): green,
    (7, 6): light_jade_green,
    (7, 7): green_cyan,

    # special
    (-1, -1): swamp_cave,
    (-2, -2): garins_grave_b1,
    (-3, -3): garins_grave_b2,
    (-4, -4): garins_grave_b3,
    (-5, -5): garins_grave_b4,

}

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
