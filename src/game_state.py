from typing import Optional


class GameState:
    def __init__(self, config):
        self.enable_movement = True
        self.enable_animate = True
        self.enable_roaming = True
        self.is_initial_dialog = True
        self.is_post_death_dialog = False
        self.automatic_initial_dialog_run = False
        self.radiant_start: Optional[int] = None
        self.tiles_moved_total = 0
        self.radiant_active = False
        self.config = config
        self.game_loaded_from_save = False
        self.music_enabled = config["MUSIC_ENABLED"]

    def unpause_all_movement(self) -> None:
        """
        Unpause movement of animation, roaming, and character.
        :return: None
        """
        self.enable_animate, self.enable_roaming, self.enable_movement = True, True, True

    def pause_all_movement(self) -> None:
        """
        Pause movement of animation, roaming, and character.
        :return: None
        """
        self.enable_animate, self.enable_roaming, self.enable_movement = False, False, False
