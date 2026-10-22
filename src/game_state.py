from typing import List

# NES LightDiameter ($D0) is the width, in blocks, of the lit square around the hero in a dungeon. The visible-area
# checks in Bank00 (ChkLightDiameterX/ChkLightDiameterY) black out every block further than LightDiameter tiles from
# the screen center, so a diameter of 1, 3, 5 or 7 lights a 1x1, 3x3, 5x5 or 7x7 square of blocks.
MIN_LIGHT_DIAMETER = 1  # InitMapData
TORCH_LIGHT_DIAMETER = 3  # UseTorch
RADIANT_MAX_LIGHT_DIAMETER = 7  # LightIncreaseLoop
LIGHT_DIAMETER_STEP = 2  # LightIncreaseLoop grows, and GameEngineLoop shrinks, the light by 2 blocks at a time
# NES RadiantTimer ($DA), counted in steps: RADIANT sets it to $50, then each time it runs out while the light is still
# larger than the minimum, GameEngineLoop reloads it with $3C and shrinks the light.
RADIANT_TIMER_START = 0x50
RADIANT_TIMER_RELOAD = 0x3C
# Each light change is shown by a PostMoveUpdate, which redraws the 7 block rows around the hero one per frame
# (TickColLoop waits for an NMI before each row) and then waits for one more NMI before returning.
LIGHT_REDRAW_FRAMES = 8


class GameState:
    def __init__(self, config):
        self.enable_movement = True
        self.enable_animate = True
        self.enable_roaming = True
        self.is_initial_dialog = True
        self.is_post_death_dialog = False
        self.automatic_initial_dialog_run = False
        self.tiles_moved_total = 0
        # NES LightDiameter and RadiantTimer (see the constants above)
        self.light_diameter = MIN_LIGHT_DIAMETER
        self.radiant_timer = 0
        # The light that is on screen. The NES only redraws the dungeon when the hero moves (UpdtHorzDungeon,
        # UpdtVertDungeon) or a light is used (PostMoveUpdate), so a light that GameEngineLoop shrinks after a step
        # isn't seen until the next step.
        self.lit_diameter = MIN_LIGHT_DIAMETER
        # Light diameters still to be drawn by PostMoveUpdate after RADIANT or a torch, one per LIGHT_REDRAW_FRAMES
        self.pending_light_redraws: List[int] = []
        self.light_redraw_frame = 0
        self.config = config
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

    def reset_light(self) -> None:
        """NES InitMapData: entering a map that isn't a dungeon puts out the light and clears the radiant timer, so a
        light lasts from one dungeon floor to the next but not out of the dungeon."""
        self.light_diameter = self.lit_diameter = MIN_LIGHT_DIAMETER
        self.radiant_timer = 0
        self.pending_light_redraws = []
        self.light_redraw_frame = 0

    def cast_radiant(self) -> None:
        """NES DoSpell, SPL_RADIANT branch (Bank03): set the radiant timer to $50 steps, then LightIncreaseLoop grows
        the light by 2 blocks at a time up to 7, playing SFX_RADIANT and redrawing the screen (PostMoveUpdate) for
        each step. A light that is already at 7 only has its timer restarted, with no sound."""
        self.radiant_timer = RADIANT_TIMER_START
        while self.light_diameter != RADIANT_MAX_LIGHT_DIAMETER:
            self.light_diameter += LIGHT_DIAMETER_STEP
            self._queue_light_redraw()

    def use_torch(self) -> None:
        """NES UseTorch (ChkTorch, Bank03): clear any radiant time left, set the light to 3 blocks (growing or
        shrinking it), play SFX_RADIANT once and redraw the screen. With no timer, the torch's light lasts until the
        hero leaves the dungeon."""
        self.radiant_timer = 0
        self.light_diameter = TORCH_LIGHT_DIAMETER
        self.pending_light_redraws = []
        self._queue_light_redraw()

    def _queue_light_redraw(self) -> None:
        if not self.pending_light_redraws:
            self.light_redraw_frame = 0
        self.pending_light_redraws.append(self.light_diameter)

    def tick_radiant_timer(self) -> None:
        """NES GameEngineLoop (Bank03), run after every step: count the radiant timer down. When it runs out and the
        light is larger than the minimum, reload it with $3C and shrink the light by 2 blocks, so RADIANT's light is 7
        blocks wide for 80 steps, 5 for 60, 3 for 60 and then back to 1."""
        if not self.radiant_timer:
            return
        self.radiant_timer -= 1
        if self.radiant_timer or self.light_diameter == MIN_LIGHT_DIAMETER:
            return
        self.radiant_timer = RADIANT_TIMER_RELOAD
        self.light_diameter -= LIGHT_DIAMETER_STEP

    def update_lit_diameter(self, hero_is_stepping: bool) -> bool:
        """Advance what is on screen by one frame. A light redraw from RADIANT or a torch plays SFX_RADIANT on its
        first frame and shows its light LIGHT_REDRAW_FRAMES frames later; otherwise a step redraws the screen with
        the current light. Returns True when SFX_RADIANT should play."""
        if not self.pending_light_redraws:
            if hero_is_stepping:
                self.lit_diameter = self.light_diameter
            return False
        play_sound = self.light_redraw_frame == 0
        self.light_redraw_frame += 1
        if self.light_redraw_frame == LIGHT_REDRAW_FRAMES:
            self.lit_diameter = self.pending_light_redraws.pop(0)
            self.light_redraw_frame = 0
        return play_sound
