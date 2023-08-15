class Enemy:
    def __init__(self, hp, attack, defense, speed, xp, gold, spells):
        self.max_hp = hp
        self.hp = hp
        self.attack = attack
        self.defense = defense
        self.speed = speed
        self.xp = xp
        self.gold = gold
        self.spells = spells
        self.name = ''
        self.is_asleep = False
        self.pattern = self.set_pattern()

    def get_current_hp(self):
        return self.hp

    def set_pattern(self):
        return []

    def refresh_pattern(self):
        self.pattern = self.set_pattern()


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

    def set_pattern(self):
        return [(75, "HURT"), "ATTACK"]


class Drakee(Enemy):

    def __init__(self):
        super().__init__(hp=6, attack=9, defense=6, speed=15, xp=2, gold=2, spells=None)
        self.name = "Drakee"


class Magidrakee(Enemy):

    def __init__(self):
        super().__init__(hp=15, attack=14, defense=14, speed=0, xp=5, gold=12, spells=["HURT"])
        self.name = "Magidrakee"
        self.pattern = [(50, "HURT", True), "ATTACK"]


class Drakeema(Enemy):

    def __init__(self):
        super().__init__(hp=20, attack=22, defense=26, speed=32, xp=11, gold=20, spells=["HEAL", "HURT"])
        self.name = "Drakeema"
        self.pattern = self.set_pattern()

    def set_pattern(self):
        return [(25, "HEAL", self.get_current_hp() < self.max_hp / 4), (50, "HURT", True), "ATTACK"]


class Ghost(Enemy):

    def __init__(self):
        super().__init__(hp=7, attack=11, defense=8, speed=15, xp=3, gold=4, spells=None)
        self.name = "Ghost"


class Poltergeist(Enemy):

    def __init__(self):
        super().__init__(hp=23, attack=18, defense=20, speed=0, xp=7, gold=18, spells=("HURT",))
        self.name = "Poltergeist"
        self.pattern = [(75, "HURT"), "ATTACK"]


class Specter(Enemy):

    def __init__(self):
        super().__init__(hp=36, attack=40, defense=38, speed=None, xp=18, gold=70, spells=("HURT", "SLEEP"))
        self.name = "Specter"

    def set_pattern(self):
        return [(25, "SLEEP"), (75, "HURT"), "ATTACK"]


class Magician(Enemy):

    def __init__(self):
        super().__init__(hp=12, attack=11, defense=12, speed=0, xp=4, gold=12, spells=("HURT",))
        self.name = "Magician"
        self.pattern = self.set_pattern()

    def set_pattern(self):
        return [(50, "HURT", True), "ATTACK"]


class Warlock(Enemy):

    def __init__(self):
        super().__init__(hp=30, attack=28, defense=22, speed=49, xp=14, gold=35, spells=("HURT", "SLEEP"))
        self.name = "Warlock"

    def set_pattern(self):
        return [(25, "SLEEP", True), (50, "HURT", True), "ATTACK"]


class Wizard(Enemy):

    def __init__(self):
        super().__init__(hp=65, attack=80, defense=70, speed=247, xp=50, gold=65, spells=("HURTMORE", "SLEEP"))
        self.name = "Wizard"

    def set_pattern(self):
        return [(50, "HURTMORE", True), "ATTACK"]


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

    def set_pattern(self):
        return [(75, "HEAL", self.get_current_hp() < self.max_hp / 4), (25, "HURT", True), "ATTACK"]


class Droll(Enemy):

    def __init__(self):
        super().__init__(hp=25, attack=24, defense=24, speed=14, xp=10, gold=25, spells=None)
        self.name = "Droll"


class Drollmagi(Enemy):

    def __init__(self):
        super().__init__(hp=38, attack=52, defense=50, speed=34, xp=22, gold=90, spells=("HEAL", "HURT", "STOPSPELL"))
        self.name = "Drollmagi"

    def set_pattern(self):
        return [(50, "STOPSPELL", True), "ATTACK"]


class Skeleton(Enemy):

    def __init__(self):
        super().__init__(hp=30, attack=28, defense=22, speed=15, xp=11, gold=30, spells=None)
        self.name = "Skeleton"


class Wraith(Enemy):

    def __init__(self):
        super().__init__(hp=36, attack=44, defense=34, speed=112, xp=17, gold=60, spells=("HEAL",))
        self.name = "Wraith"

    def set_pattern(self):
        return [(25, "HEAL", self.get_current_hp() < self.max_hp / 4), "ATTACK"]


