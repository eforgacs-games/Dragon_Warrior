from enum import IntEnum


class Direction(IntEnum):
    DOWN = 0
    LEFT = 1
    UP = 2
    RIGHT = 3


def nes_direction(nes_value: int) -> int:
    """The Direction of an NES direction (Dragon_Warrior_Defines DIR_UP $00, DIR_RIGHT $01, DIR_DOWN $02, DIR_LEFT
    $03): the NES goes round clockwise from up, this game from down."""
    return (nes_value + 2) % 4
