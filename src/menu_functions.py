def get_opposite_direction(direction: int) -> int:
    if direction >= 2:
        return direction - 2
    else:
        return direction + 2
