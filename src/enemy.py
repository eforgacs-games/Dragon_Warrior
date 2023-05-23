class Enemy:
    def __init__(self, hp, attack, defense, speed, xp, gold, spells):
        self.hp = hp
        self.attack = attack
        self.defense = defense
        self.speed = speed
        self.xp = xp
        self.gold = gold
        self.spells = spells
        self.name = ''


# stats from http://www.thealmightyguru.com/Reviews/DragonWarrior/DW-Enemies.html


class Slime(Enemy):
    def __init__(self):
        super().__init__(hp=3, attack=5, defense=3, speed=15, xp=1, gold=1, spells=None)
        self.name = "Slime"


class RedSlime(Enemy):
    def __init__(self):
        super().__init__(hp=4, attack=7, defense=3, speed=15, xp=1, gold=2, spells=None)
        self.name = "Red Slime"


class MetalSlime(Enemy):

    def __init__(self):
        super().__init__(hp=4, attack=10, defense=225, speed=255, xp=115, gold=6, spells=["HURT"])
        self.name = "Metal Slime"


class Drakee(Enemy):

    def __init__(self):
        super().__init__(hp=6, attack=9, defense=6, speed=15, xp=2, gold=2, spells=None)
        self.name = "Drakee"


class Magidrakee(Enemy):

    def __init__(self):
        super().__init__(hp=15, attack=14, defense=14, speed=0, xp=5, gold=12, spells=["HURT"])
        self.name = "Magidrakee"


class Drakeema(Enemy):

    def __init__(self):
        super().__init__(hp=20, attack=22, defense=26, speed=32, xp=11, gold=20, spells=["HEAL", "HURT"])
        self.name = "Drakeema"


class Ghost(Enemy):

    def __init__(self):
        super().__init__(hp=7, attack=11, defense=8, speed=15, xp=3, gold=4, spells=None)
        self.name = "Ghost"


class Poltergeist(Enemy):

    def __init__(self):
        super().__init__(hp=23, attack=18, defense=20, speed=0, xp=7, gold=18, spells=("HURT",))
        self.name = "Poltergeist"


class Specter(Enemy):

    def __init__(self):
        super().__init__(hp=36, attack=40, defense=38, speed=None, xp=18, gold=70, spells=("HURT", "SLEEP"))
        self.name = "Specter"


class Magician(Enemy):

    def __init__(self):
        super().__init__(hp=12, attack=11, defense=12, speed=0, xp=4, gold=12, spells=("HURT",))
        self.name = "Magician"


class Warlock(Enemy):

    def __init__(self):
        super().__init__(hp=30, attack=28, defense=22, speed=49, xp=14, gold=35, spells=("HURT", "SLEEP"))
        self.name = "Warlock"


class Wizard(Enemy):

    def __init__(self):
        super().__init__(hp=65, attack=80, defense=70, speed=247, xp=50, gold=65, spells=("HURTMORE", "SLEEP"))
        self.name = "Wizard"


class Scorpion(Enemy):

    def __init__(self):
        super().__init__(hp=20, attack=18, defense=16, speed=15, xp=6, gold=16, spells=None)
        self.name = "Scorpion"


class MetalScorpion(Enemy):

    def __init__(self):
        super().__init__(hp=22, attack=36, defense=42, speed=15, xp=14, gold=40, spells=None)
        self.name = "Metal Scorpion"


class RogueScorpion(Enemy):

    def __init__(self):
        super().__init__(hp=35, attack=60, defense=90, speed=127, xp=26, gold=110, spells=None)
        self.name = "Rogue Scorpion"


class Druin(Enemy):

    def __init__(self):
        super().__init__(hp=22, attack=22, defense=18, speed=15, xp=7, gold=16, spells=None)
        self.name = "Druin"


class Druinlord(Enemy):

    def __init__(self):
        super().__init__(hp=35, attack=47, defense=40, speed=240, xp=20, gold=85, spells=["HURT"])
        self.name = "Druinlord"


class Droll(Enemy):

    def __init__(self):
        super().__init__(hp=25, attack=24, defense=24, speed=14, xp=10, gold=25, spells=None)
        self.name = "Droll"


class Drollmagi(Enemy):

    def __init__(self):
        super().__init__(hp=38, attack=52, defense=50, speed=34, xp=22, gold=90, spells=("HEAL", "HURT", "STOPSPELL"))
        self.name = "Drollmagi"


