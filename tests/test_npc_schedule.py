"""Roaming NPCs take turns, two at a time, on the NES's 16-frame schedule instead of all stepping together.

NES DoSprites/UpdateNPCs1/UpdateNPCCounter (Bank00): see src/npc_schedule.py. The game is run a frame at a time
(MovementController.sprites_frame, which the main loop calls once a frame) and checked against that schedule.
"""
import os
import random
from unittest import TestCase
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame  # noqa: E402

from src.config.test_config import test_config  # noqa: E402
from src.direction import Direction  # noqa: E402
from src.game import Game  # noqa: E402
from src.maps import MapWithoutNPCs  # noqa: E402
from src.maps_functions import get_center_point  # noqa: E402
from pygame import K_LEFT  # noqa: E402

from src.npc_schedule import FRAMES_PER_CYCLE, FRAMES_PER_TURN, MOBILE_NPC_SLOTS, NPCS_PER_TURN, POP_UP_FRAME, \
    TURNS_PER_CYCLE  # noqa: E402
from src.sprites.animated_sprite import AnimatedSprite  # noqa: E402
from src.sprites.roaming_character import RoamingCharacter  # noqa: E402
from tests.test_freeze_movement import FreezeTestCase  # noqa: E402

BRICK = 3
CYCLES = 5


def turn_of(frame: int) -> int:
    """The pair (NPCUpdateCntr) whose turn frame `frame` (1 = the first frame on the map) is in."""
    return (frame - 1) // FRAMES_PER_TURN % TURNS_PER_CYCLE


def make_game(start_map: str) -> Game:
    with patch('src.game.SCALED', 0):
        game = Game({**test_config, 'START_MAP': start_map, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True})
    game.game_state.is_initial_dialog = False
    return game


