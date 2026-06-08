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
