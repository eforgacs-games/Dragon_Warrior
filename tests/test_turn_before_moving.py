"""Tapping a direction turns the hero without moving; holding it walks (issue #237).

NES CheckInputs (Bank03) points the hero in the held direction (STA CharDirection) on the frame it's read, but
DoJoyUp/DoJoyDown/DoJoyLeft/DoJoyRight (Bank00) only start a step when FrameCounter & $0F is 0. FrameCounter goes up
by one every frame the hero stands still (IdleUpdate -> WaitForNMI) and is reset to 0 after every step
(JoypadCheckLoop) and every bump (DirectionBlocked).

These run the real main-loop update (Game.get_events) a frame at a time in the throne room, where the hero starts at
(13, 10): King Lorik's table is above, two brick tiles then the wall are to the left, and GUARD_2 stands two tiles
below.
"""
from unittest.mock import patch

from pygame import K_DOWN, K_LEFT, K_UP, K_i

from src.config.test_config import test_config
from src.direction import Direction
from src.game import STEP_SYNC_FRAMES
from src.waiting import set_game_speed
from tests.test_freeze_movement import FreezeTestCase, keydown


class TestTurnBeforeMoving(FreezeTestCase):

    def setUp(self):
        super().setUp()
        # the roaming guard would otherwise wander about at random
        self.game.game_state.enable_roaming = False
        self.player = self.game.player
        self.play_sound = patch.object(self.game.movement.sound, 'play_sound').start()
        self.addCleanup(patch.stopall)
        self.assertEqual((13, 10), (self.player.column, self.player.row))
        self.assertEqual(0, self.game.movement.frame_counter)

    def hero_xy(self):
        return self.player.rect.x, self.player.rect.y

    def stand_still(self, frames):
        self.frames(frames)
        self.assertFalse(self.player.is_moving)

    def frames_until_moved(self, held, limit=STEP_SYNC_FRAMES * 3):
        """Hold a key until the hero moves. Returns the number of frames that took, counting the one it moved on."""
        before = self.hero_xy()
        for count in range(1, limit + 1):
            self.frame(held=held)
            if self.hero_xy() != before:
                return count
        self.fail(f"The hero didn't move in {limit} frames")

    # ------------------------------------------------------------------ #
    #  Turning                                                            #
    # ------------------------------------------------------------------ #

    def test_a_tap_only_turns_the_hero(self):
        self.stand_still(5)
        before = self.hero_xy()
        self.frame(held=(K_LEFT,))
        # turned on the very frame the press is read
        self.assertEqual(Direction.LEFT.value, self.player.direction_value)
        self.frames(3, held=(K_LEFT,))
        self.frames(STEP_SYNC_FRAMES * 3)
        self.assertEqual(before, self.hero_xy())
        self.assertEqual(Direction.LEFT.value, self.player.direction_value)
        self.assertFalse(self.player.is_moving)
        self.assertEqual(0, self.game.tiles_moved_since_spawn)

    def test_taps_in_each_direction_turn_the_hero_to_face_it(self):
        self.stand_still(1)
        before = self.hero_xy()
        for held, direction in ((K_LEFT, Direction.LEFT), (K_DOWN, Direction.DOWN), (K_UP, Direction.UP)):
            self.frame(held=(held,))
            self.assertEqual(direction.value, self.player.direction_value)
        self.assertEqual(before, self.hero_xy())

    def test_up_wins_when_two_directions_are_held(self):
        # NES CheckInputs checks up, down, left, right in that order
        self.stand_still(1)
        self.frame(held=(K_LEFT, K_UP))
        self.assertEqual(Direction.UP.value, self.player.direction_value)

    # ------------------------------------------------------------------ #
    #  When the first step starts                                         #
    # ------------------------------------------------------------------ #

    def test_holding_turns_then_steps_on_the_next_multiple_of_16_frames(self):
        self.stand_still(5)  # FrameCounter is now 5
        start_x, start_y = self.hero_xy()
        for _ in range(STEP_SYNC_FRAMES - 5):  # read with FrameCounter 5 to 15: turned, but no step yet
            self.frame(held=(K_LEFT,))
            self.assertEqual(Direction.LEFT.value, self.player.direction_value)
            self.assertEqual((start_x, start_y), self.hero_xy())
        self.frame(held=(K_LEFT,))  # FrameCounter 16
        self.assertTrue(self.player.is_moving)
        self.assertEqual((start_x - self.game.speed, start_y), self.hero_xy())

    def test_the_first_step_waits_0_to_15_frames(self):
        for idle_frames in range(STEP_SYNC_FRAMES * 2):
            with self.subTest(idle_frames=idle_frames):
                self.setUp()
                self.stand_still(idle_frames)
                expected = (STEP_SYNC_FRAMES - idle_frames % STEP_SYNC_FRAMES) % STEP_SYNC_FRAMES + 1
                self.assertEqual(expected, self.frames_until_moved((K_LEFT,)))

    def test_a_press_on_the_sync_frame_steps_at_once(self):
        self.stand_still(STEP_SYNC_FRAMES)
        self.assertEqual(1, self.frames_until_moved((K_LEFT,)))

    def test_the_pop_up_window_frame_skips_a_count(self):
        # NES IdleUpdate: on FrameCounter $31 it shows the pop-up window and sets FrameCounter to $32
        self.stand_still(60)
        self.assertEqual(61, self.game.movement.frame_counter)
        self.assertEqual(4, self.frames_until_moved((K_LEFT,)))  # 61, 62, 63, then 64

    def test_the_delay_is_counted_in_frames_at_any_game_speed(self):
        # The speed keys (src/waiting.py's game speed) run the main loop at 60, 120, 240 or 480 frames per second
        self.addCleanup(set_game_speed, 1)
        for speed in (1, 2, 4, 8):
            with self.subTest(speed=speed):
                self.setUp()
                set_game_speed(speed)
                self.assertEqual(60 * speed, self.game.fps)
                self.stand_still(5)
                self.assertEqual(STEP_SYNC_FRAMES - 5 + 1, self.frames_until_moved((K_LEFT,)))

    # ------------------------------------------------------------------ #
    #  Walking                                                            #
    # ------------------------------------------------------------------ #

    def test_holding_the_same_direction_walks_without_pausing(self):
        start_x, start_y = self.hero_xy()
        frames_per_step = self.tile_size // self.game.speed
        self.assertEqual(STEP_SYNC_FRAMES, frames_per_step)
        for frame in range(1, frames_per_step * 2 + 1):
            self.frame(held=(K_LEFT,))
            self.assertEqual((start_x - frame * self.game.speed, start_y), self.hero_xy())
        self.assertEqual(2, self.game.tiles_moved_since_spawn)

    def test_each_step_is_counted_on_the_frame_the_hero_arrives(self):
        frames_per_step = self.tile_size // self.game.speed
        self.frames(frames_per_step - 1, held=(K_LEFT,))
        self.assertEqual(0, self.game.tiles_moved_since_spawn)
        self.assertTrue(self.player.is_moving)
        self.frame(held=(K_LEFT,))
        self.assertEqual(1, self.game.tiles_moved_since_spawn)
        self.assertFalse(self.player.is_moving)
        self.assertEqual((12, 10), (self.player.column, self.player.row))
        self.assertEqual(0, self.game.movement.frame_counter)

    def test_letting_go_mid_step_finishes_the_step(self):
        start_x, _ = self.hero_xy()
        self.frames(3, held=(K_LEFT,))
        self.frames(STEP_SYNC_FRAMES * 2)
        self.assertEqual(start_x - self.tile_size, self.player.rect.x)
        self.assertFalse(self.player.is_moving)

    def test_turning_mid_walk_finishes_the_step_then_steps_the_new_way_at_once(self):
        start_x, start_y = self.hero_xy()
        frames_per_step = self.tile_size // self.game.speed
        self.frames(6, held=(K_LEFT,))
        for _ in range(frames_per_step - 6):  # DOWN is ignored until the step to the left is done
            self.frame(held=(K_DOWN,))
            self.assertEqual(Direction.LEFT.value, self.player.direction_value)
            self.assertEqual(start_y, self.player.rect.y)
        self.assertEqual((start_x - self.tile_size, start_y), self.hero_xy())
        # the very next frame turns the hero and starts the step down: no pause
        self.frame(held=(K_DOWN,))
        self.assertEqual(Direction.DOWN.value, self.player.direction_value)
        self.assertEqual((start_x - self.tile_size, start_y + self.game.speed), self.hero_xy())

    # ------------------------------------------------------------------ #
    #  Bumping                                                            #
    # ------------------------------------------------------------------ #

    def test_walking_into_a_wall_turns_and_bumps_every_16_frames(self):
        before = self.hero_xy()
        self.frame(held=(K_UP,))  # King Lorik's table
        self.assertEqual(Direction.UP.value, self.player.direction_value)
        self.assertEqual(1, self.play_sound.call_count)
        self.assertFalse(self.player.is_moving)
        self.assertFalse(self.player.bumped)
        self.frames(STEP_SYNC_FRAMES - 1, held=(K_UP,))
        self.assertEqual(1, self.play_sound.call_count)
        self.frame(held=(K_UP,))
        self.assertEqual(2, self.play_sound.call_count)
        self.frames(STEP_SYNC_FRAMES, held=(K_UP,))
        self.assertEqual(3, self.play_sound.call_count)
        self.assertEqual(before, self.hero_xy())
        self.assertEqual(0, self.game.tiles_moved_since_spawn)

    def test_a_bump_restarts_the_count_for_another_direction_too(self):
        self.frame(held=(K_UP,))  # bump: FrameCounter is reset
        self.assertEqual(STEP_SYNC_FRAMES, self.frames_until_moved((K_LEFT,)))

    def test_walking_up_to_the_wall_bumps_after_the_last_step(self):
        frames_per_step = self.tile_size // self.game.speed
        self.frames(frames_per_step * 2, held=(K_LEFT,))
        self.assertEqual((11, 10), (self.player.column, self.player.row))
        self.play_sound.assert_not_called()
        self.frame(held=(K_LEFT,))  # FrameCounter is 0 right after a step: the bump is at once
        self.assertEqual(1, self.play_sound.call_count)
        self.assertEqual((11, 10), (self.player.column, self.player.row))

    def test_walking_into_an_npc_bumps(self):
        frames_per_step = self.tile_size // self.game.speed
        self.frames(frames_per_step, held=(K_DOWN,))
        self.assertEqual((13, 11), (self.player.column, self.player.row))
        before = self.hero_xy()
        self.frame(held=(K_DOWN,))  # GUARD_2 is at (13, 12)
        self.assertEqual(1, self.play_sound.call_count)
        self.frames(STEP_SYNC_FRAMES * 2, held=(K_DOWN,))
        self.assertEqual(before, self.hero_xy())
        self.assertEqual(3, self.play_sound.call_count)
        self.assertEqual(1, self.game.tiles_moved_since_spawn)

    # ------------------------------------------------------------------ #
    #  Pausing                                                            #
    # ------------------------------------------------------------------ #

    def test_pausing_while_waiting_to_step_does_not_move_the_hero(self):
        self.stand_still(5)
        before = self.hero_xy()
        self.frames(3, held=(K_LEFT,))
        self.frame(keydown(K_i), held=(K_LEFT,))  # FrameCounter 9
        # NES PausePrepLoop keeps calling DoSprites until FrameCounter & $0F is 1, the start of the NPCs' next turn,
        # and the hero doesn't step in the meantime
        for _ in range(STEP_SYNC_FRAMES - 9):
            self.assertFalse(self.game.paused)
            self.frame(held=(K_LEFT,))
        self.assertTrue(self.game.paused)
        self.assertEqual(before, self.hero_xy())
        self.frames(STEP_SYNC_FRAMES * 2, held=(K_LEFT,))
        self.assertEqual(before, self.hero_xy())
        # NES: unpausing ends with JMP JoypadCheckLoop, so FrameCounter is 0 and a held direction steps at once
        self.frame(keydown(K_i), held=(K_LEFT,))
        self.assertFalse(self.game.paused)
        self.assertEqual((before[0] - self.game.speed, before[1]), self.hero_xy())

    def test_pausing_mid_walk_stops_on_the_next_tile(self):
        start_x, _ = self.hero_xy()
        self.frames(4, held=(K_LEFT,))
        self.frame(keydown(K_i), held=(K_LEFT,))
        self.frames(STEP_SYNC_FRAMES * 2, held=(K_LEFT,))
        self.assertTrue(self.game.paused)
        self.assertEqual(start_x - self.tile_size, self.player.rect.x)
        self.assertEqual(1, self.game.tiles_moved_since_spawn)