class TestNpcScheduleInTown(TestCase):
    """Cantlin, with its 10 roaming NPCs: every mobile slot is used, so all 5 pairs take turns."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    def setUp(self):
        self.game = make_game('Cantlin')
        self.npcs = self.game.current_map.roaming_characters
        self.assertEqual(MOBILE_NPC_SLOTS, len(self.npcs))
        self.tile_size = self.game.tile_size
        self.nes_pixel = self.tile_size // 16

    def run_frames(self, frames: int, seed: int = 0):
        """Run `frames` frames from the map's first, with the NPCs picking seeded random directions. Returns the frames
        each NPC decided on (by slot), and each NPC's top left corner before the first frame (positions[0]) and after
        every frame (positions[frame])."""
        decisions: dict[int, list[int]] = {slot: [] for slot in range(len(self.npcs))}
        positions = [[npc.rect.topleft for npc in self.npcs]]
        frame = [0]
        start_npc_step = self.game.movement.start_npc_step

        def spy(npc):
            decisions[self.npcs.index(npc)].append(frame[0])
            start_npc_step(npc)

        with patch('src.movement.random', random.Random(seed)), patch.object(self.game.movement, 'start_npc_step', spy):
            for frame[0] in range(1, frames + 1):
                self.game.movement.sprites_frame()
                positions.append([npc.rect.topleft for npc in self.npcs])
        return decisions, positions

    def test_each_pair_decides_only_on_the_first_frame_of_its_turn(self):
        decisions, _ = self.run_frames(CYCLES * FRAMES_PER_CYCLE)
        for slot in range(MOBILE_NPC_SLOTS):
            pair = slot // NPCS_PER_TURN
            # NES: FrameCounter & $0F == 1, and NPCUpdateCntr == pair; the first frame on a map is pair 0's
            expected = [cycle * FRAMES_PER_CYCLE + pair * FRAMES_PER_TURN + 1 for cycle in range(CYCLES)]
            self.assertEqual(expected, decisions[slot], self.npcs[slot].identifier)

    def test_npcs_are_not_in_lock_step(self):
        # The bug: every NPC picked a new step on the same frame, every second
        decisions, _ = self.run_frames(FRAMES_PER_CYCLE)
        first_decisions = [frames[0] for frames in decisions.values()]
        self.assertEqual([1, 1, 17, 17, 33, 33, 49, 49, 65, 65], first_decisions)

    def test_steps_move_a_pixel_a_frame_for_the_whole_turn_and_never_overlap(self):
        frames = CYCLES * FRAMES_PER_CYCLE
        decisions, positions = self.run_frames(frames, seed=3)
        steps = 0
        for slot in range(MOBILE_NPC_SLOTS):
            for decision_frame in decisions[slot]:
                before_x, before_y = positions[decision_frame - 1][slot]
                moved = [abs(x - before_x) + abs(y - before_y)
                         for x, y in (positions[decision_frame + k][slot] for k in range(FRAMES_PER_TURN))]
                if moved[-1] == 0:
                    self.assertEqual([0] * FRAMES_PER_TURN, moved)  # blocked: stays put the whole turn
                    continue
                steps += 1
                # 1 NES pixel on each of the turn's 16 frames, arriving on a tile on the last one
                self.assertEqual([self.nes_pixel * k for k in range(1, FRAMES_PER_TURN + 1)], moved)
        self.assertGreater(steps, CYCLES * MOBILE_NPC_SLOTS // 4)
        # Nobody outside the pair on turn ever moves, so steps of different pairs never overlap
        for frame in range(1, frames + 1):
            for slot in range(MOBILE_NPC_SLOTS):
                if positions[frame][slot] != positions[frame - 1][slot]:
                    self.assertEqual(turn_of(frame), slot // NPCS_PER_TURN, (frame, slot))

    def test_everyone_swaps_legs_together_every_16_frames(self):
        # NES CharLeftRight: one walking frame for the hero and every NPC, moved on when FrameCounter & $0F is 0
        characters = [character_dict['character'] for character_dict in self.game.current_map.characters.values()]
        self.assertIn(self.game.player, characters)
        first = AnimatedSprite.walk_frame
        with patch('src.movement.random', random.Random(5)):
            for frame in range(1, 3 * FRAMES_PER_TURN + 1):
                self.game.movement.sprites_frame()
                for character in characters:
                    character.animate()
                expected = first ^ (frame // FRAMES_PER_TURN % 2)
                self.assertEqual({expected}, {character.current_frame for character in characters}, frame)

    def test_a_new_map_starts_with_the_first_pair(self):
        self.game.movement.npc_schedule.give_turn_to(7)
        self.game.movement.sprites_frame()
        self.game.set_roaming_character_positions()  # what MapManager.change_map does
        decisions, _ = self.run_frames(1)
        self.assertEqual([[1], [1]] + [[]] * 8, [decisions[slot] for slot in range(MOBILE_NPC_SLOTS)])


class OpenRoom(MapWithoutNPCs):
    """A room with nothing but floor, so nothing but the edge can stop a step."""
    __test__ = False

    def __init__(self, config):
        super().__init__([[BRICK] * 24 for _ in range(24)], config, None, (1, 1))

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.DOWN.value


class TestNpcWalkingRate(TestCase):
    """Over a long run, each roaming NPC that's never blocked takes exactly one step every 80 frames (1.33 s)."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    def setUp(self):
        self.game = make_game('TantegelThroneRoom')
        self.tile_size = self.game.tile_size
        self.game.current_map = OpenRoom(self.game.config)
        self.game.current_map.load_map(self.game.player, (1, 1), self.tile_size)

    def add_npcs(self, count):
        images = self.game.current_map.scale_sprite_sheet(self.game.directories.UNARMED_HERO_PATH)
        npcs = []
        for index in range(count):
            row, column = 3 + 2 * index, 10
            npc = RoamingCharacter(get_center_point(column, row, self.tile_size), Direction.DOWN.value, images,
                                   f'NPC_{index}')
            npc.row, npc.column = row, column
            self.game.current_map.roaming_characters.append(npc)
            npcs.append(npc)
        self.game.set_roaming_character_positions()
        return npcs

    def walk(self, npcs, cycles):
        """Run `cycles` 80-frame cycles with the NPCs walking left and right in turn. Returns each NPC's steps."""
        steps = [0] * len(npcs)
        directions = {}

        def choose(_directions):
            # Whichever NPC is deciding: the opposite of its last step, so it stays near where it started
            npc = deciding[0]
            directions[npc] = Direction.RIGHT.value if directions.get(npc) == Direction.LEFT.value \
                else Direction.LEFT.value
            return directions[npc]

        deciding = [None]
        start_npc_step = self.game.movement.start_npc_step

        def spy(npc):
            deciding[0] = npc
            start_npc_step(npc)

        with patch('src.movement.random.choice', side_effect=choose), patch.object(self.game.movement, 'start_npc_step', spy):
            for _ in range(cycles * FRAMES_PER_CYCLE):
                tiles = [(npc.row, npc.column) for npc in npcs]
                self.game.movement.sprites_frame()
                for index, npc in enumerate(npcs):
                    if (npc.row, npc.column) != tiles[index]:
                        steps[index] += 1
        return steps

    def test_one_step_every_80_frames_whatever_the_number_of_npcs(self):
        cycles = 60  # 4800 frames: 80 seconds at 60 frames a second
        for count in (1, 3, 10):
            with self.subTest(npcs=count):
                self.setUp()
                npcs = self.add_npcs(count)
                # NES: 5 turns of 16 frames whatever the number of NPCs, so 1 step per NPC per 80 frames
                self.assertEqual([cycles] * count, self.walk(npcs, cycles))

    def test_both_npcs_of_a_pair_step_together_and_the_pairs_one_after_another(self):
        npcs = self.add_npcs(MOBILE_NPC_SLOTS)
        offsets = []  # each frame: how far each NPC is from its tile, in NES pixels
        with patch('src.movement.random.choice', return_value=Direction.RIGHT.value):
            for _ in range(FRAMES_PER_CYCLE):
                self.game.movement.sprites_frame()
                offsets.append([npc.rect.x % self.tile_size // (self.tile_size // 16) for npc in npcs])
        for frame, frame_offsets in enumerate(offsets, start=1):
            pair = turn_of(frame)
            phase = frame % FRAMES_PER_TURN
            for slot, offset in enumerate(frame_offsets):
                # The pair on turn is `phase` pixels into its step (and back on a tile on the turn's last frame)
                self.assertEqual(phase if slot // NPCS_PER_TURN == pair else 0, offset, (frame, slot))
        # One step each in the cycle
        self.assertEqual([11] * MOBILE_NPC_SLOTS, [npc.column for npc in npcs])


class TestHeroAndNpcsShareTheFrameCounter(FreezeTestCase):
    """The throne room, a frame at a time through the main loop's update (Game.get_events). The hero and the NPCs read
    the same NES FrameCounter, so the hero's steps take exactly one NPC turn, from its first frame to its last."""

    def setUp(self):
        super().setUp()
        patcher = patch.object(self.game.movement.sound, 'play_sound')
        patcher.start()
        self.addCleanup(patcher.stop)

    def frames_until_the_hero_moves(self, held):
        before = self.game.player.rect.topleft
        for count in range(1, 3 * FRAMES_PER_TURN + 1):
            self.frame(held=held)
            if self.game.player.rect.topleft != before:
                return count
        self.fail("The hero didn't move")

    def test_the_hero_steps_on_the_first_frame_of_an_npc_turn(self):
        for idle_frames in range(0, 3 * FRAMES_PER_TURN, 5):
            with self.subTest(idle_frames=idle_frames):
                self.setUp()
                self.game.game_state.enable_roaming = False  # keep the guard out of the way
                self.frames(idle_frames)
                self.frames_until_the_hero_moves((K_LEFT,))
                self.assertTrue(self.game.movement.npc_schedule.is_decision_frame)
                self.frames(FRAMES_PER_TURN - 1, held=(K_LEFT,))
                self.assertFalse(self.game.player.is_moving)  # arrived on the turn's last frame
                self.assertTrue(self.game.movement.npc_schedule.between_turns)
                # and the next step starts at once, on the next turn's first frame
                self.assertEqual(1, self.frames_until_the_hero_moves((K_LEFT,)))
                self.assertTrue(self.game.movement.npc_schedule.is_decision_frame)

    def test_the_pop_up_window_opens_on_the_pop_up_frame(self):
        # NES IdleUpdate: on the $31st frame of standing still, counted in frames like the steps and the NPC turns,
        # not on the game clock (which the drawer used to read, so it opened a couple of frames later, and further off
        # when the map ran slower or faster than the clock)
        drawer = self.game.drawer
        self.frames(POP_UP_FRAME - 1)
        self.assertFalse(drawer.display_hovering_stats)
        self.frame()
        self.assertTrue(drawer.display_hovering_stats)

    def test_the_pop_up_window_opens_after_the_kings_words(self):
        # The automatic dialogs keep it closed while they wait for a button; the hero has been standing all along
        drawer = self.game.drawer
        drawer.display_hovering_stats = False
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box'), patch('src.drawer.display'):
            drawer.run_automatic_initial_dialog([], True, self.game.cmd_menu)
        self.assertTrue(drawer.display_hovering_stats)
        drawer.display_hovering_stats = False
        with patch.object(self.game.cmd_menu, 'show_text_in_dialog_box'), patch('src.drawer.set_to_save_prompt'):
            drawer.run_automatic_post_death_dialog([], True, self.game.cmd_menu)
        self.assertTrue(drawer.display_hovering_stats)

    def test_the_pop_up_window_frame_runs_two_npc_frames(self):
        # NES IdleUpdate on FrameCounter $31: the pop-up window's drawing calls DoSprites (WndCalcBufAddr), then
        # FrameCounter is set to $32 and DoSprites runs again
        self.game.game_state.enable_roaming = False  # the guard stays where he starts until his turn below
        self.frames(POP_UP_FRAME - 1)
        self.assertEqual(POP_UP_FRAME - 1, self.game.movement.frame_counter)
        self.game.game_state.enable_roaming = True
        self.game.movement.npc_schedule.update_counter = 0  # the guard's turn is next
        offsets = []
        with patch('src.movement.random.choice', return_value=Direction.LEFT.value):
            for _ in range(FRAMES_PER_TURN - 1):
                self.frame()
                offsets.append((self.guard.last_rect.x - self.guard.rect.x) // (self.tile_size // 16))
        self.assertEqual(0x40, self.game.movement.frame_counter)  # the turn still ends on a multiple of 16
        # 2 pixels on the pop-up frame, then 1 a frame: the step still ends on the turn's last frame
        self.assertEqual(list(range(2, FRAMES_PER_TURN + 1)), offsets)
        self.assertFalse(self.guard.is_moving)
