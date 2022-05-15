from src.sound import bump


def bump_and_reset(character, pre_bump_next_tile, pre_bump_next_next_tile):
    if character.next_tile_id != pre_bump_next_tile:
        character.next_tile_id = pre_bump_next_tile
    if character.next_next_tile_id != pre_bump_next_next_tile:
        character.next_next_tile_id = pre_bump_next_next_tile
    bump(character)
