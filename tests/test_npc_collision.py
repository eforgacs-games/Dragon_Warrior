from unittest import TestCase

import pygame

from src.config.test_config import test_config
from src.direction import Direction
from src.game_functions import set_character_position
from src.maps import MapWithoutNPCs
from src.maps_functions import get_center_point
from src.sprites.roaming_character import RoamingCharacter
from tests.helpers import new_game

BRICK = 3


class OpenRoom(MapWithoutNPCs):
    """A 5x5 room with nothing but floor, so only characters can block a step."""
    __test__ = False

    def __init__(self, config):
        super().__init__([[BRICK] * 5 for _ in range(5)], config, None, (2, 1))

    def hero_underlying_tile(self):
        return 'BRICK'

    def hero_initial_direction(self):
        return Direction.RIGHT.value


class TestNpcCollision(TestCase):
    """You and an NPC heading for the same square: whoever starts the step first gets it, and nobody is
    stopped halfway through a step (NES checks a move once, when it starts, and reserves the destination)."""

    @classmethod
    def setUpClass(cls):
        # pygame isn't quit afterwards: later test modules (e.g. test_player) rely on the display staying up
        pygame.init()

    def setUp(self):
        self.game = new_game({**test_config, 'NO_WAIT': True, 'RENDER_TEXT': False, 'NO_BLIT': True})
        self.tile_size = self.game.tile_size
        self.game.current_map = OpenRoom(self.game.config)
        self.game.current_map.load_map(self.game.player, (2, 1), self.tile_size)
        self.player = self.game.player
        self.player.direction_value = Direction.RIGHT.value
        set_character_position(self.player, self.tile_size)
        images = self.game.current_map.scale_sprite_sheet(self.game.directories.UNARMED_HERO_PATH)
        self.npc = RoamingCharacter(get_center_point(3, 2, self.tile_size), Direction.LEFT.value, images,
                                    'ROAMING_GUARD')
        self.npc.column, self.npc.row = 3, 2
        self.game.current_map.roaming_characters.append(self.npc)

    def step_frame(self, character):
        self.game.move_laterally(character)

    def finish_step(self, character):
        while character.rect.x % self.tile_size:
            self.step_frame(character)
        self.game.finish_step(character)
        set_character_position(character, self.tile_size)

    def tile(self, character):
        return character.rect.x // self.tile_size, character.rect.y // self.tile_size

    def test_player_starts_first_and_gets_the_square(self):
        self.step_frame(self.player)
        self.assertEqual(self.player.step_destination, (2, 2))
        npc_x = self.npc.rect.x
        self.step_frame(self.npc)
        self.assertEqual(self.npc.rect.x, npc_x)  # the NPC is blocked instead of walking into the same square
        self.finish_step(self.player)
        self.assertEqual(self.tile(self.player), (2, 2))
        self.assertEqual(self.tile(self.npc), (3, 2))

    def test_npc_starts_first_and_gets_the_square(self):
        self.step_frame(self.npc)
        self.assertEqual(self.npc.step_destination, (2, 2))
        player_x = self.player.rect.x
        self.step_frame(self.player)
        self.assertEqual(self.player.rect.x, player_x)
        self.assertTrue(self.player.bumped)
        self.finish_step(self.npc)
        self.assertEqual(self.tile(self.npc), (2, 2))
        self.assertEqual(self.tile(self.player), (1, 2))

    def test_no_stopping_halfway_through_a_step(self):
        self.step_frame(self.player)
        # Even if someone ends up in the way mid-step, the step that already started finishes
        self.npc.column, self.npc.row = 2, 2
        x = self.player.rect.x
        self.step_frame(self.player)
        self.assertGreater(self.player.rect.x, x)

    def test_reservation_is_released_on_arrival(self):
        self.step_frame(self.player)
        self.finish_step(self.player)
        self.assertIsNone(self.player.step_origin)
        self.assertIsNone(self.player.step_destination)

    def test_standing_npc_still_blocks(self):
        self.npc.column, self.npc.row = 2, 2
        x = self.player.rect.x
        self.step_frame(self.player)
        self.assertEqual(self.player.rect.x, x)
        self.assertIsNone(self.player.step_destination)
