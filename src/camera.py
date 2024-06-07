class Camera:
    def __init__(self, hero_position, current_map, screen, tile_size):
        self.x = None
        self.y = None
        self.current_map = current_map
        self.screen = screen
        self.set_camera_position(hero_position, tile_size)

    @property
    def pos(self):
        return self.x, self.y

    @pos.setter
    def pos(self, coord):
        self.x, self.y = coord

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

    # TODO: Migrate game move method here.
