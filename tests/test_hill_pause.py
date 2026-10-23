"""Stepping onto a hill pauses for three frames (issue #306).

NES CheckBlockDmg (Bank03): after a step onto BLK_HILL, ChkBlkSand calls WaitForNMI three times (LCE0A-LCE10), with
nothing moving and no DoSprites, then makes the step's fight roll (ChkSandFight). Once the Dragonlord is dead,
ChkOtherBlocks returns before any of that, so there is no pause.

On the overworld, row 37 has hills from column 62 to 67 and grass from 68 to 70: the hero starts on the grass at
(37, 68) and walks left onto the hills.
"""
from unittest.mock import patch

from pygame import K_LEFT

from src.movement import HILL_PAUSE_FRAMES, STEP_SYNC_FRAMES
from src.maps import Alefgard
from tests.test_freeze_movement import FreezeTestCase

GRASS = (37, 68)


class TestHillPause(FreezeTestCase):

    def setUp(self):
        super().setUp()
        self.game.change_map(Alefgard(self.game.config), destination_coordinates=GRASS)
        self.player = self.game.player
        self.addCleanup(patch.stopall)
        patch.dict(self.game.game_state.config, NO_BATTLES=True).start()
        patch.object(self.game.movement.sound, 'play_sound').start()
        self.rolls: list[int] = []  # the frame numbers of the fight rolls
        patch.object(self.game, 'roll_for_fight', side_effect=lambda *_: self.rolls.append(self.frame_number)).start()
        self.game.movement.frame_counter = 0

    def hero_tile(self):
        return self.player.rect.y // self.tile_size, self.player.rect.x // self.tile_size

    def walk_left_one_step(self):
        """Hold left from a standstill until the hero arrives on the next tile; returns the frame it arrived on."""
        self.frames(STEP_SYNC_FRAMES, held=(K_LEFT,))
        self.assertFalse(self.player.is_moving)
        return self.frame_number

    def frames_until_moved(self):
        before = self.player.rect.x
        for count in range(1, STEP_SYNC_FRAMES + 1):
            self.frame(held=(K_LEFT,))
            if self.player.rect.x != before:
                return count
        self.fail("The hero didn't move")

    def test_the_pause_is_three_frames(self):
        self.assertEqual(3, HILL_PAUSE_FRAMES)

    def test_a_step_onto_a_hill_waits_three_frames_before_the_next_step(self):
        self.walk_left_one_step()
        self.assertEqual('HILLS', self.player.current_tile)
        self.assertEqual((37, 67), self.hero_tile())
        # three frames of pause, then the next step starts on the frame after them
        self.assertEqual(HILL_PAUSE_FRAMES + 1, self.frames_until_moved())

    def test_a_step_onto_grass_does_not_pause(self):
        self.player.direction_value = 0
        self.game.change_map(Alefgard(self.game.config), destination_coordinates=(37, 70))
        self.game.movement.frame_counter = 0
        self.walk_left_one_step()
        self.assertEqual('GRASS', self.player.current_tile)
        self.assertEqual(1, self.frames_until_moved())

    def test_the_fight_roll_comes_after_the_pause(self):
        arrived = self.walk_left_one_step()
        self.assertEqual([], self.rolls)
        self.frames(HILL_PAUSE_FRAMES)
        self.assertEqual([arrived + HILL_PAUSE_FRAMES], self.rolls)

    def test_nothing_moves_during_the_pause(self):
        self.walk_left_one_step()
        self.assertEqual(0, self.game.movement.frame_counter)
        position = self.player.rect.topleft
        with patch.object(self.game.movement, 'do_sprites') as do_sprites:
            self.frames(HILL_PAUSE_FRAMES, held=(K_LEFT,))
        do_sprites.assert_not_called()
        self.assertEqual(position, self.player.rect.topleft)
        self.assertEqual(0, self.game.movement.frame_counter)

    def test_no_pause_once_the_dragonlord_is_dead(self):
        # NES ChkOtherBlocks returns before ChkBlkSand once F_DGNLRD_DEAD is set
        self.game.story_flags.dragonlord_defeated = True
        self.walk_left_one_step()
        self.assertEqual('HILLS', self.player.current_tile)
        self.assertEqual(1, self.frames_until_moved())
        self.assertEqual([], self.rolls)
