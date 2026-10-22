BLACK, WHITE, RED, ORANGE, PINK = (0, 0, 0), (255, 255, 255), (255, 0, 0), (234, 158, 34), (243, 106, 255)
# NES color $26 (NES_PALETTE[0x26] in visual_effects.py), which AddPalByte's ChkLowHPPal (Bank03) loads into background
# palette 0's color 1 ($3F01) while HP is low: the windows, their text and cursor, and the map's palette 0 tiles.
LOW_HP_RED = (252, 116, 96)


def is_low_hp(current_hp: int, max_hp: int) -> bool:
    """NES ChkLowHPPal (AddPalByte, Bank03) and ChkLowHP (MovementUpdates): HP is low when it is at most a quarter of
    the max HP (rounded down) plus 1: LDA DisplayedMaxHP / LSR / LSR / CLC / ADC #$01 / CMP HitPoints. (The
    disassembly's comments say 1/8, but the code shifts right twice.)"""
    return current_hp <= max_hp // 4 + 1


def window_color(current_hp: int, max_hp: int) -> tuple[int, int, int]:
    """The color of every window's border, text and cursor: background palette 0's color 1 ($3F01), which AddPalByte
    loads as red ($26) instead of white ($30) while HP is low."""
    return LOW_HP_RED if is_low_hp(current_hp, max_hp) else WHITE
