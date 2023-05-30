class Camera:
    def __init__(self, hero_position, current_map, screen, tile_size):
        self.current_map = current_map
        self.x = None
        self.y = None
        self.screen = screen
        self.set_camera_position(hero_position, tile_size)

    def set_camera_position(self, hero_position: tuple, tile_size: int):
        """
        Sets the camera position.
        :type hero_position: tuple
        :param hero_position: Position of the hero, in (column, row) format.
        :type tile_size: int
        :param tile_size: Size of a tile, in pixels.
        """
        column, row = hero_position
        if self.screen:
            self.x = (-column + (self.screen.get_width() / tile_size / 2)) * tile_size
            self.y = (-row + (self.screen.get_height() / tile_size // 2)) * tile_size
        else:
            self.x = (-column + 8) * tile_size
            self.y = (-row + 7) * tile_size

    def get_pos(self) -> tuple:
        """
        Gets the position of a particular rectangle.
        """
        return self.x, self.y

    def set_pos(self, coord):
        """
        Sets the position of a particular rectangle.
        """
        self.x = coord[0]
        self.y = coord[1]
        # TODO: Investigate Python getters/setters (prop and props live templates?)

    # TODO: Migrate game move method here.