class TestStepLengthAtEveryScale(FreezeTestCase):
    """The hero moves one NES pixel a frame (TILE_SIZE is 16 * SCALE), so a step is 16 frames at any SCALE, in step
    with NES DoJoyUp etc.'s FrameCounter & $0F check (STEP_SYNC_FRAMES)."""

    scale = 2

    def setUp(self):
        scaled = patch.dict(test_config, SCALE=self.scale, TILE_SIZE=16 * self.scale)
        scaled.start()
        self.addCleanup(scaled.stop)
        super().setUp()
        self.game.game_state.enable_roaming = False
        patch.object(self.game.movement.sound, 'play_sound').start()
        self.addCleanup(patch.stopall)

    def test_a_step_takes_16_frames(self):
        self.assertEqual(16 * self.scale, self.tile_size)
        start_x = self.game.player.rect.x
        self.frames(STEP_SYNC_FRAMES - 1, held=(K_LEFT,))
        self.assertTrue(self.game.player.is_moving)
        self.assertEqual(start_x - (STEP_SYNC_FRAMES - 1) * self.scale, self.game.player.rect.x)
        self.frame(held=(K_LEFT,))
        self.assertFalse(self.game.player.is_moving)
        self.assertEqual(start_x - self.tile_size, self.game.player.rect.x)
        self.assertEqual((12, 10), (self.game.player.column, self.game.player.row))


class TestStepLengthAtScale1(TestStepLengthAtEveryScale):
    scale = 1


class TestStepLengthAtScale3(TestStepLengthAtEveryScale):
    scale = 3
