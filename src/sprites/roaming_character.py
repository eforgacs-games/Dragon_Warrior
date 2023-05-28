from src.config import dev_config
from src.sprites.animated_sprite import AnimatedSprite

# TODO: Replace with game config
config = dev_config


class RoamingCharacter(AnimatedSprite):
    def __init__(self, center_point, direction_value, images, identifier):
        super().__init__(center_point, direction_value, images, identifier)
        self.last_roaming_clock_check = None
        self.column = None
        self.row = None
        self.is_moving = False
        self.previous_previous_tile = None
        self.previous_tile = None
        self.current_tile = None
        self.next_tile_id = None
        self.next_tile_checked = False


def handle_roaming_character_sides_collision(current_map, roaming_character):
    """
    Handle collision with the sides of the map (for roaming characters).
    :return: None
    @param current_map: The current loaded map.
    @param roaming_character: Roaming character to check for sides collision.
    """
    max_x_bound, max_y_bound, min_bound = current_map.width - config['TILE_SIZE'], current_map.height - config['TILE_SIZE'], 0
    if roaming_character.rect.x < min_bound:  # Simple Sides Collision
        roaming_character.rect.x = min_bound  # Reset Player Rect Coord
    elif roaming_character.rect.x > max_x_bound:
        roaming_character.rect.x = max_x_bound
    if roaming_character.rect.y < min_bound:
        roaming_character.rect.y = min_bound
    elif roaming_character.rect.y > max_y_bound:
        roaming_character.rect.y = max_y_bound
