from enum import Enum


class Spell(str, Enum):
    """All spells in the game. Inherits str so values can be used as dict keys
    and in gettext calls without casting."""
    HEAL = "HEAL"
    HEALMORE = "HEALMORE"
    HURT = "HURT"
    HURTMORE = "HURTMORE"
    SLEEP = "SLEEP"
    RADIANT = "RADIANT"
    STOPSPELL = "STOPSPELL"
    OUTSIDE = "OUTSIDE"
    RETURN = "RETURN"
    REPEL = "REPEL"
    FIREBREATH = "FIREBREATH"
    FIREBREATH2 = "FIREBREATH2"
    ATTACK = "ATTACK"

    def __str__(self) -> str:
        # Python 3.11+ formats str-mixin enums as "Spell.HEAL"; spell names appear in dialog and menus
        return self.value
