from enum import StrEnum


class Spell(StrEnum):
    """All spells in the game. A StrEnum, so values can be used as dict keys and in gettext calls without casting, and
    str()/format() give the plain name ("HEAL", not "Spell.HEAL") for dialog and menus."""
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
