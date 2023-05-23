class Enemy:
    def __init__(self, hp, xp, gold):
        self.hp = hp
        self.xp = xp
        self.gold = gold
        self.name = ''


class Slime(Enemy):
    def __init__(self):
        super().__init__(hp=3, xp=1, gold=1)
        self.name = "Slime"


class RedSlime(Enemy):
    def __init__(self):
        super().__init__(hp=4, xp=1, gold=2)
        self.name = "Red Slime"


class MetalSlime(Enemy):

    def __init__(self):
        super().__init__(hp=4, xp=1, gold=3)
        self.name = "Metal Slime"


class Drakee(Enemy):

    def __init__(self):
        super().__init__(hp=4, xp=1, gold=3)
        self.name = "Drakee"


class Magidrakee(Enemy):

    def __init__(self):
        super().__init__(hp=15, xp=5, gold=12)
        self.name = "Magidrakee"


class Drakeema(Enemy):

    def __init__(self):
        super().__init__(hp=20, xp=11, gold=20)
        self.name = "Drakeema"


class Ghost(Enemy):

    def __init__(self):
        super().__init__(hp=7, xp=3, gold=5)
        self.name = "Ghost"


class Poltergeist(Enemy):

    def __init__(self):
        super().__init__(hp=23, xp=8, gold=18)
        self.name = "Poltergeist"


class Specter(Enemy):

    def __init__(self):
        super().__init__(hp=36, xp=18, gold=70)
        self.name = "Specter"


class Magician(Enemy):

    def __init__(self):
        super().__init__(hp=13, xp=4, gold=12)
        self.name = "Magician"


class Warlock(Enemy):

    def __init__(self):
        super().__init__(hp=30, xp=13, gold=35)
        self.name = "Warlock"


class Wizard(Enemy):

    def __init__(self):
        super().__init__(hp=65, xp=50, gold=165)
        self.name = "Wizard"


class Scorpion(Enemy):

    def __init__(self):
        super().__init__(hp=20, xp=6, gold=16)
        self.name = "Scorpion"


class MetalScorpion(Enemy):

    def __init__(self):
        super().__init__(hp=22, xp=14, gold=40)
        self.name = "Metal Scorpion"


class RogueScorpion(Enemy):

    def __init__(self):
        super().__init__(hp=50, xp=37, gold=150)
        self.name = "Rogue Scorpion"


class Druin(Enemy):

    def __init__(self):
        super().__init__(hp=22, xp=7, gold=16)
        self.name = "Druin"


class Druinlord(Enemy):

    def __init__(self):
        super().__init__(hp=35, xp=20, gold=85)
        self.name = "Druinlord"


class Droll(Enemy):

    def __init__(self):
        super().__init__(hp=25, xp=10, gold=25)
        self.name = "Droll"


class Drollmagi(Enemy):

    def __init__(self):
        super().__init__(hp=38, xp=22, gold=90)
        self.name = "Drollmagi"


class Skeleton(Enemy):

    def __init__(self):
        super().__init__(hp=30, xp=11, gold=30)
        self.name = "Skeleton"


class Wraith(Enemy):

    def __init__(self):
        super().__init__(hp=36, xp=17, gold=60)
        self.name = "Wraith"


class WraithKnight(Enemy):

    def __init__(self):
        super().__init__(hp=46, xp=28, gold=120)
        self.name = "Wraith Knight"


class DemonKnight(Enemy):

    def __init__(self):
        super().__init__(hp=50, xp=37, gold=150)
        self.name = "Demon Knight"


class Wolf(Enemy):

    def __init__(self):
        super().__init__(hp=34, xp=16, gold=50)
        self.name = "Wolf"


class Wolflord(Enemy):

    def __init__(self):
        super().__init__(hp=38, xp=20, gold=80)
        self.name = "Wolflord"


class Werewolf(Enemy):

    def __init__(self):
        super().__init__(hp=60, xp=40, gold=155)
        self.name = "Werewolf"


class Goldman(Enemy):

    def __init__(self):
        super().__init__(hp=50, xp=6, gold=200)
        self.name = "Goldman"


class Golem(Enemy):

    def __init__(self):
        super().__init__(hp=70, xp=5, gold=10)
        self.name = "Golem"


class Stoneman(Enemy):

    def __init__(self):
        super().__init__(hp=160, xp=65, gold=140)
        self.name = "Stoneman"


class Wyvern(Enemy):

    def __init__(self):
        super().__init__(hp=42, xp=24, gold=100)
        self.name = "Wyvern"


class Magiwyvern(Enemy):

    def __init__(self):
        super().__init__(hp=58, xp=34, gold=140)
        self.name = "Magiwyvern"


class Starwyvern(Enemy):

    def __init__(self):
        super().__init__(hp=65, xp=43, gold=160)
        self.name = "Starwyvern"


class Knight(Enemy):

    def __init__(self):
        super().__init__(hp=55, xp=33, gold=130)
        self.name = "Knight"


class AxeKnight(Enemy):

    def __init__(self):
        super().__init__(hp=70, xp=54, gold=165)
        self.name = "Axe Knight"


class ArmoredKnight(Enemy):

    def __init__(self):
        super().__init__(hp=90, xp=70, gold=140)
        self.name = "Armored Knight"


class GreenDragon(Enemy):

    def __init__(self):
        super().__init__(hp=65, xp=45, gold=160)
        self.name = "Green Dragon"


class BlueDragon(Enemy):

    def __init__(self):
        super().__init__(hp=70, xp=60, gold=150)
        self.name = "Blue Dragon"


class RedDragon(Enemy):

    def __init__(self):
        super().__init__(hp=100, xp=100, gold=140)
        self.name = "Red Dragon"


class Dragonlord(Enemy):

    def __init__(self):
        super().__init__(hp=100, xp=0, gold=0)
        self.name = "Dragonlord"


class Dragonlord2(Enemy):

    def __init__(self):
        super().__init__(hp=130, xp=0, gold=0)
        self.name = "Dragonlord 2"