class WraithKnight(Enemy):

    def __init__(self):
        super().__init__(hp=46, attack=68, defense=56, speed=80, xp=28, gold=120, spells=("HEAL",))
        self.name = "Wraith Knight"

    def set_pattern(self):
        return [(75, "HEAL", self.get_current_hp() < self.max_hp / 4), "ATTACK"]


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

    def set_pattern(self):
        return [(50, "STOPSPELL", True), "ATTACK"]


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

    def set_pattern(self):
        return [(50, "SLEEP", True), "ATTACK"]


class Starwyvern(Enemy):

    def __init__(self):
        super().__init__(hp=65, attack=86, defense=80, speed=128, xp=43, gold=160, spells=("HEALMORE", "FIREBREATH"))
        self.name = "Starwyvern"

    def set_pattern(self):
        return [(75, "HEALMORE", self.get_current_hp() < self.max_hp / 4), "FIREBREATH", "ATTACK"]


class Knight(Enemy):

    def __init__(self):
        super().__init__(hp=55, attack=76, defense=78, speed=103, xp=33, gold=150, spells=("STOPSPELL",))
        self.name = "Knight"

    def set_pattern(self):
        return [(50, "STOPSPELL", True), "ATTACK"]


class AxeKnight(Enemy):

    def __init__(self):
        super().__init__(hp=70, attack=94, defense=82, speed=243, xp=54, gold=165, spells=("SLEEP", "STOPSPELL",))
        self.name = "Axe Knight"

    def set_pattern(self):
        return [(25, "SLEEP", True), "ATTACK"]


class ArmoredKnight(Enemy):

    def __init__(self):
        super().__init__(hp=90, attack=105, defense=86, speed=147, xp=70, gold=140, spells=("HEALMORE", "HURTMORE"))
        self.name = "Armored Knight"

    def set_pattern(self):
        return [(75, "HEALMORE", self.get_current_hp() < self.max_hp / 4), (25, "HURTMORE", True), "ATTACK"]


class GreenDragon(Enemy):

    def __init__(self):
        super().__init__(hp=65, attack=88, defense=74, speed=127, xp=45, gold=110, spells=("FIREBREATH",))
        self.name = "Green Dragon"

    def set_pattern(self):
        return [(25, "FIREBREATH", True), "ATTACK"]


class BlueDragon(Enemy):

    def __init__(self):
        super().__init__(hp=70, attack=98, defense=84, speed=255, xp=60, gold=150, spells=("FIREBREATH",))
        self.name = "Blue Dragon"

    def set_pattern(self):
        return [(25, "FIREBREATH", True), "ATTACK"]


class RedDragon(Enemy):

    def __init__(self):
        super().__init__(hp=100, attack=120, defense=90, speed=247, xp=100, gold=140, spells=("SLEEP", "FIREBREATH"))
        self.name = "Red Dragon"

    def set_pattern(self):
        return [(25, "SLEEP", True), (25, "FIREBREATH", True), "ATTACK"]


class Dragonlord(Enemy):

    def __init__(self):
        super().__init__(hp=100, attack=90, defense=75, speed=55, xp=0, gold=0, spells=("STOPSPELL", "HURTMORE"))
        self.name = "Dragonlord"

    def set_pattern(self):
        return [(25, "STOPSPELL", True), (75, "HURTMORE", True), "ATTACK"]


class Dragonlord2(Enemy):

    def __init__(self):
        super().__init__(hp=130, attack=140, defense=200, speed=90, xp=0, gold=0, spells=("FIREBREATH2",))
        self.name = "Dragonlord 2"

    def set_pattern(self):
        return [(50, "FIREBREATH2", True), "ATTACK"]


# Group 1: #00 (Slime) - #19 (Druinlord)
# Group 2: #20 (Drollmagi) - #29 (Werewolf)
# Group 3: #30 (Green Dragon) - #34 (Blue Dragon)
# Group 4: #35 (Stoneman) - #39 (Dragonlord second form)

enemy_groups = {
    1: ["Slime", "Red Slime", "Drakee", "Ghost", "Magician", "Magidrakee", "Scorpion", "Druin", "Poltergeist", "Droll",
        "Drakeema", "Skeleton",
        "Warlock", "Metal Scorpion", "Wolf", "Wraith", "MetalSlime", "Specter", "Wolflord", "Druinlord"],
    2: ["Drollmagi", "Wyvern", "Rogue Scorpion", "Wraith Knight", "Golem", "Goldman", "Knight", "Magiwyvern",
        "Demon Knight", "Werewolf"],
    3: ["Green Dragon", "Starwyvern", "Wizard", "Axe Knight", "Blue Dragon"],
    4: ["Stoneman", "Armored Knight", "Red Dragon", "Dragonlord", "Dragonlord2"]
}
