"""NPCS_MAKE_WAY (a modern option, not NES; on by default): a roaming NPC the hero walks into steps out of the way.

Every test runs the main loop's update a frame at a time (Game.get_events) with the keys held, so the hero's bump,
the NES FrameCounter and the NPC schedule (src/npc_schedule.py) all play their part. Random NPC steps are pointed
left (back at the hero, so blocked) unless a test says otherwise, so only making way moves anyone.
"""
from collections import defaultdict
from unittest import TestCase
from unittest.mock import patch

import pygame
from pygame import K_RIGHT

from src.config.test_config import test_config
from src.direction import Direction
from src.game import Game
from src.game_functions import set_character_position
from src.maps import MapWithoutNPCs
from src.maps_functions import get_center_point
from src.npc_schedule import FRAMES_PER_CYCLE, FRAMES_PER_TURN
from src.sprites.fixed_character import FixedCharacter
from src.sprites.roaming_character import RoamingCharacter

W, B = 1, 3  # WALL, BRICK

# A corridor one tile high along row 2, with an alcove above and below column 3
CORRIDOR = [
    [W, W, W, W, W, W, W],
    [W, W, W, B, W, W, W],
    [B, B, B, B, B, B, B],
    [W, W, W, B, W, W, W],
    [W, W, W, W, W, W, W],
]
# The same corridor with no alcoves, ending in a wall at column 4
DEAD_END = [
    [W, W, W, W, W, W, W],
    [W, W, W, W, W, W, W],
    [B, B, B, B, W, W, W],
    [W, W, W, W, W, W, W],
    [W, W, W, W, W, W, W],
]
# No alcoves, but the corridor goes on past the NPC
STRAIGHT = [
    [W, W, W, W, W, W, W],
    [W, W, W, W, W, W, W],
    [B, B, B, B, B, B, B],
    [W, W, W, W, W, W, W],
    [W, W, W, W, W, W, W],
]
HERO_START = (2, 2)  # (row, column): just left of the NPC
NPC_TILE = (3, 2)  # (column, row)


def keys_held(*held_keys):
    # A dict, not an array: pygame key codes for the arrows are over a billion
    return defaultdict(int, {held_key: 1 for held_key in held_keys})