class Skeleton(Enemy):

    def __init__(self):
        super().__init__(hp=30, attack=28, defense=22, speed=15, xp=11, gold=30, spells=None)
        self.name = "Skeleton"


class Wraith(Enemy):

    def __init__(self):
        super().__init__(hp=36, attack=44, defense=34, speed=112, xp=17, gold=60, spells=("HEAL",))
        self.name = "Wraith"


class WraithKnight(Enemy):

    def __init__(self):
        super().__init__(hp=46, attack=68, defense=56, speed=80, xp=28, gold=120, spells=("HEAL",))
        self.name = "Wraith Knight"


class DemonKnight(Enemy):

    def __init__(self):
        super().__init__(hp=50, attack=79, defense=64, speed=255, xp=37, gold=150, spells=("HURT", "SLEEP"))
        self.name = "Demon Knight"


class Wolf(Enemy):

    def __init__(self):
        super().__init__(hp=34, attack=40, defense=30, speed=31, xp=16, gold=45, spells=None)
        self.name = "Wolf"


class Wolflord(Enemy):

    def __init__(self):
        super().__init__(hp=38, attack=50, defense=36, speed=71, xp=20, gold=80, spells=("STOPSPELL",))
        self.name = "Wolflord"


class Werewolf(Enemy):

    def __init__(self):
        super().__init__(hp=60, attack=86, defense=70, speed=127, xp=40, gold=155, spells=None)
        self.name = "Werewolf"


class Goldman(Enemy):

    def __init__(self):
        super().__init__(hp=50, attack=48, defense=40, speed=223, xp=6, gold=200, spells=None)
        self.name = "Goldman"


class Golem(Enemy):

    def __init__(self):
        super().__init__(hp=70, attack=120, defense=60, speed=255, xp=5, gold=10, spells=None)
        self.name = "Golem"


class Stoneman(Enemy):

    def __init__(self):
        super().__init__(hp=160, attack=100, defense=40, speed=47, xp=65, gold=140, spells=None)
        self.name = "Stoneman"


class Wyvern(Enemy):

    def __init__(self):
        super().__init__(hp=42, attack=56, defense=48, speed=79, xp=24, gold=100, spells=None)
        self.name = "Wyvern"


class Magiwyvern(Enemy):

    def __init__(self):
        super().__init__(hp=58, attack=78, defense=68, speed=32, xp=34, gold=140, spells=("SLEEP", "FIREBREATH"))
        self.name = "Magiwyvern"


class Starwyvern(Enemy):

    def __init__(self):
        super().__init__(hp=65, attack=86, defense=80, speed=128, xp=43, gold=160, spells=("HEALMORE", "FIREBREATH"))
        self.name = "Starwyvern"


class Knight(Enemy):

    def __init__(self):
        super().__init__(hp=55, attack=76, defense=78, speed=103, xp=33, gold=150, spells=("STOPSPELL",))
        self.name = "Knight"


class AxeKnight(Enemy):

    def __init__(self):
        super().__init__(hp=70, attack=94, defense=82, speed=243, xp=54, gold=165, spells=("SLEEP", "STOPSPELL",))
        self.name = "Axe Knight"


class ArmoredKnight(Enemy):

    def __init__(self):
        super().__init__(hp=90, attack=105, defense=86, speed=147, xp=70, gold=140, spells=("HEALMORE", "HURTMORE"))
        self.name = "Armored Knight"


class GreenDragon(Enemy):

    def __init__(self):
        super().__init__(hp=65, attack=88, defense=74, speed=127, xp=45, gold=110, spells=("FIREBREATH",))
        self.name = "Green Dragon"


class BlueDragon(Enemy):

    def __init__(self):
        super().__init__(hp=70, attack=98, defense=84, speed=255, xp=60, gold=150, spells=("FIREBREATH",))
        self.name = "Blue Dragon"


class RedDragon(Enemy):

    def __init__(self):
        super().__init__(hp=100, attack=120, defense=90, speed=247, xp=100, gold=140, spells=("SLEEP", "FIREBREATH"))
        self.name = "Red Dragon"


class Dragonlord(Enemy):

    def __init__(self):
        super().__init__(hp=100, attack=90, defense=75, speed=55, xp=0, gold=0, spells=("STOPSPELL", "HURTMORE"))
        self.name = "Dragonlord"


class Dragonlord2(Enemy):

    def __init__(self):
        super().__init__(hp=130, attack=140, defense=200, speed=90, xp=0, gold=0, spells=("FIREBREATH",))
        self.name = "Dragonlord 2"