class Corridor(MapWithoutNPCs):
    __test__ = False

    def __init__(self, config, layout):
        super().__init__([row[:] for row in layout], config, None, HERO_START)
        self.identifier = 'TestCorridor'

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class MakeWayTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((800, 600))

    def make_game(self, layout, make_way=True):
        with patch('src.game.SCALED'):
            self.game = Game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True,
                              'NO_BATTLES': True, 'NPCS_MAKE_WAY': make_way})
        self.game.game_state.is_initial_dialog = False
        self.tile_size = self.game.tile_size
        self.game.current_map = Corridor(self.game.config, layout)
        self.game.current_map.load_map(self.game.player, HERO_START, self.tile_size)
        self.game.player.direction_value = Direction.RIGHT.value
        self.layout = layout
        patcher = patch.object(self.game.movement.sound, 'play_sound')
        patcher.start()
        self.addCleanup(patcher.stop)
        pygame.event.clear()

    def add_npc(self, column, row, roaming=True, name='NPC'):
        images = self.game.current_map.scale_sprite_sheet(self.game.directories.UNARMED_HERO_PATH)
        cls = RoamingCharacter if roaming else FixedCharacter
        npc = cls(get_center_point(column, row, self.tile_size), Direction.LEFT.value, images, name)
        npc.column, npc.row = column, row
        if roaming:
            self.game.current_map.roaming_characters.append(npc)
        else:
            self.game.current_map.fixed_characters.append(npc)
        self.game.current_map.characters[name] = {'character': npc}
        return npc

    def start(self):
        """Line the NPC turns up so the hero's first frame holding a direction tries a step, and the first NPC's own
        turn (slot 0) is as far away as it can be."""
        set_character_position(self.game.player, self.tile_size)
        self.game.set_roaming_character_positions()
        self.game.frame_counter = 0
        self.game.npc_schedule.update_counter = 1

    def frame(self, held=()):
        with patch('src.game.key') as mock_key:
            mock_key.get_pressed.return_value = keys_held(*held)
            self.game.get_events()
        self.check_nobody_overlaps()

    def frames(self, count, held=(), random_direction=Direction.LEFT.value):
        with patch('src.game.random.choice', return_value=random_direction):
            for _ in range(count):
                self.frame(held=held)

    def tile(self, character):
        return character.column, character.row

    def everyone(self):
        return [self.game.player, *self.game.current_map.roaming_characters, *self.game.current_map.fixed_characters]

    def check_nobody_overlaps(self):
        """Each character's tile (and, mid-step, both tiles it's between) is its own, on the map and walkable."""
        taken = []
        for character in self.everyone():
            tiles = {(character.rect.x // self.tile_size, character.rect.y // self.tile_size),
                     ((character.rect.right - 1) // self.tile_size, (character.rect.bottom - 1) // self.tile_size)}
            for column, row in tiles:
                self.assertTrue(0 <= row < len(self.layout) and 0 <= column < len(self.layout[0]), character)
                self.assertEqual(B, self.layout[row][column], (character.identifier, column, row))
                self.assertNotIn((column, row), taken, character.identifier)
            taken.extend(tiles)


class TestNpcsMakeWay(MakeWayTestCase):

    def test_an_npc_in_a_one_tile_corridor_steps_aside_and_the_hero_passes(self):
        self.make_game(CORRIDOR)
        npc = self.add_npc(*NPC_TILE)
        self.start()
        self.frame(held=(K_RIGHT,))
        self.assertTrue(self.game.player.bumped is False and self.tile(self.game.player) == (2, 2))
        # The step aside started at once, sideways, like any NPC step: a pixel a frame, the walking frame its own
        self.assertTrue(npc.is_moving)
        self.assertIn(npc.direction_value, (Direction.UP.value, Direction.DOWN.value))
        self.assertIn(npc.step_destination, ((3, 1), (3, 3)))
        self.assertEqual(self.tile_size // 16, abs(npc.rect.y - npc.last_rect.y))
        offsets = []
        for _ in range(FRAMES_PER_TURN - 1):
            self.frames(1, held=(K_RIGHT,))
            offsets.append(abs(npc.rect.y - npc.last_rect.y) // (self.tile_size // 16))
        self.assertEqual(list(range(2, FRAMES_PER_TURN + 1)), offsets)
        self.assertFalse(npc.is_moving)
        self.assertIn(self.tile(npc), ((3, 1), (3, 3)))
        # The hero, still holding right, walks on through on the very next frame
        self.frames(3 * FRAMES_PER_TURN, held=(K_RIGHT,))
        self.assertEqual((5, 2), self.tile(self.game.player))

    def test_it_stands_still_through_its_next_turn_so_it_does_not_walk_straight_back(self):
        self.make_game(CORRIDOR)
        npc = self.add_npc(*NPC_TILE)
        self.start()
        self.frames(FRAMES_PER_TURN, held=(K_RIGHT,))
        aside = self.tile(npc)
        back = Direction.DOWN.value if aside == (3, 1) else Direction.UP.value
        # The hero lets go. Its own next turn comes within the cycle: it rests, though the way back is free
        self.frames(FRAMES_PER_CYCLE - FRAMES_PER_TURN, random_direction=back)
        self.assertEqual(aside, self.tile(npc))
        self.assertEqual(0, npc.turns_to_rest)
        # On the turn after, it walks as usual again
        self.frames(FRAMES_PER_CYCLE, random_direction=back)
        self.assertEqual(NPC_TILE, self.tile(npc))

    def test_it_avoids_another_npc_in_one_alcove(self):
        self.make_game(CORRIDOR)
        npc = self.add_npc(*NPC_TILE)
        other = self.add_npc(3, 1, name='OTHER')
        self.start()
        for _ in range(5):  # whichever side it would have liked
            self.frames(FRAMES_PER_TURN, held=(K_RIGHT,))
        self.assertEqual((3, 3), self.tile(npc))
        self.assertEqual((3, 1), self.tile(other))

    def test_with_no_way_to_the_side_it_steps_on_ahead(self):
        self.make_game(STRAIGHT)
        npc = self.add_npc(*NPC_TILE)
        self.start()
        self.frames(FRAMES_PER_TURN, held=(K_RIGHT,))
        self.assertEqual((4, 2), self.tile(npc))
        self.assertEqual(Direction.RIGHT.value, npc.direction_value)

    def test_with_nowhere_to_go_nothing_happens(self):
        for layout, blockers in ((DEAD_END, ()), (CORRIDOR, ((3, 1), (3, 3), (4, 2)))):
            with self.subTest(blockers=blockers):
                self.make_game(layout)
                npc = self.add_npc(*NPC_TILE)
                for index, (column, row) in enumerate(blockers):
                    self.add_npc(column, row, name=f'BLOCKER_{index}')
                self.start()
                facing = npc.direction_value
                for _ in range(4 * FRAMES_PER_TURN):
                    self.frames(1, held=(K_RIGHT,))
                    self.assertEqual(NPC_TILE, self.tile(npc))
                    self.assertFalse(npc.is_moving)
                self.assertEqual(facing, npc.direction_value)
                self.assertEqual(0, npc.turns_to_rest)
                self.assertEqual((2, 2), self.tile(self.game.player))

    def test_static_npcs_never_move(self):
        self.make_game(CORRIDOR)
        npc = self.add_npc(*NPC_TILE, roaming=False)
        self.start()
        self.frames(4 * FRAMES_PER_TURN, held=(K_RIGHT,))
        self.assertEqual(NPC_TILE, self.tile(npc))
        self.assertEqual((npc.rect.x, npc.rect.y), (3 * self.tile_size, 2 * self.tile_size))
        self.assertEqual((2, 2), self.tile(self.game.player))

    def test_with_the_option_off_the_npc_stays_put_as_on_the_nes(self):
        self.make_game(CORRIDOR, make_way=False)
        npc = self.add_npc(*NPC_TILE)
        self.start()
        self.frames(4 * FRAMES_PER_TURN, held=(K_RIGHT,))
        self.assertEqual(NPC_TILE, self.tile(npc))
        self.assertEqual((2, 2), self.tile(self.game.player))
        self.assertIsNone(self.game.npc_asked_to_make_way)

    def test_the_option_is_on_by_default(self):
        from src.config.prod_config import prod_config
        self.assertTrue(prod_config['NPCS_MAKE_WAY'])

    def test_facing_an_npc_and_talking_does_not_move_it(self):
        self.make_game(CORRIDOR)
        npc = self.add_npc(*NPC_TILE)
        self.start()
        self.frames(FRAMES_PER_TURN)  # standing, facing the NPC
        self.game.cmd_menu.current_map = self.game.current_map
        self.game.cmd_menu.characters = self.game.current_map.characters
        with patch.object(self.game.cmd_menu, 'launch_dialog') as launch_dialog, \
                patch.object(self.game, 'unlaunch_menu'):
            self.game.cmd_menu.talk()
        launch_dialog.assert_called_once_with('NPC', self.game.current_map)
        self.frames(2 * FRAMES_PER_TURN)
        self.assertEqual(NPC_TILE, self.tile(npc))
        self.assertIsNone(self.game.npc_asked_to_make_way)

    def test_it_never_steps_under_a_roof(self):
        # NES $B839-$B84F: an NPC can't step between a covered and an uncovered block; making way is no exception
        self.make_game(CORRIDOR)
        self.game.current_map.covered_area = frozenset({(1, 3)})  # (row, column): the upper alcove
        npc = self.add_npc(*NPC_TILE)
        self.start()
        for _ in range(5):  # whichever side it would have liked
            self.frames(FRAMES_PER_TURN, held=(K_RIGHT,))
        self.assertEqual((3, 3), self.tile(npc))
